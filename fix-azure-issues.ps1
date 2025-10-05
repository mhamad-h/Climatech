# Fix Azure Deployment Issues
# This script will fix the problems and deploy properly

Write-Host "🔧 Fixing Azure Deployment Issues" -ForegroundColor Cyan

# Step 1: Check Docker Desktop
Write-Host "`n1. Checking Docker Desktop..." -ForegroundColor Yellow
$dockerProcess = Get-Process "Docker Desktop" -ErrorAction SilentlyContinue
if (!$dockerProcess) {
    Write-Host "Starting Docker Desktop..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Write-Host "Waiting for Docker to start (30 seconds)..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
}

# Wait for Docker to be ready
$retries = 0
do {
    $retries++
    Write-Host "Testing Docker connection (attempt $retries)..." -ForegroundColor Yellow
    $dockerWorking = $false
    try {
        docker version | Out-Null
        $dockerWorking = $true
        Write-Host "✅ Docker is working!" -ForegroundColor Green
    } catch {
        if ($retries -lt 6) {
            Write-Host "Waiting for Docker... (10 more seconds)" -ForegroundColor Yellow
            Start-Sleep -Seconds 10
        }
    }
} while (!$dockerWorking -and $retries -lt 6)

if (!$dockerWorking) {
    Write-Error "❌ Docker is not working. Please start Docker Desktop manually and try again."
    exit 1
}

# Step 2: Register Azure Resource Providers
Write-Host "`n2. Registering Azure resource providers..." -ForegroundColor Yellow
Write-Host "Registering Microsoft.ContainerRegistry..." -ForegroundColor Cyan
az provider register --namespace Microsoft.ContainerRegistry --wait

Write-Host "Registering Microsoft.App..." -ForegroundColor Cyan  
az provider register --namespace Microsoft.App --wait

Write-Host "Registering Microsoft.OperationalInsights..." -ForegroundColor Cyan
az provider register --namespace Microsoft.OperationalInsights --wait

# Step 3: Verify registrations
Write-Host "`n3. Verifying registrations..." -ForegroundColor Yellow
$containerRegistryStatus = az provider show --namespace Microsoft.ContainerRegistry --query registrationState --output tsv
$appStatus = az provider show --namespace Microsoft.App --query registrationState --output tsv

Write-Host "Microsoft.ContainerRegistry: $containerRegistryStatus" -ForegroundColor Cyan
Write-Host "Microsoft.App: $appStatus" -ForegroundColor Cyan

if ($containerRegistryStatus -ne "Registered" -or $appStatus -ne "Registered") {
    Write-Host "❌ Resource providers not fully registered. Please wait a few minutes and try again." -ForegroundColor Red
    exit 1
}

Write-Host "✅ All resource providers registered!" -ForegroundColor Green
Write-Host "`n🎯 Now you can run the deployment script:" -ForegroundColor Yellow
Write-Host ".\deploy-azure.ps1" -ForegroundColor White