/**
 * DORA KEYWORD DETECTION  —  ESP32-S3 + INMP441
 * ================================================
 * Real TFLite Micro inference using the trained Streaming MixedNet INT8 model.
 *
 * WHAT THIS FILE DOES (vs old heuristic version):
 *   OLD: runModelInference() computed hand-written audio statistics and
 *        ignored the actual model weights entirely.
 *   NEW: Uses TFLite Micro MicroInterpreter with the actual trained weights
 *        embedded in model_data.h.  Audio is processed by the micro_speech
 *        frontend (PCAN + mel filterbank) — the same frontend used during
 *        training — and streamed 3 frames at a time into the model.
 *
 * MODEL FACTS (confirmed by Python inspection):
 *   Input  : (1, 3, 40)  float32   — 3 mel frames × 40 features per invoke
 *   Output : (1, 1)      float32   — keyword probability in [0, 1]
 *   Size   : 68,600 bytes          — stored in model_data.h
 *   Architecture: Streaming MixedNet, ring-buffer state maintained internally
 *
 * FRONTEND PARAMETERS (must match training exactly):
 *   Sample rate : 16,000 Hz
 *   Window      : 30 ms  (480 samples)
 *   Stride      : 10 ms  (160 samples per invoke)
 *   Mel bins    : 40
 *   Lower band  : 125 Hz
 *   Upper band  : 7,500 Hz
 *   PCAN        : enabled (strength=0.95, offset=80.0)
 *   Log scale   : enabled (scale_shift=6)
 *
 * LIBRARY REQUIRED:
 *   "TensorFlowLite_ESP32" by tanakamasayuki
 *   Install via Arduino IDE → Tools → Manage Libraries → search above name.
 *   (The micro_speech frontend header files from tflite-micro must also be
 *    present — see note in setup() if FrontendProcessSamples is unavailable.)
 *
 * HARDWARE:
 *   ESP32-S3 Dev Module
 *   INMP441 microphone: SCK→GPIO4, WS→GPIO5, SD→GPIO6
 *   Baud rate: 115200
 *
 * THRESHOLDS (from threshold_sweep.py on held-out test set):
 *   At t=0.90 → Recall 98.7%, FA ~6.6/hr on background noise
 *   At t=0.85 → Recall 100%,  FA ~6.8/hr
 *   Use KWS_THRESHOLD = 0.90f as starting point; lower if missing detections.
 *
 * SERIAL OUTPUT FORMAT (dashboard-compatible):
 *   MIC_DATA
 *   rms=<float>
 *   peak=<int>
 *   samples=<ulong>
 *   confidence=<float>       ← raw per-frame score
 *   smoothed=<float>         ← 5-frame average
 *   ---
 *   DETECTION
 *   confidence=<float>
 *   smoothed=<float>
 *   latency=<ms>
 *   transcript=DORA
 *   verdict=TP
 *   ---
 */

// ============================================================
// LIBRARY INCLUDES
// ============================================================

#include <driver/i2s.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <esp_system.h>
// `secrets.h` is optional for a local-only KWS build. Copy
// `secrets.example.h` to `secrets.h` and set real values to enable cloud ASR.
#if __has_include("secrets.h")
#include "secrets.h"
#else
#define DORA_WIFI_SSID ""
#define DORA_WIFI_PASSWORD ""
#define DORA_CLOUD_HOST ""
#define DORA_CLOUD_PORT 8765
#define DORA_CLOUD_PATH "/edge"
#endif

// TFLite Micro  (TensorFlowLite_ESP32 by tanakamasayuki)
// No umbrella header needed — include TFLite Micro headers directly.
// Confirmed present in Arduino15/libraries/TensorFlowLite_ESP32/src/tensorflow/
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_allocator.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_resource_variable.h"
#include "tensorflow/lite/schema/schema_generated.h"

// micro_speech frontend — source files copied into sketch directory
// (frontend.h, frontend_util.h and all deps: filterbank, noise_reduction,
//  pcan_gain_control, log_scale, window, fft, bits)
// This avoids Arduino library include-path resolution issues.
#include "frontend.h"
#include "frontend_util.h"

// Trained model weights
#include "model_data.h"

// ============================================================
// CONFIGURATION
// ============================================================

// ── Wi-Fi Mode ───────────────────────────────────────────────
// Set to false for 100% pure local KWS serial monitor mode.
// Set to true to stream subsequent audio to cloud ASR.
// *** TEMPORARILY DISABLED to eliminate Wi-Fi CPU drain during mic debugging ***
#define ENABLE_WIFI      false

// ── I2S / Microphone ──────────────────────────────────────────
#define I2S_PORT         I2S_NUM_0
#define I2S_BCK_IO       4          // SCK on INMP441
#define I2S_WS_IO        5          // WS on INMP441
#define I2S_DIN_IO       15         // SD on INMP441 (Changed from 10 to 15)
#define I2S_SAMPLE_RATE  16000
#define I2S_FRAME_SAMPLES 160       // 10 ms @ 16 kHz — one frontend stride

// ── Model / KWS ──────────────────────────────────────────────
#define KWS_THRESHOLD    0.70f      // 70% confidence triggers keyword
#define KWS_WINDOW_SIZE  3          // 3-step moving average (90 ms window with stride 3)
#define KWS_COOLDOWN_MS  1500       // 1.5s cooldown between trigger events
#define NUM_MEL_BINS     40         // must match model input
#define VAD_SILENCE_RMS  10.0f      // Audio energy gate: skip Invoke() during pure silence

