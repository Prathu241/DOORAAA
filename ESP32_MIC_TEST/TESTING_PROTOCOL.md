# DORA ESP32 Testing Protocol
## Complete Test Procedures with Expected Results

---

## TEST 1: Hardware Connectivity Check

### Objective
Verify that all hardware components are properly connected and powered.

### Pre-requisites
- ESP32-S3 with USB cable connected to computer
- INMP441 microphone wired to ESP32-S3
- Arduino IDE installed and configured

### Procedure

1. **Check Device Manager (Windows)**
   - Right-click Start → Device Manager
   - Look for "Ports (COM & LPT)"
   - Expand and verify a new COM port appears (e.g., COM3, COM4)
   - Note the port number

2. **Check Board Recognition**
   - Open Arduino IDE
   - Tools → Board → Select "ESP32-S3 Dev Module"
   - Tools → Port → Select the COM port from step 1
   - Should not show any errors

3. **Measure Power**
   - With ESP32 powered on (USB plugged in)
   - Use multimeter: Measure VDD to GND on INMP441
   - Should read: **3.3V ± 0.1V**
   - If lower (2.5V or less): Power supply issue
   - If higher (3.5V or more): Voltage regulator issue

### Expected Results ✅

| Component | Expected Result |
|-----------|-----------------|
| COM Port | Visible in Device Manager |
| Board Selection | ESP32-S3 Dev Module selected without error |
| Power Measurement | 3.3V ± 0.1V |

### Pass/Fail Criteria

- ✅ PASS: All three checks successful
- ❌ FAIL: Any measurement incorrect or port not visible

---

## TEST 2: Microphone Audio Capture

### Objective
Verify that the microphone is capturing audio correctly from the I2S interface.

### Pre-requisites
- Hardware Connectivity Check (TEST 1) passed
- mic_test.ino sketch available

### Procedure

1. **Upload Test Firmware**
   - In Arduino IDE: File → Open → `ESP32_MIC_TEST/mic_test.ino`
   - Click Upload (Ctrl+U)
   - Wait for "Upload successful" message
   - Press ESP32 reset button if needed

2. **Open Serial Monitor**
   - Tools → Serial Monitor (Ctrl+Shift+M)
   - Verify bottom-right shows **9600** baud rate
   - You should see startup messages

3. **Perform Silence Test (10 seconds)**
   - Sit completely quiet
   - Observe Serial Monitor output for 3-4 readings
   - Record RMS values for silent environment

4. **Perform Voice Test (5 seconds)**
   - Speak "DORA" clearly into microphone
   - Observe RMS values jump
   - Record peak values

5. **Perform Noise Test (3 seconds)**
   - Clap hands sharply near microphone
   - Observe peak spike
   - Record maximum peak value

### Data Collection

Create a table to record results:

```
┌─────────────────┬──────────┬──────────┬────────────┐
│ Test Type       │ RMS      │ Peak     │ Confidence │
├─────────────────┼──────────┼──────────┼────────────┤
│ Silence (10s)   │ 45.2     │ 105      │ Low ✓      │
│ Voice: "DORA"   │ 250.8    │ 680      │ High ✓     │
│ Clap            │ 120.5    │ 1200     │ High ✓     │
└─────────────────┴──────────┴──────────┴────────────┘
```

### Expected Results ✅

| Test | Expected RMS | Expected Peak | Notes |
|------|--------------|---------------|-------|
| Silence | 30-60 | 50-100 | Low, stable values |
| Voice | 150-400 | 300-800 | Jump 3-5x from silence |
| Clap | 100-200 | 1000+ | Sharp spike visible |

### Pass/Fail Criteria

- ✅ PASS if:
  - Silence test: RMS < 100, peak < 150
  - Voice test: RMS > 150, peak > 300
  - Voice RMS > (Silence RMS × 3)
  - Clap peak > 800

- ❌ FAIL if:
  - All readings stay near 0 (microphone not working)
  - No change between silence and voice
  - Values are erratic/random
  - Serial shows only garbage text

---

## TEST 3: Model File Validation

### Objective
Verify that the trained TensorFlow Lite model exists and is valid.

