# 🚀 DEPLOY YOUR TRAINED DORA MODEL TO ESP32

**This deploys YOUR trained model (the one you trained for hours) to ESP32 hardware.**

---

## 📋 WHAT YOU'LL GET:

✅ Your trained DORA model running on ESP32
✅ Real-time keyword detection (continuous 24/7)
✅ Live dashboard showing detection results
✅ Real performance metrics (CPU, RAM, latency)

---

## ⚡ COMPLETE DEPLOYMENT (5 Steps)

### STEP 1: Convert Model to ESP32 Format

**Run this command:**
```powershell
cd C:\Users\PRATHAM\DORA_MIXED-net
python convert_model_for_esp32.py
```

**Expected output:**
```
====================================
DORA MODEL → ESP32 CONVERSION
====================================

[1/4] Loading trained model...
  Path: trained_models/DORA/stream_state_internal
[2/4] Applying INT8 quantization...
[3/4] Converting to TFLite...
  ✅ Conversion successful
  Model size: 78,234 bytes
  ✅ Saved: trained_models/DORA/dora_model_int8.tflite
[4/4] Generating C header file...
  ✅ Saved: ESP32_MIC_TEST/dora_full_inference/model_data.h

✅ CONVERSION COMPLETE
```

**This creates:**
- `model_data.h` - Your model as C array (for ESP32)
- `dora_model_int8.tflite` - TFLite version (for reference)

---

### STEP 2: Install Arduino Libraries

**In Arduino IDE:**

1. Tools → Manage Libraries
2. Search: **"TensorFlowLite_ESP32"**
   - Install: "TensorFlowLite_ESP32 by tanakamasayuki"
3. Search: **"ESP32_audioI2S"**
   - Install if available, otherwise skip

---

### STEP 3: Upload Firmware to ESP32

**In Arduino IDE:**

1. **File → Open**
   - Navigate to: `ESP32_MIC_TEST/dora_full_inference/`
   - Open: **`dora_real_model.ino`**

2. **Select Board Settings:**
   - Board: **ESP32S3 Dev Module**
   - Port: **COM11** (check Device Manager if different)
   - Upload Speed: **921600**
   - USB CDC On Boot: **Enabled**

3. **Click Upload**
   - Wait for compilation (may take 2-3 minutes first time)
   - Wait for "Hard resetting via RTS pin..."

4. **Verify Upload:**
   - Open Serial Monitor (115200 baud)
   - Should see:
     ```
     ================================================
     DORA KEYWORD DETECTION - ESP32-S3
     Real Trained Model Deployment
     ================================================
     [I2S] ✅ Microphone ready
     [TFLite] Model loaded: 78234 bytes
     [TFLite] ✅ Model ready for inference
     [READY] Listening for 'DORA'...
     ```

---

### STEP 4: Connect Dashboard to ESP32

**Terminal 1 (ESP32 Bridge):**
```powershell
cd C:\Users\PRATHAM\DORA_MIXED-net\dashboard
node esp32-bridge.js
```

**Expected:**
```
✅ Serial bridge started
📡 Listening on COM11 @ 115200 baud
🌐 WebSocket server: ws://localhost:8080
[COM11] MIC_DATA
[COM11] rms=42.5
[COM11] ---
WebSocket client connected
```

**Terminal 2 (Dashboard UI):**
```powershell
cd C:\Users\PRATHAM\DORA_MIXED-net\dashboard
npm run dev
```

**Expected:**
```
VITE ready in 500 ms
➜  Local: http://localhost:5173/
```

---

### STEP 5: Test Detection

1. **Open browser:** http://localhost:5173

2. **Check connection:**
   - Top-right shows: 🟢 **"ESP32 LIVE"** (green dot)
   - Microphone panel visible with live RMS values

3. **Test audio:**
   - Speak normally → RMS level increases
   - Voice orb turns GREEN
   - Status shows "🎤 LISTENING"

4. **Test keyword:**
   - Say **"DORA"** clearly
   - Voice orb flashes RED
   - Text shows: "DORA"
   - Detection log adds entry with confidence score
   - Serial Monitor shows: `🎯 DETECTED! Confidence: 0.873`

---

## 📊 WHAT YOU'LL SEE:

### Serial Monitor (ESP32 Output):
```
MIC_DATA
rms=42.5
peak=1024
min=-128
max=127
samples=18176
---

🎯 DETECTED! Confidence: 0.873

DETECTION
confidence=0.873
latency=58
transcript=DORA
verdict=TP
---
```

### Dashboard:
- 🟢 **"ESP32 LIVE"** - Connected to real hardware
- **Voice Orb:** Pulses green when speaking, flashes red on detection
- **Detection Log:** Shows timestamp, confidence (from your model!)
- **Graph:** Confidence scores from your trained model
- **System Metrics:** Real CPU/RAM usage from ESP32

---

