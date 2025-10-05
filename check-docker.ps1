# Docker Setup and Check Script for Climatech Deployment

Write-Host "🐳 Checking Docker Status for Climatech Deployment" -ForegroundColor Cyan

# Check if Docker Desktop is installed
$dockerPath = Get-Command docker -ErrorAction SilentlyContinue
if (!$dockerPath) {
    Write-Host "❌ Docker not found!" -ForegroundColor Red
    Write-Host "`n📥 Install Docker Desktop:" -ForegroundColor Yellow
    Write-Host "1. Go to: https://www.docker.com/products/docker-desktop" -ForegroundColor White
    Write-Host "2. Download Docker Desktop for Windows" -ForegroundColor White
    Write-Host "3. Install and restart your computer" -ForegroundColor White
    Write-Host "4. Run this script again" -ForegroundColor White
    exit 1
}

Write-Host "✅ Docker CLI found at: $($dockerPath.Source)" -ForegroundColor Green

# Check if Docker is running
Write-Host "`n🔍 Checking if Docker is running..." -ForegroundColor Yellow
try {
    $dockerVersion = docker version --format json 2>$null | ConvertFrom-Json
    if ($dockerVersion) {
        Write-Host "✅ Docker is running!" -ForegroundColor Green
        Write-Host "   Client Version: $($dockerVersion.Client.Version)" -ForegroundColor Cyan
        Write-Host "   Server Version: $($dockerVersion.Server.Version)" -ForegroundColor Cyan
        
        # Test Docker with a simple command
        Write-Host "`n🧪 Testing Docker..." -ForegroundColor Yellow
        docker run --rm hello-world > $null 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ Docker test successful!" -ForegroundColor Green
            Write-Host "`n🚀 Docker is ready for deployment!" -ForegroundColor Cyan
            Write-Host "You can now run: .\deploy-azure.ps1" -ForegroundColor White
        } else {
            Write-Host "⚠️ Docker test failed, but Docker is running" -ForegroundColor Yellow
            Write-Host "This might be due to network issues or permissions" -ForegroundColor Yellow
        }
    }
} catch {
    Write-Host "❌ Docker is not running!" -ForegroundColor Red
    
    # Try to start Docker Desktop
    Write-Host "`n🔧 Attempting to start Docker Desktop..." -ForegroundColor Yellow
    
    $dockerDesktopPaths = @(
        "${env:ProgramFiles}\Docker\Docker\Docker Desktop.exe",
        "${env:ProgramFiles(x86)}\Docker\Docker\Docker Desktop.exe",
        "${env:LOCALAPPDATA}\Programs\Docker\Docker\Docker Desktop.exe"
    )
    
    $dockerDesktopPath = $null
    foreach ($path in $dockerDesktopPaths) {
        if (Test-Path $path) {
            $dockerDesktopPath = $path
            break
        }
    }
    
    if ($dockerDesktopPath) {
        Write-Host "Starting Docker Desktop from: $dockerDesktopPath" -ForegroundColor Cyan
        Start-Process -FilePath $dockerDesktopPath
        
        Write-Host "`n⏳ Waiting for Docker to start..." -ForegroundColor Yellow
        Write-Host "This may take 30-60 seconds..." -ForegroundColor Gray
        
        # Wait for Docker to start (max 2 minutes)
        $timeout = 120
        $elapsed = 0
        $started = $false
        
        while ($elapsed -lt $timeout) {
            Start-Sleep -Seconds 5
            $elapsed += 5
            
            try {
                docker version > $null 2>&1
                if ($LASTEXITCODE -eq 0) {
                    $started = $true
                    break
                }
            } catch {
                # Continue waiting
            }
            
            Write-Host "." -NoNewline -ForegroundColor Gray
        }
        
        Write-Host ""
        
        if ($started) {
            Write-Host "✅ Docker started successfully!" -ForegroundColor Green
            Write-Host "`n🚀 Docker is ready for deployment!" -ForegroundColor Cyan
            Write-Host "You can now run: .\deploy-azure.ps1" -ForegroundColor White
        } else {
            Write-Host "⏰ Docker is taking longer than expected to start" -ForegroundColor Yellow
            Write-Host "`n📝 Manual steps:" -ForegroundColor Yellow
            Write-Host "1. Wait for Docker Desktop to fully load (check system tray)" -ForegroundColor White
            Write-Host "2. Look for the Docker whale icon in your system tray" -ForegroundColor White
            Write-Host "3. When it shows 'Docker Desktop is running', try deployment again" -ForegroundColor White
            Write-Host "4. Run: docker version" -ForegroundColor White
            Write-Host "5. If successful, run: .\deploy-azure.ps1" -ForegroundColor White
        }
    } else {
        Write-Host "❌ Docker Desktop not found!" -ForegroundColor Red
        Write-Host "`n📝 Manual steps:" -ForegroundColor Yellow
        Write-Host "1. Open Docker Desktop manually from Start Menu" -ForegroundColor White
        Write-Host "2. Wait for it to start completely" -ForegroundColor White
        Write-Host "3. Run this script again" -ForegroundColor White
        Write-Host "`nOr install Docker Desktop from:" -ForegroundColor Yellow
        Write-Host "https://www.docker.com/products/docker-desktop" -ForegroundColor Cyan
    }
}

Write-Host "`n📋 Troubleshooting Tips:" -ForegroundColor Yellow
Write-Host "• Make sure you have Windows Subsystem for Linux (WSL2) enabled" -ForegroundColor White
Write-Host "• Restart your computer if Docker won't start" -ForegroundColor White
Write-Host "• Check Windows Updates are installed" -ForegroundColor White
Write-Host "• Run PowerShell as Administrator if needed" -ForegroundColor White