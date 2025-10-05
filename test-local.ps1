# Quick Local Testing Script
# Run this to test your app locally before deploying

Write-Host "🌦️ Starting Climatech Local Testing Environment" -ForegroundColor Cyan

# Check if we're in the right directory
if (!(Test-Path "backend/app.py")) {
    Write-Error "Please run this script from the Climatech root directory"
    exit 1
}

# Start Backend
Write-Host "`n🔧 Starting Backend Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$(Get-Location)\backend'; C:\Users\Admin\Documents\GeoClime\Climatech\venv\Scripts\python.exe app.py"

# Wait a moment for backend to start
Start-Sleep -Seconds 5

# Test Backend Health
Write-Host "Testing backend health..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://192.168.164.97:8000/health" -TimeoutSec 10
    Write-Host "✅ Backend is running!" -ForegroundColor Green
    Write-Host "Backend URL: http://192.168.164.97:8000" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Backend not responding" -ForegroundColor Red
    Write-Host "Trying localhost..." -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -TimeoutSec 10
        Write-Host "✅ Backend is running on localhost!" -ForegroundColor Green
        Write-Host "Backend URL: http://localhost:8000" -ForegroundColor Cyan
    } catch {
        Write-Host "❌ Backend not responding on localhost either" -ForegroundColor Red
    }
}

# Start Frontend
Write-Host "`n🎨 Starting Frontend Development Server..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$(Get-Location)\client'; npm run dev"

Write-Host "`n🎯 Local URLs:" -ForegroundColor Cyan
Write-Host "Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "Backend: http://192.168.164.97:8000 (or http://localhost:8000)" -ForegroundColor White
Write-Host "API Docs: http://192.168.164.97:8000/docs" -ForegroundColor White

Write-Host "`n📝 Test the connection by:" -ForegroundColor Yellow
Write-Host "1. Open http://localhost:5173 in your browser" -ForegroundColor White
Write-Host "2. Try to generate a weather forecast" -ForegroundColor White
Write-Host "3. Check browser console for any API errors" -ForegroundColor White