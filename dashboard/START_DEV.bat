@echo off
echo ========================================
echo DORA DASHBOARD - STARTING DEV SERVER
echo ========================================
echo.

cd /d "%~dp0"

echo [1/2] Installing dependencies...
call npm install
echo.

echo [2/2] Starting Vite dev server...
echo.
echo Dashboard will open at: http://localhost:5173
echo.
echo If you see a blank page:
echo   1. Press F12 to open browser dev tools
echo   2. Go to Console tab
echo   3. Press Ctrl+Shift+R to hard refresh
echo   4. Check for errors in console
echo.
echo Starting server...
echo.

call npm run dev

pause
