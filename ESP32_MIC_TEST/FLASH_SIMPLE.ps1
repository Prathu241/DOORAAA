# Simple PowerShell script to flash ESP32-S3
# Usage: .\FLASH_SIMPLE.ps1

Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host "DORA Microphone Test - ESP32-S3 Flasher" -ForegroundColor Green
Write-Host "===============================================================" -ForegroundColor Cyan
Write-Host ""

# Find the .bin file
$binFile = Get-ChildItem -Path . -Filter "*.esp32s3.bin" -ErrorAction SilentlyContinue | Select-Object -First 1

if (-not $binFile) {
    Write-Host "ERROR: No .esp32s3.bin file found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "You need to generate it first:" -ForegroundColor Yellow
    Write-Host "  1. Arduino IDE: Sketch → Export Compiled Binary" -ForegroundColor White
    Write-Host "  2. Copy the .esp32s3.bin file to this folder" -ForegroundColor White
    Write-Host "  3. Run this script again" -ForegroundColor White
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

$binPath = $binFile.FullName
Write-Host "Found binary: $($binFile.Name)" -ForegroundColor Green
Write-Host "Full path: $binPath" -ForegroundColor White
Write-Host ""

Write-Host "Flashing to ESP32-S3 on COM3..." -ForegroundColor Yellow
Write-Host "Speed: 921600 baud" -ForegroundColor White
Write-Host ""

# Try to flash
python -m esptool -p COM3 -b 921600 --after hard_reset write_flash -z --flash_mode dio --flash_freq 80m --flash_size detect 0x0 "$binPath"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Green
    Write-Host "SUCCESS! Firmware flashed to ESP32-S3" -ForegroundColor Green
    Write-Host "===============================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Open Arduino IDE Serial Monitor (9600 baud)" -ForegroundColor White
    Write-Host "  2. Speak 'DORA' into microphone" -ForegroundColor White
    Write-Host "  3. Report if RMS/peak values jump (MIC PASS)" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "===============================================================" -ForegroundColor Red
    Write-Host "FAILED! Flash error" -ForegroundColor Red
    Write-Host "===============================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  1. Check USB cable is plugged in" -ForegroundColor White
    Write-Host "  2. Try different USB port" -ForegroundColor White
    Write-Host "  3. Hold BOOT button during flash" -ForegroundColor White
    Write-Host ""
}

Read-Host "Press Enter to exit"
