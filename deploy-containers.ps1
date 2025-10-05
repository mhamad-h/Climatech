# Simple Azure Container Instances Deployment (Alternative)
# This avoids Container Apps complexity and deploys to Container Instances

param(
    [string]$ResourceGroup = "climatech-rg",
    [string]$Location = "East US",
    [string]$RegistryName = "climatechregistry$(Get-Random -Minimum 1000 -Maximum 9999)"
)

Write-Host "🌦️ Deploying Climatech to Azure Container Instances" -ForegroundColor Cyan

# Check Azure login
$account = az account show 2>$null | ConvertFrom-Json
if (!$account) {
    Write-Host "Please login to Azure..." -ForegroundColor Yellow
    az login
    $account = az account show | ConvertFrom-Json
}

Write-Host "Using Azure account: $($account.user.name)" -ForegroundColor Green

try {
    # Step 1: Clean up any existing resources
    Write-Host "`n🧹 Cleaning up existing resources..." -ForegroundColor Yellow
    az group delete --name $ResourceGroup --yes --no-wait 2>$null
    Start-Sleep -Seconds 10

    # Step 2: Create fresh resource group
    Write-Host "`n1. Creating resource group..." -ForegroundColor Yellow
    az group create --name $ResourceGroup --location $Location

    # Step 3: Create container registry
    Write-Host "`n2. Creating container registry..." -ForegroundColor Yellow
    az acr create --resource-group $ResourceGroup --name $RegistryName --sku Basic --admin-enabled true

    # Step 4: Build and push images
    Write-Host "`n3. Building and pushing images..." -ForegroundColor Yellow
    $acrLoginServer = az acr show --name $RegistryName --resource-group $ResourceGroup --query loginServer --output tsv
    az acr login --name $RegistryName

    # Build backend
    Write-Host "Building backend..." -ForegroundColor Cyan
    docker build -t "${acrLoginServer}/climatech-backend:latest" -f infra/Dockerfile.backend ./backend
    docker push "${acrLoginServer}/climatech-backend:latest"

    # Build frontend
    Write-Host "Building frontend..." -ForegroundColor Cyan
    docker build -t "${acrLoginServer}/climatech-frontend:latest" -f infra/Dockerfile.frontend ./client
    docker push "${acrLoginServer}/climatech-frontend:latest"

    # Step 5: Get ACR credentials
    $acrCredentials = az acr credential show --name $RegistryName --resource-group $ResourceGroup | ConvertFrom-Json
    $acrUsername = $acrCredentials.username
    $acrPassword = $acrCredentials.passwords[0].value

    # Step 6: Deploy backend container
    Write-Host "`n4. Deploying backend container..." -ForegroundColor Yellow
    az container create `
        --name "climatech-backend" `
        --resource-group $ResourceGroup `
        --location $Location `
        --image "${acrLoginServer}/climatech-backend:latest" `
        --registry-login-server $acrLoginServer `
        --registry-username $acrUsername `
        --registry-password $acrPassword `
        --dns-name-label "climatech-backend-$(Get-Random -Min 100 -Max 999)" `
        --ports 8000 `
        --environment-variables "BACKEND_HOST=0.0.0.0" "BACKEND_PORT=8000" "ENVIRONMENT=production" "CORS_ORIGINS=*" `
        --cpu 1 `
        --memory 2

    # Step 7: Get backend URL
    $backendInfo = az container show --name "climatech-backend" --resource-group $ResourceGroup | ConvertFrom-Json
    $backendUrl = $backendInfo.ipAddress.fqdn
    $backendApiUrl = "http://$backendUrl:8000/api"

    # Step 8: Deploy frontend container
    Write-Host "`n5. Deploying frontend container..." -ForegroundColor Yellow
    az container create `
        --name "climatech-frontend" `
        --resource-group $ResourceGroup `
        --location $Location `
        --image "${acrLoginServer}/climatech-frontend:latest" `
        --registry-login-server $acrLoginServer `
        --registry-username $acrUsername `
        --registry-password $acrPassword `
        --dns-name-label "climatech-frontend-$(Get-Random -Min 100 -Max 999)" `
        --ports 80 `
        --environment-variables "VITE_API_URL=$backendApiUrl" `
        --cpu 0.5 `
        --memory 1

    # Step 9: Get frontend URL
    $frontendInfo = az container show --name "climatech-frontend" --resource-group $ResourceGroup | ConvertFrom-Json
    $frontendUrl = $frontendInfo.ipAddress.fqdn

    # Step 10: Update backend CORS
    Write-Host "`n6. Updating CORS settings..." -ForegroundColor Yellow
    az container restart --name "climatech-backend" --resource-group $ResourceGroup

    Write-Host "`n✅ Deployment completed!" -ForegroundColor Green
    Write-Host "🌐 Frontend: http://$frontendUrl" -ForegroundColor Cyan
    Write-Host "🔧 Backend:  http://$backendUrl:8000" -ForegroundColor Cyan
    Write-Host "📚 API Docs: http://$backendUrl:8000/docs" -ForegroundColor Cyan
    Write-Host "💊 Health:   http://$backendUrl:8000/health" -ForegroundColor Cyan

} catch {
    Write-Error "Deployment failed: $_"
    Write-Host "`n🧹 Cleanup command:" -ForegroundColor Yellow
    Write-Host "az group delete --name $ResourceGroup --yes --no-wait" -ForegroundColor White
}