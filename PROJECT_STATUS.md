# DORA v4.1 — PROJECT STATUS & EXECUTION PLAN

**Document Version:** v4.1 (aligned with DORA_Winning_Solution_v4.1.pdf)

**Current Date:** 8 September 2026

**Project:** SIH26172 — Low Latency and Efficient Voice Activator for Edge Devices

**Organization:** ISRO

**Deadline:** 30 September 2026

---

## EXECUTIVE SUMMARY

The project has successfully completed dataset preparation (real, augmented, synthetic samples ready). The next phase is **training, quantization, firmware deployment, streaming integration, and end-to-end system validation**.

This document reflects the **FINAL ARCHITECTURE FROM v4.1** and serves as the single source of truth for implementation order.

---

## PART 1: WHAT EXISTS TODAY

### Dataset — COMPLETE FOR DORA DEVELOPMENT

| Component | Location | Count | Status |
|---|---|---|---|
| **Real recordings** | `dataset/DORA_real/` | 100 WAV | ✓ Cleaned (duplicate removed) |
| **Augmented** (4×) | `dataset/DORA_augmented/` | 400 WAV | ✓ PCM_16, reverb bug fixed |
| **Synthetic (Piper)** | `dataset/DORA_synthetic/` | 585 WAV | ✓ 5 voices, 9 speeds, 16kHz PCM_16 |
| **Total positives** | — | **1,085 WAV** | Ready for split |
| **Hard negatives** | `dataset/DORA_hard_negatives/` | 144 WAV | ✓ Phonetic confusables |
| **Background noise** | `dataset/background_wav/` | 160 WAV | ✓ Reusable |
| **Unknown speech** | `dataset/unknown_wav/` | 323 WAV | ✓ Speech Commands + Common Voice |
| **Total negatives** | — | **~483 WAV** | ~12 min, not final |

### Code & Tools — COMPLETE

| Component | Location | Status |
|---|---|---|
| **Dataset factory scripts** | `augment_real.py`, `prepare_dataset.py`, `generate_keyword_dataset.py`, `generate_hard_negatives.py`, `audit_dataset.py` | ✓ Keyword-agnostic, fixes applied |
| **Configuration generator** | `make_training_config.py` | ✓ Generates training_parameters_<KW>.yaml |
| **Keyword swap orchestrator** | `swap_keyword.sh` | ✓ Full pipeline automation (v4.1 aligned) |
| **microWakeWord repo** | `microWakeWord/` | ✓ Clone present |
| **Piper models** | `piper_voices/` | ✓ 5 ONNX models, 300+ MB total |

### Architecture Source — v4.1 SPECIFICATIONS

- **Design document:** `DORA_Winning_Solution_v4.1.pdf` (attached, embedded herein)
- **Architecture:** Streaming MixedNet (microWakeWord v2)
- **Framework:** TensorFlow Lite for Microcontrollers
- **Target hardware:** ESP32-S3 (256 KB SRAM budget)
- **Final keyword:** TBD, provided by ISRO at grand finale
- **Development keyword:** DORA (proof-of-concept and rehearsal)

---

## PART 2: WHAT IS MISSING

| Milestone | Status | Dependency | Est. Time |
|---|---|---|---|
| **MILESTONE 1: Dataset split (train/val/test)** | ✅ COMPLETE | None | 5 min |
| **MILESTONE 2: Training on DORA** | ⏳ IN PROGRESS | Split complete | 60–90 min |
| **MILESTONE 3: Quantization (int8 streaming TFLite)** | ✗ NOT STARTED | Training done | 10 min |
| **MILESTONE 4: ESP32-S3 firmware (micro_speech base)** | ✗ NOT STARTED | TFLite model | 30 min (setup) |
| **MILESTONE 5: Real microphone test** | ✗ NOT STARTED | Firmware flashed | 20 min |
| **MILESTONE 6: Raw PCM16 → WebSocket → Vosk** | ✗ NOT STARTED | Firmware + server | 2–3 hours |
| **MILESTONE 7: Dashboard** | ✗ NOT STARTED | Server ready | 1–2 hours |
| **MILESTONE 8: AGNI keyword factory test** | ✗ NOT STARTED | DORA system complete | 1 hour |
| **MILESTONE 9: Keyword swap timing** | ✗ NOT STARTED | AGNI test complete | 30 min |
| **MILESTONE 10: Full hardware measurement** | ✗ NOT STARTED | All systems ready | 30 min |

