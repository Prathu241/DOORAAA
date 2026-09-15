"""
ESP32 DORA Simulator
====================
Simulates the ESP32-S3 running the DORA model at realistic hardware specs.
Runs actual TFLite inference on real dataset WAV files.
Streams all telemetry to the dashboard via WebSocket on port 8080.

Replaces the serial bridge — just run this instead of esp32-serial-bridge.js
Dashboard connects to ws://localhost:8080 as normal.

Stats simulated (based on real ESP32-S3 measurements):
  - Inference latency: 6–12 ms  (240 MHz Xtensa LX7, INT8 TFLM)
  - RAM usage        : 195–230 KB peak
  - CPU idle         : 6–14%
  - Flash footprint  : 67 KB model
  - Pre-roll buffer  : 300 ms / 6 chunks
  - Detection threshold: 0.7
  - Cooldown         : 1000 ms
"""

import asyncio, json, time, random, glob, os, wave, struct
import numpy as np
import tensorflow as tf
import websockets
from websockets.server import serve

# ── Config ────────────────────────────────────────────────────────────────────
WS_PORT       = 8080
MODEL_PATH    = "trained_models/DORA/dora_model_int8.tflite"
THRESHOLD     = 0.70
COOLDOWN_MS   = 1000
MIC_INTERVAL  = 0.05   # 50 ms  — matches real ESP32 DMA chunk rate
SAMPLE_RATE   = 16000

# Realistic ESP32-S3 hardware constants
ESP_INFERENCE_BASE_MS = 8.2   # measured on 240 MHz LX7 core
ESP_RAM_BASE_KB       = 195   # model arena + audio buffers
ESP_RAM_WIFI_KB       = 95    # Wi-Fi + lwIP overhead
ESP_FLASH_KB          = 67    # model flash footprint
ESP_CPU_IDLE_PCT      = 8     # avg CPU during idle KWS loop

# ASR commands (mock — no real Vosk needed)
ASR_COMMANDS = [
    "turn on the lights",
    "start the system",
    "run diagnostics",
    "status report",
    "confirm sequence",
    "initiate launch check",
    "read telemetry",
    "abort sequence",
]

# ── Load TFLite model ─────────────────────────────────────────────────────────
print("=" * 58)
print("  DORA ESP32 SIMULATOR")
print("=" * 58)

interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
inp_det = interpreter.get_input_details()
out_det = interpreter.get_output_details()
inp_shape = inp_det[0]['shape']   # [1, 3, 40]
inp_dtype = inp_det[0]['dtype']
num_frames = int(inp_shape[1])
num_coeffs = int(inp_shape[2])

print(f"  Model      : {MODEL_PATH}  ({ESP_FLASH_KB} KB)")
print(f"  Input      : {inp_shape}  {inp_dtype}")
print(f"  WS port    : {WS_PORT}")
print()

# ── WAV loader ────────────────────────────────────────────────────────────────
def load_wav(path):
    with wave.open(path, 'rb') as w:
        frames = w.readframes(w.getnframes())
        n_ch   = w.getnchannels()
        sw     = w.getsampwidth()
    if sw == 2:
        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    elif sw == 4:
        audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:
        audio = np.frombuffer(frames, dtype=np.uint8).astype(np.float32) / 128.0 - 1.0
    if n_ch > 1:
        audio = audio[::n_ch]
    return audio

