# NEXT STEPS: Microphone → KWS Pipeline

**Current Status:** Microphone test created  
**Next Gate:** MIC PASS (microphone capture verified)  
**Goal:** Connect I2S capture → micro_speech frontend → Streaming MixedNet inference → Detection

---

## Timeline (After MIC PASS)

| Step | Duration | Dependency |
|---|---|---|
| 1. Integrate micro_speech | 15 min | MIC PASS |
| 2. Load DORA model | 10 min | Training complete |
| 3. Implement streaming KWS | 20 min | Steps 1 + 2 |
| 4. Test on device | 10 min | Steps 1-3 |
| **Total** | **~1 hour** | Training + MIC PASS |

---

## Step 1: Integrate micro_speech Frontend (15 min)

**Goal:** Convert PCM16 audio → 40-feature mel-spectrogram (micro_speech format)

### Files to Extract
From microWakeWord training environment:
```
microWakeWord/
  ├── microwakeword/audio/audio_utils.py
  ├── microwakeword/audio/spectrograms.py
  └── microwakeword/model/kws_model.py
```

Extract C-compatible versions (already in microWakeWord source):
```
microWakeWord/
  ├── tensorflow/lite/micro/examples/micro_speech/
  │   ├── micro_features_micro_model_settings.h
  │   ├── micro_features_micro_model_settings.cc
  │   └── micro_features_generator.cc  ← REUSE THIS
```

### Integration Code (Pseudo)
```c
#include "micro_features_generator.h"

// After I2S capture → PCM16
int16_t pcm_buffer[16000]; // 1 second @ 16 kHz

// Generate 40-feature spectrogram
int8_t spectrogram[1][49][40]; // 1 frame, 49 time steps, 40 mels

generate_micro_features(pcm_buffer, spectrogram);
```

### What Happens
1. **30 ms window** of PCM16 samples (480 samples @ 16 kHz)
2. Apply **FFT** (1024-point)
3. Map to **40 mel-frequency bins**
4. Output: **1×40 feature vector**

### Streaming Characteristic
- **Overlap:** 10 ms stride → new spectrogram every 10 ms
- **Ring buffer:** Maintain 30 ms history
- **Output:** Continuous 40-feature stream

---

## Step 2: Load DORA Streaming MixedNet Model (10 min)

**Goal:** Embed trained quantized TFLite model into firmware

### File Dependencies
Waiting for training to complete:
```
trained_models/DORA/
  └── tflite_stream_state_internal_quant/
      └── stream_state_internal_quant.tflite
```

### Convert to C Header
```bash
xxd -i stream_state_internal_quant.tflite > DORA_model_data.cc
```

Creates:
```c
unsigned char stream_state_internal_quant_tflite[] = {
    0x54, 0x46, 0x4c, 0x33,  // TFLite header
    // ... 30-80 KB of model bytes ...
};
unsigned int stream_state_internal_quant_tflite_len = 65536;
```

### Integration Code (Pseudo)
```c
#include "DORA_model_data.h"
#include "tensorflow/lite/micro/micro_interpreter.h"

// Initialize model
tflite::MicroInterpreter interpreter(
    model_data, 
    micro_op_resolver,
    tensor_arena, 
    kArenaSize
);

// Input tensor pointer
int8_t* model_input = interpreter.input(0)->data.int8;

// Output tensor pointer
int8_t* model_output = interpreter.output(0)->data.int8;
```

### Tensor Layout (Streaming MixedNet)
- **Input:** 1×49×40×1 (batch, time, features, channels)
- **Output:** 1×2 (prob not keyword, prob keyword)
- **Quantization:** int8 (±127 range)
- **Latency:** ~2-5 ms inference per frame

---

## Step 3: Implement Streaming KWS Loop (20 min)

**Goal:** Continuous real-time keyword detection

### Algorithm
```
Loop every 10 ms:
  1. Capture 160 PCM16 samples (10 ms @ 16 kHz)
  2. Add to 30 ms ring buffer
  3. Generate new 40-feature vector
  4. Shift existing spectrogram (49 frames) left by 1
  5. Append new feature vector
  6. Run model inference
  7. Extract confidence score (output[1])
  8. Apply 5-frame smoothing window
  9. Check threshold
  10. If > threshold → DORA DETECTED
```

