#include "main.h"
#include "usb_device.h"
#include "usbd_cdc_if.h"
#include "protocol.h"
#include <string.h>

// ---------------------------------------------------------------------------
// Machine state — written by CDC RX callback, read by ISR and main loop
// ---------------------------------------------------------------------------
extern USBD_HandleTypeDef hUsbDeviceHS;
extern TIM_HandleTypeDef  htim2;

volatile uint8_t  is_powered    = 0;
volatile uint8_t  steam_mode    = 0;
volatile char     control_mode  = 'P';
volatile float    target_val    = 0.0f;
volatile float    target_tw     = 20.0f;
volatile float    target_tg     = 20.0f;
volatile float    flow_limit    = 0.0f;
volatile float    pressure_limit = 0.0f;

// Simulation state (replace with real sensor reads on hardware)
volatile float sim_p         = 0.0f;
volatile float sim_f         = 0.0f;
volatile float sim_w         = 0.0f;
volatile float sim_tw        = 20.0f;
volatile float sim_tg        = 20.0f;
volatile float sim_pump_duty = 0.0f;

// ---------------------------------------------------------------------------
// Microsecond counter — incremented by 1000 each 1 kHz ISR tick
// ---------------------------------------------------------------------------
volatile uint32_t us_counter = 0;

// ---------------------------------------------------------------------------
// Ring buffer  (power-of-2 size for cheap modulo)
// ISR writes ring_head; main loop reads ring_tail — no critical section needed
// on single-core ARM where uint32_t reads/writes are atomic.
// ---------------------------------------------------------------------------
#define RING_SIZE  64u           // must be power of 2; 64 × 1 ms = 64 ms depth
#define RING_MASK  (RING_SIZE - 1u)

static Sample_t         ring[RING_SIZE];
volatile uint32_t       ring_head        = 0;
volatile uint32_t       ring_tail        = 0;
volatile uint8_t        ring_overrun_count = 0;

// ---------------------------------------------------------------------------
// TX state
// tx_ready is cleared when a transfer starts and set in the TX-complete
// callback, avoiding the DMA race of the previous double-buffer design.
// ---------------------------------------------------------------------------
#define TX_BUF_SIZE  512u

#if defined(__GNUC__)
__attribute__((aligned(32)))
#endif
static uint8_t          tx_buf[TX_BUF_SIZE];
volatile uint8_t        tx_ready = 1;

// Pending ACK — queued by the command handler, sent by the main loop
// when TX is free, so ACK transmission never races with telemetry.
static volatile uint8_t ack_pending = 0;
static volatile uint8_t ack_seq     = 0;
static volatile uint8_t ack_opcode  = 0;

// ---------------------------------------------------------------------------
// frame_and_send — builds a complete framed packet into tx_buf and transmits.
// Must only be called when tx_ready == 1.
// ---------------------------------------------------------------------------
static void frame_and_send(uint8_t ptype, const void *payload, uint16_t plen) {
    uint16_t total = FRAME_HEADER_LEN + plen + FRAME_CRC_LEN;
    if (total > TX_BUF_SIZE) return;

    tx_buf[0] = PROTO_SYNC0;
    tx_buf[1] = PROTO_SYNC1;
    tx_buf[2] = ptype;
    tx_buf[3] = (uint8_t)(plen & 0xFFu);
    tx_buf[4] = (uint8_t)(plen >> 8);
    memcpy(tx_buf + FRAME_HEADER_LEN, payload, plen);

    // CRC covers TYPE + LEN (2 bytes) + PAYLOAD
    uint16_t crc = proto_crc16(tx_buf + 2, 3u + plen);
    tx_buf[FRAME_HEADER_LEN + plen]     = (uint8_t)(crc & 0xFFu);
    tx_buf[FRAME_HEADER_LEN + plen + 1] = (uint8_t)(crc >> 8);

    tx_ready = 0;
    CDC_Transmit_HS(tx_buf, total);
}

// Called by the USB CDC middleware when the previous TX transfer completes.
// Clearing tx_ready here (not after CDC_Transmit_HS returns) avoids the
// DMA race where the ISR could swap into a buffer still being read by DMA.
void CDC_TransmitCplt_HS(uint8_t *Buf, uint32_t *Len, uint8_t epnum) {
    (void)Buf; (void)Len; (void)epnum;
    tx_ready = 1;
}

