# Software Design
## Document 05 — SIH26172 | DORA

---

## 1. Software Layers Overview

DORA's software is split across three environments:

| Environment | Language | Framework | Purpose |
|---|---|---|---|
| ESP32-S3 Firmware | C / C++ | ESP-IDF v5.2 + FreeRTOS | Audio capture, KWS inference, streaming |
| Training Environment | Python 3.10+ | TensorFlow 2.15, microWakeWord | Dataset prep, model training, quantisation |
| Server Environment | Python 3.10+ | FastAPI, Vosk, opuslib | ASR, telemetry, dashboard |

---

## 2. Firmware Software Design

### 2.1 Module Map

```
dora_firmware/main/
├── main.c                 ← Entry point: Wi-Fi init, task creation, WS pre-warm
├── ring_buffer.h/.c       ← Generic circular buffer (audio pre-roll)
├── audio_capture.h/.c     ← I2S DMA driver → ring buffer + inference queue
├── kws_model.h/.c         ← TFLite Micro inference + 5-frame sliding window
├── websocket_client.h/.c  ← Pre-warmed WS connection + Opus streaming
├── telemetry.h/.c         ← RAM/CPU HTTP POST every 5 seconds
├── kws_model_data.cc      ← Embedded int8 KWS .tflite (xxd-generated)
└── vad_model_data.cc      ← Embedded VAD .tflite (xxd-generated)
```

### 2.2 Inter-Module Interface

```
main.c
  │
  ├── wifi_init()               ← blocking until IP obtained
  ├── ws_init(SERVER_URI)       ← pre-warm WebSocket at boot
  ├── xQueueCreate(g_audio_queue)
  │
  ├── audio_capture_task(g_audio_queue)   [Core 0, priority 5]
  │       │  reads I2S DMA
  │       ├── rb_write(g_pre_roll_buf)    ← always writing pre-roll
  │       └── xQueueSend(g_audio_queue)  ← non-blocking to KWS
  │
  ├── kws_inference_task(g_audio_queue)  [Core 1, priority 4]
  │       │  reads audio queue
  │       ├── FrontendProcessSamples()   ← Mel spectrogram
  │       ├── interp.Invoke()            ← MixedNet inference
  │       ├── kws_process_score()        ← 5-frame window
  │       └── ws_start_stream(t_kw_end) ← on detection
  │
  └── telemetry_task(NULL)              [Core 0, priority 1]
          └── HTTP POST /telemetry every 5s
```

### 2.3 Shared State

| Variable | Owner | Consumers |
|---|---|---|
| `g_audio_queue` | `main.c` | `audio_capture_task` (writer), `kws_inference_task` (reader) |
| `g_pre_roll_buf` | `audio_capture.c` | `websocket_client.c` (reader on detection) |

No mutex is used on `g_pre_roll_buf` — audio capture writes continuously, WS client reads once on detection. The circular overwrite semantics mean a missed write during the read window is acceptable (adds < 1 ms gap).

### 2.4 KWS Decision Logic

```c
// 5-frame sliding window — defined in kws_model.c
#define KWS_WINDOW_SIZE   5       // 5 × 10 ms = 50 ms window
#define KWS_THRESHOLD     0.65f   // tuned via threshold_sweep.py
#define KWS_COOLDOWN_MS   1000    // prevents double-detection

// Per 10 ms inference result:
score_buf[score_idx % KWS_WINDOW_SIZE] = keyword_prob;
score_idx++;
avg = mean(score_buf);

if (avg >= KWS_THRESHOLD) {
    t_keyword_end_us = esp_timer_get_time();
    ws_start_stream(t_keyword_end_us);
    reset_window();
    vTaskDelay(KWS_COOLDOWN_MS);
}
```

- **Window size 5:** Prevents single-frame noise spikes from triggering detection
- **Threshold 0.65:** Starting point — tune via `threshold_sweep.py` for ≥ 92% recall
- **Cooldown 1000 ms:** Prevents the trailing edge of one detection triggering another

### 2.5 WebSocket Stream Protocol

The WS stream uses a simple JSON + binary multiplexed protocol:

```
Device → Server:  {"type":"start","t_kw_end_us":1234567890}   ← text frame
Device → Server:  <Opus binary frame 1>                        ← binary frame
Device → Server:  <Opus binary frame 2>                        ← binary frame
...
Device → Server:  {"type":"end"}                               ← text frame
Server → Device:  {"type":"result","text":"hello","latency_ms":42.1}
Server → Device:  {"type":"partial","text":"hel"}              ← optional mid-stream
```

### 2.6 Opus Encoding Parameters

| Parameter | Value | Rationale |
|---|---|---|
| Sample rate | 16,000 Hz | Matches ASR input requirement |
| Channels | 1 (mono) | Matches INMP441 config |
| Bitrate | 24,000 bps | 10× less than raw PCM; sufficient for speech |
| Frame size | 320 samples (20 ms) | Opus standard; low latency frame |
| Complexity | 3 | Low CPU — MCU cannot afford higher |
| Application | OPUS_APPLICATION_VOIP | Optimised for voice, not music |

