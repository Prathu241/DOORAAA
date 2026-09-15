# Find ESP32 Serial Port

Write-Host "Scanning for ESP32 serial ports..." -ForegroundColor Cyan

$ports = Get-WmiObject Win32_SerialPort
if ($ports) {
    Write-Host "`nAvailable Serial Ports:" -ForegroundColor Green
    foreach ($port in $ports) {
        Write-Host "  - $($port.Name): $($port.Description)" -ForegroundColor Yellow
    }
} else {
    Write-Host "No serial ports found!" -ForegroundColor Red
}

Write-Host "`nTo use a different port:" -ForegroundColor Cyan
Write-Host "1. Edit: esp32-serial-bridge.js" -ForegroundColor White
Write-Host "2. Change line 17: const SERIAL_PORT = 'COMX';" -ForegroundColor White
Write-Host "3. Replace X with your port number" -ForegroundColor White
