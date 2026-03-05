// usbd_cdc_if.c — USB CDC receive handler + frame decoder for Pi→MCU commands
//
// Incoming bytes are fed one at a time into a state-machine frame decoder.
// Complete, CRC-validated frames are dispatched to execute_command().
// The TX-complete callback clears tx_ready so the main loop knows it is safe
// to start the next transfer.

#include "usbd_cdc_if.h"
#include "protocol.h"
#include <string.h>

// ---------------------------------------------------------------------------
// External references to machine state (defined in main.c)
// ---------------------------------------------------------------------------
extern volatile uint8_t  is_powered;
extern volatile uint8_t  steam_mode;
extern volatile char     control_mode;
extern volatile float    target_val;
extern volatile float    target_tw;
extern volatile float    target_tg;
extern volatile float    flow_limit;
extern volatile float    sim_w;          // tare resets weight accumulator

// Pending ACK — set here, consumed and transmitted by the main loop
extern volatile uint8_t  ack_pending;
extern volatile uint8_t  ack_seq;
extern volatile uint8_t  ack_opcode;

// ---------------------------------------------------------------------------
// Frame decoder state machine
// ---------------------------------------------------------------------------
typedef enum {
    DEC_SYNC0   = 0,
    DEC_SYNC1,
    DEC_TYPE,
    DEC_LEN0,
    DEC_LEN1,
    DEC_PAYLOAD,
    DEC_CRC0,
    DEC_CRC1,
} DecState_t;

// Maximum expected payload size: telemetry is MCU→Pi; largest Pi→MCU is
// PKT_COMMAND (6 bytes).  128 bytes gives plenty of headroom.
#define RX_PAYLOAD_MAX  128u

static DecState_t dec_state    = DEC_SYNC0;
static uint8_t    dec_type     = 0;
static uint16_t   dec_len      = 0;
static uint16_t   dec_pos      = 0;
static uint8_t    dec_buf[RX_PAYLOAD_MAX];
static uint8_t    dec_crc_lo   = 0;

// ---------------------------------------------------------------------------
// execute_command — act on a fully-decoded, CRC-validated command frame
// ---------------------------------------------------------------------------
static void execute_command(uint8_t ptype, const uint8_t *payload, uint16_t plen) {
    if (ptype == PKT_PING) {
        // Respond with an ACK (seq=0, opcode=0)
        ack_seq     = 0;
        ack_opcode  = 0;
        ack_pending = 1;
        return;
    }

    if (ptype != PKT_COMMAND || plen < sizeof(CommandPayload_t)) return;

    // Overlay CommandPayload_t onto payload bytes (struct is packed, so safe)
    const CommandPayload_t *cmd = (const CommandPayload_t *)payload;

    switch ((CmdOpcode_t)cmd->opcode) {
        case CMD_POWER_ON:
            is_powered  = 1;
            target_tw   = 93.0f;
            target_tg   = 93.0f;
            break;

        case CMD_POWER_OFF:
            is_powered  = 0;
            target_val  = 0.0f;
            flow_limit  = 0.0f;
            steam_mode  = 0;
            break;

        case CMD_TARE:
            sim_w = 0.0f;
            break;

        case CMD_STOP:
            target_val = 0.0f;
            flow_limit = 0.0f;
            break;

        case CMD_STEAM_ON:
            steam_mode = 1;
            break;

        case CMD_STEAM_OFF:
            steam_mode = 0;
            break;

        case CMD_SET_P:
            control_mode = 'P';
            target_val   = cmd->value;
            break;

        case CMD_SET_F:
            control_mode = 'F';
            target_val   = cmd->value;
            break;

        case CMD_SET_TW:
            target_tw = cmd->value;
            break;

        case CMD_SET_TG:
            target_tg = cmd->value;
            break;

        case CMD_SET_FL:
            flow_limit = cmd->value;
            break;

        default:
            // Unknown opcode — send ACK anyway so the host knows we got it
            break;
    }

    // Queue ACK — main loop will transmit when TX is free
    ack_seq     = cmd->seq;
    ack_opcode  = cmd->opcode;
    ack_pending = 1;
}

// ---------------------------------------------------------------------------
// process_rx_byte — feed one byte into the decoder state machine
// ---------------------------------------------------------------------------
static void process_rx_byte(uint8_t b) {
    switch (dec_state) {

        case DEC_SYNC0:
            if (b == PROTO_SYNC0) dec_state = DEC_SYNC1;
            break;

        case DEC_SYNC1:
            if      (b == PROTO_SYNC1) dec_state = DEC_TYPE;
            else if (b == PROTO_SYNC0) dec_state = DEC_SYNC1;  // 0xAA 0xAA ...
            else                       dec_state = DEC_SYNC0;
            break;

        case DEC_TYPE:
            dec_type  = b;
            dec_state = DEC_LEN0;
            break;

        case DEC_LEN0:
            dec_len   = b;                  // low byte
            dec_state = DEC_LEN1;
            break;

        case DEC_LEN1:
            dec_len  |= (uint16_t)b << 8;  // high byte
            dec_pos   = 0;
            if (dec_len == 0) {
                dec_state = DEC_CRC0;       // zero-length payload (e.g. PING)
            } else if (dec_len > RX_PAYLOAD_MAX) {
                dec_state = DEC_SYNC0;      // implausibly large — drop and resync
            } else {
                dec_state = DEC_PAYLOAD;
            }
            break;

        case DEC_PAYLOAD:
            dec_buf[dec_pos++] = b;
            if (dec_pos == dec_len) dec_state = DEC_CRC0;
            break;

        case DEC_CRC0:
            dec_crc_lo = b;
            dec_state  = DEC_CRC1;
            break;

        case DEC_CRC1: {
            uint16_t received = (uint16_t)dec_crc_lo | ((uint16_t)b << 8);

            // CRC input: TYPE (1B) + LEN (2B LE) + PAYLOAD (dec_len B)
            uint8_t crc_hdr[3] = {
                dec_type,
                (uint8_t)(dec_len & 0xFFu),
                (uint8_t)(dec_len >> 8),
            };
            uint16_t expected = proto_crc16(crc_hdr, 3u);
            expected = proto_crc16_continue(expected, dec_buf, dec_len);

            if (received == expected) {
                execute_command(dec_type, dec_buf, dec_len);
            }
            // Always return to sync hunt regardless of CRC result
            dec_state = DEC_SYNC0;
            break;
        }
    }
}

// ---------------------------------------------------------------------------
// CDC receive callback — called by USB middleware with each received packet
// ---------------------------------------------------------------------------
static int8_t CDC_Receive_HS(uint8_t *Buf, uint32_t *Len) {
    for (uint32_t i = 0; i < *Len; i++) {
        process_rx_byte(Buf[i]);
    }
    // Re-arm the CDC RX endpoint for the next packet
    USBD_CDC_SetRxBuffer(&hUsbDeviceHS, UserRxBufferHS);
    USBD_CDC_ReceivePacket(&hUsbDeviceHS);
    return USBD_OK;
}
