#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>

// Optimized for High Speed USB (10ms updates)
#define SAMPLES_PER_PACKET 10 

// Data Structure (20 bytes per sample)
typedef struct {
    float pressure;   
    float flow;       
    float weight;     // Scale reading (grams)
    float temp_water; 
    float temp_group; 
} Measurement_t;

// Packet Structure
typedef struct {
    uint8_t header[2]; // 'E','S'
    Measurement_t samples[SAMPLES_PER_PACKET];
} LogPacket_t;

#endif