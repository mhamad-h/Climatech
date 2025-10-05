import asyncio
import httpx
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
import numpy as np
from diskcache import Cache
import logging

from models.weather_data import HistoricalWeatherData, WindDirection
from utils.config import get_settings

logger = logging.getLogger(__name__)


class HistoricalDataService:
    """Service for fetching and processing historical weather data from NASA POWER API"""
    
    def __init__(self):
        self.settings = get_settings()
        self.cache = Cache(self.settings.cache_dir)
        self.base_url = "https://power.larc.nasa.gov/api/temporal/daily/point"
        
        # NASA POWER parameters mapping
        self.nasa_parameters = {
            "T2M_MAX": "temperature_max",      # Maximum Temperature at 2 Meters (C)
            "T2M_MIN": "temperature_min",      # Minimum Temperature at 2 Meters (C)
            "PRECTOTCORR": "precipitation",    # Precipitation Corrected (mm/day)
            "RH2M": "humidity",                # Relative Humidity at 2 Meters (%)
            "WS2M": "wind_speed",              # Wind Speed at 2 Meters (m/s)
            "WD2M": "wind_direction",          # Wind Direction at 2 Meters (Degrees)
            "PS": "pressure"                   # Surface Pressure (kPa)
        }
    
    async def fetch_historical_data(
        self, 
        latitude: float, 
        longitude: float,
        start_date: date,
        end_date: date,
        use_cache: bool = True
    ) -> List[HistoricalWeatherData]:
        """Fetch historical weather data from NASA POWER API"""
        
        cache_key = f"historical_{latitude}_{longitude}_{start_date}_{end_date}"
        
        if use_cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                logger.info(f"Using cached historical data for {latitude}, {longitude}")
                return cached_data
        
        try:
            parameters = ",".join(self.nasa_parameters.keys())
            
            url = (
                f"{self.base_url}"
                f"?parameters={parameters}"
                f"&community=RE"
                f"&longitude={longitude}"
                f"&latitude={latitude}"
                f"&start={start_date.strftime('%Y%m%d')}"
                f"&end={end_date.strftime('%Y%m%d')}"
                f"&format=JSON"
            )
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
            
            historical_records = self._parse_nasa_power_response(data)
            
            # Cache the results for 24 hours
            if use_cache:
                self.cache.set(cache_key, historical_records, expire=86400)
            
            logger.info(f"Fetched {len(historical_records)} historical records for {latitude}, {longitude}")
            return historical_records
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {str(e)}")
            raise
    
    def _parse_nasa_power_response(self, data: Dict) -> List[HistoricalWeatherData]:
        """Parse NASA POWER API response into HistoricalWeatherData objects"""
        
        try:
            parameters_data = data["properties"]["parameter"]
            
            # Get all dates from the first parameter
            first_param = list(parameters_data.keys())[0]
            dates = list(parameters_data[first_param].keys())
            
            records = []
            
            for date_str in dates:
                try:
                    record_date = datetime.strptime(date_str, "%Y%m%d").date()
                    
                    # Extract values for each parameter
                    temp_max = parameters_data.get("T2M_MAX", {}).get(date_str, np.nan)
                    temp_min = parameters_data.get("T2M_MIN", {}).get(date_str, np.nan)
                    precipitation = parameters_data.get("PRECTOTCORR", {}).get(date_str, np.nan)
                    humidity = parameters_data.get("RH2M", {}).get(date_str, np.nan)
                    wind_speed = parameters_data.get("WS2M", {}).get(date_str, np.nan)
                    wind_direction_degrees = parameters_data.get("WD2M", {}).get(date_str, np.nan)
                    pressure = parameters_data.get("PS", {}).get(date_str, np.nan)
                    
                    # Skip records with critical missing data
                    if any(np.isnan(val) or val == -999 for val in [temp_max, temp_min]):
                        continue
                    
                    # Handle missing values
                    precipitation = max(0, precipitation) if not np.isnan(precipitation) and precipitation != -999 else 0
                    humidity = max(0, min(100, humidity)) if not np.isnan(humidity) and humidity != -999 else 50
                    wind_speed = max(0, wind_speed) if not np.isnan(wind_speed) and wind_speed != -999 else 0
                    
                    # Convert wind direction to cardinal direction
                    wind_dir = self._degrees_to_cardinal(wind_direction_degrees) if not np.isnan(wind_direction_degrees) else None
                    
                    # Convert pressure from kPa to hPa if available
                    pressure_hpa = pressure * 10 if not np.isnan(pressure) and pressure != -999 else None
                    
                    record = HistoricalWeatherData(
                        date=record_date,
                        temperature_max=float(temp_max),
                        temperature_min=float(temp_min),
                        precipitation=float(precipitation),
                        humidity=float(humidity),
                        wind_speed=float(wind_speed),
                        wind_direction=wind_dir,
                        pressure=pressure_hpa
                    )
                    
                    records.append(record)
                    
                except Exception as e:
                    logger.warning(f"Error parsing record for date {date_str}: {str(e)}")
                    continue
            
            return records
            
        except Exception as e:
            logger.error(f"Error parsing NASA POWER response: {str(e)}")
            raise
    
    def _degrees_to_cardinal(self, degrees: float) -> Optional[WindDirection]:
        """Convert wind direction degrees to cardinal direction"""
        
        if np.isnan(degrees) or degrees < 0:
            return None
        
        # Normalize to 0-360
        degrees = degrees % 360
        
        directions = [
            WindDirection.N, WindDirection.NE, WindDirection.E, WindDirection.SE,
            WindDirection.S, WindDirection.SW, WindDirection.W, WindDirection.NW
        ]
        
        # Each direction covers 45 degrees, with N being 337.5-22.5
        direction_index = int((degrees + 22.5) / 45) % 8
        return directions[direction_index]
    
    async def get_last_n_years_data(
        self, 
        latitude: float, 
        longitude: float,
        years: int = 5
    ) -> List[HistoricalWeatherData]:
        """Get historical data for the last N years"""
        
        end_date = date.today() - timedelta(days=1)  # Yesterday
        start_date = date(end_date.year - years, 1, 1)
        
        return await self.fetch_historical_data(latitude, longitude, start_date, end_date)
    
    async def get_climatology_period_data(
        self, 
        latitude: float, 
        longitude: float,
        target_date: date,
        window_days: int = 30
    ) -> List[HistoricalWeatherData]:
        """Get historical data for climatology analysis around a specific date"""
        
        all_data = await self.get_last_n_years_data(latitude, longitude)
        
        target_doy = target_date.timetuple().tm_yday
        
        relevant_data = []
        for record in all_data:
            record_doy = record.date.timetuple().tm_yday
            
            # Calculate day difference considering year boundary
            day_diff = min(
                abs(record_doy - target_doy),
                abs(record_doy - target_doy - 365),
                abs(record_doy - target_doy + 365)
            )
            
            if day_diff <= window_days // 2:
                relevant_data.append(record)
        
        return relevant_data
    
    def calculate_data_completeness(
        self, 
        data: List[HistoricalWeatherData],
        expected_days: int
    ) -> float:
        """Calculate percentage of data completeness"""
        
        if expected_days == 0:
            return 100.0
        
        actual_days = len(data)
        return min(100.0, (actual_days / expected_days) * 100)
    
    def validate_data_quality(
        self, 
        data: List[HistoricalWeatherData]
    ) -> Dict[str, float]:
        """Validate and score data quality"""
        
        if not data:
            return {"overall_quality": 0.0, "completeness": 0.0, "consistency": 0.0}
        
        # Check for reasonable ranges
        temp_outliers = 0
        precip_outliers = 0
        humidity_outliers = 0
        
        for record in data:
            # Temperature checks
            if record.temperature_max < -50 or record.temperature_max > 60:
                temp_outliers += 1
            if record.temperature_min < -60 or record.temperature_min > 50:
                temp_outliers += 1
            if record.temperature_max < record.temperature_min:
                temp_outliers += 1
            
            # Precipitation checks
            if record.precipitation < 0 or record.precipitation > 500:  # 500mm in a day is extreme but possible
                precip_outliers += 1
            
            # Humidity checks
            if record.humidity < 0 or record.humidity > 100:
                humidity_outliers += 1
        
        total_records = len(data)
        temp_quality = 1.0 - (temp_outliers / (total_records * 3))  # 3 temp checks per record
        precip_quality = 1.0 - (precip_outliers / total_records)
        humidity_quality = 1.0 - (humidity_outliers / total_records)
        
        overall_quality = (temp_quality + precip_quality + humidity_quality) / 3
        
        # Check temporal consistency
        sorted_data = sorted(data, key=lambda x: x.date)
        date_gaps = 0
        
        for i in range(1, len(sorted_data)):
            expected_date = sorted_data[i-1].date + timedelta(days=1)
            if sorted_data[i].date != expected_date:
                date_gaps += 1
        
        consistency = 1.0 - (date_gaps / max(1, len(sorted_data) - 1))
        
        return {
            "overall_quality": max(0.0, min(1.0, overall_quality)) * 100,
            "completeness": 100.0,  # Calculated separately
            "consistency": max(0.0, min(1.0, consistency)) * 100,
            "temp_quality": max(0.0, min(1.0, temp_quality)) * 100,
            "precip_quality": max(0.0, min(1.0, precip_quality)) * 100,
            "humidity_quality": max(0.0, min(1.0, humidity_quality)) * 100
        }
    
    async def get_recent_conditions(
        self, 
        latitude: float, 
        longitude: float,
        days: int = 7
    ) -> List[HistoricalWeatherData]:
        """Get recent weather conditions for persistence forecasting"""
        
        end_date = date.today() - timedelta(days=1)
        start_date = end_date - timedelta(days=days)
        
        return await self.fetch_historical_data(latitude, longitude, start_date, end_date)