# Azure CLI Installation and Deployment Guide

## Step 1: Install Azure CLI

# Option A: Download installer
Write-Host "Download Azure CLI installer from:" -ForegroundColor Cyan
Write-Host "https://aka.ms/installazurecliwindows" -ForegroundColor Yellow

# Option B: Use winget (if available)
Write-Host "`nOr install via winget:" -ForegroundColor Cyan
Write-Host "winget install -e --id Microsoft.AzureCLI" -ForegroundColor Yellow

# Option C: Use chocolatey (if available)
Write-Host "`nOr install via chocolatey:" -ForegroundColor Cyan
Write-Host "choco install azure-cli" -ForegroundColor Yellow

Write-Host "`nAfter installation:" -ForegroundColor Green
Write-Host "1. Close and reopen PowerShell" -ForegroundColor White
Write-Host "2. Run: az --version" -ForegroundColor White
Write-Host "3. Run: .\deploy-azure.ps1" -ForegroundColor White