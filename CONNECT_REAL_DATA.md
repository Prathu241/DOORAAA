# 🔴 Dashboard Shows DEMO MODE → 🟢 Get REAL ESP32 Data

## Current Status: SIMULATED DATA
**Top-right shows:** 🔴 "DEMO MODE" (red dot)
**What this means:** Dashboard is running but showing fake/simulated data

---

## To Get REAL-TIME Data from ESP32:

### ⚡ QUICK METHOD (Without WiFi) - RECOMMENDED

**This method sends data via USB serial directly to dashboard**

#### Step 1: Upload Simple Test Firmware
```
File: ESP32_MIC_TEST/mic_test.ino (already exists)
Board: ESP32S3 Dev Module
Port: COM11
```

**Upload** the mic_test.ino (you already did this earlier)

#### Step 2: Close Arduino Serial Monitor
**IMPORTANT:** Serial Monitor blocks the COM port!
- Close Arduino IDE Serial Monitor completely

#### Step 3: Start ESP32 Bridge (Terminal 1)
```powershell
cd C:\Users\PRATHAM\DORA_MIXED-net\dashboard
node esp32-bridge.js
```

**Expected output:**
```
✅ Serial bridge started
📡 Listening on COM11 @ 115200 baud
🌐 WebSocket server: ws://localhost:8080
Waiting for ESP32 data...
```

#### Step 4: Dashboard Already Running (Terminal 2)
```
Keep npm run dev running
Refresh browser: http://localhost:5173
```

**Now dashboard should show:**
- 🟢 **"ESP32 LIVE"** (green dot) instead of red
- **Real RMS values** from microphone
- **Real metrics** updating

---

### 🌐 FULL METHOD (With WiFi) - More Complex

This uses WiFi to connect ESP32 to dashboard wirelessly.

#### Step 1: Find Your Computer's IP
```powershell
ipconfig
```
Look for "IPv4 Address" under your WiFi adapter (e.g., 192.168.1.100)

#### Step 2: Edit Firmware WiFi Settings
```
File: ESP32_MIC_TEST/dora_full_inference/dora_full_inference.ino
```

Change these lines:
```cpp
#define WIFI_SSID "YOUR_WIFI_NAME"        // Your WiFi network name
#define WIFI_PASS "YOUR_WIFI_PASSWORD"    // Your WiFi password
#define SERVER_IP "192.168.1.100"         // Your PC's IP from ipconfig
```

#### Step 3: Install WebSockets Library
- Arduino IDE → Tools → Manage Libraries
- Search: "WebSocketsClient"
- Install: **"WebSockets by Markus Sattler"**

#### Step 4: Upload Full Inference Firmware
- Open: `ESP32_MIC_TEST/dora_full_inference/dora_full_inference.ino`
- Board: ESP32S3 Dev Module
- Port: COM11
- Click **Upload**

#### Step 5: Start Bridge + Dashboard
Same as Quick Method steps 2-4 above

---

## How to Check if Real Data is Working:

### ✅ SUCCESS Indicators:

**Top-Right Header:**
- Shows: 🟢 **"ESP32 LIVE"** (green dot)
- NOT: 🔴 "DEMO MODE"

**System Metrics Panel:**
- **CPU:** Changes based on processing (not stuck at 7%)
- **RAM:** Shows actual memory usage (not stuck at 150KB)

**Microphone Panel (appears when connected):**
- **RMS Level:** Changes when you speak (40-60 silent, 200-300 speaking)
- **Peak:** Shows amplitude spikes
- **Samples:** Increases continuously
- **Status:** Says "CAPTURING AUDIO" or "SILENT / LOW SIGNAL"

**Voice Orb:**
- **Idle (Blue):** When silent
- **Active (Green):** When you speak → RMS > 50
- **Detected (Red):** When "DORA" detected → RMS > 200

**Detection Log:**
- Real timestamps (not simulated)
- Actual confidence scores from model
- Updates only when you speak "DORA"

### ❌ DEMO MODE Indicators:

**Top-Right Header:**
- Shows: 🔴 **"DEMO MODE"** (red dot)

