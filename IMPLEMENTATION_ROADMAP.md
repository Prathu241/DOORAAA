# IMPLEMENTATION ROADMAP — v4.1 Aligned

**Source:** DORA_Winning_Solution_v4.1

**Status:** Phase 1 (Dataset) Complete | Phase 2 (Training) Ready

**Deadline:** 30 September 2026

---

## MILESTONE SEQUENCE

### ✅ MILESTONE 1: Dataset Pipeline (COMPLETE)

**Objective:** Prepare keyword-agnostic dataset factory for DORA development.

**Tasks:**
- [x] Collect 100+ real recordings (OSCode drive)
- [x] Generate ~600 synthetic TTS samples (Piper, 5 voices, 9 speeds)
- [x] Generate hard negatives (phonetic confusables)
- [x] Augment real samples (4× noise/pitch/speed/reverb)
- [x] Prepare reusable negatives (Google Speech Commands v0.02, Mozilla Common Voice, MUSAN, DEMAND)
- [x] Build recording-group-disjoint train/val/test split (70/15/15)
- [x] Run dataset quality audit
- [x] Verify zero augmentation leakage

**Deliverables:**
- `dataset/split/train/DORA/` (935 files)
- `dataset/split/val/DORA/` (75 files)
- `dataset/split/test/DORA/` (75 files)
- `audit_dataset.py` output (format + leakage verified)

**Status:** ✅ PASS (2 expected warnings on negative coverage)

---

### ⏳ MILESTONE 2: Training Streaming MixedNet (IN PROGRESS)

**Objective:** Train binary keyword classifier from scratch, using microWakeWord architecture.

**Tasks:**
- [ ] Run training command with --restore_checkpoint 0 (fresh start)
- [ ] Monitor training loss / accuracy curves
- [ ] Verify floating-point model convergence
- [ ] Quantize to int8 streaming TFLite
- [ ] Measure quantized model size (target: 30–80 KB)
- [ ] Export final model: `stream_state_internal_quant.tflite`
- [ ] Generate `MODEL_CARD_DORA.md` with training metadata

**Command:**
```bash
cd microWakeWord
python -m microwakeword.model_train_eval \
    --training_config "../training_parameters_DORA.yaml" \
    --train 1 --restore_checkpoint 0 \
    --test_tflite_streaming_quantized 1 \
    mixednet \
    --pointwise_filters "64,64,64,64" \
    --repeat_in_block "1,1,1,1" \
    --mixconv_kernel_sizes "[5],[7,11],[9,15],[23]" \
    --residual_connection "0,0,0,0" \
    --first_conv_filters 32 --first_conv_kernel_size 5 --stride 3
```

**Output:**
- `trained_models/DORA/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite`
- Training metrics (recall, FA rate)
- Quantization stats

**Est. Time:** 60–90 minutes

**Status:** Ready to execute

---

### ⏳ MILESTONE 3: Model Export & Integration (PENDING)

**Objective:** Convert trained TFLite model into firmware-deployable C++ header.

**Tasks:**
- [ ] Extract `.tflite` model
- [ ] Generate C array: `xxd -i stream_state_internal_quant.tflite > DORA_model_data.cc`
- [ ] Create `DORA_model_data.h` with model dimensions and metadata
- [ ] Verify model loads in TFLite Micro without shape mismatches
- [ ] Test quantized inference: latency < 10 ms per call
- [ ] Document tensor arena size, input/output specs

**Deliverables:**
- `DORA_model_data.cc` (C byte array)
- `DORA_model_data.h` (const declarations)
- Inference latency measurement on CPU

**Est. Time:** 10 minutes

---

### ⏳ MILESTONE 4: ESP32-S3 Firmware (PENDING)

**Objective:** Deploy Streaming MixedNet on ESP32-S3 with real microphone I2S capture.

