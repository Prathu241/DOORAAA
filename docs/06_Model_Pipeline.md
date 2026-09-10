# Model Pipeline — Exact Spec & Training
## Document 06 — SIH26172 | DORA

---

## 1. Model Choice Rationale

DORA uses the **Streaming MixedNet** architecture from the microWakeWord project. This is the same architecture that powers production wake words on Home Assistant devices running on ESP32-S3 hardware. It is:

- Field-proven on the exact target chip
- Designed for streaming inference (one 10 ms frame at a time, no look-ahead)
- Small enough to fit in 80 KB tensor arena with int8 quantisation
- Fast enough for < 10 ms inference per frame at 240 MHz

> **Policy:** We do NOT start from scratch. We clone the microWakeWord training repo and retrain it on our custom keyword. This is correct engineering — use proven infrastructure, change only the data.

---

## 2. Training Repository Setup

```bash
git clone https://github.com/kahrendt/microWakeWord
cd microWakeWord
pip install -r requirements.txt
```

This gives you:
- `train.py` — float32 model training
- `convert_to_streaming.py` — streaming TFLite conversion + int8 quantisation
- `evaluate.py` — recall / precision / FA/hr metrics
- Pre-configured audio front-end matching the on-device C preprocessor exactly

---

## 3. Model Architecture

### 3.1 Input

```
Input tensor: [1 × 40] float32
              └── One 10 ms spectrogram slice (40 Mel filterbank coefficients)
```

Each inference call processes exactly one 10 ms audio frame. The model maintains internal streaming state across calls — it never sees a full utterance at once.

### 3.2 Network Layers

```
Input [1 × 40]
    │
    ▼
MixedNet Streaming Block × 3:
    MixConv (depthwise, mixed kernels: 3×3 / 5×5 / 7×7)
    → Batch Normalization
    → ReLU6
    │
    ▼
Global Average Pooling
    │
    ▼
Dense(3) → Softmax
    ├── Class 0: keyword        (score fed to 5-frame window)
    ├── Class 1: unknown speech
    └── Class 2: background / silence
```

### 3.3 Why MixConv?

MixConv uses multiple depthwise convolution kernel sizes simultaneously:
- **3×3 kernels** — capture short-range phoneme transitions
- **5×5 kernels** — capture mid-range coarticulation patterns
- **7×7 kernels** — capture longer temporal patterns (vowels, diphthongs)

This gives a higher effective receptive field than a single 3×3 at nearly the same parameter count — critical for a single-word detection task.

### 3.4 Post-Quantisation

| Stage | Size | Location |
|---|---|---|
| Float32 Keras model | ~200–400 KB | Training laptop only |
| Streaming TFLite (float32) | ~100–200 KB | Intermediate |
| **int8 quantised TFLite** | **50–80 KB** | **Embedded in firmware flash** |
| Runtime tensor arena | 60–80 KB | ESP32-S3 RAM (allocated once) |

---

## 4. Audio Front-End Parameters

These parameters are **fixed** and must match the on-device `micro_speech` C preprocessor exactly:

```python
SAMPLE_RATE  = 16000   # Hz, mono
WINDOW_MS    = 30      # ms — spectrogram window width
STRIDE_MS    = 10      # ms — one inference call per stride
N_MEL        = 40      # Mel filterbank features per window
N_FFT        = 512
HOP_LENGTH   = 160     # samples = 10 ms at 16 kHz
```

> **Warning:** Changing any of these values will cause a train/inference mismatch. The on-device C code uses these values hard-coded in the `micro_speech` frontend. Do not touch them.

---

## 5. Training — Step by Step

### Step 1: Train Float32 Model

```bash
# From inside the microWakeWord repo directory:
python train.py \
  --keyword        DORA \
  --positive_dir   ../dataset/split/train/DORA \
  --negative_dir   ../dataset/unknown \
  --background_dir ../dataset/background \
  --epochs         100 \
  --batch_size     64 \
  --output_dir     ../models/
```

**Expected output:** `../models/DORA_float32.keras`  
**Expected training time:** 30–90 minutes (CPU), 10–20 minutes (GPU)

### Step 2: Convert to Streaming TFLite + int8

```bash
python convert_to_streaming.py \
  --model  ../models/DORA_float32.keras \
  --output ../models/DORA_streaming_int8.tflite
```

**Expected output:** `../models/DORA_streaming_int8.tflite` (50–80 KB)

