#include "main.h"
#include "usb_device.h"
#include "usbd_cdc_if.h"
#include "protocol.h"
#include <string.h>

// --- GLOBALS ---
// Aligned buffers for USB HS DMA
#if defined ( __GNUC__ )
__attribute__((aligned(32))) 
#endif
volatile LogPacket_t buffer_A;

#if defined ( __GNUC__ )
__attribute__((aligned(32))) 
#endif
volatile LogPacket_t buffer_B;

volatile LogPacket_t *fill_ptr = &buffer_A;
volatile LogPacket_t *send_ptr = &buffer_B;
volatile uint8_t packet_ready_to_send = 0;
volatile uint16_t sample_idx = 0;

// Hardware Handles
extern USBD_HandleTypeDef hUsbDeviceHS; 
extern TIM_HandleTypeDef htim2; 

// Machine State
volatile uint8_t is_powered = 0;
volatile float target_val = 0.0f;
volatile char control_mode = 'P'; // 'P' or 'F'
volatile float target_tw = 20.0f;
volatile float target_tg = 20.0f;
volatile uint8_t steam_mode = 0;

// Simulation State (Replace with real sensor vars)
volatile float sim_p = 0.0f;
volatile float sim_f = 0.0f;
volatile float sim_w = 0.0f; // Weight accumulator
volatile float sim_tw = 20.0f;
volatile float sim_tg = 20.0f;
volatile float sim_pump_duty = 0.0f;

// --- FAST LOOP (1kHz Interrupt) ---
void HAL_TIM_PeriodElapsedCallback(TIM_HandleTypeDef *htim) {
    if (htim->Instance == TIM2) {
        float dt = 0.001f;

        // 1. Physics (Thermals)
        // If unpowered, cool to 20C. If Steam Mode, heat to 140C.
        float setpoint_w = is_powered ? (steam_mode ? 140.0f : target_tw) : 20.0f;
        float setpoint_g = is_powered ? target_tg : 20.0f;
        
        // Simple heating/cooling lag simulation
        sim_tw += (sim_tw < setpoint_w) ? 2.0f * dt : -0.5f * dt;
        sim_tg += (sim_tg < setpoint_g) ? 0.5f * dt : -0.1f * dt;

        // 2. Physics (Hydraulics)
        if (is_powered) {
            // PID Loop Simulation
            float pv = (control_mode == 'P') ? sim_p : sim_f;
            float err = target_val - pv;
            
            sim_pump_duty += err * 5.0f * dt;
            // Clamp Pump
            if (sim_pump_duty < 0.0f) sim_pump_duty = 0.0f;
            if (sim_pump_duty > 12.0f) sim_pump_duty = 12.0f;
            
            // Apply Pump to Physics
            sim_p = sim_pump_duty;
            sim_f = (sim_p / 1.5f); // Resistance approximation
            if (sim_f < 0) sim_f = 0;
            
            // Weight Integration (Flow -> Weight)
            sim_w += sim_f * dt; 
        } else {
            // Power Cut: Depressurize immediately
            sim_p = 0.0f; 
            sim_f = 0.0f; 
            sim_pump_duty = 0.0f;
            // Note: We do NOT reset weight here. Weight persists until TARE.
        }

        // 3. Pack Data
        fill_ptr->samples[sample_idx].pressure = sim_p;
        fill_ptr->samples[sample_idx].flow = sim_f;
        fill_ptr->samples[sample_idx].weight = sim_w;
        fill_ptr->samples[sample_idx].temp_water = sim_tw;
        fill_ptr->samples[sample_idx].temp_group = sim_tg;
        
        sample_idx++;

        // 4. Swap Logic
        if (sample_idx >= SAMPLES_PER_PACKET) {
            if (!packet_ready_to_send) {
                // Swap Buffers
                LogPacket_t *temp = fill_ptr;
                fill_ptr = send_ptr;
                send_ptr = temp;
                
                // Add Header
                send_ptr->header[0] = 'E';
                send_ptr->header[1] = 'S';
                
                packet_ready_to_send = 1;
                sample_idx = 0;
            } else {
                // Buffer Overrun (Host too slow)
                sample_idx = 0; 
            }
        }
    }
}

// --- MAIN LOOP ---
int main(void) {
    HAL_Init();
    SystemClock_Config();
    MX_USB_DEVICE_Init(); // HS Init
    MX_TIM2_Init();
    
    HAL_TIM_Base_Start_IT(&htim2);

    while (1) {
        if (packet_ready_to_send) {
            // Send via High Speed Endpoint
            uint8_t status = CDC_Transmit_HS((uint8_t*)send_ptr, sizeof(LogPacket_t));
            
            if (status == USBD_OK) {
                packet_ready_to_send = 0;
            }
        }
    }
}