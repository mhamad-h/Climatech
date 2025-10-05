#!/usr/bin/env pwsh

<#
.SYNOPSIS
Update frontend to use correct backend URL: http://climatech-backend-2467.eastus.azurecontainer.io:8000/api
#>

try {
    $ResourceGroup = "climatech-app-895"
    $BackendUrl = "http://climatech-backend-2467.eastus.azurecontainer.io:8000/api"
    
    Write-Host "=== Updating Frontend in $ResourceGroup ===" -ForegroundColor Green
    Write-Host "Target Backend URL: $BackendUrl" -ForegroundColor Cyan
    
    # Find frontend container
    Write-Host "`n1. Finding frontend container..." -ForegroundColor Yellow
    $containers = az container list --resource-group $ResourceGroup --query "[?contains(name, 'frontend')]" | ConvertFrom-Json
    
    if ($containers.Count -eq 0) {
        throw "No frontend containers found in resource group $ResourceGroup"
    }
    
    $frontendContainer = $containers[0]
    $ContainerName = $frontendContainer.name
    Write-Host "Found container: $ContainerName" -ForegroundColor Green
    Write-Host "Current URL: http://$($frontendContainer.ipAddress.fqdn)" -ForegroundColor Cyan
    
    # Find registry
    Write-Host "`n2. Finding container registry..." -ForegroundColor Yellow
    $registries = az acr list --resource-group $ResourceGroup | ConvertFrom-Json
    if ($registries.Count -eq 0) { throw "No registry found" }
    
    $registry = $registries[0]
    $RegistryName = $registry.name
    $LoginServer = $registry.loginServer
    Write-Host "Using registry: $RegistryName" -ForegroundColor Green
    
    # Get credentials
    Write-Host "`n3. Getting registry credentials..." -ForegroundColor Yellow
    $creds = az acr credential show --name $RegistryName --resource-group $ResourceGroup | ConvertFrom-Json
    
    # Update .env.production with correct backend URL
    Write-Host "`n4. Updating .env.production with correct backend URL..." -ForegroundColor Yellow
    $envContent = @"
# Production environment variables
VITE_API_URL=$BackendUrl
VITE_APP_NAME=Geoclime
VITE_APP_VERSION=1.0.0
VITE_DEBUG_MODE=false
VITE_ENABLE_ANALYTICS=true
"@
    Set-Content -Path "./client/.env.production" -Value $envContent -Force
    Write-Host "✅ Updated .env.production with: $BackendUrl" -ForegroundColor Green
    
    # Login to Docker
    Write-Host "`n5. Logging into Docker registry..." -ForegroundColor Yellow
    echo $creds.passwords[0].value | docker login $LoginServer --username $creds.username --password-stdin
    if ($LASTEXITCODE -ne 0) { throw "Failed to login to Docker" }
    
    # Build frontend with correct backend URL
    Write-Host "`n6. Building frontend with correct backend URL..." -ForegroundColor Yellow
    $frontendImage = "$LoginServer/climatech-frontend:latest"
    docker build -t $frontendImage -f ./infra/Dockerfile.frontend ./client
    if ($LASTEXITCODE -ne 0) { throw "Failed to build frontend" }
    
    # Push updated frontend
    Write-Host "`n7. Pushing updated frontend..." -ForegroundColor Yellow
    docker push $frontendImage
    if ($LASTEXITCODE -ne 0) { throw "Failed to push frontend" }
    
    # Restart frontend container
    Write-Host "`n8. Restarting frontend container..." -ForegroundColor Yellow
    az container restart --name $ContainerName --resource-group $ResourceGroup --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to restart container" }
    
    # Wait for restart
    Write-Host "`n9. Waiting for container to restart..." -ForegroundColor Yellow
    Start-Sleep -Seconds 20
    
    # Get updated info
    $updatedContainer = az container show --name $ContainerName --resource-group $ResourceGroup | ConvertFrom-Json
    $frontendUrl = $updatedContainer.ipAddress.fqdn
    
    Write-Host "`nFrontend Update Completed!" -ForegroundColor Green
    Write-Host "================================================" -ForegroundColor Green
    Write-Host "✅ Frontend URL: http://$frontendUrl" -ForegroundColor White
    Write-Host "✅ Now connects to: $BackendUrl" -ForegroundColor White
    Write-Host "✅ No more wrong URL errors!" -ForegroundColor Green
    
    Write-Host "`nTest your app now - it should connect to the correct backend!" -ForegroundColor Cyan
    
    # Clean up
    docker rmi $frontendImage -f 2>$null
    
} catch {
    Write-Error "Update failed: $_"
    exit 1
}