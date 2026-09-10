# DORA ESP32 Deployment & Testing Quick Start Guide
## Complete Step-by-Step Instructions

---

## ✅ PRE-FLIGHT CHECKLIST

Before starting, verify you have:

- [ ] ESP32-S3 DevKit board with USB-C cable
- [ ] INMP441 I2S microphone module
- [ ] 6 jumper wires (male-female)
- [ ] Arduino IDE installed (v2.0+)
- [ ] ESP32 board support installed in Arduino IDE
- [ ] Trained model: `trained_models/DORA/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite`
- [ ] Dashboard running (Python server)
- [ ] Network connectivity

---

## 🔧 PHASE 1: HARDWARE SETUP (10 minutes)

### Step 1.1: Wire the Microphone to ESP32-S3

Connect INMP441 to ESP32-S3 using the wiring below:

```
INMP441          ESP32-S3 Pin
─────────────────────────────
VDD       →      3.3V
GND       →      GND
WS        →      GPIO 5  (LRCK / Word Select)
SCK       →      GPIO 4  (BCLK / Bit Clock)
SD        →      GPIO 6  (DIN / Data In)
L/R       →      GND     (Select LEFT channel - mono)
```

**Visual Check:**
- All 6 wires securely connected
- No loose connections
- Power connections on correct rails

### Step 1.2: Verify Power

1. Connect ESP32 to computer via USB-C cable
2. Open Device Manager (Windows) or System Report (Mac)
3. Check that a new COM port appears (e.g., COM3, COM4, COM5)
4. Note the COM port number

**Expected:** One new COM port appears when plugged in

---

## 🧪 PHASE 2: TEST MICROPHONE (15 minutes)

### Step 2.1: Open Arduino IDE

1. Launch Arduino IDE (v2.0 or newer)
2. Go to **Tools → Board Manager**
3. Search for "ESP32"
4. Install **ESP32** by Espressif Systems (if not already installed)

### Step 2.2: Configure Arduino IDE

1. **Tools → Board** → Select **ESP32-S3 Dev Module**
2. **Tools → Port** → Select the COM port from Step 1.2 (e.g., COM3)
3. **Tools → Upload Speed** → Select **921600**
4. **Tools → Partition Scheme** → Select **Default (with SPIFFS)**

**Verification Screenshot:**
```
Tools → Board: ESP32-S3 Dev Module
Tools → Port: COM3 (or your port)
Tools → Upload Speed: 921600
```

### Step 2.3: Load Microphone Test Sketch

1. In Arduino IDE: **File → Open**
2. Browse to: `ESP32_MIC_TEST/mic_test.ino`
3. Click "Open"
4. You should see the code in the editor

### Step 2.4: Upload Firmware

1. Click **Upload** button (→ arrow icon) or press **Ctrl+U**
2. Wait for compilation (30-60 seconds)
3. Watch for: **"Leaving... Hard resetting via RTS pin"**
4. Wait for: **"Upload successful"** message

**If failed:**
- Check USB cable is seated firmly
- Try a different USB port on your computer
- Check COM port is correct in Tools → Port

### Step 2.5: Monitor Serial Output

1. Click **Tools → Serial Monitor** (or Ctrl+Shift+M)
2. Bottom-right: Verify baud rate is **9600**
3. In the serial monitor window, you should see:

```
=====================================================
DORA MICROPHONE TEST - ESP32-S3 + INMP441
=====================================================
Initializing I2S audio capture...
✓ I2S initialized successfully!
✓ Sample rate: 16 kHz
✓ Bit depth: 32-bit I2S (INMP441 24-bit packed)
✓ Converting to PCM16...

Listening for audio... Speak or clap near microphone!
=====================================================

MIC TEST
samples=8000
rms=45.2
peak=105
min=-98
max=92
---
```

### Step 2.6: Test Microphone Response

Perform these tests in Serial Monitor:

**Test 1: SILENCE TEST (10 seconds)**
- Sit completely quiet
- Watch RMS, peak values
- Expected: RMS ~30-60, peak ~50-100
- All values should be LOW and stable

**Test 2: SPEAK TEST (5 seconds)**
- Speak "DORA" clearly into the microphone
- Watch values jump
- Expected: RMS jumps to 150-400, peak jumps to 300-800+
- Values should be MUCH HIGHER than silence test

**Test 3: CLAP TEST (3 seconds)**
- Clap sharply near the microphone
- Expected: Peak should spike to 1000+
- Should be clearly visible as a spike

### Step 2.7: Report Microphone Status