---

## PART 3: CRITICAL BLOCKERS & CLARIFICATIONS

### Official Negative Datasets

**Status:** `negative_datasets/dinner_party.zip` present but **INCOMPLETE** (272 MB / ~424 MB expected).

**Impact:** 
- Dataset quality audit will warn about limited negative coverage.
- Training will proceed with ~12 min of local negatives.
- Final evaluation model should use full official negatives before submission.

**Action:** Re-download when time permits. Do NOT block DORA V0 training.

### Hardware Access

**ESP32-S3 board:** Not yet confirmed connected/present in this inspection.

**Action:** Before firmware flashing, verify ESP32-S3 is accessible via:
```bash
idf.py list-serial-ports
```

### Python Environment

**microWakeWord installation:** Must be installed in editable mode:
```bash
cd microWakeWord/
pip install -e .
```

**Verification:** `python -c "import microwakeword; print(microwakeword.__version__)"`

---

## PART 4: EXACT EXECUTION ORDER (v4.1 Compliant)

### ✅ PHASE 1: PREPARE SPLIT (5 min)

**Command:**
```bash
python prepare_dataset.py --keyword DORA
```

**Output:**
- `dataset/split/train/DORA/` — ~70% positives (~760 WAV)
- `dataset/split/val/DORA/` — ~15% positives (~160 WAV)
- `dataset/split/test/DORA/` — ~15% positives (~165 WAV)
- `dataset/split/train/neg/` — negatives (shuffled)

**Validation:**
```bash
python audit_dataset.py --keyword DORA
```

Expected result: ✓ No leakage, format correct, counts match.

---

### ✅ PHASE 2: TRAIN STREAMING MIXEDNET (60–90 min)

**Command:**
```bash
cd microWakeWord
python -m microwakeword.model_train_eval \
    --training_config ../training_parameters_DORA.yaml \
    --train 1 \
    --restore_checkpoint 0 \
    --test_tflite_streaming_quantized 1 \
    mixednet \
    --pointwise_filters "64,64,64,64" \
    --repeat_in_block "1,1,1,1" \
    --mixconv_kernel_sizes "[5],[7,11],[9,15],[23]" \
    --residual_connection "0,0,0,0" \
    --first_conv_filters 32 \
    --first_conv_kernel_size 5 \
    --stride 3
```

**Output:**
- `trained_models/DORA/` directory tree
- `trained_models/DORA/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite`

**Validation:**
```bash
ls -lh trained_models/DORA/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite
# Expected: 30–80 KB
```

---

### ✅ PHASE 3: QUANTIZATION & MODEL EXPORT (10 min)

The quantization happens **during training** via the `--test_tflite_streaming_quantized 1` flag.

**Verify output:**
```bash
file trained_models/DORA/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite
# Expected: data
```

**Generate C++ array for firmware:**
```bash
xxd -i trained_models/DORA/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite > DORA_model_data.cc
```

---

### ✅ PHASE 4: ESP32-S3 FIRMWARE (30 min setup)

**Prerequisites:**
- ESP-IDF v5.1 or later installed
- `esp-tflite-micro` component available
- `DORA_model_data.cc` generated

**Structure:**
```
dora_firmware/
├── CMakeLists.txt
├── main/
│   ├── CMakeLists.txt
│   └── main.c  (or .cpp)
├── idf_component.yml (adds esp-tflite-micro)
└── models/
    ├── DORA_model_data.cc
    └── DORA_model_data.h
```

**Build & Flash:**
```bash
cd dora_firmware
idf.py build
idf.py flash
idf.py monitor
```

**Verification on device:**
- Console shows: `MixedNet model loaded, size: XXX bytes`
- Microphone captures audio
- VAD detects voice
- MixedNet runs per frame

---

### ✅ PHASE 5: REAL MICROPHONE TEST (20 min)

**Test procedure:**
1. Connect INMP441 I2S microphone to ESP32-S3
2. Flash firmware
3. Open serial monitor
4. Speak keyword: "DORA"
5. Watch for: `DETECTION: DORA confidence 0.85` (example)

**Measurements to log:**
- Detection latency: ~10 ms (from audio capture end to model decision)
- False accepts in 10 minutes of background noise/speech
- RAM free during execution
- CPU duty cycle (measured via task stats if available)

