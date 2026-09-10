# Cloud ASR Server & Real-Time Dashboard
## Document 09 — SIH26172 | DORA

---

## 1. Overview

The server is a single Python process running on port 8765. It handles three concerns:

| Endpoint | Protocol | Purpose |
|---|---|---|
| `ws://server:8765/stream` | WebSocket | Receive Opus audio from ESP32, run Vosk ASR, measure latency |
| `POST /telemetry` | HTTP | Receive RAM/CPU metrics from ESP32 |
| `GET /data` | HTTP | Return current state as JSON (polled by dashboard) |
| `GET /` | HTTP | Serve `dashboard.html` |

Everything runs in one `uvicorn` process. No message broker, no database, no separate services.

---

## 2. Setup

### 2.1 Python Environment

```bash
pip install fastapi "uvicorn[standard]" vosk opuslib websockets numpy
```

### 2.2 Vosk Model Download

```bash
# Download the small English model (~40 MB)
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
# This creates: vosk-model-small-en-us-0.15/ in the current directory
```

> The Vosk model directory must be in the same folder as `server.py`. If you move it, update `VOSK_MODEL_PATH` in `server.py`.

### 2.3 Start the Server

```bash
python server.py
# Dashboard available at: http://localhost:8765/
# WebSocket endpoint at:  ws://localhost:8765/stream
```

For LAN access (ESP32 on same network):
```bash
# The server binds to 0.0.0.0 by default — accessible from any LAN device
# Access from browser: http://<server_laptop_ip>:8765/
```

---

## 3. Server Architecture (`server.py`)

### 3.1 Shared State

```python
state = {
    "ram_kb":         0,      # from ESP32 telemetry POST
    "cpu_pct":        0.0,    # from ESP32 telemetry POST
    "detections":     0,      # incremented per keyword event
    "last_latency_ms": None,  # keyword-end → first-byte ms
    "last_asr_text":  "",     # most recent Vosk final result
    "events":         []      # ring buffer, last 100 events
}
```

All endpoints read and write this dictionary. FastAPI's async event loop ensures no concurrent modification issues for simple types.

### 3.2 WebSocket Handler (`/stream`)

**Per session (one ESP32 connection):**

```
1. Accept WebSocket
2. Create KaldiRecognizer(vosk_model, 16000)
3. Create opuslib.Decoder(16000, channels=1)
4. Loop:
   a. Receive frame (text or binary)
   b. If text JSON, type=="start":
      → Record t_kw_end and t_arrived
      → Compute latency_ms = (t_arrived - t_kw_end) * 1000
   c. If binary (Opus audio):
      → Decode Opus → PCM (320 samples)
      → Feed PCM bytes to KaldiRecognizer
      → If partial result available, send {"type":"partial","text":"..."}
   d. If text JSON, type=="end":
      → Get final ASR text from recognizer.FinalResult()
      → Append event to state["events"]
      → Send {"type":"result","text":"...","latency_ms":...} back to device
```

### 3.3 Latency Calculation Detail

```python
if msg.get("type") == "start":
    # t_kw_end_us comes from esp_timer_get_time() on the device
    # It is microseconds since device boot (not wall clock)
    # We compare against server wall clock time.time()
    # This measures: keyword-end on device → first bytes arrive at server
    t_kw_end  = msg["t_kw_end_us"] / 1_000_000   # µs → seconds
    t_arrived = time.time()
    latency_ms = round((t_arrived - t_kw_end) * 1000, 1)
```

> This is the correct measurement for the PS's third judging criterion. It captures Wi-Fi transit + Opus encoding + WebSocket framing overhead. It does NOT require NTP or clock synchronisation between device and server.

### 3.4 Telemetry Endpoint (`POST /telemetry`)

```python
@app.post("/telemetry")
async def recv_telemetry(data: dict):
    state.update({k: v for k, v in data.items() if k in ("ram_kb", "cpu_pct")})
    return {"ok": True}
```