---

## 3. Training Environment Software Design

### 3.1 Script Pipeline

```
generate_keyword_dataset.py   ← Piper TTS synthesis
record_keyword.py             ← Manual recordings
augment_real.py               ← 4× augmentation of real recordings
prepare_dataset.py            ← Merge + speaker-split
        │
        ▼
microWakeWord/train.py        ← Float32 model training
microWakeWord/convert.py      ← Streaming TFLite + int8 quantisation
microWakeWord/evaluate.py     ← Recall / FA / precision metrics
threshold_sweep.py            ← Pick optimal KWS_THRESHOLD
```

### 3.2 Audio Front-End Parameters

These parameters must match exactly between training and the on-device C preprocessor:

| Parameter | Value |
|---|---|
| `SAMPLE_RATE` | 16,000 Hz |
| `WINDOW_MS` | 30 ms |
| `STRIDE_MS` | 10 ms |
| `N_MEL` | 40 |
| `N_FFT` | 512 |
| `HOP_LENGTH` | 160 samples (= 10 ms at 16 kHz) |

> **Critical:** Changing any of these values breaks the training/inference match. The C preprocessor (`micro_speech` in esp-tflite-micro) uses these same values hard-coded.

---

## 4. Server Software Design

### 4.1 FastAPI Application Structure

```python
app = FastAPI()

# Shared state dictionary (in-memory, single process)
state = {
    "ram_kb": 0, "cpu_pct": 0.0, "detections": 0,
    "last_latency_ms": None, "last_asr_text": "",
    "events": []   # ring buffer of last 100 events
}

@app.websocket("/stream")    ← ESP32 audio stream
@app.post("/telemetry")      ← ESP32 RAM/CPU metrics
@app.get("/data")            ← Dashboard JSON poll
@app.get("/")                ← Dashboard HTML
```

### 4.2 Latency Calculation

```python
# On receiving {"type":"start","t_kw_end_us": N}:
t_kw_end  = msg["t_kw_end_us"] / 1_000_000   # µs → seconds
t_arrived = time.time()                        # server wall clock
latency_ms = round((t_arrived - t_kw_end) * 1000, 1)
```

> **Note:** This measures keyword-end → server-first-byte latency, which is exactly the metric the PS specifies. It includes Wi-Fi transit time, Opus encode/decode, and server receive processing. It does **not** require clock synchronisation — `esp_timer_get_time()` measures relative microseconds since boot; `time.time()` on the server is absolute. The difference is valid because the device sends `t_kw_end_us` inside the first WebSocket frame received by the server.

### 4.3 ASR Pipeline

```python
# Per WebSocket session:
recognizer = KaldiRecognizer(vosk_model, 16000)   # streaming recognizer
opus_dec    = opuslib.Decoder(16000, 1)            # Opus → PCM

# Per binary frame:
pcm      = opus_dec.decode(raw_bytes, 320)
pcm_bytes = struct.pack(f"{len(pcm)}h", *pcm)
recognizer.AcceptWaveform(pcm_bytes)

# On {"type":"end"}:
text = json.loads(recognizer.FinalResult())["text"]
```

---

## 5. Dashboard Software Design

The dashboard is a single `dashboard.html` file served by FastAPI. It uses:

- **Chart.js 4.4.0** (CDN) for the latency trend chart
- **Vanilla JS** `setInterval(refresh, 1000)` for polling `/data` every second
- **CSS custom properties** for the dark theme

### 5.1 UI Panels

| Panel | Data Source | Refresh |
|---|---|---|
| Last Latency (KPI) | `state.last_latency_ms` | 1 s |
| Detections (KPI) | `state.detections` | 1 s |
| Free RAM (KPI + bar) | `state.ram_kb` | 1 s (from telemetry POST) |
| Idle CPU (KPI) | `state.cpu_pct` | 1 s (from telemetry POST) |
| Latency chart (line) | `state.events[-30:]` | 1 s |
| Last ASR Result | `state.last_asr_text` | 1 s |
| Detection Event Log | `state.events[-100:]` | 1 s |
| Session Statistics | min/max/avg/p95 of `events` | 1 s |

### 5.2 Status Indicator

The status pill switches between `online` (green) and `offline` (red) based on whether the `/data` fetch succeeds. This gives immediate visual feedback if the server goes down.

---

## 6. Software Dependencies — Complete List

### Firmware (ESP-IDF)

```
ESP-IDF v5.2+
espressif/esp-tflite-micro   # TFLite Micro runtime + micro_speech preprocessor
espressif/esp-opus            # libopus port for ESP32
esp_websocket_client          # built-in to ESP-IDF, no extra component
```

### Training (Python)

```
tensorflow==2.15.0
tensorflow-model-optimization
numpy
librosa
soundfile
sounddevice
piper-tts
```

### Server (Python)

```
fastapi
uvicorn[standard]
vosk
opuslib
websockets
numpy
```
