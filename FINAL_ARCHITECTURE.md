# FINAL ARCHITECTURE — v4.1 Specification

**Source:** <cite index="1-1,1-4,1-5">DORA_Winning_Solution_v4.1 — FINAL, TECHNICALLY-CORRECTED</cite>

**Project:** SIH26172 — Low Latency and Efficient Voice Activator for Edge Devices

**Organization:** Indian Space Research Organisation (ISRO)

**Category:** Hardware | Theme: Smart Automation

**Deadline:** 30 September 2026

---

## 1. DESIGN DRIVER — KEYWORD AGNOSTIC

<cite index="1-6,1-7">The problem statement does not say teams may pick any custom keyword and ship it — it says the model must "work for the given custom key word." The keyword is given to teams, most plausibly only at the grand-finale evaluation stage. That single line means the deliverable was never "a trained DORA model" — it is a pipeline that turns any newly-announced keyword into a flashed, working, benchmarked device within a few hours.</cite>

<cite index="1-8">DORA remains the development keyword used to build and rehearse that pipeline.</cite>

**Deliverable:** 
- **NOT** a static DORA model
- **NOT** a one-time build
- **YES** a keyword-agnostic pipeline: `KEYWORD → DATASET → TRAIN → QUANTIZE → FIRMWARE → FLASH`

---

## 2. PRIOR ART & ARCHITECTURE CHOICE

<cite index="1-9,1-10">After checking the official problem statement against sih.gov.in's tracked data and surveying the open-source wake-word market, microWakeWord — the engine that actually ships inside Home Assistant's ESP32-S3 voice hardware today — is the closest and strongest prior art. This design adopts its proven architecture family rather than defending a choice against a 2017 paper alone, and directs original engineering effort at the part of the problem that stays genuinely unsolved by any existing open-source project: the latency-optimized edge-to-cloud handoff.</cite>

<cite index="1-41">Architecture: Streaming Inception network, evolved to "MixedNet" (MixConv mixed depthwise-separable convolutions) in v2</cite>

**NO REINVENTION.** Streaming MixedNet is final.

---

## 3. SYSTEM ARCHITECTURE

<cite index="1-46,1-47,1-48,1-49,1-50,1-51">Final pipeline: Mic (I2S) → VAD Model → Streaming MixedNet → Pre-roll + Stream → Vosk ASR → App/Dashboard. Tier 0 (VAD model, always-on, sub-1% CPU) and Tier 1 (streaming MixedNet KWS, triggered only on VAD-positive windows) reproduce the architecture family already proven on this chip. Tier 2 (pre-roll buffer flush + pre-warmed WebSocket stream to Vosk) and Tier 3 (cloud ASR + live telemetry dashboard) are the original contribution this submission adds on top. This pipeline is keyword-agnostic end to end — nothing in Tiers 0–3 changes based on which word is currently trained.</cite>

### Tier 0: Always-On VAD
- Continuous voice activity detection
- Sub-0.1% CPU cost
- Gates Tier 1 KWS invocation

### Tier 1: Streaming MixedNet KWS
- Triggered only on VAD-positive frames
- 20–30 ms stride inference
- < 10 ms latency per call
- 5-frame sliding-window averaging for decision smoothing
- Binary classifier: `keyword / not-keyword`

### Tier 2: Pre-Roll + Streaming
- <cite index="1-52,1-53,1-54">300 ms pre-roll buffer. The first working milestone should stream raw 16-bit PCM directly (ESP32 → WebSocket → Vosk), since that is the path guaranteed to work with an unmodified Vosk server. Opus encoding is added afterward as a bandwidth optimization, paired with an explicit server-side Opus-decode step before the audio reaches Vosk.</cite>

### Tier 3: Cloud ASR + Dashboard
- <cite index="1-87">Vosk (Kaldi-based), unchanged: true low-latency streaming API, CPU-only, matches a hackathon-provisioned server without GPU dependency.</cite>
- <cite index="1-88">Entirely keyword-independent — it transcribes whatever comes after the wake word, regardless of what the wake word itself is.</cite>

---

## 4. FRONT-END SPECIFICATION

<cite index="1-56">16 kHz mono, 16-bit PCM input. micro_speech-style preprocessor: 40 spectrogram features generated over a 30 ms window, new features every 10 ms. Streaming input: the model consumes only the newest feature slice per inference call, not a full re-computed window.</cite>

---

## 5. CLASSIFIER — STREAMING MIXEDNET

<cite index="1-56">A depthwise-separable convolutional network using MixConv (mixed-kernel-size depthwise convolutions), converted to streaming form so each inference only processes the newest audio stride rather than recomputing the full window.</cite>

<cite index="1-57">Output: a single probability (wake word / not wake word) per 20–30 ms stride; a 5-frame sliding-window average against a probability cutoff (not a bare single-frame threshold) triggers detection.</cite>

