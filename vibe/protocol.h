#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

#define SAMPLES_PER_PACKET 50  // 50ms buffer

// The data sent to the Pi (16 bytes per sample)
typedef struct {
    float pressure;   // 4 bytes
    float flow;       // 4 bytes
    float temp_water; // 4 bytes
    float temp_group; // 4 bytes
} Measurement_t;

// The packet format
typedef struct {
    uint8_t header[2]; // 'E','S'
    Measurement_t samples[SAMPLES_PER_PACKET];
} LogPacket_t;

// Global Machine State
typedef struct {
    // Safety
    uint8_t is_powered;      // 0 = Standby, 1 = Active
    
    // Control Targets
    float target_val;        // Value for Pressure OR Flow
    char control_mode;       // 'P' or 'F'
    float target_temp_water; // Boiler Setpoint
    float target_temp_group; // Grouphead Setpoint
    
    // Modes
    uint8_t steam_mode;      // 0 = Off, 1 = On (Force 140C)
} MachineState_t;

#endif