### Step 3: Evaluate on Held-Out Test Set

```bash
python evaluate.py \
  --model    ../models/DORA_streaming_int8.tflite \
  --test_dir ../dataset/split/test/DORA
```

**Expected output:**
```
Recall:     92.3%     ← must be ≥ 90%
Precision:  91.7%
FA/hr:      0.8       ← must be ≤ 1
```

> **Always evaluate on held-out speakers only.** If any speaker in your test set appeared in training, the numbers are invalid. `prepare_dataset.py` enforces this automatically via speaker-based splitting.

---

## 6. Decision Logic — 5-Frame Sliding Window

Defined in `kws_model.c`. This is the only threshold you need to tune:

```c
#define KWS_WINDOW_SIZE   5       // 5 consecutive 10ms frames averaged
#define KWS_THRESHOLD     0.65f   // start here; tune via threshold_sweep.py
#define KWS_COOLDOWN_MS   1000    // silence period after one detection

static float score_buf[KWS_WINDOW_SIZE] = {0};
static int   score_idx = 0;
static bool  buf_ready  = false;

void kws_process_score(float keyword_prob) {
    score_buf[score_idx % KWS_WINDOW_SIZE] = keyword_prob;
    score_idx++;
    if (score_idx >= KWS_WINDOW_SIZE) buf_ready = true;
    if (!buf_ready) return;

    float avg = 0.0f;
    for (int i = 0; i < KWS_WINDOW_SIZE; i++) avg += score_buf[i];
    avg /= KWS_WINDOW_SIZE;

    if (avg >= KWS_THRESHOLD) {
        int64_t t_keyword_end_us = esp_timer_get_time();
        ws_start_stream(t_keyword_end_us);
        memset(score_buf, 0, sizeof(score_buf));
        score_idx = 0;
        buf_ready = false;
        vTaskDelay(pdMS_TO_TICKS(KWS_COOLDOWN_MS));
    }
}
```

---

## 7. Threshold Sweep

After training, sweep the threshold on the **validation set only** (not test set):

```python
# threshold_sweep.py
thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]
for t in thresholds:
    tp, fp, fn = evaluate_with_threshold(model, val_dir, t)
    recall = tp / max(tp + fn, 1)
    prec   = tp / max(tp + fp, 1)
    f1     = 2 * prec * recall / max(prec + recall, 1e-9)
    print(f"t={t:.2f}  recall={recall:.3f}  precision={prec:.3f}  F1={f1:.3f}  FA≈{fp}")
```

**Pick the threshold that gives:**
- FA/hr ≤ 2 on validation set (budget for test-set degradation)
- Recall ≥ 90%
- Highest F1

Set the chosen value as `KWS_THRESHOLD` in `kws_model.c` and rebuild.

---

## 8. Embedding the Model into Firmware

```bash
# Convert .tflite binary to C array:
xxd -i models/DORA_streaming_int8.tflite > dora_firmware/main/kws_model_data.cc

# Fix variable name to match firmware expectations:
# (xxd generates: "unsigned char models_DORA_streaming_int8_tflite[]")
# (firmware expects: "const unsigned char g_kws_model_data[]")
sed -i \
  's/^unsigned char .*/const unsigned char g_kws_model_data[] __attribute__((aligned(8))) = {/' \
  dora_firmware/main/kws_model_data.cc

# Fix length variable:
# Replace the auto-generated length line with the correct name
# (manually set the integer value from the original xxd output)

# Build and flash:
cd dora_firmware
idf.py build flash monitor
```

---

## 9. Op Resolver Configuration

Only register the ops that MixedNet actually uses. Registering extra ops wastes flash:

```cpp
static tflite::MicroMutableOpResolver<8> resolver;
resolver.AddConv2D();
resolver.AddDepthwiseConv2D();
resolver.AddReshape();
resolver.AddSoftmax();
resolver.AddMean();
resolver.AddAdd();
resolver.AddMul();
resolver.AddFullyConnected();
```

---

## 10. Accuracy Measurement Log

Fill this table before the Grand Finale evaluation:

| Date | Keyword | Recall | FA/hr | RAM Peak | CPU Avg | Latency p50 | Latency p95 |
|---|---|---|---|---|---|---|---|
| — | DORA | TBD | TBD | TBD | TBD | TBD | TBD |
| — | Grand Finale keyword | TBD | TBD | TBD | TBD | TBD | TBD |
