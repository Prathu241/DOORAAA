# DORA Microphone Test Firmware

**Status:** Ready to flash  
**Target:** ESP32-S3 DevKit  
**Microphone:** INMP441 I2S Digital Microphone  
**Duration:** ~5-10 minutes to verify microphone capture

---

## Hardware Wiring

| INMP441 Pin | ESP32-S3 GPIO | Purpose |
|---|---|---|
| GND | GND | Ground |
| 3.3V | 3.3V | Power |
| L/R | GND | Mono (left channel) |
| WS | GPIO 5 | Word Select (LRCK) |
| SCK | GPIO 4 | Bit Clock (BCLK) |
| SD | GPIO 6 | Serial Data (DIN) |

**Connections:**
```
ESP32-S3        INMP441
3.3V     -----> VCC
GND      -----> GND
GPIO 4   -----> SCK (bit clock)
GPIO 5   -----> WS (word select)
GPIO 6   -----> SD (data in)
GND      -----> L/R (mono left)
```

---

## Setup Steps

### 1. Install Arduino IDE or VS Code + PlatformIO
- **Arduino IDE:** Download from arduino.cc, select ESP32-S3 board
- **OR PlatformIO:** Install in VS Code, create ESP32-S3 project

### 2. Select Board
- **Arduino IDE:** Tools → Board → ESP32-S3 Dev Module
- **PlatformIO:** platform = espressif32, board = esp32-s3-devkitc-1

### 3. Configure Serial Settings
- **Baud rate:** 9600
- **Upload speed:** 921600 (or 460800 if issues)
- **Partition scheme:** Default (or "Minimal SPIFFS")

### 4. Copy Code
Copy the entire contents of `mic_test.ino` into the Arduino IDE sketch editor.

### 5. Build & Upload
- **Arduino IDE:** Sketch → Upload (or Ctrl+U)
- **PlatformIO:** Cmd+Shift+U or click Upload button

### 6. Verify Upload
- Look for `Leaving... Hard resetting via RTS pin` message
- Device will reboot

---

## Testing

### 1. Open Serial Monitor
- **Arduino IDE:** Tools → Serial Monitor (9600 baud)
- **PlatformIO:** PlatformIO → Serial Port Monitor (9600 baud)

### 2. Expected Output
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
peak=120
min=-150
max=180
---
MIC TEST
samples=16000
rms=42.1
peak=110
min=-160
max=175
---
```

### 3. Test Procedure
1. **Silent test (10 sec):**
   - Hold quiet
   - RMS, peak, min, max should be very small (< 50)
   - All values near 0

2. **Speak test (5 sec):**
   - Speak "DORA" clearly into microphone
   - RMS should jump to 100-300+
   - Peak should be > 500
   - Values should clearly change

3. **Clap test (3 sec):**
   - Clap loudly near microphone
   - Peak should spike to 1000-2000+
   - RMS should jump

4. **Background noise (5 sec):**
   - Play quiet music or fan noise
   - RMS should be 50-200
   - Consistent readings

---

## Success Criteria

**MIC PASS:**
- ✓ Serial output prints every 500ms without errors
- ✓ Silent values: rms < 50, peak < 100
- ✓ Speaking "DORA": rms > 100, peak > 500
- ✓ Values clearly change with different sounds
- ✓ No crashes or error messages

**MIC FAIL:**
- ✗ No serial output
- ✗ Only zeros printed (1000s of 0 values)
- ✗ High static noise (peak > 500 during silence)
- ✗ I2S driver errors

---

## Troubleshooting

### Issue: No Serial Output
**Solution:**
- Check USB cable connection
- Verify board selected correctly in IDE
- Try different COM port
- Check UART drivers (CH340 or CP2104)

### Issue: Only Zeros in Output
**Solution:**
- Check I2S GPIO wiring (especially GPIO 4, 5, 6)
- Verify INMP441 pin connections
- Check 3.3V and GND connections
- INMP441 might need 50ms power-up time

### Issue: High Noise (peak > 500 at silence)
**Solution:**
- Check for loose wiring
- Add 0.1 µF capacitor near INMP441 power pin
- Verify GPIO 4/5/6 are not interfering with other devices
- Try ferrite bead on SCK line

### Issue: Compil Error "I2S not found"
**Solution:**
- Ensure esp-idf toolchain is installed
- Re-select ESP32-S3 board (not generic ESP32)
- In PlatformIO, update platform: `pio pkg update`

---

## Next Steps (After MIC PASS)

Once microphone test confirms capture is working:

1. **Integrate micro_speech frontend**
   - Apply 40-feature mel-spectrogram
   - Test spectrogram output

2. **Load Streaming MixedNet model**
   - Use generated DORA_model_data.cc
   - Test inference on live audio

3. **Add VAD (Voice Activity Detection)**
   - Optional pre-filter to reduce false triggers

4. **Implement streaming classifier**
   - Feed spectrograms to model
   - Apply 5-frame averaging
   - Generate detection events

---

## Hardware Notes

### INMP441 Specifications
- **Sample Rate:** 8 kHz – 104 kHz (we use 16 kHz)
- **Bit Depth:** 24-bit resolution
- **I2S Packing:** 24-bit audio in 32-bit frames
- **Power:** 3.0V – 3.6V (use 3.3V from ESP32)
- **Current:** ~1.3 mA during operation
- **Signal-to-Noise Ratio:** 61 dB

### ESP32-S3 I2S Specifications
- **Max Sample Rate:** 160 kHz
- **Max Channels:** 2 (stereo)
- **DMA Buffers:** Configurable
- **Clock Source:** Internal or external

---

## Reference

- ESP32-S3 I2S Driver: https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/i2s.html
- INMP441 Datasheet: INVENSENSE (24-bit digital output PDM to I2S)
- Arduino ESP32 Docs: https://github.com/espressif/arduino-esp32

---

**Test Status:** Ready  
**Last Updated:** 8 September 2026  
**Maintainer:** DORA Hackathon Team
