#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

// ---------------------------------------------------------------------------
// Frame format (both directions):
//   [0xAA][0x55][TYPE:1][LEN:2 LE][PAYLOAD:LEN][CRC16:2 LE]
//   CRC16-CCITT (poly=0x1021, init=0xFFFF) over TYPE+LEN+PAYLOAD
// ---------------------------------------------------------------------------

#define PROTO_SYNC0  0xAAu
#define PROTO_SYNC1  0x55u

// Packet types — MCU→Pi
#define PKT_TELEMETRY  0x01u   // 100 Hz: 10 raw samples + machine state
#define PKT_ACK        0x02u   // command acknowledgement
#define PKT_ERROR      0x03u   // error report

// Packet types — Pi→MCU
#define PKT_COMMAND    0x10u   // binary command with optional float value
#define PKT_PING       0x11u   // keepalive; MCU responds with ACK(seq=0, op=0)

// ---------------------------------------------------------------------------
// Command opcodes  (PKT_COMMAND payload byte 1)
// ---------------------------------------------------------------------------
typedef enum {
    CMD_POWER_ON  = 0x01,
    CMD_POWER_OFF = 0x02,
    CMD_TARE      = 0x03,
    CMD_STOP      = 0x04,
    CMD_STEAM_ON  = 0x05,
    CMD_STEAM_OFF = 0x06,
    CMD_SET_P     = 0x10,   // value = bar
    CMD_SET_F     = 0x11,   // value = ml/s
    CMD_SET_TW    = 0x12,   // value = °C  (water setpoint)
    CMD_SET_TG    = 0x13,   // value = °C  (group setpoint)
    CMD_SET_FL    = 0x14,   // value = ml/s flow limit (0 = off)
    CMD_SET_PL    = 0x15,   // value = bar  pressure limit (0 = off)
} CmdOpcode_t;

// ---------------------------------------------------------------------------
// Telemetry structures  (all packed — no implicit padding)
// ---------------------------------------------------------------------------

// One raw sensor sample: 24 bytes
typedef struct __attribute__((packed)) {
    uint32_t timestamp_us;   // free-running MCU microsecond counter
    float    pressure;       // bar
    float    flow;           // ml/s
    float    weight;         // g (persists across power cycles until TARE)
    float    temp_water;     // °C
    float    temp_group;     // °C
} Sample_t;

// MachineState_t flags byte
#define STATE_FLAG_POWERED  (1u << 0)
#define STATE_FLAG_STEAM    (1u << 1)

// Machine state snapshot included in every telemetry packet: 24 bytes
typedef struct __attribute__((packed)) {
    float    target_val;       // current setpoint (bar or ml/s depending on control_mode)
    float    target_tw;        // water temperature setpoint °C
    float    target_tg;        // group temperature setpoint °C
    float    flow_limit;       // ml/s cap (0 = disabled)
    float    pressure_limit;   // bar cap in flow mode (0 = disabled)
    uint8_t  flags;            // STATE_FLAG_* bits
    uint8_t  control_mode;     // 'P' (0x50) or 'F' (0x46)
    uint8_t  overrun_count;    // ring-buffer overruns since last packet (resets each packet)
    uint8_t  _pad;
} MachineState_t;

#define SAMPLES_PER_PACKET  10u   // 10 × 1 ms = 10 ms per packet → 100 Hz packet rate

// Full telemetry payload: 24 + 10×24 = 264 bytes
typedef struct __attribute__((packed)) {
    MachineState_t state;
    Sample_t       samples[SAMPLES_PER_PACKET];
} TelemetryPayload_t;

// ---------------------------------------------------------------------------
// Command / ACK structures
// ---------------------------------------------------------------------------

// Pi→MCU command payload: 6 bytes
typedef struct __attribute__((packed)) {
    uint8_t seq;     // sequence counter; echoed in ACK for confirmation
    uint8_t opcode;  // CmdOpcode_t
    float   value;   // numeric argument (0.0 for commands that don't need one)
} CommandPayload_t;

// MCU→Pi ACK payload: 2 bytes
typedef struct __attribute__((packed)) {
    uint8_t seq;     // echoed from the command
    uint8_t opcode;  // echoed from the command
} AckPayload_t;

// ---------------------------------------------------------------------------
// Frame overhead sizes (useful for buffer sizing)
// ---------------------------------------------------------------------------
#define FRAME_OVERHEAD   7u   // 2 sync + 1 type + 2 len + 2 CRC
#define FRAME_HEADER_LEN 5u   // bytes before payload
#define FRAME_CRC_LEN    2u

#define TELEMETRY_FRAME_SIZE  (FRAME_OVERHEAD + sizeof(TelemetryPayload_t))  // 271
#define COMMAND_FRAME_SIZE    (FRAME_OVERHEAD + sizeof(CommandPayload_t))     //  13
#define ACK_FRAME_SIZE        (FRAME_OVERHEAD + sizeof(AckPayload_t))         //   9

// ---------------------------------------------------------------------------
// CRC-16/CCITT-FALSE  (poly=0x1021, init=0xFFFF, no reflection)
// Covers: TYPE byte + LEN (2 bytes LE) + PAYLOAD
// ---------------------------------------------------------------------------

// Continue a CRC computation over additional data (useful for multi-segment input)
static inline uint16_t proto_crc16_continue(uint16_t crc, const uint8_t *data, uint16_t len) {
    for (uint16_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int j = 0; j < 8; j++) {
            crc = (crc & 0x8000u) ? (uint16_t)((crc << 1) ^ 0x1021u)
                                  : (uint16_t)(crc << 1);
        }
    }
    return crc;
}

// Full CRC over a contiguous buffer (initialises to 0xFFFF)
static inline uint16_t proto_crc16(const uint8_t *data, uint16_t len) {
    return proto_crc16_continue(0xFFFFu, data, len);
}

#endif /* PROTOCOL_H */