**Architecture:**
```
I2S Microphone (INMP441 or similar)
    ↓
16 kHz PCM16 capture ring buffer
    ↓
VAD model (always-on, sub-1% CPU)
    ↓
If VAD triggered:
  micro_speech preprocessor (40 features, 30 ms window, 10 ms stride)
    ↓
  Streaming MixedNet classifier
    ↓
  5-frame sliding-window decision smoothing
    ↓
  Threshold comparison
    ↓
  DETECTION EVENT → Trigger Tier 2
```

**Tasks:**
- [ ] Set up ESP-IDF project with `esp-tflite-micro` component
- [ ] Integrate I2S microphone driver (INMP441 or target mic)
- [ ] Integrate VAD model (keyword-independent, from microWakeWord)
- [ ] Integrate micro_speech feature preprocessor (C implementation, reused from microWakeWord)
- [ ] Integrate Streaming MixedNet inference loop
- [ ] Implement 5-frame sliding-window averaging + threshold
- [ ] Embed `DORA_model_data.cc` into firmware
- [ ] Build, compile, and flash to ESP32-S3
- [ ] Monitor serial output for VAD/detection events
- [ ] Measure on-device RAM usage, tensor arena size, inference latency

**Deliverables:**
- `dora_firmware/` (ESP-IDF project)
- Binary `.bin` files
- Serial log showing VAD + detection events
- RAM/CPU/latency measurements

**Est. Time:** 30 minutes (setup) + 30 minutes (testing)

---

### ⏳ MILESTONE 5: Real Microphone Testing (PENDING)

**Objective:** Verify on-device detection with actual spoken keyword.

**Test Procedure:**
1. Power ESP32-S3 with microphone connected
2. Open serial monitor
3. Speak "DORA" clearly in quiet environment
4. Verify detection event printed to console
5. Record confidence score
6. Repeat with 10 speaks, background noise, confusables
7. Log false accepts during 10 minutes of silence + background

**Metrics to Record:**
- Detection latency (ms)
- Confidence score per detection
- False accepts in 10 min idle
- Peak RAM observed
- CPU duty cycle during idle vs active

**Deliverables:**
- `HARDWARE_TEST_LOG_DORA.txt`
- Screenshots of serial output
- Confidence score distribution

**Est. Time:** 20 minutes

---

### ⏳ MILESTONE 6: Streaming Handoff (PENDING)

**Objective:** Stream audio from ESP32-S3 to cloud ASR (Vosk) via WebSocket.

**Architecture:**
```
[On-device, Tier 1]
Streaming MixedNet → DETECTION

[Pre-roll buffer, Tier 2]
Maintain 300 ms ring buffer of PCM16

[On detection]
Flush pre-roll + stream live audio
→ WebSocket connection to server

[Server, Tier 3]
Receive raw PCM16
→ Vosk ASR
→ Transcription results
→ Dashboard update
```

**Build Order (CRITICAL):**
1. **First:** Raw PCM16 WebSocket (NO compression)
   - ESP32 → raw PCM16 bytes → WebSocket → Vosk
   - Goal: Simplest possible path that works
   - Verify end-to-end streaming

2. **Second:** Opus compression (optimization, only after raw works)
   - ESP32 → Opus-encoded frames → WebSocket → server Opus decode → Vosk
   - Do NOT assume Vosk supports Opus natively

**Tasks:**
- [ ] Implement 300 ms pre-roll buffer on ESP32
- [ ] Implement WebSocket client on ESP32 (using ESP-IDF lwIP)
- [ ] Set up Vosk server (FastAPI + Vosk Python bindings)
- [ ] Stream raw PCM16 frames on keyword detection
- [ ] Receive ASR results from Vosk
- [ ] Log keyword-end timestamp, first-result timestamp → latency
- [ ] Test with 10 keyword detections, measure latency distribution

**First Milestone (Raw PCM16):**
- ESP32 client code streaming PCM16
- Vosk server receiving + transcribing
- Verified end-to-end latency < 300 ms

