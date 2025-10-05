# Fixed Azure Deployment - Uses new resource group name
param(
    [string]$ResourceGroup = "climatech-app-$(Get-Random -Minimum 100 -Maximum 999)",
    [string]$Location = "East US",
    [string]$RegistryName = "climatechreg$(Get-Random -Minimum 1000 -Maximum 9999)"
)

Write-Host "🌦️ Deploying Climatech to Azure Container Instances" -ForegroundColor Cyan
Write-Host "Using NEW resource group: $ResourceGroup" -ForegroundColor Yellow

# Check Azure login
$account = az account show 2>$null | ConvertFrom-Json
if (!$account) {
    Write-Host "Please login to Azure..." -ForegroundColor Yellow
    az login
    $account = az account show | ConvertFrom-Json
}

Write-Host "Using Azure account: $($account.user.name)" -ForegroundColor Green

# Check if Docker is working
Write-Host "`nChecking Docker..." -ForegroundColor Yellow
try {
    docker version | Out-Null
    Write-Host "✅ Docker is working" -ForegroundColor Green
} catch {
    Write-Error "❌ Docker is not working. Please start Docker Desktop first."
    exit 1
}

$confirmation = Read-Host "`nProceed with deployment? (y/N)"
if ($confirmation -ne 'y') {
    Write-Host "Deployment cancelled." -ForegroundColor Red
    exit 0
}