**Behavior:**
- Stats change randomly every 2-3 seconds
- Detection log adds fake entries automatically
- Metrics look realistic but are simulated
- No microphone panel visible
- Voice orb stays blue (never responds to real audio)

---

## Terminal Output to Check:

### Terminal 1 (esp32-bridge.js) - When Working:
```
✅ Serial bridge started
📡 Listening on COM11 @ 115200 baud
🌐 WebSocket server: ws://localhost:8080
[COM11] MIC TEST
[COM11] samples=18176
[COM11] rms=42.5
[COM11] peak=1024
[COM11] ---
WebSocket client connected
```

### Terminal 1 - When NOT Working:
```
✅ Serial bridge started
📡 Listening on COM11 @ 115200 baud
ERROR: Cannot open COM11
Error: Port is busy or doesn't exist
```

**Fix:** Close Arduino Serial Monitor

---

## Current Microphone Status:

From your previous tests, you showed:
```
samples=18176
rms=1.0
peak=1
min=-1
max=-1
```

**This means:**
- ⚠️ **Microphone is NOT capturing audio properly**
- RMS should be 40-60 (silent) or 200-300 (speaking)
- RMS stuck at 1.0 = hardware issue

**Possible causes:**
1. Wrong GPIO pins (check: SCK→GPIO4, WS→GPIO5, SD→GPIO6)
2. Loose wiring / bad soldering
3. INMP441 not getting power (check VDD=3.3V with multimeter)
4. Damaged microphone

**Even with broken microphone:**
- Dashboard will still show "ESP32 LIVE" (green)
- You'll see samples increasing
- But RMS will be stuck at low values
- Detection won't work until mic fixed

---

## Quick Test Commands:

### Test 1: Check if ESP32 is sending data
```powershell
# In dashboard folder
node esp32-bridge.js
```
Watch for: `[COM11] MIC TEST` or `[COM11] samples=...`

### Test 2: Check WebSocket connection
```
Open browser → F12 → Console tab
Look for: "✅ WebSocket connected to ESP32 bridge"
```

### Test 3: Manually check serial data
```
Open Arduino Serial Monitor
Set to 115200 baud
You should see:
  MIC TEST
  samples=18176
  rms=42.5
  ---
```

---

## RECOMMENDED: Start with Quick Method

1. **Don't edit firmware WiFi** (skip that for now)
2. **Use USB serial** (simpler, no WiFi needed)
3. **Upload mic_test.ino** (you already did)
4. **Close Serial Monitor**
5. **Run esp32-bridge.js**
6. **Refresh dashboard**

**Result:**
- Dashboard shows: 🟢 "ESP32 LIVE"
- Real RMS values displayed
- Microphone panel appears
- Stats come from hardware

**Once this works, THEN** you can try WiFi method if you want wireless connection.

---

## Troubleshooting:

**Q: Bridge says "Cannot open COM11"**
A: Close Arduino Serial Monitor completely

**Q: Dashboard still shows DEMO MODE**
A: 
1. Check Terminal 1 shows "WebSocket client connected"
2. Hard refresh browser (Ctrl+Shift+R)
3. Check F12 Console for errors

**Q: ESP32 LIVE but RMS stuck at 1.0**
A: Microphone hardware issue (wiring/soldering), not dashboard problem

**Q: No "Microphone Live Feed" panel visible**
A: Dashboard only shows it when `isConnected=true`, check bridge running

---

## Summary:

**DEMO MODE = Dashboard working, no hardware connected**
**ESP32 LIVE = Dashboard receiving real data from ESP32**

To switch from DEMO → LIVE:
1. Upload firmware to ESP32 ✅ (you did this)
2. Close Serial Monitor ⚠️ (do this)
3. Start bridge: `node esp32-bridge.js` ⚠️ (do this)
4. Refresh dashboard ⚠️ (do this)

After these 4 steps, top-right should show: 🟢 **"ESP32 LIVE"**

---

**Current Next Step:** Run the bridge to connect hardware to dashboard.
