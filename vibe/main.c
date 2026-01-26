#include "main.h"
#include "usb_device.h"
#include "usbd_cdc_if.h"
#include "protocol.h"
#include <string.h>
#include <math.h> // For simulation math

// --- GLOBALS ---
volatile LogPacket_t buffer_A;
volatile LogPacket_t buffer_B;
volatile LogPacket_t *fill_ptr = &buffer_A;
volatile LogPacket_t *send_ptr = &buffer_B;
volatile uint8_t packet_ready_to_send = 0;
volatile uint16_t sample_idx = 0;

// Default State: OFF
volatile MachineState_t machine_state = {
    .is_powered = 0,
    .target_val = 0.0f,
    .control_mode = 'P',
    .target_temp_water = 20.0f,
    .target_temp_group = 20.0f,
    .steam_mode = 0
};

// Simulation State (Remove these when using real sensors)
float sim_p = 0.0f;
float sim_f = 0.0f;
float sim_tw = 20.0f;
float sim_tg = 20.0f;
float sim_pump_duty = 0.0f;

// --- 1. THE FAST LOOP (1kHz Interrupt) ---
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {
    if (htim->Instance == TIM2) {
        
        // ============================
        // 1. INPUT STAGE (SENSORS)
        // ============================
        // REAL HARDWARE:
        // float p_act = Read_Pressure_Sensor();
        // float tw_act = Read_Thermistor_Boiler();
        
        // SIMULATION:
        float dt = 0.001f; // 1ms
        float current_target_tw = machine_state.target_temp_water;
        
        // Safety: If unpowered, cool down.
        if (!machine_state.is_powered) {
            current_target_tw = 20.0f; 
        } else if (machine_state.steam_mode) {
            current_target_tw = 140.0f; // Override for steam
        }

        // Sim Heater Physics
        if (sim_tw < current_target_tw) sim_tw += 2.0f * dt;
        else sim_tw -= 0.5f * dt;
        
        float current_target_tg = machine_state.is_powered ? machine_state.target_temp_group : 20.0f;
        if (sim_tg < current_target_tg) sim_tg += 0.5f * dt;
        else sim_tg -= 0.1f * dt;

        // ============================
        // 2. CONTROL STAGE (PID)
        // ============================
        if (machine_state.is_powered) {
            // Determine Process Variable (PV)
            float pv = (machine_state.control_mode == 'P') ? sim_p : sim_f;
            float error = machine_state.target_val - pv;
            
            // Simple P-Controller for simulation
            sim_pump_duty += error * 5.0f * dt;
            if (sim_pump_duty > 12.0f) sim_pump_duty = 12.0f;
            if (sim_pump_duty < 0.0f) sim_pump_duty = 0.0f;
        } else {
            // Power cut -> Pumps off immediately
            sim_pump_duty = 0.0f;
        }

        // Apply Physics (Pump -> Pressure -> Flow)
        sim_p = sim_pump_duty;
        // Flow resistance model
        sim_f = (sim_p / 1.5f); // 1.5 = resistance
        if (sim_f < 0) sim_f = 0;

        // ============================
        // 3. LOGGING STAGE
        // ============================
        fill_ptr->samples[sample_idx].pressure = sim_p;
        fill_ptr->samples[sample_idx].flow = sim_f;
        fill_ptr->samples[sample_idx].temp_water = sim_tw;
        fill_ptr->samples[sample_idx].temp_group = sim_tg;
        
        sample_idx++;

        // Buffer Swap Logic
        if (sample_idx >= SAMPLES_PER_PACKET) {
            if (packet_ready_to_send == 0) {
                LogPacket_t *temp = fill_ptr;
                fill_ptr = send_ptr;
                send_ptr = temp;
                
                send_ptr->header[0] = 'E';
                send_ptr->header[1] = 'S';
                packet_ready_to_send = 1;
                sample_idx = 0;
            } else {
                sample_idx = 0; // Overrun, drop frame
            }
        }
    }
}

// --- MAIN LOOP ---
int main(void) {
    HAL_Init();
    SystemClock_Config();
    MX_USB_DEVICE_Init();
    MX_TIM2_Init();
    HAL_TIM_Base_Start_IT(&htim2);

    while (1) {
        if (packet_ready_to_send) {
            uint8_t status = CDC_Transmit_FS((uint8_t*)send_ptr, sizeof(LogPacket_t));
            if (status == USBD_OK) {
                packet_ready_to_send = 0;
            }
        }
    }
}
