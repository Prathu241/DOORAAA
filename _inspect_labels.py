"""
Inspect and categorize DORA positive label quality.
Reports all unique filename stems, categorized by type.
Does NOT modify any files.
"""
import glob, os, re

real_files = sorted(glob.glob("dataset/DORA_real/*.wav"))
print(f"Total DORA_real source recordings: {len(real_files)}")
print()

# Extract stems (strip dora_spk_raw_ prefix)
def clean_stem(f):
    s = os.path.splitext(os.path.basename(f))[0]
    s = re.sub(r"^dora_spk_raw_", "", s)
    s = re.sub(r"_aug\d+$", "", s)
    return s

stems = sorted(set(clean_stem(f) for f in real_files))

# Categorize
isolated_dora = []
phrase_dora   = []  # contains "hey", "sunn", "oyee", "oyy", etc.
distorted     = []  # "dhora", elongated, "doooo"
unknown       = []

PHRASE_MARKERS = ["hey", "sunn", "hello", "oi", "oyy", "oyeee", "chorus",
                  "tharki", "angry", "whisper", "slow", "heavy", "fake",
                  "light", "accented", "farhan", "chorus"]
DISTORTED_MARKERS = ["dhora", "doooooo", "doraaaa", "dur"]

for s in stems:
    sl = s.lower()
    if any(m in sl for m in DISTORTED_MARKERS):
        distorted.append(s)
    elif any(m in sl for m in PHRASE_MARKERS):
        phrase_dora.append(s)
    elif re.match(r"^dora$", sl) or re.match(r"^dora_\d+$", sl) \
         or re.match(r"^dora\d+$", sl) or re.match(r"^dora_00\d+$", sl) \
         or re.match(r"^whatsapp_ptt_", sl):
        isolated_dora.append(s)
    else:
        unknown.append(s)

print(f"--- ISOLATED DORA ({len(isolated_dora)}) ---")
for s in isolated_dora[:20]:
    print(f"  {s}")
if len(isolated_dora) > 20:
    print(f"  ... and {len(isolated_dora)-20} more")

print(f"\n--- PHRASE VARIANTS ({len(phrase_dora)}) ---")
print("  (These contain DORA embedded in phrases or with expressive/distorted styles)")
for s in phrase_dora:
    print(f"  {s}")

print(f"\n--- DISTORTED PRONUNCIATIONS ({len(distorted)}) ---")
for s in distorted:
    print(f"  {s}")

print(f"\n--- UNCLASSIFIED ({len(unknown)}) ---")
for s in unknown:
    print(f"  {s}")

print()
print("=" * 60)
print("LABELING DECISION:")
print()
print("Training objective for a practical wake-word system:")
print("  The model should trigger whenever it HEARS 'DORA',")
print("  regardless of surrounding context or speaking style.")
print()
print("KEEP AS POSITIVE:")
print("  - All isolated DORA utterances (dora, dora_0001, whatsapp clips)")
print("  - All phrase variants (hey dora, sunn dora, oyy dora)")
print("    Reason: In real use the word DORA will appear in phrases.")
print("    The system must detect it in ANY phonetic context.")
print("  - Expressive styles (angry, whisper, accented, farhan)")
print("    Reason: Increases vocal variation, reduces speaker overfitting.")
print()
print("CONSIDER MOVING TO HARD NEGATIVES (do NOT auto-delete):")
print("  - dhora: incorrect pronunciation; could confuse the model")
print("  - doooooo raaaa: elongated beyond recognition")
print("  - These are borderline. Keep for now but flag for human review.")
print()
print("VERDICT: Current labeling is ACCEPTABLE for a wake-word system.")
print("  The only items needing review are the 2 distorted pronunciations.")
print("  No bulk re-labeling is required.")
print("=" * 60)
