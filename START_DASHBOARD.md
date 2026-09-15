# START DORA DASHBOARD - No External Dependencies

## One-Click Start (Easy)

```powershell
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
powershell .\start-services.ps1
```

This opens 2 new windows automatically:
- **Window 1:** ESP32 Serial Bridge (WebSocket on port 8080)
- **Window 2:** Dashboard (Express server on port 5000)

Then open browser: **http://localhost:5000**

---

## Manual Start (3 Steps)

### Step 1: Open PowerShell Terminal 1
```powershell
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
node esp32-serial-bridge.js
```

Wait for:
```
🔧 ESP32 Serial Bridge
📡 Serial Port: COM3 @ 9600 baud
🌐 WebSocket: ws://localhost:8080
🩺 Health check: http://localhost:3000/health
```

### Step 2: Open PowerShell Terminal 2
```powershell
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
npm start
```

Wait for:
```
🚀 DORA Dashboard Server running on http://localhost:5000
```

### Step 3: Open Browser
```
http://localhost:5000
```

---

## What's Running

| Service | Port | Function |
|---------|------|----------|
| Serial Bridge | 8080 (WebSocket) | Reads ESP32 data |
| Dashboard | 5000 (HTTP) | React UI |
| Health Check | 3000 (HTTP) | Status endpoint |

---

## How It Works (NO VOSK NEEDED!)

1. **ESP32 sends** audio stats via serial (RMS, Peak, etc.)
2. **Serial Bridge reads** serial data
3. **Bridge detects** voice activity (RMS > 100)
4. **Bridge uses mock ASR** to simulate recognition
5. **Dashboard displays** detection with confidence, latency, transcript

---

## Mock ASR Behavior

**No Vosk server needed!** Built-in mock ASR:

- **Confidence > 150**: 80% chance to recognize "DORA"
- **Confidence 100-150**: 40% chance to recognize random keyword
- **Confidence < 100**: Background noise

Transcripts appear in Detection Log with:
- Time
- Confidence (from RMS)
- Latency (simulated 50-150ms)
- Verdict (TP/FP)

---

## Test Without Hardware

Even without ESP32 connected, you can:
1. Start serial bridge (will show "disconnected" status)
2. Dashboard still works in DEMO MODE
3. All metrics simulate in real-time

---

## Stop Services

Press `Ctrl+C` in each terminal

Or kill all:
```powershell
Get-Process node | Stop-Process -Force
```

---

## Troubleshooting

### "Could not find module 'serialport'"
```powershell
npm install serialport
```

### "Cannot find module 'ws'"
```powershell
npm install ws
```

### "Serial Bridge not responding"
```powershell
curl http://localhost:3000/health
```

### ESP32 not found (COM3)
Edit `esp32-serial-bridge.js` line 14:
```javascript
const SERIAL_PORT = 'COM4';  // Change to your port
```

List available ports:
```powershell
Get-WmiObject Win32_SerialPort
```

---

## Advanced: Real Vosk (Optional)

To use real Vosk cloud ASR later:

1. Install: `pip install vosk-server`
2. Run: `python -m vosk.server.server --port 2700`
3. Serial bridge will auto-connect and use real ASR

For now, **mock ASR works perfectly for testing!**

---

## Status: ✅ READY TO START

No external dependencies. Everything included.

```powershell
powershell .\start-services.ps1
```

Then open: http://localhost:5000
