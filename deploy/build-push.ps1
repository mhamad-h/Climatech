# Build and Push Docker Images to Azure Container Registry

# Variables - UPDATE THESE TO MATCH YOUR AZURE RESOURCES
$resourceGroup = "climatech-rg"
$registryName = "climatechregistryXXXX"  # Replace XXXX with your actual registry number
$backendImage = "climatech-backend"
$frontendImage = "climatech-frontend"

Write-Host "Building and pushing Docker images..." -ForegroundColor Green

# Get ACR login server
$acrLoginServer = az acr show --name $registryName --resource-group $resourceGroup --query loginServer --output tsv
Write-Host "ACR Login Server: $acrLoginServer" -ForegroundColor Cyan

# Login to ACR
Write-Host "Logging into Azure Container Registry..." -ForegroundColor Yellow
az acr login --name $registryName

# Build and push backend image
Write-Host "Building backend image..." -ForegroundColor Yellow
docker build -t "${acrLoginServer}/${backendImage}:latest" -f infra/Dockerfile.backend ./backend

Write-Host "Pushing backend image..." -ForegroundColor Yellow
docker push "${acrLoginServer}/${backendImage}:latest"

# Build and push frontend image
Write-Host "Building frontend image..." -ForegroundColor Yellow
docker build -t "${acrLoginServer}/${frontendImage}:latest" -f infra/Dockerfile.frontend ./client

Write-Host "Pushing frontend image..." -ForegroundColor Yellow
docker push "${acrLoginServer}/${frontendImage}:latest"

Write-Host "Docker images built and pushed successfully!" -ForegroundColor Green
Write-Host "Backend image: ${acrLoginServer}/${backendImage}:latest" -ForegroundColor Cyan
Write-Host "Frontend image: ${acrLoginServer}/${frontendImage}:latest" -ForegroundColor Cyan