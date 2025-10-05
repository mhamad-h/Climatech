#!/usr/bin/env pwsh

<#
.SYNOPSIS
Smart deployment script that handles dynamic backend URLs
#>

param(
    [string]$Location = "eastus",
    [string]$SubscriptionId = "",
    [switch]$Force
)

try {
    # Configuration
    $ResourceGroup = "climatech-rg-$(Get-Date -Format 'MMdd')"
    $RegistryName = "climatechregistry$(Get-Random -Min 1000 -Max 9999)"
    $backendImageName = "climatech-backend:latest"
    $frontendImageName = "climatech-frontend:latest"

    Write-Host "=== Smart Climatech Deployment ===" -ForegroundColor Green
    Write-Host "Location: $Location" -ForegroundColor Cyan
    Write-Host "Resource Group: $ResourceGroup" -ForegroundColor Cyan
    
    # Step 1: Login and set subscription
    Write-Host "`n1. Checking Azure login..." -ForegroundColor Yellow
    $accountInfo = az account show 2>$null | ConvertFrom-Json
    if (-not $accountInfo) {
        Write-Host "Please login to Azure..."
        az login
        $accountInfo = az account show | ConvertFrom-Json
    }
    
    if ($SubscriptionId) {
        az account set --subscription $SubscriptionId
    }
    
    Write-Host "Using subscription: $($accountInfo.name)" -ForegroundColor Green

    # Step 2: Create resource group
    Write-Host "`n2. Creating resource group..." -ForegroundColor Yellow
    az group create --name $ResourceGroup --location $Location --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to create resource group" }

    # Step 3: Create container registry
    Write-Host "`n3. Creating container registry..." -ForegroundColor Yellow
    az acr create --name $RegistryName --resource-group $ResourceGroup --sku Basic --admin-enabled --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to create container registry" }
    
    $acrLoginServer = az acr show --name $RegistryName --query "loginServer" --output tsv

    # Step 4: Build and push backend first
    Write-Host "`n4. Building and pushing backend..." -ForegroundColor Yellow
    az acr build --registry $RegistryName --image $backendImageName ./backend --file ./infra/Dockerfile.backend --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to build backend image" }

    # Step 5: Deploy backend container to get its URL
    Write-Host "`n5. Deploying backend container..." -ForegroundColor Yellow
    $backendDns = "climatech-backend-$(Get-Random -Min 1000 -Max 9999)"
    $acrCredentials = az acr credential show --name $RegistryName --resource-group $ResourceGroup | ConvertFrom-Json
    $acrUsername = $acrCredentials.username
    $acrPassword = $acrCredentials.passwords[0].value
    
    az container create `
        --name "climatech-backend" `
        --resource-group $ResourceGroup `
        --location $Location `
        --image "$acrLoginServer/$backendImageName" `
        --os-type Linux `
        --registry-login-server $acrLoginServer `
        --registry-username $acrUsername `
        --registry-password $acrPassword `
        --dns-name-label $backendDns `
        --ports 8000 `
        --environment-variables "BACKEND_HOST=0.0.0.0" "BACKEND_PORT=8000" "ENVIRONMENT=production" "CORS_ORIGINS=*" `
        --cpu 1 `
        --memory 2 `
        --output none
    
    if ($LASTEXITCODE -ne 0) { throw "Failed to deploy backend container" }

    # Step 6: Get backend URL and wait for it to be ready
    Write-Host "`n6. Getting backend URL..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15  # Wait for container to be ready
    $backendInfo = az container show --name "climatech-backend" --resource-group $ResourceGroup | ConvertFrom-Json
    $backendUrl = $backendInfo.ipAddress.fqdn
    $backendApiUrl = "http://${backendUrl}:8000/api"
    
    Write-Host "Backend URL: http://${backendUrl}:8000" -ForegroundColor Cyan
    Write-Host "API URL: $backendApiUrl" -ForegroundColor Cyan

    # Step 7: Update frontend config with backend URL and build
    Write-Host "`n7. Updating frontend config and building..." -ForegroundColor Yellow
    
    # Create a temporary .env.production file with the correct API URL
    $envContent = "VITE_API_URL=$backendApiUrl"
    Set-Content -Path "./client/.env.production" -Value $envContent -Force
    Write-Host "Created .env.production with: $envContent" -ForegroundColor Green

    # Build frontend with the correct backend URL
    az acr build --registry $RegistryName --image $frontendImageName ./client --file ./infra/Dockerfile.frontend --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to build frontend image" }

    # Step 8: Deploy frontend container
    Write-Host "`n8. Deploying frontend container..." -ForegroundColor Yellow
    $frontendDns = "climatech-frontend-$(Get-Random -Min 1000 -Max 9999)"
    
    az container create `
        --name "climatech-frontend" `
        --resource-group $ResourceGroup `
        --location $Location `
        --image "$acrLoginServer/$frontendImageName" `
        --os-type Linux `
        --registry-login-server $acrLoginServer `
        --registry-username $acrUsername `
        --registry-password $acrPassword `
        --dns-name-label $frontendDns `
        --ports 80 `
        --cpu 0.5 `
        --memory 1 `
        --output none
    
    if ($LASTEXITCODE -ne 0) { throw "Failed to deploy frontend container" }

    # Step 9: Get frontend URL
    Write-Host "`n9. Getting frontend URL..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10  # Wait for container to be ready
    $frontendInfo = az container show --name "climatech-frontend" --resource-group $ResourceGroup | ConvertFrom-Json
    $frontendUrl = $frontendInfo.ipAddress.fqdn

    Write-Host "`nDeployment completed successfully!" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "`nYour Geoclime Application URLs:" -ForegroundColor Cyan
    Write-Host "  Frontend:    http://$frontendUrl" -ForegroundColor White
    Write-Host "  Backend:     http://${backendUrl}:8000" -ForegroundColor White
    Write-Host "  API Docs:    http://${backendUrl}:8000/docs" -ForegroundColor White
    Write-Host "  Health:      http://${backendUrl}:8000/health" -ForegroundColor White
    
    Write-Host "`nFor your domain (geoclime.earth):" -ForegroundColor Yellow
    Write-Host "  Add A record: @ -> $(az container show --name "climatech-frontend" --resource-group $ResourceGroup --query "ipAddress.ip" --output tsv)" -ForegroundColor White
    Write-Host "  Add CNAME: www -> $frontendUrl" -ForegroundColor White
    
    Write-Host "`nResource Details:" -ForegroundColor Yellow
    Write-Host "  Resource Group: $ResourceGroup" -ForegroundColor White
    Write-Host "  Registry:       $RegistryName" -ForegroundColor White
    Write-Host "  Location:       $Location" -ForegroundColor White
    
    Write-Host "`nTo update deployment with code changes:" -ForegroundColor Yellow
    Write-Host "  .\deploy-smart.ps1" -ForegroundColor White
    
    Write-Host "`nTo delete everything:" -ForegroundColor Yellow
    Write-Host "  az group delete --name $ResourceGroup --yes --no-wait" -ForegroundColor White

} catch {
    Write-Error "Deployment failed: $_"
    Write-Host "`nCleanup command (if resources were created):" -ForegroundColor Yellow
    Write-Host "az group delete --name $ResourceGroup --yes --no-wait" -ForegroundColor White
    exit 1
}