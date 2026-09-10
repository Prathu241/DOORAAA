# Firmware Guide — ESP32-S3 Complete Walkthrough
## Document 08 — SIH26172 | DORA

---

## 1. Prerequisites

- ESP-IDF v5.2 or later installed and sourced (`idf.py --version` should work)
- ESP32-S3-DevKitC-1 connected via USB-C
- INMP441 wired per Document 04 (GPIO 4/5/6)
- Server IP known and set in `main.c`
- Trained `.tflite` model available at `models/DORA_streaming_int8.tflite`

---

## 2. Project Structure

```
dora_firmware/
├── CMakeLists.txt              ← Top-level ESP-IDF CMake
├── idf_component.yml           ← Component dependencies declaration
└── main/
    ├── CMakeLists.txt          ← main component sources list
    ├── main.c                  ← app_main, Wi-Fi, task creation
    ├── ring_buffer.h           ← Circular buffer API
    ├── ring_buffer.c           ← Circular buffer implementation
    ├── audio_capture.h         ← I2S driver API + pre-roll buffer extern
    ├── audio_capture.c         ← I2S DMA → ring buffer + audio queue
    ├── kws_model.h             ← KWS inference task API
    ├── kws_model.c             ← TFLite Micro + 5-frame window
    ├── websocket_client.h      ← WS init + stream API
    ├── websocket_client.c      ← Opus encode + pre-roll flush + WS send
    ├── telemetry.h             ← Telemetry task API
    ├── telemetry.c             ← RAM/CPU HTTP POST
    ├── kws_model_data.cc       ← Embedded KWS model (xxd-generated)
    └── vad_model_data.cc       ← Embedded VAD model (xxd-generated)
```

---

## 3. Component Dependencies (`idf_component.yml`)

```yaml
dependencies:
  espressif/esp-tflite-micro: ">=1.0.0"
  espressif/esp-opus: ">=1.0.0"
```

Install them:
```bash
cd dora_firmware
idf.py add-dependency "espressif/esp-tflite-micro"
idf.py add-dependency "espressif/esp-opus"
```

`esp_websocket_client` is built into ESP-IDF — no extra component needed.

---

## 4. Module Reference

### 4.1 ring_buffer — Circular Pre-Roll Buffer

**API:**
```c
void   rb_init  (ring_buffer_t *rb, size_t capacity);
void   rb_write (ring_buffer_t *rb, const void *data, size_t bytes);
int    rb_read  (ring_buffer_t *rb, void *dst, size_t bytes);
void   rb_reset (ring_buffer_t *rb);
size_t rb_count (ring_buffer_t *rb);
```

**Key behaviour:** `rb_write` is a circular overwrite — when full, oldest data is silently dropped. This means the buffer always contains the most recent `AUDIO_PRE_ROLL_MS` milliseconds of audio.

**Allocated size:** `300 ms × 16,000 Hz × 2 bytes = 9,600 bytes (~9.6 KB)`

---

### 4.2 audio_capture — I2S DMA Driver

**Key constants:**
```c
#define AUDIO_SAMPLE_RATE   16000    // Hz, mono
#define AUDIO_DMA_BUF_LEN   512      // samples per DMA interrupt
#define AUDIO_PRE_ROLL_MS   300      // ms of pre-roll maintained
```

**Task behaviour:**
1. Initialises `g_pre_roll_buf` (9.6 KB circular buffer)
2. Configures I2S0 in standard Philips mode, 16-bit mono, 16 kHz
3. Loops forever: reads 512 samples from DMA → writes to pre-roll → sends to audio queue

**GPIO config:**
```c
.bclk = GPIO_NUM_5,   // SCK on INMP441
.ws   = GPIO_NUM_4,   // WS on INMP441
.din  = GPIO_NUM_6,   // SD on INMP441
```

---

### 4.3 kws_model — TFLite Micro Inference

**Tensor arena size:** 80 KB (adjust down to 60 KB if RAM is tight)

**Op resolver — only 8 ops needed:**
```cpp
resolver.AddConv2D();
resolver.AddDepthwiseConv2D();
resolver.AddReshape();
resolver.AddSoftmax();
resolver.AddMean();
resolver.AddAdd();
resolver.AddMul();
resolver.AddFullyConnected();
```

**Feature extraction note:**
The `kws_model.c` file contains a placeholder for the feature extraction call. Replace with the actual `FrontendProcessSamples()` API from the microWakeWord ESP-IDF component:

```c
// Replace placeholder block with:
int8_t features[40];
size_t n_samples_read;
FrontendOutput fo = FrontendProcessSamples(
    &frontend_state, frame.data, frame.len, &n_samples_read);
memcpy(in->data.int8, fo.values, 40 * sizeof(int8_t));
```

**Detection flow:**
- Per frame: run inference → get `keyword_prob = out->data.f[0]`
- Feed to 5-frame window average
- If avg ≥ `KWS_THRESHOLD`: record `t_kw_end_us`, call `ws_start_stream()`, reset window, delay 1 second

---

### 4.4 websocket_client — Opus Streaming