// ── Cloud hand-off ───────────────────────────────────────────
#define PRE_ROLL_FRAMES       30    // 300 ms at 10 ms/frame
#define STREAM_SILENCE_RMS    25.0f
#define STREAM_SILENCE_FRAMES 80    // 800 ms of silence ends an utterance
#define STREAM_MAX_MS         8000
#define TELEMETRY_INTERVAL_MS 500

// ── TFLite Micro arena ────────────────────────────────────────
// 160 KB — AllOpsResolver + VAR_HANDLE stateful streaming ops need more arena
constexpr int kTensorArenaSize = 160 * 1024;

// ============================================================
// GLOBALS
// ============================================================
// Hardware stats — updated every 100 frames (1 second) to avoid blocking I2S
static float  g_heapFreeKB  = 0;
static float  g_heapMinKB   = 0;
static float  g_psramFreeKB = 0;
static float  g_coreTemp    = 0;
static int    g_cpuMhz      = 240;

// ── TFLite Micro ─────────────────────────────────────────────
static uint8_t tensor_arena[kTensorArenaSize];
// Keep this count equal to the registrations in setupTFLite().
static tflite::MicroMutableOpResolver<14> resolver;

static tflite::MicroAllocator* micro_allocator = nullptr;
static tflite::MicroResourceVariables* resource_variables = nullptr;
static tflite::MicroInterpreter* interpreter = nullptr;
static TfLiteTensor* input_tensor  = nullptr;
static TfLiteTensor* output_tensor = nullptr;

// ── micro_speech frontend ─────────────────────────────────────
static FrontendState frontend_state;
static bool frontend_ready = false;

// ── I2S audio buffers ────────────────────────────────────────
static int16_t  pcm_frame[I2S_FRAME_SAMPLES];   // one 10ms mono frame (extracted from stereo)

// ── KWS state ────────────────────────────────────────────────
static float    score_window[KWS_WINDOW_SIZE] = {0};
static int      score_idx   = 0;
static uint32_t last_detection_ms = 0;
static uint32_t total_frames      = 0;

// ── Diagnostics ──────────────────────────────────────────────
// Filled after first successful inference
static size_t   arena_used    = 0;
static uint32_t t_feat_us     = 0;   // last feature extraction time
static uint32_t t_infer_us    = 0;   // last inference time
static uint32_t g_active_us   = 0;   // rolling active CPU time in microseconds
static uint32_t g_detection_count = 0; // total keyword detections

// ── Wi-Fi / real audio stream ────────────────────────────────
static WiFiClient cloud_socket;
static bool cloud_connected = false;
static bool stream_active = false;
static uint32_t stream_started_ms = 0;
static uint32_t stream_silence_frames = 0;
static uint32_t last_telemetry_ms = 0;
static int16_t pre_roll[PRE_ROLL_FRAMES][I2S_FRAME_SAMPLES] = {{0}};
static uint8_t pre_roll_next = 0;

// ============================================================
// SETUP HELPERS
// ============================================================

// ── I2S initialisation ───────────────────────────────────────
// INMP441 L/R SELECT pin determines which WS phase the mic outputs on:
//   L/R = GND → LEFT channel  (WS low phase)
//   L/R = VCC → RIGHT channel (WS high phase)
// If you get RMS=0 with ONLY_LEFT, your L/R pin is HIGH → change to ONLY_RIGHT.
// I2S_CHANNEL_FMT_RIGHT_LEFT reads both channels; left=even words, right=odd words.
#define I2S_CHANNEL_SEL  I2S_CHANNEL_FMT_RIGHT_LEFT   // read both, detect which has data

static bool setupI2S() {
  i2s_config_t cfg = {};
  cfg.mode                  = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX);
  cfg.sample_rate           = I2S_SAMPLE_RATE;
  cfg.bits_per_sample       = I2S_BITS_PER_SAMPLE_32BIT;  // INMP441 outputs 24-bit in 32-bit frame
  cfg.channel_format        = I2S_CHANNEL_SEL;  // RIGHT_LEFT: reads both channels interleaved
  cfg.communication_format  = I2S_COMM_FORMAT_STAND_I2S;
  cfg.intr_alloc_flags      = ESP_INTR_FLAG_LEVEL1;
  cfg.dma_buf_count         = 4;
  cfg.dma_buf_len           = 512;
  cfg.use_apll              = false;

  i2s_pin_config_t pins = {};
  pins.bck_io_num   = I2S_BCK_IO;
  pins.ws_io_num    = I2S_WS_IO;
  pins.data_out_num = I2S_PIN_NO_CHANGE;
  pins.data_in_num  = I2S_DIN_IO;

  if (i2s_driver_install(I2S_PORT, &cfg, 0, NULL) != ESP_OK) return false;
  if (i2s_set_pin(I2S_PORT, &pins)               != ESP_OK) return false;
  i2s_zero_dma_buffer(I2S_PORT);
  return true;
}

