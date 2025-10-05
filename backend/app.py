import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from routers import climatology
from utils.config import get_settings
from utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting Climatech API server")
    
    # Create necessary directories
    os.makedirs("data/cache", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("models", exist_ok=True)
    
    yield
    
    # Shutdown
    logger.info("Shutting down Climatech API server")


# Create FastAPI app
app = FastAPI(
    title="Climatech Weather Forecasting API",
    description="A comprehensive climatology-based weather forecasting API using NASA historical data and proven meteorological methods",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Get settings
settings = get_settings()

# Configure CORS with environment-specific settings
if settings.cors_origins == "*":
    cors_origins = ["*"]
else:
    # Split comma-separated origins
    cors_origins = [origin.strip() for origin in settings.cors_origins.split(",")]

if settings.environment == "production":
    # In production, be more specific about allowed origins
    cors_origins = [
        settings.frontend_url,
        settings.production_frontend_url if hasattr(settings, 'production_frontend_url') else None,
        "http://climatech-frontend-7057.eastus.azurecontainer.io",
        "https://*.azurecontainerapps.io",
        "https://*.azure.com"
    ]
    # Remove None values
    cors_origins = [origin for origin in cors_origins if origin is not None]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(climatology.router, prefix="/api", tags=["climatology", "forecasting"])


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Climatech Weather Forecasting API",
        "version": "2.0.0", 
        "docs": "/docs",
        "status": "running",
        "methods": ["persistence", "analog", "climatology"],
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler."""
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=True,
        log_level="info"
    )