**Deliverables:**
- `esp32_websocket_client.c` (raw PCM16)
- `server.py` (Vosk FastAPI endpoint)
- `STREAMING_TEST_LOG_DORA.txt` (latency measurements)

**Est. Time:** 2–3 hours (complexity: WebSocket + streaming sync)

---

### ⏳ MILESTONE 7: Live Dashboard (PENDING)

**Objective:** Real-time monitoring of device state, detections, transcriptions.

**Dashboard Features:**
- Online/offline status of ESP32-S3
- Current keyword (auto-updates when model changes)
- Detection event log (timestamp, confidence)
- Keyword-end time, cloud-receive time, measured latency
- ASR partial transcript, final transcript
- Live CPU/RAM/latency metrics (if ESP32 exports them)
- Threshold adjustment (manual, persisted)

**Architecture:**
```
ESP32-S3 (emits JSON events to WebSocket)
  ↓
Server (FastAPI aggregator)
  ↓
Dashboard (real-time Chart.js / WebSocket)
```

**Tasks:**
- [ ] Create `dashboard.html` (Chart.js for latency history, event log table)
- [ ] Create `dashboard_server.py` (FastAPI WebSocket aggregator)
- [ ] Integrate dashboard with streaming server
- [ ] Subscribe to detection + ASR events
- [ ] Display keyword dynamically (read from device config)
- [ ] Test with live DORA detections

**Deliverables:**
- `dashboard.html`
- `dashboard_server.py`
- Live screenshots of dashboard

**Est. Time:** 1–2 hours

---

### ⏳ MILESTONE 8: AGNI Keyword Factory Test (PENDING)

**Objective:** Prove the entire pipeline works with a **different** keyword (no DORA hardcoding).

**Procedure:**
1. Collect/record ~30 AGNI samples (or use pre-recorded set)
2. Run full factory pipeline:
   ```bash
   ./swap_keyword.sh AGNI
   ```
3. Generate synthetic AGNI samples
4. Augment real AGNI recordings
5. Build AGNI split
6. Train Streaming MixedNet for AGNI from scratch
7. Quantize
8. Update firmware model
9. Flash ESP32-S3
10. Test: Speak "AGNI", verify detection
11. Verify device no longer detects "DORA"

**Success Criteria:**
- Same binary classifier architecture (no code changes)
- Same firmware (only model file swapped)
- Same dashboard (displays "AGNI" keyword)
- Same server (keyword-independent ASR)
- AGNI detected, DORA NOT detected

**Deliverables:**
- `trained_models/AGNI/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite`
- Updated firmware flashed with AGNI model
- Test log: "AGNI detected, DORA rejected"

**Est. Time:** 1 hour (second run is faster, with rehearsed scripts)

---

### ⏳ MILESTONE 9: Measure Keyword Swap Turnaround (PENDING)

**Objective:** Measure time from keyword announcement to flashed working device.

**Procedure:**
1. Start timer
2. Run `./swap_keyword.sh <TEST_KEYWORD>` with timing
3. Manually launch training (if not auto-launched)
4. Monitor training until completion
5. Export model + update firmware
6. Build + flash
7. Test detection on device
8. Stop timer

**Breakdown:**
- Synthetic TTS generation: 15–30 min
- Real recording: 30 min
- Augmentation + split + audit: 20–30 min
- Training: 60–90 min
- Quantize + export + firmware update: 15–20 min
- Build + flash: 5 min
- Device test + threshold tuning: 10 min
- **Total: 3.5–5 hours** (target: < 4 hours)

**Log to `KEYWORD_SWAP_TIMING.md`:**
```
Test keyword: AGNI
Start time: 2026-09-08 14:00:00
End time: 2026-09-08 17:30:00
Total: 3.5 hours

Breakdown:
  TTS: 25 min
  Recording: 30 min
  Augment/Split: 25 min
  Training: 75 min
  Export/Firmware: 20 min
  Flash/Test: 10 min
  Buffer: 10 min
```

**Est. Time:** 30 minutes (logging + analysis)

---

