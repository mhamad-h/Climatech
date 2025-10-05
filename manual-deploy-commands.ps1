# Manual Azure Deployment Commands
# Run these commands one by one after installing Azure CLI

Write-Host "🌦️ Manual Azure Deployment for Climatech" -ForegroundColor Cyan
Write-Host "Run these commands one by one:" -ForegroundColor Yellow

Write-Host "`n1. Login to Azure:" -ForegroundColor Green
Write-Host "az login" -ForegroundColor White

Write-Host "`n2. Create resource group:" -ForegroundColor Green
Write-Host 'az group create --name "climatech-rg" --location "East US"' -ForegroundColor White

Write-Host "`n3. Create container registry:" -ForegroundColor Green
Write-Host 'az acr create --resource-group "climatech-rg" --name "climatechregistry2024" --sku Basic --admin-enabled true' -ForegroundColor White

Write-Host "`n4. Create container apps environment:" -ForegroundColor Green
Write-Host 'az containerapp env create --name "climatech-env" --resource-group "climatech-rg" --location "East US"' -ForegroundColor White

Write-Host "`n5. Login to container registry:" -ForegroundColor Green
Write-Host 'az acr login --name "climatechregistry2024"' -ForegroundColor White

Write-Host "`n6. Build and push backend image:" -ForegroundColor Green
Write-Host 'docker build -t "climatechregistry2024.azurecr.io/climatech-backend:latest" -f infra/Dockerfile.backend ./backend' -ForegroundColor White
Write-Host 'docker push "climatechregistry2024.azurecr.io/climatech-backend:latest"' -ForegroundColor White

Write-Host "`n7. Build and push frontend image:" -ForegroundColor Green
Write-Host 'docker build -t "climatechregistry2024.azurecr.io/climatech-frontend:latest" -f infra/Dockerfile.frontend ./client' -ForegroundColor White
Write-Host 'docker push "climatechregistry2024.azurecr.io/climatech-frontend:latest"' -ForegroundColor White

Write-Host "`n8. Get ACR credentials:" -ForegroundColor Green
Write-Host 'az acr credential show --name "climatechregistry2024" --resource-group "climatech-rg"' -ForegroundColor White

Write-Host "`n9. Deploy backend container app:" -ForegroundColor Green
Write-Host @'
az containerapp create \
  --name "climatech-backend" \
  --resource-group "climatech-rg" \
  --environment "climatech-env" \
  --image "climatechregistry2024.azurecr.io/climatech-backend:latest" \
  --target-port 8000 \
  --ingress external \
  --registry-server "climatechregistry2024.azurecr.io" \
  --registry-username "[FROM_STEP_8]" \
  --registry-password "[FROM_STEP_8]" \
  --env-vars "BACKEND_HOST=0.0.0.0" "BACKEND_PORT=8000" "ENVIRONMENT=production" \
  --cpu 1.0 \
  --memory 2Gi \
  --min-replicas 1 \
  --max-replicas 3
'@ -ForegroundColor White

Write-Host "`n10. Get backend URL:" -ForegroundColor Green
Write-Host 'az containerapp show --name "climatech-backend" --resource-group "climatech-rg" --query properties.configuration.ingress.fqdn --output tsv' -ForegroundColor White

Write-Host "`n11. Deploy frontend container app (replace BACKEND_URL):" -ForegroundColor Green
Write-Host @'
az containerapp create \
  --name "climatech-frontend" \
  --resource-group "climatech-rg" \
  --environment "climatech-env" \
  --image "climatechregistry2024.azurecr.io/climatech-frontend:latest" \
  --target-port 80 \
  --ingress external \
  --registry-server "climatechregistry2024.azurecr.io" \
  --registry-username "[FROM_STEP_8]" \
  --registry-password "[FROM_STEP_8]" \
  --env-vars "VITE_API_URL=https://[BACKEND_URL_FROM_STEP_10]/api" \
  --cpu 0.5 \
  --memory 1Gi \
  --min-replicas 1 \
  --max-replicas 2
'@ -ForegroundColor White

Write-Host "`n12. Get frontend URL:" -ForegroundColor Green
Write-Host 'az containerapp show --name "climatech-frontend" --resource-group "climatech-rg" --query properties.configuration.ingress.fqdn --output tsv' -ForegroundColor White

Write-Host "`n13. Update backend CORS (replace FRONTEND_URL):" -ForegroundColor Green
Write-Host 'az containerapp update --name "climatech-backend" --resource-group "climatech-rg" --set-env-vars "CORS_ORIGINS=https://[FRONTEND_URL_FROM_STEP_12]"' -ForegroundColor White

Write-Host "`n✅ After all steps, your app will be live!" -ForegroundColor Green