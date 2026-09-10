"""
convert_negatives.py — Convert Background and Unknown audio files to 16 kHz mono WAV.

Handles .aac, .mp3, .ogg, .m4a, .flac, .opus — anything ffmpeg can decode.
Skips files that are already .wav (copies them as-is after resampling to 16 kHz mono).

Usage:
    python convert_negatives.py

Output directories:
    dataset/background_wav/      ← from dataset/Raw/Background/
    dataset/unknown_wav/         ← from dataset/Raw/Unknown/
"""

import os
import subprocess
from pathlib import Path
from tqdm import tqdm

ROOT = Path(__file__).parent

JOBS = [
    {
        "src_dirs": [
            ROOT / "dataset" / "Raw" / "Background",
        ],
        "out_dir": ROOT / "dataset" / "background_wav",
        "label":   "Background",
    },
    {
        "src_dirs": [
            ROOT / "dataset" / "Raw" / "Unknown" / "speech",
            ROOT / "dataset" / "Raw" / "Unknown" / "hard_negatives",
        ],
        "out_dir": ROOT / "dataset" / "unknown_wav",
        "label":   "Unknown",
    },
]

AUDIO_EXTS = {".aac", ".mp3", ".ogg", ".m4a", ".flac", ".opus", ".wav", ".wma"}


def convert_to_wav(src: Path, dst: Path) -> bool:
    cmd = [
        "ffmpeg", "-y",
        "-i", str(src),
        "-ar", "16000",
        "-ac", "1",
        "-sample_fmt", "s16",
        str(dst),
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


def main():
    for job in JOBS:
        out_dir = job["out_dir"]
        out_dir.mkdir(parents=True, exist_ok=True)

        # Collect all audio files from all src_dirs
        all_files = []
        for src_dir in job["src_dirs"]:
            if src_dir.exists():
                for f in src_dir.rglob("*"):
                    if f.is_file() and f.suffix.lower() in AUDIO_EXTS:
                        all_files.append(f)

        if not all_files:
            print(f"[WARN] No audio files found for {job['label']}")
            continue

        print(f"\nConverting {len(all_files)} {job['label']} files → {out_dir}")
        ok = fail = skipped = 0

        for src in tqdm(all_files, desc=job["label"], unit="file"):
            # Build unique output name: subfolder_stem.wav
            rel   = src.relative_to(src.parent.parent) if src.parent != src.parent.parent else src.name
            stem  = str(rel).replace(os.sep, "_").replace(" ", "_")
            stem  = Path(stem).stem  # strip original extension
            dst   = out_dir / f"{stem}.wav"

            # Handle name collisions
            counter = 1
            base_stem = stem
            while dst.exists() and dst.stat().st_size > 0:
                dst = out_dir / f"{base_stem}_{counter}.wav"
                counter += 1

            if dst.exists() and dst.stat().st_size > 0:
                skipped += 1
                continue

            if convert_to_wav(src, dst):
                ok += 1
            else:
                fail += 1

        print(f"  Converted: {ok}  |  Skipped (exists): {skipped}  |  Failed: {fail}")
        print(f"  Total WAVs in {out_dir.name}: {len(list(out_dir.glob('*.wav')))}")

    print("\nDone.")


if __name__ == "__main__":
    main()
