"""
threshold_sweep.py — Sweep KWS_THRESHOLD on the validation set

Usage:
    python threshold_sweep.py \
        --model   models/DORA_streaming_int8.tflite \
        --val_dir dataset/split/val/DORA \
        --neg_dir dataset/Raw/Unknown/speech

What it does:
    Tests thresholds from 0.50 to 0.85 and prints recall / precision / F1 / FA
    so you can pick the optimal KWS_THRESHOLD for kws_model.c

Requirements:
    pip install tflite-runtime  (or tensorflow)
"""

import argparse
import glob
import os
import sys

import librosa
import numpy as np


def load_tflite_model(model_path: str):
    """Load a TFLite model using tflite-runtime or tensorflow.lite."""
    try:
        import tflite_runtime.interpreter as tflite
        interp = tflite.Interpreter(model_path=model_path)
    except ImportError:
        try:
            import tensorflow as tf
            interp = tf.lite.Interpreter(model_path=model_path)
        except ImportError:
            print("[ERROR] Install tflite-runtime or tensorflow:")
            print("        pip install tflite-runtime")
            sys.exit(1)
    interp.allocate_tensors()
    return interp


def extract_features(audio: np.ndarray, sr: int = 16000, n_mels: int = 40) -> np.ndarray:
    """Extract log-Mel spectrogram matching the micro_speech front-end parameters."""
    mel = librosa.feature.melspectrogram(
        y=audio, sr=sr, n_fft=512, hop_length=160,
        win_length=480, n_mels=n_mels, fmin=60, fmax=7600
    )
    log_mel = librosa.power_to_db(mel + 1e-6)
    return log_mel.astype(np.float32)


def run_inference(interp, features: np.ndarray) -> float:
    """Run streaming model inference on a feature matrix, return keyword prob."""
    inp_details = interp.get_input_details()
    out_details = interp.get_output_details()
    n_frames    = features.shape[1]  # time axis
    keyword_probs = []

    for t in range(n_frames):
        frame = features[:, t].reshape(inp_details[0]["shape"])
        interp.set_tensor(inp_details[0]["index"], frame)
        interp.invoke()
        out = interp.get_tensor(out_details[0]["index"])
        keyword_probs.append(float(out.flat[0]))

    return max(keyword_probs) if keyword_probs else 0.0


def evaluate_with_threshold(interp, pos_files, neg_files, threshold):
    tp = fp = fn = 0
    for f in pos_files:
        try:
            audio, _ = librosa.load(f, sr=16000, mono=True)
            feats    = extract_features(audio)
            score    = run_inference(interp, feats)
            if score >= threshold:
                tp += 1
            else:
                fn += 1
        except Exception:
            fn += 1

    for f in neg_files:
        try:
            audio, _ = librosa.load(f, sr=16000, mono=True)
            feats    = extract_features(audio)
            score    = run_inference(interp, feats)
            if score >= threshold:
                fp += 1
        except Exception:
            pass

    return tp, fp, fn


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model",   required=True, help="Path to .tflite model")
    parser.add_argument("--val_dir", required=True, help="Validation positives directory")
    parser.add_argument("--neg_dir", default="dataset/Raw/Unknown/speech",
                        help="Negatives directory for FA estimation")
    args = parser.parse_args()

    if not os.path.exists(args.model):
        print(f"[ERROR] Model not found: {args.model}")
        sys.exit(1)

    pos_files = glob.glob(os.path.join(args.val_dir, "*.wav"))
    neg_files = glob.glob(os.path.join(args.neg_dir, "*.wav"))[:200]  # cap at 200

    if not pos_files:
        print(f"[ERROR] No .wav files in {args.val_dir}")
        sys.exit(1)

    print(f"Model     : {args.model}")
    print(f"Positives : {len(pos_files)} files from {args.val_dir}")
    print(f"Negatives : {len(neg_files)} files from {args.neg_dir}")
    print()

    interp     = load_tflite_model(args.model)
    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85]

    print(f"{'Threshold':>10}  {'Recall':>8}  {'Precision':>10}  {'F1':>6}  {'FA (est.)':>10}")
    print("─" * 55)

    best_f1 = -1
    best_t  = 0.65

    for t in thresholds:
        tp, fp, fn = evaluate_with_threshold(interp, pos_files, neg_files, t)
        recall  = tp / max(tp + fn, 1)
        prec    = tp / max(tp + fp, 1)
        f1      = 2 * prec * recall / max(prec + recall, 1e-9)
        print(f"  t={t:.2f}    {recall*100:6.1f}%    {prec*100:8.1f}%    {f1:.3f}   FA≈{fp}")
        if f1 > best_f1 and fp <= 2:
            best_f1 = f1
            best_t  = t

    print("─" * 55)
    print(f"\n  Recommended KWS_THRESHOLD = {best_t:.2f}  (best F1 with FA ≤ 2)")
    print(f"  Set this in: dora_firmware/main/kws_model.c")
    print(f"  #define KWS_THRESHOLD  {best_t:.2f}f")


if __name__ == "__main__":
    main()
