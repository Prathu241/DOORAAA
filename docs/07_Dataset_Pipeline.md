# Dataset Pipeline
## Document 07 — SIH26172 | DORA

---

## 1. Dataset Requirements

| Class | Minimum Count | Source |
|---|---|---|
| Keyword positives | ≥ 1,500 | TTS synthesis + real recordings + augmentation |
| Hard negatives (phonetically similar) | ≥ 300 | Manual + Common Voice |
| Unknown speech | ≥ 3,000 | Google Speech Commands v0.02 |
| Background / noise | ≥ 1,000 | MUSAN |
| **Grand total** | **≥ 5,800** | |

---

## 2. Final Dataset Composition (DORA)

| Class | Count | Source |
|---|---|---|
| DORA — real (existing recordings) | ~220 | Manual recordings |
| DORA — synthetic (Piper TTS) | ~550 | `generate_keyword_dataset.py` |
| DORA — augmented (4× real) | ~880 | `augment_real.py` |
| **Total positives** | **~1,650** | |
| Hard negatives | ~300 | Manual + Common Voice |
| Unknown speech | ~3,000 | Google Speech Commands v0.02 |
| Background / noise | ~1,000 | MUSAN clips |
| **Total negatives** | **~4,300** | |
| **Grand total** | **~5,950** | |

---

## 3. Script 1 — Piper TTS Synthesis (~550 samples)

**Why TTS is the primary positive source, not a backup:**

Piper generates 5 distinct synthetic voices × 9 speaking speeds. Each combination produces a different acoustic realisation of the keyword. The model learns the phoneme pattern of the word — not one person's voice. This is exactly what generalises to an ISRO judge's unfamiliar voice.

This method is used by microWakeWord's own production keywords.

### 3.1 Voice Model Download (one-time, do NOW while online)

```bash
mkdir -p piper_voices && cd piper_voices

wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_IN/medium/en_IN-female-medium.onnx"
wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_IN/medium/en_IN-female-medium.onnx.json"

wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx"
wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx.json"

wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"

wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx"
wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json"

wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/hemant/medium/hi_IN-hemant-medium.onnx"
wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/hemant/medium/hi_IN-hemant-medium.onnx.json"

cd ..
```

### 3.2 Usage

```bash
python generate_keyword_dataset.py --keyword DORA --count 600
# Output: dataset/DORA_synthetic/  (~550 .wav files)
# Works for any keyword — reuse at grand finale with --keyword AGNI
```

### 3.3 How It Works

- Iterates 5 voices × 9 speeds (0.75× to 1.30×) × N samples
- Calls `piper` CLI with each voice model and length-scale parameter
- Outputs 16 kHz mono WAV files named `dora_00001.wav`, `dora_00002.wav`, etc.
- If a voice model is missing, it skips that voice and continues

---

## 4. Script 2 — Manual Recording (~120 samples)

**Target:** 6 team members × 20 recordings each = 120 real human samples

### 4.1 Usage

```bash
# Run once per team member — increment --speaker each time
python record_keyword.py --keyword DORA --speaker spk001 --count 20
python record_keyword.py --keyword DORA --speaker spk002 --count 20
# ... up to spk006
```

### 4.2 Recording Protocol

- **Duration per recording:** 1.5 seconds (~0.4s silence + keyword + ~0.5s silence)
- **Vary across takes:** distance from mic (0.3m, 0.6m, 1m), speaking speed, volume
- **Output:** `dataset/DORA_real/dora_spk001_000.wav`, `dora_spk001_001.wav`, ...

> **Critical:** The `spkXXX` token in the filename is used by `prepare_dataset.py` to split speakers between train/val/test. Never use the same speaker ID for two different people.

---

## 5. Script 3 — Augmentation (4× real recordings, ~480 extra samples)

Augmentation simulates real acoustic conditions without additional recording sessions.

### 5.1 Usage

