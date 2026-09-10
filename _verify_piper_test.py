"""Verify Piper test samples: format, duration, not silent, not clipped."""
import glob, os
import numpy as np
import soundfile as sf

files = sorted(glob.glob("dataset/_piper_test/*.wav"))
print(f"Files to verify: {len(files)}")

errors = []
for f in files:
    info = sf.info(f)
    data, _ = sf.read(f, dtype="float32", always_2d=False)
    if data.ndim > 1:
        data = data[:, 0]
    rms = float(np.sqrt(np.mean(data**2)))
    peak = float(np.max(np.abs(data)))
    dur = info.duration

    problems = []
    if info.samplerate != 16000:
        problems.append(f"sr={info.samplerate}")
    if info.channels != 1:
        problems.append(f"ch={info.channels}")
    if info.subtype not in ("PCM_16", "PCM_S8", "PCM_24"):
        problems.append(f"fmt={info.subtype}")
    if dur < 0.1:
        problems.append(f"too_short={dur:.2f}s")
    if rms < 0.002:
        problems.append(f"silent(rms={rms:.5f})")
    if peak > 0.99:
        problems.append(f"clipped(peak={peak:.3f})")

    status = "OK" if not problems else "!!"
    name = os.path.basename(f)
    print(f"  [{status}] {name:<35}  {info.samplerate}Hz  {info.channels}ch  {info.subtype:<8}  {dur:.2f}s  rms={rms:.4f}")
    if problems:
        errors.append(f"{name}: {', '.join(problems)}")

print()
if errors:
    print(f"ERRORS ({len(errors)}):")
    for e in errors:
        print(f"  {e}")
else:
    print(f"ALL {len(files)} SAMPLES VALID")
    print("  16 kHz, mono, PCM_16, non-silent, non-clipped")
