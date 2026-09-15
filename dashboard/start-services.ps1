# Start DORA Dashboard Services
# Usage: powershell .\start-services.ps1

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "   DORA Dashboard - Multi-Service Start" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Kill any existing node processes
Write-Host "Cleaning up existing processes..." -ForegroundColor Yellow
Get-Process node -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "Starting 2 services in separate windows..." -ForegroundColor Cyan
Write-Host ""

# Terminal 1: ESP32 Serial Bridge
Write-Host "1️⃣  Starting ESP32 Serial Bridge (Port 8080)..." -ForegroundColor Green
$cmd1 = "cd '$PSScriptRoot'; Write-Host '📡 ESP32 Serial Bridge' -ForegroundColor Cyan; node esp32-serial-bridge.js"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd1 -WindowStyle Normal

Start-Sleep -Seconds 2

# Terminal 2: Dashboard
Write-Host "2️⃣  Starting Dashboard Server (Port 5000)..." -ForegroundColor Green
$cmd2 = "cd '$PSScriptRoot'; Write-Host '🎙️ DORA Dashboard' -ForegroundColor Cyan; npm start"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $cmd2 -WindowStyle Normal

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "✅ Services starting..." -ForegroundColor Green
Write-Host ""
Write-Host "📊 Serial Bridge: ws://localhost:8080" -ForegroundColor Yellow
Write-Host "🌐 Dashboard: http://localhost:5000" -ForegroundColor Yellow
Write-Host "🩺 Health Check: http://localhost:3000/health" -ForegroundColor Yellow
Write-Host ""
Write-Host "Open browser: http://localhost:5000" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
