"""Inspect near-silent augmented files."""
import glob, os, re
import numpy as np
import soundfile as sf

aug_files = sorted(glob.glob("dataset/DORA_augmented/*.wav"))
silent = []
for f in aug_files:
    data, sr = sf.read(f, dtype="float32", always_2d=False)
    if data.ndim > 1:
        data = data[:, 0]
    rms = float(np.sqrt(np.mean(data ** 2)))
    if rms < 0.002:
        stem = os.path.splitext(os.path.basename(f))[0]
        m = re.search(r"_aug(\d+)$", stem)
        aug_n = int(m.group(1)) if m else -1
        source_stem = re.sub(r"_aug\d+$", "", stem)
        src_path = f"dataset/DORA_real/{source_stem}.wav"
        src_rms = None
        if os.path.exists(src_path):
            sd, _ = sf.read(src_path, dtype="float32", always_2d=False)
            if sd.ndim > 1:
                sd = sd[:, 0]
            src_rms = float(np.sqrt(np.mean(sd ** 2)))
        dur = len(data) / sr
        silent.append({
            "file": os.path.basename(f),
            "aug_n": aug_n,
            "rms": round(rms, 7),
            "dur": round(dur, 2),
            "src_rms": round(src_rms, 5) if src_rms is not None else "no_src",
            "source_stem": source_stem,
        })

aug_names = {0: "noise", 1: "pitch", 2: "speed", 3: "reverb"}
print(f"Near-silent augmented files (RMS < 0.002): {len(silent)}")
counts = {}
for s in silent:
    counts[s["aug_n"]] = counts.get(s["aug_n"], 0) + 1
print("\nBreakdown by augmentation variant:")
for n in sorted(counts):
    print(f"  aug{n} ({aug_names.get(n,'?')}): {counts[n]} files")

print("\nFirst 15 samples:")
for s in silent[:15]:
    print(f"  {s['file']:<55}  rms={s['rms']:<10}  dur={s['dur']}s  src_rms={s['src_rms']}")

# Check if source files themselves are short or silent
short_sources = set()
silent_sources = set()
for s in silent:
    stem = s["source_stem"]
    src_path = f"dataset/DORA_real/{stem}.wav"
    if os.path.exists(src_path):
        sd, sr2 = sf.read(src_path, dtype="float32", always_2d=False)
        if sd.ndim > 1:
            sd = sd[:, 0]
        if len(sd) / sr2 < 0.5:
            short_sources.add(stem)
        if float(np.sqrt(np.mean(sd ** 2))) < 0.01:
            silent_sources.add(stem)

print(f"\nUnique source stems with silent aug3: {len(set(s['source_stem'] for s in silent if s['aug_n']==3))}")
print(f"Short source files (< 0.5s): {len(short_sources)}")
print(f"Silent source files (RMS < 0.01): {len(silent_sources)}")
