# Grand Finale Playbook — ISRO Keyword Swap in Under 4 Hours
## Document 13 — SIH26172 | DORA

---

## 1. The Grand Finale Scenario

At the Grand Finale, ISRO will announce a keyword (e.g., "AGNI") that you have **never seen before**. You must:

1. Build a complete training dataset for the new keyword
2. Train, quantise, and evaluate the model
3. Flash the firmware with the new model
4. Demonstrate live detection to the judges

**Time budget: 4 hours maximum. DORA is designed to complete this in under 4 hours.**

---

## 2. What You Have When ISRO Announces

| Asset | Status | Notes |
|---|---|---|
| Piper voice models (5 voices) | ✓ Ready on disk | `piper_voices/` |
| Negative datasets (~4,300 samples) | ✓ Ready on disk | `dataset/unknown/`, `dataset/background/` |
| Training environment | ✓ Ready | `microWakeWord/` cloned + dependencies installed |
| Firmware project | ✓ Ready | Only model file needs replacement |
| Server + dashboard | ✓ Ready | No changes needed |
| Keyword samples | ✗ Zero | Must generate immediately |

---

## 3. Dataset Build for a Brand-New Keyword

| Source | Script | Samples | Time |
|---|---|---|---|
| Piper TTS (5 voices × 9 speeds) | `generate_keyword_dataset.py --keyword AGNI` | ~550 | 15 min (automated) |
| Manual team recordings (6 speakers × 20) | `record_keyword.py --keyword AGNI` | ~120 | 30 min |
| Augmentation of real recordings (4×) | `augment_real.py --keyword AGNI` | ~480 | 5 min (automated) |
| **Total positives** | | **~1,150** | **~50 min** |
| Negatives (reuse existing) | Already on disk | ~4,300 | 0 min |
| **Grand total** | | **~5,450** | **~50 min** |

---

## 4. Detailed Swap Timeline

```
T+0:00  ISRO announces keyword (e.g., "AGNI")

T+0:02  START: python generate_keyword_dataset.py --keyword AGNI --count 600
        (runs in background — 15 minutes, fully automated)

T+0:05  Team splits into 6 people for simultaneous recording:
        Person 1: python record_keyword.py --keyword AGNI --speaker spk001 --count 20
        Person 2: python record_keyword.py --keyword AGNI --speaker spk002 --count 20
        Person 3: python record_keyword.py --keyword AGNI --speaker spk003 --count 20
        Person 4: python record_keyword.py --keyword AGNI --speaker spk004 --count 20
        Person 5: python record_keyword.py --keyword AGNI --speaker spk005 --count 20
        Person 6: python record_keyword.py --keyword AGNI --speaker spk006 --count 20
        (Each person takes ~5 minutes — all run in parallel)

T+0:35  Recordings done. 120 real samples collected.

T+0:40  python augment_real.py --keyword AGNI
        (5 minutes, automated)

T+0:45  TTS synthesis complete (was running in background since T+0:02)
        python prepare_dataset.py --keyword AGNI
        (merges synthetic + real + augmented, speaker-splits)

T+0:50  START TRAINING:
        cd microWakeWord
        python train.py --keyword AGNI \
          --positive_dir ../dataset/split/train/AGNI \
          --negative_dir ../dataset/unknown \
          --background_dir ../dataset/background \
          --epochs 80 --batch_size 64 --output_dir ../models/

T+2:30  Training done (~100 min for 80 epochs on a laptop CPU)

T+2:35  python convert_to_streaming.py \
          --model  ../models/AGNI_float32.keras \
          --output ../models/AGNI_streaming_int8.tflite

T+2:40  python evaluate.py \
          --model    ../models/AGNI_streaming_int8.tflite \
          --test_dir ../dataset/split/test/AGNI
        Check: Recall ≥ 90%

        If recall < 90%:
          → Lower KWS_THRESHOLD by 0.05 in kws_model.c, re-evaluate (no retraining)
        If recall still < 90%:
          → python train.py ... --epochs 20 --resume
          → Takes ~25 min more

T+2:50  python threshold_sweep.py \
          --model   models/AGNI_streaming_int8.tflite \
          --val_dir dataset/split/val/AGNI
        → Pick optimal threshold, update kws_model.c

T+3:00  Embed model:
        xxd -i models/AGNI_streaming_int8.tflite > dora_firmware/main/kws_model_data.cc
        (Edit variable names as documented in Section 08)

T+3:05  idf.py build flash monitor

T+3:20  Live test: each team member says "AGNI" 5× near the device
        Dashboard must show latency < 75 ms and correct detection count

T+3:30  Buffer time — debug any issues
        (Common: threshold too high → lower by 0.05 and rebuild, no retrain needed)

T+4:00  READY FOR ISRO EVALUATION ✓
```

