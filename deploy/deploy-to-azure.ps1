# Complete Azure Deployment Script for Climatech
# This script will deploy the entire application to Azure Container Apps

param(
    [Parameter(Mandatory=$false)]
    [string]$ResourceGroup = "climatech-rg",
    
    [Parameter(Mandatory=$false)]
    [string]$Location = "East US",
    
    [Parameter(Mandatory=$false)]
    [string]$RegistryName = "climatechregistry$(Get-Random -Minimum 1000 -Maximum 9999)"
)

Write-Host "🌦️  Deploying Climatech to Azure Container Apps" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Check if Azure CLI is installed
if (!(Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI is not installed. Please install it from https://aka.ms/installazurecliwindows"
    exit 1
}

# Check if Docker is running
try {
    docker version | Out-Null
} catch {
    Write-Error "Docker is not running. Please start Docker Desktop."
    exit 1
}

# Login check
Write-Host "Checking Azure login..." -ForegroundColor Yellow
$account = az account show 2>$null | ConvertFrom-Json
if (!$account) {
    Write-Host "Please login to Azure..." -ForegroundColor Yellow
    az login
}

Write-Host "Using Azure account: $($account.user.name)" -ForegroundColor Green
Write-Host "Using subscription: $($account.name)" -ForegroundColor Green

# Variables
$containerAppEnv = "climatech-env"
$backendApp = "climatech-backend"
$frontendApp = "climatech-frontend"

Write-Host "`n📋 Deployment Configuration:" -ForegroundColor Yellow
Write-Host "  Resource Group: $ResourceGroup" -ForegroundColor White
Write-Host "  Location: $Location" -ForegroundColor White
Write-Host "  Registry: $RegistryName" -ForegroundColor White

$confirmation = Read-Host "`nProceed with deployment? (y/N)"
if ($confirmation -ne 'y' -and $confirmation -ne 'Y') {
    Write-Host "Deployment cancelled." -ForegroundColor Red
    exit 0
}

try {
    # Step 1: Create Resource Group
    Write-Host "`n🔧 Creating resource group..." -ForegroundColor Yellow
    az group create --name $ResourceGroup --location $Location --output table

    # Step 2: Create Azure Container Registry
    Write-Host "`n🐳 Creating Azure Container Registry..." -ForegroundColor Yellow
    az acr create --resource-group $ResourceGroup --name $RegistryName --sku Basic --admin-enabled true --output table

    # Step 3: Create Container Apps Environment
    Write-Host "`n🌐 Creating Container Apps Environment..." -ForegroundColor Yellow
    az containerapp env create --name $containerAppEnv --resource-group $ResourceGroup --location $Location --output table

    # Step 4: Build and Push Images
    Write-Host "`n🏗️ Building and pushing Docker images..." -ForegroundColor Yellow
    
    $acrLoginServer = az acr show --name $RegistryName --resource-group $ResourceGroup --query loginServer --output tsv
    az acr login --name $RegistryName

    # Build backend
    Write-Host "Building backend image..." -ForegroundColor Cyan
    docker build -t "${acrLoginServer}/climatech-backend:latest" -f infra/Dockerfile.backend ./backend
    docker push "${acrLoginServer}/climatech-backend:latest"

    # Build frontend  
    Write-Host "Building frontend image..." -ForegroundColor Cyan
    docker build -t "${acrLoginServer}/climatech-frontend:latest" -f infra/Dockerfile.frontend ./client
    docker push "${acrLoginServer}/climatech-frontend:latest"

    # Step 5: Get ACR Credentials
    $acrUsername = az acr credential show --name $RegistryName --resource-group $ResourceGroup --query username --output tsv
    $acrPassword = az acr credential show --name $RegistryName --resource-group $ResourceGroup --query passwords[0].value --output tsv

    # Step 6: Deploy Backend
    Write-Host "`n🚀 Deploying backend container app..." -ForegroundColor Yellow
    az containerapp create `
        --name $backendApp `
        --resource-group $ResourceGroup `
        --environment $containerAppEnv `
        --image "${acrLoginServer}/climatech-backend:latest" `
        --target-port 8000 `
        --ingress external `
        --registry-server $acrLoginServer `
        --registry-username $acrUsername `
        --registry-password $acrPassword `
        --env-vars "BACKEND_HOST=0.0.0.0" "BACKEND_PORT=8000" "ENVIRONMENT=production" "CORS_ORIGINS=*" `
        --cpu 1.0 `
        --memory 2Gi `
        --min-replicas 1 `
        --max-replicas 3 `
        --output table

    # Get backend URL
    $backendUrl = az containerapp show --name $backendApp --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn --output tsv
    $backendApiUrl = "https://$backendUrl/api"

    # Step 7: Deploy Frontend
    Write-Host "`n🎨 Deploying frontend container app..." -ForegroundColor Yellow
    az containerapp create `
        --name $frontendApp `
        --resource-group $ResourceGroup `
        --environment $containerAppEnv `
        --image "${acrLoginServer}/climatech-frontend:latest" `
        --target-port 80 `
        --ingress external `
        --registry-server $acrLoginServer `
        --registry-username $acrUsername `
        --registry-password $acrPassword `
        --env-vars "VITE_API_URL=$backendApiUrl" "NODE_ENV=production" `
        --cpu 0.5 `
        --memory 1Gi `
        --min-replicas 1 `
        --max-replicas 2 `
        --output table

    # Get frontend URL
    $frontendUrl = az containerapp show --name $frontendApp --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn --output tsv

    # Step 8: Update CORS settings
    Write-Host "`n⚙️ Updating CORS settings..." -ForegroundColor Yellow
    az containerapp update `
        --name $backendApp `
        --resource-group $ResourceGroup `
        --set-env-vars "CORS_ORIGINS=https://$frontendUrl,https://$backendUrl" `
        --output table

    # Success!
    Write-Host "`n✅ Deployment completed successfully!" -ForegroundColor Green
    Write-Host "===========================================" -ForegroundColor Green
    Write-Host "`n🌦️  Your Climatech Application is live:" -ForegroundColor Cyan
    Write-Host "  🌐 Frontend:  https://$frontendUrl" -ForegroundColor White
    Write-Host "  🔧 Backend:   https://$backendUrl" -ForegroundColor White  
    Write-Host "  📚 API Docs:  https://$backendUrl/docs" -ForegroundColor White
    Write-Host "  📊 Health:    https://$backendUrl/health" -ForegroundColor White
    Write-Host "`n📋 Resource Information:" -ForegroundColor Yellow
    Write-Host "  Resource Group: $ResourceGroup" -ForegroundColor White
    Write-Host "  Location: $Location" -ForegroundColor White
    Write-Host "  Container Registry: $RegistryName" -ForegroundColor White
    Write-Host "`n🎯 Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Test your application at the frontend URL" -ForegroundColor White
    Write-Host "  2. Set up custom domain name (optional)" -ForegroundColor White
    Write-Host "  3. Configure monitoring and alerts" -ForegroundColor White
    Write-Host "  4. Set up CI/CD pipeline for automatic deployments" -ForegroundColor White

} catch {
    Write-Error "Deployment failed: $_"
    Write-Host "`n🧹 Cleanup commands (if needed):" -ForegroundColor Yellow
    Write-Host "  az group delete --name $ResourceGroup --yes --no-wait" -ForegroundColor White
    exit 1
}