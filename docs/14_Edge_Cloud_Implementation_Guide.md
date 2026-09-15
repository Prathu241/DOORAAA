# DORA Edge Cloud Implementation Guide

## Purpose

This guide records the implemented path for running the DORA wake word model on an ESP32-S3, sending real microphone audio only after detection, recognising the command with Vosk, and displaying the outcome in the dashboard. It distinguishes completed code from steps that still require physical hardware validation.

## Implemented Components

| Component | File | Status |
|---|---|---|
| DORA TFLite model | `trained_models/DORA/dora_model_int8.tflite` | Present. 68,600 bytes. Input and output are float32 despite the filename. |
| ESP32 local KWS | `ESP32_MIC_TEST/dora_full_inference/dora_full_inference.ino` | Updated. Captures INMP441 audio, applies the local frontend, and invokes TFLite Micro. |
| Model header | `ESP32_MIC_TEST/dora_full_inference/model_data.h` | Present and embedded in firmware. |
| Wi-Fi settings | `ESP32_MIC_TEST/dora_full_inference/secrets.h` | Created locally; must be filled before flashing and is ignored by Git. |
| Edge gateway | `dashboard/edge-stream-server.js` | Added. Receives ESP32 WebSocket frames, forwards actual PCM to Vosk after utterance end, and sends lifecycle events to dashboard clients. |
| Dashboard client | `dashboard/src/hooks/useESP32Bridge.js` | Already consumes the event types emitted by the new gateway on port 8080. |
| Vosk ASR | `vosk_asr_server.py` | Existing. Receives raw 16 kHz PCM16 in an HTTP request and returns a final transcript. |

## Audio Path

1. The INMP441 produces 32-bit I2S samples at 16 kHz.
2. ESP32 converts them to signed PCM16 and retains the most recent 30 frames, equal to 300 ms.
3. The micro-speech frontend creates 40 mel features and TFLite Micro scores DORA locally.
4. On a threshold crossing, the ESP32 opens the already connected WebSocket session, sends metadata, sends pre-roll PCM, and then sends continuing PCM frames.
5. The ESP32 ends streaming after 800 ms of low energy or after 8 seconds.
6. `edge-stream-server.js` forwards audio lifecycle events to the dashboard and posts the exact captured PCM bytes to Vosk.
7. Vosk returns a transcript that appears in the dashboard detection log.

No microphone PCM is sent while DORA has not been detected. The previous serial bridge remains useful for USB diagnostics but is not part of the remote audio path.

## Before Flashing

### 1. Verify Wiring

| INMP441 | ESP32-S3 |
|---|---|
| VDD | 3.3 V only |
| GND | GND |
| SCK | GPIO4 |
| WS | GPIO5 |
| SD | GPIO6 |
| L R | GND for left channel |

### 2. Test the Microphone

Flash `ESP32_MIC_TEST/mic_test/mic_test.ino` first. In the serial monitor at 115200 baud, RMS and peak must change clearly when speaking. If values remain approximately 0 or 1, stop and correct power, grounds, wiring, or the I2S sample shift before using the KWS firmware.

### 3. Configure Wi-Fi and Server Address

Edit `ESP32_MIC_TEST/dora_full_inference/secrets.h`.

```cpp
#define DORA_WIFI_SSID "Your WiFi"
#define DORA_WIFI_PASSWORD "Your password"
#define DORA_CLOUD_HOST "192.168.1.25"
```

`DORA_CLOUD_HOST` must be the LAN IPv4 address of the computer that runs the gateway. It must not be `localhost`. Place the computer and ESP32 on the same network and allow inbound TCP port 8765 through the computer firewall.

## Install and Run the Cloud Side

Open three terminals from the repository root.

Terminal 1 starts Vosk:

```powershell
python vosk_asr_server.py
```

Terminal 2 starts the Wi-Fi edge gateway and dashboard event WebSocket:

```powershell
cd dashboard
npm install
npm run edge
```

Terminal 3 starts the dashboard:

```powershell
cd dashboard
npm run dev
```

Open the Vite URL printed by Terminal 3. Do not run `esp32-serial-bridge.js` at the same time as `edge-stream-server.js`, because both provide dashboard WebSockets on port 8080.

