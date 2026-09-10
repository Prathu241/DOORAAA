# GRAND FINALE KEYWORD SWAP PROCEDURE — v4.1

**Source:** DORA_Winning_Solution_v4.1, Section 11

**Purpose:** Repeatable, timed procedure to take an ISRO-announced keyword to a flashed, working, benchmarked device within ~4 hours.

---

## PREREQUISITE CHECKLIST

Before grand finale day, verify ALL of the following are ready:

- [x] `./swap_keyword.sh` tested with DORA and AGNI (dry-runs complete)
- [x] All training scripts keyword-agnostic (--keyword parameter)
- [x] Piper models downloaded (5 ONNX files in `piper_voices/`)
- [x] Official negative datasets downloaded (if available; local fallback exists)
- [x] microWakeWord repo cloned and `pip install -e` completed
- [x] ESP32-S3 board connected and flashing verified
- [x] Vosk server environment ready (Python + FastAPI + Vosk)
- [x] Dashboard code complete and tested
- [x] All timing measurements logged for DORA + AGNI
- [x] Reserve keyword (second test keyword) already trained and benchmarked
- [x] DORA model known to work on hardware
- [x] Teams briefed on procedure and roles
- [x] Backup hardware (second ESP32-S3) available
- [x] Offline demo recording (pre-recorded DORA detections) as failsafe

---

## PROCEDURE TIMELINE

**Target:** Keyword announcement to flashed device = **< 4 hours**

### PHASE A: Synthetic Data + Recording (45 min)

**Parallel tasks (do simultaneously):**

#### Task A1: Generate Synthetic Samples (15–30 min)
```bash
python generate_keyword_dataset.py \
    --keyword <ISRO_KEYWORD> \
    --count 600 \
    --piper_models piper_voices/
```

**Output:**
- `dataset/<KEYWORD>_synthetic/` with ~600 TTS samples
- Expected WAV file count: 600 (5 voices × 9 speeds × 13 samples/speed)

**Verify:** 
```bash
ls dataset/<KEYWORD>_synthetic/ | wc -l  # should be ~600
ffprobe dataset/<KEYWORD>_synthetic/<SAMPLE>.wav | grep -E "sample_rate|channels"  # verify 16kHz, mono
```

#### Task A2: Record Real Samples (30 min)
```bash
python record_keyword.py \
    --keyword <ISRO_KEYWORD> \
    --speaker spk001 spk002 spk003 spk004 \
    --count 25 \
    --output dataset/<KEYWORD>_real/
```

**Output:**
- `dataset/<KEYWORD>_real/` with ~20–30 real samples
- Multiple speakers recommended

**Verify:**
```bash
ls dataset/<KEYWORD>_real/ | wc -l  # expect 20–30
```

**Time check:** After 45 min, you should have:
- [ ] ~600 synthetic samples
- [ ] ~20–30 real samples

---

### PHASE B: Data Preparation (30 min)

#### Task B1: Augment Real Samples (20 min)
```bash
python augment_real.py \
    --keyword <ISRO_KEYWORD> \
    --input dataset/<ISRO_KEYWORD>_real/ \
    --output dataset/<ISRO_KEYWORD>_augmented/ \
    --multiplier 4
```

**Output:**
- `dataset/<KEYWORD>_augmented/` with 4× augmented variants

**Verify:**
```bash
ls dataset/<KEYWORD>_augmented/ | wc -l  # expect 4 × (real count)
```

#### Task B2: Generate Hard Negatives (10 min)
```bash
python generate_hard_negatives.py \
    --keyword <ISRO_KEYWORD> \
    --count 150 \
    --output dataset/<KEYWORD>_hard_negatives/

# Merge hard negatives into unknown_wav
cp dataset/<KEYWORD>_hard_negatives/*.wav dataset/unknown_wav/
```

**Output:**
- `dataset/<KEYWORD>_hard_negatives/` with ~150 phonetic confusables

**Time check:** After 30 min, you should have:
- [ ] Augmented real samples
- [ ] Hard negatives merged

**Cumulative time: ~75 min**

---

### PHASE C: Split & Validation (30 min)

#### Task C1: Build Train/Val/Test Split (10 min)
```bash
python prepare_dataset.py --keyword <ISRO_KEYWORD>
```

**Output:**
- `dataset/split/train/<KEYWORD>/`
- `dataset/split/val/<KEYWORD>/`
- `dataset/split/test/<KEYWORD>/`

