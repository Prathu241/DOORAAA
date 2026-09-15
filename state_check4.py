import os, sys
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import tensorflow as tf
import numpy as np
import librosa
from microwakeword.audio.audio_utils import generate_features_for_clip

log_lines = []
def L(s=''):
    log_lines.append(str(s))

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

audio, _ = librosa.load('dataset/split/test/DORA/dora_spk_raw_dhora.wav', sr=16000, mono=True)
audio_int16 = np.clip(audio * 32768, -32768, 32767).astype(np.int16)
feats = generate_features_for_clip(audio_int16, step_ms=10)
L(f"Feature shape: {feats.shape}")

# Snapshot helper
def snapshot():
    snap = {}
    for t in all_t:
        try:
            snap[t['index']] = interp.get_tensor(t['index']).copy()
        except:
            snap[t['index']] = None
    return snap

zero_states()
before = snapshot()
chunk = feats[0:3].reshape(1, 3, 40).astype(np.float32)
interp.set_tensor(inp_idx, chunk)
interp.invoke()
after = snapshot()

L("Tensors changed by invoke:")
for idx in sorted(before.keys()):
    b, a = before[idx], after[idx]
    if b is None or a is None: continue
    try:
        sh = shape_map[idx]
        if len(sh)>0 and max(sh)<300 and not np.allclose(b, a, atol=1e-6):
            L(f"  idx={idx:3d}  shape={str(sh):20s}  {name_map[idx]}")
    except: pass

L()
L("State tensor values after first invoke:")
for idx, shape in STATE_IN:
    val = interp.get_tensor(idx)
    b = before[idx]
    changed = not np.allclose(b, val, atol=1e-6) if b is not None else 'unknown'
    L(f"  idx={idx}  sum={val.sum():.4f}  max={val.max():.4f}  changed={changed}")

# Sequential persistent state
L()
L("Full DORA clip - sequential (persistent state):")
zero_states()
scores_seq = []
T = feats.shape[0]
for j in range(0, T-2):
    chunk = feats[j:j+3].reshape(1,3,40).astype(np.float32)
    interp.set_tensor(inp_idx, chunk)
    interp.invoke()
    scores_seq.append(float(interp.get_tensor(out_idx).flat[0]))
peak = max(scores_seq)
mean = sum(scores_seq)/len(scores_seq)
above90 = sum(1 for s in scores_seq if s > 0.9)
L(f"  frames={len(scores_seq)}  peak={peak:.4f}  mean={mean:.4f}  frames>0.9={above90}")

# Background clip sequential
L()
L("Background clip - sequential (persistent state):")
bg_audio, _ = librosa.load('dataset/background_wav/Background_synth_pink_noise_0.wav', sr=16000, mono=True)
bg_int16 = np.clip(bg_audio * 32768, -32768, 32767).astype(np.int16)
bg_feats = generate_features_for_clip(bg_int16, step_ms=10)
zero_states()
bg_scores = []
for j in range(0, bg_feats.shape[0]-2):
    chunk = bg_feats[j:j+3].reshape(1,3,40).astype(np.float32)
    interp.set_tensor(inp_idx, chunk)
    interp.invoke()
    bg_scores.append(float(interp.get_tensor(out_idx).flat[0]))
L(f"  frames={len(bg_scores)}  peak={max(bg_scores):.4f}  mean={sum(bg_scores)/len(bg_scores):.4f}")

# Unknown hard negative
L()
L("Hard negative 'good_morning_dora' - sequential:")
unk_audio, _ = librosa.load('dataset/unknown_wav/hard_negatives_good_morning_dora.wav', sr=16000, mono=True)
unk_int16 = np.clip(unk_audio * 32768, -32768, 32767).astype(np.int16)
unk_feats = generate_features_for_clip(unk_int16, step_ms=10)
zero_states()
unk_scores = []
for j in range(0, unk_feats.shape[0]-2):
    chunk = unk_feats[j:j+3].reshape(1,3,40).astype(np.float32)
    interp.set_tensor(inp_idx, chunk)
    interp.invoke()
    unk_scores.append(float(interp.get_tensor(out_idx).flat[0]))
L(f"  frames={len(unk_scores)}  peak={max(unk_scores):.4f}  mean={sum(unk_scores)/len(unk_scores):.4f}")

L()
L("DONE")

# Write to file
with open('state_check_result.txt', 'w') as f:
    f.write('\n'.join(log_lines))
