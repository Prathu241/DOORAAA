"""
generate_keyword_dataset.py — Piper TTS synthesis of keyword samples.

KEYWORD-GENERIC: --keyword is REQUIRED. No silent defaults.
Supports any keyword:
    python generate_keyword_dataset.py --keyword DORA  --count 600
    python generate_keyword_dataset.py --keyword AGNI  --count 600
    python generate_keyword_dataset.py --keyword <ISRO_KEYWORD> --count 600

OUTPUT FORMAT: 16 kHz mono PCM_16 WAV.
Piper natively outputs at the voice model's sample rate (22050 Hz for most
medium models). This script automatically resamples every generated file
to 16 kHz using ffmpeg — required for microWakeWord feature extraction.

VOICE MODELS:
    Place .onnx + .onnx.json pairs in piper_voices/ (default) or pass --voices_dir.
    Download with: python generate_keyword_dataset.py --download_voices

SAMPLE COUNT:
    Generates approximately --count samples spread across all available voices
    and all 9 speaking speeds. Exact count may differ slightly depending on
    how many voice models are present.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from tqdm import tqdm

VOICE_URLS = {
    # en_US voices — verified working at v1.0.0 tag
    "en_US-ryan-medium": (
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
        "/en/en_US/ryan/medium/en_US-ryan-medium.onnx"
    ),
    "en_US-lessac-medium": (
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
        "/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
    ),
    "en_US-amy-medium": (
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
        "/en/en_US/amy/medium/en_US-amy-medium.onnx"
    ),
    "en_US-joe-medium": (
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
        "/en/en_US/joe/medium/en_US-joe-medium.onnx"
    ),
    # en_GB voices
    "en_GB-alan-medium": (
        "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0"
        "/en/en_GB/alan/medium/en_GB-alan-medium.onnx"
    ),
}

# Nine speaking speeds covering slow → fast range
SPEEDS = [0.75, 0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.20, 1.30]

TARGET_SR = 16000  # microWakeWord feature extractor requirement


# ── Helpers ───────────────────────────────────────────────────────────────────

def _check_ffmpeg() -> bool:
    """Return True if ffmpeg is on PATH."""
    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            check=True,
        )
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _check_piper() -> bool:
    """Return True if piper CLI is on PATH."""
    try:
        subprocess.run(
            ["piper", "--help"],
            capture_output=True,
        )
        return True
    except FileNotFoundError:
        return False


def _resample_to_16k(src: str) -> bool:
    """
    Resample src (any rate) → 16 kHz mono PCM_16 WAV in-place via ffmpeg.
    Returns True on success.
    """
    tmp = src + ".tmp16k.wav"
    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", src,
            "-ar", str(TARGET_SR),
            "-ac", "1",
            "-sample_fmt", "s16",
            tmp,
        ],
        capture_output=True,
    )
    if result.returncode == 0:
        os.replace(tmp, src)
        return True
    # Clean up failed temp file
    if os.path.exists(tmp):
        os.remove(tmp)
    return False


def download_voices(voices_dir: str):
    """Download all five Piper voice models (.onnx + .onnx.json)."""
    import urllib.request

    os.makedirs(voices_dir, exist_ok=True)
    for name, url in VOICE_URLS.items():
        for url_suffix, local_ext in [("", ".onnx"), (".json", ".onnx.json")]:
            full_url  = url + url_suffix
            dst_path  = os.path.join(voices_dir, name + local_ext)
            if os.path.exists(dst_path):
                print(f"  Already exists : {name}{local_ext}")
                continue
            print(f"  Downloading    : {name}{local_ext} …", end="", flush=True)
            try:
                urllib.request.urlretrieve(full_url, dst_path)
                print(" ✓")
            except Exception as exc:
                print(f" ✗  ({exc})")


def _probe_sample_rate(path: str) -> int:
    """Return the sample rate of a WAV file using ffprobe, or 0 on failure."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "a:0",
                "-show_entries", "stream=sample_rate",
                "-of", "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            capture_output=True,
            text=True,
        )
        return int(result.stdout.strip())
    except Exception:
        return 0


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate Piper TTS keyword samples at 16 kHz mono PCM_16. "
            "Keyword-generic — supports any keyword."
        )
    )
    parser.add_argument(
        "--keyword",
        required=False,
        default=None,
        help="Keyword to synthesise (e.g. DORA, AGNI, <ISRO_KEYWORD>). "
             "REQUIRED for synthesis. Not required when using --download_voices alone.",
    )
    parser.add_argument(
        "--count",
        default=600,
        type=int,
        help="Approximate number of samples to generate. Default 600.",
    )
    parser.add_argument(
        "--voices_dir",
        default="piper_voices",
        help="Directory containing .onnx voice model files. Default 'piper_voices'.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory. Defaults to dataset/<KEYWORD>_synthetic/.",
    )
    parser.add_argument(
        "--download_voices",
        action="store_true",
        help="Download all five Piper voice models to --voices_dir, then exit.",
    )
    args = parser.parse_args()

    # ── Download-and-exit mode ────────────────────────────────────────────────
    if args.download_voices:
        print(f"Downloading Piper voice models -> {args.voices_dir}/")
        download_voices(args.voices_dir)
        print("Done. Run again with --keyword DORA --count 600 to synthesise samples.")
        return

    # ── Keyword is required for synthesis ────────────────────────────────────
    if not args.keyword:
        print(
            "[ERROR] --keyword is required for synthesis.\n"
            "        Example: python generate_keyword_dataset.py --keyword DORA --count 600\n"
            "        To download voices only: python generate_keyword_dataset.py --download_voices"
        )
        sys.exit(1)

    # ── Pre-flight checks ────────────────────────────────────────────────────
    if not _check_piper():
        print(
            "[ERROR] 'piper' not found on PATH.\n"
            "        Install with: pip install piper-tts"
        )
        sys.exit(1)

    if not _check_ffmpeg():
        print(
            "[ERROR] 'ffmpeg' not found on PATH.\n"
            "        Install from: https://ffmpeg.org/download.html\n"
            "        (Windows: winget install Gyan.FFmpeg)"
        )
        sys.exit(1)

    kw      = args.keyword.strip()          # keep original casing for Piper input
    kw_up   = kw.upper()                    # for directory naming
    out_dir = args.output or os.path.join("dataset", f"{kw_up}_synthetic")
    os.makedirs(out_dir, exist_ok=True)

    # ── Discover voice models ─────────────────────────────────────────────────
    if not os.path.isdir(args.voices_dir):
        print(
            f"[ERROR] Voices directory not found: {args.voices_dir}\n"
            f"        Run: python generate_keyword_dataset.py --download_voices"
        )
        sys.exit(1)

    voice_files = sorted(
        str(p)
        for p in Path(args.voices_dir).glob("*.onnx")
        if p.is_file()
    )

    if not voice_files:
        print(
            f"[ERROR] No .onnx files in {args.voices_dir}.\n"
            f"        Run: python generate_keyword_dataset.py --download_voices"
        )
        sys.exit(1)

    # ── Generation plan ──────────────────────────────────────────────────────
    sps = max(1, (args.count // len(voice_files)) // len(SPEEDS))

    print(f"\nKeyword        : {kw}")
    print(f"Voice models   : {len(voice_files)}")
    print(f"Speeds         : {SPEEDS}")
    print(f"Samples/speed  : {sps}")
    print(f"Target count   : ≈ {len(voice_files) * len(SPEEDS) * sps}")
    print(f"Output         : {out_dir}")
    print(f"Output format  : {TARGET_SR} Hz mono PCM_16\n")

    idx = ok = fail = skipped = resample_fail = 0

    for vpath in voice_files:
        vname = Path(vpath).stem
        vc    = 0

        for spd in SPEEDS:
            for _ in range(sps):
                out_file = os.path.join(out_dir, f"{kw_up.lower()}_{idx:05d}.wav")

                if os.path.exists(out_file):
                    # Verify it is already 16 kHz; resample if not
                    if _probe_sample_rate(out_file) != TARGET_SR:
                        _resample_to_16k(out_file)
                    idx     += 1
                    vc      += 1
                    skipped += 1
                    continue

                # Call Piper to generate
                result = subprocess.run(
                    [
                        "piper",
                        "--model",        vpath,
                        "--length-scale", str(round(spd, 2)),
                        "--output-file",  out_file,
                    ],
                    input=kw.encode(),
                    capture_output=True,
                )

                if result.returncode != 0:
                    err = result.stderr.decode(errors="replace")[:120]
                    print(f"  [WARN] Piper failed ({vname} spd={spd}): {err}")
                    fail += 1
                    idx  += 1
                    continue

                # Resample to 16 kHz (Piper typically outputs 22050 Hz)
                native_sr = _probe_sample_rate(out_file)
                if native_sr != TARGET_SR:
                    if not _resample_to_16k(out_file):
                        print(f"  [WARN] Resample failed: {out_file}")
                        os.remove(out_file)
                        resample_fail += 1
                        idx += 1
                        continue

                ok  += 1
                vc  += 1
                idx += 1

        print(f"  {vname}: {vc} samples")

    # ── Spot-check a few output files ────────────────────────────────────────
    sample_files = sorted(Path(out_dir).glob("*.wav"))[:5]
    bad_sr = [
        str(f) for f in sample_files
        if _probe_sample_rate(str(f)) != TARGET_SR
    ]
    if bad_sr:
        print(f"\n[ERROR] {len(bad_sr)} file(s) are NOT {TARGET_SR} Hz after resample:")
        for b in bad_sr:
            print(f"  {b}")
        sys.exit(1)

    total_out = len(list(Path(out_dir).glob("*.wav")))
    print(f"\n{'─'*54}")
    print(f"  Keyword        : {kw}")
    print(f"  Generated      : {ok}")
    print(f"  Skipped        : {skipped}  (already existed)")
    print(f"  Piper failures : {fail}")
    print(f"  Resamp. fail   : {resample_fail}")
    print(f"  Total in dir   : {total_out}")
    print(f"  Format check   : {TARGET_SR} Hz mono PCM_16 ✓")
    print(f"{'─'*54}")

    if fail + resample_fail > 0:
        print(
            f"\n[WARN] {fail + resample_fail} file(s) could not be generated.\n"
            f"       Review messages above and rerun to fill gaps."
        )


if __name__ == "__main__":
    main()
