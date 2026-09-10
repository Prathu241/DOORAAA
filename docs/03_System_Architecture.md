# System Architecture
## Document 03 — SIH26172 | DORA

---

## 1. High-Level Overview

DORA is a two-tier system: an **edge device** (ESP32-S3) handles always-on listening and keyword detection, and a **server** (laptop or Raspberry Pi 4) handles heavy ASR processing and dashboard rendering.

```
┌──────────────────────────────────────────────────────────────────┐
│                      ESP32-S3 (Edge Device)                      │
│                                                                  │
│  [I2S INMP441 Mic] ──▶ [VAD Model, always-on, <0.1% CPU]        │
│                                  │ voice detected                │
│                                  ▼                               │
│                      [Streaming MixedNet KWS]                    │
│                      [<10ms inference, int8]                     │
│                                  │ keyword confirmed             │
│                                  ▼                               │
│                      [Pre-roll Ring Buffer, 300ms]               │
│                      [+ live audio capture]                      │
│                                  │                               │
│                                  ▼                               │
│                      [Opus Encoder, 24 kbps]                     │
│                      [10× bandwidth reduction]                   │
│                                  │                               │
│                                  ▼                               │
│                      [Pre-warmed WebSocket]                      │
│                      [connected at boot — zero conn latency]     │
└──────────────────────────────────────────────────────────────────┘
                               │ Wi-Fi / LAN
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     Server (laptop / Pi 4)                       │
│                                                                  │
│  [Opus Decode] ──▶ [Vosk ASR, streaming] ──▶ [FastAPI server]   │
│                                                    │             │
│                                           [/data  /telemetry]   │
│                                                    │             │
│                                           [Dashboard HTML]       │
│                                     [Live: latency, RAM,        │
│                                      CPU, ASR text, events]     │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. Five-Stage Pipeline

### Stage 1 — Voice Activity Detection (VAD)

- **Purpose:** Gate Stage 2 — only wake the KWS when voice is present
- **Model:** Small binary TFLite classifier (microWakeWord cascade, adapted)
- **Location:** ESP32-S3 Core 0, always-on
- **CPU cost:** < 0.1% (runs on energy envelope of silence)
- **Input:** Raw I2S PCM @ 16 kHz, mono
- **Output:** Binary voice/no-voice decision per 10 ms frame

### Stage 2 — Keyword Spotting (KWS)

- **Purpose:** Detect the specific keyword (e.g., "DORA") in the voice stream
- **Model:** Streaming MixedNet, int8 quantised (microWakeWord architecture, retrained from scratch)
- **Location:** ESP32-S3 Core 1
- **Latency:** < 10 ms per inference call
- **RAM:** 60–80 KB tensor arena
- **Flash:** 50–80 KB model weights (.rodata)
- **Decision:** 5-frame sliding window average ≥ 0.65 threshold triggers detection

### Stage 3 — Pre-roll Buffer Flush

- **Purpose:** Capture the 300 ms of audio that occurred **before** the keyword ended
- **Implementation:** Circular ring buffer continuously updated by the I2S DMA task
- **Why it matters:** Without pre-roll, the ASR receives audio starting after the keyword — missing context
- **RAM cost:** 300 ms × 16,000 Hz × 2 bytes = **9.6 KB**

### Stage 4 — Opus Encoding + WebSocket Streaming

- **Purpose:** Compress and transmit audio to the server with minimal latency
- **Codec:** Opus at 24 kbps (libopus port for ESP32)
- **Transport:** Pre-warmed WebSocket (connected at boot, always ready)
- **Frame size:** 320 samples = 20 ms @ 16 kHz
- **Bandwidth:** 24 kbps vs 256 kbps raw PCM = **10× reduction**
- **Timestamp:** `t_kw_end_us` (from `esp_timer_get_time()`) sent in the `{"type":"start"}` JSON frame for latency calculation

### Stage 5 — Cloud ASR + Dashboard

- **ASR:** Vosk (Kaldi-based, fully offline, CPU-only) running on the server
- **Decoding:** Opus → PCM → KaldiRecognizer → text
- **Latency measurement:** `time.time()` on first byte received minus `t_kw_end_us` from device
- **Dashboard:** FastAPI serves `dashboard.html` — polls `/data` every 1 second for live metrics

---

## 3. Stage Origin Table

| Stage | Component | Origin |
|---|---|---|
| 1 — VAD | Always-on voice gate | microWakeWord cascade (adapted) |
| 2 — KWS | Streaming MixedNet, int8 | microWakeWord architecture, **retrained from scratch** |
| 3 — Pre-roll | 300 ms ring buffer flush | **Original** |
| 4 — Opus + WebSocket | Compressed pre-warmed stream | **Original** |
| 5 — Dashboard | Live latency + telemetry | **Original** |

---

## 4. Data Flow Diagram

```
I2S DMA (512 samples / 32 ms)
         │
         ├──▶ Ring Buffer (continuous overwrite, 300ms window)
         │
         └──▶ Audio Queue (FreeRTOS, depth=8)
                    │
                    ▼
             [Core 1: KWS Task]
             Mel spectrogram → MixedNet inference
             5-frame window average
                    │
            ┌── No detection: continue loop
            │
            └── Detection:
                   │
                   ├── Record t_kw_end_us
                   │
                   └──▶ [WS Stream Task]
                            │
                            ├── Send JSON start frame with timestamp
                            ├── Flush pre-roll buffer (Opus encoded)
                            ├── Stream live audio for 3 seconds
                            └── Send JSON end frame
                                        │
                                        ▼
                              [Server: Vosk ASR]
                              Opus decode → PCM → text
                              Measure latency = time.time() - t_kw_end
                                        │
                                        ▼
                              [FastAPI /data endpoint]
                              Update shared state
                                        │
                                        ▼
                              [Dashboard polls /data every 1s]
                              Render KPIs, chart, event log
