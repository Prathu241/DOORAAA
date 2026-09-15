"""
threshold_sweep.py  —  DORA Streaming MixedNet evaluation
==========================================================

FIXED version. Previous version was broken because it:
  1. Used librosa log-mel features instead of the real micro frontend
  2. Fed the model one frame at a time with a fresh interpreter per frame
     (no ring-buffer state accumulation — model always output near 0)

Correct approach (confirmed by inspection):
  - Model input:  (1, 3, 40)  — streaming, 3 mel frames at a time
  - Frontend:     pymicro-features  generate_features_for_clip(int16, step_ms=10)
                  (matches training exactly — PCAN noise suppression, 30ms window)
  - State:        6 ring-buffer tensors (indices 51,52,53,57,62,67)
                  → zero once per clip, then let accumulate through all frames
  - Scoring:      max score across all frame positions in the clip

Usage:
    python threshold_sweep.py \\
        --model   trained_models/DORA/dora_model_int8.tflite \\
        --pos_dir dataset/split/test/DORA \\
        --neg_dir dataset/background_wav \\
        --neg_dir2 dataset/unknown_wav
"""

import argparse
import glob
import os
import sys

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'   # suppress TF log noise

import numpy as np
import librosa

# ── Load TFLite interpreter ──────────────────────────────────────────────────
def load_tflite(model_path: str):
    try:
        import tflite_runtime.interpreter as tflite
        interp = tflite.Interpreter(model_path=model_path)
    except ImportError:
        import tensorflow as tf
        interp = tf.lite.Interpreter(model_path=model_path)
    interp.allocate_tensors()
    return interp


# ── Ring-buffer state tensor indices & shapes ────────────────────────────────
# Identified by inspecting all tensors that change during invoke.
# These are the streaming model's internal ring buffers (concatenate ReadVariableOp).
STATE_TENSORS = [
    (51, [1, 22, 1, 64]),   # stream_10 ring buffer
    (52, [1, 16, 1, 64]),   # stream_11 ring buffer
    (53, [1,  2, 1, 40]),   # stream_6  ring buffer
    (57, [1,  4, 1, 32]),   # stream_7  ring buffer
    (62, [1, 10, 1, 64]),   # stream_8  ring buffer
    (67, [1, 14, 1, 64]),   # stream_9  ring buffer
]


def reset_states(interp):
    """Zero all ring-buffer state tensors for a fresh clip."""
    for idx, shape in STATE_TENSORS:
        interp.set_tensor(idx, np.zeros(shape, dtype=np.float32))


# ── Feature extraction (matches training pipeline exactly) ───────────────────
def extract_features(audio_float32: np.ndarray, step_ms: int = 10) -> np.ndarray:
    """
    Uses the same pymicro-features C frontend used during training.
    Input:  float32 audio, 16 kHz mono
    Output: float32 array shape (T, 40)  — log-scaled mel energies
    """
    from microwakeword.audio.audio_utils import generate_features_for_clip
    audio_int16 = np.clip(audio_float32 * 32768.0, -32768, 32767).astype(np.int16)
    feats = generate_features_for_clip(audio_int16, step_ms=step_ms)
    return feats.astype(np.float32)   # (T, 40)


# ── Score a single clip ───────────────────────────────────────────────────────
def score_clip(audio_float32: np.ndarray, interp, inp_idx: int, out_idx: int) -> float:
    """
    Streams a clip through the model frame-by-frame (3 frames per invoke).
    State is zeroed at the start of each clip.
    Returns the peak score across all frame positions.
    """
    feats = extract_features(audio_float32)   # (T, 40)
    T = feats.shape[0]

    if T < 3:
        # Clip too short to produce any output
        return 0.0

    reset_states(interp)

    peak = 0.0
    for j in range(0, T - 2):
        chunk = feats[j : j + 3].reshape(1, 3, 40)
        interp.set_tensor(inp_idx, chunk)
        interp.invoke()
        s = float(interp.get_tensor(out_idx).flat[0])
        if s > peak:
            peak = s

    return peak


