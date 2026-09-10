@echo off
REM Flash script for mic_test.ino to ESP32-S3
REM Make sure esptool is installed: pip install esptool

cls
echo ===============================================================
echo         DORA Microphone Test - Command Line Flasher
echo ===============================================================
echo.

REM Check if esptool exists
esptool.py version >nul 2>&1
if errorlevel 1 (
    echo ERROR: esptool not found
    echo Install it first: pip install esptool
    echo.
    pause
    exit /b 1
)

echo Flashing to COM3...
echo.

REM Try with standard speed first
echo Attempting flash at 921600 baud...
esptool.py -p COM3 -b 921600 --after hard_reset write_flash -z --flash_mode dio --flash_freq 80m --flash_size detect 0x0 "mic_test.ino.esp32s3.bin"

if errorlevel 1 (
    echo.
    echo First attempt failed. Trying slower speed (115200 baud)...
    esptool.py -p COM3 -b 115200 --after hard_reset write_flash -z --flash_mode dio --flash_freq 80m --flash_size detect 0x0 "mic_test.ino.esp32s3.bin"
    
    if errorlevel 1 (
        echo.
        echo ERROR: Flash failed at both speeds
        echo Troubleshooting:
        echo - Check USB cable is plugged in
        echo - Try different USB port
        echo - Hold BOOT button during flash
        echo.
        pause
        exit /b 1
    )
)

echo.
echo ===============================================================
echo SUCCESS! Firmware flashed to ESP32-S3
echo ===============================================================
echo.
echo Next steps:
echo 1. Open Serial Monitor in Arduino IDE (9600 baud)
echo 2. Speak "DORA" into microphone
echo 3. Report if RMS/peak values change
echo.
pause
