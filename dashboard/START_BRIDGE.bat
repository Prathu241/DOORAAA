@echo off
echo ========================================
echo ESP32 SERIAL BRIDGE - STARTING
echo ========================================
echo.
echo This connects ESP32 serial data to dashboard
echo.

cd /d "%~dp0"

echo IMPORTANT:
echo   - Make sure ESP32 is connected via USB
echo   - CLOSE Arduino Serial Monitor completely
echo   - ESP32 must have firmware uploaded (mic_test.ino)
echo.
echo Starting bridge on COM11...
echo.
echo If you see "Cannot open COM11":
echo   1. Close Arduino IDE Serial Monitor
echo   2. Run this script again
echo.
echo Dashboard will connect automatically when it sees:
echo   "WebSocket server: ws://localhost:8080"
echo.

node esp32-bridge.js

pause
