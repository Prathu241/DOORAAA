import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
import tensorflow as tf
import numpy as np
import librosa
from microwakeword.audio.audio_utils import generate_features_for_clip

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

STATE_IN = [(51,[1,22,1,64]), (52,[1,16,1,64]), (53,[1,2,1,40]),
            (57,[1,4,1,32]),  (62,[1,10,1,64]), (67,[1,14,1,64])]

def zero_states():
    for idx, shape in STATE_IN:
        interp.set_tensor(idx, np.zeros(shape, dtype=np.float32))

# Load clip
audio, _ = librosa.load('dataset/split/test/DORA/dora_spk_raw_dhora.wav', sr=16000, mono=True)
audio_int16 = np.clip(audio * 32768, -32768, 32767).astype(np.int16)
feats = generate_features_for_clip(audio_int16, step_ms=10)
print("Feature shape:", feats.shape)

# Snapshot before invoke
def snapshot():
    snap = {}
    for t in all_t:
        try:
            snap[t['index']] = interp.get_tensor(t['index']).copy()
        except Exception:
            snap[t['index']] = None
    return snap

zero_states()
before = snapshot()
chunk = feats[0:3].reshape(1, 3, 40).astype(np.float32)
interp.set_tensor(inp_idx, chunk)
interp.invoke()
after = snapshot()

print("\nTensors changed by invoke (shape max < 300):")
for idx in sorted(before.keys()):
    b, a = before[idx], after[idx]
    if b is None or a is None:
        continue
    try:
        sh = shape_map[idx]
        if len(sh) > 0 and max(sh) < 300 and not np.allclose(b, a, atol=1e-6):
            print(f"  idx={idx:3d}  shape={str(sh):20s}  {name_map[idx]}")
    except Exception:
        pass

print("\nState tensor values after first invoke:")
for idx, shape in STATE_IN:
    val = interp.get_tensor(idx)
    print(f"  idx={idx}  sum={val.sum():.4f}  max={val.max():.4f}  shape={val.shape}")

# Run full DORA clip sequentially (persistent state) and record peak score
print("\nFull clip sequential (state persists between frames):")
zero_states()
scores_seq = []
T = feats.shape[0]
for j in range(0, T-2):
    chunk = feats[j:j+3].reshape(1, 3, 40).astype(np.float32)
    interp.set_tensor(inp_idx, chunk)
    interp.invoke()
    scores_seq.append(float(interp.get_tensor(out_idx).flat[0]))
print(f"  frames={len(scores_seq)}  max={max(scores_seq):.4f}  mean={sum(scores_seq)/len(scores_seq):.4f}")
above90 = [s for s in scores_seq if s > 0.9]
print(f"  frames>0.90: {len(above90)}")

# Run same clip with fresh interp per frame (no state) 
print("\nFull clip fresh-interp each frame (no state):")
scores_fresh = []
for j in range(0, T-2):
    i2 = tf.lite.Interpreter(model_content=model_bytes)
    i2.allocate_tensors()
    chunk = feats[j:j+3].reshape(1, 3, 40).astype(np.float32)
    i2.set_tensor(i2.get_input_details()[0]['index'], chunk)
    i2.invoke()
    scores_fresh.append(float(i2.get_tensor(i2.get_output_details()[0]['index']).flat[0]))
    if j > 30:  # only need first 30 to see pattern
        scores_fresh.append(0.0)
        break
print(f"  first 30 frames  max={max(scores_fresh):.4f}  mean={sum(scores_fresh)/len(scores_fresh):.4f}")

# Run a background noise clip sequentially
print("\nBackground clip sequential (state persists):")
bg_audio, _ = librosa.load('dataset/background_wav/Background_synth_pink_noise_0.wav', sr=16000, mono=True)
bg_int16 = np.clip(bg_audio * 32768, -32768, 32767).astype(np.int16)
bg_feats = generate_features_for_clip(bg_int16, step_ms=10)
zero_states()
bg_scores = []
T2 = bg_feats.shape[0]
for j in range(0, T2-2):
    chunk = bg_feats[j:j+3].reshape(1, 3, 40).astype(np.float32)
    interp.set_tensor(inp_idx, chunk)
    interp.invoke()
    bg_scores.append(float(interp.get_tensor(out_idx).flat[0]))
print(f"  frames={len(bg_scores)}  max={max(bg_scores):.4f}  mean={sum(bg_scores)/len(bg_scores):.4f}")

print("\nDONE")