```bash
python augment_real.py --keyword DORA
# Reads: dataset/DORA_real/
# Writes: dataset/DORA_augmented/  (4 variants per original file)
```

### 5.2 Four Augmentation Variants

| Variant | What it simulates | Implementation |
|---|---|---|
| Additive noise (SNR 10–20 dB) | Background chatter, fan noise | Random Gaussian noise at computed power |
| Pitch shift ±1–2 semitones | Different vocal tracts | `librosa.effects.pitch_shift` |
| Speed perturbation ±10% | Natural speaking rate variation | `librosa.effects.time_stretch` |
| Reverb (exponential decay IR) | Far-field, room echo | `np.convolve` with impulse response |

---

## 6. Script 4 — Merge + Speaker-Split

Merges all positive sources and splits by **speaker**, not by file. This prevents data leakage: if any file from a speaker is in the training set, all files from that speaker stay in training.

### 6.1 Usage

```bash
python prepare_dataset.py --keyword DORA --train_ratio 0.70 --val_ratio 0.15
# Output:
#   dataset/split/train/DORA/  ← 70% of speakers + all synthetic
#   dataset/split/val/DORA/    ← 15% of speakers
#   dataset/split/test/DORA/   ← 15% of speakers (unseen, used for final eval only)
```

### 6.2 Split Logic

```
All speakers → random shuffle
Train: first 70% of speakers + ALL synthetic/augmented files (no speaker ID)
Val:   next 15% of speakers
Test:  remaining 15% of speakers — NEVER seen during training or threshold sweep
```

---

## 7. Negatives Setup (one-time download)

```bash
# Unknown speech class — Google Speech Commands v0.02
wget http://download.tensorflow.org/data/speech_commands_v0.02.tar.gz
mkdir -p dataset/unknown
tar -xzf speech_commands_v0.02.tar.gz -C dataset/unknown/

# Background / noise class — MUSAN
wget https://www.openslr.org/resources/17/musan.tar.gz
mkdir -p dataset/background
tar -xzf musan.tar.gz -C dataset/background/

# Hard negatives — phonetically similar words to DORA:
# "door", "draw", "Nora", "Sora", "adora", "flora", "more", "four"
# Record or source from Mozilla Common Voice
# Place in dataset/unknown/ alongside Speech Commands
```

### 7.1 Why Hard Negatives Matter

Without phonetically similar negatives, the model learns "any word that sounds vaguely like DORA" triggers detection. Hard negatives force it to learn the precise phoneme sequence /d ɔː r ə/ and reject near-misses.

---

## 8. Dataset Directory Structure

```
dataset/
├── DORA_synthetic/          ← Piper TTS output (no speaker ID in filename)
├── DORA_real/               ← Manual recordings (spkXXX in filename)
├── DORA_augmented/          ← 4× augmented real (spkXXX preserved in stem)
├── DORA/                    ← Merged positives (prepare_dataset.py input)
├── unknown/                 ← Speech Commands v0.02 + hard negatives
├── background/              ← MUSAN clips
└── split/
    ├── train/DORA/          ← Training set positives
    ├── val/DORA/            ← Validation set positives
    └── test/DORA/           ← Test set positives (held out until final eval)
```

---

## 9. Grand Finale Dataset Swap Summary

When ISRO announces a new keyword (e.g., "AGNI"), the full dataset pipeline runs in ~50 minutes:

| Step | Script | Time |
|---|---|---|
| TTS synthesis (auto) | `generate_keyword_dataset.py --keyword AGNI` | 15 min |
| Manual recordings (6 speakers) | `record_keyword.py --keyword AGNI` | 30 min |
| Augmentation (auto) | `augment_real.py --keyword AGNI` | 5 min |
| Merge + split (auto) | `prepare_dataset.py --keyword AGNI` | < 1 min |
| **Total** | | **~51 min** |

Negatives are keyword-agnostic and do not need to be re-collected.
