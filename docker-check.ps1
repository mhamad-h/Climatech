# Simple Docker Check Script

Write-Host "Checking Docker status..." -ForegroundColor Yellow

# Check if Docker is installed
if (!(Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker not found. Please install Docker Desktop from:" -ForegroundColor Red
    Write-Host "https://www.docker.com/products/docker-desktop" -ForegroundColor Cyan
    exit 1
}

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "Docker is running successfully!" -ForegroundColor Green
    Write-Host "You can now run the Azure deployment script." -ForegroundColor Cyan
} catch {
    Write-Host "Docker is not running." -ForegroundColor Red
    Write-Host ""
    Write-Host "To start Docker:" -ForegroundColor Yellow
    Write-Host "1. Open Docker Desktop from Start Menu" -ForegroundColor White
    Write-Host "2. Wait for it to fully start (whale icon in system tray)" -ForegroundColor White
    Write-Host "3. Run this script again" -ForegroundColor White
    Write-Host ""
    Write-Host "Or try starting it automatically..." -ForegroundColor Yellow
    
    # Try to find and start Docker Desktop
    $dockerPath = "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerPath) {
        Write-Host "Starting Docker Desktop..." -ForegroundColor Cyan
        Start-Process $dockerPath
        Write-Host "Docker Desktop is starting. Please wait for it to fully load, then run deployment script." -ForegroundColor Green
    } else {
        Write-Host "Docker Desktop not found in default location." -ForegroundColor Red
        Write-Host "Please start it manually from the Start Menu." -ForegroundColor Yellow
    }
}