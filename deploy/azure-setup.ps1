# Azure Container Apps Deployment Script for Climatech

# Variables - UPDATE THESE VALUES
$resourceGroup = "climatech-rg"
$location = "East US"
$containerAppEnv = "climatech-env"
$backendApp = "climatech-backend"
$frontendApp = "climatech-frontend"
$registryName = "climatechregistry$(Get-Random -Minimum 1000 -Maximum 9999)"

Write-Host "Creating Azure resources for Climatech deployment..." -ForegroundColor Green

# Create resource group
Write-Host "Creating resource group: $resourceGroup" -ForegroundColor Yellow
az group create --name $resourceGroup --location $location

# Create Azure Container Registry
Write-Host "Creating Azure Container Registry: $registryName" -ForegroundColor Yellow
az acr create --resource-group $resourceGroup --name $registryName --sku Basic --admin-enabled true

# Get ACR login server
$acrLoginServer = az acr show --name $registryName --resource-group $resourceGroup --query loginServer --output tsv

# Create Container Apps Environment
Write-Host "Creating Container Apps Environment: $containerAppEnv" -ForegroundColor Yellow
az containerapp env create --name $containerAppEnv --resource-group $resourceGroup --location $location

Write-Host "Azure resources created successfully!" -ForegroundColor Green
Write-Host "Container Registry: $acrLoginServer" -ForegroundColor Cyan
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Build and push Docker images to ACR" -ForegroundColor White
Write-Host "2. Deploy container apps" -ForegroundColor White