<cite index="1-58,1-59,1-60">Binary training target: <keyword> / not-keyword, trained from scratch each time a keyword changes. The negative class is deliberately built from unknown speech, background noise, and hard negatives so it covers that ground at the dataset level rather than as separate output classes. No reuse of any released microWakeWord keyword model — only the open architecture and training code are reused, not any trained weights.</cite>

---

## 6. QUANTIZATION & DEPLOYMENT

<cite index="1-61">Train float32 in TensorFlow → convert to streaming TFLite → full-integer uint8/int8 quantization → deploy via TensorFlow Lite for Microcontrollers, exactly as the prior art does.</cite>

<cite index="1-62">Reuse the open-source spectrogram feature-generation component (a C implementation of the micro_speech preprocessor) rather than hand-rolling FFT/Mel code.</cite>

<cite index="1-63">Fresh training runs must pass --restore_checkpoint 0; that flag defaults to resuming an existing checkpoint (1), which is the wrong setting for a new keyword's first training run.</cite>

---

## 7. DATASET & TRAINING — KEYWORD-PARAMETERIZED

<cite index="1-65,1-66,1-67">Real positives: a recording drive — real speaker diversity is not replaceable by synthetic data alone. For a finale keyword, this shrinks to whichever teammates are on-site. Synthetic positives: generate a large batch of additional keyword samples using an open-source TTS sample generator (the same Piper-based tool the prior art uses), instantly multiplying effective positive-class size without waiting on more recording sessions.</cite>

<cite index="1-68">Negatives/unknown: Google Speech Commands v0.02 + Mozilla Common Voice (Indian-English/Hindi included for accent match) — keyword-independent, prepared once and reused for every keyword.</cite>

<cite index="1-69">Background/noise: MUSAN + DEMAND + self-recorded deployment-environment noise — also keyword-independent and reused as-is.</cite>

<cite index="1-70">Hard negatives: phonetically close words to whichever keyword is current (for "DORA": "Nora," "Sora," "door," "adora") — still the highest-leverage addition for false-accept rate, and the one part of the negative set that must be regenerated per keyword.</cite>

<cite index="1-71,1-72">Split by recording/source group (not just by file) into train/val/test, to avoid augmentation leakage. This is not yet true speaker-disjoint evaluation, since source recordings are not currently tagged with verified speaker IDs — collecting that metadata during the OSCode recording drive is what upgrades this to genuine unseen-speaker evaluation.</cite>

---

## 8. RESOURCE BUDGET

### RAM / Flash / CPU / Latency

<cite index="1-78,1-79">MixedNet tensor arena (activations) ≈ 60–80 KB. Audio ring buffer (analysis + preroll + in-flight chunk) ≈ 45–50 KB. Spectrogram feature buffer ≈ 6–8 KB. VAD model + decision/debounce state ≈ 2–4 KB. Model weights (int8, flash not RAM) — Expected tens of KB flash, memory-mapped const. Pre-network KWS subtotal ≈ 140–160 KB Model + tensor arena + buffers only.</cite>

<cite index="1-79,1-80,1-81">Final system RAM (target) < 256 KB peak, TBD. VAD: negligible, sub-0.1% of a 240 MHz core. KWS inference: < 10 ms per call, field-measured on ESP32-S3. VAD gating is expected to reduce KWS invocation frequency enough to bring time-averaged CPU under the 10% ceiling during idle listening.</cite>

### Latency

<cite index="1-82,1-83,1-84">KWS inference (detection decision) < 10 ms (field-measured, prior art). Buffer flush + stream send (pre-warmed socket, PCM16 first) 5–15 ms. Network transit (Wi-Fi, LAN-scale, venue-dependent) 10–50 ms. Preliminary total: keyword-end → first byte at cloud ASR (component estimate) 25–75 ms under favorable LAN conditions. Latency target (PS requirement) < 300 ms.</cite>

---

## 9. DEPLOYMENT ARTIFACTS

<cite index="1-86">Trained float32 model <kw>_kws_float32.keras / SavedModel (training artifact only). Streaming quantized model <kw>_kws_streaming_int8.tflite (converted via the microWakeWord-style training/eval CLI, streaming + quantized). Firmware-embeddable model <kw>_model_data.cc / .h (xxd -i <kw>_kws_streaming_int8.tflite, wrapped const/alignas(8), linked into flash .rodata). VAD model vad.tflite → vad_data.cc (keyword-independent, trained once, reused for every swap). Firmware project ESP-IDF source tree (git repo). Cloud ASR server server.py + requirements.txt (± optional Dockerfile). Monitoring dashboard dashboard.html + dashboard_server.py. Model provenance record MODEL_CARD.md.</cite>

---

## 10. GRAND-FINALE KEYWORD SWAP PROCEDURE

