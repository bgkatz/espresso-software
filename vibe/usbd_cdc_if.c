// External references to state variables
extern volatile uint8_t is_powered;
extern volatile uint8_t steam_mode;
extern volatile char control_mode;
extern volatile float target_val;
extern volatile float target_tw;
extern volatile float target_tg;
extern volatile float sim_w;

static int8_t CDC_Receive_HS(uint8_t* Buf, uint32_t *Len) {
    // Null terminate for safety
    Buf[*Len] = 0;
    char* cmd = (char*)Buf;

    // 1. GLOBAL COMMANDS
    if (strncmp(cmd, "POWER_ON", 8) == 0) {
        is_powered = 1;
        target_tw = 93.0f; target_tg = 93.0f;
    }
    else if (strncmp(cmd, "POWER_OFF", 9) == 0) {
        is_powered = 0;
        target_val = 0.0f; steam_mode = 0;
    }
    else if (strncmp(cmd, "STOP", 4) == 0) {
        target_val = 0.0f;
    }
    else if (strncmp(cmd, "TARE", 4) == 0) {
        sim_w = 0.0f; // Reset Weight
    }
    else if (strncmp(cmd, "STEAM_ON", 8) == 0) steam_mode = 1;
    else if (strncmp(cmd, "STEAM_OFF", 9) == 0) steam_mode = 0;

    // 2. VALUE COMMANDS
    else {
        // Parse "CMD:VALUE"
        char* val_ptr = strchr(cmd, ':');
        if (val_ptr) {
            float val = strtof(val_ptr + 1, NULL);
            
            if (strncmp(cmd, "SET_P", 5) == 0) {
                control_mode = 'P'; target_val = val;
            }
            else if (strncmp(cmd, "SET_F", 5) == 0) {
                control_mode = 'F'; target_val = val;
            }
            else if (strncmp(cmd, "SET_TW", 6) == 0) target_tw = val;
            else if (strncmp(cmd, "SET_TG", 6) == 0) target_tg = val;
        }
    }

    USBD_CDC_SetRxBuffer(&hUsbDeviceHS, UserRxBufferHS);
    USBD_CDC_ReceivePacket(&hUsbDeviceHS);
    return (USBD_OK);
}