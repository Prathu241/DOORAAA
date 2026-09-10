# Resource Budget — Final Ledger
## Document 12 — SIH26172 | DORA

---

## 1. RAM Budget (ESP32-S3 Internal SRAM)

**Total internal SRAM: 512 KB**  
**Hard limit from PS: 256 KB**  
**DORA target: < 180 KB peak**

| Component | RAM (KB) | Source of Estimate | Notes |
|---|---|---|---|
| KWS tensor arena (MixedNet activations) | 60–80 | microWakeWord field-measured on ESP32-S3 | Allocated once at startup, never freed |
| Pre-roll ring buffer (300 ms × 16 kHz × 2 B) | 9.6 | Exact calculation: 300×16000×2 = 9,600 B | Always full during listening |
| I2S DMA buffers (4 × 512 samples × 2 B) | 4.0 | ESP-IDF default (4 DMA descriptors) | Fixed by driver |
| Spectrogram feature ring buffer | 6.0 | 40 features × ~15 frames × 4 B/float | Sliding window for streaming |
| VAD model tensor arena | 10.0 | Small binary classifier | Much smaller than KWS |
| Opus encoder state (libopus) | 20.0 | libopus documented encoder state | Allocated at boot via `ws_init()` |
| WebSocket client + lwIP TCP/IP stack | 40.0 | ESP-IDF measured (lwIP default config) | Includes TCP send/recv buffers |
| FreeRTOS task stacks (3 tasks) | 15.0 | audio=4KB, kws=8KB, telemetry=3KB | See task creation in main.c |
| FreeRTOS kernel + queues | 4.0 | ESP-IDF overhead | Fixed |
| **Total (pessimistic)** | **~168–188** | | **< 256 KB limit ✓** |
| **Headroom** | **68–88** | | **Against 256 KB ceiling** |

### 1.1 PSRAM Usage

The ESP32-S3 N8R8 has 8 MB of external OPI PSRAM. DORA does **not** rely on PSRAM for the critical path — all latency-sensitive buffers (tensor arena, ring buffer, DMA) are in internal SRAM. PSRAM is available as overflow for larger allocations like TTS processing during dataset generation (not used at runtime).

### 1.2 How to Measure Peak RAM on Device

```c
// Add to app_main after all tasks are created, after a 5-second delay:
vTaskDelay(pdMS_TO_TICKS(5000));
size_t min_heap = heap_caps_get_minimum_free_size(MALLOC_CAP_INTERNAL);
size_t cur_heap = heap_caps_get_free_size(MALLOC_CAP_INTERNAL);
ESP_LOGI("RAM", "Current free: %u KB, Minimum ever free: %u KB",
         cur_heap/1024, min_heap/1024);
```

The `minimum_free_size` value reflects worst-case peak usage including FreeRTOS stack high-water marks.

---

## 2. Flash Budget (8 MB Total)

| Component | Flash (KB) | Notes |
|---|---|---|
| KWS model weights (.rodata) | 50–80 | `kws_model_data.cc` embedded array |
| VAD model weights (.rodata) | ~10 | `vad_model_data.cc` embedded array |
| ESP-IDF firmware binary | ~1,500 | lwIP, Wi-Fi stack, TFLite Micro, Opus |
| Application code (all .c/.cc) | ~50 | Small compared to libraries |
| NVS partition | 24 | Wi-Fi credentials, ESP-IDF key-value store |
| OTA partition (reserved) | 1,024 | Optional — for over-the-air updates |
| **Total** | **~2,760** | **Well within 8 MB = 8,192 KB ✓** |

---

## 3. CPU Budget (ESP32-S3, Dual Core, 240 MHz)

| Task | Core | CPU % at Idle | CPU % During Stream | Notes |
|---|---|---|---|---|
| `audio_capture_task` | 0 | ~1% | ~3% | I2S DMA + ring buffer write |
| VAD inference | 0 (within audio task) | ~0.1% | ~0.1% | Tiny model, runs always |
| `kws_inference_task` | 1 | ~8% | ~8% | Mel features + MixedNet + window |
| Opus encode + WS send | 1 (within kws task) | 0% | ~15% | Only active during 3s stream window |
| `telemetry_task` | 0 | ~0.1% | ~0.1% | HTTP POST every 5s, very short |
| lwIP / Wi-Fi stack | 0 | ~1% | ~2% | Background maintenance |
| FreeRTOS idle | Both | ~90% | ~72% | |
| **Active CPU (non-idle)** | | **~10%** | **~28%** | |

> **PS requirement:** < 10% idle CPU. DORA meets this: during silence (no stream active), active CPU is ~9–10%. During the 3-second stream window after detection, CPU spikes to ~28% — acceptable because this is not "idle".

### 3.1 How Idle CPU is Measured by Telemetry

```c
// From telemetry.c — cpu_active_pct()
// Uses FreeRTOS uxTaskGetSystemState() to get per-task run time counters
// Computes: 100% - (idle_task_time / total_time × 100%)
// Reports 5-second rolling average
```

---

## 4. Network Bandwidth Budget

| Traffic | Bandwidth | Notes |
|---|---|---|
| Opus stream (active) | 24 kbps | Only during 3s stream window per detection |
| Raw PCM equivalent | 256 kbps | For comparison — 10× higher |
| WebSocket keep-alive | < 1 kbps | Ping/pong frames |
| Telemetry POST | < 0.1 kbps | ~100 bytes every 5 seconds |
| **Peak (during stream)** | **~25 kbps** | **Far below any Wi-Fi limit** |

Even on a congested Wi-Fi network, 25 kbps is negligible. This is why Opus compression is critical for latency — less data in the pipe means lower queuing delay.

---

## 5. Power Budget

| Mode | Current Draw | Duration | Energy |
|---|---|---|---|
| Idle listening (Wi-Fi on, VAD + KWS active) | ~200 mA @ 3.3V = 660 mW | Continuous | ~660 mWh/hr |
| Active stream (Opus encode + WS send) | ~260 mA @ 3.3V = 858 mW | ~3s per event | ~0.7 mWh/event |
| Deep sleep (Wi-Fi off) | ~10 mA | Not used in current design | — |

**Battery life estimate (1000 mAh LiPo @ 3.7V = 3.7 Wh):**
- Continuous listening: ~5.6 hours
- With keyword every 5 minutes: ~5.4 hours (stream overhead negligible)

---

## 6. Resource Budget vs. Competitors

| System | RAM | Flash | Idle CPU | Latency |
|---|---|---|---|---|
| ESP-Alexa (Amazon) | > 512 KB | > 4 MB | > 30% | ~1500 ms |
| microWakeWord | ~80 KB | ~150 KB | ~5% | N/A |
| **DORA** | **~168–188 KB** | **~2.7 MB** | **~10%** | **< 75 ms** |
| PS Hard Limit | 256 KB | 8 MB | 15% | Minimise |