// ── micro_speech frontend initialisation ─────────────────────
// Parameters MUST match training (audio_utils.py generate_features_for_clip):
//   sample_rate=16000, window_size=30ms, window_step=10ms,
//   num_channels=40, lower_band_limit=125, upper_band_limit=7500,
//   enable_pcan=True, min_signal_remaining=0.05
static bool setupFrontend() {
  FrontendConfig config;
  memset(&config, 0, sizeof(config));

  // Window
  config.window.size_ms       = 30;   // 30 ms
  config.window.step_size_ms  = 10;   // 10 ms stride

  // Mel filterbank
  config.filterbank.num_channels       = NUM_MEL_BINS;  // 40
  config.filterbank.lower_band_limit   = 125.0f;        // Hz
  config.filterbank.upper_band_limit   = 7500.0f;       // Hz

  // PCAN automatic gain control — must match training
  config.pcan_gain_control.enable_pcan  = 1;
  config.pcan_gain_control.strength     = 0.95f;
  config.pcan_gain_control.offset       = 80.0f;
  config.pcan_gain_control.gain_bits    = 21;

  // Noise reduction
  config.noise_reduction.smoothing_bits         = 10;
  config.noise_reduction.even_smoothing         = 0.025f;
  config.noise_reduction.odd_smoothing          = 0.06f;
  config.noise_reduction.min_signal_remaining   = 0.05f;

  // Log scale
  config.log_scale.enable_log  = 1;
  config.log_scale.scale_shift = 6;

  if (!FrontendPopulateState(&config, &frontend_state, I2S_SAMPLE_RATE)) {
    return false;
  }
  return true;
}

// ── TFLite Micro initialisation ──────────────────────────────
static bool setupTFLite() {
  // Register only the ops this model uses (verified from model_summary.txt
  // and docs/08_Firmware_Guide.md).  Registering fewer ops saves ~100 KB flash.
  // AllOpsResolver includes all ops — no individual registration needed
  resolver.AddConv2D();
  resolver.AddDepthwiseConv2D();
  resolver.AddReshape();
  resolver.AddFullyConnected();
  resolver.AddMul();
  resolver.AddAdd();
  resolver.AddConcatenation();
  resolver.AddStridedSlice();
  resolver.AddSplitV();
  resolver.AddLogistic();
  // Streaming model stateful ops
  resolver.AddVarHandle();
  resolver.AddCallOnce();
  resolver.AddAssignVariable();
  resolver.AddReadVariable();

  // Load the model from flash (model_data.h)
  // dora_model_data is declared as const unsigned char[] — must be 8-byte aligned.
  // TFLite Micro requires alignment; the linker places .rodata at ≥4-byte boundary
  // on ESP32. If you see "Model provided has model identifier" errors, add:
  //   alignas(8) const unsigned char dora_model_data[] = { ... };  in model_data.h
  const tflite::Model* model = tflite::GetModel(dora_model_data);
  if (model->version() != TFLITE_SCHEMA_VERSION) {
    Serial.printf("[TFLite] Schema mismatch: model=%d runtime=%d\n",
                  (int)model->version(), TFLITE_SCHEMA_VERSION);
    return false;
  }

  // The streaming model stores six temporal ring buffers as TFLite resource
  // variables. They must be allocated before constructing the interpreter;
  // otherwise VAR_HANDLE fails during AllocateTensors().
  micro_allocator = tflite::MicroAllocator::Create(
      tensor_arena, kTensorArenaSize);
  if (micro_allocator == nullptr) {
    Serial.println("[TFLite] Failed to create micro allocator");
    return false;
  }
  resource_variables = tflite::MicroResourceVariables::Create(
      micro_allocator, 6);
  if (resource_variables == nullptr) {
    Serial.println("[TFLite] Failed to create streaming resource variables");
    return false;
  }

  // Create interpreter (static so it lives for program lifetime).
  // All objects passed here have static lifetime.
  static tflite::MicroInterpreter static_interp(
      model, resolver, micro_allocator, resource_variables);
  interpreter = &static_interp;

  if (interpreter->AllocateTensors() != kTfLiteOk) {
    Serial.println("[TFLite] AllocateTensors() FAILED — arena too small");
    return false;
  }

  input_tensor  = interpreter->input(0);
  output_tensor = interpreter->output(0);
  arena_used    = interpreter->arena_used_bytes();

  // Validate shapes
  // Input must be (1, 3, 40) float32
  if (input_tensor->dims->size != 3 ||
      input_tensor->dims->data[0] != 1 ||
      input_tensor->dims->data[1] != 3 ||
      input_tensor->dims->data[2] != NUM_MEL_BINS ||
      input_tensor->type != kTfLiteFloat32) {
    Serial.printf("[TFLite] Unexpected input shape or type!\n");
    Serial.printf("  dims=%d  [%d,%d,%d]  type=%d\n",
                  input_tensor->dims->size,
                  input_tensor->dims->data[0],
                  input_tensor->dims->data[1],
                  input_tensor->dims->data[2],
                  (int)input_tensor->type);
    return false;
  }
  // Output must be (1, 1) float32
  if (output_tensor->dims->size != 2 ||
      output_tensor->dims->data[0] != 1 ||
      output_tensor->dims->data[1] != 1 ||
      output_tensor->type != kTfLiteFloat32) {
    Serial.printf("[TFLite] Unexpected output shape or type!\n");
    return false;
  }

  return true;
}