### Pre-requisites
- Model training completed (or backup model available)
- Python environment set up

### Procedure

1. **Check File Existence**
   ```bash
   # PowerShell:
   Get-Item trained_models/DORA/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite
   
   # Should show file info, not error
   ```

2. **Check File Size**
   ```bash
   # Should be 200-500 KB for quantized model
   # If < 100 KB: too small (incomplete)
   # If > 1 MB: too large (unquantized or wrong model)
   ```

3. **Validate Model Structure (Python)**
   ```bash
   python
   >>> import tensorflow as tf
   >>> interpreter = tf.lite.Interpreter("trained_models/DORA/tflite_stream_state_internal_quant/stream_state_internal_quant.tflite")
   >>> interpreter.allocate_tensors()
   >>> print("Model loaded successfully!")
   >>> interpreter.get_input_details()  # Should show input tensor info
   >>> interpreter.get_output_details()  # Should show output tensor info
   ```

### Expected Results ✅

| Check | Expected Result |
|-------|-----------------|
| File Exists | File found at correct path |
| File Size | 200-500 KB |
| Model Loads | No errors in TensorFlow |
| Input Shape | [1, samples, 40, 1] (typical) |
| Output Shape | [1, num_classes] |

### Pass/Fail Criteria

- ✅ PASS: All checks successful, model loads without errors
- ❌ FAIL: File missing, wrong size, or won't load

---

## TEST 4: Dashboard Server Connectivity

### Objective
Verify that the dashboard server runs and listens on correct port.

### Pre-requisites
- Python 3.10+ installed
- Required packages installed (see requirements_server.txt)
- Dashboard directory structure intact

### Procedure

1. **Start Dashboard Server**
   ```bash
   cd dashboard
   python server.js  # or python app.py if using Flask
   ```

2. **Verify Server Started**
   - Should see message like: "Server running on http://localhost:8765"
   - Should see: "WebSocket ready at ws://localhost:8765/stream"
   - No error messages about port already in use

3. **Test Connectivity (New Terminal)**
   ```bash
   curl http://localhost:8765
   # Should return HTML or "OK", not connection refused
   ```

4. **Test WebSocket Endpoint**
   ```bash
   # Using wscat or similar:
   wscat -c ws://localhost:8765/stream
   # Should connect, not refuse connection
   ```

### Expected Results ✅

| Component | Expected Result |
|-----------|-----------------|
| Server Start | No errors, port 8765 available |
| HTTP Endpoint | Responds to GET request |
| WebSocket | Accepts connections |
| Dashboard UI | Loads without 404 errors |

### Pass/Fail Criteria

- ✅ PASS: Server starts, HTTP responds, WebSocket accepts connections
- ❌ FAIL: Port already in use, connection refused, or error messages

---

## TEST 5: ESP32 WiFi Connectivity

### Objective
Verify that ESP32 can connect to WiFi network.