```

---

## 5. FreeRTOS Task Model

| Task | Core | Priority | Stack | Function |
|---|---|---|---|---|
| `audio_capture_task` | Core 0 | 5 (highest) | 4 KB | I2S DMA → ring buffer + audio queue |
| `kws_inference_task` | Core 1 | 4 | 8 KB | Mel features → MixedNet → threshold check |
| `telemetry_task` | Core 0 | 1 (lowest) | 3 KB | RAM/CPU HTTP POST to server every 5s |

> Audio capture is pinned to Core 0 at highest priority to avoid I2S buffer overflow. KWS runs on Core 1 to avoid blocking audio DMA.

---

## 6. Network Topology

```
ESP32-S3 ──(Wi-Fi 2.4GHz)──▶ Router ──(LAN)──▶ Server (port 8765)
                                                    │
                                           ws://server:8765/stream   ← audio WebSocket
                                           POST /telemetry            ← RAM/CPU metrics
                                           GET  /data                 ← dashboard poll
                                           GET  /                     ← dashboard HTML
```

**Important:** Both the ESP32-S3 and the server must be on the same LAN segment for < 75 ms latency. Wi-Fi over the public internet adds ~50–200 ms of additional RTT.

---

## 7. Latency Budget Breakdown

| Segment | Expected | Notes |
|---|---|---|
| Keyword detection (5 frames × 10 ms) | ~50 ms | Unavoidable — sliding window |
| Pre-roll flush (Opus encode 300 ms) | ~15 ms | Pipelined with live capture |
| Wi-Fi transmission (LAN) | ~5–15 ms | Depends on router |
| Vosk decode + first partial | ~10–20 ms | Small Vosk model |
| **Total keyword-end → first-byte** | **~30–75 ms** | **Target: < 75 ms** |

The WebSocket pre-warming eliminates the ~300–500 ms connection setup that would otherwise dominate this budget.
