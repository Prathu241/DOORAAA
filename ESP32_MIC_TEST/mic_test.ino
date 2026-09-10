/*
 * DORA Microphone Test - ESP32-S3 + INMP441
 * 
 * Purpose: Validate I2S audio capture from INMP441 digital microphone
 * 
 * Wiring (ESP32-S3 DevKit):
 *   INMP441 -> ESP32-S3
 *   GND     -> GND
 *   3.3V    -> 3.3V
 *   WS      -> GPIO 5  (LRCK/Word Select)
 *   SCK     -> GPIO 4  (BCLK/Bit Clock)
 *   SD      -> GPIO 6  (DIN/Data In)
 * 
 * Serial output: 9600 baud
 * 
 * Expected behavior:
 * - Prints audio statistics every 500ms
 * - RMS, peak, min, max values change when speaking/clapping
 * - If silent: all values near 0
 */

#include <driver/i2s.h>
#include <esp_err.h>
#include <math.h>

// I2S configuration
#define I2S_PORT I2S_NUM_0
#define I2S_BCK_IO 4      // Bit clock
#define I2S_WS_IO 5       // Word select (LRCK)
#define I2S_DIN_IO 6      // Data in (SD)
#define I2S_SAMPLE_RATE 16000
#define I2S_SAMPLE_BITS I2S_BITS_PER_SAMPLE_32BIT
#define I2S_READ_LEN 1024  // Read 1024 bytes (512 samples at 32-bit)
#define STATS_INTERVAL_MS 500

// DMA buffer
uint8_t i2s_read_buf[I2S_READ_LEN];
int16_t pcm_data[I2S_READ_LEN / 4];  // 32-bit -> 16-bit conversion

unsigned long last_stats_time = 0;
uint32_t sample_count = 0;

void setup() {
    Serial.begin(9600);
    delay(1000);
    
    Serial.println("\n=====================================================");
    Serial.println("DORA MICROPHONE TEST - ESP32-S3 + INMP441");
    Serial.println("=====================================================");
    Serial.println("Initializing I2S audio capture...");
    
    // I2S configuration
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = I2S_SAMPLE_RATE,
        .bits_per_sample = I2S_SAMPLE_BITS,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,  // INMP441 is mono (left channel)
        .communication_format = (i2s_comm_format_t)(I2S_COMM_FORMAT_I2S),
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 8,
        .dma_buf_len = 256,
        .use_apll = false,
        .tx_desc_auto_clear = true,
        .fixed_mclk = 0
    };
    
    // I2S pin configuration
    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_BCK_IO,
        .ws_io_num = I2S_WS_IO,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_DIN_IO
    };
    
    // Install driver
    esp_err_t ret = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    if (ret != ESP_OK) {
        Serial.printf("FAIL: i2s_driver_install returned 0x%x\n", ret);
        while(1) delay(100);
    }
    
    // Set pins
    ret = i2s_set_pin(I2S_PORT, &pin_config);
    if (ret != ESP_OK) {
        Serial.printf("FAIL: i2s_set_pin returned 0x%x\n", ret);
        while(1) delay(100);
    }
    
    // Start I2S
    ret = i2s_start(I2S_PORT);
    if (ret != ESP_OK) {
        Serial.printf("FAIL: i2s_start returned 0x%x\n", ret);
        while(1) delay(100);
    }
    
    Serial.println("✓ I2S initialized successfully!");
    Serial.println("✓ Sample rate: 16 kHz");
    Serial.println("✓ Bit depth: 32-bit I2S (INMP441 24-bit packed)");
    Serial.println("✓ Converting to PCM16...");
    Serial.println("");
    Serial.println("Listening for audio... Speak or clap near microphone!");
    Serial.println("=====================================================\n");
    
    last_stats_time = millis();
}

void loop() {
    // Read I2S data
    size_t bytes_read = 0;
    esp_err_t ret = i2s_read(I2S_PORT, i2s_read_buf, I2S_READ_LEN, &bytes_read, portMAX_DELAY);
    
    if (ret != ESP_OK || bytes_read == 0) {
        Serial.println("ERROR: i2s_read failed");
        delay(10);
        return;
    }
    
    // Convert 32-bit I2S samples to 16-bit PCM
    // INMP441 sends 24-bit audio left-justified in 32-bit frame
    uint32_t num_samples = bytes_read / 4;  // 4 bytes per 32-bit sample
    
    for (uint32_t i = 0; i < num_samples; i++) {
        // Read 32-bit sample (little-endian)
        uint32_t sample32 = (i2s_read_buf[i*4+3] << 24) |
                            (i2s_read_buf[i*4+2] << 16) |
                            (i2s_read_buf[i*4+1] << 8)  |
                            (i2s_read_buf[i*4+0]);
        
        // Extract 24-bit audio (left-aligned in 32-bit)
        // Shift right 8 bits to center it, then convert to 16-bit
        int32_t sample24 = (int32_t)(sample32) >> 8;
        int16_t sample16 = (int16_t)(sample24 >> 8);  // Convert 24-bit to 16-bit
        
        pcm_data[i] = sample16;
    }
    
    sample_count += num_samples;
    
    // Calculate and print statistics every 500ms
    unsigned long now = millis();
    if (now - last_stats_time >= STATS_INTERVAL_MS) {
        calculate_and_print_stats(pcm_data, num_samples);
        last_stats_time = now;
    }
}

void calculate_and_print_stats(int16_t* samples, uint32_t num_samples) {
    // Calculate statistics
    float rms = 0.0;
    int16_t peak = 0;
    int16_t min_val = 32767;
    int16_t max_val = -32768;
    
    // Calculate RMS and min/max
    for (uint32_t i = 0; i < num_samples; i++) {
        int16_t sample = samples[i];
        
        // RMS calculation
        rms += (float)sample * sample;
        
        // Track peak (absolute max)
        if (abs(sample) > peak) {
            peak = abs(sample);
        }
        
        // Track min/max
        if (sample < min_val) min_val = sample;
        if (sample > max_val) max_val = sample;
    }
    
    rms = sqrt(rms / num_samples);
    
    // Print formatted output
    Serial.printf("MIC TEST\n");
    Serial.printf("samples=%ld\n", sample_count);
    Serial.printf("rms=%.1f\n", rms);
    Serial.printf("peak=%d\n", peak);
    Serial.printf("min=%d\n", min_val);
    Serial.printf("max=%d\n", max_val);
    Serial.println("---");
}
