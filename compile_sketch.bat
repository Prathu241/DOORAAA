@echo off
SET CLI=%LOCALAPPDATA%\Programs\Arduino IDE\resources\app\lib\backend\resources\arduino-cli.exe
SET SKETCH=C:\Users\PRATHAM\DORA_MIXED-net\ESP32_MIC_TEST\dora_full_inference
SET OUT=C:\Users\PRATHAM\DORA_MIXED-net\build_result3.txt

echo Compiling DORA sketch for ESP32-S3...
echo Build started: %DATE% %TIME% > "%OUT%"
"%CLI%" compile --fqbn esp32:esp32:esp32s3 --warnings default "%SKETCH%" >> "%OUT%" 2>&1
echo Exit code: %ERRORLEVEL% >> "%OUT%"
echo Done.
