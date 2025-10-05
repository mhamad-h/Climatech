# Azure Deployment Script for Climatech - Fixed Version
param(
    [string]$ResourceGroup = "climatech-rg",
    [string]$Location = "East US",
    [string]$RegistryName = "climatechregistry$(Get-Random -Minimum 1000 -Maximum 9999)"
)

Write-Host "🌦️ Deploying Climatech to Azure Container Apps" -ForegroundColor Cyan

# Check prerequisites
if (!(Get-Command az -ErrorAction SilentlyContinue)) {
    Write-Error "Azure CLI not found. Install from https://aka.ms/installazurecliwindows"
    exit 1
}

try {
    docker version | Out-Null
} catch {
    Write-Error "Docker not running. Start Docker Desktop first."
    exit 1
}

# Check Azure login
Write-Host "Checking Azure login..." -ForegroundColor Yellow
$account = az account show 2>$null | ConvertFrom-Json
if (!$account) {
    Write-Host "Logging into Azure..." -ForegroundColor Yellow
    az login
    $account = az account show | ConvertFrom-Json
}

Write-Host "Using Azure account: $($account.user.name)" -ForegroundColor Green
Write-Host "Using subscription: $($account.name)" -ForegroundColor Green

# Variables
$containerAppEnv = "climatech-env"
$backendApp = "climatech-backend"
$frontendApp = "climatech-frontend"

Write-Host "`nDeployment Configuration:" -ForegroundColor Yellow
Write-Host "  Resource Group: $ResourceGroup"
Write-Host "  Location: $Location"
Write-Host "  Registry: $RegistryName"

$confirmation = Read-Host "`nProceed with deployment? (y/N)"
if ($confirmation -ne 'y') {
    Write-Host "Deployment cancelled."
    exit 0
}

Write-Host "`n1. Creating Azure resources..." -ForegroundColor Yellow

# Create resource group
az group create --name $ResourceGroup --location $Location

# Create container registry
az acr create --resource-group $ResourceGroup --name $RegistryName --sku Basic --admin-enabled true

# Create container apps environment
az containerapp env create --name $containerAppEnv --resource-group $ResourceGroup --location $Location

Write-Host "`n2. Building and pushing images..." -ForegroundColor Yellow

# Get ACR details
$acrLoginServer = az acr show --name $RegistryName --resource-group $ResourceGroup --query loginServer --output tsv
az acr login --name $RegistryName

# Build and push backend
Write-Host "Building backend..."
docker build -t "${acrLoginServer}/climatech-backend:latest" -f infra/Dockerfile.backend ./backend
docker push "${acrLoginServer}/climatech-backend:latest"

# Build and push frontend
Write-Host "Building frontend..."
docker build -t "${acrLoginServer}/climatech-frontend:latest" -f infra/Dockerfile.frontend ./client
docker push "${acrLoginServer}/climatech-frontend:latest"

Write-Host "`n3. Deploying applications..." -ForegroundColor Yellow

# Get ACR credentials
$acrUsername = az acr credential show --name $RegistryName --resource-group $ResourceGroup --query username --output tsv
$acrPassword = az acr credential show --name $RegistryName --resource-group $ResourceGroup --query passwords[0].value --output tsv

# Deploy backend
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
    --env-vars "BACKEND_HOST=0.0.0.0" "BACKEND_PORT=8000" "ENVIRONMENT=production" `
    --cpu 1.0 `
    --memory 2Gi `
    --min-replicas 1 `
    --max-replicas 3

# Get backend URL
$backendUrl = az containerapp show --name $backendApp --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn --output tsv
$backendApiUrl = "https://$backendUrl/api"

# Deploy frontend
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
    --env-vars "VITE_API_URL=$backendApiUrl" `
    --cpu 0.5 `
    --memory 1Gi `
    --min-replicas 1 `
    --max-replicas 2

# Get frontend URL
$frontendUrl = az containerapp show --name $frontendApp --resource-group $ResourceGroup --query properties.configuration.ingress.fqdn --output tsv

# Update CORS
az containerapp update `
    --name $backendApp `
    --resource-group $ResourceGroup `
    --set-env-vars "CORS_ORIGINS=https://$frontendUrl"

Write-Host "`n✅ Deployment completed!" -ForegroundColor Green
Write-Host "Frontend: https://$frontendUrl" -ForegroundColor Cyan
Write-Host "Backend:  https://$backendUrl" -ForegroundColor Cyan
Write-Host "API Docs: https://$backendUrl/docs" -ForegroundColor Cyan