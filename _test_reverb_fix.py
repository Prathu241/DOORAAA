"""Quick test: verify fixed aug_reverb produces non-silent output."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import soundfile as sf
import librosa

# Replicate the fixed function inline
SR = 16000

def aug_reverb_fixed(audio):
    ir_len = SR // 8
    ir = np.exp(-np.linspace(0, 8, ir_len)).astype(np.float32)
    ir /= ir.max()
    reverbed = np.convolve(audio, ir, mode="same").astype(np.float32)
    src_rms = float(np.sqrt(np.mean(audio ** 2)))
    rev_rms = float(np.sqrt(np.mean(reverbed ** 2)))
    if rev_rms > 1e-9:
        reverbed = reverbed * (src_rms / rev_rms)
    return np.clip(reverbed, -1.0, 1.0).astype(np.float32)

def aug_reverb_old(audio):
    ir_len = SR // 8
    ir = np.exp(-np.linspace(0, 8, ir_len)).astype(np.float32)
    ir /= ir.sum()
    return np.clip(np.convolve(audio, ir, mode="same"), -1.0, 1.0).astype(np.float32)

# Test on first 5 real recordings
import glob
files = sorted(glob.glob("dataset/DORA_real/*.wav"))[:5]
all_ok = True
for f in files:
    audio, _ = librosa.load(f, sr=SR, mono=True)
    src_rms = float(np.sqrt(np.mean(audio**2)))
    old_out = aug_reverb_old(audio)
    new_out = aug_reverb_fixed(audio)
    old_rms = float(np.sqrt(np.mean(old_out**2)))
    new_rms = float(np.sqrt(np.mean(new_out**2)))
    ratio = new_rms / src_rms if src_rms > 0 else 0
    ok = new_rms > 0.002
    all_ok = all_ok and ok
    status = "OK" if ok else "STILL SILENT"
    print(f"  [{status}] {os.path.basename(f)}")
    print(f"    src_rms={src_rms:.5f}  old_rms={old_rms:.7f}  new_rms={new_rms:.5f}  ratio={ratio:.3f}")

print()
if all_ok:
    print("REVERB FIX: VERIFIED -- all test files produce non-silent output.")
else:
    print("REVERB FIX: FAILED -- some files still silent.")
    sys.exit(1)
