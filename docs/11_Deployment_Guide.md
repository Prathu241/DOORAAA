# Deployment Guide — From Zero to Running Demo
## Document 11 — SIH26172 | DORA

---

## 1. Prerequisites Checklist

Before starting, verify you have:

- [ ] ESP32-S3-DevKitC-1 N8R8 board
- [ ] INMP441 I2S microphone module
- [ ] 6 jumper wires (male-female)
- [ ] USB-C cable
- [ ] Laptop (Windows/Linux/macOS) with at least 8 GB RAM
- [ ] ESP-IDF v5.2+ installed ([esp-idf install guide](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/get-started/))
- [ ] Python 3.10+ installed
- [ ] Git installed
- [ ] Internet connection (for initial downloads)

---

## 2. One-Time Setup (Do Before the Hackathon)

### Step 1: Clone and Set Up This Repository

```bash
git clone <your-repo-url> DORA_MIXED-net
cd DORA_MIXED-net
```

### Step 2: Install Training Environment

```bash
pip install tensorflow==2.15.0 tensorflow-model-optimization \
            numpy librosa soundfile sounddevice piper-tts
```

### Step 3: Install Server Environment

```bash
pip install fastapi "uvicorn[standard]" vosk opuslib websockets numpy
```

### Step 4: Clone microWakeWord Training Repo

```bash
git clone https://github.com/kahrendt/microWakeWord
cd microWakeWord
pip install -r requirements.txt
cd ..
```

### Step 5: Download Piper Voice Models (Requires Internet)

```bash
mkdir -p piper_voices && cd piper_voices

wget "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_IN/medium/en_IN-female-medium.onnx"
wget "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_IN/medium/en_IN-female-medium.onnx.json"
wget "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx"
wget "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/medium/en_US-ryan-medium.onnx.json"
wget "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
wget "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
wget "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx"
wget "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json"
wget "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/hemant/medium/hi_IN-hemant-medium.onnx"
wget "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/hemant/medium/hi_IN-hemant-medium.onnx.json"

cd ..
```

### Step 6: Download Vosk Model (Requires Internet)

```bash
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
# Creates: vosk-model-small-en-us-0.15/ in current directory
```

### Step 7: Download Negative Datasets (Requires Internet)

```bash
# Google Speech Commands v0.02
wget http://download.tensorflow.org/data/speech_commands_v0.02.tar.gz
mkdir -p dataset/unknown
tar -xzf speech_commands_v0.02.tar.gz -C dataset/unknown/

# MUSAN noise/speech/music
wget https://www.openslr.org/resources/17/musan.tar.gz
mkdir -p dataset/background
tar -xzf musan.tar.gz -C dataset/background/
```

### Step 8: Offline Backup (Critical — Do Before the Venue)

```bash
# Backup all Python packages for offline install at venue
pip download -r requirements_server.txt -d pip_cache/
pip download tensorflow==2.15.0 -d pip_cache/

# Verify all downloads complete before the event
ls piper_voices/*.onnx | wc -l    # should be 5
ls vosk-model-small-en-us-0.15/   # should contain model files
```

---

## 3. Hardware Assembly

### Step 1: Wire INMP441 to ESP32-S3

```
INMP441 VDD  → ESP32-S3 3.3V
INMP441 GND  → ESP32-S3 GND
INMP441 WS   → ESP32-S3 GPIO 4
INMP441 SCK  → ESP32-S3 GPIO 5
INMP441 SD   → ESP32-S3 GPIO 6
INMP441 L/R  → ESP32-S3 GND  (mono LEFT channel)
```

### Step 2: Verify Wiring

Use a multimeter: with board powered, measure VDD–GND on INMP441 = 3.3V ± 0.1V.

### Step 3: Flash Test Firmware

```bash
cd dora_firmware
idf.py build flash monitor
# Confirm: "I2S started at 16000 Hz" in serial monitor
```

---