**✅ MIC PASS** if:
- RMS and peak values jump significantly when speaking/clapping
- Silent test shows low values (~30-50 RMS)
- Speech test shows high values (~200+ RMS)
- Clap test shows spike (1000+ peak)

**❌ MIC FAIL** if:
- Values stay at ~0 even when speaking loud
- No change between silent and speech tests
- Serial shows garbage/corrupted text

**If FAILED:** Check wiring per Step 1.1, especially GPIO 4, 5, 6 and power pins.

---

## 🤖 PHASE 3: PREPARE TRAINED MODEL (5 minutes)

### Step 3.1: Locate Your Trained Model

The trained model should be at:
```
trained_models/DORA/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite
```

If this file doesn't exist:
- Train the model first: `python run_training.py`
- Export to TFLite: Follow docs/06_Model_Pipeline.md
- Quantize: Use `tflite_convert` with `--optimizations DEFAULT --target_ops TFLITE_BUILTINS_INT8`

### Step 3.2: Verify Model File

```bash
# In PowerShell/terminal:
cd c:\Users\PRATHAM\DORA_MIXED-net
Get-Item trained_models/DORA/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite | Select-Object Length

# Should show size: ~200-500 KB (quantized model)
```

---

## 📱 PHASE 4: START DASHBOARD SERVER (5 minutes)

### Step 4.1: Start Python Server

```bash
# In PowerShell:
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
python server.js  # OR if using Python backend: python app.py
```

**Expected output:**
```
Server running on http://localhost:8765
WebSocket ready at ws://localhost:8765/stream
```

### Step 4.2: Start Frontend (Optional - if using React)

```bash
# In another PowerShell window:
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
npm run dev

# Or if built:
npm run preview
```

### Step 4.3: Open Dashboard

Open browser and go to: **http://localhost:8765** (or http://localhost:3000 if using Vite)

---

## 🚀 PHASE 5: DEPLOY FULL FIRMWARE (30 minutes)

### Step 5.1: Create Full Firmware Project

The full DORA firmware requires:
- TensorFlow Lite Micro
- Opus codec (for audio compression)
- WebSocket client
- Audio capture driver

**Two options:**

#### Option A: Use Existing Firmware (If Available)

If a complete firmware project exists:

```bash
# Navigate to firmware directory
cd dora_firmware

# Build
idf.py build

# Flash to ESP32
idf.py flash monitor

# You should see:
# [I] DORA Inference Engine Starting
# [I] Connecting to WiFi: YOUR_SSID
# [I] Connected! IP: 192.168.1.XXX
# [I] WebSocket Connected to ws://192.168.1.100:8765
# [I] Listening for keyword...
```

#### Option B: Use Microphone-Only Firmware (Recommended to Start)

Start simple - just send raw audio to the server for processing:

```bash
# This is what we tested above (mic_test.ino)
# Can be extended to stream audio to server
# See Step 5.2 below
```

### Step 5.2: Configure Network

Edit the firmware to connect to your network:

**For Arduino firmware:**
```c
// In the sketch, find and update:
#define WIFI_SSID "YOUR_WIFI_NAME"
#define WIFI_PASS "YOUR_WIFI_PASSWORD"
#define SERVER_IP "192.168.1.100"  // Your laptop IP
```

**Find your computer's IP:**
```bash
# Windows PowerShell:
ipconfig
# Look for "IPv4 Address" under your active network (e.g., 192.168.1.100)

# Mac/Linux:
ifconfig | grep "inet " | grep -v 127.0.0.1
```

### Step 5.3: Build & Upload Full Firmware

```bash
# If using ESP-IDF:
cd dora_firmware
idf.py build
idf.py flash monitor

# If using Arduino IDE:
# 1. Create new sketch
# 2. Copy full firmware code
# 3. Upload same as microphone test
```

### Step 5.4: Monitor Output

Serial Monitor should show:
```
[BOOT] DORA Inference Engine v1.0
[I2S] Initializing audio capture at 16000 Hz
[WiFi] Connecting to "YOUR_SSID"...
[WiFi] Connected! IP: 192.168.1.50
[WS] Connecting to ws://192.168.1.100:8765/stream
[WS] Connected!
[KWS] Listening for "DORA"...
[TELEMETRY] RAM: 112 KB, CPU: 5.2%
```

---

## 🎤 PHASE 6: END-TO-END TESTING (10 minutes)

### Test 1: Keyword Detection

1. **Speak the keyword** clearly: "DORA" (pause) "DORA"
2. **Watch for:**
   - Serial Monitor shows detection confidence
   - Dashboard receives audio stream (if display implemented)
   - Server logs show incoming audio

