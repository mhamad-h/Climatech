#!/usr/bin/env pwsh

<#
.SYNOPSIS
Deploy Geoclime with STABLE URLs using Azure Container Apps
This solves the dynamic URL problem by using custom domain-ready endpoints
#>

param(
    [string]$Location = "eastus",
    [string]$AppName = "geoclime",
    [switch]$Force
)

try {
    # Configuration with stable naming
    $ResourceGroup = "geoclime-production"
    $RegistryName = "geoclimeregistry$(Get-Random -Min 100 -Max 999)"
    $ContainerAppEnv = "geoclime-env"
    $backendAppName = "geoclime-api"
    $frontendAppName = "geoclime-web"

    Write-Host "=== Geoclime Stable Deployment ===" -ForegroundColor Green
    Write-Host "This deployment creates STABLE URLs that won't change!" -ForegroundColor Cyan
    Write-Host "Perfect for your geoclime.earth domain!" -ForegroundColor Cyan
    
    # Step 1: Login check
    Write-Host "`n1. Checking Azure login..." -ForegroundColor Yellow
    $accountInfo = az account show 2>$null | ConvertFrom-Json
    if (-not $accountInfo) {
        Write-Host "Please login to Azure..."
        az login
        $accountInfo = az account show | ConvertFrom-Json
    }
    Write-Host "Using subscription: $($accountInfo.name)" -ForegroundColor Green

    # Step 2: Create resource group
    Write-Host "`n2. Creating production resource group..." -ForegroundColor Yellow
    az group create --name $ResourceGroup --location $Location --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to create resource group" }

    # Step 3: Create container registry
    Write-Host "`n3. Creating container registry..." -ForegroundColor Yellow
    az acr create --name $RegistryName --resource-group $ResourceGroup --sku Basic --admin-enabled --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to create container registry" }
    
    $acrLoginServer = az acr show --name $RegistryName --query "loginServer" --output tsv
    $acrCredentials = az acr credential show --name $RegistryName --resource-group $ResourceGroup | ConvertFrom-Json

    # Step 4: Build images locally (to avoid ACR Tasks issues)
    Write-Host "`n4. Building images locally..." -ForegroundColor Yellow
    
    # Login to Docker
    echo $acrCredentials.passwords[0].value | docker login $acrLoginServer --username $acrCredentials.username --password-stdin
    if ($LASTEXITCODE -ne 0) { throw "Failed to login to Docker registry" }

    # Build backend
    $backendImage = "$acrLoginServer/geoclime-backend:latest"
    docker build -t $backendImage -f ./infra/Dockerfile.backend ./backend
    if ($LASTEXITCODE -ne 0) { throw "Failed to build backend image" }
    docker push $backendImage
    if ($LASTEXITCODE -ne 0) { throw "Failed to push backend image" }

    # Step 5: Create Container Apps Environment
    Write-Host "`n5. Creating Container Apps environment..." -ForegroundColor Yellow
    az containerapp env create `
        --name $ContainerAppEnv `
        --resource-group $ResourceGroup `
        --location $Location `
        --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to create Container Apps environment" }

    # Step 6: Deploy backend with STABLE URL
    Write-Host "`n6. Deploying backend with stable URL..." -ForegroundColor Yellow
    az containerapp create `
        --name $backendAppName `
        --resource-group $ResourceGroup `
        --environment $ContainerAppEnv `
        --image $backendImage `
        --registry-server $acrLoginServer `
        --registry-username $acrCredentials.username `
        --registry-password $acrCredentials.passwords[0].value `
        --target-port 8000 `
        --ingress external `
        --min-replicas 1 `
        --max-replicas 2 `
        --cpu 1.0 `
        --memory 2.0Gi `
        --env-vars "BACKEND_HOST=0.0.0.0" "BACKEND_PORT=8000" "ENVIRONMENT=production" "CORS_ORIGINS=*" `
        --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to deploy backend app" }

    # Step 7: Get stable backend URL
    Write-Host "`n7. Getting stable backend URL..." -ForegroundColor Yellow
    $backendApp = az containerapp show --name $backendAppName --resource-group $ResourceGroup | ConvertFrom-Json
    $backendUrl = "https://$($backendApp.properties.configuration.ingress.fqdn)"
    $backendApiUrl = "$backendUrl/api"
    
    Write-Host "Stable Backend URL: $backendUrl" -ForegroundColor Cyan
    Write-Host "Stable API URL: $backendApiUrl" -ForegroundColor Cyan

    # Step 8: Update frontend config with stable backend URL
    Write-Host "`n8. Configuring frontend with stable backend URL..." -ForegroundColor Yellow
    $envContent = "VITE_API_URL=$backendApiUrl"
    Set-Content -Path "./client/.env.production" -Value $envContent -Force
    Write-Host "Frontend configured with: $backendApiUrl" -ForegroundColor Green

    # Step 9: Build and deploy frontend
    Write-Host "`n9. Building and deploying frontend..." -ForegroundColor Yellow
    $frontendImage = "$acrLoginServer/geoclime-frontend:latest"
    docker build -t $frontendImage -f ./infra/Dockerfile.frontend ./client
    if ($LASTEXITCODE -ne 0) { throw "Failed to build frontend image" }
    docker push $frontendImage
    if ($LASTEXITCODE -ne 0) { throw "Failed to push frontend image" }

    # Deploy frontend with STABLE URL
    az containerapp create `
        --name $frontendAppName `
        --resource-group $ResourceGroup `
        --environment $ContainerAppEnv `
        --image $frontendImage `
        --registry-server $acrLoginServer `
        --registry-username $acrCredentials.username `
        --registry-password $acrCredentials.passwords[0].value `
        --target-port 80 `
        --ingress external `
        --min-replicas 1 `
        --max-replicas 3 `
        --cpu 0.5 `
        --memory 1.0Gi `
        --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to deploy frontend app" }

    # Step 10: Get stable frontend URL
    Write-Host "`n10. Getting stable frontend URL..." -ForegroundColor Yellow
    $frontendApp = az containerapp show --name $frontendAppName --resource-group $ResourceGroup | ConvertFrom-Json
    $frontendUrl = "https://$($frontendApp.properties.configuration.ingress.fqdn)"

    # Cleanup local images
    docker rmi $backendImage -f 2>$null
    docker rmi $frontendImage -f 2>$null

    Write-Host "`nDeployment completed successfully!" -ForegroundColor Green
    Write-Host "=================================================================" -ForegroundColor Green
    Write-Host "`nYour Geoclime Application - STABLE URLS:" -ForegroundColor Cyan
    Write-Host "  Frontend:  $frontendUrl" -ForegroundColor White
    Write-Host "  Backend:   $backendUrl" -ForegroundColor White
    Write-Host "  API Docs:  $backendUrl/docs" -ForegroundColor White
    Write-Host "  Health:    $backendUrl/health" -ForegroundColor White
    
    Write-Host "`nDNS Setup for geoclime.earth:" -ForegroundColor Yellow
    $frontendDomain = $frontendApp.properties.configuration.ingress.fqdn
    $backendDomain = $backendApp.properties.configuration.ingress.fqdn
    Write-Host "  1. Add CNAME record: @ -> $frontendDomain" -ForegroundColor White
    Write-Host "  2. Add CNAME record: www -> $frontendDomain" -ForegroundColor White
    Write-Host "  3. Add CNAME record: api -> $backendDomain" -ForegroundColor White
    
    Write-Host "`nSTABLE URLS - These URLs will NEVER change!" -ForegroundColor Green
    Write-Host "Auto-scaling enabled" -ForegroundColor Green
    Write-Host "HTTPS included automatically" -ForegroundColor Green
    Write-Host "Ready for custom domain (geoclime.earth)" -ForegroundColor Green
    
    Write-Host "`nTo update with new code:" -ForegroundColor Yellow
    Write-Host "  Just rebuild and push images - URLs stay the same!" -ForegroundColor White
    
    Write-Host "`nEstimated Cost: 10-20 USD/month (pay per use)" -ForegroundColor Green
    Write-Host "`nTo delete everything:" -ForegroundColor Yellow
    Write-Host "  az group delete --name $ResourceGroup --yes --no-wait" -ForegroundColor White

} catch {
    Write-Error "Deployment failed: $_"
    Write-Host "`nCleanup command:" -ForegroundColor Yellow
    Write-Host "az group delete --name $ResourceGroup --yes --no-wait" -ForegroundColor White
    exit 1
}