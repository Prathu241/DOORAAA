"""
record_keyword.py — Interactive real-voice keyword recording

Usage:
    python record_keyword.py --keyword DORA --speaker spk001 --count 20
    python record_keyword.py --keyword DORA --speaker spk002 --count 20
    (run once per team member, incrementing --speaker each time)

Guidelines:
    - Vary distance from microphone (0.3m, 0.6m, 1m) across takes
    - Vary speaking speed and volume
    - Record in the actual demo environment if possible
    - Each recording is ~1.5 seconds: 0.4s silence + keyword + 0.5s silence

Output:
    dataset/DORA_real/dora_spk001_000.wav
    dataset/DORA_real/dora_spk001_001.wav
    ...
"""

import argparse
import os

import numpy as np
import sounddevice as sd
import soundfile as sf


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", required=True, help="Keyword to record, e.g. DORA")
    parser.add_argument("--speaker", required=True, help="Speaker ID, e.g. spk001")
    parser.add_argument("--count",   default=20,   type=int, help="Number of recordings")
    parser.add_argument("--output",  default=None, help="Output directory")
    args = parser.parse_args()

    kw      = args.keyword.strip().upper()
    spk     = args.speaker.strip().lower()
    out_dir = args.output or os.path.join("dataset", f"{kw}_real")
    os.makedirs(out_dir, exist_ok=True)

    SR  = 16000
    DUR = 1.5   # seconds: 0.4s pre-silence + keyword + 0.5s post-silence

    print(f"\nKeyword  : {kw}")
    print(f"Speaker  : {spk}")
    print(f"Output   : {out_dir}")
    print(f"Duration : {DUR}s per recording\n")
    print("Tips:")
    print("  - Vary your distance from the mic (30cm, 60cm, 1m)")
    print("  - Vary speaking speed and volume across takes")
    print("  - Wait for the prompt before speaking\n")

    for i in range(args.count):
        fname = os.path.join(out_dir, f"dora_{spk}_{i:03d}.wav")
        if os.path.exists(fname):
            print(f"  [{i+1:02d}/{args.count}] Already exists — skipping")
            continue

        input(f"  [{i+1:02d}/{args.count}] Press ENTER, then say '{kw}'...")
        print("  ● Recording...", end="", flush=True)
        audio = sd.rec(int(DUR * SR), samplerate=SR, channels=1, dtype="int16")
        sd.wait()
        sf.write(fname, audio, SR)
        print(f"  ✓  saved → {os.path.basename(fname)}")

    print(f"\n{args.count} recordings saved to {out_dir}/")
    spk_num = int("".join(filter(str.isdigit, spk))) if any(c.isdigit() for c in spk) else 1
    next_spk = f"spk{spk_num+1:03d}"
    print(f"Next person: python record_keyword.py --keyword {kw} --speaker {next_spk}")


if __name__ == "__main__":
    main()
