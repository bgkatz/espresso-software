extern MachineState_t machine_state;

static int8_t CDC_Receive_FS(uint8_t* Buf, uint32_t *Len) {
    // Ensure null termination for string processing
    // Note: Buf is usually a reusable buffer, check implementation
    Buf[*Len] = 0; 
    
    // 1. POWER COMMANDS
    if (strncmp((char*)Buf, "POWER_ON", 8) == 0) {
        machine_state.is_powered = 1;
        // Set defaults upon power up
        machine_state.target_temp_water = 93.0f;
        machine_state.target_temp_group = 93.0f;
    }
    else if (strncmp((char*)Buf, "POWER_OFF", 9) == 0) {
        machine_state.is_powered = 0;
        machine_state.target_val = 0.0f; // Cut pump
        machine_state.steam_mode = 0;
    }
    // 2. STOP COMMAND
    else if (strncmp((char*)Buf, "STOP", 4) == 0) {
        machine_state.target_val = 0.0f;
    }
    // 3. STEAM COMMANDS
    else if (strncmp((char*)Buf, "STEAM_ON", 8) == 0) {
        machine_state.steam_mode = 1;
    }
    else if (strncmp((char*)Buf, "STEAM_OFF", 9) == 0) {
        machine_state.steam_mode = 0;
    }
    // 4. VALUE COMMANDS (Parse float)
    else {
        // Find delimiter
        char* val_str = NULL;
        for (uint32_t i=0; i<*Len; i++) {
            if (Buf[i] == ':') {
                val_str = (char*)&Buf[i+1];
                break;
            }
        }

        if (val_str) {
            float val = strtof(val_str, NULL);
            
            if (strncmp((char*)Buf, "SET_P", 5) == 0) {
                machine_state.control_mode = 'P';
                machine_state.target_val = val;
            }
            else if (strncmp((char*)Buf, "SET_F", 5) == 0) {
                machine_state.control_mode = 'F';
                machine_state.target_val = val;
            }
            else if (strncmp((char*)Buf, "SET_TW", 6) == 0) {
                machine_state.target_temp_water = val;
            }
            else if (strncmp((char*)Buf, "SET_TG", 6) == 0) {
                machine_state.target_temp_group = val;
            }
        }
    }

    USBD_CDC_SetRxBuffer(&hUsbDeviceFS, UserRxBufferFS);
    USBD_CDC_ReceivePacket(&hUsbDeviceFS);
    return (USBD_OK);
}
