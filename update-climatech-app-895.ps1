#!/usr/bin/env pwsh

<#
.SYNOPSIS
Update backend in climatech-app-895 resource group with CORS fix
#>

try {
    $ResourceGroup = "climatech-app-895"
    
    Write-Host "=== Updating Backend in $ResourceGroup ===" -ForegroundColor Green
    
    # Find backend container in this resource group
    Write-Host "`n1. Finding backend container..." -ForegroundColor Yellow
    $containers = az container list --resource-group $ResourceGroup --query "[?contains(name, 'backend')]" | ConvertFrom-Json
    
    if ($containers.Count -eq 0) {
        throw "No backend containers found in resource group $ResourceGroup"
    }
    
    $backendContainer = $containers[0]
    $ContainerName = $backendContainer.name
    Write-Host "Found container: $ContainerName" -ForegroundColor Green
    Write-Host "Current URL: http://$($backendContainer.ipAddress.fqdn):8000" -ForegroundColor Cyan
    
    # Find container registry in this resource group
    Write-Host "`n2. Finding container registry..." -ForegroundColor Yellow
    $registries = az acr list --resource-group $ResourceGroup | ConvertFrom-Json
    
    if ($registries.Count -eq 0) {
        throw "No container registry found in resource group $ResourceGroup"
    }
    
    $registry = $registries[0]
    $RegistryName = $registry.name
    $LoginServer = $registry.loginServer
    Write-Host "Using registry: $RegistryName" -ForegroundColor Green
    
    # Get registry credentials
    Write-Host "`n3. Getting registry credentials..." -ForegroundColor Yellow
    $creds = az acr credential show --name $RegistryName --resource-group $ResourceGroup | ConvertFrom-Json
    
    # Login to Docker
    Write-Host "`n4. Logging into Docker registry..." -ForegroundColor Yellow
    echo $creds.passwords[0].value | docker login $LoginServer --username $creds.username --password-stdin
    if ($LASTEXITCODE -ne 0) { throw "Failed to login to Docker" }
    
    # Build updated backend with CORS fix
    Write-Host "`n5. Building backend with CORS allowing ALL origins..." -ForegroundColor Yellow
    $backendImage = "$LoginServer/climatech-backend:latest"
    docker build -t $backendImage -f ./infra/Dockerfile.backend ./backend
    if ($LASTEXITCODE -ne 0) { throw "Failed to build backend" }
    
    # Push updated image
    Write-Host "`n6. Pushing updated backend..." -ForegroundColor Yellow
    docker push $backendImage
    if ($LASTEXITCODE -ne 0) { throw "Failed to push backend" }
    
    # Restart container to use new image
    Write-Host "`n7. Restarting backend container..." -ForegroundColor Yellow
    az container restart --name $ContainerName --resource-group $ResourceGroup --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to restart container" }
    
    # Wait for container to be ready
    Write-Host "`n8. Waiting for container to restart..." -ForegroundColor Yellow
    Start-Sleep -Seconds 20
    
    # Get updated container info
    $updatedContainer = az container show --name $ContainerName --resource-group $ResourceGroup | ConvertFrom-Json
    $backendUrl = $updatedContainer.ipAddress.fqdn
    
    Write-Host "`nBackend CORS Update Completed!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "✅ Backend now allows ALL origins (CORS=*)" -ForegroundColor Green
    Write-Host "✅ Backend URL: http://${backendUrl}:8000" -ForegroundColor White
    Write-Host "✅ API URL: http://${backendUrl}:8000/api" -ForegroundColor White
    Write-Host "✅ Health: http://${backendUrl}:8000/health" -ForegroundColor White
    Write-Host "✅ Docs: http://${backendUrl}:8000/docs" -ForegroundColor White
    
    Write-Host "`nYour frontend should now work without CORS errors!" -ForegroundColor Cyan
    
    # Clean up local image
    docker rmi $backendImage -f 2>$null
    
} catch {
    Write-Error "Update failed: $_"
    Write-Host "`nTip: Make sure you're in the Climatech directory and Docker is running" -ForegroundColor Yellow
    exit 1
}