### Test 2: Latency Measurement

1. **Clap once** sharply near microphone
2. **Note the time** on dashboard when detection appears
3. Expected latency: **100-500ms** from audio to detection

### Test 3: False Positive Test

1. **Speak other words:** "Hello", "Hi", "Camera", "Data"
2. **Should NOT trigger** detection
3. Monitor should stay quiet

### Test 4: Continuous Streaming

1. **Keep server running** for 2+ minutes
2. **Speak multiple keywords** throughout
3. **Check:**
   - No crashes
   - No disconnections
   - Telemetry updating every 5 seconds

---

## 📊 PHASE 7: VALIDATION CHECKLIST

### Hardware Tests ✅

- [ ] Microphone connects via 6 wires without issues
- [ ] Arduino IDE recognizes ESP32-S3 board
- [ ] Firmware uploads successfully (no compile errors)
- [ ] Serial Monitor shows stable output at 9600 baud
- [ ] Microphone responds to sound (RMS/peak values change)

### Software Tests ✅

- [ ] Trained model file exists at expected path
- [ ] Model file size is 200-500 KB
- [ ] Dashboard server starts without errors
- [ ] ESP32 connects to WiFi successfully
- [ ] ESP32 connects to WebSocket server

### Integration Tests ✅

- [ ] Keyword "DORA" triggers detection
- [ ] False positives minimal (other words don't trigger)
- [ ] System runs for 2+ minutes without crashing
- [ ] Latency is reasonable (< 500ms)
- [ ] Telemetry data updates correctly

---

## 🐛 TROUBLESHOOTING

### Problem: "Port not found" in Arduino IDE

**Solution:**
1. Unplug USB cable
2. Wait 2 seconds
3. Plug back in
4. Go to Tools → Port and select new COM port
5. Try upload again

### Problem: "Board not recognized"

**Solution:**
1. Go to Tools → Board → Boards Manager
2. Search "ESP32" and reinstall package
3. Restart Arduino IDE
4. Select ESP32-S3 Dev Module again

### Problem: "Upload successful" but Serial Monitor shows garbage

**Solution:**
1. Bottom-right of Serial Monitor, verify baud rate is **9600**
2. If not, click dropdown and select 9600
3. Close and reopen Serial Monitor

### Problem: Microphone values stay at ~0

**Solution:**
1. Check wiring: GPIO 4 (SCK), GPIO 5 (WS), GPIO 6 (SD)
2. Check power: VDD to 3.3V, GND to GND
3. Try different USB cable
4. Check INMP441 has power (small LED may be visible)

### Problem: WiFi connection fails

**Solution:**
1. Verify WiFi SSID and password are correct
2. Check router is broadcasting 2.4GHz (ESP32-S3 doesn't support 5GHz)
3. Ensure router is in range
4. Restart router and ESP32

### Problem: WebSocket connection fails

**Solution:**
1. Verify server IP is correct (run `ipconfig` to find)
2. Check server is running on correct port (default 8765)
3. Ensure firewall allows connections on port 8765
4. Try disabling Windows Firewall temporarily to test

---

## 📝 NEXT STEPS

After successful deployment:

1. **Collect more keyword samples** for better accuracy
2. **Tune threshold** for your environment (no false positives)
3. **Measure latency** precisely (add timestamps)
4. **Add commands** beyond keyword detection
5. **Test in different environments** (quiet vs. noisy)
6. **Optimize model size** for production deployment

---

## 📚 REFERENCE DOCUMENTS

- **Wiring Diagram:** ESP32_MIC_TEST/WIRING_STEPS_SIMPLE.txt
- **Microphone Test:** ESP32_MIC_TEST/mic_test.ino
- **Firmware Guide:** docs/08_Firmware_Guide.md
- **Deployment Guide:** docs/11_Deployment_Guide.md
- **Model Pipeline:** docs/06_Model_Pipeline.md

---

## ✨ SUCCESS CRITERIA

Your deployment is **SUCCESSFUL** when:

1. ✅ Microphone test passes (values respond to sound)
2. ✅ ESP32 connects to WiFi
3. ✅ ESP32 connects to dashboard server
4. ✅ Keyword "DORA" triggers detection consistently
5. ✅ System runs for 5+ minutes without crashing
6. ✅ False positive rate is low (< 1 false positive per minute)

---

**Questions? Check the troubleshooting section above or review the reference documents.**

**Ready? Start with Phase 1 (Hardware Setup) and work your way through. Good luck! 🚀**