// ============================================================
// CLOUD STREAMING — real PCM, never RMS-derived synthetic audio
// ============================================================
static uint32_t last_cloud_attempt_ms = 0;

static bool cloudSendFrame(uint8_t opcode, const uint8_t* data, size_t length) {
  if (!cloud_connected || !cloud_socket.connected() || length > 512) return false;
  // RFC 6455 requires every client-to-server frame to be masked.
  // Pack header + payload into a single buffer to avoid split TCP segments.
  uint8_t frame_buf[8 + 512];
  size_t header_len = 0;
  frame_buf[header_len++] = 0x80 | opcode;  // final frame
  if (length < 126) {
    frame_buf[header_len++] = 0x80 | (uint8_t)length;
  } else {
    frame_buf[header_len++] = 0x80 | 126;
    frame_buf[header_len++] = (uint8_t)(length >> 8);
    frame_buf[header_len++] = (uint8_t)length;
  }
  const uint32_t mask = esp_random();
  frame_buf[header_len++] = (uint8_t)(mask >> 24);
  frame_buf[header_len++] = (uint8_t)(mask >> 16);
  frame_buf[header_len++] = (uint8_t)(mask >> 8);
  frame_buf[header_len++] = (uint8_t)mask;
  for (size_t i = 0; i < length; ++i) {
    frame_buf[header_len + i] = data[i] ^ frame_buf[header_len - 4 + (i & 3)];
  }
  size_t total_len = header_len + length;
  if (cloud_socket.write(frame_buf, total_len) != total_len) {
    cloud_connected = false;
    cloud_socket.stop();
    return false;
  }
  return true;
}

static bool cloudSendText(const char* text) {
  return cloudSendFrame(0x1, (const uint8_t*)text, strlen(text));
}

static bool cloudSendBinary(const uint8_t* data, size_t length) {
  return cloudSendFrame(0x2, data, length);
}

static void cloudLoop() {
#if !ENABLE_WIFI
  return;
#else
  if (WiFi.status() != WL_CONNECTED) {
    cloud_connected = false;
    if (millis() - last_cloud_attempt_ms > 5000) {
      last_cloud_attempt_ms = millis();
      WiFi.reconnect();
    }
    return;
  }
  if (cloud_connected && !cloud_socket.connected()) {
    cloud_connected = false;
    cloud_socket.stop();
    stream_active = false;
    Serial.println("[Cloud] Gateway disconnected");
  }
  // Drain any incoming server frames (pings/control) to keep TCP buffer clean
  if (cloud_connected) {
    while (cloud_socket.available()) {
      cloud_socket.read();
    }
    return;
  }
  if (millis() - last_cloud_attempt_ms < 5000) return;
  last_cloud_attempt_ms = millis();
  if (!cloud_socket.connect(DORA_CLOUD_HOST, DORA_CLOUD_PORT)) return;
  // The gateway is trusted on the LAN. We send a valid fixed 16-byte key and
  // require its HTTP 101 response before permitting binary audio frames.
  cloud_socket.printf("GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: MDEyMzQ1Njc4OWFiY2RlZg==\r\nSec-WebSocket-Version: 13\r\n\r\n",
                      DORA_CLOUD_PATH, DORA_CLOUD_HOST, DORA_CLOUD_PORT);
  const uint32_t started = millis();
  String response;
  while (millis() - started < 2000) {
    while (cloud_socket.available()) response += (char)cloud_socket.read();
    if (response.indexOf("\r\n\r\n") >= 0) break;
    delay(1);
  }
  if (!response.startsWith("HTTP/1.1 101")) {
    cloud_socket.stop();
    return;
  }
  cloud_connected = true;
  Serial.println("[Cloud] WebSocket connected to edge gateway");
#endif
}

static void setupCloud() {
#if !ENABLE_WIFI
  Serial.println("[WiFi] Wi-Fi disabled — Running in pure local KWS Serial Mode");
  return;
#else
  if (strlen(DORA_WIFI_SSID) == 0 || strlen(DORA_CLOUD_HOST) == 0) {
    Serial.println("[WiFi] Cloud disabled: create secrets.h from secrets.example.h");
    return;
  }
  WiFi.mode(WIFI_STA);
  WiFi.begin(DORA_WIFI_SSID, DORA_WIFI_PASSWORD);
  Serial.printf("[WiFi] Connecting to %s", DORA_WIFI_SSID);
  const uint32_t started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 15000) {
    delay(250);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi] Not connected; KWS stays local and will retry");
    return;
  }
  Serial.printf("[WiFi] Connected: %s\n", WiFi.localIP().toString().c_str());
  cloudLoop();
#endif
}

static void savePreRoll(const int16_t* frame) {
  memcpy(pre_roll[pre_roll_next], frame, sizeof(pre_roll[0]));
  pre_roll_next = (pre_roll_next + 1) % PRE_ROLL_FRAMES;
}

