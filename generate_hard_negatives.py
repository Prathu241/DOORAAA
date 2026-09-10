"""
generate_hard_negatives.py — Keyword-generic phonetically-confusable negative generator.

PURPOSE:
    Hard negatives are words/phrases that sound similar to the target keyword
    but must NOT trigger it. Without them the model only sees clearly-wrong
    speech as negatives and will have a high false-accept rate on near-miss words.

USAGE:
    python generate_hard_negatives.py --keyword DORA
    python generate_hard_negatives.py --keyword AGNI
    python generate_hard_negatives.py --keyword DORA --count 200 --output dataset/hard_neg_DORA

KEYWORD-GENERIC DESIGN:
    The script has a built-in phonetic-confusion table for common English/Hindi
    phoneme patterns. For each keyword it auto-derives candidate confusables
    using these rules:
        1. Known confusable table (covers DORA and common SIH-likely words).
        2. Automatic vowel substitution (D-O-R-A → D-U-R-A, D-A-R-A, etc.).
        3. Onset/coda substitution (DORA → MORA, BORA, NORA, etc.).
        4. Syllable reduction/extension (DORA → DOR, DORAH).

    For an UNKNOWN keyword (e.g. ISRO's assigned word), rules 2-4 are applied
    automatically — no code change needed.

OUTPUT FORMAT: 16 kHz mono PCM_16 WAV via Piper TTS.
    Files are saved to: dataset/<KEYWORD>_hard_negatives/

WHAT TO DO WITH THE OUTPUT:
    These files go into dataset/unknown_wav/ (or a keyword-specific subfolder)
    so they are available as negative examples during training.
    They are NOT labelled as the keyword — they are negative examples.

REQUIREMENTS:
    pip install piper-tts
    ffmpeg on PATH
    .onnx voice models in piper_voices/
"""

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# ── Phonetic confusables table ────────────────────────────────────────────────
# Maps keyword → list of confusable words/phrases to generate.
# Key is UPPERCASE. Add entries here as new SIH keywords become known.
# These are generated as negative examples (NOT as the keyword).
KNOWN_CONFUSABLES: dict[str, list[str]] = {
    "DORA": [
        "door", "draw", "Nora", "Sora", "Bora", "Flora", "Mora", "Hora",
        "Dura", "Dara", "Doa", "Dor", "Dorah", "adora", "fedora",
        "Tora", "Cora", "Lora", "Jora", "Gora",
        "dola", "dova", "dowa", "doka",
    ],
    "AGNI": [
        "agony", "Annie", "Agni", "Agna", "Igni", "Ugni", "Agne",
        "ogni", "Akni", "Agri", "Agmi", "Ahni",
        "Ragni", "Magni", "Vagni", "Tagni",
    ],
    "ISRO": [
        "Israel", "Esro", "Asro", "Isra", "Isrow", "Izro",
        "Intro", "Bistro", "Castro",
    ],
}

# Vowel substitution pool (IPA-inspired)
VOWELS     = list("aeiou")
CONSONANTS = list("bcdfghjklmnpqrstvwxyz")

# Speaking speed range (same as TTS synthesis script)
SPEEDS = [0.85, 0.95, 1.00, 1.05, 1.15]

TARGET_SR = 16000


# ── Phoneme helpers ───────────────────────────────────────────────────────────

def auto_confusables(keyword: str) -> list[str]:
    """
    Generate phonetically-close words from a keyword automatically.
    Applied when the keyword is NOT in KNOWN_CONFUSABLES.
    Returns a deduplicated list of candidate strings.
    """
    kw = keyword.strip().upper()
    candidates: list[str] = []

    # 1. Vowel substitutions
    for i, ch in enumerate(kw):
        if ch in "AEIOU":
            for v in VOWELS:
                mutated = kw[:i] + v.upper() + kw[i+1:]
                if mutated != kw:
                    candidates.append(mutated.capitalize())

    # 2. Initial consonant swaps (onset confusables)
    if kw[0] not in "AEIOU":
        for c in "BDFGHJKLMNPRSTVW":
            if c != kw[0]:
                candidates.append((c + kw[1:]).capitalize())

    # 3. Final consonant removal / append
    candidates.append(kw[:-1].capitalize())           # drop last char
    candidates.append((kw + "A").capitalize())        # add trailing vowel
    candidates.append((kw + "AH").capitalize())       # common suffix

    # 4. Simple syllable-level near-misses
    if len(kw) >= 4:
        candidates.append(kw[:3].capitalize())        # first 3 chars
        candidates.append((kw[0] + kw[2:]).capitalize())  # drop 2nd char

    # Deduplicate, remove the keyword itself
    seen: set[str] = {kw}
    return [c for c in candidates if c.upper() not in seen and len(c) >= 2
            and (seen.add(c.upper()) or True)]  # type: ignore[func-returns-value]


def get_confusables(keyword: str) -> list[str]:
    """Return confusable list — from table if known, auto-generated otherwise."""
    kw_up = keyword.strip().upper()
    if kw_up in KNOWN_CONFUSABLES:
        return KNOWN_CONFUSABLES[kw_up]
    print(f"[INFO] '{kw_up}' not in known confusables table — auto-generating.")
    return auto_confusables(kw_up)


# ── ffmpeg / piper helpers ────────────────────────────────────────────────────

def _check_ffmpeg() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False