# ── Collect WAV files from one or more directories ────────────────────────────
def collect_wavs(dirs, limit=None):
    files = []
    for d in (dirs if isinstance(dirs, list) else [dirs]):
        if os.path.isdir(d):
            found = sorted(glob.glob(os.path.join(d, '*.wav')))
            files.extend(found)
    if limit:
        files = files[:limit]
    return files


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='DORA threshold sweep (streaming model)')
    parser.add_argument('--model',    default='trained_models/DORA/dora_model_int8.tflite')
    parser.add_argument('--pos_dir',  default='dataset/split/test/DORA',
                        help='Directory of positive (DORA) WAV files')
    parser.add_argument('--neg_dir',  default='dataset/background_wav',
                        help='Directory of negative WAV files (background noise)')
    parser.add_argument('--neg_dir2', default='dataset/unknown_wav',
                        help='Second negative directory (speech / hard negatives)')
    parser.add_argument('--limit_neg', type=int, default=None,
                        help='Cap number of negative files (default: all)')
    args = parser.parse_args()

    # Verify model exists
    if not os.path.exists(args.model):
        print(f'[ERROR] Model not found: {args.model}')
        sys.exit(1)

    # Load interpreter once and reuse (state is zeroed per clip)
    interp  = load_tflite(args.model)
    inp_det = interp.get_input_details()[0]
    out_det = interp.get_output_details()[0]
    inp_idx = inp_det['index']
    out_idx = out_det['index']

    print('=' * 65)
    print('  DORA THRESHOLD SWEEP  —  Streaming MixedNet INT8')
    print('=' * 65)
    print(f'  Model      : {args.model}  ({os.path.getsize(args.model)//1024} KB)')
    print(f'  Input shape: {inp_det["shape"]}  dtype={inp_det["dtype"]}')
    print(f'  Output shape:{out_det["shape"]}  dtype={out_det["dtype"]}')
    print(f'  Frontend   : pymicro-features  step_ms=10  n_mels=40')
    print()

    # Collect files
    pos_files  = collect_wavs(args.pos_dir)
    neg_files  = collect_wavs([args.neg_dir, args.neg_dir2], limit=args.limit_neg)
    neg_bg     = collect_wavs(args.neg_dir)
    neg_speech = collect_wavs(args.neg_dir2)

    print(f'  Positives  : {len(pos_files)} files  ({args.pos_dir})')
    print(f'  Neg-BG     : {len(neg_bg)} files  ({args.neg_dir})')
    print(f'  Neg-Speech : {len(neg_speech)} files  ({args.neg_dir2})')
    print(f'  Total negs : {len(neg_files)} files')
    print()

    if not pos_files:
        print(f'[ERROR] No positive WAV files in {args.pos_dir}')
        sys.exit(1)

    # ── Score all clips ──────────────────────────────────────────────────────
    def run_batch(files, label):
        scores = []
        n = len(files)
        for i, f in enumerate(files):
            try:
                audio, sr = librosa.load(f, sr=16000, mono=True)
                s = score_clip(audio, interp, inp_idx, out_idx)
                scores.append(s)
            except Exception as e:
                print(f'  [WARN] {os.path.basename(f)}: {e}')
                scores.append(0.0)
            if (i + 1) % 50 == 0 or (i + 1) == n:
                sys.stdout.write(f'\r  Scoring {label}: {i+1}/{n} ...')
                sys.stdout.flush()
        print()
        return scores

    pos_scores   = run_batch(pos_files, 'positives')
    neg_bg_scores    = run_batch(neg_bg,     'neg-background')
    neg_spe_scores   = run_batch(neg_speech, 'neg-speech')
    neg_all_scores   = neg_bg_scores + neg_spe_scores

    # ── Print score distribution ─────────────────────────────────────────────
    def dist(scores, label):
        if not scores: return
        mn, mx, mean = min(scores), max(scores), sum(scores)/len(scores)
        above90 = sum(1 for s in scores if s > 0.9)
        above80 = sum(1 for s in scores if s > 0.8)
        above70 = sum(1 for s in scores if s > 0.7)
        print(f'  {label:<22} n={len(scores):<5} min={mn:.4f}  max={mx:.4f}  mean={mean:.4f}'
              f'  >0.9={above90}  >0.8={above80}  >0.7={above70}')

    print()
    print('SCORE DISTRIBUTIONS')
    print('-' * 90)
    dist(pos_scores,       'Positive (DORA)')
    dist(neg_bg_scores,    'Neg background')
    dist(neg_spe_scores,   'Neg speech/hard')
    dist(neg_all_scores,   'Neg combined')

    # ── Threshold sweep ──────────────────────────────────────────────────────
    # FA/hr estimate: based on how many 1.5s clips of background audio per hour
    # 1 hour = 3600s / 1.5s = 2400 clips
    CLIP_DUR_S = 1.5
    clips_per_hour = 3600.0 / CLIP_DUR_S

    def sweep(neg_scores, neg_label, neg_total_s=None):
        if not neg_scores:
            return
        n_neg = len(neg_scores)
        if neg_total_s is None:
            neg_total_s = n_neg * CLIP_DUR_S
        fa_rate = 3600.0 / neg_total_s  # multiplier: FP/n_neg → FA/hr

        print()
        print(f'THRESHOLD SWEEP  vs  {neg_label}  ({n_neg} clips, ~{neg_total_s:.0f}s audio)')
        print(f'{"Thresh":>8}  {"TP":>5}  {"FN":>5}  {"FP":>5}  {"Recall%":>8}  {"Prec%":>7}  {"FA_count":>9}  {"FA/hr":>7}')
        print('─' * 72)

        best_row = None
        best_f1  = -1.0

        for t in [0.50, 0.60, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 0.97, 0.99]:
            tp = sum(1 for s in pos_scores    if s >= t)
            fn = len(pos_scores) - tp
            fp = sum(1 for s in neg_scores    if s >= t)
            tn = n_neg - fp
            recall = tp / max(tp + fn, 1)
            prec   = tp / max(tp + fp, 1)
            f1     = 2 * prec * recall / max(prec + recall, 1e-9)
            fa_hr  = (fp / n_neg) * fa_rate

            row = (f'  {t:>6.2f}  {tp:>5}  {fn:>5}  {fp:>5}  '
                   f'{recall*100:>7.1f}%  {prec*100:>6.1f}%  {fp:>9}  {fa_hr:>7.1f}')
            print(row)

            if f1 > best_f1:
                best_f1   = f1
                best_row  = (t, tp, fn, fp, recall, prec, fa_hr)

        print('─' * 72)
        if best_row:
            t, tp, fn, fp, recall, prec, fa_hr = best_row
            print(f'  Best F1 threshold: {t:.2f}  →  '
                  f'Recall={recall*100:.1f}%  Prec={prec*100:.1f}%  FA/hr={fa_hr:.1f}')
            print(f'  → #define KWS_THRESHOLD  {t:.2f}f')

    sweep(neg_bg_scores,   'background noise',    len(neg_bg) * CLIP_DUR_S)
    sweep(neg_spe_scores,  'speech/hard negatives')
    sweep(neg_all_scores,  'combined negatives')

    # ── Top false positives ──────────────────────────────────────────────────
    print()
    print('TOP FALSE POSITIVES (neg score > 0.70):')
    all_neg_with_names = list(zip(neg_bg + neg_speech, neg_all_scores))
    fps = [(f, s) for f, s in all_neg_with_names if s > 0.70]
    fps.sort(key=lambda x: -x[1])
    if fps:
        for f, s in fps[:20]:
            print(f'  {s:.4f}  {os.path.basename(f)}')
    else:
        print('  None above 0.70')

    print()
    print('=' * 65)
    print('  STATUS: PASS' if max(pos_scores) > 0.90 else '  STATUS: BLOCKED — positives not scoring')
    print('=' * 65)


if __name__ == '__main__':
    main()