### ⏳ MILESTONE 10: Full System Measurement (PENDING)

**Objective:** Measure all v4.1 acceptance criteria on actual hardware.

**Measurements:**

| Metric | Method | Target | Measured |
|---|---|---|---|
| **RAM (peak)** | `esp_get_free_heap_size()` during VAD/KWS active | < 256 KB | — |
| **Idle CPU** | FreeRTOS task stats, 10 min idle | < 10% | — |
| **TP rate (recall)** | Run test set through device, count detections | ≥ 90–95% | — |
| **FA rate** | 10 min background/speech noise, count false positives | ≤ 1/hr | — |
| **KWS latency** | Firmware timestamp: audio-end to decision | < 10 ms | — |
| **Cloud latency** | Sync ESP32 + server clocks, measure keyword-end → cloud-first-byte | < 300 ms | — |
| **Model size** | File size: `stream_state_internal_quant.tflite` | < 100 KB int8 | — |

**Procedure:**
1. Enable firmware logging: timestamps for VAD, KWS decision, buffer flush, WebSocket send
2. Enable server logging: timestamp for first byte received
3. Synchronize ESP32 + server clocks (NTP or simple offset measurement)
4. Run 75 test-set audio clips through device
5. Log each detection (confidence, timing)
6. Run 10 minutes of background noise, count false accepts
7. Idle for 10 minutes, sample heap + CPU
8. Compile results into table

**Deliverables:**
- `VALIDATION_REPORT_DORA.md` (all measured values vs targets)
- Per-detection log (confidence, latency, timestamp)
- Inference latency histogram
- False-accept log

**Est. Time:** 30 minutes

---

## TOTAL TIMELINE

| Phase | Task | Status | Duration | Cumulative |
|---|---|---|---|---|
| 1 | Dataset + audit | ✅ | 15 min | 15 min |
| 2 | Train MixedNet | ⏳ | 90 min | 105 min |
| 3 | Model export | — | 10 min | 115 min |
| 4 | ESP32 firmware + setup | — | 60 min | 175 min |
| 5 | Real mic test | — | 20 min | 195 min |
| 6 | Streaming (raw PCM16) | — | 120 min | 315 min |
| 7 | Dashboard | — | 90 min | 405 min |
| 8 | AGNI factory test | — | 60 min | 465 min |
| 9 | Keyword swap timing | — | 30 min | 495 min |
| 10 | Full measurement | — | 30 min | 525 min |
| | **Buffer for fixes** | — | 120 min | **645 min** |
| | **TOTAL** | — | — | **~11 hours** |

**Remaining time before deadline (30 Sept):** 22 days

**Recommendation:** Complete all milestones by 15 September to allow 2 weeks for optimization, official negative dataset integration, and final rehearsal.

---

## SUCCESS CRITERIA (v4.1 Section 12 & 13)

### Functional
- ✅ Keyword-agnostic pipeline (no hardcoding of DORA)
- ✅ Streaming MixedNet trained from scratch (no pretrained weights)
- ✅ ESP32-S3 firmware deploys without rewrite per keyword
- ✅ Real microphone detection works
- ✅ WebSocket streaming to Vosk works
- ✅ Dashboard reflects current keyword
- ✅ AGNI keyword factory test proves repeatability

### Performance
- ✅ RAM < 256 KB (measured)
- ✅ Idle CPU < 10% (measured)
- ✅ TP rate ≥ 90–95% (measured)
- ✅ FA rate ≤ 1/hr (measured)
- ✅ Latency < 300 ms (measured)
- ✅ Model size < 100 KB int8 (measured)

### Process
- ✅ Keyword swap < 4 hours (dry-run proven)
- ✅ All measurements logged (not estimated)
- ✅ FINAL_ARCHITECTURE.md updated with v4.1 spec
- ✅ Runbook created for grand finale

---

**Document Version:** 4.1  
**Last Updated:** 8 September 2026  
**Status:** Ready for Phase 2 execution
