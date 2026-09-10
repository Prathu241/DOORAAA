"""
prepare_dataset.py — Base-recording-disjoint train/val/test split.

KEYWORD-GENERIC: contains zero DORA-specific hardcoding.
Pass --keyword explicitly. This script will NEVER read another keyword's data.

Usage:
    python prepare_dataset.py --keyword DORA
    python prepare_dataset.py --keyword AGNI
    python prepare_dataset.py --keyword DORA --train_ratio 0.70 --val_ratio 0.15

SOURCE DIRECTORIES SCANNED (derived from --keyword, never hardcoded):
    dataset/<KEYWORD>_real/        real recordings
    dataset/<KEYWORD>_augmented/   augmented variants  (stem_augN.wav)
    dataset/<KEYWORD>_synthetic/   Piper TTS samples   (no augN suffix)

OUTPUT:
    dataset/split/train/<KEYWORD>/
    dataset/split/val/<KEYWORD>/
    dataset/split/test/<KEYWORD>/

GROUPING CONTRACT (CRITICAL — prevents leakage):
    Group key = filename stem with _augN suffix stripped.
    Example:
        dora_spk001_000.wav        → group "dora_spk001_000"
        dora_spk001_000_aug0.wav   → group "dora_spk001_000"
        dora_spk001_000_aug1.wav   → group "dora_spk001_000"
        dora_spk001_000_aug2.wav   → group "dora_spk001_000"
        dora_spk001_000_aug3.wav   → group "dora_spk001_000"
    All five files → same split. Zero augmentation leakage by construction.

    Synthetic files (no _augN suffix, no speaker token) have no reliable group
    boundary so they are assigned entirely to train only.

SPLIT STRATEGY:
    Groups are split 70/15/15 by count (deterministic, seeded).
    Synthetic files go to train only (they are not speaker-identified).
    If < 3 groups exist the script falls back to file-level split with a warning.
"""

import argparse
import glob
import os
import re
import random
import shutil
import sys
from collections import defaultdict


ROOT = os.path.dirname(os.path.abspath(__file__))


# ── Grouping helpers ──────────────────────────────────────────────────────────

def extract_group(filename: str) -> str:
    """
    Return the base-recording group key for a filename.

    Strips the _augN suffix so that a source file and all its augmented
    variants share the same group key and therefore land in the same split.

    Examples:
        dora_spk001_000.wav        → "dora_spk001_000"
        dora_spk001_000_aug2.wav   → "dora_spk001_000"
        keyword_00042.wav          → "keyword_00042"
        keyword_00042_aug3.wav     → "keyword_00042"
    """
    stem = os.path.splitext(os.path.basename(filename))[0]
    # Strip trailing _aug<digit(s)>
    return re.sub(r"_aug\d+$", "", stem).lower()


def is_synthetic(filename: str) -> bool:
    """
    Returns True if the file looks like a Piper TTS synthetic sample.
    Synthetic files are named keyword_NNNNN.wav (5-digit zero-padded index)
    and contain NO speaker token.
    """
    stem = os.path.splitext(os.path.basename(filename))[0]
    # Synthetic pattern: keyword_00000 through keyword_99999 (no spk token)
    return bool(re.search(r"_\d{4,6}$", stem)) and "spk" not in stem.lower()


# ── File copy helper ──────────────────────────────────────────────────────────