## 4. Dataset Generation and Training (DORA Keyword)

```bash
# Step 1: Generate TTS samples
python generate_keyword_dataset.py --keyword DORA --count 600

# Step 2: Record real samples (6 team members)
python record_keyword.py --keyword DORA --speaker spk001 --count 20
python record_keyword.py --keyword DORA --speaker spk002 --count 20
python record_keyword.py --keyword DORA --speaker spk003 --count 20
python record_keyword.py --keyword DORA --speaker spk004 --count 20
python record_keyword.py --keyword DORA --speaker spk005 --count 20
python record_keyword.py --keyword DORA --speaker spk006 --count 20

# Step 3: Augment real recordings
python augment_real.py --keyword DORA

# Step 4: Merge and split
python prepare_dataset.py --keyword DORA

# Step 5: Train
cd microWakeWord
python train.py \
  --keyword        DORA \
  --positive_dir   ../dataset/split/train/DORA \
  --negative_dir   ../dataset/unknown \
  --background_dir ../dataset/background \
  --epochs         100 \
  --batch_size     64 \
  --output_dir     ../models/
cd ..

# Step 6: Convert to streaming TFLite + int8
cd microWakeWord
python convert_to_streaming.py \
  --model  ../models/DORA_float32.keras \
  --output ../models/DORA_streaming_int8.tflite
cd ..

# Step 7: Evaluate
cd microWakeWord
python evaluate.py \
  --model    ../models/DORA_streaming_int8.tflite \
  --test_dir ../dataset/split/test/DORA
cd ..

# Step 8: Sweep threshold and pick best value
python threshold_sweep.py \
  --model   models/DORA_streaming_int8.tflite \
  --val_dir dataset/split/val/DORA
# Update KWS_THRESHOLD in dora_firmware/main/kws_model.c
```

---

## 5. Embed Model and Flash Firmware

```bash
# Embed model as C array
xxd -i models/DORA_streaming_int8.tflite > dora_firmware/main/kws_model_data.cc

# Edit kws_model_data.cc:
# Line 1: change to → const unsigned char g_kws_model_data[] __attribute__((aligned(8))) = {
# Last line: change to → const unsigned int g_kws_model_data_len = NNNN;

# Edit dora_firmware/main/main.c — set your network details:
# #define WIFI_SSID   "YourNetworkName"
# #define WIFI_PASS   "YourPassword"
# #define SERVER_URI  "ws://192.168.X.Y:8765/stream"

# Build and flash
cd dora_firmware
idf.py build flash monitor
```

---

## 6. Start the Server and Dashboard

```bash
# In a separate terminal:
python server.py

# Open dashboard:
# http://localhost:8765/         (on server machine)
# http://<server-ip>:8765/      (from any LAN device)
```

---

## 7. Verify Full System

1. Serial monitor shows device connected to Wi-Fi and WebSocket pre-warmed
2. Dashboard status pill shows green "Live"
3. Say "DORA" — dashboard shows:
   - Detection count increments
   - Latency value appears (target < 75 ms)
   - ASR text shows what was said after keyword
4. RAM panel shows > 68 KB free
5. CPU panel shows < 10%

---

## 8. Finale Kit USB Contents

Pack this USB drive before travelling to the venue:

```
finale_kit/
├── piper_voices/              ← All 5 .onnx + .json voice models
├── pip_cache/                 ← Offline pip packages
├── vosk-model-small-en-us-0.15/  ← Vosk model
├── speech_commands_v0.02.tar.gz  ← Negatives (already extracted)
├── musan.tar.gz               ← Background noise
├── DORA_MIXED-net/            ← Full repo (git archive)
│   ├── dataset/unknown/       ← Pre-extracted Speech Commands
│   ├── dataset/background/    ← Pre-extracted MUSAN
│   └── models/DORA_streaming_int8.tflite  ← Pre-trained DORA model
└── README_FINALE.txt          ← Quick-start instructions
```
