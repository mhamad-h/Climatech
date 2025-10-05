#!/usr/bin/env pwsh

<#
.SYNOPSIS
Find and fix CORS for climatech-backend-2467 container
#>

try {
    Write-Host "=== Finding Backend Container ===" -ForegroundColor Green
    
    # Find the container across all resource groups
    Write-Host "`n1. Searching for climatech-backend containers..." -ForegroundColor Yellow
    $containers = az container list --query "[?contains(name, 'climatech-backend')]" | ConvertFrom-Json
    
    if ($containers.Count -eq 0) {
        throw "No climatech-backend containers found"
    }
    
    # Find the specific container ending with 2467
    $targetContainer = $containers | Where-Object { $_.name -like "*2467*" -or $_.ipAddress.fqdn -like "*2467*" }
    
    if (-not $targetContainer) {
        Write-Host "Available containers:" -ForegroundColor Yellow
        foreach ($container in $containers) {
            Write-Host "  Name: $($container.name) | FQDN: $($container.ipAddress.fqdn) | RG: $($container.resourceGroup)" -ForegroundColor White
        }
        throw "Could not find container with 2467 in name or URL"
    }
    
    $ResourceGroup = $targetContainer.resourceGroup
    $ContainerName = $targetContainer.name
    
    Write-Host "Found container: $ContainerName in resource group: $ResourceGroup" -ForegroundColor Green
    
    # Find registry in the same resource group
    Write-Host "`n2. Finding container registry..." -ForegroundColor Yellow
    $registries = az acr list --resource-group $ResourceGroup | ConvertFrom-Json
    
    if ($registries.Count -eq 0) {
        throw "No container registries found in resource group $ResourceGroup"
    }
    
    $RegistryName = $registries[0].name
    Write-Host "Using registry: $RegistryName" -ForegroundColor Green
    
    # Get credentials and build/push updated backend
    $acrCredentials = az acr credential show --name $RegistryName --resource-group $ResourceGroup | ConvertFrom-Json
    $acrLoginServer = $registries[0].loginServer
    
    Write-Host "`n3. Logging into Docker registry..." -ForegroundColor Yellow
    echo $acrCredentials.passwords[0].value | docker login $acrLoginServer --username $acrCredentials.username --password-stdin
    
    Write-Host "`n4. Building backend with CORS fix..." -ForegroundColor Yellow
    $backendImage = "$acrLoginServer/climatech-backend:latest"
    docker build -t $backendImage -f ./infra/Dockerfile.backend ./backend
    
    Write-Host "`n5. Pushing updated backend..." -ForegroundColor Yellow
    docker push $backendImage
    
    Write-Host "`n6. Restarting backend container..." -ForegroundColor Yellow
    az container restart --name $ContainerName --resource-group $ResourceGroup
    
    Write-Host "`nCORS fix completed!" -ForegroundColor Green
    Write-Host "Backend: $($targetContainer.ipAddress.fqdn):8000" -ForegroundColor White
    Write-Host "Try your frontend again!" -ForegroundColor Green
    
} catch {
    Write-Error "Fix failed: $_"
    exit 1
}