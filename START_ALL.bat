@echo off
title DORA — Full System Startup
color 0A

echo.
echo ============================================================
echo   DORA SYSTEM STARTUP
echo ============================================================
echo.

:: Kill anything on ports 8080 and 5000
echo [1/4] Clearing ports 8080 and 5000...
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":8080 "') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon 2^>nul ^| findstr ":5000 "') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 >nul

:: Detect ESP32 COM port
echo [2/4] Detecting ESP32 COM port...
set ESP_PORT=

for %%p in (COM10 COM9 COM8 COM7 COM6 COM5 COM11 COM12) do (
    if "%ESP_PORT%"=="" (
        mode %%p >nul 2>&1
        if not errorlevel 1 set ESP_PORT=%%p
    )
)

if "%ESP_PORT%"=="" (
    echo.
    echo  *** ESP32 NOT DETECTED on any COM port ***
    echo  Make sure Arduino IDE is CLOSED and ESP32 is plugged in.
    echo.
    echo  Plug in ESP32 then press any key to retry...
    pause >nul
    goto :eof
)

echo     ESP32 detected on %ESP_PORT%
echo.

:: Start bridge
echo [3/4] Starting Serial Bridge ^(%ESP_PORT%^)...
start "DORA Bridge" cmd /k "cd /d c:\Users\PRATHAM\DORA_MIXED-net\dashboard && set SERIAL_PORT=%ESP_PORT%&& node esp32-serial-bridge.js"
timeout /t 3 >nul

:: Start server
echo [4/4] Starting Dashboard Server...
start "DORA Server" cmd /k "cd /d c:\Users\PRATHAM\DORA_MIXED-net\dashboard && node server.js"
timeout /t 3 >nul

:: Open browser
echo.
echo ============================================================
echo   DONE
echo   Bridge   : ws://localhost:8080   ESP32=%ESP_PORT%
echo   Dashboard: http://localhost:5000
echo ============================================================
echo.
start http://localhost:5000
pause
