from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:5173"
    
    # Azure Configuration
    azure_storage_connection_string: str = ""
    azure_key_vault_url: str = ""
    azure_app_insights_key: str = ""
    
    # Environment
    environment: str = "development"  # development, staging, production
    
    # Security
    secret_key: str = "climatech-secret-key-change-in-production"
    cors_allow_credentials: bool = True
    
    # NASA APIs
    nasa_power_base_url: str = "https://power.larc.nasa.gov/api/temporal/hourly/point"
    gpm_data_url: str = "https://gpm1.gesdisc.eosdis.nasa.gov/data/GPM_L3"
    
    # External APIs
    nominatim_url: str = "https://nominatim.openstreetmap.org"
    open_elevation_url: str = "https://api.open-elevation.com/api/v1/lookup"
    
    # Data and Caching
    cache_dir: str = "./data/cache"
    max_cache_size_gb: int = 5
    
    # Model Configuration
    model_retrain_interval_days: int = 30
    max_forecast_horizon_hours: int = 720  # 30 days
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "./logs/app.log"
    
    # CORS
    cors_origins: str = "*"  # Will be split on commas
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()