"""
augment_real.py — 4x deterministic augmentation of real keyword recordings.

KEYWORD-GENERIC: contains zero DORA-specific assumptions.
Pass --keyword and --input explicitly. The script will NOT fall back silently
to any other keyword's directory.

Usage:
    python augment_real.py --keyword DORA
    python augment_real.py --keyword AGNI
    python augment_real.py --keyword DORA --input dataset/DORA_real --output dataset/DORA_augmented

Output format: 16 kHz mono PCM_16 WAV (identical format to source recordings).

Augmentation variants produced per input file:
    <stem>_aug0.wav  — Additive white Gaussian noise (SNR 10-20 dB)
    <stem>_aug1.wav  — Pitch shift ±1 or ±2 semitones
    <stem>_aug2.wav  — Speed perturbation ±10% (time-stretch, no pitch change)
    <stem>_aug3.wav  — Synthetic reverb (exponential-decay impulse response)

Naming contract (IMPORTANT for prepare_dataset.py grouping):
    source file : dora_spk001_000.wav
    augmented   : dora_spk001_000_aug0.wav  ...  dora_spk001_000_aug3.wav
    group key   : dora_spk001_000          (aug suffix stripped by prepare_dataset.py)

This contract ensures all augmented variants of the same source recording
are assigned to the same train/val/test split (zero leakage by design).
"""

import argparse
import glob
import os
import random
import sys

import librosa
import numpy as np
import soundfile as sf
from tqdm import tqdm

SR = 16000  # must match microWakeWord feature extractor


# ── Augmentation functions ────────────────────────────────────────────────────

def aug_noise(audio: np.ndarray) -> np.ndarray:
    """Add white Gaussian noise at random SNR 10-20 dB."""
    snr_db = random.uniform(10, 20)
    sig_power = np.mean(audio ** 2)
    if sig_power < 1e-12:
        return audio
    noise_power = sig_power / (10 ** (snr_db / 10))
    noise = np.random.randn(len(audio)) * np.sqrt(noise_power)
    return np.clip(audio + noise, -1.0, 1.0).astype(np.float32)


def aug_pitch(audio: np.ndarray) -> np.ndarray:
    """Pitch-shift by a random ±1 or ±2 semitones."""
    n_steps = random.choice([-2, -1, 1, 2])
    return librosa.effects.pitch_shift(audio, sr=SR, n_steps=n_steps).astype(np.float32)


def aug_speed(audio: np.ndarray) -> np.ndarray:
    """Time-stretch ±10% without changing pitch. Pads/trims to original length."""
    rate = random.uniform(0.90, 1.10)
    stretched = librosa.effects.time_stretch(audio, rate=rate)
    if len(stretched) >= len(audio):
        return stretched[: len(audio)].astype(np.float32)
    pad = np.zeros(len(audio) - len(stretched), dtype=np.float32)
    return np.concatenate([stretched, pad]).astype(np.float32)


def aug_reverb(audio: np.ndarray) -> np.ndarray:
    """Synthetic reverb via exponential-decay impulse response (125 ms).

    BUG FIX (was: ir /= ir.sum() which made output near-zero because
    sum of exp(-linspace(0,8,2000)) >> 1 so every sample gets divided by ~250).
    FIX: normalise by peak so IR max = 1, preserving perceptual level.
    Then rescale output to match input RMS so volume is consistent.
    """
    ir_len = SR // 8   # 125 ms at 16 kHz = 2000 samples
    ir = np.exp(-np.linspace(0, 8, ir_len)).astype(np.float32)
    ir /= ir.max()     # peak-normalise: max coefficient = 1.0, no division-by-sum
    reverbed = np.convolve(audio, ir, mode="same").astype(np.float32)
    # Rescale reverbed output to match input RMS (prevents volume collapse)
    src_rms = float(np.sqrt(np.mean(audio ** 2)))
    rev_rms = float(np.sqrt(np.mean(reverbed ** 2)))
    if rev_rms > 1e-9:
        reverbed = reverbed * (src_rms / rev_rms)
    return np.clip(reverbed, -1.0, 1.0).astype(np.float32)


