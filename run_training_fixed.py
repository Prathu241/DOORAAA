#!/usr/bin/env python3
"""
PHASE 2: Run DORA Streaming MixedNet Training
No Unicode characters - compatible with Windows PowerShell
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

def main():
    os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'
    
    project_root = Path(__file__).parent
    mww_dir = project_root / 'microWakeWord'
    yaml_config = project_root / 'training_parameters_DORA_FIXED.yaml'
    
    print("\n" + "="*70)
    print("PHASE 2: DORA STREAMING MIXEDNET TRAINING")
    print("="*70)
    print()
    
    # Verify prerequisites
    print("Preflight checks:")
    if not yaml_config.exists():
        print(f"  [FAIL] Config not found: {yaml_config}")
        return 1
    print(f"  [PASS] Config found")
    
    if not mww_dir.exists():
        print(f"  [FAIL] microWakeWord dir not found: {mww_dir}")
        return 1
    print(f"  [PASS] microWakeWord found")
    
    print()
    print("Configuration:")
    print("  Keyword: DORA")
    print("  Architecture: Streaming MixedNet")
    print("  Training steps: 15,000")
    print("  Batch size: 128")
    print("  Checkpoint: fresh (--restore_checkpoint 0)")
    print("  Quantization: int8 streaming TFLite")
    print()
    
    # Build command
    cmd = [
        sys.executable, '-m', 'microwakeword.model_train_eval',
        '--training_config', str(yaml_config),
        '--train', '1',
        '--restore_checkpoint', '0',
        '--test_tf_nonstreaming', '0',
        '--test_tflite_nonstreaming', '0',
        '--test_tflite_nonstreaming_quantized', '0',
        '--test_tflite_streaming', '0',
        '--test_tflite_streaming_quantized', '1',
        '--use_weights', 'best_weights',
        'mixednet',
        '--pointwise_filters', '64,64,64,64',
        '--repeat_in_block', '1,1,1,1',
        '--mixconv_kernel_sizes', '[5],[7,11],[9,15],[23]',
        '--residual_connection', '0,0,0,0',
        '--first_conv_filters', '32',
        '--first_conv_kernel_size', '5',
        '--stride', '3',
    ]
    
    print("Starting training...")
    print(f"Start time: {datetime.now()}")
    print()
    
    # Change to microWakeWord directory for training
    os.chdir(mww_dir)
    
    # Execute training
    start_time = datetime.now()
    result = subprocess.run(cmd)
    end_time = datetime.now()
    duration_minutes = (end_time - start_time).total_seconds() / 60
    
    print()
    print("="*70)
    print("TRAINING EXECUTION COMPLETE")
    print("="*70)
    print(f"End time: {end_time}")
    print(f"Duration: {duration_minutes:.1f} minutes")
    print(f"Exit code: {result.returncode}")
    print()
    
    return result.returncode

if __name__ == '__main__':
    sys.exit(main())