try {
    # Step 1: Create resource group
    Write-Host "`n1. Creating resource group: $ResourceGroup..." -ForegroundColor Yellow
    az group create --name $ResourceGroup --location $Location
    if ($LASTEXITCODE -ne 0) { throw "Failed to create resource group" }

    # Step 2: Create container registry
    Write-Host "`n2. Creating container registry: $RegistryName..." -ForegroundColor Yellow
    az acr create --resource-group $ResourceGroup --name $RegistryName --sku Basic --admin-enabled true
    if ($LASTEXITCODE -ne 0) { throw "Failed to create container registry" }

    # Step 3: Get ACR login server and login
    Write-Host "`n3. Configuring container registry..." -ForegroundColor Yellow
    $acrLoginServer = az acr show --name $RegistryName --resource-group $ResourceGroup --query loginServer --output tsv
    Write-Host "Registry server: $acrLoginServer" -ForegroundColor Cyan
    
    az acr login --name $RegistryName
    if ($LASTEXITCODE -ne 0) { throw "Failed to login to container registry" }

    # Step 4: Build and push backend
    Write-Host "`n4. Building and pushing backend..." -ForegroundColor Yellow
    $backendImage = "${acrLoginServer}/climatech-backend:latest"
    Write-Host "Building: $backendImage" -ForegroundColor Cyan
    
    docker build -t $backendImage -f infra/Dockerfile.backend ./backend
    if ($LASTEXITCODE -ne 0) { throw "Failed to build backend image" }
    
    docker push $backendImage
    if ($LASTEXITCODE -ne 0) { throw "Failed to push backend image" }

    # Step 5: Build and push frontend
    Write-Host "`n5. Building and pushing frontend..." -ForegroundColor Yellow
    $frontendImage = "${acrLoginServer}/climatech-frontend:latest"
    Write-Host "Building: $frontendImage" -ForegroundColor Cyan
    
    docker build -t $frontendImage -f infra/Dockerfile.frontend ./client
    if ($LASTEXITCODE -ne 0) { throw "Failed to build frontend image" }
    
    docker push $frontendImage
    if ($LASTEXITCODE -ne 0) { throw "Failed to push frontend image" }

    # Step 6: Get ACR credentials
    Write-Host "`n6. Getting registry credentials..." -ForegroundColor Yellow
    $acrCredentials = az acr credential show --name $RegistryName --resource-group $ResourceGroup | ConvertFrom-Json
    $acrUsername = $acrCredentials.username
    $acrPassword = $acrCredentials.passwords[0].value

    # Step 7: Deploy backend container
    Write-Host "`n7. Deploying backend container..." -ForegroundColor Yellow
    $backendDns = "climatech-backend-$(Get-Random -Min 1000 -Max 9999)"
    
    az container create `
        --name "climatech-backend" `
        --resource-group $ResourceGroup `
        --location $Location `
        --image $backendImage `
        --os-type Linux `
        --registry-login-server $acrLoginServer `
        --registry-username $acrUsername `
        --registry-password $acrPassword `
        --dns-name-label $backendDns `
        --ports 8000 `
        --environment-variables "BACKEND_HOST=0.0.0.0" "BACKEND_PORT=8000" "ENVIRONMENT=production" "CORS_ORIGINS=*" `
        --cpu 1 `
        --memory 2
    
    if ($LASTEXITCODE -ne 0) { throw "Failed to deploy backend container" }

    # Step 8: Get backend URL
    Write-Host "`n8. Getting backend URL..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10  # Wait for container to be ready
    $backendInfo = az container show --name "climatech-backend" --resource-group $ResourceGroup | ConvertFrom-Json
    $backendUrl = $backendInfo.ipAddress.fqdn
    $backendApiUrl = "http://${backendUrl}:8000/api"
    
    Write-Host "Backend URL: http://${backendUrl}:8000" -ForegroundColor Cyan

    # Step 9: Deploy frontend container
    Write-Host "`n9. Deploying frontend container..." -ForegroundColor Yellow
    $frontendDns = "climatech-frontend-$(Get-Random -Min 1000 -Max 9999)"
    
    az container create `
        --name "climatech-frontend" `
        --resource-group $ResourceGroup `
        --location $Location `
        --image $frontendImage `
        --os-type Linux `
        --registry-login-server $acrLoginServer `
        --registry-username $acrUsername `
        --registry-password $acrPassword `
        --dns-name-label $frontendDns `
        --ports 80 `
        --environment-variables "VITE_API_URL=$backendApiUrl" `
        --cpu 0.5 `
        --memory 1
    
    if ($LASTEXITCODE -ne 0) { throw "Failed to deploy frontend container" }

    # Step 10: Get frontend URL
    Write-Host "`n10. Getting frontend URL..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10  # Wait for container to be ready
    $frontendInfo = az container show --name "climatech-frontend" --resource-group $ResourceGroup | ConvertFrom-Json
    $frontendUrl = $frontendInfo.ipAddress.fqdn

    Write-Host "`nDeployment completed successfully!" -ForegroundColor Green
    Write-Host "===============================================" -ForegroundColor Green
    Write-Host "`nYour Climatech Application URLs:" -ForegroundColor Cyan
    Write-Host "  Frontend:    http://$frontendUrl" -ForegroundColor White
    Write-Host "  Backend:     http://${backendUrl}:8000" -ForegroundColor White
    Write-Host "  API Docs:    http://${backendUrl}:8000/docs" -ForegroundColor White
    Write-Host "  Health:      http://${backendUrl}:8000/health" -ForegroundColor White
    
    Write-Host "`nResource Details:" -ForegroundColor Yellow
    Write-Host "  Resource Group: $ResourceGroup" -ForegroundColor White
    Write-Host "  Registry:       $RegistryName" -ForegroundColor White
    Write-Host "  Location:       $Location" -ForegroundColor White
    
    Write-Host "`nNext Steps:" -ForegroundColor Yellow
    Write-Host "  1. Test your application at: http://$frontendUrl" -ForegroundColor White
    Write-Host "  2. Check API health at: http://${backendUrl}:8000/health" -ForegroundColor White
    Write-Host "  3. View API documentation at: http://${backendUrl}:8000/docs" -ForegroundColor White
    
    Write-Host "`nEstimated Monthly Cost: 15-25 USD" -ForegroundColor Green
    Write-Host "`nTo delete everything later:" -ForegroundColor Yellow
    Write-Host "  az group delete --name $ResourceGroup --yes --no-wait" -ForegroundColor White

} catch {
    Write-Error "Deployment failed: $_"
    Write-Host "`nCleanup command (if resources were created):" -ForegroundColor Yellow
    Write-Host "az group delete --name $ResourceGroup --yes --no-wait" -ForegroundColor White
    exit 1
}