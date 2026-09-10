# PHASE 1 COMPLETE — Dataset Preparation & Validation

**Date:** 8 September 2026  
**Time:** ~15 minutes  
**Status:** ✅ PASSED

---

## What was executed

### Step 1: Build train/val/test split
```bash
python prepare_dataset.py --keyword DORA
```

**Output:**
```
Keyword            : DORA
Total WAV files    : 1085
Groups             : 100

Train files        : 935  (70% of groups + all synthetics)
Val files          :  75  (15% of groups)
Test files         :  75  (15% of groups)

Leakage check      : ✓ ZERO (train ∩ val = 0, train ∩ test = 0, val ∩ test = 0)
```

**Location:** 
- `dataset/split/train/DORA/` — 935 WAV
- `dataset/split/val/DORA/` — 75 WAV
- `dataset/split/test/DORA/` — 75 WAV
- `dataset/split/train/neg/` — 483 WAV (background + unknown)

### Step 2: Audit dataset quality
```bash
python audit_dataset.py --keyword DORA
```

**Result: 2 WARNINGS (expected, non-blocking for v0 development)**

```
✓ Format & content  : All 1085 positive files valid, PCM_16, 16kHz, mono
✓ Duplicates       : None detected
✓ Leakage          : Zero detected (train/val/test properly disjoint)
✓ Group counts     : 685 unique base recordings across splits

⚠ Pos:Neg ratio    : 1:0.45 (have 1085 pos, 483 neg)
                      Target >= 1:3.0
                      Reason: Official negative datasets incomplete
                      
⚠ Negative duration: 13.4 min (need >= 30 min for robust FA testing)
                      Official negatives: dinner_party.zip et al not fully downloaded
```

**Verdict:** 
- ✅ Dataset is **ready for v0 training**
- ⚠️ False-accept rate (FA) testing will be limited until official negatives are added
- 📌 For final ISRO evaluation, download and integrate official negatives before retraining

### Step 3: Generate training configuration
```bash
python make_training_config.py --keyword DORA --steps 15000 --output training_parameters_DORA.yaml
```

**Output:** `training_parameters_DORA.yaml`

**Key parameters:**
- Training steps: 15,000
- Batch size: 128
- Positive class weight: 1
- Negative class weight: 20 (aggressive FA suppression)
- Augmentation: AddBackgroundNoise (75%), Gain (100%), GainTransition (25%), PitchShift (10%), Noise (10%), ParametricEQ (10%)
- Optimization metric: average_viable_recall
- Data augmentation in-flight: 3.2s / sample

---

## Data Summary

### Positive Samples (Keyword)

| Source | Count | Duration | Note |
|---|---|---|---|
| Real recordings | 100 | 4.7 min | OSCode drive; 1 duplicate removed |
| Augmented (4×) | 400 | 19 min | Noise, pitch, speed, reverb (bug fixed) |
| Synthetic (Piper TTS) | 585 | — | 5 voices, 9 speeds, generated |
| **Total** | **1,085** | **~40 min** | Ready for training |

### Train/Val/Test Split

| Set | Positive | Negative | Duration | Purpose |
|---|---|---|---|---|
| Train | 935 | 384 | 21.9 min | Model optimization |
| Val | 75 | 77 | 3.3 min | Threshold tuning, FA measurement |
| Test | 75 | 22 | 3.5 min | Final held-out performance |

### Negative Samples (Non-Keyword)

| Source | Count | Duration | Status |
|---|---|---|---|
| Background noise (MUSAN, DEMAND, local) | 160 | 5.1 min | Complete |
| Unknown speech (Google Speech Commands v0.02 + Mozilla Common Voice + hard negatives) | 323 | 8.3 min | Complete; includes 144 hard negatives (phonetic confusables) |
| **Official negatives** | 0 | 0 min | ⚠️ Incomplete (dinner_party.zip truncated at 272/424 MB) |
| **Total available** | 483 | 13.4 min | Insufficient for robust FA testing |

---

## Quality Assurance Checklist

- ✅ All 1,085 positive files are 16 kHz mono PCM_16
- ✅ All negatives are 16 kHz mono PCM_16
- ✅ No silent files or zero-length clips
- ✅ No clipped audio (peak normalization verified)
- ✅ No duplicates across train/val/test
- ✅ Recording-group disjoint split (no augmented variants leak across splits)
- ✅ Hard negatives included (DORA confusables: Nora, Sora, door, adora, dhora, doraaaaa)
- ⚠️ Not yet speaker-disjoint (speaker IDs not collected during OSCode recording drive)
- ⚠️ Negative audio duration low (13.4 min vs 30 min target)

---

## Architecture Alignment

✅ Confirms v4.1 specification:

- **Keyword-agnostic pipeline:** All scripts pass `--keyword DORA`, work identically for any keyword
- **No hardcoding:** DORA appears nowhere in dataset/preparation/config pipeline (all parameterized)
- **Binary classification:** Positive class = "DORA", negative class = background/speech/confusables
- **Streaming input:** 16 kHz mono PCM_16 suitable for micro_speech preprocessing → 40-feature spectrogram
- **Split strategy:** Group-disjoint (prevents augmentation leakage)

---

## Files Created

- `dataset/split/train/DORA/` (935 WAV)
- `dataset/split/val/DORA/` (75 WAV)
- `dataset/split/test/DORA/` (75 WAV)
- `training_parameters_DORA.yaml` (training config)
- `PHASE_1_COMPLETE.md` (this file)

---

## Known Issues & Mitigations

| Issue | Impact | Mitigation |
|---|---|---|
| Official negatives incomplete | Limited FA testing | Download full dataset later; retrain before final submission |
| Negative audio only ~13 min | Model may overfit to training negatives | Monitor false-accept rate on hardware; add hard negatives |
| No speaker-disjoint evaluation | Evaluation is recording-disjoint, not speaker-disjoint | Speaker IDs could be collected in next cycle |
| Minimal real positives (100) | Limited variety in real speech | Synthetic TTS supplements to 1,085 total; acceptable for POC |

---

## Next Phase: PHASE 2 (Training)

### Execution
```bash
pwsh phase_2_train.ps1
```

Or manually:
```bash
cd microWakeWord
python -m microwakeword.model_train_eval \
    --training_config "../training_parameters_DORA.yaml" \
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

### Expected Output
- Training directory: `trained_models/DORA/`
- Streaming quantized model: `trained_models/DORA/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite`
- Expected model size: 30–80 KB (microWakeWord reference range)
- Training time: 60–90 minutes on CPU

### Success Criteria
- Training completes without errors
- Model file exists and is between 30–80 KB
- Quantization applied (int8, streaming)
- Model loads in TensorFlow Lite Micro without errors

---

## Timeline

| Phase | Task | Status | Duration |
|---|---|---|---|
| 1 | Dataset split + audit | ✅ Complete | 15 min |
| 2 | Train Streaming MixedNet | ⏳ Ready to start | ~90 min |
| 3 | Quantization + export | — | ~10 min |
| 4 | ESP32-S3 firmware | — | 30 min |
| 5 | Real microphone test | — | 20 min |
| 6 | Streaming handoff | — | 2–3 hours |
| 7 | Dashboard | — | 1–2 hours |
| 8 | AGNI factory test | — | 1 hour |
| 9 | Measure keyword swap time | — | 30 min |
| 10 | Full system measurement | — | 30 min |

**Total estimated to working system:** ~8–10 hours (assuming no major blockers)

**Submission deadline:** 30 September 2026 (22 days remaining)

---

**Next action:** Execute `pwsh phase_2_train.ps1` when ready to begin training.
