# Azure Deployment Guide for Climatech

## Prerequisites

1. **Azure Account**: Active Azure subscription
2. **Azure CLI**: Install from [https://aka.ms/installazurecliwindows](https://aka.ms/installazurecliwindows)
3. **Docker Desktop**: Install from [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)
4. **PowerShell**: Windows PowerShell 5.1+ or PowerShell Core 7+

## Quick Deployment (Recommended)

### Option 1: One-Click Deployment

```powershell
# Navigate to your project directory
cd "C:\Users\Admin\Documents\GeoClime\Climatech"

# Run the complete deployment script
.\deploy\deploy-to-azure.ps1
```

This script will:
- ✅ Create all Azure resources
- ✅ Build Docker images
- ✅ Push to Azure Container Registry
- ✅ Deploy both frontend and backend
- ✅ Configure networking and CORS
- ✅ Provide live URLs

### Option 2: Step-by-Step Deployment

If you prefer more control:

```powershell
# 1. Create Azure resources
.\deploy\azure-setup.ps1

# 2. Build and push images (update registry name first)
.\deploy\build-push.ps1

# 3. Deploy container apps (update registry name first)
.\deploy\deploy-apps.ps1
```

## Configuration

### Environment Variables

The deployment uses these environment variables:

**Backend:**
- `BACKEND_HOST=0.0.0.0`
- `BACKEND_PORT=8000`
- `ENVIRONMENT=production`
- `CORS_ORIGINS=<frontend-url>`

**Frontend:**
- `VITE_API_URL=<backend-api-url>`
- `NODE_ENV=production`

### Resource Specifications

**Backend Container:**
- CPU: 1.0 cores
- Memory: 2GB
- Min replicas: 1
- Max replicas: 3
- Port: 8000

**Frontend Container:**
- CPU: 0.5 cores
- Memory: 1GB
- Min replicas: 1
- Max replicas: 2
- Port: 80

## Post-Deployment

### 1. Test Your Application

After deployment, test these URLs:
- Frontend: `https://<your-frontend-url>`
- Backend Health: `https://<your-backend-url>/health`
- API Documentation: `https://<your-backend-url>/docs`

### 2. Monitor Resources

```powershell
# Check container app status
az containerapp show --name climatech-backend --resource-group climatech-rg

# View logs
az containerapp logs show --name climatech-backend --resource-group climatech-rg --follow

# Check resource usage
az containerapp revision list --name climatech-backend --resource-group climatech-rg --output table
```

### 3. Scale Applications

```powershell
# Scale backend
az containerapp update --name climatech-backend --resource-group climatech-rg --min-replicas 2 --max-replicas 5

# Scale frontend
az containerapp update --name climatech-frontend --resource-group climatech-rg --min-replicas 1 --max-replicas 3
```

## Custom Domain (Optional)

### 1. Add Custom Domain

```powershell
# Add custom domain to frontend
az containerapp hostname add --name climatech-frontend --resource-group climatech-rg --hostname "weather.yourdomain.com"

# Add SSL certificate
az containerapp ssl upload --name climatech-frontend --resource-group climatech-rg --hostname "weather.yourdomain.com" --certificate-file "path/to/cert.pfx"
```

### 2. Update DNS

Add CNAME record in your DNS provider:
```
weather.yourdomain.com -> <frontend-container-app-url>
```

## CI/CD Pipeline (Optional)

### GitHub Actions

Create `.github/workflows/azure-deploy.yml`:

```yaml
name: Deploy to Azure Container Apps

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Login to Azure
      uses: azure/login@v1
      with:
        creds: ${{ secrets.AZURE_CREDENTIALS }}
    
    - name: Build and Deploy
      run: |
        az acr build --registry climatechregistry --image climatech-backend:latest --file infra/Dockerfile.backend ./backend
        az acr build --registry climatechregistry --image climatech-frontend:latest --file infra/Dockerfile.frontend ./client
        az containerapp update --name climatech-backend --resource-group climatech-rg --image climatechregistry.azurecr.io/climatech-backend:latest
        az containerapp update --name climatech-frontend --resource-group climatech-rg --image climatechregistry.azurecr.io/climatech-frontend:latest
```

## Troubleshooting

### Common Issues

1. **Docker Build Fails**
   ```powershell
   # Ensure Docker is running
   docker version
   
   # Check Dockerfile paths
   ls infra/
   ```

2. **ACR Login Issues**
   ```powershell
   # Re-login to Azure
   az login --use-device-code
   
   # Re-login to ACR
   az acr login --name <registry-name>
   ```

3. **Container App Won't Start**
   ```powershell
   # Check logs
   az containerapp logs show --name climatech-backend --resource-group climatech-rg --follow
   
   # Check configuration
   az containerapp show --name climatech-backend --resource-group climatech-rg
   ```

4. **CORS Errors**
   ```powershell
   # Update CORS settings
   az containerapp update --name climatech-backend --resource-group climatech-rg --set-env-vars "CORS_ORIGINS=https://your-frontend-url"
   ```

### Health Checks

- Backend: `GET /health`
- Frontend: `GET /` (should return HTML)

### Logs

```powershell
# Real-time logs
az containerapp logs show --name climatech-backend --resource-group climatech-rg --follow

# Historical logs  
az containerapp logs show --name climatech-backend --resource-group climatech-rg --since 1h
```

## Cost Optimization

1. **Use spot instances** for development
2. **Scale to zero** during off-hours
3. **Monitor resource usage** and adjust specs
4. **Use Azure Cost Management** for tracking

## Security

1. **Enable managed identity** for inter-service communication
2. **Use Azure Key Vault** for secrets
3. **Enable HTTPS only**
4. **Configure network security groups**

## Cleanup

To delete all resources:

```powershell
az group delete --name climatech-rg --yes --no-wait
```

## Support

- Azure Container Apps: [Documentation](https://docs.microsoft.com/en-us/azure/container-apps/)
- Azure CLI: [Reference](https://docs.microsoft.com/en-us/cli/azure/)
- Issues: Create GitHub issues in your repository