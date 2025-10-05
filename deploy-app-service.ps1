# Alternative: Use Azure App Service (Easier Deployment)
# This avoids Docker and Container Registry issues

param(
    [string]$ResourceGroup = "climatech-rg",
    [string]$Location = "East US",
    [string]$AppServicePlan = "climatech-plan",
    [string]$BackendApp = "climatech-backend-$(Get-Random -Min 100 -Max 999)",
    [string]$FrontendApp = "climatech-frontend-$(Get-Random -Min 100 -Max 999)"
)

Write-Host "🌦️ Deploying Climatech to Azure App Service (No Docker Required)" -ForegroundColor Cyan

# Check Azure login
$account = az account show 2>$null | ConvertFrom-Json
if (!$account) {
    Write-Host "Please login to Azure..." -ForegroundColor Yellow
    az login
    $account = az account show | ConvertFrom-Json
}

Write-Host "Using Azure account: $($account.user.name)" -ForegroundColor Green

Write-Host "`nDeployment Configuration:" -ForegroundColor Yellow
Write-Host "  Resource Group: $ResourceGroup"
Write-Host "  Backend App: $BackendApp"
Write-Host "  Frontend App: $FrontendApp"

$confirmation = Read-Host "`nProceed with App Service deployment? (y/N)"
if ($confirmation -ne 'y') {
    exit 0
}

try {
    # Step 1: Create resource group
    Write-Host "`n1. Creating resource group..." -ForegroundColor Yellow
    az group create --name $ResourceGroup --location $Location

    # Step 2: Create App Service plan
    Write-Host "`n2. Creating App Service plan..." -ForegroundColor Yellow
    az appservice plan create --name $AppServicePlan --resource-group $ResourceGroup --location $Location --sku B1 --is-linux

    # Step 3: Create backend web app (Python)
    Write-Host "`n3. Creating backend web app..." -ForegroundColor Yellow
    az webapp create --name $BackendApp --resource-group $ResourceGroup --plan $AppServicePlan --runtime "PYTHON|3.11"

    # Step 4: Configure backend settings
    Write-Host "`n4. Configuring backend..." -ForegroundColor Yellow
    az webapp config appsettings set --name $BackendApp --resource-group $ResourceGroup --settings `
        "BACKEND_HOST=0.0.0.0" `
        "BACKEND_PORT=8000" `
        "ENVIRONMENT=production" `
        "CORS_ORIGINS=*" `
        "SCM_DO_BUILD_DURING_DEPLOYMENT=true"

    # Step 5: Deploy backend code
    Write-Host "`n5. Deploying backend code..." -ForegroundColor Yellow
    Compress-Archive -Path "backend\*" -DestinationPath "backend-deploy.zip" -Force
    az webapp deployment source config-zip --name $BackendApp --resource-group $ResourceGroup --src "backend-deploy.zip"

    # Step 6: Create frontend web app (Node.js)
    Write-Host "`n6. Creating frontend web app..." -ForegroundColor Yellow
    az webapp create --name $FrontendApp --resource-group $ResourceGroup --plan $AppServicePlan --runtime "NODE|18-lts"

    # Get backend URL
    $backendUrl = az webapp show --name $BackendApp --resource-group $ResourceGroup --query defaultHostName --output tsv

    # Step 7: Build frontend with correct API URL
    Write-Host "`n7. Building frontend..." -ForegroundColor Yellow
    Set-Location "client"
    $env:VITE_API_URL = "https://$backendUrl/api"
    npm run build
    Set-Location ".."

    # Step 8: Deploy frontend
    Write-Host "`n8. Deploying frontend..." -ForegroundColor Yellow
    Compress-Archive -Path "client\dist\*" -DestinationPath "frontend-deploy.zip" -Force
    az webapp deployment source config-zip --name $FrontendApp --resource-group $ResourceGroup --src "frontend-deploy.zip"

    # Get URLs
    $frontendUrl = az webapp show --name $FrontendApp --resource-group $ResourceGroup --query defaultHostName --output tsv

    # Step 9: Update CORS settings
    Write-Host "`n9. Updating CORS settings..." -ForegroundColor Yellow
    az webapp config appsettings set --name $BackendApp --resource-group $ResourceGroup --settings "CORS_ORIGINS=https://$frontendUrl"

    Write-Host "`n✅ Deployment completed!" -ForegroundColor Green
    Write-Host "Frontend: https://$frontendUrl" -ForegroundColor Cyan
    Write-Host "Backend:  https://$backendUrl" -ForegroundColor Cyan
    Write-Host "API Docs: https://$backendUrl/docs" -ForegroundColor Cyan

    # Cleanup
    Remove-Item "backend-deploy.zip" -Force -ErrorAction SilentlyContinue
    Remove-Item "frontend-deploy.zip" -Force -ErrorAction SilentlyContinue

} catch {
    Write-Error "Deployment failed: $_"
}