"""
DORA Model Test — runs on laptop, no hardware needed.
Tests the trained TFLite model against WAV files from the dataset.
"""

import numpy as np
import tensorflow as tf
import os, time, glob

MODEL_PATH = "trained_models/DORA/dora_model_int8.tflite"
THRESHOLD  = 0.7

# ── Load model ────────────────────────────────────────────────────────────────
print("=" * 60)
print("  DORA MODEL TEST — Laptop Inference")
print("=" * 60)

interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()

inp_details = interpreter.get_input_details()
out_details = interpreter.get_output_details()

inp_shape = inp_details[0]['shape']   # e.g. [1, 204, 40]
inp_dtype = inp_details[0]['dtype']

print(f"\n  Model      : {MODEL_PATH}")
print(f"  Input shape: {inp_shape}  dtype={inp_dtype}")
print(f"  Output     : {out_details[0]['shape']}  dtype={out_details[0]['dtype']}")
print(f"  Threshold  : {THRESHOLD}")

num_frames = int(inp_shape[1])
num_coeffs = int(inp_shape[2])
print(f"\n  Expects {num_frames} frames x {num_coeffs} coefficients per inference")

# ── Feature extraction (matches .ino energy approximation) ───────────────────
def extract_features(audio_float32, num_frames, num_coeffs):
    total = len(audio_float32)
    frame_len = max(1, total // num_frames)
    features = np.zeros((num_frames, num_coeffs), dtype=np.float32)
    for f in range(num_frames):
        start = f * frame_len
        for c in range(num_coeffs):
            band_size  = max(1, frame_len // num_coeffs)
            band_start = start + c * band_size
            seg = audio_float32[band_start : band_start + band_size]
            if len(seg) > 0:
                features[f, c] = np.log(np.sum(seg ** 2) + 1e-10)
    return features

# ── Run inference on a numpy float32 audio array ─────────────────────────────
def run_inference(audio_float32):
    features = extract_features(audio_float32, num_frames, num_coeffs)
    model_input = features.reshape(inp_shape).astype(inp_dtype)
    interpreter.set_tensor(inp_details[0]['index'], model_input)
    t0 = time.perf_counter()
    interpreter.invoke()
    latency_ms = (time.perf_counter() - t0) * 1000
    result = interpreter.get_tensor(out_details[0]['index']).flatten()
    score = float(result[-1])
    return score, latency_ms, result

# ── Load WAV without sounddevice ──────────────────────────────────────────────
def load_wav(path):
    import wave, struct
    with wave.open(path, 'rb') as w:
        frames  = w.readframes(w.getnframes())
        n_ch    = w.getnchannels()
        sampw   = w.getsampwidth()
        rate    = w.getframerate()
    if sampw == 2:
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampw == 4:
        audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        audio = np.frombuffer(frames, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
    if n_ch > 1:
        audio = audio[::n_ch]
    return audio, rate

# ── Find test WAV files ───────────────────────────────────────────────────────
POSITIVE_DIRS = [
    "dataset/DORA_augmented",
    "dataset/DORA_real",
    "dataset/DORA_wav",
]
NEGATIVE_DIRS = [
    "dataset/background_wav",
    "dataset/non_DORA_wav",
    "dataset/negatives",
]

def collect_wavs(dirs, limit=10):
    files = []
    for d in dirs:
        if os.path.isdir(d):
            found = glob.glob(os.path.join(d, "**/*.wav"), recursive=True) + \
                    glob.glob(os.path.join(d, "*.wav"))
            files.extend(found[:limit])
            if len(files) >= limit:
                break
    return files[:limit]

pos_files = collect_wavs(POSITIVE_DIRS, limit=10)
neg_files = collect_wavs(NEGATIVE_DIRS, limit=10)

print(f"\n  Found {len(pos_files)} positive WAV files to test")
print(f"  Found {len(neg_files)} negative WAV files to test")

# ── Run tests ─────────────────────────────────────────────────────────────────
def test_batch(files, label, expect_detect):
    if not files:
        print(f"\n  ⚠️  No {label} files found — skipping")
        return 0, 0, []

    print(f"\n{'─'*60}")
    print(f"  {label.upper()} FILES (expect: {'DETECTED' if expect_detect else 'NOT detected'})")
    print(f"{'─'*60}")

    correct = 0
    scores  = []
    latencies = []

    for path in files:
        try:
            audio, rate = load_wav(path)
            score, lat, raw = run_inference(audio)
            detected  = score > THRESHOLD
            is_correct = detected == expect_detect
            correct   += int(is_correct)
            scores.append(score)
            latencies.append(lat)

            status = "✅" if is_correct else "❌"
            det_str = "DETECTED" if detected else "not detected"
            fname = os.path.basename(path)[:35]
            print(f"  {status}  {fname:<36}  score={score:.4f}  lat={lat:.1f}ms  → {det_str}")
        except Exception as e:
            print(f"  ⚠️  {os.path.basename(path)}: {e}")

    if scores:
        print(f"\n  Accuracy : {correct}/{len(files)} correct ({100*correct/len(files):.0f}%)")
        print(f"  Avg score: {np.mean(scores):.4f}   min={np.min(scores):.4f}  max={np.max(scores):.4f}")
        print(f"  Avg latency: {np.mean(latencies):.1f} ms per inference")

    return correct, len(files), scores

pos_correct, pos_total, pos_scores = test_batch(pos_files, "POSITIVE (DORA)", expect_detect=True)
neg_correct, neg_total, neg_scores = test_batch(neg_files, "NEGATIVE (background)", expect_detect=False)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("  OVERALL RESULTS")
print(f"{'='*60}")

total_correct = pos_correct + neg_correct
total_files   = pos_total + neg_total

if pos_total > 0:
    recall    = pos_correct / pos_total * 100
    print(f"  Recall (TP rate)    : {pos_correct}/{pos_total}  →  {recall:.1f}%")
if neg_total > 0:
    specificity = neg_correct / neg_total * 100
    print(f"  Specificity (TN rate): {neg_correct}/{neg_total}  →  {specificity:.1f}%")
if total_files > 0:
    overall = total_correct / total_files * 100
    print(f"  Overall accuracy    : {total_correct}/{total_files}  →  {overall:.1f}%")

print(f"\n  Model file size : {os.path.getsize(MODEL_PATH) / 1024:.1f} KB")
print(f"  Detection threshold used: {THRESHOLD}")
print("=" * 60)