---

## 5. One-Command Swap Script

```bash
# Usage: ./swap_keyword.sh AGNI
# Run from DORA_MIXED-net/ root directory
# Prerequisites: piper_voices/ downloaded, negatives on disk, ESP-IDF env active

./swap_keyword.sh AGNI
```

The script (`swap_keyword.sh`) runs all 7 steps:
1. TTS synthesis
2. Pause for manual recordings (press ENTER when done)
3. Augmentation
4. Dataset merge + split
5. Training (80 epochs)
6. Streaming conversion + int8 quantisation + evaluation
7. Embed model → build → flash

---

## 6. Contingency Plans

### If recall is < 90% after training

- **First:** Lower `KWS_THRESHOLD` by 0.05 (0.65 → 0.60). Re-evaluate. No retraining needed. Takes 2 minutes.
- **Second:** Run `python train.py ... --resume --epochs 20`. Takes ~25 min.
- **Third:** Check dataset — verify positive files are correctly labelled (listen to a few). If synthesis failed, rerun `generate_keyword_dataset.py`.

### If training takes longer than expected (> 2 hours)

- Reduce `--epochs 80` to `--epochs 50`. Recall may drop 2–4%. Compensate by lowering threshold.
- If GPU is available, training will be ~5× faster.

### If Wi-Fi is unavailable at the venue

- Piper voices and Vosk model are already on disk (no internet needed)
- Use a mobile hotspot for ESP32-S3 + server laptop connection
- Update `WIFI_SSID` and `WIFI_PASS` in `main.c` to match the hotspot

### If the server laptop is different from the training laptop

- Copy `vosk-model-small-en-us-0.15/`, `server.py`, and `dashboard.html`
- Run `pip install fastapi "uvicorn[standard]" vosk opuslib websockets numpy` (offline from `pip_cache/`)

### If flash fails

- Put ESP32-S3 in download mode: hold BOOT button, press RESET, release BOOT
- Try: `idf.py -p COMX flash` (specify COM port explicitly)

---

## 7. Pre-Finale Dry Run

**Run this at least 2 days before the Grand Finale:**

```bash
# Dry run with a fake keyword to test the full pipeline
./swap_keyword.sh SOMA

# Verify:
# - TTS generates ~550 .wav files
# - Recording script works on your microphone
# - Training completes in < 2 hours
# - evaluate.py shows ≥ 90% recall
# - Firmware flashes successfully
# - Dashboard shows live detections
```

Time the dry run. It must complete in under 3 hours to give 1 hour buffer at the finale.

---

## 8. Finale Day Checklist

**Night before:**
- [ ] Fully charge laptop and LiPo battery
- [ ] Verify `piper_voices/` has all 5 `.onnx` files
- [ ] Verify `vosk-model-small-en-us-0.15/` is present
- [ ] Verify `dataset/unknown/` and `dataset/background/` are populated
- [ ] Pack `finale_kit/` USB as backup
- [ ] Pre-build firmware with DORA keyword — flash it, test it works

**At the venue (before ISRO announces keyword):**
- [ ] Connect ESP32-S3 to laptop
- [ ] Start server: `python server.py`
- [ ] Open dashboard: `http://localhost:8765/`
- [ ] Confirm DORA detection works as baseline
- [ ] Note the Wi-Fi network name and password at the venue
- [ ] Update `WIFI_SSID` / `WIFI_PASS` in `main.c` if needed

**After ISRO announces keyword:**
- [ ] Start `./swap_keyword.sh <ANNOUNCED_KEYWORD>` immediately
- [ ] Follow the timeline in Section 4 above
- [ ] All 6 team members ready for parallel recording session