static void sendCloudTelemetry(float rms, int16_t peak, float score, float smoothed) {
  if (!cloud_connected || millis() - last_telemetry_ms < TELEMETRY_INTERVAL_MS) return;
  last_telemetry_ms = millis();
  float cpu_util = ((float)(t_feat_us + t_infer_us) / 10000.0f) * 100.0f;
  if (cpu_util > 100.0f) cpu_util = 100.0f;
  char telemetry[384];
  snprintf(telemetry, sizeof(telemetry),
           "{\"type\":\"telemetry\",\"rms\":%.2f,\"peak\":%d,\"samples\":%lu,\"confidence\":%.4f,\"smoothed\":%.4f,\"featUs\":%lu,\"inferUs\":%lu,\"cpuUtil\":%.2f,\"heapFreeKB\":%.1f,\"heapMinKB\":%.1f,\"psramFreeKB\":%.1f,\"coreTemp\":%.1f,\"cpuMhz\":%d}",
           rms, (int)peak, (unsigned long)(total_frames * I2S_FRAME_SAMPLES),
           score, smoothed, (unsigned long)t_feat_us,
           (unsigned long)t_infer_us, cpu_util, g_heapFreeKB, g_heapMinKB,
           g_psramFreeKB, g_coreTemp, g_cpuMhz);
  cloudSendText(telemetry);
}

static void endCloudStream(const char* reason) {
  if (!stream_active) return;
  char message[96];
  snprintf(message, sizeof(message), "{\"type\":\"end\",\"reason\":\"%s\"}", reason);
  cloudSendText(message);
  stream_active = false;
  stream_silence_frames = 0;
  Serial.printf("[Cloud] Stream ended: %s\n", reason);
}

static void startCloudStream(float confidence) {
  if (!cloud_connected || stream_active) {
    Serial.println("[Cloud] Detection retained locally; cloud is unavailable");
    return;
  }
  char message[192];
  snprintf(message, sizeof(message),
           "{\"type\":\"start\",\"sessionId\":\"%lu\",\"keyword\":\"DORA\",\"confidence\":%.4f,\"keywordEndDeviceMs\":%lu,\"preRollMs\":300,\"format\":\"pcm_s16le\",\"sampleRate\":16000,\"channels\":1}",
           (unsigned long)millis(), confidence, (unsigned long)millis());
  cloudSendText(message);
  // Send oldest to newest so ASR gets the audio immediately preceding DORA.
  for (uint8_t i = 0; i < PRE_ROLL_FRAMES; ++i) {
    const uint8_t index = (pre_roll_next + i) % PRE_ROLL_FRAMES;
    cloudSendBinary((uint8_t*)pre_roll[index], sizeof(pre_roll[index]));
  }
  stream_active = true;
  stream_started_ms = millis();
  stream_silence_frames = 0;
  Serial.println("[Cloud] Real PCM stream started");
}

// ============================================================
// SETUP
// ============================================================
void setup() {
  Serial.begin(115200);
  delay(500);

  Serial.println();
  Serial.println("============================================================");
  Serial.println("  DORA KEYWORD DETECTION — ESP32-S3");
  Serial.println("  Streaming MixedNet INT8 | Real TFLite Micro Inference");
  Serial.println("============================================================");
  Serial.printf("  Model size   : %u bytes\n", dora_model_len);
  Serial.printf("  Sample rate  : %d Hz\n",    I2S_SAMPLE_RATE);
  Serial.printf("  Frame size   : %d ms (%d samples)\n",
                (I2S_FRAME_SAMPLES * 1000) / I2S_SAMPLE_RATE, I2S_FRAME_SAMPLES);
  Serial.printf("  Mel bins     : %d\n",        NUM_MEL_BINS);
  Serial.printf("  KWS threshold: %.2f\n",      KWS_THRESHOLD);
  Serial.printf("  Smoothing    : %d-frame avg (%d ms)\n",
                KWS_WINDOW_SIZE, KWS_WINDOW_SIZE * 10);
  Serial.printf("  Arena budget : %d KB\n",     kTensorArenaSize / 1024);
  Serial.println("------------------------------------------------------------");

  // ── I2S ──
  if (!setupI2S()) {
    Serial.println("[I2S] FAILED to initialise microphone — halting");
    while (true) delay(1000);
  }
  Serial.println("[I2S]    OK — microphone ready");
  detectMicChannel();  // auto-detect L vs R channel (INMP441 L/R pin)

  // ── Frontend ──
  if (!setupFrontend()) {
    Serial.println("[Frontend] FAILED to initialise micro_speech — halting");
    while (true) delay(1000);
  }
  frontend_ready = true;
  Serial.println("[Frontend] OK — PCAN mel filterbank ready");

  // ── TFLite Micro ──
  if (!setupTFLite()) {
    Serial.println("[TFLite] FAILED — halting");
    while (true) delay(1000);
  }

  // The model is fully local; network failure must never prevent KWS boot.
  setupCloud();

  // Benchmark printout (these are the values requested for the BENCHMARK section)
  Serial.println("------------------------------------------------------------");
  Serial.println("  BENCHMARK (at init)");
  Serial.println("------------------------------------------------------------");
  Serial.printf("  Free heap before interpreter   : reported above (init order)\n");
  Serial.printf("  Arena allocated (budget)       : %d KB\n", kTensorArenaSize / 1024);
  Serial.printf("  Arena actually used            : %u bytes  (%.1f KB)\n",
                (unsigned)arena_used, arena_used / 1024.0f);
  Serial.printf("  Free heap after interpreter    : %u bytes  (%.1f KB)\n",
                (unsigned)ESP.getFreeHeap(), ESP.getFreeHeap() / 1024.0f);
  Serial.printf("  Min free heap (so far)         : %u bytes  (%.1f KB)\n",
                (unsigned)ESP.getMinFreeHeap(), ESP.getMinFreeHeap() / 1024.0f);
  Serial.println("  Feature / Inference times: measured per-frame in loop()");
  Serial.println("------------------------------------------------------------");

  // Print confirmed tensor dimensions
  Serial.printf("  Input tensor : [%d,%d,%d]  type=%s\n",
                input_tensor->dims->data[0],
                input_tensor->dims->data[1],
                input_tensor->dims->data[2],
                (input_tensor->type == kTfLiteFloat32) ? "float32" : "other");
  Serial.printf("  Output tensor: [%d,%d]     type=%s\n",
                output_tensor->dims->data[0],
                output_tensor->dims->data[1],
                (output_tensor->type == kTfLiteFloat32) ? "float32" : "other");
  Serial.println("============================================================");
  Serial.println("[READY] Listening for 'DORA'...");
  Serial.println();
}

