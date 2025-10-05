# Azure deployment script
# This script deploys Climatech to Azure Container Apps

# Variables
$RESOURCE_GROUP = "climatech-rg"
$LOCATION = "eastus"
$ACR_NAME = "climatechregistry"
$CONTAINER_APP_ENV = "climatech-env"

# Login to Azure
Write-Host "Logging into Azure..."
az login

# Create Resource Group
Write-Host "Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Container Registry
Write-Host "Creating Azure Container Registry..."
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true

# Get ACR credentials
$ACR_SERVER = az acr show --name $ACR_NAME --query loginServer --output tsv
$ACR_USERNAME = az acr credential show --name $ACR_NAME --query username --output tsv
$ACR_PASSWORD = az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv

# Build and push Docker images
Write-Host "Building and pushing Docker images..."

# Backend
Write-Host "Building backend image..."
docker build -t "$ACR_SERVER/climatech-backend:latest" -f infra/Dockerfile.backend ./backend
az acr login --name $ACR_NAME
docker push "$ACR_SERVER/climatech-backend:latest"

# Frontend
Write-Host "Building frontend image..."
docker build -t "$ACR_SERVER/climatech-frontend:latest" -f infra/Dockerfile.frontend ./client
docker push "$ACR_SERVER/climatech-frontend:latest"

# Create Container Apps Environment
Write-Host "Creating Container Apps Environment..."
az containerapp env create --name $CONTAINER_APP_ENV --resource-group $RESOURCE_GROUP --location $LOCATION

# Deploy Backend Container App
Write-Host "Deploying backend container app..."
az containerapp create `
  --name "climatech-backend" `
  --resource-group $RESOURCE_GROUP `
  --environment $CONTAINER_APP_ENV `
  --image "$ACR_SERVER/climatech-backend:latest" `
  --target-port 8000 `
  --ingress external `
  --registry-server $ACR_SERVER `
  --registry-username $ACR_USERNAME `
  --registry-password $ACR_PASSWORD `
  --env-vars "BACKEND_HOST=0.0.0.0" "BACKEND_PORT=8000" "ENVIRONMENT=production" `
  --cpu 0.5 --memory 1Gi `
  --min-replicas 1 --max-replicas 10

# Get backend URL
$BACKEND_URL = az containerapp show --name "climatech-backend" --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn --output tsv
$BACKEND_URL = "https://$BACKEND_URL"

# Deploy Frontend Container App
Write-Host "Deploying frontend container app..."
az containerapp create `
  --name "climatech-frontend" `
  --resource-group $RESOURCE_GROUP `
  --environment $CONTAINER_APP_ENV `
  --image "$ACR_SERVER/climatech-frontend:latest" `
  --target-port 80 `
  --ingress external `
  --registry-server $ACR_SERVER `
  --registry-username $ACR_USERNAME `
  --registry-password $ACR_PASSWORD `
  --env-vars "REACT_APP_API_URL=$BACKEND_URL" `
  --cpu 0.25 --memory 0.5Gi `
  --min-replicas 1 --max-replicas 5

# Get frontend URL
$FRONTEND_URL = az containerapp show --name "climatech-frontend" --resource-group $RESOURCE_GROUP --query properties.configuration.ingress.fqdn --output tsv

Write-Host "Deployment completed!"
Write-Host "Frontend URL: https://$FRONTEND_URL"
Write-Host "Backend URL: $BACKEND_URL"

# Update backend with correct frontend URL
Write-Host "Updating backend with frontend URL..."
az containerapp update `
  --name "climatech-backend" `
  --resource-group $RESOURCE_GROUP `
  --set-env-vars "FRONTEND_URL=https://$FRONTEND_URL"

Write-Host "Climatech has been successfully deployed to Azure!"
Write-Host "Access your application at: https://$FRONTEND_URL"