<cite index="1-94">Step 1: ISRO announces the keyword; kick off synthetic TTS generation (Piper) — ~500–600 samples (15–30 min). Step 2: Team records real samples of the new word (multiple speakers, ~30 min recording session) (30 min). Step 3: Augment real recordings (noise, pitch, speed) to multiply volume; merge with synthetic + existing negative/background sets; group-split (20–30 min). Step 4: Train the streaming MixedNet binary classifier on the new dataset using the existing, unchanged architecture/config and a fresh checkpoint (--restore_checkpoint 0); quantize (60–90 min). Step 5: Embed the new model into the existing firmware (model file swap only, no firmware logic changes); reflash (15–20 min). Step 6: Say the word, confirm detection on the dashboard, sweep the detection threshold if needed, re-flash if adjusted (20–30 min). Target: under 4 hours end to end.</cite>

<cite index="1-95,1-96,1-97,1-98">This is a target, not yet a demonstrated result — it must be proven through at least one complete, timed dry run on a stand-in keyword (ideally two: e.g. "DORA" and a second word such as "AGNI") before it is relied on at the finale. The single-command wrapper for this sequence (e.g. ./swap_keyword.sh <NEWWORD>) should exist and be dry-run well ahead of time — a script that has only ever been run once, on "DORA," is not a tested script.</cite>

---

## 11. EVALUATION PROTOCOL

<cite index="1-101,1-102,1-103">Idle RAM/CPU: 10-minute idle-listening run, sampling heap high-water-mark and CPU duty cycle; report peak and average. TP/FP: run the held-out (unseen-speaker) test set through the on-device quantized firmware; report recall and false-accepts-per-hour. Latency: timestamp keyword-end on-device and first-byte-received on the ASR server, clocks synchronized beforehand.</cite>

| Metric | Target | Measured |
|---|---|---|
| RAM (peak) | < 256 KB | — |
| Idle CPU (avg) | < 10% | — |
| TP rate | ≥ 90–95% | — |
| FA rate | ≤ 1/hr | — |
| Latency | < 300 ms | — |
| Keyword-swap turnaround (dry run) | < 4 hr | — |

---

## 12. RISK REGISTER

<cite index="1-106">Grand-finale keyword swap takes longer than budgeted: Dry-run the full swap procedure on a stand-in word before the finale, not for the first time on the day. MixedNet training is newer/less documented than plain DS-CNN; the prior-art repo itself warns training a good model "is still very difficult": Start from the prior art's own published training config/hyperparameters rather than from scratch. Synthetic TTS-generated samples may not fully match real speech variation: Synthetic data supplements, never replaces, real recordings. False wake-ups from phonetically similar words: Explicit hard-negative class, regenerated per keyword. RAM overflow once Wi-Fi stack + model run together: Profile real free heap on-device early; ≥ 30% headroom maintained by design.</cite>

---

## 13. ROADMAP

<cite index="1-107,1-108,1-109,1-110,1-111,1-112,1-113,1-114,1-115">Clone the open-source microWakeWord training repo and its ESP-IDF component as the starting point. Build the dataset pipeline as keyword-parameterized from day one — never hard-code "DORA" into the scripts. Train the streaming MixedNet model on the DORA dataset; quantize; validate accuracy against the held-out speaker split. Swap the trained model into the ESP-IDF firmware; confirm real tensor-arena size and inference latency on hardware. Implement the pre-roll buffer + Opus encode + pre-warmed WebSocket client; stand up the Vosk server. Stand up the monitoring dashboard against both the ESP32 and the laptop/Pi harness. Run the full evaluation protocol; populate the empirical validation log with real numbers before the submission deadline. Dry-run the entire keyword-swap procedure on a stand-in word, end to end, timed — before the grand finale, not during it. Rehearse the live demo with the dashboard visible.</cite>

---

## 14. REFERENCES

<cite index="1-117,1-118">kahrendt / OHF-Voice — microWakeWord and esphome-on-device-wake-word (open-source, TensorFlow Lite Micro, ESP32-S3) — the primary prior-art reference for this design. Rykabov, Kononenko, Subrahmanya, Visontai, Laurenzo — "Streaming Keyword Spotting on Mobile Devices" — the underlying research microWakeWord's streaming Inception/MixedNet architecture is based on. dscripka — openWakeWord (open-source, ONNX-based wake-word framework; Piper TTS sample-generation tooling reused here for synthetic data). Zhang, Y. et al. — "Hello Edge: Keyword Spotting on Microcontrollers" (2017) — background reference for the depthwise-separable-convolution family MixedNet descends from. Espressif ESP-SR / WakeNet documentation — evaluated and excluded. Google Speech Commands v0.02; Mozilla Common Voice; MUSAN & DEMAND noise corpora. Vosk (Kaldi-based open-source streaming ASR) documentation.</cite>

---

**Document Version:** 4.1 (FINAL, TECHNICALLY-CORRECTED)  
**Last Updated:** 8 September 2026  
**Status:** Ready for implementation