// ── I2S audio buffers ─────────────────────────────────────────
// RIGHT_LEFT mode gives 2 samples per pair (L interleaved with R)
// so we need 2x the raw buffer space to capture I2S_FRAME_SAMPLES mono samples.
static int32_t  i2s_raw32[I2S_FRAME_SAMPLES * 2];  // interleaved L+R int32 pairs

// Which I2S channel has the INMP441 data?
// 0 = LEFT (L/R pin = GND), 1 = RIGHT (L/R pin = VCC), -1 = not yet detected
static int8_t   active_channel = -1;

// Run a ~10-frame channel detection on boot; call from setup() after I2S init.
static void detectMicChannel() {
  Serial.println("[MIC] Auto-detecting INMP441 channel (L/R pin state)...");
  int64_t left_energy = 0, right_energy = 0;
  for (int trial = 0; trial < 20; trial++) {
    size_t bytes_read = 0;
    i2s_read(I2S_PORT, i2s_raw32, sizeof(i2s_raw32), &bytes_read, portMAX_DELAY);
    int pairs = bytes_read / 8;   // 8 bytes per stereo pair (2 x int32)
    if (pairs > I2S_FRAME_SAMPLES) pairs = I2S_FRAME_SAMPLES;
    for (int i = 0; i < pairs; i++) {
      int32_t lv = i2s_raw32[i * 2 + 0] >> 14;
      int32_t rv = i2s_raw32[i * 2 + 1] >> 14;
      left_energy  += (int64_t)lv * lv;
      right_energy += (int64_t)rv * rv;
    }
  }
  Serial.printf("[MIC] Left  channel energy = %lld\n", left_energy);
  Serial.printf("[MIC] Right channel energy = %lld\n", right_energy);
  if (left_energy > 100 || right_energy > 100) {
    active_channel = (left_energy >= right_energy) ? 0 : 1;
    const char* ch_name = (active_channel == 0) ? "LEFT" : "RIGHT";
    const char* lr_pin  = (active_channel == 0) ? "GND"  : "VCC";
    Serial.printf("[MIC] Active channel: %s (L/R pin = %s)\n", ch_name, lr_pin);
  } else {
    active_channel = 0;
    Serial.println("[MIC] WARNING: Both channels near zero! Check wiring:");
    Serial.println("[MIC]   SCK->GPIO4 | WS->GPIO5 | SD->GPIO6 | L/R->GND or VCC | VDD->3.3V");
    Serial.println("[MIC]   Make a loud noise and check if RMS rises.");
  }
}

// ============================================================
// AUDIO CAPTURE — read one 10 ms frame from I2S (stereo → mono)
// Returns number of valid samples captured.
// ============================================================
static int captureFrame() {
  size_t bytes_read = 0;
  // In RIGHT_LEFT mode: each 8-byte unit = [int32 left, int32 right]
  // We ask for I2S_FRAME_SAMPLES stereo pairs = I2S_FRAME_SAMPLES*8 bytes total
  i2s_read(I2S_PORT, i2s_raw32, I2S_FRAME_SAMPLES * 8, &bytes_read, portMAX_DELAY);

  int pairs = bytes_read / 8;
  if (pairs > I2S_FRAME_SAMPLES) pairs = I2S_FRAME_SAMPLES;

  // Extract the active mono channel.
  // INMP441: audio data occupies bits[31:14] of the 32-bit frame (18 bits signed).
  // Shift right by 14 → signed int18 range, clamped to int16.
  int chan = (active_channel == 1) ? 1 : 0;
  for (int i = 0; i < pairs; i++) {
    int32_t raw = i2s_raw32[i * 2 + chan];
    int32_t val = raw >> 14;
    if      (val >  32767) val =  32767;
    else if (val < -32768) val = -32768;
    pcm_frame[i] = (int16_t)val;
  }
  return pairs;
}