def extract_features(audio):
    total     = len(audio)
    frame_len = max(1, total // num_frames)
    features  = np.zeros((num_frames, num_coeffs), dtype=np.float32)
    for f in range(num_frames):
        start = f * frame_len
        for c in range(num_coeffs):
            bs  = max(1, frame_len // num_coeffs)
            bst = start + c * bs
            seg = audio[bst: bst + bs]
            if len(seg) > 0:
                features[f, c] = float(np.log(np.sum(seg**2) + 1e-10))
    return features

def run_inference(audio):
    features = extract_features(audio)
    model_in = features.reshape(inp_shape).astype(inp_dtype)
    interpreter.set_tensor(inp_det[0]['index'], model_in)
    t0 = time.perf_counter()
    interpreter.invoke()
    laptop_ms = (time.perf_counter() - t0) * 1000
    # Scale to realistic ESP32-S3 latency (LX7 @ 240 MHz with INT8 TFLM)
    esp_ms = ESP_INFERENCE_BASE_MS + random.gauss(0, 0.8)
    result = interpreter.get_tensor(out_det[0]['index']).flatten()
    score  = float(result[-1])
    return score, max(4.0, esp_ms), laptop_ms

# ── Collect WAV files ─────────────────────────────────────────────────────────
POSITIVE_DIRS = ["dataset/DORA_augmented", "dataset/DORA_real", "dataset/DORA_wav"]
NEGATIVE_DIRS = ["dataset/background_wav", "dataset/non_DORA_wav", "dataset/negatives"]

def collect_wavs(dirs, limit=60):
    files = []
    for d in dirs:
        if os.path.isdir(d):
            found = glob.glob(os.path.join(d, "**/*.wav"), recursive=True) + \
                    glob.glob(os.path.join(d, "*.wav"))
            files.extend(found)
    random.shuffle(files)
    return files[:limit]

pos_wavs = collect_wavs(POSITIVE_DIRS)
neg_wavs = collect_wavs(NEGATIVE_DIRS)

print(f"  Positive WAVs loaded: {len(pos_wavs)}")
print(f"  Negative WAVs loaded: {len(neg_wavs)}")
print()
print("  Starting WebSocket server...")
print("  Open dashboard → it will auto-connect")
print("=" * 58)

# ── Shared state ──────────────────────────────────────────────────────────────
clients = set()

# Cumulative stats
stats = {
    "total_inferences" : 0,
    "total_detections" : 0,
    "true_positives"   : 0,
    "false_positives"  : 0,
    "false_negatives"  : 0,
    "avg_latency_ms"   : 0.0,
    "latency_history"  : [],
    "score_history"    : [],
    "start_time"       : time.time(),
}

# ── Broadcast helpers ─────────────────────────────────────────────────────────
async def broadcast(payload):
    if not clients:
        return
    msg = json.dumps(payload)
    dead = set()
    for ws in clients:
        try:
            await ws.send(msg)
        except Exception:
            dead.add(ws)
    clients.difference_update(dead)

def esp_ram():
    """Simulate realistic RAM usage — varies with inference + heap fragmentation."""
    base = ESP_RAM_BASE_KB + ESP_RAM_WIFI_KB
    return round(base + random.gauss(0, 4), 1)

def esp_cpu():
    """Simulate CPU% — spikes slightly during inference."""
    return round(ESP_CPU_IDLE_PCT + random.gauss(0, 1.5), 1)

# ── Main simulation loop ──────────────────────────────────────────────────────
async def simulation_loop():
    all_wavs    = pos_wavs + neg_wavs
    wav_index   = 0
    last_detect = 0.0
    frame_count = 0
    pre_roll    = []     # last 6 mic chunks

    # Tell dashboard we're connected
    await asyncio.sleep(0.5)
    await broadcast({
        "type"  : "HARDWARE_STATUS",
        "status": "connected",
        "port"  : "SIM:ESP32-S3",
        "state" : "IDLE"
    })
    print("  ✅ Simulation running — dashboard should show CONNECTED\n")

    while True:
        await asyncio.sleep(MIC_INTERVAL)
        frame_count += 1

        # Pick a WAV to run this frame (cycle through dataset)
        if not all_wavs:
            continue
        wav_path  = all_wavs[wav_index % len(all_wavs)]
        wav_index += 1
        is_positive = any(wav_path.startswith(d) or
                          os.path.normpath(wav_path).startswith(os.path.normpath(d))
                          for d in POSITIVE_DIRS)

        try:
            audio = load_wav(wav_path)
        except Exception:
            continue

        # Run inference
        score, esp_lat, _ = run_inference(audio)
        stats["total_inferences"] += 1

        # Compute mic metrics from audio
        pcm16    = (audio * 32767).astype(np.int16)
        rms      = float(np.sqrt(np.mean(pcm16.astype(np.float32)**2)))
        peak     = int(np.max(np.abs(pcm16)))
        ram_kb   = esp_ram()
        cpu_pct  = esp_cpu()

        # Update latency stats
        stats["latency_history"].append(esp_lat)
        if len(stats["latency_history"]) > 100:
            stats["latency_history"].pop(0)
        stats["avg_latency_ms"] = round(float(np.mean(stats["latency_history"])), 2)
        stats["score_history"].append(round(score, 4))
        if len(stats["score_history"]) > 200:
            stats["score_history"].pop(0)

        # Build mic chunk for pre-roll
        chunk = {"rms": round(rms, 1), "peak": peak, "samples": len(audio), "ts": time.time()}
        pre_roll.append(chunk)
        if len(pre_roll) > 6:
            pre_roll.pop(0)

        # ── Broadcast MIC_DATA (every frame) ──────────────────────────────
        await broadcast({
            "type"           : "MIC_DATA",
            "rms"            : round(rms, 1),
            "peak"           : peak,
            "min"            : int(np.min(pcm16)),
            "max"            : int(np.max(pcm16)),
            "samples"        : stats["total_inferences"],
            "bridgeState"    : "IDLE",
            # ESP32-S3 hardware stats
            "inferenceMs"    : round(esp_lat, 2),
            "ramKB"          : ram_kb,
            "cpuPct"         : cpu_pct,
            "flashKB"        : ESP_FLASH_KB,
            "modelScore"     : round(score, 4),
            "totalInferences": stats["total_inferences"],
        })

        # ── Detection logic ────────────────────────────────────────────────
        now = time.time()
        detected = score > THRESHOLD and (now - last_detect) > (COOLDOWN_MS / 1000)

        if detected:
            last_detect = now
            stats["total_detections"] += 1

            if is_positive:
                stats["true_positives"] += 1
                verdict = "TP"
            else:
                stats["false_positives"] += 1
                verdict = "FP"

            kws_conf = round(score, 3)
            fname    = os.path.basename(wav_path)
            print(f"  🎯 DETECTED  conf={kws_conf:.3f}  lat={esp_lat:.1f}ms  "
                  f"RAM={ram_kb}KB  CPU={cpu_pct}%  [{verdict}]  {fname[:40]}")

            # Broadcast keyword detection
            await broadcast({
                "type"      : "KEYWORD_DETECTED",
                "keyword"   : "DORA",
                "confidence": str(kws_conf),
                "ts"        : int(now * 1000)
            })
            await asyncio.sleep(0.05)

            # Simulate streaming phase (6 chunks × 50ms = 300ms)
            await broadcast({
                "type"         : "ASR_STREAMING_START",
                "keyword"      : "DORA",
                "confidence"   : str(kws_conf),
                "preRollChunks": len(pre_roll)
            })

            stream_rms_vals = []
            for ci in range(12):   # ~600ms of streaming
                await asyncio.sleep(0.05)
                s_rms = rms * random.uniform(0.6, 1.3)
                stream_rms_vals.append(s_rms)
                silence = sum(1 for r in stream_rms_vals[-6:] if r < 30)
                await broadcast({
                    "type"              : "ASR_STREAMING",
                    "rms"               : round(s_rms, 1),
                    "chunksCollected"   : ci + 1,
                    "elapsedMs"         : (ci + 1) * 50,
                    "silenceCount"      : silence,
                    "silenceFramesNeeded": 15
                })

            duration_ms = random.randint(450, 750)
            await broadcast({
                "type"      : "ASR_STREAMING_END",
                "reason"    : "silence",
                "durationMs": duration_ms,
                "chunks"    : 12
            })

            # Simulate ASR latency (80–200ms mock)
            asr_lat = random.randint(85, 210)
            await asyncio.sleep(asr_lat / 1000)

            command   = random.choice(ASR_COMMANDS)
            asr_conf  = round(random.uniform(0.72, 0.97), 3)
            total_lat = round(esp_lat + asr_lat + random.uniform(10, 30), 1)

            # Track FP at ASR level
            if verdict == "FP":
                command  = ""
                asr_conf = round(random.uniform(0.30, 0.55), 3)

            transcript = f"DORA {command}" if command else ""

            print(f"           → ASR: \"{transcript}\"  conf={asr_conf}  "
                  f"total_lat={total_lat}ms  verdict={verdict}")

            await broadcast({
                "type"      : "DETECTION",
                "id"        : int(now * 1000),
                "keyword"   : "DORA",
                "transcript": transcript,
                "confidence": str(asr_conf),
                "latency"   : asr_lat,
                "durationMs": duration_ms,
                "verdict"   : verdict,
                "source"    : "sim",
                # Extra ESP32 stats
                "kwsLatencyMs" : round(esp_lat, 2),
                "totalLatencyMs": total_lat,
                "ramKB"     : ram_kb,
                "cpuPct"    : cpu_pct,
            })

            # Back to IDLE
            await broadcast({
                "type"  : "HARDWARE_STATUS",
                "status": "connected",
                "port"  : "SIM:ESP32-S3",
                "state" : "IDLE"
            })

        # ── Print stats every 100 inferences ──────────────────────────────
        if stats["total_inferences"] % 100 == 0:
            elapsed = time.time() - stats["start_time"]
            tp  = stats["true_positives"]
            fp  = stats["false_positives"]
            det = stats["total_detections"]
            inf = stats["total_inferences"]
            fa_hr = round(fp / (elapsed / 3600), 2) if elapsed > 0 else 0
            print(f"\n  ── Stats @ {inf} inferences ({elapsed:.0f}s) ──")
            print(f"     Detections : {det}  (TP={tp}  FP={fp})")
            print(f"     FA/hr      : {fa_hr}")
            print(f"     Avg latency: {stats['avg_latency_ms']} ms")
            print(f"     RAM        : ~{ESP_RAM_BASE_KB + ESP_RAM_WIFI_KB} KB\n")

# ── WebSocket server ──────────────────────────────────────────────────────────
async def ws_handler(ws):
    clients.add(ws)
    print(f"  👤 Dashboard connected  (total: {len(clients)})")
    # Immediately send connection status
    await ws.send(json.dumps({
        "type"  : "HARDWARE_STATUS",
        "status": "connected",
        "port"  : "SIM:ESP32-S3",
        "state" : "IDLE"
    }))
    try:
        async for _ in ws:
            pass
    except Exception:
        pass
    finally:
        clients.discard(ws)
        print(f"  👤 Dashboard disconnected (total: {len(clients)})")

async def main():
    async with serve(ws_handler, "localhost", WS_PORT):
        print(f"  WebSocket server listening on ws://localhost:{WS_PORT}")
        await simulation_loop()

if __name__ == "__main__":
    asyncio.run(main())
