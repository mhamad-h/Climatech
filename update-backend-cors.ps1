#!/usr/bin/env pwsh

<#
.SYNOPSIS
Update backend container to fix CORS issues
#>

try {
    $ResourceGroup = "climatech-app-678"  # Your resource group
    $RegistryName = "climatechreg3152"    # Your actual registry name
    $ContainerName = "climatech-backend"  # Your backend container name
    
    Write-Host "=== Fixing Backend CORS ===" -ForegroundColor Green
    Write-Host "Registry: $RegistryName" -ForegroundColor Cyan
    Write-Host "Resource Group: $ResourceGroup" -ForegroundColor Cyan
    
    # Get ACR login server and credentials
    Write-Host "`n1. Getting registry credentials..." -ForegroundColor Yellow
    $acrLoginServer = az acr show --name $RegistryName --resource-group $ResourceGroup --query "loginServer" --output tsv
    $acrCredentials = az acr credential show --name $RegistryName --resource-group $ResourceGroup | ConvertFrom-Json
    
    # Login to Docker registry
    Write-Host "`n2. Logging into Docker registry..." -ForegroundColor Yellow
    echo $acrCredentials.passwords[0].value | docker login $acrLoginServer --username $acrCredentials.username --password-stdin
    if ($LASTEXITCODE -ne 0) { throw "Failed to login to Docker registry" }
    
    # Build backend with CORS fix
    Write-Host "`n3. Building updated backend..." -ForegroundColor Yellow
    $backendImage = "$acrLoginServer/climatech-backend:latest"
    docker build -t $backendImage -f ./infra/Dockerfile.backend ./backend
    if ($LASTEXITCODE -ne 0) { throw "Failed to build backend image" }
    
    # Push updated backend
    Write-Host "`n4. Pushing updated backend..." -ForegroundColor Yellow
    docker push $backendImage
    if ($LASTEXITCODE -ne 0) { throw "Failed to push backend image" }
    
    # Restart backend container
    Write-Host "`n5. Restarting backend container..." -ForegroundColor Yellow
    az container restart --name $ContainerName --resource-group $ResourceGroup --output none
    if ($LASTEXITCODE -ne 0) { throw "Failed to restart container" }
    
    # Wait and check status
    Write-Host "`n6. Waiting for container to restart..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15
    
    $containerInfo = az container show --name $ContainerName --resource-group $ResourceGroup | ConvertFrom-Json
    $backendUrl = $containerInfo.ipAddress.fqdn
    
    Write-Host "`nCORS Fix completed!" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "Backend URL: http://${backendUrl}:8000" -ForegroundColor White
    Write-Host "API URL: http://${backendUrl}:8000/api" -ForegroundColor White
    Write-Host "Health Check: http://${backendUrl}:8000/health" -ForegroundColor White
    
    Write-Host "`nTesting CORS..." -ForegroundColor Yellow
    Write-Host "Try your frontend again - CORS should be fixed!" -ForegroundColor Green
    
    # Clean up local image
    docker rmi $backendImage -f 2>$null
    
} catch {
    Write-Error "Update failed: $_"
    exit 1
}