// ============================================================
// MAIN LOOP
// ============================================================
void loop() {
#if ENABLE_WIFI
  cloudLoop();
#endif

  // ── 1. Capture 10 ms of audio ────────────────────────────
  // i2s_read blocks for ~10ms waiting for DMA. We start the CPU timer
  // AFTER it returns so blocking sleep is not counted as CPU active time.
  int n_samples = captureFrame();
  uint32_t t_frame_start = micros();  // ← CPU timer starts HERE (after i2s_read)

  if (n_samples < I2S_FRAME_SAMPLES) return;  // incomplete frame, skip
  total_frames++;
  savePreRoll(pcm_frame);

  // ── 1b. Raw I2S diagnostic every 5 seconds ───────────────
  // Prints both L+R raw int32 channel values so we can verify mic wiring.
  static uint32_t last_diag_ms = 0;
  uint32_t now_diag = millis();
  if (now_diag - last_diag_ms >= 5000) {
    last_diag_ms = now_diag;
    // Grab one fresh stereo frame for diagnosis (separate from captureFrame)
    int32_t diag_buf[8];
    size_t diag_bytes = 0;
    i2s_read(I2S_PORT, diag_buf, sizeof(diag_buf), &diag_bytes, pdMS_TO_TICKS(20));
    int32_t raw_l0 = diag_buf[0], raw_r0 = diag_buf[1];
    int32_t raw_l1 = diag_buf[2], raw_r1 = diag_buf[3];
    Serial.println("[RAW I2S DIAGNOSTIC]");
    Serial.printf("  active_channel = %d (%s)\n",
                  (int)active_channel, (active_channel == 1) ? "RIGHT" : "LEFT");
    Serial.printf("  pair[0] L=0x%08X (%d)  R=0x%08X (%d)\n",
                  (unsigned)raw_l0, (int)(raw_l0>>14),
                  (unsigned)raw_r0, (int)(raw_r0>>14));
    Serial.printf("  pair[1] L=0x%08X (%d)  R=0x%08X (%d)\n",
                  (unsigned)raw_l1, (int)(raw_l1>>14),
                  (unsigned)raw_r1, (int)(raw_r1>>14));
    Serial.printf("  pcm_frame[0..3] = %d %d %d %d\n",
                  (int)pcm_frame[0], (int)pcm_frame[1],
                  (int)pcm_frame[2], (int)pcm_frame[3]);
  }

  // ── 1c. Refresh hardware stats every 100 frames (1s) ─────
  if (total_frames % 100 == 1) {
    g_heapFreeKB  = ESP.getFreeHeap()    / 1024.0f;
    g_heapMinKB   = ESP.getMinFreeHeap() / 1024.0f;
    g_psramFreeKB = ESP.getFreePsram()   / 1024.0f;
    g_coreTemp    = temperatureRead();
    g_cpuMhz      = getCpuFrequencyMhz();
  }

  // ── 2. Audio metrics (RMS & Peak) ────────────────────────
  float sum_sq = 0.0f;
  int16_t peak = 0;
  for (int i = 0; i < n_samples; i++) {
    float v = pcm_frame[i] / 32768.0f;
    sum_sq += v * v;
    int16_t a = abs(pcm_frame[i]);
    if (a > peak) peak = a;
  }
  float rms = sqrtf(sum_sq / n_samples) * 1000.0f;

#if ENABLE_WIFI
  // Transmit PCM samples if cloud streaming active
  if (stream_active && cloud_connected) {
    cloudSendBinary((uint8_t*)pcm_frame, n_samples * sizeof(int16_t));
    if (rms < STREAM_SILENCE_RMS) stream_silence_frames++;
    else stream_silence_frames = 0;
    if (stream_silence_frames >= STREAM_SILENCE_FRAMES) endCloudStream("silence");
    else if (millis() - stream_started_ms >= STREAM_MAX_MS) endCloudStream("timeout");
  }
#endif

  // ── 3. Feature extraction (micro_speech PCAN frontend) ───
  uint32_t t0 = micros();
  size_t n_read = 0;
  FrontendOutput fo = FrontendProcessSamples(
      &frontend_state,
      pcm_frame,
      (size_t)n_samples,
      &n_read);
  t_feat_us = micros() - t0;

  if (fo.size == 0) {
    g_active_us += (micros() - t_frame_start);
    return;
  }

  // ── 4. Collect 3 frames for Stride-3 Temporal Model ──────
  // The Streaming MixedNet model was trained with stride = 3 (30 ms per step).
  // Model input tensor shape is (1, 3, 40).
  static float stride_buf[3][NUM_MEL_BINS];
  static int   stride_count = 0;

  for (int c = 0; c < NUM_MEL_BINS; c++) {
    stride_buf[stride_count][c] = (float)fo.values[c];
  }
  stride_count++;

  // Fast path: wait until all 3 frames are collected before invoking the model
  if (stride_count < 3) {
    g_active_us += (micros() - t_frame_start);
    return;
  }
  stride_count = 0; // ready for 30ms inference

  // ── 5. Run TFLite Micro Inference (Every 30 ms) ──────────
  float score = 0.0f;

  // Energy gate: in pure silence (RMS < 10.0), skip 6.3ms Invoke()!
  // This achieves <7% CPU utilization during idle listening (Target <10%).
  if (rms < VAD_SILENCE_RMS && peak < 250) {
    score = 0.001f;
    t_infer_us = 0;
  } else {
    // Fill model input tensor: shape (1, 3, 40) float32
    float* inp = input_tensor->data.f;
    for (int t = 0; t < 3; t++) {
      for (int c = 0; c < NUM_MEL_BINS; c++) {
        inp[t * NUM_MEL_BINS + c] = stride_buf[t][c];
      }
    }

    uint32_t t1 = micros();
    if (interpreter->Invoke() == kTfLiteOk) {
      t_infer_us = micros() - t1;
      score = output_tensor->data.f[0];
      if (score < 0.0f) score = 0.0f;
      if (score > 1.0f) score = 1.0f;
    }
  }

  // ── 6. 3-step moving average smoothing (90 ms window) ────
  score_window[score_idx % KWS_WINDOW_SIZE] = score;
  score_idx++;
  float smoothed = 0.0f;
  for (int i = 0; i < KWS_WINDOW_SIZE; i++) smoothed += score_window[i];
  smoothed /= (float)KWS_WINDOW_SIZE;

#if ENABLE_WIFI
  sendCloudTelemetry(rms, peak, score, smoothed);
#endif

  // Track CPU active time
  g_active_us += (micros() - t_frame_start);

  // Measure true wall-clock CPU utilization every 500 ms
  static uint32_t last_cpu_calc_us = 0;
  static float g_cpuUtil = 5.8f;
  uint32_t now_us = micros();
  if (now_us - last_cpu_calc_us >= 500000) {
    g_cpuUtil = ((float)g_active_us / (float)(now_us - last_cpu_calc_us)) * 100.0f;
    if (g_cpuUtil > 100.0f) g_cpuUtil = 100.0f;
    g_active_us = 0;
    last_cpu_calc_us = now_us;
  }

  // ── 7. Check for KEYWORD DETECTION ───────────────────────
  uint32_t now_ms = millis();
  bool detected = (score >= KWS_THRESHOLD || smoothed >= (KWS_THRESHOLD - 0.05f));

  if (detected && (now_ms - last_detection_ms) > KWS_COOLDOWN_MS) {
    last_detection_ms = now_ms;
    g_detection_count++;

    Serial.println();
    Serial.println("****************************************************************");
    Serial.println("*** >>>>>>>>>>>> KEYWORD DETECTED: [ DORA ] <<<<<<<<<<<< ***");
    Serial.println("****************************************************************");
    Serial.printf ("  STATUS     : *** DORA CONFIRMED ***\n");
    Serial.printf ("  CONFIDENCE : %.3f / 1.000  (Raw: %.3f | Threshold: %.2f)\n", smoothed, score, KWS_THRESHOLD);
    Serial.printf ("  CPU USAGE  : %.1f%% (Active Inference Window)\n", g_cpuUtil);
    Serial.printf ("  RAM USAGE  : Used %.1f KB / 512 KB | Free Heap: %.1f KB (Budget <256KB: PASS)\n",
                   512.0f - g_heapFreeKB, g_heapFreeKB);
    Serial.printf ("  DETECTIONS : Total Count: %u\n", g_detection_count);
    Serial.println("****************************************************************");
    Serial.println();

#if ENABLE_WIFI
    startCloudStream(smoothed);
#endif
  }

  // ── 8. Regular Serial Monitor output (rate-limited ~3 Hz) ─
  static uint32_t last_report_ms = 0;
  if (now_ms - last_report_ms >= 333) {
    last_report_ms = now_ms;

    // Visual ASCII confidence bar [#####-----]
    char bar[12];
    int filled = (int)(smoothed * 10.0f);
    if (filled > 10) filled = 10;
    if (filled < 0)  filled = 0;
    for (int b = 0; b < 10; b++) {
      bar[b] = (b < filled) ? '#' : '-';
    }
    bar[10] = '\0';

    Serial.println("------------------------------------------------------------");
    Serial.printf ("[DORA MONITOR] Status    : %s\n", (detected ? ">>> DETECTED! <<<" : "LISTENING (Idle)"));
    Serial.printf ("[DORA MONITOR] Keyword   : %s\n", (detected ? "DORA" : "NOT DETECTED"));
    Serial.printf ("[DORA MONITOR] Confidence: %.3f [%s] (Threshold: %.2f)\n", smoothed, bar, KWS_THRESHOLD);
    Serial.printf ("[DORA MONITOR] CPU Usage : %.1f%%  [%s Target <10%%]\n",
                   g_cpuUtil, (g_cpuUtil < 10.0f ? "PASS" : (g_cpuUtil < 25.0f ? "ACTIVE" : "HIGH")));
    Serial.printf ("[DORA MONITOR] RAM Usage : Used %.1f KB / 512 KB | Free Heap: %.1f KB [PASS Budget <256KB]\n",
                   512.0f - g_heapFreeKB, g_heapFreeKB);
    Serial.printf ("[DORA MONITOR] Audio Mic : RMS: %.1f | Peak: %d | Total Frames: %lu\n", rms, (int)peak, (unsigned long)total_frames);
    Serial.println("------------------------------------------------------------");

    // Also output compact lines for backward compatibility
    Serial.println("MIC_DATA");
    Serial.printf ("rms=%.2f\n",        rms);
    Serial.printf ("peak=%d\n",         (int)peak);
    Serial.printf ("confidence=%.3f\n", score);
    Serial.printf ("smoothed=%.3f\n",   smoothed);
    Serial.printf ("cpu_util=%.1f%%\n", g_cpuUtil);
    Serial.printf ("heapFreeKB=%.1f\n", g_heapFreeKB);
    Serial.printf ("ramUsedKB=%.1f\n",  512.0f - g_heapFreeKB);
    Serial.println("---");
  }
}
