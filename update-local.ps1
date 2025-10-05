#!/usr/bin/env pwsh

<#
.SYNOPSIS
Update existing deployment with new code (local build method)
#>

param(
    [string]$ResourceGroup = "climatech-app-678"
)

try {
    Write-Host "=== Climatech Local Build Update ===" -ForegroundColor Green
    Write-Host "Resource Group: $ResourceGroup" -ForegroundColor Cyan

    # Get existing resources
    Write-Host "`n1. Getting existing resources..." -ForegroundColor Yellow
    $registries = az acr list --resource-group $ResourceGroup | ConvertFrom-Json
    if ($registries.Count -eq 0) { throw "No container registry found" }
    $RegistryName = $registries[0].name
    $acrLoginServer = $registries[0].loginServer

    Write-Host "Registry: $RegistryName" -ForegroundColor Green

    # Get ACR credentials
    Write-Host "`n2. Getting registry credentials..." -ForegroundColor Yellow
    $acrCredentials = az acr credential show --name $RegistryName --resource-group $ResourceGroup | ConvertFrom-Json
    $acrUsername = $acrCredentials.username
    $acrPassword = $acrCredentials.passwords[0].value

    # Login to Docker registry
    Write-Host "`n3. Logging into Docker registry..." -ForegroundColor Yellow
    echo $acrPassword | docker login $acrLoginServer --username $acrUsername --password-stdin
    if ($LASTEXITCODE -ne 0) { throw "Failed to login to Docker registry" }

    # Build backend locally
    Write-Host "`n4. Building backend locally..." -ForegroundColor Yellow
    $backendImage = "$acrLoginServer/climatech-backend:latest"
    docker build -t $backendImage -f ./infra/Dockerfile.backend ./backend
    if ($LASTEXITCODE -ne 0) { throw "Failed to build backend image" }

    # Push backend image
    Write-Host "`n5. Pushing backend image..." -ForegroundColor Yellow
    docker push $backendImage
    if ($LASTEXITCODE -ne 0) { throw "Failed to push backend image" }

    # Build frontend locally
    Write-Host "`n6. Building frontend locally..." -ForegroundColor Yellow
    $frontendImage = "$acrLoginServer/climatech-frontend:latest"
    docker build -t $frontendImage -f ./infra/Dockerfile.frontend ./client
    if ($LASTEXITCODE -ne 0) { throw "Failed to build frontend image" }

    # Push frontend image
    Write-Host "`n7. Pushing frontend image..." -ForegroundColor Yellow
    docker push $frontendImage
    if ($LASTEXITCODE -ne 0) { throw "Failed to push frontend image" }

    # Restart containers to use new images
    Write-Host "`n8. Restarting containers..." -ForegroundColor Yellow
    az container restart --name "climatech-backend" --resource-group $ResourceGroup --output none
    az container restart --name "climatech-frontend" --resource-group $ResourceGroup --output none

    # Wait and get URLs
    Start-Sleep -Seconds 15
    $backendInfo = az container show --name "climatech-backend" --resource-group $ResourceGroup | ConvertFrom-Json
    $frontendInfo = az container show --name "climatech-frontend" --resource-group $ResourceGroup | ConvertFrom-Json
    
    $backendUrl = $backendInfo.ipAddress.fqdn
    $frontendUrl = $frontendInfo.ipAddress.fqdn

    Write-Host "`nUpdate completed successfully!" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "`nYour Updated Geoclime URLs:" -ForegroundColor Cyan
    Write-Host "  Frontend:    http://$frontendUrl" -ForegroundColor White
    Write-Host "  Backend:     http://${backendUrl}:8000" -ForegroundColor White
    Write-Host "  API Docs:    http://${backendUrl}:8000/docs" -ForegroundColor White
    Write-Host "  Health:      http://${backendUrl}:8000/health" -ForegroundColor White

    # Cleanup local images to save space
    Write-Host "`n9. Cleaning up local images..." -ForegroundColor Yellow
    docker rmi $backendImage -f 2>$null
    docker rmi $frontendImage -f 2>$null

} catch {
    Write-Error "Update failed: $_"
    exit 1
}