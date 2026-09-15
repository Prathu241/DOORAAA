/**
 * INMP441 MICROPHONE RAW TEST
 * Upload this, open Serial Monitor at 115200
 * This prints the RAW 32-bit values straight from I2S
 * No processing - just raw data to confirm mic is alive
 */

#include <driver/i2s.h>

#define I2S_PORT    I2S_NUM_0
#define PIN_SCK     4
#define PIN_WS      5
#define PIN_SD      6   // ← try changing to 3 if still -1

// If still getting -1, try these combinations:
// SCK=36, WS=35, SD=37  (alternative pinout)
// SCK=14, WS=12, SD=13  (another option)

int32_t raw_buf[64];

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== INMP441 RAW TEST ===");
  Serial.println("If all values are 0 = wiring issue");
  Serial.println("If values change    = mic is working");
  Serial.println();

  i2s_config_t cfg = {
    .mode                 = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate          = 16000,
    .bits_per_sample      = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format       = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags     = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count        = 4,
    .dma_buf_len          = 64,
    .use_apll             = false,
  };

  i2s_pin_config_t pins = {
    .bck_io_num   = PIN_SCK,
    .ws_io_num    = PIN_WS,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num  = PIN_SD,
  };

  esp_err_t r1 = i2s_driver_install(I2S_PORT, &cfg, 0, NULL);
  esp_err_t r2 = i2s_set_pin(I2S_PORT, &pins);

  Serial.printf("I2S init: driver=%d pins=%d\n", r1, r2);
  Serial.println(r1 == ESP_OK && r2 == ESP_OK ? "I2S OK" : "I2S FAILED");
  Serial.println();
}

void loop() {
  size_t bytes_read = 0;
  i2s_read(I2S_PORT, raw_buf, sizeof(raw_buf), &bytes_read, portMAX_DELAY);

  int samples = bytes_read / 4;

  // Print first 8 raw values
  Serial.print("RAW: ");
  for (int i = 0; i < 8 && i < samples; i++) {
    Serial.printf("%10ld ", (long)raw_buf[i]);
  }

  // Check if all zero
  bool all_zero = true;
  int32_t peak = 0;
  for (int i = 0; i < samples; i++) {
    if (raw_buf[i] != 0) all_zero = false;
    int32_t a = abs(raw_buf[i]);
    if (a > peak) peak = a;
  }

  if (all_zero) {
    Serial.println("  << ALL ZERO - CHECK WIRING");
  } else {
    Serial.printf("  peak=%ld  OK\n", (long)peak);
  }

  delay(200);
}
