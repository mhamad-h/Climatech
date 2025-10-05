#!/usr/bin/env pwsh

<#
.SYNOPSIS
Update existing deployment with new code
#>

param(
    [string]$ResourceGroup = ""
)

try {
    # Find existing resource group if not specified
    if (-not $ResourceGroup) {
        $groups = az group list --query "[?contains(name, 'climatech')]" | ConvertFrom-Json
        if ($groups.Count -eq 0) {
            throw "No Climatech resource groups found. Run deploy-smart.ps1 first."
        }
        $ResourceGroup = $groups[0].name
        Write-Host "Found resource group: $ResourceGroup" -ForegroundColor Green
    }

    # Get existing resources
    Write-Host "`n1. Getting existing resources..." -ForegroundColor Yellow
    $registries = az acr list --resource-group $ResourceGroup | ConvertFrom-Json
    if ($registries.Count -eq 0) { throw "No container registry found" }
    $RegistryName = $registries[0].name
    $acrLoginServer = $registries[0].loginServer

    # Get current backend URL (for display only - NOT changing it)
    $backendInfo = az container show --name "climatech-backend" --resource-group $ResourceGroup | ConvertFrom-Json
    $backendUrl = $backendInfo.ipAddress.fqdn
    $backendApiUrl = "http://${backendUrl}:8000/api"
    
    Write-Host "Current Backend URL: $backendApiUrl" -ForegroundColor Cyan
    Write-Host "Keeping existing configuration - NOT changing URLs" -ForegroundColor Green

    # Rebuild and push images (keeping existing config)
    Write-Host "`n2. Rebuilding backend..." -ForegroundColor Yellow
    az acr build --registry $RegistryName --image "climatech-backend:latest" ./backend --file ./infra/Dockerfile.backend --output none
    
    Write-Host "`n3. Rebuilding frontend..." -ForegroundColor Yellow
    az acr build --registry $RegistryName --image "climatech-frontend:latest" ./client --file ./infra/Dockerfile.frontend --output none

    # Restart containers to use new images
    Write-Host "`n4. Restarting containers..." -ForegroundColor Yellow
    az container restart --name "climatech-backend" --resource-group $ResourceGroup --output none
    az container restart --name "climatech-frontend" --resource-group $ResourceGroup --output none

    # Wait and get URLs
    Start-Sleep -Seconds 15
    $frontendInfo = az container show --name "climatech-frontend" --resource-group $ResourceGroup | ConvertFrom-Json
    $frontendUrl = $frontendInfo.ipAddress.fqdn

    Write-Host "`nUpdate completed successfully!" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "`nYour Updated Geoclime URLs:" -ForegroundColor Cyan
    Write-Host "  Frontend:    http://$frontendUrl" -ForegroundColor White
    Write-Host "  Backend:     http://${backendUrl}:8000" -ForegroundColor White
    Write-Host "  API Docs:    http://${backendUrl}:8000/docs" -ForegroundColor White

} catch {
    Write-Error "Update failed: $_"
    exit 1
}