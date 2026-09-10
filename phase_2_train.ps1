# phase_2_train.ps1 -- PHASE 2: Train DORA Streaming MixedNet
# Automates the training sequence described in PROJECT_STATUS.md

$ErrorActionPreference = "Stop"
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User") + ";C:\Users\PRATHAM\AppData\Local\Programs\Python\Python310\Scripts"
$env:PYTHONIOENCODING = "utf-8"
$env:TF_CPP_MIN_LOG_LEVEL = "2"

Set-Location "C:\Users\PRATHAM\DORA_MIXED-net"

function info  { Write-Host "[INFO]  $args" -ForegroundColor Cyan }
function ok    { Write-Host "[OK]    $args" -ForegroundColor Green }
function warn  { Write-Host "[WARN]  $args" -ForegroundColor Yellow }
function err   { Write-Host "[ERR]   $args" -ForegroundColor Red }
function sep   { Write-Host "$(('=')*60)" -ForegroundColor Cyan }

sep
Write-Host "PHASE 2: Train DORA Streaming MixedNet" -ForegroundColor Cyan
sep
Write-Host ""

# Step 1: Verify prerequisites
info "Step 1: Verify microWakeWord installation"
try {
    python -c "import microwakeword; print(f'  microWakeWord OK')" 2>&1 | Select-Object -First 1
} catch {
    err "microWakeWord not installed. Run: cd microWakeWord && pip install -e ."
    exit 1
}

# Step 2: Verify training YAML exists
info "Step 2: Verify training_parameters_DORA.yaml"
if (!(Test-Path "training_parameters_DORA.yaml")) {
    err "training_parameters_DORA.yaml not found. Run: python make_training_config.py --keyword DORA"
    exit 1
}
ok "Found training_parameters_DORA.yaml"

# Step 3: Verify dataset split
info "Step 3: Verify dataset split"
$train_count = (Get-ChildItem "dataset/split/train/DORA" -Filter "*.wav" -ErrorAction SilentlyContinue | Measure-Object).Count
$val_count   = (Get-ChildItem "dataset/split/val/DORA" -Filter "*.wav" -ErrorAction SilentlyContinue | Measure-Object).Count
$test_count  = (Get-ChildItem "dataset/split/test/DORA" -Filter "*.wav" -ErrorAction SilentlyContinue | Measure-Object).Count

if ($train_count -lt 100 -or $val_count -lt 10 -or $test_count -lt 10) {
    err "Dataset split incomplete: train=$train_count val=$val_count test=$test_count"
    exit 1
}
ok "Split verified: train=$train_count val=$val_count test=$test_count"

# Step 4: Navigate to microWakeWord and start training
Write-Host ""
sep
info "Step 4: Starting training (this will take 60–90 minutes)"
sep
Write-Host ""

$train_start = Get-Date
info "Training started at: $train_start"
Write-Host ""

$yaml_path = (Resolve-Path "training_parameters_DORA.yaml").Path

cd microWakeWord

# Run the exact training command
python -m microwakeword.model_train_eval `
    --training_config "$yaml_path" `
    --train 1 `
    --restore_checkpoint 0 `
    --test_tf_nonstreaming 0 `
    --test_tflite_nonstreaming 0 `
    --test_tflite_nonstreaming_quantized 0 `
    --test_tflite_streaming 0 `
    --test_tflite_streaming_quantized 1 `
    --use_weights best_weights `
    mixednet `
    --pointwise_filters "64,64,64,64" `
    --repeat_in_block "1,1,1,1" `
    --mixconv_kernel_sizes "[5],[7,11],[9,15],[23]" `
    --residual_connection "0,0,0,0" `
    --first_conv_filters 32 `
    --first_conv_kernel_size 5 `
    --stride 3

$train_exit = $LASTEXITCODE
$train_end = Get-Date
$train_duration = ($train_end - $train_start).TotalMinutes

Write-Host ""
sep
if ($train_exit -eq 0) {
    ok "Training completed in $([math]::Round($train_duration, 1)) minutes"
} else {
    err "Training failed with exit code $train_exit"
    exit $train_exit
}

# Step 5: Verify output model
Set-Location ".."
$model_path = "trained_models\DORA\tflite_stream_state_internal_quant\stream_state_internal_quant.tflite"

if (!(Test-Path $model_path)) {
    err "Model not found at: $model_path"
    exit 1
}

$model_size_kb = [math]::Round((Get-Item $model_path).Length / 1024, 1)
ok "Model exported: $model_path ($model_size_kb KB)"

# Step 6: Summary
Write-Host ""
sep
Write-Host "PHASE 2 COMPLETE" -ForegroundColor Green
sep
Write-Host ""
Write-Host "  Model              : $model_path"
Write-Host "  Model size         : $model_size_kb KB"
Write-Host "  Training time      : $([math]::Round($train_duration, 1)) minutes"
Write-Host "  Training finished  : $train_end"
Write-Host ""
Write-Host "Next steps (PHASE 3):"
Write-Host "  1. Generate C++ model array: xxd -i '$model_path' > DORA_model_data.cc"
Write-Host "  2. Integrate model into ESP32-S3 firmware"
Write-Host "  3. Flash and test on device"
Write-Host ""
