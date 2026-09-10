"""
convert_aac.py — Convert all .aac files from dataset/Raw/Dora into
                  16 kHz mono PCM WAV files in dataset/DORA_real/

Usage:
    python convert_aac.py

What it does:
  - Recursively finds every .aac file in dataset/Raw/Dora/
  - Converts each to 16 kHz mono signed-16-bit PCM WAV via ffmpeg
  - Sanitises the filename (lowercase, spaces → underscores, no special chars)
  - Assigns a speaker tag (spk_raw) so prepare_dataset.py can handle them
  - Reports conversion failures clearly

Requirements:
  - ffmpeg on PATH  (installed via: winget install Gyan.FFmpeg)
  - pydub           (pip install pydub)
"""

import os
import re
import subprocess
import sys
from pathlib import Path
from tqdm import tqdm

# ── Paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent
RAW_DIR    = ROOT / "dataset" / "Raw" / "Dora"
OUT_DIR    = ROOT / "dataset" / "DORA_real"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def sanitise(name: str) -> str:
    """Lower-case, replace spaces/special chars with underscores."""
    name = name.lower()
    name = re.sub(r"[^a-z0-9_]", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name


def convert_to_wav(src: Path, dst: Path) -> bool:
    """
    Use ffmpeg to convert src → dst at 16 kHz mono 16-bit PCM.
    Returns True on success, False on failure.
    """
    cmd = [
        "ffmpeg", "-y",               # overwrite output if exists
        "-i", str(src),               # input file
        "-ar", "16000",               # resample to 16 kHz
        "-ac", "1",                   # mono
        "-sample_fmt", "s16",         # 16-bit signed PCM
        str(dst)
    ]
    result = subprocess.run(cmd, capture_output=True)
    return result.returncode == 0


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    # Find all .aac files recursively
    aac_files = list(RAW_DIR.rglob("*.aac"))
    if not aac_files:
        print(f"[ERROR] No .aac files found in {RAW_DIR}")
        sys.exit(1)

    print(f"Found {len(aac_files)} .aac files in {RAW_DIR}")
    print(f"Output directory: {OUT_DIR}\n")

    ok = 0
    fail = 0
    skipped = 0
    name_counts: dict[str, int] = {}

    for src in tqdm(aac_files, desc="Converting", unit="file"):
        stem     = sanitise(src.stem)
        # Deduplicate: append _N if same stem appears more than once
        if stem in name_counts:
            name_counts[stem] += 1
            stem = f"{stem}_{name_counts[stem]:03d}"
        else:
            name_counts[stem] = 0

        # Tag with spk_raw so prepare_dataset.py treats them as real recordings
        out_name = f"dora_spk_raw_{stem}.wav"
        dst      = OUT_DIR / out_name

        if dst.exists():
            skipped += 1
            continue

        if convert_to_wav(src, dst):
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {src.name}")

    print(f"\n{'─'*50}")
    print(f"  Converted : {ok}")
    print(f"  Skipped   : {skipped}  (already existed)")
    print(f"  Failed    : {fail}")
    print(f"  Total WAV : {len(list(OUT_DIR.glob('*.wav')))}")
    print(f"{'─'*50}")
    print(f"\nAll WAV files → {OUT_DIR}")


if __name__ == "__main__":
    main()
