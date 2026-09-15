"""
Identify which tensors carry ring-buffer state between invokes.
Writes output to state_check_output.txt to avoid PowerShell stderr issues.
"""
import sys
import tensorflow as tf
import numpy as np
import librosa
from microwakeword.audio.audio_utils import generate_features_for_clip

out_file = open('state_check_output.txt', 'w')

def log(msg=''):
    out_file.write(msg + '\n')
    out_file.flush()

MODEL_PATH = 'trained_models/DORA/dora_model_int8.tflite'
with open(MODEL_PATH, 'rb') as f:
    model_bytes = f.read()

interp = tf.lite.Interpreter(model_content=model_bytes)
interp.allocate_tensors()
inp_idx = interp.get_input_details()[0]['index']
out_idx = interp.get_output_details()[0]['index']
all_t   = interp.get_tensor_details()
name_map  = {t['index']: t['name']  for t in all_t}
shape_map = {t['index']: t['shape'] for t in all_t}
dtype_map = {t['index']: t['dtype'] for t in all_t}

# Known state (ring buffer) input tensors
STATE_IN = [(51,[1,22,1,64]), (52,[1,16,1,64]), (53,[1,2,1,40]),
            (57,[1,4,1,32]),  (62,[1,10,1,64]), (67,[1,14,1,64])]

# Zero all states
for idx, shape in STATE_IN:
    interp.set_tensor(idx, np.zeros(shape, dtype=np.float32))

# Load a DORA clip
audio, _ = librosa.load('dataset/split/test/DORA/dora_spk_raw_dhora.wav', sr=16000, mono=True)
audio_int16 = np.clip(audio * 32768, -32768, 32767).astype(np.int16)
feats = generate_features_for_clip(audio_int16, step_ms=10)
log(f"Feature shape: {feats.shape}")

# Snapshot all tensors before invoke
def snapshot():
    snap = {}
    for t in all_t:
        try:
            snap[t['index']] = interp.get_tensor(t['index']).copy()
        except Exception:
            snap[t['index']] = None
    return snap

before = snapshot()
chunk = feats[0:3].reshape(1, 3, 40).astype(np.float32)
interp.set_tensor(inp_idx, chunk)
interp.invoke()
after = snapshot()

log("Tensors that changed after first invoke (shape < 300 elements):")
changed = []
for idx in before:
    b, a = before[idx], after[idx]
    if b is None or a is None:
        continue
    try:
        if not np.allclose(b, a, atol=1e-6):
            sh = shape_map[idx]
            if len(sh) > 0 and max(sh) < 300:
                changed.append(idx)
                log(f"  idx={idx:3d}  shape={str(sh):20s}  {name_map[idx]}")
    except Exception:
        pass

log()
log("State input tensors after invoke (checking if they updated):")
for idx, shape in STATE_IN:
    val = interp.get_tensor(idx)
    b   = before[idx]
    changed_flag = not np.allclose(b, val, atol=1e-6) if b is not None else 'unknown'
    log(f"  idx={idx}  shape={shape}  sum_after={val.sum():.4f}  changed={changed_flag}")

# Now run 5 frames sequentially with state explicitly managed
# Strategy: after each invoke, read back the ring-buffer tensors
# and re-set them before next invoke
log()
log("Running 5 sequential frames with manual state management:")
for idx, shape in STATE_IN:
    interp.set_tensor(idx, np.zeros(shape, dtype=np.float32))

frame_scores = []
for i in range(5):
    chunk = feats[i:i+3].reshape(1, 3, 40).astype(np.float32)
    interp.set_tensor(inp_idx, chunk)
    interp.invoke()
    score = float(interp.get_tensor(out_idx).flat[0])
    # Read back current state for logging
    s53 = interp.get_tensor(53).sum()
    frame_scores.append(score)
    log(f"  frame {i}: score={score:.4f}  state53_sum={s53:.3f}")

log()
log("Running same 5 frames with FRESH interpreter each time (reference):")
for i in range(5):
    i2 = tf.lite.Interpreter(model_content=model_bytes)
    i2.allocate_tensors()
    chunk = feats[i:i+3].reshape(1, 3, 40).astype(np.float32)
    i2.set_tensor(i2.get_input_details()[0]['index'], chunk)
    i2.invoke()
    score = float(i2.get_tensor(i2.get_output_details()[0]['index']).flat[0])
    log(f"  frame {i}: score={score:.4f}")

out_file.close()
print("Done. See state_check_output.txt")