AUGMENTATIONS = [aug_noise, aug_pitch, aug_speed, aug_reverb]
AUG_NAMES     = ["noise", "pitch", "speed", "reverb"]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="4x deterministic augmentation of real keyword recordings."
    )
    parser.add_argument(
        "--keyword",
        required=True,
        help="Keyword name, e.g. DORA or AGNI. Used only to derive default paths.",
    )
    parser.add_argument(
        "--input",
        default=None,
        help="Input directory containing real WAV recordings. "
             "Defaults to dataset/<KEYWORD>_real/. "
             "FAILS with an error if the directory does not exist — "
             "it will NOT silently fall back to any other directory.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory for augmented WAVs. "
             "Defaults to dataset/<KEYWORD>_augmented/.",
    )
    parser.add_argument(
        "--seed",
        default=42,
        type=int,
        help="Random seed for reproducibility.",
    )
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

    kw      = args.keyword.strip().upper()
    in_dir  = args.input  or os.path.join("dataset", f"{kw}_real")
    out_dir = args.output or os.path.join("dataset", f"{kw}_augmented")

    # ── Hard fail if input directory is missing ───────────────────────────────
    if not os.path.isdir(in_dir):
        print(
            f"[ERROR] Input directory not found: {in_dir}\n"
            f"        Create it and place {kw} WAV recordings inside before running.\n"
            f"        Use --input to override the path.\n"
            f"        This script will NOT fall back to any other keyword's directory."
        )
        sys.exit(1)

    wav_files = sorted(glob.glob(os.path.join(in_dir, "*.wav")))

    if not wav_files:
        print(
            f"[ERROR] No .wav files found in {in_dir}.\n"
            f"        Run convert_aac.py --keyword {kw} first."
        )
        sys.exit(1)

    os.makedirs(out_dir, exist_ok=True)

    print(f"Keyword  : {kw}")
    print(f"Input    : {in_dir}  ({len(wav_files)} WAV files)")
    print(f"Output   : {out_dir}")
    print(f"Variants : {len(AUGMENTATIONS)} per file → {len(wav_files) * len(AUGMENTATIONS)} total")
    print(f"Format   : 16 kHz mono PCM_16\n")

    ok = fail = skipped = 0

    for fpath in tqdm(wav_files, desc="Augmenting", unit="file"):
        try:
            audio, file_sr = librosa.load(fpath, sr=SR, mono=True)
        except Exception as exc:
            print(f"  [SKIP] Cannot load {os.path.basename(fpath)}: {exc}")
            fail += 1
            continue

        stem = os.path.splitext(os.path.basename(fpath))[0]

        for i, aug_fn in enumerate(AUGMENTATIONS):
            out_path = os.path.join(out_dir, f"{stem}_aug{i}.wav")

            if os.path.exists(out_path):
                skipped += 1
                continue

            try:
                augmented = aug_fn(audio)
                # Write as 16 kHz mono PCM_16 — same format as source recordings
                sf.write(out_path, augmented, SR, subtype="PCM_16")
                ok += 1
            except Exception as exc:
                print(f"  [FAIL] aug{i} ({AUG_NAMES[i]}) on {stem}: {exc}")
                fail += 1

    print(f"\n{'─'*54}")
    print(f"  Keyword   : {kw}")
    print(f"  Input     : {len(wav_files)} source files")
    print(f"  Generated : {ok}  (PCM_16 WAV)")
    print(f"  Skipped   : {skipped}  (already existed)")
    print(f"  Failed    : {fail}")
    total_out = len(glob.glob(os.path.join(out_dir, "*.wav")))
    print(f"  Total in {out_dir.split(os.sep)[-1]}/: {total_out}")
    print(f"{'─'*54}")

    if fail > 0:
        print(f"\n[WARN] {fail} augmentation(s) failed. Check messages above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