### Pre-requisites
- TEST 2 (Microphone) passed
- WiFi credentials known (SSID and password)
- WiFi network broadcasts 2.4GHz (ESP32-S3 doesn't support 5GHz)

### Procedure

1. **Check WiFi Network**
   - On your computer, verify WiFi network is visible
   - Verify password is correct
   - Ensure 2.4GHz band is available (not 5GHz only)

2. **Update Firmware Configuration**
   - If using Arduino sketch, update:
   ```c
   #define WIFI_SSID "YOUR_NETWORK_NAME"
   #define WIFI_PASS "YOUR_PASSWORD"
   ```
   - Save and recompile

3. **Upload Modified Firmware**
   - Upload to ESP32 (Ctrl+U in Arduino IDE)
   - Wait for upload to complete

4. **Monitor WiFi Connection**
   - Open Serial Monitor
   - Observe startup messages:
   ```
   [WiFi] Connecting to "YOUR_NETWORK_NAME"...
   [WiFi] Connected!
   [WiFi] IP Address: 192.168.1.50
   ```

5. **Verify Connection**
   - From your computer, ping the ESP32:
   ```bash
   ping 192.168.1.50
   # Should get response: "Reply from 192.168.1.50: bytes=32 time=XX ms"
   ```

### Expected Results ✅

| Check | Expected Result |
|-------|-----------------|
| Network Visible | Yes, SSID appears in scan |
| Connection Time | < 10 seconds |
| IP Address | 192.168.x.x (not 0.0.0.0) |
| Ping Response | Responds with < 50ms latency |

### Pass/Fail Criteria

- ✅ PASS: Connects within 10 seconds, gets valid IP, responds to ping
- ❌ FAIL: Can't connect, invalid IP (0.0.0.0), timeout on ping

---

## TEST 6: ESP32 to Dashboard Connection

### Objective
Verify that ESP32 can establish WebSocket connection to dashboard server.

### Pre-requisites
- TEST 2 (Microphone) passed
- TEST 4 (Dashboard Server) passed
- TEST 5 (WiFi Connectivity) passed
- Server IP address known (from `ipconfig`)

### Procedure

1. **Find Server IP**
   ```bash
   # PowerShell:
   ipconfig
   # Look for "IPv4 Address" like: 192.168.1.100
   ```

2. **Update Firmware**
   - If using Arduino sketch, update:
   ```c
   #define SERVER_URI "ws://192.168.1.100:8765/stream"
   ```
   - Save and recompile
   - Upload to ESP32

3. **Monitor Connection**
   - Open Serial Monitor (9600 baud)
   - Should see messages like:
   ```
   [WS] Connecting to ws://192.168.1.100:8765/stream
   [WS] Connected!
   [AUDIO] Streaming audio to server...
   ```

4. **Verify Server Received Data**
   - In dashboard server terminal, should see:
   ```
   [stream] Client connected from 192.168.1.50
   [stream] Receiving audio frame: 320 samples
   [telemetry] RAM: 112 KB, CPU: 5.2%
   ```

### Expected Results ✅

| Component | Expected Result |
|-----------|-----------------|
| ESP32 Connection Message | "Connected!" visible |
| Server Log | Shows client IP connected |
| Data Flow | Server shows "Receiving audio..." |
| Connection Stable | No disconnect messages |

### Pass/Fail Criteria

- ✅ PASS: ESP32 shows "Connected!", server receives data
- ❌ FAIL: Connection refused, timeout, or "Connection failed" messages

---

## TEST 7: Keyword Detection (End-to-End)

### Objective
Verify that the keyword "DORA" is detected correctly and triggers server action.

### Pre-requisites
- All previous tests (1-6) passed
- Trained model uploaded to ESP32
- Dashboard displaying detection results

### Procedure

1. **Prepare System**
   - Dashboard server running
   - ESP32 connected and streaming
   - Serial Monitor open showing output

2. **Test 1: Positive Detection - Speak Keyword**
   - Speak clearly: **"DORA"** (pause) **"DORA"**
   - Repeat 5 times
   - Record detection response time

3. **Test 2: Negative Detection - Speak Other Words**
   - Speak: "Hello", "Hi", "Help", "Open", "Data"
   - Should NOT trigger detection
   - Monitor for false positives

4. **Test 3: Continuous Streaming**
   - Keep system running for 2 minutes
   - Speak keyword 10 times randomly
   - Monitor for drops/disconnections

5. **Measure Latency**
   - Speak keyword and note exact time
   - Observe when detection appears on dashboard
   - Calculate: latency = detection_time - speak_time

### Data Collection

```
Keyword Detection Test Results:
─────────────────────────────────
Total Keyword Utterances: 10
Successful Detections: 9
Detection Rate: 90%

False Positives (5 minutes): 1
False Positive Rate: 1 per 5 min

Average Latency: 250ms
Min Latency: 180ms
Max Latency: 380ms

System Stability: PASS (no crashes)
```

### Expected Results ✅

| Metric | Expected Value |
|--------|-----------------|
| Detection Rate | > 85% |
| False Positive Rate | < 1 per minute |
| Average Latency | 100-500ms |
| System Uptime | > 10 minutes |
| Streaming Quality | No drops |

### Pass/Fail Criteria

- ✅ PASS if:
  - Detection rate > 80%
  - False positives < 1 per 2 minutes
  - Latency < 600ms
  - System runs 5+ minutes without crash

- ❌ FAIL if:
  - Detection rate < 60%
  - False positives frequent (> 1 per minute)
  - Latency > 1000ms
  - System crashes

---

## COMPLETE TEST CHECKLIST

Use this checklist to track overall testing progress:

```
HARDWARE TESTS
[ ] TEST 1 - Hardware Connectivity Check .......................... PASS/FAIL
[ ] TEST 2 - Microphone Audio Capture ............................ PASS/FAIL
[ ] Power supply stable (3.3V measured) ........................... YES/NO

SOFTWARE TESTS
[ ] TEST 3 - Model File Validation ............................... PASS/FAIL
[ ] TEST 4 - Dashboard Server Connectivity ....................... PASS/FAIL
[ ] Model loads without errors in Python ......................... YES/NO

INTEGRATION TESTS
[ ] TEST 5 - ESP32 WiFi Connectivity ............................. PASS/FAIL
[ ] TEST 6 - ESP32 to Dashboard Connection ....................... PASS/FAIL
[ ] TEST 7 - Keyword Detection (End-to-End) ..................... PASS/FAIL

OVERALL STATUS
[ ] All tests PASSED - Ready for deployment
[ ] Some tests FAILED - Debug and retry
```

---

## TROUBLESHOOTING DURING TESTING

### Issue: Arduino IDE won't upload to ESP32

**Diagnosis:** Check COM port and board selection
```
Tools → Port: Should show "COM3 ESP32-S3 Dev Module"
If empty or shows question mark, check USB cable
```

**Solution:**
1. Disconnect USB
2. Wait 5 seconds
3. Reconnect USB
4. Tools → Port (refresh and select again)
5. Retry upload

---

### Issue: Serial Monitor shows garbage text

**Diagnosis:** Baud rate mismatch
```
Firmware uses: 9600 baud
Serial Monitor must also use: 9600 baud
```

**Solution:**
1. Close Serial Monitor
2. Click dropdown in bottom-right: select 9600
3. Reopen Serial Monitor

---

### Issue: Microphone values stay at 0

**Diagnosis:** Wiring issue or microphone not powered
```
Check:
- GPIO 4: Connected to SCK (bit clock)
- GPIO 5: Connected to WS (word select)
- GPIO 6: Connected to SD (data in)
- 3.3V: Connected to VDD
- GND: Connected to GND and L/R pin
```

**Solution:**
1. Check each wire connection
2. Use multimeter to verify continuity
3. Look for small power LED on microphone
4. Try different USB cable for more power

---

### Issue: WiFi connection fails with "Authentication Failed"

**Diagnosis:** Wrong password or WiFi credentials
```
Check:
- SSID spelled correctly (case-sensitive)
- Password entered correctly
- WiFi is 2.4GHz (not 5GHz only)
```

**Solution:**
1. Double-check WiFi SSID and password
2. Ensure 2.4GHz band is available
3. Restart WiFi router
4. Try connecting phone to same network to verify credentials

---

### Issue: WebSocket connection refused

**Diagnosis:** Server not running or wrong IP

**Solution:**
1. Verify dashboard server is running: `python server.js`
2. Find correct server IP: `ipconfig` (look for IPv4 Address)
3. Update ESP32 firmware with correct IP
4. Check Windows Firewall allows port 8765

---

## FINAL VALIDATION

Once all tests pass, perform final validation:

```
□ Microphone test: PASS
  Evidence: RMS values jump 3-5x when speaking
  
□ Model test: PASS
  Evidence: Model file ~300 KB, loads in Python
  
□ Server test: PASS
  Evidence: Dashboard accessible at localhost:8765
  
□ Connectivity test: PASS
  Evidence: ESP32 connects to WiFi and dashboard
  
□ Detection test: PASS
  Evidence: "DORA" keyword triggers 85%+ detection
  
□ Latency acceptable: PASS
  Evidence: Detection latency < 500ms average
```

**If all boxes checked:** ✅ **YOU'RE READY FOR DEPLOYMENT**

---

**Questions? Refer to troubleshooting section or review documentation in /docs folder.**
