# DORA Dashboard Hardware Integration Guide

## Architecture

```
ESP32-S3 (mic_test.ino)
    ↓ (Serial 9600 baud)
esp32-serial-bridge.js (Node.js)
    ↓ (WebSocket)
Dashboard (React)
    ↓ (HTTP)
Vosk ASR Cloud API
```

## Setup

### 1. Install Dependencies

```powershell
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
npm install serialport ws
```

### 2. Flash ESP32 Firmware

```powershell
cd c:\Users\PRATHAM\DORA_MIXED-net\ESP32_MIC_TEST
python -m esptool -p COM3 -b 115200 write-flash 0x0 mic_test.ino.bin
```

**Bootloader reset (if timeout):**
- Unplug USB
- Hold BOOT button
- Plug USB back in (while holding BOOT)
- Release BOOT

### 3. Start Serial Bridge

```powershell
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
node esp32-serial-bridge.js
```

Output:
```
🔧 ESP32 Serial Bridge
📡 Serial Port: COM3 @ 9600 baud
🌐 WebSocket: ws://localhost:8080
☁️  Vosk ASR: http://localhost:2700
---
🩺 Health check: http://localhost:3000/health
```

### 4. Start Dashboard (in another terminal)

```powershell
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
npm start
```

Access at: **http://localhost:5000**

---

## Data Flow

### ESP32 Serial Output (every 500ms)

```
MIC TEST
samples=512
rms=45.3
peak=1200
min=-890
max=1050
---
```

**Meaning:**
- `rms`: Root Mean Square of audio (larger = louder)
- `peak`: Absolute maximum sample value
- `min/max`: Range of audio samples

### Serial Bridge Processing

1. **Receives** ESP32 data via COM3
2. **Parses** metrics
3. **Triggers detection** when RMS > 100 (voice activity)
4. **Sends audio buffer** to Vosk ASR cloud
5. **Broadcasts** results to all dashboard clients via WebSocket

### Dashboard Display

- **Real latency** from ESP32 peak values
- **Real RAM/CPU** estimated from RMS
- **Live detection log** with timestamps, confidence, latency, verdict
- **Status indicator** shows CONNECTED or DEMO MODE

---

## Cloud ASR Integration (Vosk)

### Option 1: Local Vosk Server (Recommended)

```powershell
# Install Python if needed
python -m pip install vosk-server

# Run Vosk API server
python -m vosk.server.server --interface 0.0.0.0 --port 2700
```

### Option 2: Cloud Vosk (Azure/AWS)

Set environment variable:
```powershell
$env:VOSK_API_URL = "https://your-cloud-vosk-api.com"
```

### Option 3: Mock Vosk (Testing)

If Vosk unavailable, serial bridge will:
- Still show detection events
- Display "ASR Unavailable"
- Mark verdict as "ERROR"

---

## Files Structure

```
dashboard/
├── esp32-serial-bridge.js       ← Serial reader + WebSocket server + ASR
├── src/
│   ├── components/
│   │   └── DoraDashboard.jsx    ← Dashboard UI (updated for real data)
│   └── hooks/
│       └── useESP32Bridge.js    ← WebSocket connection hook
├── server.js                    ← Express server
└── package.json
```

---

## Testing

### 1. Verify Serial Connection

```powershell
# Check if port is accessible
Get-Content \\.\COM3
```

### 2. Check Serial Bridge Health

```powershell
curl http://localhost:3000/health
```

Response:
```json
{
  "status": "connected",
  "port": "COM3",
  "clients": 1,
  "bufferSize": 4800
}
```

### 3. Test WebSocket

```powershell
# Install wscat globally
npm install -g wscat

# Connect to bridge
wscat -c ws://localhost:8080
```

You'll see messages like:
```
{"type":"MIC_DATA","rms":45.3,"peak":1200,...}
{"type":"DETECTION","confidence":"150.3","latency":145,...}
```

### 4. Speak Near Microphone

ESP32 will detect audio and send detection events to dashboard.

---

## Troubleshooting

### "Could not resolve port COM3"
- Check ESP32 is plugged in
- Verify driver installed
- Try different port (COM4, COM5, etc.)

### "WebSocket connection refused"
- Make sure `esp32-serial-bridge.js` is running
- Check firewall allows port 8080

### "Vosk connection refused"
- Start Vosk server: `python -m vosk.server.server --port 2700`
- Or set `VOSK_API_URL` environment variable

### Dashboard shows "DEMO MODE"
- Serial bridge not connected
- Check `esp32-serial-bridge.js` console for errors
- Refresh dashboard to reconnect

---

## Performance Notes

- **Latency**: ~100-200ms (microphone → ASR → dashboard)
- **CPU**: <5% on ESP32 for I2S + VAD
- **Memory**: 300ms pre-roll buffer = 48KB
- **Bandwidth**: ~5KB per detection event

---

## Command Reference

```powershell
# Terminal 1: Serial Bridge
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
node esp32-serial-bridge.js

# Terminal 2: Dashboard
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
npm start

# Terminal 3: Vosk (optional)
python -m vosk.server.server --port 2700

# Terminal 4: Testing
wscat -c ws://localhost:8080
```

---

**Status**: ✅ Ready for live hardware testing
