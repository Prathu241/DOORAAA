"""
Identifies which tensors in the streaming TFLite model change after each invoke,
so we know which ones carry ring-buffer state between calls.
"""
import tensorflow as tf
import numpy as np
import librosa
from microwakeword.audio.audio_utils import generate_features_for_clip

MODEL_PATH = 'trained_models/DORA/dora_model_int8.tflite'
with open(MODEL_PATH, 'rb') as f:
    model_bytes = f.read()

interp = tf.lite.Interpreter(model_content=model_bytes)
interp.allocate_tensors()
inp = interp.get_input_details()[0]['index']
out = interp.get_output_details()[0]['index']
all_t = interp.get_tensor_details()

STATE_INDICES = [(51,[1,22,1,64]),(52,[1,16,1,64]),(53,[1,2,1,40]),
                 (57,[1,4,1,32]),(62,[1,10,1,64]),(67,[1,14,1,64])]

# Zero all states
for idx, shape in STATE_INDICES:
    interp.set_tensor(idx, np.zeros(shape, dtype=np.float32))

audio, _ = librosa.load('dataset/split/test/DORA/dora_spk_raw_dhora.wav', sr=16000, mono=True)
audio_int16 = np.clip(audio * 32768, -32768, 32767).astype(np.int16)
feats = generate_features_for_clip(audio_int16, step_ms=10)

def safe_get(t_idx):
    try:
        return interp.get_tensor(t_idx).copy()
    except Exception:
        return None

before = {t['index']: safe_get(t['index']) for t in all_t}
chunk = feats[0:3].reshape(1,3,40).astype(np.float32)
interp.set_tensor(inp, chunk)
interp.invoke()
after = {t['index']: safe_get(t['index']) for t in all_t}

print("Tensors changed by invoke:")
name_map = {t['index']: t['name'] for t in all_t}
shape_map = {t['index']: t['shape'] for t in all_t}
for idx in before:
    b = before[idx]; a = after[idx]
    if b is None or a is None:
        continue
    try:
        if not np.allclose(b, a, atol=1e-6):
            sh = shape_map[idx]
            if len(sh) > 0 and max(sh) < 300:
                print(f"  idx={idx:3d}  shape={str(sh):20s}  {name_map[idx]}")
    except Exception:
        pass

# Now figure out: after invoke, which state indices contain the NEW state?
print()
print("State indices after invoke (current values):")
for idx, shape in STATE_INDICES:
    val = interp.get_tensor(idx)
    print(f"  idx={idx}  shape={shape}  sum={val.sum():.4f}  max={val.max():.4f}")