## Build and Flash Firmware

1. Install the ESP32 Arduino board package 3.3.11 or compatible.
2. Install `TensorFlowLite_ESP32` and `WebSockets`; both are already present in the current development toolchain.
3. Select `ESP32S3 Dev Module`.
4. Open `ESP32_MIC_TEST/dora_full_inference/dora_full_inference.ino`.
5. Compile before flashing. The Wi-Fi streaming firmware compiled successfully on the installed ESP32 Arduino core 3.3.11. It consumes 1,118,867 bytes flash (85 percent of 1,310,720 bytes) and 221,484 bytes static RAM (67 percent of 327,680 bytes), leaving 106,196 bytes for runtime. The static allocation is below the PS 256 KB RAM limit, but runtime heap, arena use, and CPU still require physical measurement.
6. Flash the selected COM port and open serial at 115200 baud.

Expected sequence:

```text
[I2S] OK - microphone ready
[Frontend] OK - PCAN mel filterbank ready
[READY] Listening for DORA
[WiFi] Connected: <ESP32 IP>
[Cloud] WebSocket connected
```

### Troubleshooting Model Allocation

If the serial monitor prints `Didn't find op for builtin opcode SPLIT_V`, the flashed sketch is older than the current firmware. The model requires `resolver.AddSplitV()` in addition to the other TFLite Micro registrations. The current source includes this registration and compiles successfully. Recompile and flash this exact sketch; do not increase the tensor arena to work around a missing operator. A missing operator makes `AllocateTensors()` fail with a misleading generic arena message.

## Functional Test Procedure

1. Confirm dashboard hardware status becomes connected over Wi-Fi.
2. Confirm RMS, peak, confidence, and inference timings update about twice per second.
3. Say DORA followed by a short command, for example `DORA turn on the light`.
4. Confirm the serial log reports `Real PCM stream started`.
5. Confirm gateway reports a first-audio event and then a Vosk transcript.
6. Confirm the dashboard displays the same transcript and audio-byte count.
7. Repeat at least 20 times for each speaker and record misses, false triggers, first-byte time, final transcript time, heap, and frontend/inference timings.

## Current Limits and Required Validation

- The DORA model currently has float32 input/output. It is not proven to be fully integer inference.
- The 99.5 percent reported model accuracy is an offline result. Deployment accuracy is not yet validated with INMP441 audio.
- Existing evaluation material reports false activation risk for phonetically similar words. Start with `KWS_THRESHOLD = 0.90f`; the current firmware value of 0.75 requires a measured justification before use.
- Raw PCM16 is used in the first real end-to-end integration: 256 kbps while streaming. It is correct and easy to validate, but not the final minimum-overhead transport. After successful testing, replace it with IMA ADPCM or Opus and remeasure recognition quality, RAM, CPU, and latency.
- The gateway currently forwards PCM to Vosk at utterance end. It proves real audio reaches the ASR server. A later upgrade should feed Vosk incrementally for partial transcription.
- Keyword-end to server-first-byte latency is not validly measured until device and server clocks are synchronized with SNTP. The gateway now records arrival time; add SNTP before presenting the PS latency metric.

## Documentation Required After Each Test

Create one dated row for every test session containing:

| Date and build hash | Hardware and network | Threshold | Speaker and phrase | TP FP FN | Heap and arena | Frontend and inference microseconds | First-byte and final-ASR times | Notes |
|---|---|---:|---|---|---|---|---|---|

Keep serial logs, dashboard screenshots, compile output, and raw test counts in a `evidence/` folder. Do not overwrite a prior test result. Update the claimed accuracy, false-alarm rate, RAM, CPU, and latency only from this physical-hardware evidence.

## Next Engineering Work

1. Compile and flash the updated firmware after replacing the placeholder Wi-Fi configuration.
2. Prove real microphone capture and record the first hardware test row.
3. Implement SNTP-based latency timestamps.
4. Convert the audio transport from PCM16 to IMA ADPCM or Opus only after establishing a PCM baseline.
5. Retrain using phonetically similar hard negatives if false activations persist.
