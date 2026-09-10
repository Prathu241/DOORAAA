# TRAINING TERMINAL - LOCATION & STATUS

## Current Training Process

**Status:** 🟢 RUNNING (Fresh Start)  
**Terminal ID:** `term_1788971002255_zc53so1l5hp`  
**Location:** Kiro IDE Background Process Panel  
**Started:** 09 Sept 2026, ~21:50 UTC

---

## HOW TO VIEW TRAINING OUTPUT

### Method 1: Kiro IDE Terminal Panel (Recommended)
1. Look at bottom of Kiro IDE window
2. Find **"Terminal"** tab or panel
3. Click it to expand
4. You should see live training output with:
   - Model architecture summary
   - Training step numbers
   - Accuracy/Recall/Precision metrics
   - Loss values

### Method 2: Terminal Command in Kiro
1. In Kiro, open the terminal (bottom panel)
2. Run: `Get-Process | grep python` to confirm training is running

### Method 3: File System Check
Training output files appear in:
```
c:\Users\PRATHAM\DORA_MIXED-net\trained_models\DORA\
├── logs/                    ← Training logs (live updates)
├── best_weights.weights.h5  ← Best model weights (updates during training)
├── tflite_stream_state_internal_quant/
│   └── stream_state_internal_quant.tflite  ← Final model (appears at end)
└── training_config.yaml
```

Watch the file timestamps - they'll update as training progresses.

---

## EXPECTED TRAINING OUTPUT

### Initial Setup (First 2-3 minutes)
```
Loading dataset...
Building model architecture...
Model parameters: 26,049 (101.75 KB)

Training starting...
Step #1: rate 0.001000, accuracy 45.23%, recall 12.34%, precision 8.92%
Step #2: rate 0.001000, accuracy 52.11%, recall 18.56%, precision 15.23%
...
```

### After 500 steps (~10 minutes)
```
Step #500: rate 0.001000, accuracy 87.34%, recall 72.45%, precision 85.23%
Step #1000: rate 0.001000, accuracy 91.23%, recall 78.92%, precision 89.34%
Step #1500: rate 0.001000, accuracy 93.45%, recall 81.23%, precision 90.12%
...
```

### Final Steps (~15000 steps, ~90 minutes total)
```
Step #14500: accuracy 95.2%, recall 85.1%, precision 93.4%
Step #15000: accuracy 95.4%, recall 85.6%, precision 93.7%

Quantizing model...
Saving int8 TFLite model...
✓ Model saved: stream_state_internal_quant.tflite (68 KB)
Training complete!
```

---

## MONITORING CHECKLIST

While waiting for training to finish:

- [ ] **Check every 5 minutes:** Accuracy is increasing (target: >93%)
- [ ] **Check recall:** Should go from low (~30%) → high (~75%+)
- [ ] **Check precision:** Should stay >85%
- [ ] **Watch for errors:** If you see red text error, report immediately
- [ ] **Don't interrupt:** Don't close terminal or stop process

---

## KEY METRICS EXPLAINED

| Metric | Meaning | Target |
|--------|---------|--------|
| **Accuracy** | % correct classifications (keyword + non-keyword) | >93% |
| **Recall** | % of actual keywords detected (False Negative rate) | 75-85% |
| **Precision** | % of detections that are correct (False Positive quality) | 85-90% |
| **Loss** | Training error (lower = better) | <0.25 |

**Important:** 
- High recall means few keywords are missed ✓
- High precision means few false alarms ✓
- Recall often lower than accuracy because keywords are harder to detect

---

## IF TRAINING FAILS

If you see an error like:

```
ValueError: ...
Traceback ...
```

**DO:**
1. Report the exact error message
2. Don't restart immediately - might be recoverable
3. Kiro will fix and restart automatically

**Common Fixes:**
- Data loading issue → Already fixed
- Memory issue → Reduce batch size (already optimized)
- Disk space → Check free space
- GPU/CPU mismatch → Using CPU (expected on Windows)

---

## COMPLETION SIGNAL

Training is **COMPLETE** when you see:

```
Step #15000: rate 0.001000, accuracy 95.4%, recall 85.6%, precision 93.7%

Saving quantized model to: tflite_stream_state_internal_quant/stream_state_internal_quant.tflite

✓ Quantization complete
✓ Model exported successfully
[Training complete]
```

Then:
1. Check file exists: `trained_models/DORA/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite`
2. Verify file size: ~30-80 KB (not 0 bytes)
3. Report: "**TRAINING COMPLETE**"
4. Kiro will integrate model into KWS firmware

---

## PARALLEL EXECUTION

**Your Tasks (while training runs):**
1. ✓ Wire microphone (30 min)
2. ✓ Flash mic_test.ino (5 min)
3. ✓ Run microphone test (10 min)
4. ✓ Report "MIC PASS" or fix error

**Kiro Tasks (in background):**
1. ✓ Training running (~90 min)
2. (After training complete) Extract quantized model
3. (After training complete + MIC PASS) Create KWS firmware

**Total Time:** 90 min (training) + 30 min (hardware) = ~2 hours
**Within 4-hour window:** ✓ YES

---

## TERMINAL TROUBLESHOOTING

### "I can't see terminal output"
→ Click Terminal tab at bottom of Kiro IDE
→ If no Terminal tab, press Ctrl+` to open

### "Terminal shows old training"
→ That's OK - scroll down to see new training
→ Check file modification times to confirm it's running now

### "Terminal says process stopped"
→ Check if error appeared above
→ If no error, training might have completed
→ Check for tflite file in trained_models/DORA/

### "Terminal disappeared"
→ Don't worry - process is still running
→ Kiro terminal auto-closes after completion
→ Check trained_models/DORA/ for output files

---

## NEXT STEPS

1. **Monitor training** - Takes ~90 minutes
2. **Wire hardware** - Parallel while training runs
3. **Test microphone** - Flash and verify capture works
4. **Upon training completion** - Extract model
5. **Upon MIC PASS** - Integrate and test KWS

---

**Training Status:** Active  
**Last Update:** 09 Sept 2026 21:50 UTC  
**Estimated Completion:** 09 Sept 2026 23:20 UTC (+90 min)

Check progress every 10 minutes!