### Pseudo Code
```c
// Ring buffer for 30 ms audio (480 samples)
int16_t audio_ring_buffer[480];
uint16_t buffer_idx = 0;

// Spectrogram buffer (streaming)
int8_t spectrogram[49][40];  // 49 time steps, 40 features
float confidence_history[5]; // 5-frame sliding window
uint8_t history_idx = 0;

// Detection threshold
const float THRESHOLD = 0.7;
const uint32_t DEBOUNCE_MS = 500; // Prevent rapid re-triggers
uint32_t last_detection_time = 0;

void kws_loop() {
    // 1. Capture 10 ms audio (160 samples)
    while (i2s_samples_available() < 160) {
        delay(1);
    }
    i2s_read_samples(audio_ring_buffer[buffer_idx], 160);
    buffer_idx = (buffer_idx + 160) % 480;
    
    // 2. Generate spectrogram
    int8_t new_feature[40];
    generate_micro_features_streaming(audio_ring_buffer, new_feature);
    
    // 3. Shift spectrogram left, append new feature
    memmove(spectrogram, spectrogram + 1, 48 * 40 * sizeof(int8_t));
    memcpy(spectrogram[48], new_feature, 40 * sizeof(int8_t));
    
    // 4. Run model inference
    memcpy(model_input, spectrogram, 49 * 40 * sizeof(int8_t));
    interpreter.Invoke();
    
    // 5. Extract confidence (dequantize if needed)
    uint8_t keyword_logit = (uint8_t)model_output[1];
    float confidence = (keyword_logit / 128.0);  // Scale to [0, 1]
    
    // 6. Apply 5-frame smoothing
    confidence_history[history_idx] = confidence;
    history_idx = (history_idx + 1) % 5;
    
    float smoothed_confidence = 0;
    for (int i = 0; i < 5; i++) {
        smoothed_confidence += confidence_history[i];
    }
    smoothed_confidence /= 5.0;
    
    // 7. Check threshold with debounce
    if (smoothed_confidence > THRESHOLD) {
        uint32_t now = millis();
        if (now - last_detection_time > DEBOUNCE_MS) {
            Serial.printf("DORA DETECTED (confidence=%.2f)\n", smoothed_confidence);
            last_detection_time = now;
            // Trigger Tier 2: Start WebSocket, send pre-roll, etc.
        }
    }
}
```

### Model Quantization Details
- **Input quantization:** int8 (range -127 to 127)
  - Pre-training quantization aware training ensures scale known
  - Spectrogram features: typically -50 to +50 in feature space
  - Scale: ~1 feature unit = ~2-3 int8 units
  
- **Output quantization:** int8 (logit space)
  - Dequantize: `probability = (logit + 128) / 256` (rough, depends on training)
  - More accurate: Use TFLite interpreter's quantization params

### Threshold Tuning
- **Start:** 0.7 (70% confidence)
- **If too many false positives:** Increase to 0.8 or 0.85
- **If missing detections:** Decrease to 0.6 or 0.5
- **Typical range:** 0.65–0.80

---

## Step 4: Test on Device (10 min)

### Test Procedure
1. **Flash firmware** to ESP32-S3
2. **Open serial monitor** (115200 baud)
3. **Run tests:**
   - **Quiet (5 sec):** No detection
   - **Speak "DORA" (5 sec):** Detection with confidence ~0.85-0.95
   - **Other words (5 sec):** No detection
   - **Silence (30 sec):** No false positives

### Expected Serial Output
```
[INIT] I2S initialized
[INIT] Streaming MixedNet model loaded (65 KB)
[INIT] Tensor arena: 256 KB allocated
[RUN] Listening...

[AUDIO] RMS=120 peak=500
[KWS] confidence=0.42 (speaker detected)

[AUDIO] RMS=180 peak=800
[KWS] confidence=0.91 (STRONG keyword signal)

*** DORA DETECTED (confidence=0.92) ***
[ACTION] Trigger pre-roll buffer

[AUDIO] RMS=50 peak=100
[KWS] confidence=0.15 (quiet word, rejected)
```

### Success Criteria
- ✓ Detects "DORA" reliably (3/3 test speaks)
- ✓ Rejects other words (0 false positives on "HELLO", "WORLD", etc.)
- ✓ Rejects silence (0 false positives in 30 sec quiet)
- ✓ Latency < 10 ms per 10 ms audio frame
- ✓ No crashes, stable operation > 5 minutes

---

## Hardware Memory Budget

Assuming ESP32-S3 with 512 KB SRAM:

```
Tensor Arena (TFLite):    256 KB
Audio Ring Buffer:        1 KB (480 samples × 2 bytes)
Spectrogram Buffer:       2 KB (49×40×1 byte)
Confidence History:       0.1 KB
Model Data (FLASH):       ~70 KB (quantized int8 TFLite)
I2S DMA Buffers:          64 KB (driver internal)
FreeRTOS + Drivers:       ~100 KB
----
Total SRAM used:          ~423 KB (safe < 512 KB)
Total FLASH used:         ~250 KB (safe < 2 MB)
```

---

## Integration Checklist

- [ ] Extract micro_speech frontend from microWakeWord
- [ ] Compile TFLite Micro dependency
- [ ] Wait for DORA training to complete
- [ ] Convert quantized model to C header (xxd)
- [ ] Create streaming spectrogram buffer logic
- [ ] Implement model inference loop
- [ ] Add 5-frame confidence smoothing
- [ ] Test on ESP32-S3 with live "DORA" speech
- [ ] Measure latency and memory usage
- [ ] Document threshold settings

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Training delayed | Proceed with placeholder model or dummy inference |
| Model too large | Quantize further or prune (if time permits) |
| Latency > 10 ms | Reduce spectrogram resolution or DMA buffer size |
| Memory overflow | Reduce tensor arena or confidence history depth |
| False positives high | Increase threshold or add VAD pre-filter |
| False negatives high | Lower threshold or improve audio preprocessing |

---

## Reference Implementation

Complete example will be provided in:
```
ESP32_MIC_TEST/
  ├── mic_test.ino (current: audio capture only)
  ├── kws_streaming.ino (full KWS pipeline - to be added)
  └── DORA_model_data.cc (generated from training)
```

---

**Status:** Waiting for MIC PASS  
**Next Gate:** Training completion + microphone validation  
**Estimated Completion:** ~1 hour after both gates pass
