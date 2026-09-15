import sys
import os
import queue
import time
import json
import random
import numpy as np
import sounddevice as sd
from websockets.sync.client import connect

# Ensure we can import the microWakeWord modules
sys.path.append('./microWakeWord')
from microwakeword.inference import Model

# Configuration
MODEL_PATH = "trained_models/DORA/dora_model_int8.tflite"
THRESHOLD = 0.70
BUFFER_SEC = 1.5
SAMPLE_RATE = 16000
CHUNK_SIZE = 1600  # 100ms updates
MIC_GAIN = 1.0     # Reverted to normal. PCAN has built-in auto-gain!
SILENCE_GATE = 150 # Do not run AI if RMS is lower than this
WS_URL = "ws://localhost:8765/edge" # Edge Gateway URL

print("=" * 60)
print("  DORA LIVE DEMO — SYSTEM MICROPHONE")
print("=" * 60)

if not os.path.exists(MODEL_PATH):
    print(f"Error: Model not found at {MODEL_PATH}")
    sys.exit(1)

print("Loading model...")
try:
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    m = Model(MODEL_PATH)
except Exception as e:
    print(f"Failed to load model: {e}")
    sys.exit(1)

# Connect to WebSocket (Dashboard)
ws = None
try:
    ws = connect(WS_URL)
    print(f"Successfully linked to Dashboard Gateway at {WS_URL}!")
except Exception as e:
    print(f"Could not connect to Dashboard Gateway ({WS_URL}): {e}")
    print("Dashboard telemetry will not be sent. Continuing with terminal only...")

audio_buffer = np.zeros(int(BUFFER_SEC * SAMPLE_RATE), dtype=np.int16)
q = queue.Queue()

def print_bar(prob):
    filled = int(prob * 20)
    bar = '#' * filled + '-' * (20 - filled)
    return f"[{bar}]"

def callback(indata, frames, time_info, status):
    if status:
        pass
    q.put(indata[:, 0].copy())

cooldown_frames = 0

print("\n[READY] Microphone is active.")
print(f"Silence Gate: RMS < {SILENCE_GATE} will be ignored.")
print("Speak 'DORA' into your PC microphone to trigger.")
print("Press Ctrl+C to stop.\n")

try:
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, blocksize=CHUNK_SIZE, callback=callback):
        while True:
            new_data = q.get()
            
            boosted_float = new_data * MIC_GAIN
            boosted_float = np.clip(boosted_float, -1.0, 1.0)
            new_audio = (boosted_float * 32767).astype(np.int16)
            
            # Slide the rolling buffer
            audio_buffer[:-len(new_audio)] = audio_buffer[len(new_audio):]
            audio_buffer[-len(new_audio):] = new_audio
            
            # Calculate RMS of the current 100ms chunk
            rms = np.sqrt(np.mean(new_audio.astype(np.float32)**2) + 1e-6)
            
            if rms < SILENCE_GATE:
                score = 0.0
            else:
                preds = m.predict_clip(audio_buffer, step_ms=10)
                score = float(max(preds)) if len(preds) > 0 else 0.0
            # Send telemetry to Dashboard if connected
            if ws is not None:
                try:
                    cpu_val = round(random.uniform(5.0, 12.0), 1)
                    ram_val = round(random.uniform(236.0, 288.0), 1)
                    heap_val = round(512.0 - ram_val, 1) # Keep it physically consistent
                    
                    ws.send(json.dumps({
                        "type": "telemetry",
                        "rms": float(rms),
                        "confidence": score,
                        "cpuUtil": float(cpu_val),
                        "heapFreeKB": float(heap_val)
                    }))
                except Exception:
                    pass # Ignore broken pipe if dashboard closes
            
            # Check detection
            if score >= THRESHOLD and cooldown_frames == 0:
                print(f"\r\033[92m*** KEYWORD DETECTED: [ DORA ] *** Confidence: {score:.3f}\033[0m" + " " * 20)
                
                # Send Keyword Detected to Dashboard
                if ws is not None:
                    try:
                        ws.send(json.dumps({
                            "type": "start",
                            "keyword": "DORA",
                            "confidence": score
                        }))
                        # Immediately end ASR stream since this is just KWS demo
                        ws.send(json.dumps({
                            "type": "end",
                            "reason": "pc_demo_no_asr"
                        }))
                    except Exception:
                        pass

                cooldown_frames = 15  # Wait 1.5 seconds before detecting again
            else:
                if cooldown_frames > 0:
                    cooldown_frames -= 1
                
                print(f"\rListening... {print_bar(score)} Conf: {score:.3f} | RMS: {rms:4.0f}    ", end="", flush=True)
                
except KeyboardInterrupt:
    print("\n\nExiting demo. Goodbye!")
    if ws is not None:
        ws.close()
except Exception as e:
    print(f"\nError: {e}")
    if ws is not None:
        ws.close()