def _check_piper() -> bool:
    try:
        subprocess.run(["piper", "--help"], capture_output=True)
        return True
    except FileNotFoundError:
        return False


def _resample_to_16k(path: str) -> bool:
    tmp = path + ".tmp16k.wav"
    r = subprocess.run(
        ["ffmpeg", "-y", "-i", path,
         "-ar", str(TARGET_SR), "-ac", "1", "-sample_fmt", "s16", tmp],
        capture_output=True,
    )
    if r.returncode == 0:
        os.replace(tmp, path)
        return True
    if os.path.exists(tmp):
        os.remove(tmp)
    return False


def _probe_sr(path: str) -> int:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a:0",
             "-show_entries", "stream=sample_rate",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True,
        )
        return int(r.stdout.strip())
    except Exception:
        return 0


# ── Synthesis ─────────────────────────────────────────────────────────────────

def synthesise(
    words: list[str],
    voices: list[str],
    out_dir: str,
    count_per_word: int,
) -> tuple[int, int]:
    """
    Synthesise `count_per_word` samples per word using available voices and speeds.
    Returns (ok, fail).
    """
    os.makedirs(out_dir, exist_ok=True)
    ok = fail = 0
    idx = 0

    for word in words:
        word_slug = re.sub(r"[^a-z0-9]", "_", word.lower()).strip("_")
        generated = 0

        for vpath in voices:
            if generated >= count_per_word:
                break
            vname = Path(vpath).stem
            for spd in SPEEDS:
                if generated >= count_per_word:
                    break

                out_file = os.path.join(out_dir, f"neg_{word_slug}_{idx:05d}.wav")

                if os.path.exists(out_file):
                    idx += 1
                    ok  += 1
                    generated += 1
                    continue

                r = subprocess.run(
                    ["piper", "--model", vpath,
                     "--length-scale", str(round(spd, 2)),
                     "--output-file", out_file],
                    input=word.encode(),
                    capture_output=True,
                )

                if r.returncode != 0:
                    fail += 1
                    idx  += 1
                    continue

                if _probe_sr(out_file) != TARGET_SR:
                    if not _resample_to_16k(out_file):
                        os.remove(out_file)
                        fail += 1
                        idx  += 1
                        continue

                ok        += 1
                generated += 1
                idx       += 1

    return ok, fail


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate phonetically-confusable hard negative samples for a keyword. "
            "Keyword-generic — works for any keyword."
        )
    )
    parser.add_argument(
        "--keyword",
        required=True,
        help="Target keyword (e.g. DORA, AGNI). Determines confusable word list.",
    )
    parser.add_argument(
        "--count",
        default=150,
        type=int,
        help="Approximate total hard-negative samples to generate. Default 150.",
    )
    parser.add_argument(
        "--voices_dir",
        default="piper_voices",
        help="Directory with .onnx Piper voice models.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output directory. Defaults to dataset/<KEYWORD>_hard_negatives/.",
    )
    parser.add_argument(
        "--list_only",
        action="store_true",
        help="Print the confusable word list and exit without generating audio.",
    )
    args = parser.parse_args()

    kw      = args.keyword.strip()
    kw_up   = kw.upper()
    out_dir = args.output or os.path.join("dataset", f"{kw_up}_hard_negatives")

    confusables = get_confusables(kw_up)

    print(f"\nKeyword        : {kw_up}")
    print(f"Confusables    : {len(confusables)}")
    for w in confusables:
        print(f"  - {w}")

    if args.list_only:
        print("\n(--list_only: no audio generated)")
        return

    # ── Pre-flight ────────────────────────────────────────────────────────────
    if not _check_piper():
        print("[ERROR] 'piper' not found. pip install piper-tts")
        sys.exit(1)
    if not _check_ffmpeg():
        print("[ERROR] 'ffmpeg' not found on PATH.")
        sys.exit(1)

    if not os.path.isdir(args.voices_dir):
        print(
            f"[ERROR] Voices directory not found: {args.voices_dir}\n"
            f"        python generate_keyword_dataset.py --download_voices"
        )
        sys.exit(1)

    voices = sorted(str(p) for p in Path(args.voices_dir).glob("*.onnx") if p.is_file())
    if not voices:
        print(f"[ERROR] No .onnx files in {args.voices_dir}.")
        sys.exit(1)

    count_per_word = max(1, args.count // len(confusables))
    total_target   = count_per_word * len(confusables)

    print(f"\nOutput         : {out_dir}")
    print(f"Voices         : {len(voices)}")
    print(f"Per-word count : {count_per_word}")
    print(f"Total target   : {total_target}\n")

    ok, fail = synthesise(confusables, voices, out_dir, count_per_word)

    total_out = len(list(Path(out_dir).glob("*.wav")))
    print(f"\n{'─'*54}")
    print(f"  Keyword        : {kw_up}")
    print(f"  Generated      : {ok}")
    print(f"  Failed         : {fail}")
    print(f"  Total in dir   : {total_out}")
    print(f"  Format         : {TARGET_SR} Hz mono PCM_16")
    print(f"{'─'*54}")
    print(
        f"\nNext step: copy these files into dataset/unknown_wav/ so they are\n"
        f"included as negatives during microWakeWord training:\n"
        f"  Copy-Item -Path {out_dir}\\*.wav -Destination dataset\\unknown_wav\\"
    )


if __name__ == "__main__":
    main()
