# DORA — Deployable Open-source Real-time Activator
## Project Overview

**Problem Statement ID:** SIH26172  
**Organization:** ISRO / Department of Space  
**Category:** Hardware  
**Domain:** Smart Automation  
**Document Version:** 2.0 — Final, Build-Ready  
**Date:** September 2026  

---

## 1. Project Summary

DORA (Deployable Open-source Real-time Activator) is a two-stage, always-listening edge voice activation system built on the ESP32-S3 microcontroller. It detects a custom keyword on-device with sub-10 ms latency, then streams compressed audio to a cloud ASR server over a pre-warmed WebSocket — measuring the full end-to-end handoff latency that no existing open-source solution addresses.

---

## 2. One-Line Pitch

> **An open-source, always-on keyword spotter that runs on a ₹600 microcontroller, consumes less than 160 KB RAM, and hands off to cloud ASR in under 75 ms — with every metric measured live on a real-time dashboard.**

---

## 3. Key Innovations

| Innovation | Description |
|---|---|
| Two-stage edge pipeline | VAD gates MixedNet KWS — saves CPU when silent |
| Opus-compressed stream | 24 kbps vs 256 kbps raw PCM — 10× bandwidth reduction |
| Pre-warmed WebSocket | Connection established at boot — zero connection latency on detection |
| Pre-roll ring buffer | 300 ms of audio captured before keyword end — never miss context |
| Keyword-end → first-byte latency | The metric ISRO judges but no other open-source project measures |
| Keyword-agnostic pipeline | Swap any keyword in under 4 hours using one shell script |
| Live telemetry dashboard | RAM, CPU, latency, ASR text — all visible in real time |

---

## 4. Evaluation Axes Addressed

The problem statement specifies three judging axes. DORA is the **only open-source system** that addresses all three with measured numbers:

| Axis | DORA's Answer | Target |
|---|---|---|
| **Efficiency** | < 160 KB RAM, < 10% idle CPU | < 256 KB RAM, < 10% CPU |
| **Accuracy** | ≥ 92% True Positive Rate, ≤ 1 FA/hr | ≥ 90% TPR |
| **Latency** | < 75 ms keyword-end → ASR first-byte | Minimize |

---

## 5. Competitive Positioning

| Feature | Cloud-only (Google/Alexa) | microWakeWord | openWakeWord | **DORA** |
|---|---|---|---|---|
| Runs on ESP32-S3 | ✗ | ✓ | ✗ | ✓ |
| < 256 KB RAM | ✗ | ✓ | ✗ | ✓ |
| Open-source training | ✗ | ✓ | ✓ | ✓ |
| Measures handoff latency | ✗ | ✗ | ✗ | ✓ |
| Opus-compressed stream | ✗ | ✗ | ✗ | ✓ |
| Keyword-agnostic pipeline | ✗ | ✗ | ✗ | ✓ |
| Real-time dashboard | ✗ | ✗ | ✗ | ✓ |
| Pre-roll buffer | ✗ | ✗ | ✗ | ✓ |

> microWakeWord solves on-device KWS perfectly but stops there — no cloud handoff, no latency metric, no dashboard. DORA begins exactly where microWakeWord ends.

---

## 6. Technology Stack Summary

| Layer | Technology |
|---|---|
| Edge MCU | ESP32-S3-DevKitC-1 N8R8 |
| Microphone | INMP441 I2S MEMS |
| RTOS | FreeRTOS (via ESP-IDF v5.2+) |
| ML Runtime | TFLite Micro (espressif/esp-tflite-micro) |
| KWS Model | Streaming MixedNet, int8 quantised |
| Audio Codec | Opus 24 kbps (espressif/esp-opus) |
| Transport | Pre-warmed WebSocket (esp_websocket_client) |
| ASR Engine | Vosk (Kaldi-based, CPU-only) |
| Server Framework | FastAPI + Uvicorn |
| Dashboard | Vanilla HTML/JS + Chart.js |

---

## 7. Repository Structure

```
DORA_MIXED-net/
├── docs/                        ← This documentation package
├── dora_firmware/               ← ESP32-S3 ESP-IDF project
│   └── main/
│       ├── main.c
│       ├── ring_buffer.h/.c
│       ├── audio_capture.h/.c
│       ├── kws_model.h/.c
│       ├── websocket_client.h/.c
│       ├── telemetry.h/.c
│       ├── kws_model_data.cc
│       └── vad_model_data.cc
├── microWakeWord/               ← Cloned training repo
├── dataset/                     ← Audio data (gitignored if large)
├── models/                      ← Trained .tflite files
├── piper_voices/                ← TTS voice models
├── server.py                    ← Cloud ASR + dashboard server
├── dashboard.html               ← Live monitoring UI
├── generate_keyword_dataset.py  ← TTS synthesis script
├── record_keyword.py            ← Manual recording script
├── augment_real.py              ← Data augmentation script
├── prepare_dataset.py           ← Merge + speaker-split script
├── threshold_sweep.py           ← KWS threshold tuner
└── swap_keyword.sh              ← One-command keyword swap
```

---

## 8. Document Map

| Document | Contents |
|---|---|
| `02_Problem_Statement.md` | Original PS analysis and DORA's response |
| `03_System_Architecture.md` | Full 5-stage pipeline diagram and data flow |
| `04_Hardware_Documentation.md` | BOM, wiring, GPIO pinout |
| `05_Software_Design.md` | Software components, task model, interfaces |
| `06_Model_Pipeline.md` | Architecture, training, quantisation, evaluation |
| `07_Dataset_Pipeline.md` | All 4 dataset scripts with usage |
| `08_Firmware_Guide.md` | Complete ESP-IDF firmware walkthrough |
| `09_Server_and_Dashboard.md` | FastAPI server + dashboard UI guide |
| `10_Evaluation_and_Testing.md` | Test protocol, targets, measurement log |
| `11_Deployment_Guide.md` | Step-by-step setup from zero |
| `12_Resource_Budget.md` | RAM, flash, CPU breakdown |
| `13_Grand_Finale_Playbook.md` | Keyword swap timeline and one-command script |