Accepts: `{"ram_kb": 88, "cpu_pct": 7.3}`  
Updates state immediately — dashboard sees it within 1 second.

---

## 4. Dashboard Design (`dashboard.html`)

### 4.1 Layout

```
┌──────────────────────────────────────────────────────────────┐
│  DORA · Live Monitor                           ● Live / Offline│
├──────────────────────────────────────────────────────────────┤
│  Last Latency  │  Detections  │  Free RAM  │  Idle CPU        │
│   42.1 ms      │     17       │  88 KB     │   7.3%           │
├──────────────────────────────────────────────────────────────┤
│                                          │                    │
│  Latency over time (line chart)          │  Last ASR Result   │
│  Target < 75 ms (dashed red line)        │  "hello dora"      │
│                                          │  System info       │
├──────────────────────────────────────────────────────────────┤
│  Detection Event Log                     │  Session Stats     │
│  [time] [latency] [ASR text]             │  min/max/avg/p95   │
└──────────────────────────────────────────────────────────────┘
```

### 4.2 Colour Coding

| Metric | Green | Amber | Red |
|---|---|---|---|
| Latency | < 75 ms | 75–150 ms | > 150 ms |
| RAM bar fill | < 70% used | 70–90% used | > 90% used |
| CPU | ≤ 10% | — | > 10% |
| Status pill | Server reachable | — | Server offline |

### 4.3 Chart Configuration

- **Type:** Line chart (Chart.js 4.4.0)
- **Data:** Last 30 detection events
- **Y-axis:** 0–300 ms
- **Reference line:** Dashed red at 75 ms target
- **Animation:** Disabled (`animation: false`) for instant updates
- **Refresh:** Every 1 second via `setInterval(refresh, 1000)`

### 4.4 Session Statistics Panel

Computed client-side from the events array on each refresh:

```javascript
Min latency  = Math.min(...allLats)
Max latency  = Math.max(...allLats)
Avg latency  = allLats.reduce((a,b)=>a+b,0) / allLats.length
p95 latency  = percentile(allLats, 95)   // sorted array index
```

---

## 5. Server Deployment Options

### 5.1 Laptop (Recommended for Demo)

```bash
python server.py
# Runs on port 8765, accessible at http://<laptop-ip>:8765/
```

### 5.2 Raspberry Pi 4

```bash
# Install dependencies
pip3 install fastapi "uvicorn[standard]" vosk opuslib websockets numpy

# Run as a systemd service for auto-start
sudo nano /etc/systemd/system/dora-server.service
```

```ini
[Unit]
Description=DORA ASR Server
After=network.target

[Service]
User=pi
WorkingDirectory=/home/pi/DORA_MIXED-net
ExecStart=/usr/bin/python3 server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable dora-server
sudo systemctl start dora-server
```

---

## 6. Vosk Model Options

| Model | Size | Latency | Use Case |
|---|---|---|---|
| `vosk-model-small-en-us-0.15` | 40 MB | 10–20 ms | **Demo — use this** |
| `vosk-model-en-us-0.22` | 1.8 GB | 30–60 ms | Higher accuracy |
| `vosk-model-small-en-in-0.4` | 36 MB | 10–20 ms | Indian English accent |

For SIH demo, use the small model. It has sufficient accuracy for short commands and gives the lowest latency.

---

## 7. Testing the Server Independently

```python
# test_server.py — test without the ESP32
import asyncio, websockets, json

async def test():
    uri = "ws://localhost:8765/stream"
    async with websockets.connect(uri) as ws:
        # Simulate keyword detection
        import time
        t_us = int(time.time() * 1_000_000)
        await ws.send(json.dumps({"type":"start","t_kw_end_us": t_us}))
        
        # Send dummy silence (320 zero samples, Opus-encoded)
        # In a real test, send actual Opus frames
        
        await ws.send(json.dumps({"type":"end"}))
        result = await ws.recv()
        print("Server response:", result)

asyncio.run(test())
```
