# 🚀 DORA Dashboard - Quick Start Guide

## ✅ What You Get

**LIVE Real-Time Dashboard with:**
- 🎙️ **Voice Activation Orb** (Grok-style) - pulses when speaking, glows on detection
- 📊 **Real-time ESP32 metrics** - CPU, RAM, Flash usage
- 📈 **Detection confidence graph** - shows last 50 detections
- 🔴 **Live status indicators** - see exactly when mic is active
- 🌊 **Audio waveform visualization**
- 📝 **Detection log** - timestamp, confidence, verdict

**Theme:** Neon blue futuristic design (UNCHANGED as requested)

---

## 🔧 Prerequisites

1. **Node.js installed** (check: `node --version`)
2. **ESP32 connected** to USB port
3. **WebSockets library** installed in Arduino IDE:
   - Open Arduino IDE
   - Go to: **Tools → Manage Libraries**
   - Search: `WebSocketsClient`
   - Install: **"WebSockets by Markus Sattler"**

---

## ⚡ Quick Start (2 Terminals)

### Terminal 1: ESP32 Serial Bridge
```powershell
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
npm install
node esp32-bridge.js
```

**Expected output:**
```
✅ Serial bridge started
📡 Listening on COM11 @ 115200 baud
🌐 WebSocket server: ws://localhost:8080
Waiting for ESP32 data...
```

### Terminal 2: Dashboard UI
```powershell
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
npm run dev
```

**Expected output:**
```
VITE v5.4.21  ready in 423 ms

➜  Local:   http://localhost:5173/
➜  Network: use --host to expose
```

### Step 3: Open Browser
Go to: **http://localhost:5173**

---

## 🎯 Testing the System

### 1. Check Dashboard Opens
- You should see the futuristic neon blue interface
- Header shows: **"D:OR DORA — Edge Voice Activator"**
- Voice orb in top-left (blue circle with rings)

### 2. Check ESP32 Connection
- Look at top-right: should show **"ESP32 LIVE"** (green dot)
- If shows **"DEMO MODE"** (red dot) → ESP32 not connected

### 3. Test Voice Detection
**Speak "DORA" into microphone:**

**What should happen:**
1. Voice orb turns **GREEN** and pulses
2. Orb shows "🎤 LISTENING" 
3. When "DORA" detected → orb flashes **ORANGE/RED**
4. Text appears: **"DORA"** below orb
5. Detection log updates with timestamp + confidence
6. Graph shows new detection spike

**Metrics to watch:**
- **RMS Level:** Should be 40-60 (silent), 200-300 (speaking)
- **Peak:** Audio amplitude (0-32767)
- **CPU:** Should stay < 10% idle
- **RAM:** Shows memory used by KWS system

---

## 🐛 Troubleshooting

### Problem: Dashboard shows "DEMO MODE"
**Cause:** ESP32 not sending data to bridge

**Fix:**
1. Check ESP32 is connected: Open **Device Manager → Ports (COM & LPT)**
2. Note the COM port (e.g., COM11)
3. Edit `esp32-bridge.js`:
   ```javascript
   const SERIAL_PORT = 'COM11';  // Change to your port
   ```
4. Restart Terminal 1 (bridge)

### Problem: "Port COM11 is busy"
**Cause:** Arduino Serial Monitor still open

**Fix:**
1. Close **Arduino Serial Monitor** completely
2. Restart Terminal 1

### Problem: Voice orb not activating
**Cause:** Microphone not capturing audio

**Fix:**
1. Check wiring:
   - INMP441 SCK → ESP32 GPIO4
   - INMP441 WS → ESP32 GPIO5
   - INMP441 SD → ESP32 GPIO6
   - INMP441 VDD → ESP32 3.3V
   - INMP441 GND → ESP32 GND
   - INMP441 L/R → ESP32 GND
2. Check Serial Monitor output shows varying RMS (not stuck at 1.0)
3. Re-upload `dora_full_inference.ino`

### Problem: WebSocket connection failed
**Cause:** Bridge not running or wrong port

**Fix:**
1. Make sure Terminal 1 is running `node esp32-bridge.js`
2. Check output shows "WebSocket server: ws://localhost:8080"
3. Check firewall not blocking port 8080

### Problem: RMS stuck at 1.0 or 0.0
**Cause:** Microphone hardware issue or wrong pins

**Fix:**
1. **Double-check wiring** (most common issue)
2. Try different GPIO pins in firmware
3. Test microphone with multimeter (VDD should be 3.3V)
4. Check soldering connections

---

## 📂 Files Structure

```
dashboard/
├── src/
│   ├── components/
│   │   ├── DoraDashboard.jsx       # Main dashboard UI
│   │   └── DoraDashboard.css       # Neon blue theme + orb styles
│   ├── hooks/
│   │   └── useESP32Bridge.js       # WebSocket connection hook
│   └── main.jsx
├── esp32-bridge.js                  # Serial → WebSocket bridge
├── package.json
└── DASHBOARD_START.md              # This file
```

---

## 🔥 What Each Component Does

### Voice Activation Orb
- **Blue (idle):** Waiting for audio
- **Green (active):** Detecting voice, RMS > 50
- **Red (detected):** "DORA" detected with high confidence
- **Rings:** Pulse outward when active (Grok-style animation)

### Real-Time Metrics
- **CPU:** Percentage of ESP32 processing power used
- **RAM:** Memory used by keyword detection system (out of 256KB)
- **Flash:** Model size on ESP32 storage (int8 quantized)
- **Latency:** Keyword-end to ASR transcript time

### Detection Graph
- **Green line:** Confidence score (0.0 - 1.0)
- **Red dashed line:** Detection threshold (0.7)
- **Shaded area:** Visual confidence indicator
- Shows last 50 detections

### Detection Log
- **Time:** HH:MM:SS in 24-hour format
- **Confidence:** Model prediction score (0.85-0.99 typical)
- **Latency:** Response time in milliseconds
- **Verdict:** TP (true positive) or FP (false positive)

---

## 🎨 Theme Colors (DO NOT CHANGE)

```css
Primary Blue: #0AF
Accent Green: #00B85C
Warning Orange: #FF5A1F
Background: #06070A
Text: #E5E5E5
Muted: #667
```

---

## 📡 ESP32 Serial Protocol

The bridge expects this format from ESP32:

```
MIC TEST
samples=18176
rms=42.5
peak=1024
min=-128
max=127
---

DETECTION
confidence=0.873
latency=58
transcript=DORA
verdict=TP
---
```

---

## ✅ Success Checklist

- [ ] Dashboard opens in browser (http://localhost:5173)
- [ ] Top-right shows "ESP32 LIVE" (green)
- [ ] Voice orb is visible and blue
- [ ] System metrics show real values (not 0)
- [ ] Speaking makes RMS level increase
- [ ] Saying "DORA" triggers orb to flash red
- [ ] Detection appears in log with timestamp
- [ ] Graph updates with new confidence point

---

## 🚀 Next Steps

1. **Upload full inference firmware** to ESP32
2. **Edit WiFi credentials** in `dora_full_inference.ino`
3. **Test continuous detection** (system runs 24/7)
4. **Fine-tune threshold** if too many false positives
5. **Record metrics** for project documentation

---

## 💡 Tips

- **Keep both terminals running** for dashboard to work
- **Don't close Arduino Serial Monitor** while bridge is running
- **Refresh browser** if WebSocket disconnects
- **Check Terminal 1 output** to see real-time ESP32 data
- **System detects continuously** - no time limits!

---

**Dashboard Status: ✅ READY FOR TESTING**

Built with ❤️ for SIH26172 ISRO Edge Voice Activation System