// ---------------------------------------------------------------------------
// 1 kHz ISR — reads sensors (simulation here), pushes to ring buffer
// ---------------------------------------------------------------------------
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {
    if (htim->Instance != TIM2) return;

    const float dt = 0.001f;
    us_counter += 1000u;

    // --- Thermal simulation (replace with ADC reads) ---
    float sp_w = is_powered ? (steam_mode ? 140.0f : target_tw) : 20.0f;
    float sp_g = is_powered ? target_tg : 20.0f;
    sim_tw += (sim_tw < sp_w) ?  2.0f * dt : -0.5f * dt;
    sim_tg += (sim_tg < sp_g) ?  0.5f * dt : -0.1f * dt;

    // --- Hydraulic simulation (replace with sensor reads + PID output) ---
    if (is_powered) {
        float pv  = (control_mode == 'P') ? sim_p : sim_f;
        float err = target_val - pv;
        sim_pump_duty += err * 5.0f * dt;
        if (sim_pump_duty < 0.0f)  sim_pump_duty = 0.0f;
        if (sim_pump_duty > 12.0f) sim_pump_duty = 12.0f;
        sim_p = sim_pump_duty;
        if (pressure_limit > 0.0f && sim_p > pressure_limit) sim_p = pressure_limit;
        sim_f = sim_p / 1.5f;
        if (flow_limit > 0.0f && sim_f > flow_limit) sim_f = flow_limit;
        if (sim_f < 0.0f) sim_f = 0.0f;
        sim_w += sim_f * dt;
    } else {
        sim_p = 0.0f; sim_f = 0.0f; sim_pump_duty = 0.0f;
        // Weight intentionally not reset — persists until TARE command
    }

    // --- Push sample to ring buffer ---
    uint32_t next_head = (ring_head + 1u) & RING_MASK;
    if (next_head == ring_tail) {
        // Ring is full: count the overrun, drop this sample
        if (ring_overrun_count < 255u) ring_overrun_count++;
        return;
    }
    ring[ring_head].timestamp_us = us_counter;
    ring[ring_head].pressure     = sim_p;
    ring[ring_head].flow         = sim_f;
    ring[ring_head].weight       = sim_w;
    ring[ring_head].temp_water   = sim_tw;
    ring[ring_head].temp_group   = sim_tg;
    ring_head = next_head;   // publish atomically (single word write on ARM)
}

// ---------------------------------------------------------------------------
// Main loop
// ---------------------------------------------------------------------------
int main(void) {
    HAL_Init();
    SystemClock_Config();
    MX_USB_DEVICE_Init();
    MX_TIM2_Init();
    HAL_TIM_Base_Start_IT(&htim2);

    uint32_t last_telemetry_tick = 0;

    while (1) {

        // --- 1. Send pending ACK (highest priority — sent before next telemetry) ---
        if (ack_pending && tx_ready) {
            AckPayload_t ack = { ack_seq, ack_opcode };
            ack_pending = 0;
            frame_and_send(PKT_ACK, &ack, sizeof(ack));
        }

        // --- 2. Send telemetry at 100 Hz (every 10 ms) ---
        uint32_t now = HAL_GetTick();
        if (tx_ready && (now - last_telemetry_tick >= 10u)) {
            uint32_t avail = (ring_head - ring_tail) & RING_MASK;
            if (avail >= SAMPLES_PER_PACKET) {
                last_telemetry_tick = now;

                TelemetryPayload_t pkt;

                // Snapshot machine state
                pkt.state.target_val    = target_val;
                pkt.state.target_tw     = target_tw;
                pkt.state.target_tg     = target_tg;
                pkt.state.flow_limit    = flow_limit;
                pkt.state.pressure_limit = pressure_limit;
                pkt.state.flags         = (is_powered  ? STATE_FLAG_POWERED : 0u)
                                        | (steam_mode  ? STATE_FLAG_STEAM   : 0u);
                pkt.state.control_mode  = (uint8_t)control_mode;
                pkt.state.overrun_count = ring_overrun_count;
                pkt.state._pad          = 0;
                ring_overrun_count      = 0;   // reset after reporting

                // Drain 10 samples from ring buffer
                for (uint32_t i = 0; i < SAMPLES_PER_PACKET; i++) {
                    pkt.samples[i] = ring[ring_tail];
                    ring_tail = (ring_tail + 1u) & RING_MASK;
                }

                frame_and_send(PKT_TELEMETRY, &pkt, sizeof(pkt));
            }
        }
    }
}
