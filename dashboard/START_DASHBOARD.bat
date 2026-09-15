@echo off
echo ========================================
echo DORA Dashboard - Live ESP32 Monitor
echo ========================================
echo.
echo Starting services...
echo.

REM Start ESP32 Serial Bridge (port 8080)
start "ESP32 Bridge" cmd /k "node esp32-bridge.js"
timeout /t 2 /nobreak >nul

REM Start Dashboard Frontend (port 5173)
start "Dashboard" cmd /k "npm run dev"

echo.
echo ========================================
echo Dashboard starting...
echo.
echo ESP32 Bridge: ws://localhost:8080
echo Dashboard UI: http://localhost:5173
echo.
echo Close Arduino Serial Monitor first!
echo ========================================
echo.
pause