## 🔍 HOW TO KNOW IT'S YOUR REAL MODEL:

### ✅ Using Your Trained Model:
1. Serial Monitor shows model size matching your trained model
2. Confidence scores are from actual TFLite inference
3. Detection only happens when model confidence > 0.7
4. False positive rate matches your training metrics
5. Responds to YOUR voice samples (the ones you trained on)

### ❌ NOT Using Model (Simulation):
1. Would show generic confidence scores (always 0.85-0.99)
2. Would detect randomly, not based on audio
3. Would work even without microphone
4. Performance metrics would be fake

---

## 🐛 TROUBLESHOOTING:

### Problem: "model_data.h: No such file"
**Solution:** Run Step 1 again (`python convert_model_for_esp32.py`)

### Problem: "TensorFlowLite_ESP32.h: No such file"
**Solution:**
```powershell
# Install manually via Arduino Library Manager
# OR download: https://github.com/tanakamasayuki/TensorFlowLite_ESP32
```

### Problem: Upload fails - "Out of memory"
**Solution:** Model too large, reduce tensor_arena_size in .ino file

### Problem: "Model schema mismatch"
**Solution:** Update TensorFlow Lite library to match training version

### Problem: RMS stuck at 1.0 (hardware issue)
**Solution:** 
- Check wiring: SCK→GPIO4, WS→GPIO5, SD→GPIO6
- Check VDD=3.3V with multimeter
- Re-solder INMP441 connections

### Problem: Dashboard still shows "DEMO MODE"
**Solution:**
1. Close Arduino Serial Monitor
2. Restart Terminal 1 (bridge)
3. Hard refresh browser (Ctrl+Shift+R)

---

## 📈 PERFORMANCE EXPECTATIONS:

**With Your Trained Model:**
- **Latency:** 40-80ms (keyword detection)
- **CPU Usage:** 5-15% (idle listening)
- **RAM Usage:** ~70KB (model) + ~50KB (audio buffer)
- **Flash:** ~80KB (your model size)
- **Accuracy:** Matches your training metrics (check model_summary.txt)

**Detection Quality:**
- True Positive Rate: Based on your validation set
- False Positive Rate: Based on your training
- Works best with voices similar to training data
- May need threshold tuning (adjust DETECTION_THRESHOLD in .ino)

---

## 🎯 VERIFICATION CHECKLIST:

After deployment, verify these:

- [ ] Serial Monitor shows your model size (78KB or similar)
- [ ] TFLite initialization successful
- [ ] Arena memory allocated correctly
- [ ] MIC_DATA messages appearing every ~50ms
- [ ] RMS values change when speaking
- [ ] Dashboard shows "ESP32 LIVE"
- [ ] Voice orb responds to speech
- [ ] Saying "DORA" triggers detection
- [ ] Confidence scores are realistic (0.7-0.95)
- [ ] False positives are low (< 5% like training)

---

## 🔧 TUNING DETECTION:

**If too sensitive (many false positives):**
```cpp
// In dora_real_model.ino
#define DETECTION_THRESHOLD 0.8  // Increase from 0.7
```

**If not sensitive enough (missing detections):**
```cpp
#define DETECTION_THRESHOLD 0.6  // Decrease from 0.7
```

**Adjust cooldown between detections:**
```cpp
#define COOLDOWN_MS 1500  // Increase from 1000 (1.5s minimum gap)
```

---

## ✅ SUCCESS CRITERIA:

**Your deployment is successful when:**

1. ✅ ESP32 Serial Monitor shows model loaded
2. ✅ Dashboard shows 🟢 "ESP32 LIVE"
3. ✅ Speaking increases RMS level
4. ✅ Saying "DORA" triggers detection
5. ✅ Confidence scores match training expectations
6. ✅ System runs continuously without crashes
7. ✅ Detection latency < 100ms
8. ✅ False positive rate acceptable for your use case

---

## 📦 FILES CREATED:

After Step 1 (conversion):
- `trained_models/DORA/dora_model_int8.tflite` - TFLite model
- `ESP32_MIC_TEST/dora_full_inference/model_data.h` - C array for ESP32

Firmware:
- `ESP32_MIC_TEST/dora_full_inference/dora_real_model.ino` - Main firmware

Dashboard (already exists):
- `dashboard/esp32-bridge.js` - Serial → WebSocket
- `dashboard/src/components/DoraDashboard.jsx` - UI

---

## 🎉 YOU'RE DONE!

Your trained model is now running on ESP32 hardware!

**Next steps:**
- Collect real-world performance metrics
- Fine-tune threshold if needed
- Test with different speakers
- Measure battery life (if portable)
- Document false positive/negative rates

**For production deployment:**
- Add error recovery code
- Implement watchdog timer
- Add LED status indicators
- Optimize power consumption
- Add WiFi/BLE configuration interface

---

**Questions? Check Serial Monitor output and dashboard console (F12) for errors.**
