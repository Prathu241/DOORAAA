# DORA Dashboard v4.0 — Enhanced with Live Content Reference

**Status:** ✅ LIVE at http://localhost:5000

## New Components Added

### 1. **Signal Pipeline** (Tier 0–3 Processing)
- Visual flow: MIC → VAD → MixedNet KWS → PRE-ROLL → VOSK ASR
- Real-time status: LIVE / STANDBY
- Animated arrows with active state styling

### 2. **Model Card** 
- Architecture: Streaming MixedNet
- Chip Target: ESP32-S3
- Runtime: TFLite Micro
- Quantization: INT8 Full-Integer
- Trained On: DORA Dataset
- Weights Source: From Scratch
- Footer: Version, size (287 KB), verification status

### 3. **Detection Accuracy**
- TP Rate: 98.8% (with bar visualization)
- FA Rate: 1.2% (critical threshold indicator)
- Overall Accuracy: 99.5%
- Latency: 145 ms
- Eval Split: Recording-Disjoint
- Decision Rule: 5-frame avg / cutoff
- Validation note: "Model validated on held-out test set"

### 4. **Latency Monitor**
- **Main display:** Round-trip latency (145 ms, color-coded: pass/fail)
- **Target:** < 300 ms (§12)
- **Breakdown:**
  - Round Trip: Dynamic monitoring
  - LAN Estimate: 25–75 ms range
- Clock-synced measurement note

### 5. **Keyword Swap Console** (§11 · <4hr target)
- **Keyword selector:** DORA, AGNI, VAYU, JALA, PRITHVI
- **Workflow runner:** 6-step timeline
  1. TTS Synth Batch (Piper, ~500 samples) — 15–30m
  2. Real Recording Pass (on-site speakers) — 30m
  3. Augment + Group-Split (merge w/ negatives) — 20–30m
  4. Train + Quantize (--restore_checkpoint 0) — 60–90m
  5. Flash Firmware (model swap only) — 15–20m
  6. Verify + Tune (threshold sweep) — 20–30m
- Button: "RUN WORKFLOW" (executes ./swap_keyword.sh KEYWORD)
- Total time: <4hr Target

## Layout (Grid-based)

```
┌──────────────────────────────────────────────────────┐
│ HEADER: DORA · KWS :: ESP32-S3 :: INMP441            │
│         STATUS: MODEL READY ✓                        │
├──────────────────────────────────────────────────────┤
│ [SIGNAL PIPELINE - FULL WIDTH]                       │
│ MIC → VAD → KWS → PRE-ROLL → ASR (Tier 0–3)         │
├─────────────────┬─────────────────┬──────────────────┤
│ SYSTEM RAM      │ CPU LOAD        │ GPU MEMORY       │
│ 45% / 3.2 GB    │ 38% / 8 threads │ 62% / 0.64 GB    │
├─────────────────┼─────────────────┼──────────────────┤
│ TEMPERATURE     │ MODEL CARD      │ DETECTION ACC    │
│ 52°C · NORMAL   │ Streaming Mixed │ TP: 98.8%        │
│                 │ ESP32-S3 · INT8 │ FA: 1.2%         │
├─────────────────┴─────────────────┼──────────────────┤
│ LATENCY MONITOR                   │                  │
│ 145 ms / <300 ms target           │                  │
├───────────────────────────────────┴──────────────────┤
│ [CONTROL PANEL - FULL WIDTH]                         │
│ [🎙️ MIC ON/OFF] [▶️ RECORD] [⚡ TEST] [🔄 RESET]    │
├──────────────────────────────────────────────────────┤
│ [TRAINING METRICS] [HARDWARE] [AUDIO VISUALIZER]    │
├──────────────────────────────────────────────────────┤
│ [KEYWORD DETECTOR] [MODEL DEPLOYMENT] [TIMELINE]    │
├──────────────────────────────────────────────────────┤
│ [KEYWORD SWAP CONSOLE - FULL WIDTH]                 │
│ SELECT: [AGNI ▼] [RUN WORKFLOW ▶]                  │
│ 1. TTS Synth     2. Real Recording  3. Augment       │
│ 4. Train+Quant   5. Flash Firmware  6. Verify+Tune   │
├──────────────────────────────────────────────────────┤
│ FOOTER: DORA KWS · ESP32-S3 + INMP441               │
│         99.5% Accuracy | 98.8% Recall | v3.0 INT8   │
└──────────────────────────────────────────────────────┘
```

## Theme (Brutalist Terminal + Neon Blue)

- **Background:** Dark navy (#0a0e27) with 40px mesh grid (rgba(0, 153, 255, 0.05))
- **Primary Color:** Neon Blue (#0099ff)
- **Secondary Color:** Cyan (#00d9ff)
- **Accent:** Green success (#00ff88), Orange warning (#ff9900), Red critical (#ff0000)
- **Font:** Courier New monospace (terminal aesthetic)
- **Borders:** Sharp 90° angles, no rounded corners
- **Effects:** 
  - Glow animations on headers/footers
  - Pipeline arrow pulsing
  - Shimmer gradient on neon accents
  - Floating animations on logos
  - Hover state with cyan borders

## Features

- ✅ Real-time resource metrics (RAM/CPU/GPU/Temp with dynamic updates)
- ✅ Interactive controls (Mic, Record, Test, Reset buttons)
- ✅ Signal pipeline visualization with status
- ✅ Model metadata card with full specifications
- ✅ Detection accuracy metrics with TP/FA visualization
- ✅ Latency monitoring with round-trip tracking
- ✅ Keyword swap workflow console (6-step timeline)
- ✅ Training status and deployment timeline
- ✅ Hardware monitoring
- ✅ Audio visualizer
- ✅ Keyword detection log
- ✅ Professional brutalist design with neon theme

## Build Info

- **Build Size:** CSS 27.67 KB (gzip 5.20 KB), JS 548.36 KB (gzip 157.47 KB)
- **Total Assets:** ~576 KB (build) / ~163 KB (gzip)
- **Build Time:** ~5.2s
- **Server:** Express.js on port 5000
- **Live URL:** http://localhost:5000

## Files Added

```
dashboard/src/components/
├── SignalPipeline.jsx / .css
├── ModelCard.jsx / .css
├── DetectionAccuracy.jsx / .css
├── LatencyMonitor.jsx / .css
└── KeywordSwapConsole.jsx / .css
```

## Reference Document

All content derived from `dora-dashboard.html` reference provided by user, following:
- Signal pipeline architecture (Tier 0–3)
- System load metrics (RAM/CPU/Flash)
- Detection accuracy (TP/FA rates)
- Model specifications
- Keyword swap workflow (<4hr target)
- Professional telemetry layout

**Dashboard is ready for hardware integration and live demonstration.**
