@echo off
echo ================================================================
echo DORA MODEL DEPLOYMENT - COMPLETE SYSTEM
echo ================================================================
echo.
echo This will deploy YOUR trained model to ESP32 and start dashboard
echo.

cd /d "%~dp0"

echo [STEP 1/5] Converting model to ESP32 format...
echo.
python convert_model_for_esp32.py
if errorlevel 1 (
    echo.
    echo [ERROR] Model conversion failed!
    echo Check that Python and TensorFlow are installed.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo [STEP 2/5] Model converted successfully!
echo ================================================================
echo.
echo Next steps (do these manually):
echo.
echo 1. Open Arduino IDE
echo 2. Install library: TensorFlowLite_ESP32
echo    (Tools -^> Manage Libraries -^> Search "TensorFlowLite_ESP32")
echo.
echo 3. Open firmware:
echo    ESP32_MIC_TEST\dora_full_inference\dora_real_model.ino
echo.
echo 4. Upload to ESP32:
echo    - Board: ESP32S3 Dev Module
echo    - Port: COM11
echo    - Click Upload
echo.
echo 5. Close Arduino Serial Monitor (important!)
echo.
echo Press any key when ESP32 upload is complete...
pause

echo.
echo [STEP 3/5] Starting ESP32 bridge...
echo.
echo Opening Terminal 1 for bridge...
start "ESP32 Bridge" powershell -NoExit -Command "cd '%CD%\dashboard'; node esp32-bridge.js"
timeout /t 3 /nobreak >nul

echo.
echo [STEP 4/5] Starting dashboard...
echo.
echo Opening Terminal 2 for dashboard...
start "Dashboard UI" powershell -NoExit -Command "cd '%CD%\dashboard'; npm run dev"
timeout /t 5 /nobreak >nul

echo.
echo [STEP 5/5] Opening browser...
echo.
timeout /t 3 /nobreak >nul
start http://localhost:5173

echo.
echo ================================================================
echo DEPLOYMENT COMPLETE
echo ================================================================
echo.
echo Dashboard: http://localhost:5173
echo.
echo Check for:
echo   - Top-right shows: "ESP32 LIVE" (green dot)
echo   - Microphone panel visible
echo   - RMS values updating
echo.
echo Test detection:
echo   1. Speak normally -^> RMS increases
echo   2. Say "DORA" -^> Orb flashes red
echo   3. Check detection log
echo.
echo If dashboard shows "DEMO MODE":
echo   - Make sure Arduino Serial Monitor is closed
echo   - Check Terminal 1 for bridge errors
echo.
pause
