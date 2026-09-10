"""
audit_dataset.py -- Full dataset quality report for any keyword.

Usage:
    python audit_dataset.py --keyword DORA
    python audit_dataset.py --keyword AGNI
    python audit_dataset.py --keyword DORA --verbose

Checks performed:
    FORMAT    : 16 kHz, mono, PCM_16, non-zero length
    CONTENT   : clipping detection, near-silence detection
    DUPLICATES: SHA-256 hash duplicate detection across all splits
    LEAKAGE   : Train/Val/Test group overlap (ALL must be ZERO)
    BALANCE   : positive/negative counts, train/val/test ratios
    GROUPS    : base-recording group counts per split
    NEGATIVES : background_wav and unknown_wav inventory
    DURATION  : min/max/mean/total per split

Exit code:
    0  -- all checks passed
    1  -- one or more checks FAILED
"""

# Force UTF-8 output on Windows to avoid cp1252 crashes
import io
import sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import argparse
import glob
import hashlib
import os
import re
from collections import defaultdict

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.abspath(__file__))

SEP  = "=" * 64
SEP2 = "-" * 64

# ---- Helpers -----------------------------------------------------------------

def extract_group(filename: str) -> str:
    """Strip _augN suffix to get the base-recording group key."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    return re.sub(r"_aug\d+$", "", stem).lower()


def file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def check_wav(path: str) -> dict:
    """
    Check a single WAV file.
    Returns dict: ok, sr, channels, subtype, duration_s, clipped, silent, error
    """
    r = dict(ok=False, sr=0, channels=0, subtype="",
             duration_s=0.0, clipped=False, silent=False, error="")
    try:
        info = sf.info(path)
        r["sr"]         = info.samplerate
        r["channels"]   = info.channels
        r["subtype"]    = info.subtype
        r["duration_s"] = info.duration

        if info.duration < 0.05:
            r["error"] = "too_short"
            return r

        data, _ = sf.read(path, dtype="float32", always_2d=False)
        if data.ndim > 1:
            data = data[:, 0]

        peak = float(np.max(np.abs(data)))
        rms  = float(np.sqrt(np.mean(data ** 2)))

        # Hard-clip check: flagged only if > 1% of samples are at or above 0.98
        # This distinguishes hard clipping from peak normalisation (e.g. Piper TTS output).
        n_near_peak = int(np.sum(np.abs(data) >= 0.98))
        r["clipped"] = (n_near_peak / max(len(data), 1)) > 0.01
        r["silent"]  = rms < 0.002

        if info.samplerate != 16000:
            r["error"] = f"sr={info.samplerate}"
        elif info.channels != 1:
            r["error"] = f"channels={info.channels}"
        elif info.subtype not in ("PCM_16", "PCM_S8", "PCM_24", "FLOAT", "DOUBLE"):
            r["error"] = f"subtype={info.subtype}"
        else:
            r["ok"] = True
    except Exception as exc:
        r["error"] = str(exc)[:80]
    return r


def audit_directory(label: str, wav_dir: str, verbose: bool = False) -> dict:
    """Audit all WAV files in a directory. Returns aggregated stats."""
    files = sorted(glob.glob(os.path.join(wav_dir, "*.wav")))
    stats = dict(
        label=label, count=len(files),
        ok=0, bad_sr=0, bad_ch=0, bad_fmt=0,
        clipped=0, silent=0, zero_len=0, errors=0,
        durations=[], bad_files=[],
    )
    for fpath in files:
        r = check_wav(fpath)
        if r["duration_s"] < 0.05:
            stats["zero_len"] += 1
            stats["bad_files"].append((os.path.basename(fpath), "zero_length"))
            continue
        stats["durations"].append(r["duration_s"])
        if r["ok"]:
            stats["ok"] += 1
        else:
            stats["errors"] += 1
            if "sr="       in r["error"]: stats["bad_sr"]  += 1
            elif "channels" in r["error"]: stats["bad_ch"]  += 1
            elif "subtype"  in r["error"]: stats["bad_fmt"] += 1
            if verbose:
                stats["bad_files"].append((os.path.basename(fpath), r["error"]))
        if r["clipped"]: stats["clipped"] += 1
        if r["silent"]:  stats["silent"]  += 1
    return stats


def print_dir_stats(s: dict, verbose: bool = False):
    d = s["durations"]
    dur_str = (
        f"min={min(d):.2f}s  max={max(d):.2f}s  "
        f"mean={sum(d)/len(d):.2f}s  total={sum(d)/60:.1f}min"
        if d else "N/A"
    )
    flag = "OK" if s["errors"] == 0 and s["zero_len"] == 0 else "!!"
    print(f"  [{flag}] {s['label']:32s}  {s['count']:5d} files")
    print(f"       Duration : {dur_str}")
    print(f"       Format   : ok={s['ok']}  bad_sr={s['bad_sr']}  "
          f"bad_ch={s['bad_ch']}  bad_fmt={s['bad_fmt']}")
    print(f"       Clipped  : {s['clipped']}   Silent: {s['silent']}   "
          f"Zero-len: {s['zero_len']}")
    if verbose and s["bad_files"]:
        for name, reason in s["bad_files"][:10]:
            print(f"         BAD: {name}  ({reason})")


# ---- Main --------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Full dataset quality audit for a keyword dataset."
    )
    parser.add_argument("--keyword", required=True,
                        help="Keyword to audit (e.g. DORA, AGNI).")
    parser.add_argument("--verbose", action="store_true",
                        help="Print names of individual bad files.")
    args = parser.parse_args()

    kw = args.keyword.strip().upper()
    all_failed: list[str] = []

    print(f"\n{SEP}")
    print(f"  DATASET AUDIT -- keyword: {kw}")
    print(f"{SEP}\n")

    # ---- 1. Format audit per directory ---------------------------------------
    print("-- 1. FORMAT & CONTENT AUDIT " + "-" * 35 + "\n")

    dirs_to_audit = [
        (f"{kw}_real",
         os.path.join(ROOT, "dataset", f"{kw}_real")),
        (f"{kw}_augmented",
         os.path.join(ROOT, "dataset", f"{kw}_augmented")),
        ("background_wav",
         os.path.join(ROOT, "dataset", "background_wav")),
        ("unknown_wav",
         os.path.join(ROOT, "dataset", "unknown_wav")),
        (f"split/train/{kw}",
         os.path.join(ROOT, "dataset", "split", "train", kw)),
        (f"split/val/{kw}",
         os.path.join(ROOT, "dataset", "split", "val",   kw)),
        (f"split/test/{kw}",
         os.path.join(ROOT, "dataset", "split", "test",  kw)),
    ]

    all_dir_stats: dict[str, dict] = {}
    for label, dirpath in dirs_to_audit:
        if not os.path.isdir(dirpath):
            print(f"  [--] {label:32s}  NOT FOUND (skipped)")
            print()
            continue
        s = audit_directory(label, dirpath, args.verbose)
        all_dir_stats[label] = s
        print_dir_stats(s, args.verbose)
        print()
        if s["errors"] > 0 or s["zero_len"] > 0:
            all_failed.append(f"Format errors in {label}: "
                               f"errors={s['errors']} zero_len={s['zero_len']}")

    # Report clipped negatives as warning (not failure -- clipping in noise is OK)
    bg_s = all_dir_stats.get("background_wav", {})
    if bg_s.get("clipped", 0) > 0:
        print(f"  [WARN] background_wav: {bg_s['clipped']} clipped files.\n"
              f"         Clipping in background noise clips is acceptable but\n"
              f"         check that these are genuinely noise (not keyword recordings).\n")

    unk_s = all_dir_stats.get("unknown_wav", {})
    if unk_s.get("clipped", 0) > 0:
        print(f"  [WARN] unknown_wav: {unk_s['clipped']} clipped files.\n"
              f"         Review whether clipping is from recording level or corruption.\n")

    # Augmented silent files warning
    aug_s = all_dir_stats.get(f"{kw}_augmented", {})
    if aug_s.get("silent", 0) > 0:
        print(f"  [WARN] {kw}_augmented: {aug_s['silent']} near-silent files.\n"
              f"         These are likely reverb aug3 variants of very short clips.\n"
              f"         Not fatal but review if count is large.\n")

    # ---- 2. Duplicate detection ----------------------------------------------
    print("-- 2. DUPLICATE DETECTION " + "-" * 38 + "\n")
    all_split_files: list[str] = []
    for split in ("train", "val", "test"):
        d = os.path.join(ROOT, "dataset", "split", split, kw)
        if os.path.isdir(d):
            all_split_files.extend(glob.glob(os.path.join(d, "*.wav")))

    if all_split_files:
        hash_to_files: dict[str, list[str]] = defaultdict(list)
        for fpath in all_split_files:
            h = file_sha256(fpath)
            hash_to_files[h].append(os.path.basename(fpath))

        dups = {h: v for h, v in hash_to_files.items() if len(v) > 1}
        if dups:
            print(f"  [!!] {len(dups)} duplicate group(s) found:")
            for h, files in list(dups.items())[:5]:
                print(f"       {files}")
            all_failed.append(f"Duplicates: {len(dups)} groups")
        else:
            print(f"  [OK] No duplicate files across train/val/test splits.")
    else:
        print(f"  [--] No split files found -- skipping duplicate check.")
    print()

    # ---- 3. Leakage analysis -------------------------------------------------
    print("-- 3. LEAKAGE ANALYSIS " + "-" * 41 + "\n")

    def load_groups(split: str) -> set[str]:
        d = os.path.join(ROOT, "dataset", "split", split, kw)
        if not os.path.isdir(d):
            return set()
        return {
            extract_group(os.path.basename(f))
            for f in glob.glob(os.path.join(d, "*.wav"))
        }

    train_grps = load_groups("train")
    val_grps   = load_groups("val")
    test_grps  = load_groups("test")

    tv = train_grps & val_grps
    tt = train_grps & test_grps
    vt = val_grps   & test_grps

    for label, overlap in [
        ("Train ^ Val  overlap", tv),
        ("Train ^ Test overlap", tt),
        ("Val   ^ Test overlap", vt),
    ]:
        if overlap:
            print(f"  [!!] {label}: {len(overlap)} group(s) LEAKED")
            for g in sorted(overlap)[:3]:
                print(f"       {g}")
        else:
            print(f"  [OK] {label}: 0  -- ZERO (correct)")

    print()
    if tv: all_failed.append(f"Train^Val  leakage: {len(tv)} groups")
    if tt: all_failed.append(f"Train^Test leakage: {len(tt)} groups")
    if vt: all_failed.append(f"Val^Test   leakage: {len(vt)} groups")

    # ---- 4. Group counts -----------------------------------------------------
    print("-- 4. GROUP (BASE-RECORDING) COUNTS " + "-" * 28 + "\n")
    all_grps = train_grps | val_grps | test_grps
    print(f"  Train groups  : {len(train_grps)}")
    print(f"  Val   groups  : {len(val_grps)}")
    print(f"  Test  groups  : {len(test_grps)}")
    print(f"  Total unique  : {len(all_grps)}")
    print()

    # ---- 5. Dataset balance --------------------------------------------------
    print("-- 5. DATASET BALANCE " + "-" * 42 + "\n")

    def count_wav(d):
        return len(glob.glob(os.path.join(d, "*.wav"))) if os.path.isdir(d) else 0

    n_train = count_wav(os.path.join(ROOT, "dataset", "split", "train", kw))
    n_val   = count_wav(os.path.join(ROOT, "dataset", "split", "val",   kw))
    n_test  = count_wav(os.path.join(ROOT, "dataset", "split", "test",  kw))
    n_pos   = n_train + n_val + n_test
    n_bg    = count_wav(os.path.join(ROOT, "dataset", "background_wav"))
    n_unk   = count_wav(os.path.join(ROOT, "dataset", "unknown_wav"))
    n_neg   = n_bg + n_unk
    n_total = n_pos + n_neg

    def pct(n, tot):
        return f"{100*n/tot:.1f}%" if tot else "N/A"

    print(f"  Positives (keyword)  : {n_pos:5d}  ({pct(n_pos, n_total)} of total)")
    print(f"    Train              : {n_train:5d}")
    print(f"    Val                : {n_val:5d}")
    print(f"    Test               : {n_test:5d}")
    print(f"  Negatives            : {n_neg:5d}  ({pct(n_neg, n_total)} of total)")
    print(f"    background_wav     : {n_bg:5d}")
    print(f"    unknown_wav        : {n_unk:5d}")
    print(f"  Grand total          : {n_total:5d}")

    ratio = round(n_neg / n_pos, 2) if n_pos else 0
    ratio_ok = ratio >= 3.0
    ratio_flag = "OK" if ratio_ok else "WARN"
    print(f"  Pos:Neg ratio        : 1:{ratio}  [{ratio_flag}]"
          f"  (target >= 1:3 for robust training)")
    print()

    if not ratio_ok:
        all_failed.append(
            f"Pos:Neg ratio 1:{ratio} < 1:3 -- "
            f"download microWakeWord official negative datasets before training"
        )

    # ---- 6. Negative audio duration ------------------------------------------
    print("-- 6. NEGATIVE AUDIO DURATION " + "-" * 34 + "\n")
    neg_total_min = 0.0
    for label in ("background_wav", "unknown_wav"):
        s = all_dir_stats.get(label, {})
        dur = s.get("durations", [])
        total_min = sum(dur) / 60 if dur else 0.0
        neg_total_min += total_min
        print(f"  {label:24s} : {total_min:.1f} min")

    if neg_total_min < 30:
        print(f"\n  [WARN] Total negative audio = {neg_total_min:.1f} min.")
        print(f"         Recommended >= 30 min for robust FA rate testing.")
        print(f"         Download official negatives (see docs/07_Dataset_Pipeline.md):")
        print(f"           dinner_party.zip, speech.zip, no_speech.zip from")
        print(f"           https://huggingface.co/datasets/kahrendt/microwakeword")
        all_failed.append(
            f"Only {neg_total_min:.1f} min of negative audio -- "
            f"insufficient for robust false-accept testing"
        )
    else:
        print(f"\n  [OK] {neg_total_min:.1f} min negative audio (>= 30 min threshold met).")
    print()

    # ---- 7. Source vs augmented breakdown ------------------------------------
    print("-- 7. SOURCE vs AUGMENTED BREAKDOWN " + "-" * 28 + "\n")
    all_pos_files: list[str] = []
    for split in ("train", "val", "test"):
        d = os.path.join(ROOT, "dataset", "split", split, kw)
        if os.path.isdir(d):
            all_pos_files.extend(glob.glob(os.path.join(d, "*.wav")))

    n_source = sum(1 for f in all_pos_files
                   if not re.search(r"_aug\d+\.wav$", os.path.basename(f)))
    n_aug    = len(all_pos_files) - n_source
    print(f"  Source recordings   : {n_source}")
    print(f"  Augmented variants  : {n_aug}")
    if n_source:
        print(f"  Augment multiplier  : {round(n_aug/n_source, 1)}x")
    print()

    # ---- 8. Final verdict ----------------------------------------------------
    print(SEP)
    if not all_failed:
        print(f"  RESULT: ALL CHECKS PASSED -- keyword: {kw}")
        print(f"  Dataset is format-correct and split-leak-free.")
        print(f"  Safe to proceed to training configuration (Step 9).")
    else:
        print(f"  RESULT: {len(all_failed)} CHECK(S) FAILED -- keyword: {kw}")
        for i, msg in enumerate(all_failed, 1):
            print(f"    [{i}] {msg}")
        print()
        print(f"  Fix the above before training.")
    print(SEP + "\n")

    sys.exit(0 if not all_failed else 1)


if __name__ == "__main__":
    main()
