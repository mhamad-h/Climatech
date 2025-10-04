import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from pathlib import Path
import json

import httpx
import pandas as pd
import numpy as np
from geopy.geocoders import Nominatim
from timezonefinder import TimezoneFinder

from utils.config import get_settings
from utils.logging import get_logger

logger = get_logger(__name__)


class DataFetchService:
    """Service for fetching weather and location data from various APIs."""
    
    def __init__(self):
        self.settings = get_settings()
        self.cache_dir = Path(self.settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize geocoding and timezone services
        self.geolocator = Nominatim(user_agent="climatech")
        self.timezone_finder = TimezoneFinder()
        
        # HTTP client configuration
        self.client = httpx.AsyncClient(
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
    
    async def get_location_info(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """
        Get comprehensive location information including elevation, timezone, and address.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            
        Returns:
            Dictionary containing location metadata
        """
        logger.info(f"Fetching location info for {latitude}, {longitude}")
        
        location_info = {
            "latitude": latitude,
            "longitude": longitude,
            "elevation": None,
            "timezone": None,
            "address": None
        }
        
        try:
            # Get elevation
            elevation = await self._get_elevation(latitude, longitude)
            location_info["elevation"] = elevation
            
            # Get timezone
            timezone = self.timezone_finder.timezone_at(lat=latitude, lng=longitude)
            location_info["timezone"] = timezone
            
            # Get address (optional, may be slow)
            try:
                location = self.geolocator.reverse(f"{latitude}, {longitude}", timeout=10)
                if location:
                    location_info["address"] = location.address
            except Exception as e:
                logger.warning(f"Failed to get address: {e}")
                
        except Exception as e:
            logger.error(f"Error getting location info: {e}")
            
        return location_info
    
    async def _get_elevation(self, latitude: float, longitude: float) -> Optional[float]:
        """Get elevation from Open Elevation API."""
        try:
            url = f"{self.settings.open_elevation_url}"
            params = {
                "locations": f"{latitude},{longitude}"
            }
            
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data and "results" in data and data["results"]:
                return data["results"][0]["elevation"]
                
        except Exception as e:
            logger.warning(f"Failed to get elevation: {e}")
            
        return None
    
    async def fetch_historical_data(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Fetch historical weather data from NASA POWER API.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees  
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            
        Returns:
            DataFrame with hourly weather data
        """
        logger.info(f"Fetching historical data for {latitude}, {longitude} from {start_date} to {end_date}")
        
        # Check cache first
        cache_key = f"historical_{latitude}_{longitude}_{start_date.date()}_{end_date.date()}"
        cached_data = self._load_from_cache(cache_key)
        if cached_data is not None:
            logger.info("Using cached historical data")
            return cached_data
        
        try:
            # Fetch from NASA POWER API
            data = await self._fetch_nasa_power_data(latitude, longitude, start_date, end_date)
            
            # Cache the result
            self._save_to_cache(cache_key, data)
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            # Return mock data as fallback
            return self._generate_mock_data(latitude, longitude, start_date, end_date)
    
    async def _fetch_nasa_power_data(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """Fetch data from NASA POWER API."""
        
        # Parameters for NASA POWER API
        parameters = [
            "T2M",          # Temperature at 2m
            "RH2M",         # Relative Humidity at 2m  
            "PS",           # Surface Pressure
            "PRECTOTCORR",  # Precipitation (corrected)
        ]
        
        url = self.settings.nasa_power_base_url
        params = {
            "parameters": ",".join(parameters),
            "community": "RE",
            "longitude": longitude,
            "latitude": latitude,
            "start": start_date.strftime("%Y%m%d"),
            "end": end_date.strftime("%Y%m%d"),
            "format": "JSON"
        }
        
        response = await self.client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Convert to DataFrame
        df_list = []
        properties = data.get("properties", {}).get("parameter", {})
        
        for param, values in properties.items():
            param_df = pd.DataFrame.from_dict(values, orient='index')
            param_df.columns = [param]
            param_df.index = pd.to_datetime(param_df.index, format='%Y%m%d%H')
            df_list.append(param_df)
        
        if df_list:
            df = pd.concat(df_list, axis=1)
            df = df.rename(columns={
                "T2M": "temperature_c",
                "RH2M": "humidity_percent", 
                "PS": "pressure_hpa",
                "PRECTOTCORR": "precipitation_mm"
            })
            df.index.name = "datetime"
            df = df.reset_index()
        else:
            # Fallback to mock data
            df = self._generate_mock_data(latitude, longitude, start_date, end_date)
            
        return df
    
    def _generate_mock_data(
        self,
        latitude: float,
        longitude: float,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """Generate realistic mock weather data."""
        
        # Create hourly time series
        dates = pd.date_range(start=start_date, end=end_date, freq='H')
        n_hours = len(dates)
        
        # Set random seed based on location for consistency
        np.random.seed(int(abs(latitude * longitude * 1000)) % 2**32)
        
        # Seasonal patterns
        day_of_year = dates.dayofyear
        seasonal_factor = np.sin(2 * np.pi * day_of_year / 365.25)
        
        # Diurnal patterns  
        hour_of_day = dates.hour
        diurnal_factor = np.sin(2 * np.pi * (hour_of_day - 6) / 24)  # Peak at 6 PM
        
        # Generate realistic weather data
        base_temp = 15 + 5 * np.sin(np.pi * latitude / 180)  # Latitude effect
        temperature = (base_temp + 
                      10 * seasonal_factor + 
                      5 * diurnal_factor + 
                      np.random.normal(0, 3, n_hours))
        
        base_humidity = 60 - 0.5 * abs(latitude)  # Lower humidity at poles
        humidity = np.clip(
            base_humidity + 20 * seasonal_factor + np.random.normal(0, 10, n_hours),
            0, 100
        )
        
        pressure = 1013 + np.random.normal(0, 10, n_hours)
        
        # Precipitation with seasonal and geographic patterns
        precip_prob = 0.1 + 0.1 * (1 + seasonal_factor) * (1 - abs(latitude) / 90)
        has_precip = np.random.random(n_hours) < precip_prob
        precipitation = np.where(
            has_precip,
            np.random.exponential(scale=2.0, size=n_hours),
            0.0
        )
        
        df = pd.DataFrame({
            'datetime': dates,
            'temperature_c': temperature,
            'humidity_percent': humidity,
            'pressure_hpa': pressure,
            'precipitation_mm': precipitation
        })
        
        return df
    
    def _load_from_cache(self, cache_key: str) -> Optional[pd.DataFrame]:
        """Load data from cache if available."""
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        
        if cache_file.exists():
            try:
                # Check if cache is not too old (7 days)
                if (datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)).days < 7:
                    return pd.read_parquet(cache_file)
            except Exception as e:
                logger.warning(f"Failed to load from cache: {e}")
        
        return None
    
    def _save_to_cache(self, cache_key: str, data: pd.DataFrame):
        """Save data to cache."""
        try:
            cache_file = self.cache_dir / f"{cache_key}.parquet"
            data.to_parquet(cache_file, index=False)
        except Exception as e:
            logger.warning(f"Failed to save to cache: {e}")
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()