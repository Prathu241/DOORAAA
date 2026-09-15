@echo off
echo ========================================
echo DORA DASHBOARD - AUTOMATED TEST
echo ========================================
echo.

echo Step 1: Checking Node.js installation...
node --version
if errorlevel 1 (
    echo [ERROR] Node.js not found! Install from https://nodejs.org
    pause
    exit /b 1
)
echo [OK] Node.js found
echo.

echo Step 2: Checking npm packages...
cd /d "%~dp0"
if not exist "node_modules\" (
    echo [INFO] Installing dependencies...
    call npm install
) else (
    echo [OK] Dependencies already installed
)
echo.

echo Step 3: Building dashboard...
call npm run build
if errorlevel 1 (
    echo [ERROR] Build failed! Check errors above
    pause
    exit /b 1
)
echo [OK] Build successful
echo.

echo ========================================
echo DASHBOARD TEST COMPLETE
echo ========================================
echo.
echo To start the system:
echo.
echo Terminal 1: node esp32-bridge.js
echo Terminal 2: npm run dev
echo Browser: http://localhost:5173
echo.
pause