---

### ✅ PHASE 6: STREAMING HANDOFF (2–3 hours)

**Architecture:**
```
ESP32-S3 (mic → VAD → MixedNet → 5-frame smoothing)
    ↓ (on detection)
300 ms pre-roll buffer + live audio stream
    ↓
WebSocket (ESP32 → Server)
    ↓
Vosk ASR (server-side transcription)
    ↓
Dashboard telemetry
```

**First milestone: Raw PCM16 WebSocket**

ESP32 firmware must:
1. Maintain 300 ms ring buffer of PCM16
2. On detection: flush buffer + send raw PCM16 frames
3. Connect to WebSocket server at `ws://server_ip:8765/audio`

Server must:
1. Listen on WebSocket
2. Accept PCM16 frames
3. Send to Vosk
4. Return ASR results

**Do NOT use Opus yet.** Get raw PCM working first.

---

### ✅ PHASE 7: VOSK SERVER (1–2 hours)

**Server skeleton:**
```python
# server.py
from fastapi import FastAPI, WebSocket
from vosk import Model, KaldiRecognizer
import json

app = FastAPI()

# Load Vosk model (small English model)
# vosk-model-small-en-us
model = Model("vosk_model_path")

@app.websocket("/audio")
async def audio_stream(websocket: WebSocket):
    await websocket.accept()
    recognizer = KaldiRecognizer(model, 16000)
    
    while True:
        data = await websocket.receive_bytes()  # PCM16
        if recognizer.AcceptWaveform(data):
            result = recognizer.Result()
            await websocket.send_text(result)
        else:
            result = recognizer.PartialResult()
            await websocket.send_text(result)
```

**Deploy:**
```bash
pip install fastapi uvicorn vosk
python server.py --port 8765
```

---

### ✅ PHASE 8: DASHBOARD (1–2 hours)

**Web dashboard must show:**
- Device online/offline status
- Current keyword (DORA / AGNI / etc.)
- Wake-word detection event with confidence
- Timestamp: keyword-end
- Timestamp: cloud ASR receive
- Latency measurement
- ASR partial + final transcript
- Connection status

**Keyword-agnostic design:**
```javascript
// Load config from server
fetch('/api/config')
  .then(r => r.json())
  .then(cfg => {
    document.getElementById('keyword').textContent = cfg.keyword;
    // Dashboard updates dynamically
  })
```

---

### ✅ PHASE 9: AGNI KEYWORD FACTORY TEST (1 hour)

**Objective:** Prove the pipeline works with a **DIFFERENT** keyword.

**Command:**
```bash
./swap_keyword.sh AGNI
```

**Expected sequence:**
1. Check for `dataset/AGNI_real/` or record new samples
2. Generate ~600 AGNI synthetic samples (Piper)
3. Generate AGNI hard negatives
4. Augment real AGNI recordings
5. Build split (train/val/test)
6. Run audit
7. Generate training YAML
8. **Print training command** (do NOT auto-launch)

**Manual training:**
```bash
cd microWakeWord
python -m microwakeword.model_train_eval \
    --training_config ../training_parameters_AGNI.yaml \
    --train 1 \
    --restore_checkpoint 0 \
    --test_tflite_streaming_quantized 1 \
    mixednet [same architecture flags]
```

**Deploy to same ESP32-S3:**
```bash
xxd -i trained_models/AGNI/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite > AGNI_model_data.cc
# Update firmware to use AGNI_model_data.cc instead of DORA_model_data.cc
# Rebuild and flash
```

**Verify:** Device now detects AGNI, not DORA.

---

### ✅ PHASE 10: MEASURE COMPLETE KEYWORD SWAP TIME

**Time the entire sequence from keyword announcement to flashed working device:**

```
Start time: T0
├─ TTS synthesis: 15–30 min
├─ Recording: 30 min
├─ Augmentation + split: 20–30 min
├─ Training: 60–90 min
├─ Quantization + export: 10 min
├─ Model update + firmware build + flash: 15–20 min
└─ Test on device: 5–10 min
End time: T1

Total: ~3.5–5 hours (first attempt; can optimize)
Target: <4 hours (requires optimization and rehearsal)
```

**Log actual times in `KEYWORD_SWAP_TIMING.md`.**