**Verify (CRITICAL):**
```bash
python audit_dataset.py --keyword <ISRO_KEYWORD>
# Must pass with zero leakage
```

#### Task C2: Generate Training YAML (5 min)
```bash
python make_training_config.py \
    --keyword <ISRO_KEYWORD> \
    --steps 15000 \
    --use_official_negatives \
    --output training_parameters_<ISRO_KEYWORD>.yaml
```

**Output:**
- `training_parameters_<KEYWORD>.yaml`

#### Task C3: Review Audit Output (15 min)
- Verify zero train/val/test overlap
- Check format (16 kHz, mono, PCM_16)
- Note any warnings (negatives insufficient, etc.)
- **Do NOT proceed if audit fails.**

**Time check:** After 30 min:
- [ ] Split built
- [ ] Audit passed
- [ ] Training YAML ready

**Cumulative time: ~105 min (1 h 45 min)**

---

### PHASE D: Training (90 min)

**Operator:** Begin training manually (script intentionally does NOT auto-launch).

```bash
cd microWakeWord

python -m microwakeword.model_train_eval \
    --training_config "../training_parameters_<KEYWORD>.yaml" \
    --train 1 \
    --restore_checkpoint 0 \
    --test_tf_nonstreaming 0 \
    --test_tflite_nonstreaming 0 \
    --test_tflite_nonstreaming_quantized 0 \
    --test_tflite_streaming 0 \
    --test_tflite_streaming_quantized 1 \
    --use_weights best_weights \
    mixednet \
    --pointwise_filters "64,64,64,64" \
    --repeat_in_block "1,1,1,1" \
    --mixconv_kernel_sizes "[5],[7,11],[9,15],[23]" \
    --residual_connection "0,0,0,0" \
    --first_conv_filters 32 \
    --first_conv_kernel_size 5 \
    --stride 3
```

**Monitoring:**
- Watch for convergence (loss decreases, accuracy improves)
- Training step counter should reach 15,000
- Expected output: `trained_models/<KEYWORD>/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite`

**Time check:** Training takes 60–90 min (variable by CPU, data size).

**During training:**
- [ ] Prepare ESP32-S3: connect USB, open serial terminal
- [ ] Pre-stage Vosk server startup script
- [ ] Pre-stage dashboard on browser
- [ ] Brief team on detection demo

**Cumulative time: ~195 min (3 h 15 min)**

---

### PHASE E: Model Export & Firmware Update (20 min)

#### Task E1: Generate C++ Model Array (5 min)
```bash
cd /path/to/repo

MODEL_PATH="trained_models/<KEYWORD>/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite"

xxd -i "$MODEL_PATH" > "${KEYWORD}_model_data.cc"

# Verify
ls -lh "${KEYWORD}_model_data.cc"  # should exist, >10 KB
head -20 "${KEYWORD}_model_data.cc"  # verify content
```

**Output:**
- `<KEYWORD>_model_data.cc` (C byte array)

#### Task E2: Update Firmware (10 min)
1. Copy `<KEYWORD>_model_data.cc` into firmware project
2. Update firmware `CMakeLists.txt` or model inclusion to use new model
3. Rebuild firmware:
   ```bash
   cd dora_firmware
   idf.py fullclean
   idf.py build
   ```

**Output:**
- Updated `.bin` file

**Verify:**
```bash
ls -lh dora_firmware/build/*.bin  # should be 500 KB – 1 MB
```

#### Task E3: Flash to ESP32-S3 (5 min)
```bash
idf.py flash
```

**Monitor serial output for:**
```
[I] MixedNet model loaded, size: XXXXX bytes
[I] VAD model loaded
[I] Waiting for audio input...
```

**Time check:** After 20 min, device should be flashed and reporting ready.

**Cumulative time: ~215 min (3 h 35 min)**

---

### PHASE F: Live Detection Demo (15–20 min)

#### Task F1: Speak Keyword (5 min)
1. Open serial terminal or dashboard
2. Speak the keyword CLEARLY
3. Watch for detection event:
   ```
   [D] DETECTION: confidence=0.92, latency=234ms
   [D] Streaming audio to cloud ASR...
   [D] ASR result: "<KEYWORD>"
   ```

4. Adjust threshold if needed (if too many false accepts or too few true positives)