**Opus encoder settings:**
```c
#define OPUS_BITRATE        24000    // bps
#define OPUS_FRAME_SAMPLES  320      // 20 ms × 16 kHz
#define STREAM_TIMEOUT_MS   3000     // stream for 3 seconds after keyword
```

**`ws_init(uri)` — called at boot:**
- Creates Opus encoder (complexity=3, VOIP mode)
- Opens WebSocket connection to server
- Connection stays open permanently — this is the pre-warming

**`ws_start_stream(t_kw_end_us)` — called on detection:**
1. Send `{"type":"start","t_kw_end_us":N}` — includes timestamp for latency calculation
2. Flush pre-roll ring buffer (Opus-encode each 320-sample frame)
3. Stream live audio for `STREAM_TIMEOUT_MS` (3 seconds)
4. Zero-pad final partial frame
5. Send `{"type":"end"}`

---

### 4.5 telemetry — RAM/CPU Reporting

**Reports every 5 seconds to `http://<SERVER_IP>:8765/telemetry`:**

```json
{"ram_kb": 88, "cpu_pct": 7.3}
```

- `ram_kb`: free internal heap in KB (`heap_caps_get_free_size(MALLOC_CAP_INTERNAL) / 1024`)
- `cpu_pct`: active CPU percentage, calculated from FreeRTOS task run-time stats

> Requires `configGENERATE_RUN_TIME_STATS=1` in ESP-IDF menuconfig. This is the default in ESP-IDF v5.2+.

---

### 4.6 main.c — Application Entry Point

**Configuration (edit before build):**
```c
#define WIFI_SSID   "YOUR_SSID"
#define WIFI_PASS   "YOUR_PASSWORD"
#define SERVER_URI  "ws://192.168.1.100:8765/stream"
```

**Boot sequence:**
```
1. wifi_init()            → connects to Wi-Fi, waits 3s for IP
2. ws_init(SERVER_URI)    → pre-warms WebSocket connection
3. xQueueCreate()         → creates shared audio queue (depth=8)
4. xTaskCreatePinnedToCore(audio_capture_task, Core 0, priority 5)
5. xTaskCreatePinnedToCore(kws_inference_task, Core 1, priority 4)
6. xTaskCreatePinnedToCore(telemetry_task,     Core 0, priority 1)
```

---

## 5. Embedding the Model

After training produces `models/DORA_streaming_int8.tflite`:

```bash
# Step 1: Convert to C array
xxd -i models/DORA_streaming_int8.tflite > dora_firmware/main/kws_model_data.cc

# Step 2: Fix variable name (xxd generates a non-const, non-aligned name)
# Open kws_model_data.cc and change the first line from:
#   unsigned char models_DORA_streaming_int8_tflite[] = {
# to:
#   const unsigned char g_kws_model_data[] __attribute__((aligned(8))) = {

# Step 3: Fix length line (at the end of the file), change from:
#   unsigned int models_DORA_streaming_int8_tflite_len = NNNN;
# to:
#   const unsigned int g_kws_model_data_len = NNNN;
# (keep the integer value NNNN as-is)

# Step 4: Repeat for VAD model → vad_model_data.cc
# (variable names: g_vad_model_data, g_vad_model_data_len)
```

---

## 6. Build, Flash, and Monitor

```bash
cd dora_firmware

# Configure (first time only)
idf.py menuconfig
# Ensure: Component config → FreeRTOS → Enable FreeRTOS run time stats

# Build
idf.py build

# Flash (ESP32-S3 must be in download mode or auto-reset supported)
idf.py flash

# Monitor (Ctrl+] to exit)
idf.py monitor

# All in one:
idf.py build flash monitor
```

---

## 7. Expected Serial Monitor Output on Boot

```
I (1234) AUDIO: I2S started at 16000 Hz
I (1456) WS: Pre-warmed WS → ws://192.168.1.100:8765/stream
I (1890) wifi: connected to YOUR_SSID, IP: 192.168.1.101
```

On keyword detection:
```
I (45678) KWS: keyword detected, t_end=45678123 µs
I (45680) WS: flushing pre-roll (9600 bytes)
I (45820) WS: streaming live audio...
I (48850) WS: stream ended, sent {"type":"end"}
```

---

## 8. Common Issues and Fixes

| Issue | Likely Cause | Fix |
|---|---|---|
| No audio in serial monitor | I2S GPIO wrong | Verify GPIO 4/5/6 wiring |
| INMP441 all zeros | L/R pin not tied to GND | Connect L/R to GND |
| WS connection failed | Wrong server IP | Update `SERVER_URI` in `main.c` |
| KWS never triggers | Threshold too high | Lower `KWS_THRESHOLD` to 0.55 for testing |
| KWS triggers on silence | Threshold too low / bad model | Retrain with more negatives |
| OOM / heap allocation failed | Tensor arena too large | Reduce `TENSOR_ARENA_KB` from 80 to 60 |
| Opus encode error | Wrong frame size | Ensure exactly 320 samples per Opus call |
| Build fails: missing op | Model uses op not in resolver | Add the missing `resolver.AddXxx()` call |
