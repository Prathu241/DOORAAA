@echo off
REM DORA Dashboard - Windows Batch Launcher
REM No PowerShell issues, works directly

echo.
echo ========================================
echo   DORA Dashboard - Starting Services
echo ========================================
echo.

REM Kill any existing node processes
taskkill /F /IM node.exe >nul 2>&1

timeout /t 2 /nobreak

REM Start Serial Bridge
echo 1. Starting ESP32 Serial Bridge (ws://localhost:8080)...
start "ESP32 Serial Bridge" node esp32-serial-bridge.js

timeout /t 2 /nobreak

REM Start Dashboard
echo 2. Starting Dashboard (http://localhost:5000)...
start "DORA Dashboard" npm start

echo.
echo ========================================
echo Services starting...
echo.
echo   Dashboard: http://localhost:5000
echo   Serial Bridge: ws://localhost:8080
echo   Health Check: http://localhost:3000/health
echo.
echo Open browser: http://localhost:5000
echo ========================================
echo.