#### Task F2: Verify Dashboard (5 min)
1. Open dashboard in browser
2. Watch for:
   - Device online status
   - Keyword displayed: `<KEYWORD>`
   - Detection event logged
   - Latency measurement displayed
   - ASR partial + final transcript shown

#### Task F3: Test Confusables (5–10 min)
1. Speak phonetically similar words (if any exist for the keyword)
2. Verify NO false detection
3. Speak the keyword again
4. Verify detection

**Time check:** After ~20 min, demo is complete.

**Cumulative time: ~235 min (3 h 55 min)**

---

### PHASE G: Benchmark & Documentation (Optional, if time permits)

If under 4 hours, perform quick benchmarks:

```bash
# On ESP32-S3, 10 min idle listening
# Log peak RAM, CPU duty cycle, any false accepts

# Run test set
# Measure recall + FA rate

# Measure latency (keyword-end to cloud-first-byte)
```

Log results in `FINAL_VALIDATION_<KEYWORD>.md`.

---

## CONTINGENCY PLANS

### Training Fails
- **Mitigation:** Have DORA model pre-trained and ready to revert to
- **Action:** Copy DORA model back to firmware, re-flash
- **Cost:** ~10 minutes to revert

### ESP32-S3 Flash Fails
- **Mitigation:** Have backup ESP32-S3 board
- **Action:** Flash backup board with new model
- **Cost:** ~5 minutes

### Keyword Announcement Unclear / Repeated Quickly
- **Mitigation:** Clarify with judges before starting pipeline
- **Action:** If repeat: re-run PHASES A–F with new keyword
- **Cost:** Another ~4 hours

### Wi-Fi/Network Issues During Demo
- **Mitigation:** Offline demo recording (pre-recorded DORA detections on browser, mock ASR)
- **Action:** Play video to judges showing device + dashboard + detection
- **Cost:** ~5 minutes (pre-recorded)

---

## ROLE ASSIGNMENTS

| Role | Responsibility | Backup |
|---|---|---|
| **Data Lead** | A1 (synthetic), A2 (recording), B1 (augment) | — |
| **Training Lead** | C1–C3 (split/audit), D (training) | Monitor CPU/loss |
| **Firmware Lead** | E1–E3 (model export, firmware, flash) | Prepare backup board |
| **Demo Lead** | F (live detection + dashboard) | Failsafe: offline recording |
| **Timekeeper** | Track cumulative time, alert on delays | — |

---

## FINAL CHECKLIST (BEFORE ISRO ANNOUNCES)

- [ ] All prerequisites verified
- [ ] All scripts tested (--keyword parameter works)
- [ ] Piper models present
- [ ] ESP32-S3 connectivity confirmed
- [ ] Vosk server environment ready
- [ ] Dashboard open and ready
- [ ] Reserve keyword (AGNI) trained and benchmarked
- [ ] DORA model working on device
- [ ] Offline demo recording queued
- [ ] All team members know their role
- [ ] Stopwatch ready
- [ ] Backup hardware ready
- [ ] Network stable

---

## SUCCESS CRITERIA

✅ **Keyword announced**
→ Timer starts

✅ **Phase A:** Synthetic + real samples ready
→ Timer: ~45 min

✅ **Phase B:** Augmentation + hard negatives
→ Timer: ~30 min cumulative

✅ **Phase C:** Split + audit passes
→ Timer: ~30 min cumulative

✅ **Phase D:** Training completes
→ Timer: ~105 min cumulative

✅ **Phase E:** Firmware flashed
→ Timer: ~120 min cumulative

✅ **Phase F:** Live detection + dashboard working
→ Timer: **< 240 min (4 hours)**

✅ **Judges see:** Device detecting new keyword, ASR transcribing, dashboard live-updating

---

## DRESS REHEARSAL (BEFORE GRAND FINALE)

Run this entire procedure 1–2 weeks before finals using "AGNI" as test keyword:

```bash
# Day before grand finale
./swap_keyword.sh AGNI --dryrun  # show what would run
./swap_keyword.sh AGNI           # full rehearsal

# Time the entire sequence
# Document any bottlenecks
# Optimize if possible
# Report: "AGNI swap: X hours Y minutes"
```

**Goal:** Prove < 4 hours with AGNI, so final keyword is not the first test.

---

**Document Version:** v4.1  
**Status:** Ready for grand finale  
**Last Updated:** 8 September 2026