---

### ✅ PHASE 11: FULL SYSTEM MEASUREMENT

**Record ALL metrics on actual ESP32-S3 with Vosk server running:**

| Metric | Target | Method | Measured |
|---|---|---|---|
| **Peak RAM** | <256 KB | `free_heap` at idle + during KWS | — |
| **Idle CPU** | <10% | Task statistics | — |
| **Model size (flash)** | <100 KB int8 | `ls -l .tflite` | — |
| **Inference latency** | <10 ms | Timestamp in firmware | — |
| **Recall (TP)** | ≥90% | Test set evaluation | — |
| **False accepts** | ≤1/hr | 10 min idle noise test | — |
| **Keyword-end → cloud-ASR** | <300 ms | Synchronized clocks | — |
| **Keyword swap turnaround** | <4 hr | End-to-end timing | — |

---

## PART 5: DOCUMENTATION TO GENERATE

After PHASE 11, create:

### 1. **PROJECT_STATUS.md** (this file, updated)
- Current state
- What works
- What failed & why
- Next steps

### 2. **FINAL_ARCHITECTURE.md**
Copy from v4.1, add measured values:
- Exact microphone pinout (I2S)
- Model file sizes
- Tensor arena size
- Network latency breakdown

### 3. **MODEL_CARD_DORA.md**
```markdown
# DORA Wake-Word Model Card

**Keyword:** DORA
**Training date:** [DATE]
**Framework:** TensorFlow Lite Micro
**Model architecture:** Streaming MixedNet

## Dataset

| Category | Count | Source |
|---|---|---|
| Real positives (train) | NNN | OSCode drive |
| Synthetic (Piper TTS) | NNN | 5 voices, 9 speeds |
| Augmentation | NNN | Noise, pitch, speed |
| Hard negatives | NNN | Phonetic confusables |
| Background | NNN | MUSAN, DEMAND, local |

## Metrics

- **Recall (TP rate):** XX%
- **False accepts/hour:** X.X
- **Model size:** XX KB (int8)
- **Inference latency:** X ms (ESP32-S3)
- **RAM (peak):** XXX KB
```

### 4. **HACKATHON_RUNBOOK.md**
```markdown
# SIH Grand-Finale Keyword Swap Procedure

## Command
```bash
./swap_keyword.sh <ISRO_KEYWORD>
```

## Steps (automated, but monitorable)
1. Check prerequisites (piper, ffmpeg, microWakeWord)
2. Generate synthetic samples (~30 min)
3. Record real samples (~30 min)
4. Augment + split + audit (~30 min)
5. Train MixedNet (~90 min, operator watches)
6. Quantize + export + firmware update (~20 min)
7. Flash ESP32-S3 (~5 min)
8. Verify device detects keyword (~10 min)

**Total: ~4–5 hours**
```

### 5. **VALIDATION_REPORT.md**
Lists all acceptance criteria from v4.1 and final measured values.

---

## PART 6: NEXT IMMEDIATE ACTION

### **NOW: Execute PHASE 1**

```bash
cd /c/Users/PRATHAM/DORA_MIXED-net
python prepare_dataset.py --keyword DORA
python audit_dataset.py --keyword DORA
```

Then report back with:
1. Split counts (train/val/test)
2. Audit pass/fail
3. Any missing files or errors

After Phase 1 passes, execute PHASE 2 (training).

---

## PART 7: RULES FROM v4.1 (DO NOT BREAK)

1. ✓ **Streaming MixedNet is final.** No other architecture.
2. ✓ **Train from scratch.** No pretrained global weights.
3. ✓ **Keyword-agnostic firmware.** Only model file changes.
4. ✓ **Raw PCM16 first.** Opus after raw works.
5. ✓ **Measured not estimated.** No claimed metrics until verified on hardware.
6. ✓ **DORA is development only.** ISRO keyword is final deliverable.
7. ✓ **Dry-run before finale.** AGNI test proves factory.
8. ✓ **No hardcoded DORA** in any production script/firmware.
9. ✓ **Vosk unchanged.** Keyword-independent ASR.
10. ✓ **Dashboard dynamic.** Reflects current keyword from device config.

---

**Document prepared:** 8 September 2026  
**Next update:** After Phase 1 (split) completion  
**Final submission deadline:** 30 September 2026
