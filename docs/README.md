# DORA — Final Documentation Package
## SIH26172 | ISRO / Department of Space | Hardware | Smart Automation

---

```
██████╗  ██████╗ ██████╗  █████╗
██╔══██╗██╔═══██╗██╔══██╗██╔══██╗
██║  ██║██║   ██║██████╔╝███████║
██║  ██║██║   ██║██╔══██╗██╔══██║
██████╔╝╚██████╔╝██║  ██║██║  ██║
╚═════╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
Deployable Open-source Real-time Activator
```

**Version:** 2.0 — Final, Zero-Flaw, Build-Ready  
**Target Hardware:** ESP32-S3-DevKitC-1 N8R8  
**Problem Statement:** SIH26172  
**Organization:** ISRO / Dept. of Space  
**Category:** Hardware | Smart Automation  

---

## What Is DORA?

DORA is a two-stage, always-listening edge voice activator. It runs a custom keyword spotter on an ESP32-S3 microcontroller (< 160 KB RAM, < 10 ms inference), then streams Opus-compressed audio over a pre-warmed WebSocket to a Vosk ASR server — measuring keyword-end to cloud-first-byte latency, the third judging criterion that no other open-source project addresses.

---

## Quick Start

```bash
# 1. Clone and setup
git clone <repo-url> DORA_MIXED-net && cd DORA_MIXED-net

# 2. Install server dependencies
pip install fastapi "uvicorn[standard]" vosk opuslib websockets numpy

# 3. Start server
python server.py

# 4. Open dashboard
# http://localhost:8765/

# 5. Flash firmware (after training — see doc 08)
cd dora_firmware && idf.py build flash monitor
```

---

## Document Index

| # | Document | What It Covers |
|---|---|---|
| [01](./01_Project_Overview.md) | **Project Overview** | Summary, innovations, tech stack, competitive positioning, repo structure |
| [02](./02_Problem_Statement.md) | **Problem Statement** | Original PS analysis, why it's hard, DORA's direct response to each challenge |
| [03](./03_System_Architecture.md) | **System Architecture** | 5-stage pipeline, data flow diagram, FreeRTOS task model, latency budget |
| [04](./04_Hardware_Documentation.md) | **Hardware Documentation** | BOM (< ₹800), ESP32-S3 specs, INMP441 specs, GPIO wiring, I2S config, power options |
| [05](./05_Software_Design.md) | **Software Design** | Firmware modules, inter-module interfaces, server architecture, dashboard design, all dependencies |
| [06](./06_Model_Pipeline.md) | **Model Pipeline** | MixedNet architecture, audio front-end parameters, training steps, int8 quantisation, threshold sweep, model embedding |
| [07](./07_Dataset_Pipeline.md) | **Dataset Pipeline** | All 4 scripts (TTS synthesis, manual recording, augmentation, merge+split), negatives setup, directory structure |
| [08](./08_Firmware_Guide.md) | **Firmware Guide** | Per-module reference, decision logic, Opus parameters, build/flash commands, common issues |
| [09](./09_Server_and_Dashboard.md) | **Server & Dashboard** | FastAPI endpoints, ASR pipeline, latency calculation, dashboard panels, Raspberry Pi deployment |
| [10](./10_Evaluation_and_Testing.md) | **Evaluation & Testing** | Performance targets, 4-phase test protocol, threshold sweep, judging rubric mapping, benchmark comparison |
| [11](./11_Deployment_Guide.md) | **Deployment Guide** | Full setup from zero, one-time downloads, hardware assembly, training walkthrough, finale USB kit |
| [12](./12_Resource_Budget.md) | **Resource Budget** | RAM ledger (168–188 KB total), flash budget, CPU budget, power budget, competitor comparison |
| [13](./13_Grand_Finale_Playbook.md) | **Grand Finale Playbook** | Keyword swap timeline, one-command script, contingency plans, dry-run instructions, finale day checklist |
| [14](./14_Edge_Cloud_Implementation_Guide.md) | **Edge Cloud Implementation Guide** | Implemented Wi-Fi PCM handoff, gateway setup, flash checklist, and physical validation record |

---

## Performance Targets at a Glance

| Metric | Target | How Measured |
|---|---|---|
| RAM (peak) | < 180 KB | `heap_caps_get_minimum_free_size()` |
| Idle CPU | < 10% | `telemetry_task` 5s averages |
| True Positive Rate | ≥ 92% | `evaluate.py` on held-out speakers |
| False Accept Rate | ≤ 1 / hr | 1-hour idle run |
| Keyword-end → ASR first-byte | < 75 ms (p50) | Server timestamp vs device timestamp |
| Keyword swap time | < 4 hours | `./swap_keyword.sh <KEYWORD>` |

---

## Key Scripts Reference

| Script | Command | Purpose |
|---|---|---|
| `generate_keyword_dataset.py` | `python generate_keyword_dataset.py --keyword DORA --count 600` | Piper TTS synthesis (~550 samples) |
| `record_keyword.py` | `python record_keyword.py --keyword DORA --speaker spk001 --count 20` | Manual recordings (1 per team member) |
| `augment_real.py` | `python augment_real.py --keyword DORA` | 4× augmentation of real recordings |
| `prepare_dataset.py` | `python prepare_dataset.py --keyword DORA` | Merge + speaker-split into train/val/test |
| `threshold_sweep.py` | `python threshold_sweep.py --model models/DORA_int8.tflite --val_dir dataset/split/val/DORA` | Find optimal KWS threshold |
| `swap_keyword.sh` | `./swap_keyword.sh AGNI` | Full keyword swap in one command |
| `server.py` | `python server.py` | Start ASR server + dashboard on port 8765 |

---

## Hardware Wiring (Quick Reference)

```
INMP441 VDD  → ESP32-S3 3.3V
INMP441 GND  → ESP32-S3 GND
INMP441 WS   → ESP32-S3 GPIO 4
INMP441 SCK  → ESP32-S3 GPIO 5
INMP441 SD   → ESP32-S3 GPIO 6
INMP441 L/R  → ESP32-S3 GND    ← mono LEFT channel
```

---

## System Architecture (Summary)

```
[INMP441 Mic] → [VAD] → [MixedNet KWS] → [Pre-roll Buffer] → [Opus Encoder]
                                                                      │
                                                               [WebSocket]
                                                                      │
                                                            [Vosk ASR Server]
                                                                      │
                                                           [Live Dashboard]
```

---

## Document Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | Aug 2026 | Initial technical solution document |
| 2.0 | Sep 2026 | Final build-ready version — all code complete, documentation package added |

---

*Document v2.0 — SIH26172 | ISRO | Built for ESP32-S3 | September 2026*  
*Architecture: Streaming MixedNet (microWakeWord family, retrained from scratch) + Original: pre-warmed Opus WebSocket handoff with keyword-end latency telemetry*
