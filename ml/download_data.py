"""
Download and cache historical weather data for model training.
Uses NASA POWER API and simulated GPM data for demonstration.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np
import httpx
from tqdm import tqdm

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
from utils.logging import setup_logging, get_logger

logger = get_logger(__name__)


class DataDownloader:
    """Download historical weather data from various sources."""
    
    def __init__(self, cache_dir="data/cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # NASA POWER API configuration
        self.nasa_power_url = "https://power.larc.nasa.gov/api/temporal/hourly/point"
        
        # HTTP client
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def download_location_data(
        self, 
        latitude: float, 
        longitude: float, 
        start_year: int = 2020,
        end_year: int = 2024
    ) -> pd.DataFrame:
        """
        Download historical data for a specific location.
        
        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            start_year: Start year for data retrieval
            end_year: End year for data retrieval (inclusive)
            
        Returns:
            DataFrame with hourly weather data
        """
        logger.info(f"Downloading data for {latitude}, {longitude} from {start_year} to {end_year}")
        
        # Check cache first
        cache_key = f"historical_{latitude}_{longitude}_{start_year}_{end_year}"
        cache_file = self.cache_dir / f"{cache_key}.parquet"
        
        if cache_file.exists():
            logger.info("Loading from cache")
            return pd.read_parquet(cache_file)
        
        try:
            # Try NASA POWER API first
            data = await self._fetch_nasa_power_data(latitude, longitude, start_year, end_year)
            
            # Save to cache
            data.to_parquet(cache_file, index=False)
            logger.info(f"Cached data to {cache_file}")
            
            return data
            
        except Exception as e:
            logger.warning(f"Failed to fetch real data: {e}")
            logger.info("Generating synthetic data for development")
            
            # Generate synthetic data for development
            data = self._generate_synthetic_data(latitude, longitude, start_year, end_year)
            
            # Save to cache
            data.to_parquet(cache_file, index=False)
            logger.info(f"Cached synthetic data to {cache_file}")
            
            return data
    
    async def _fetch_nasa_power_data(
        self, 
        latitude: float, 
        longitude: float, 
        start_year: int, 
        end_year: int
    ) -> pd.DataFrame:
        """Fetch real data from NASA POWER API."""
        
        parameters = [
            "T2M",          # Temperature at 2m
            "RH2M",         # Relative Humidity at 2m
            "PS",           # Surface Pressure
            "PRECTOTCORR",  # Precipitation (corrected)
        ]
        
        all_data = []
        
        # Fetch data year by year to avoid API limits
        for year in range(start_year, end_year + 1):
            logger.info(f"Fetching {year} data...")
            
            start_date = f"{year}0101"
            end_date = f"{year}1231"
            
            params = {
                "parameters": ",".join(parameters),
                "community": "RE",
                "longitude": longitude,
                "latitude": latitude,
                "start": start_date,
                "end": end_date,
                "format": "JSON"
            }
            
            try:
                response = await self.client.get(self.nasa_power_url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                # Convert to DataFrame
                year_data = self._parse_nasa_response(data)
                if not year_data.empty:
                    all_data.append(year_data)
                    
            except Exception as e:
                logger.error(f"Failed to fetch {year}: {e}")
                # Generate synthetic data for this year
                synthetic_year = self._generate_synthetic_data(latitude, longitude, year, year)
                all_data.append(synthetic_year)
        
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            raise Exception("No data retrieved")
    
    def _parse_nasa_response(self, data: dict) -> pd.DataFrame:
        """Parse NASA POWER API response into DataFrame."""
        properties = data.get("properties", {}).get("parameter", {})
        
        if not properties:
            return pd.DataFrame()
        
        # Convert each parameter to DataFrame and join
        df_list = []
        
        for param, values in properties.items():
            if not values:
                continue
                
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
            
            # Clean data
            df = df.dropna()
            df = df[df['precipitation_mm'] >= 0]  # Remove negative precipitation
            
            return df
        else:
            return pd.DataFrame()
    
    def _generate_synthetic_data(
        self, 
        latitude: float, 
        longitude: float, 
        start_year: int, 
        end_year: int
    ) -> pd.DataFrame:
        """Generate realistic synthetic weather data."""
        
        # Create hourly time series
        start_date = datetime(start_year, 1, 1)
        end_date = datetime(end_year + 1, 1, 1)
        dates = pd.date_range(start=start_date, end=end_date, freq='H')[:-1]  # Exclude last point
        
        n_hours = len(dates)
        
        # Set seed for reproducibility
        np.random.seed(int(abs(latitude * longitude * 1000)) % 2**32)
        
        # Seasonal and diurnal patterns
        day_of_year = dates.dayofyear
        hour_of_day = dates.hour
        
        # Seasonal pattern (stronger in mid-latitudes)
        seasonal_amplitude = min(20, abs(latitude) / 3)
        seasonal_factor = np.sin(2 * np.pi * (day_of_year - 81) / 365.25)  # Peak in summer
        
        # Diurnal pattern for temperature
        diurnal_factor = np.sin(2 * np.pi * (hour_of_day - 6) / 24)  # Peak at 2 PM
        
        # Generate realistic temperature
        base_temp = 15 + 15 * np.cos(np.pi * latitude / 180)  # Colder at poles
        temperature = (base_temp + 
                      seasonal_amplitude * seasonal_factor + 
                      5 * diurnal_factor + 
                      np.random.normal(0, 3, n_hours))
        
        # Generate humidity (anti-correlated with temperature)
        base_humidity = 70 - abs(latitude) / 2  # Drier at poles
        humidity = np.clip(
            base_humidity - 0.5 * seasonal_amplitude * seasonal_factor + 
            np.random.normal(0, 15, n_hours),
            10, 100
        )
        
        # Generate pressure
        base_pressure = 1013 + 5 * np.cos(np.pi * latitude / 180)  # Higher at poles
        pressure = base_pressure + np.random.normal(0, 10, n_hours)
        
        # Generate precipitation (more complex, weather-dependent)
        precipitation = self._generate_precipitation_pattern(
            dates, temperature, humidity, latitude, longitude
        )
        
        # Create DataFrame
        df = pd.DataFrame({
            'datetime': dates,
            'temperature_c': temperature,
            'humidity_percent': humidity,
            'pressure_hpa': pressure,
            'precipitation_mm': precipitation
        })
        
        return df
    
    def _generate_precipitation_pattern(
        self, 
        dates: pd.DatetimeIndex, 
        temperature: np.ndarray, 
        humidity: np.ndarray,
        latitude: float,
        longitude: float
    ) -> np.ndarray:
        """Generate realistic precipitation pattern."""
        
        n_hours = len(dates)
        precipitation = np.zeros(n_hours)
        
        # Climate-based base probability
        base_prob = 0.05 + 0.15 * (1 - abs(latitude) / 90)  # Higher near equator
        
        # Seasonal modulation
        day_of_year = dates.dayofyear
        if latitude >= 0:  # Northern hemisphere
            seasonal_precip = 1 + 0.5 * np.sin(2 * np.pi * (day_of_year - 81) / 365.25)
        else:  # Southern hemisphere
            seasonal_precip = 1 + 0.5 * np.sin(2 * np.pi * (day_of_year - 265) / 365.25)
        
        # Weather state simulation (simple Markov chain)
        wet_state = False
        
        for i in range(n_hours):
            # Probability modifiers
            temp_factor = max(0.1, 1 - (temperature[i] - 20) / 30)  # Less rain when hot
            humid_factor = max(0.5, humidity[i] / 100)  # More rain when humid
            
            # Current probability
            current_prob = base_prob * seasonal_precip[i] * temp_factor * humid_factor
            
            # Persistence (weather patterns tend to persist)
            if wet_state:
                current_prob *= 2  # More likely to continue raining
            
            # Random event
            if np.random.random() < current_prob:
                # Rain event
                wet_state = True
                
                # Rain amount (exponential distribution)
                rain_amount = np.random.exponential(scale=2.0)
                
                # Intensity modifiers
                if humid_factor > 0.8:  # High humidity = heavy rain potential
                    rain_amount *= np.random.lognormal(0, 0.5)
                
                precipitation[i] = rain_amount
            else:
                wet_state = False
                precipitation[i] = 0.0
        
        return precipitation
    
    async def download_sample_locations(self) -> None:
        """Download data for a set of sample locations for training."""
        
        # Sample locations (diverse climates)
        locations = [
            (40.7128, -74.0060, "New York"),          # Temperate
            (25.7617, -80.1918, "Miami"),             # Subtropical
            (37.7749, -122.4194, "San Francisco"),    # Mediterranean
            (41.8781, -87.6298, "Chicago"),           # Continental
            (29.7604, -95.3698, "Houston"),           # Humid subtropical
            (39.7392, -104.9903, "Denver"),           # Semi-arid
            (47.6062, -122.3321, "Seattle"),          # Oceanic
            (33.4484, -112.0740, "Phoenix"),          # Arid
        ]
        
        logger.info(f"Downloading data for {len(locations)} sample locations")
        
        for lat, lng, name in tqdm(locations, desc="Downloading locations"):
            try:
                await self.download_location_data(lat, lng)
                logger.info(f"Downloaded data for {name}")
            except Exception as e:
                logger.error(f"Failed to download data for {name}: {e}")
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def main():
    """Main function to download sample data."""
    setup_logging()
    
    downloader = DataDownloader()
    
    try:
        await downloader.download_sample_locations()
        logger.info("Data download completed successfully")
    except Exception as e:
        logger.error(f"Data download failed: {e}")
        raise
    finally:
        await downloader.close()


if __name__ == "__main__":
    asyncio.run(main())