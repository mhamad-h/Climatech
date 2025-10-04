from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # API Configuration
    backend_host: str = "localhost"
    backend_port: int = 8000
    frontend_url: str = "http://localhost:5173"
    
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
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()