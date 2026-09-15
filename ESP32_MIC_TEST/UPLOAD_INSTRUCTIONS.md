# Quick Upload Guide — DORA ESP32-S3 Firmware

**Firmware**: `dora_full_inference.ino` — Real TFLite Micro inference  
**Status**: ✅ Compiles successfully (526 KB / 40% flash, 106 KB / 32% RAM)

---

## Prerequisites

1. **Arduino IDE 2.x** installed
2. **ESP32 board support** installed:
   - File → Preferences → Additional Board Manager URLs:
     ```
     https://espressif.github.io/arduino-esp32/package_esp32_index.json
     ```
   - Tools → Board → Boards Manager → search "esp32" → Install "esp32 by Espressif" (3.3.11)

3. **TensorFlowLite_ESP32 library** installed:
   - Tools → Manage Libraries → search "TensorFlowLite_ESP32"
   - Install **version 1.0.0** by tanakamasayuki
   - (Already present if you've used Arduino IDE before — shows as "INSTALLED" in Library Manager)

---

## Upload Steps

### 1. Connect Hardware
- Plug **ESP32-S3** into USB port
- Wait for driver installation (Windows may take 30 seconds)

### 2. Configure Arduino IDE
- **File → Open**: Navigate to `ESP32_MIC_TEST/dora_full_inference/dora_full_inference.ino`
- **Tools → Board**: ESP32 Arduino → **ESP32S3 Dev Module**
- **Tools → Port**: Select the COM port for your ESP32 (e.g., COM3, COM4)
  - If unsure, unplug/replug and see which port appears/disappears
- **Tools → Upload Speed**: 115200 (default) or 921600 (faster but may fail on some cables)

### 3. Upload
- Click **Upload** button (→ arrow icon) or press `Ctrl+U`
- Wait ~60 seconds for compilation + upload
- Progress bar shows: Connecting... Writing... Verifying... Done

**Expected output**:
```
Sketch uses 526240 bytes (40%) of program storage space.
Global variables use 105896 bytes (32%) of dynamic memory.
...
Hard resetting via RTS pin...
```

### 4. Open Serial Monitor
- **Tools → Serial Monitor** (or press `Ctrl+Shift+M`)
- Set baud rate to **115200** (bottom-right dropdown)
- Press **RST button** on ESP32 to reboot and see boot sequence

---

## Expected Serial Output

**Boot sequence** (first 5 seconds):
```
============================================================
  DORA KEYWORD DETECTION — ESP32-S3
  Streaming MixedNet INT8 | Real TFLite Micro Inference
============================================================
  Model size   : 68600 bytes
  Sample rate  : 16000 Hz
  Frame size   : 10 ms (160 samples)
  Mel bins     : 40
  KWS threshold: 0.90
  Smoothing    : 5-frame avg (50 ms)
  Arena budget : 80 KB
------------------------------------------------------------
[I2S]    OK — microphone ready
[Frontend] OK — PCAN mel filterbank ready
------------------------------------------------------------
  BENCHMARK (at init)
------------------------------------------------------------
  Arena allocated (budget)       : 80 KB
  Arena actually used            : XXXXX bytes
  Free heap after interpreter    : XXXXX bytes
  Min free heap (so far)         : XXXXX bytes
------------------------------------------------------------
  Input tensor : [1,3,40]  type=float32
  Output tensor: [1,1]     type=float32
============================================================
[READY] Listening for 'DORA'...
```

**During listening** (every 10 ms):
```
MIC_DATA
rms=12.34
peak=1234
samples=160
confidence=0.123
smoothed=0.145
feat_us=1234
infer_us=3456
---
```

**On detection**:
```
DETECTION
confidence=0.998
smoothed=0.992
latency=150
transcript=DORA
verdict=TP
---

  ╔══════════════════════════════════════╗
  ║  DORA DETECTED!  score=0.998  avg=0.992  ║
  ╚══════════════════════════════════════╝

  [BENCHMARK]
    Free heap after interp : 223456 bytes
    Min free heap          : 220123 bytes
    Arena used             : 54321 bytes
    Feature extract time   : 1234 µs
    TFLite inference time  : 3456 µs
    Total proc / 10ms frame: 4690 µs
```

---

## Troubleshooting

### ❌ "Port not found" / "Device not detected"
- **Check USB cable**: Use a data cable (not charge-only)
- **Install CH340 driver** (if ESP32 uses CH340 USB chip):
  - Download from: https://www.wch.cn/downloads/CH341SER_ZIP.html
- **Try different USB port**: USB 2.0 often more reliable than 3.0
- **Check Device Manager** (Windows): Look for "USB-SERIAL CH340" or "CP210x"

### ❌ "Compilation error" / "TensorFlowLite_ESP32.h: No such file"
- **Verify library installation**: Tools → Manage Libraries → search "TensorFlowLite_ESP32"
- If missing: Install **TensorFlowLite_ESP32 v1.0.0** by tanakamasayuki
- **Restart Arduino IDE** after installation

### ❌ "Upload failed" / "Connecting........"
- **Hold BOOT button** on ESP32 while clicking Upload (release after "Connecting...")
- **Lower upload speed**: Tools → Upload Speed → 115200
- **Check COM port**: Tools → Port → verify correct port selected

### ❌ Boot loop / Repeated resets
- **Check power supply**: ESP32-S3 needs 500 mA; USB 2.0 may be insufficient
- **Try powered USB hub** or different USB port
- **Check I2S wiring**: Loose connections can cause crashes

### ❌ Microphone not working / No MIC_DATA output
- **Verify I2S connections**:
  ```
  INMP441 → ESP32-S3
  SCK     → GPIO4
  WS      → GPIO5
  SD      → GPIO6
  VDD     → 3.3V
  GND     → GND
  ```
- **Check microphone gain** (line 320 in .ino):
  ```cpp
  pcm_frame[i] = (int16_t)(raw >> 14);  // Try >>11 or >>8 if too quiet
  ```
- **Serial output shows rms=0.00?**: Microphone not connected or not powered

### ⚠️ Warnings about deprecated I2S API
- **Harmless**: ESP32 Arduino 3.3.11 still supports legacy I2S API
- Code works correctly despite warnings
- Future migration to `driver/i2s_std.h` will silence warnings

---

## Benchmark Targets

After first successful boot, check these values in serial output:

| Metric | Expected Range | Action if Outside Range |
|--------|----------------|------------------------|
| Arena used | 40–60 KB | If <50 KB, reduce `kTensorArenaSize` to save RAM |
| Free heap | >200 KB | If <150 KB, investigate memory leak |
| Feature time | 500–1500 µs | If >2000 µs, check CPU frequency (should be 240 MHz) |
| Inference time | 2000–5000 µs | If >8000 µs, verify TFLite model loaded correctly |
| Total frame time | <10000 µs | Must be <10 ms for real-time; if >10 ms, optimize |

---

## Quick Test Procedure

1. **Upload firmware** → Wait for "READY" message
2. **Say "DORA"** into microphone (within 30 cm)
3. **Observe detection** → Should trigger within 200–300 ms
4. **Check false alarms** → Leave running in quiet room for 5 minutes
   - Expected: <1 false alarm per minute at threshold=0.90
   - If >3 FA/min, raise `KWS_THRESHOLD` to 0.95

5. **Benchmark performance**:
   - Feature + inference time should be <8 ms per frame
   - Free heap should stay >200 KB
   - No repeated resets or crashes

6. **Adjust threshold** if needed:
   - Missing detections? Lower `KWS_THRESHOLD` from 0.90 → 0.85
   - Too many false alarms? Raise to 0.95 or increase `KWS_WINDOW_SIZE` to 7

---

## Next: Dashboard Integration

Once the ESP32 is running and detecting correctly:

1. **Note the COM port** (e.g., COM3)
2. **Configure dashboard bridge**:
   ```javascript
   // dashboard/esp32-serial-bridge.js line 4
   const SERIAL_PORT = 'COM3';  // <-- Update this
   ```
3. **Start dashboard**:
   ```bash
   cd dashboard
   npm start
   ```
4. **Open browser**: http://localhost:5173
5. **Verify live telemetry**: MIC_DATA updates every 10 ms

---

**✅ Upload complete!** The ESP32 is now running **real TFLite Micro inference** with the trained Streaming MixedNet model.

If you see the "READY" message in serial monitor, the firmware is working correctly. Test with real audio to verify detection accuracy.

**For detailed technical documentation**: See `ESP32_FIRMWARE_COMPLETE.md`
