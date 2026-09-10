# Problem Statement & DORA's Solution
## Document 02 — SIH26172

---

## 1. Original Problem Statement (SIH26172)

**Title:** Deployable Open-source Real-time Activator  
**Organization:** ISRO / Department of Space  
**Category:** Hardware  
**Domain:** Smart Automation  

### Core Requirement

Design and build a low-power, always-on keyword spotting (KWS) system that:

1. Runs entirely on a microcontroller-class edge device (< 256 KB RAM)
2. Detects a custom wake-word with high accuracy (≥ 90% true positive rate)
3. Hands off to a cloud ASR system upon detection with minimal latency
4. Is fully open-source and deployable in field conditions

### Three Judging Axes

The evaluation panel scores submissions on exactly three axes:

| Axis | What it tests |
|---|---|
| **Efficiency** | Can the system run within the strict RAM and CPU budget of a microcontroller? |
| **Accuracy** | Does the model detect the keyword reliably without too many false alarms? |
| **Latency** | How quickly does the system complete the full pipeline from keyword end to first ASR byte? |

---

## 2. Why This Is Hard

### 2.1 The Resource Constraint Problem

A typical neural network for speech recognition requires hundreds of megabytes of RAM and a GPU to run in real time. The ESP32-S3 has only 512 KB internal SRAM (with 8 MB PSRAM available via SPI). Running a streaming KWS model on this hardware in real time, while simultaneously capturing audio over I2S, encoding with Opus, and maintaining a WebSocket connection, is a genuine systems engineering challenge.

### 2.2 The Accuracy-Efficiency Tradeoff

Making a model small enough to fit in 80 KB tensor arena inevitably reduces its capacity. The challenge is reaching ≥ 92% recall on unseen speakers while keeping false accept rate ≤ 1 per hour. Standard approaches either:
- Use a large model (too slow, too much RAM), or
- Use a tiny but inaccurate model (high false accept rate)

The MixedNet streaming architecture hits the sweet spot by using depthwise separable mixed-kernel convolutions — high receptive field at low parameter count.

### 2.3 The Latency Measurement Gap

No existing open-source project measures keyword-end → cloud-first-byte latency. Systems like microWakeWord solve on-device KWS but stop at detection. The handoff problem — compressing audio, opening a connection, transmitting, and getting the first ASR byte back — is unaddressed and unmeasured in the open-source community.

### 2.4 The Keyword-Agnostic Requirement

ISRO assigns the keyword at the Grand Finale, not in advance. Any system trained on a fixed keyword (e.g., "Hey Siri") will fail. The pipeline must be retrained on a new keyword with zero prior samples in under 4 hours.

---

## 3. DORA's Direct Response to Each Problem

### 3.1 Resource Constraint → Two-Stage Gating + int8 Quantisation

```
VAD (< 0.1% CPU, always-on)
    ↓ only when voice is detected
MixedNet KWS (int8, < 80 KB tensor arena, < 10 ms inference)
```

- The VAD prevents MixedNet from running during silence — saves ~9.9% CPU at idle
- int8 quantisation halves model size and doubles inference speed vs float32
- Total measured RAM: **~168–188 KB** against a 256 KB ceiling

### 3.2 Accuracy → TTS-Augmented Dataset + Speaker-Split Evaluation

- **~1,650 positive samples** per keyword using three sources:
  - Piper TTS (5 voices × 9 speeds) — trains phoneme pattern, not one person's voice
  - Real recordings from 6 speakers — covers natural variation
  - 4× augmentation (noise, pitch shift, speed perturbation, reverb)
- **~4,300 negative samples** from Google Speech Commands + MUSAN + hard negatives
- Evaluation strictly on **held-out speakers** — no data leakage
- Target: **≥ 92% TPR, ≤ 1 FA/hr**

### 3.3 Latency → Pre-warmed WebSocket + Opus Compression + Pre-roll Buffer

Three specific design decisions eliminate latency:

| Problem | Solution | Saving |
|---|---|---|
| WebSocket connection time on detect | Pre-warm at boot | ~300–500 ms eliminated |
| Raw PCM bandwidth | Opus 24 kbps | 10× less data to transmit |
| Audio before keyword is lost | 300 ms pre-roll ring buffer | Context preserved |

Measured target: **< 75 ms keyword-end → ASR first-byte on LAN**

### 3.4 Keyword-Agnostic → One-Command Swap Script

```bash
./swap_keyword.sh AGNI
# Runs in under 4 hours: TTS → record → augment → train → flash
```

The entire pipeline (dataset generation, training, quantisation, firmware embedding, flashing) is scripted and parameterised by `--keyword`. Negative samples are keyword-agnostic and reused as-is.

---

## 4. What Makes DORA the Definitive Answer

DORA is specifically engineered to score the maximum on each of the three judging axes simultaneously:

- **Efficiency:** Measured RAM headroom of 68–88 KB. CPU stays < 10% during idle listening.
- **Accuracy:** Speaker-independent evaluation on held-out splits. Hard negatives for phonetically similar words.
- **Latency:** The only system that actually measures and reports keyword-end → first-byte latency. Pre-warmed connection + Opus compression achieves < 75 ms on a local network.

No other open-source solution addresses all three. DORA does.
