@echo off
echo ============================================================
echo DORA ESP32 VERIFICATION AND UPLOAD
echo ============================================================
echo.
echo [1/3] Checking Arduino CLI...
arduino-cli version
if errorlevel 1 (
    echo ERROR: Arduino CLI not found
    echo Please install from: https://arduino.github.io/arduino-cli/
    pause
    exit /b 1
)

echo.
echo [2/3] Compiling firmware...
echo Path: ESP32_MIC_TEST\dora_full_inference\dora_full_inference.ino
echo.

arduino-cli compile --fqbn esp32:esp32:esp32s3 ESP32_MIC_TEST\dora_full_inference

if errorlevel 1 (
    echo.
    echo ============================================================
    echo COMPILATION FAILED!
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo COMPILATION SUCCESS!
echo ============================================================
echo.
echo Ready to upload to ESP32-S3 on COM10
echo.
echo [3/3] Upload? (Press any key to continue, Ctrl+C to cancel)
pause

arduino-cli upload -p COM10 --fqbn esp32:esp32:esp32s3 ESP32_MIC_TEST\dora_full_inference

echo.
echo ============================================================
echo UPLOAD COMPLETE!
echo ============================================================
echo.
echo Next steps:
echo 1. Open Serial Monitor: arduino-cli monitor -p COM10 -c baudrate=115200
echo 2. Start dashboard: cd dashboard ; node esp32-bridge.js
echo 3. Start web UI: cd dashboard ; npm run dev
echo.
pause
