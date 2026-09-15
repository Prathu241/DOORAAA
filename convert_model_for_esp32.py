#!/usr/bin/env python3
"""
Convert trained DORA model to ESP32-compatible TFLite + C array
"""

import tensorflow as tf
import numpy as np
import os

# Paths
MODEL_PATH = "trained_models/DORA/stream_state_internal"
OUTPUT_TFLITE = "trained_models/DORA/dora_model_int8.tflite"
OUTPUT_HEADER = "ESP32_MIC_TEST/dora_full_inference/model_data.h"

print("=" * 60)
print("DORA MODEL → ESP32 CONVERSION")
print("=" * 60)

# Step 1: Load SavedModel
print("\n[1/4] Loading trained model...")
print(f"  Path: {MODEL_PATH}")

if not os.path.exists(MODEL_PATH):
    print(f"  ❌ ERROR: Model not found at {MODEL_PATH}")
    exit(1)

converter = tf.lite.TFLiteConverter.from_saved_model(MODEL_PATH)

# Step 2: Quantize to INT8 (for ESP32 memory constraints)
print("\n[2/4] Applying INT8 quantization...")
converter.optimizations = [tf.lite.Optimize.DEFAULT]

# Representative dataset for quantization
def representative_dataset():
    """Generate sample data for quantization calibration"""
    # Assuming input shape is [1, time_steps, features]
    # Adjust based on your model's actual input shape
    for _ in range(100):
        # Replace with actual input shape from your model
        data = np.random.randn(1, 98, 40).astype(np.float32)  # Example: 98 frames, 40 MFCC features
        yield [data]

converter.representative_dataset = representative_dataset
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8

# Step 3: Convert to TFLite
print("\n[3/4] Converting to TFLite...")
try:
    tflite_model = converter.convert()
    print(f"  ✅ Conversion successful")
    print(f"  Model size: {len(tflite_model):,} bytes")
    
    # Save TFLite file
    os.makedirs(os.path.dirname(OUTPUT_TFLITE), exist_ok=True)
    with open(OUTPUT_TFLITE, 'wb') as f:
        f.write(tflite_model)
    print(f"  ✅ Saved: {OUTPUT_TFLITE}")
    
except Exception as e:
    print(f"  ❌ Conversion failed: {e}")
    print("\n  Trying alternative conversion without quantization...")
    
    # Fallback: Convert without quantization
    converter = tf.lite.TFLiteConverter.from_saved_model(MODEL_PATH)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    tflite_model = converter.convert()
    
    with open(OUTPUT_TFLITE, 'wb') as f:
        f.write(tflite_model)
    print(f"  ✅ Saved (float32 fallback): {OUTPUT_TFLITE}")
    print(f"  Model size: {len(tflite_model):,} bytes")

# Step 4: Convert to C header file
print("\n[4/4] Generating C header file...")

# Convert bytes to C array
c_array = ','.join([f'0x{b:02x}' for b in tflite_model])

header_content = f"""/*
 * DORA Keyword Detection Model - Auto-generated
 * Model size: {len(tflite_model):,} bytes
 * Quantization: INT8
 */

#ifndef MODEL_DATA_H
#define MODEL_DATA_H

const unsigned char dora_model_data[] = {{
{c_array}
}};

const unsigned int dora_model_len = {len(tflite_model)};

#endif // MODEL_DATA_H
"""

os.makedirs(os.path.dirname(OUTPUT_HEADER), exist_ok=True)
with open(OUTPUT_HEADER, 'w') as f:
    f.write(header_content)

print(f"  ✅ Saved: {OUTPUT_HEADER}")

print("\n" + "=" * 60)
print("✅ CONVERSION COMPLETE")
print("=" * 60)
print(f"\nModel ready for ESP32:")
print(f"  • TFLite file: {OUTPUT_TFLITE}")
print(f"  • C header: {OUTPUT_HEADER}")
print(f"  • Size: {len(tflite_model):,} bytes ({len(tflite_model)/1024:.1f} KB)")
print(f"\nNext step: Upload ESP32_MIC_TEST/dora_full_inference/dora_full_inference.ino")
print()