def copy_files(file_list: list, dst_dir: str):
    os.makedirs(dst_dir, exist_ok=True)
    for src in file_list:
        dst = os.path.join(dst_dir, os.path.basename(src))
        if not os.path.exists(dst):
            shutil.copy(src, dst)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Base-recording-disjoint train/val/test split for keyword datasets."
    )
    parser.add_argument(
        "--keyword",
        required=True,
        help="Keyword name (e.g. DORA, AGNI). Determines source directories. "
             "This script will NEVER read another keyword's data.",
    )
    parser.add_argument("--train_ratio", default=0.70, type=float,
                        help="Fraction of groups assigned to train. Default 0.70.")
    parser.add_argument("--val_ratio",   default=0.15, type=float,
                        help="Fraction of groups assigned to val.   Default 0.15.")
    parser.add_argument("--seed",        default=42,   type=int,
                        help="Random seed for reproducible splits.")
    args = parser.parse_args()

    if args.train_ratio + args.val_ratio >= 1.0:
        print("[ERROR] train_ratio + val_ratio must be < 1.0")
        sys.exit(1)

    random.seed(args.seed)
    kw = args.keyword.strip().upper()

    # ── Locate source directories (keyword-specific only) ─────────────────────
    src_dirs = [
        os.path.join(ROOT, "dataset", f"{kw}_real"),
        os.path.join(ROOT, "dataset", f"{kw}_augmented"),
        os.path.join(ROOT, "dataset", f"{kw}_synthetic"),
    ]

    # Collect all WAV files, de-duplicate by basename
    all_files: list[str] = []
    seen_basenames: set[str] = set()
    found_any_dir = False

    for src_dir in src_dirs:
        if not os.path.isdir(src_dir):
            continue
        found_any_dir = True
        for f in sorted(glob.glob(os.path.join(src_dir, "*.wav"))):
            bn = os.path.basename(f)
            if bn not in seen_basenames:
                all_files.append(f)
                seen_basenames.add(bn)

    if not found_any_dir:
        print(
            f"[ERROR] No source directories found for keyword '{kw}'.\n"
            f"        Expected at least one of:\n"
            + "\n".join(f"          {d}" for d in src_dirs)
        )
        sys.exit(1)

    if not all_files:
        print(f"[ERROR] No WAV files found across source dirs for keyword '{kw}'.")
        sys.exit(1)

    print(f"\nKeyword          : {kw}")
    print(f"Total WAV files  : {len(all_files)}")

    # ── Separate synthetic (train-only) from grouped files ────────────────────
    synthetic_files: list[str] = []
    grouped_files: list[str]   = []

    for f in all_files:
        if is_synthetic(os.path.basename(f)):
            synthetic_files.append(f)
        else:
            grouped_files.append(f)

    # ── Build group → file list mapping ──────────────────────────────────────
    by_group: dict[str, list[str]] = defaultdict(list)
    for f in grouped_files:
        grp = extract_group(os.path.basename(f))
        by_group[grp].append(f)

    groups = sorted(by_group.keys())
    random.shuffle(groups)
    n = len(groups)

    print(f"Groups (base recordings) : {n}")
    print(f"Synthetic (train-only)   : {len(synthetic_files)}")

    # ── Split groups ──────────────────────────────────────────────────────────
    if n < 3:
        print(
            f"\n[WARN] Only {n} group(s) found — too few for speaker-disjoint split.\n"
            f"       Falling back to random file-level split."
        )
        all_grouped_flat = grouped_files + synthetic_files
        random.shuffle(all_grouped_flat)
        total = len(all_grouped_flat)
        n_test = max(1, int(total * (1 - args.train_ratio - args.val_ratio)))
        n_val  = max(1, int(total * args.val_ratio))
        test_files  = all_grouped_flat[:n_test]
        val_files   = all_grouped_flat[n_test : n_test + n_val]
        train_files = all_grouped_flat[n_test + n_val :]
    else:
        n_train_grps = max(1, int(n * args.train_ratio))
        n_val_grps   = max(1, int(n * args.val_ratio))
        # test gets the remainder
        train_grps = groups[:n_train_grps]
        val_grps   = groups[n_train_grps : n_train_grps + n_val_grps]
        test_grps  = groups[n_train_grps + n_val_grps :]

        train_files = synthetic_files[:]  # synthetics → train only
        val_files   = []
        test_files  = []

        for grp in train_grps:
            train_files.extend(by_group[grp])
        for grp in val_grps:
            val_files.extend(by_group[grp])
        for grp in test_grps:
            test_files.extend(by_group[grp])

    # ── Verify zero leakage before writing ────────────────────────────────────
    def group_set(files):
        return {extract_group(os.path.basename(f)) for f in files}

    train_grp_set = group_set(train_files)
    val_grp_set   = group_set(val_files)
    test_grp_set  = group_set(test_files)

    tv_overlap = train_grp_set & val_grp_set
    tt_overlap = train_grp_set & test_grp_set
    vt_overlap = val_grp_set   & test_grp_set

    if tv_overlap or tt_overlap or vt_overlap:
        print("\n[CRITICAL] Leakage detected BEFORE writing — aborting.")
        print(f"  Train ∩ Val  : {len(tv_overlap)}  {sorted(tv_overlap)[:3]}")
        print(f"  Train ∩ Test : {len(tt_overlap)}  {sorted(tt_overlap)[:3]}")
        print(f"  Val   ∩ Test : {len(vt_overlap)}  {sorted(vt_overlap)[:3]}")
        sys.exit(1)

    # ── Copy files into split directories ─────────────────────────────────────
    split_root = os.path.join(ROOT, "dataset", "split")
    splits = {"train": train_files, "val": val_files, "test": test_files}

    for split_name, files in splits.items():
        dst = os.path.join(split_root, split_name, kw)
        print(f"\nCopying {len(files):4d} files → {os.path.relpath(dst)}")
        copy_files(files, dst)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'═'*56}")
    print(f"  Keyword            : {kw}")
    print(f"  Total source files : {len(all_files)}")
    print(f"  Groups             : {n}")
    print(f"  Train groups       : {len(train_grp_set) - len(set(extract_group(os.path.basename(f)) for f in synthetic_files))} + {len(synthetic_files)} synthetic")
    print(f"  Val groups         : {len(val_grp_set)}")
    print(f"  Test groups        : {len(test_grp_set)}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Train files        : {len(train_files)}")
    print(f"  Val files          : {len(val_files)}")
    print(f"  Test files         : {len(test_files)}")
    print(f"  ─────────────────────────────────────────────")
    print(f"  Train ∩ Val        : {len(tv_overlap)}  ✓ ZERO")
    print(f"  Train ∩ Test       : {len(tt_overlap)}  ✓ ZERO")
    print(f"  Val   ∩ Test       : {len(vt_overlap)}  ✓ ZERO")
    print(f"{'═'*56}")
    print(f"\nNegative directories (shared, keyword-agnostic):")
    for neg_dir in ["dataset/background_wav", "dataset/unknown_wav"]:
        full = os.path.join(ROOT, neg_dir)
        count = len(glob.glob(os.path.join(full, "*.wav"))) if os.path.isdir(full) else 0
        status = f"{count} WAVs" if count else "NOT FOUND"
        print(f"  {neg_dir:30s} : {status}")
    print()


if __name__ == "__main__":
    main()
