# Deploy Container Apps to Azure

# Variables - UPDATE THESE TO MATCH YOUR AZURE RESOURCES
$resourceGroup = "climatech-rg"
$containerAppEnv = "climatech-env"
$registryName = "climatechregistryXXXX"  # Replace XXXX with your actual registry number
$backendApp = "climatech-backend"
$frontendApp = "climatech-frontend"

Write-Host "Deploying Container Apps..." -ForegroundColor Green

# Get ACR details
$acrLoginServer = az acr show --name $registryName --resource-group $resourceGroup --query loginServer --output tsv
$acrUsername = az acr credential show --name $registryName --resource-group $resourceGroup --query username --output tsv
$acrPassword = az acr credential show --name $registryName --resource-group $resourceGroup --query passwords[0].value --output tsv

Write-Host "ACR Details:" -ForegroundColor Cyan
Write-Host "  Login Server: $acrLoginServer" -ForegroundColor White
Write-Host "  Username: $acrUsername" -ForegroundColor White

# Deploy backend container app
Write-Host "Deploying backend container app..." -ForegroundColor Yellow
az containerapp create `
  --name $backendApp `
  --resource-group $resourceGroup `
  --environment $containerAppEnv `
  --image "${acrLoginServer}/climatech-backend:latest" `
  --target-port 8000 `
  --ingress external `
  --registry-server $acrLoginServer `
  --registry-username $acrUsername `
  --registry-password $acrPassword `
  --env-vars "BACKEND_HOST=0.0.0.0" "BACKEND_PORT=8000" "ENVIRONMENT=production" "CORS_ORIGINS=*" `
  --cpu 1.0 `
  --memory 2Gi `
  --min-replicas 1 `
  --max-replicas 3

# Get backend URL
$backendUrl = az containerapp show --name $backendApp --resource-group $resourceGroup --query properties.configuration.ingress.fqdn --output tsv
$backendApiUrl = "https://$backendUrl/api"

Write-Host "Backend deployed successfully!" -ForegroundColor Green
Write-Host "Backend URL: https://$backendUrl" -ForegroundColor Cyan

# Deploy frontend container app
Write-Host "Deploying frontend container app..." -ForegroundColor Yellow
az containerapp create `
  --name $frontendApp `
  --resource-group $resourceGroup `
  --environment $containerAppEnv `
  --image "${acrLoginServer}/climatech-frontend:latest" `
  --target-port 80 `
  --ingress external `
  --registry-server $acrLoginServer `
  --registry-username $acrUsername `
  --registry-password $acrPassword `
  --env-vars "VITE_API_URL=$backendApiUrl" "NODE_ENV=production" `
  --cpu 0.5 `
  --memory 1Gi `
  --min-replicas 1 `
  --max-replicas 2

# Get frontend URL
$frontendUrl = az containerapp show --name $frontendApp --resource-group $resourceGroup --query properties.configuration.ingress.fqdn --output tsv

Write-Host "Frontend deployed successfully!" -ForegroundColor Green
Write-Host "Frontend URL: https://$frontendUrl" -ForegroundColor Cyan

# Update backend CORS settings with frontend URL
Write-Host "Updating backend CORS settings..." -ForegroundColor Yellow
az containerapp update `
  --name $backendApp `
  --resource-group $resourceGroup `
  --set-env-vars "CORS_ORIGINS=https://$frontendUrl"

Write-Host "Deployment completed successfully!" -ForegroundColor Green
Write-Host "" -ForegroundColor White
Write-Host "🌦️ Climatech Application URLs:" -ForegroundColor Cyan
Write-Host "  Frontend: https://$frontendUrl" -ForegroundColor White
Write-Host "  Backend:  https://$backendUrl" -ForegroundColor White
Write-Host "  API Docs: https://$backendUrl/docs" -ForegroundColor White
Write-Host "" -ForegroundColor White
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Test your application at the frontend URL" -ForegroundColor White
Write-Host "2. Set up custom domain (optional)" -ForegroundColor White
Write-Host "3. Configure monitoring and logging" -ForegroundColor White