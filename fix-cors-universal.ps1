#!/usr/bin/env pwsh

<#
.SYNOPSIS
Simple script to update ANY backend container with CORS fix
#>

try {
    Write-Host "=== Universal CORS Fix ===" -ForegroundColor Green
    
    # Find all climatech backend containers
    Write-Host "Finding backend containers..." -ForegroundColor Yellow
    $allContainers = az container list --query "[?contains(name, 'climatech') && contains(name, 'backend')]" | ConvertFrom-Json
    
    if ($allContainers.Count -eq 0) {
        throw "No backend containers found"
    }
    
    # Show available containers
    Write-Host "`nFound backend containers:" -ForegroundColor Cyan
    for ($i = 0; $i -lt $allContainers.Count; $i++) {
        $container = $allContainers[$i]
        Write-Host "  [$i] $($container.name) - $($container.ipAddress.fqdn) (RG: $($container.resourceGroup))" -ForegroundColor White
    }
    
    # If only one container, use it automatically
    if ($allContainers.Count -eq 1) {
        $selectedContainer = $allContainers[0]
        Write-Host "`nUsing container: $($selectedContainer.name)" -ForegroundColor Green
    } else {
        # Let user choose (for now just use first one)
        $selectedContainer = $allContainers[0]
        Write-Host "`nUsing first container: $($selectedContainer.name)" -ForegroundColor Green
    }
    
    $ResourceGroup = $selectedContainer.resourceGroup
    $ContainerName = $selectedContainer.name
    
    # Find registry in the same resource group
    $registries = az acr list --resource-group $ResourceGroup | ConvertFrom-Json
    if ($registries.Count -eq 0) {
        throw "No registry found in resource group $ResourceGroup"
    }
    
    $registry = $registries[0]
    $RegistryName = $registry.name
    $LoginServer = $registry.loginServer
    
    Write-Host "Using registry: $RegistryName" -ForegroundColor Green
    
    # Get credentials
    $creds = az acr credential show --name $RegistryName --resource-group $ResourceGroup | ConvertFrom-Json
    
    # Login to Docker
    Write-Host "`nLogging into Docker..." -ForegroundColor Yellow
    echo $creds.passwords[0].value | docker login $LoginServer --username $creds.username --password-stdin
    
    # Build and push
    Write-Host "`nBuilding backend with CORS=* fix..." -ForegroundColor Yellow
    $image = "$LoginServer/climatech-backend:latest"
    docker build -t $image -f ./infra/Dockerfile.backend ./backend
    docker push $image
    
    # Restart container
    Write-Host "`nRestarting container..." -ForegroundColor Yellow
    az container restart --name $ContainerName --resource-group $ResourceGroup
    
    Write-Host "`nCORS Fixed! Backend allows ALL origins now." -ForegroundColor Green
    Write-Host "Backend URL: http://$($selectedContainer.ipAddress.fqdn):8000" -ForegroundColor Cyan
    Write-Host "Test your app now!" -ForegroundColor White
    
} catch {
    Write-Error "Failed: $_"
}