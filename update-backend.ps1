#!/usr/bin/env pwsh

<#
.SYNOPSIS
Update just the backend with CORS fix
#>

try {
    Write-Host "=== Updating Backend with CORS Fix ===" -ForegroundColor Green
    
    # Find your existing registry
    $registries = az acr list --query "[?contains(name, 'climatech') || contains(name, 'geoclime')]" | ConvertFrom-Json
    if ($registries.Count -eq 0) { throw "No container registry found" }
    $registry = $registries[0]
    $RegistryName = $registry.name
    $acrLoginServer = $registry.loginServer

    Write-Host "Using registry: $RegistryName" -ForegroundColor Cyan

    # Get ACR credentials
    $acrCredentials = az acr credential show --name $RegistryName --resource-group $registry.resourceGroup | ConvertFrom-Json
    $acrUsername = $acrCredentials.username
    $acrPassword = $acrCredentials.passwords[0].value

    # Login to Docker
    echo $acrPassword | docker login $acrLoginServer --username $acrUsername --password-stdin
    if ($LASTEXITCODE -ne 0) { throw "Failed to login to Docker registry" }

    # Build and push backend
    Write-Host "`nBuilding backend with CORS fix..." -ForegroundColor Yellow
    $backendImage = "$acrLoginServer/climatech-backend:latest"
    docker build -t $backendImage -f ./infra/Dockerfile.backend ./backend
    if ($LASTEXITCODE -ne 0) { throw "Failed to build backend image" }
    
    docker push $backendImage
    if ($LASTEXITCODE -ne 0) { throw "Failed to push backend image" }

    # Find and restart backend container
    Write-Host "`nRestarting backend container..." -ForegroundColor Yellow
    $containers = az container list --query "[?contains(name, 'backend')]" | ConvertFrom-Json
    if ($containers.Count -gt 0) {
        $container = $containers[0]
        az container restart --name $container.name --resource-group $container.resourceGroup --output none
        Write-Host "Restarted: $($container.name)" -ForegroundColor Green
    }

    Write-Host "`nBackend updated successfully!" -ForegroundColor Green
    Write-Host "CORS is now configured to allow all origins." -ForegroundColor Cyan

} catch {
    Write-Error "Update failed: $_"
    exit 1
}