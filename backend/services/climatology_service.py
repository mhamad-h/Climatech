import numpy as np
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Tuple, Optional, Any
from scipy import stats
from scipy.interpolate import interp1d
import math

from models.weather_data import (
    HistoricalWeatherData, WeatherForecast, ClimateNormal, 
    WeatherCondition, WindDirection, ConfidenceLevel
)


class ClimatologyService:
    """Service for climatological calculations and analysis"""
    
    def __init__(self):
        self.DAYS_IN_YEAR = 365
        self.CLIMATOLOGY_WINDOW = 30  # Days for rolling average
    
    def calculate_day_of_year_climatology(
        self, 
        historical_data: List[HistoricalWeatherData], 
        target_date: date
    ) -> ClimateNormal:
        """Calculate climate normal for a specific day of year"""
        
        target_doy = target_date.timetuple().tm_yday
        
        # Find all historical data within +/- 15 days of target day of year
        window_data = []
        
        for record in historical_data:
            record_doy = record.date.timetuple().tm_yday
            
            # Handle year boundary (e.g., Dec 31 and Jan 1)
            day_diff = min(
                abs(record_doy - target_doy),
                abs(record_doy - target_doy - 365),
                abs(record_doy - target_doy + 365)
            )
            
            if day_diff <= 15:  # Within 15-day window
                window_data.append(record)
        
        if not window_data:
            raise ValueError(f"No historical data found for day of year {target_doy}")
        
        # Calculate normals
        temp_max_values = [d.temperature_max for d in window_data]
        temp_min_values = [d.temperature_min for d in window_data]
        precip_values = [d.precipitation for d in window_data]
        humidity_values = [d.humidity for d in window_data]
        wind_values = [d.wind_speed for d in window_data]
        
        return ClimateNormal(
            date=target_date,
            temperature_max_normal=float(np.mean(temp_max_values)),
            temperature_min_normal=float(np.mean(temp_min_values)),
            precipitation_normal=float(np.mean(precip_values)),
            humidity_normal=float(np.mean(humidity_values)),
            wind_speed_normal=float(np.mean(wind_values)),
            precipitation_probability_normal=float(len([p for p in precip_values if p > 0.1]) / len(precip_values) * 100)
        )
    
    def calculate_seasonal_trends(
        self, 
        historical_data: List[HistoricalWeatherData]
    ) -> Dict[str, Any]:
        """Analyze seasonal patterns and trends"""
        
        df = pd.DataFrame([
            {
                'date': d.date,
                'doy': d.date.timetuple().tm_yday,
                'year': d.date.year,
                'month': d.date.month,
                'temp_max': d.temperature_max,
                'temp_min': d.temperature_min,
                'precipitation': d.precipitation,
                'humidity': d.humidity,
                'wind_speed': d.wind_speed
            }
            for d in historical_data
        ])
        
        # Calculate annual cycles
        monthly_means = df.groupby('month').agg({
            'temp_max': 'mean',
            'temp_min': 'mean',
            'precipitation': 'mean',
            'humidity': 'mean',
            'wind_speed': 'mean'
        }).round(2)
        
        # Calculate trends over years
        yearly_means = df.groupby('year').agg({
            'temp_max': 'mean',
            'temp_min': 'mean',
            'precipitation': 'sum',
            'humidity': 'mean',
            'wind_speed': 'mean'
        })
        
        trends = {}
        for param in ['temp_max', 'temp_min', 'precipitation', 'humidity', 'wind_speed']:
            slope, intercept, r_value, p_value, std_err = stats.linregress(
                yearly_means.index, yearly_means[param]
            )
            trends[param] = {
                'slope': float(slope),
                'r_squared': float(r_value**2),
                'p_value': float(p_value),
                'trend_per_decade': float(slope * 10)
            }
        
        return {
            'monthly_climatology': monthly_means.to_dict(),
            'annual_trends': trends,
            'data_years': sorted(df['year'].unique().tolist())
        }
    
    def persistence_forecast(
        self, 
        recent_data: List[HistoricalWeatherData], 
        forecast_date: date,
        days_ahead: int = 1
    ) -> Dict[str, float]:
        """Simple persistence forecasting - recent conditions continue"""
        
        if not recent_data:
            raise ValueError("No recent data available for persistence forecast")
        
        # Use last 7 days for persistence, with more weight on recent days
        recent_data = sorted(recent_data, key=lambda x: x.date, reverse=True)[:7]
        
        weights = np.exp(-0.2 * np.arange(len(recent_data)))  # Exponential decay
        weights = weights / weights.sum()
        
        temp_max = sum(w * d.temperature_max for w, d in zip(weights, recent_data))
        temp_min = sum(w * d.temperature_min for w, d in zip(weights, recent_data))
        precipitation = sum(w * d.precipitation for w, d in zip(weights, recent_data))
        humidity = sum(w * d.humidity for w, d in zip(weights, recent_data))
        wind_speed = sum(w * d.wind_speed for w, d in zip(weights, recent_data))
        
        # Reduce confidence for longer forecast periods
        confidence_decay = max(0.3, 1.0 - (days_ahead - 1) * 0.1)
        
        return {
            'temp_max': float(temp_max),
            'temp_min': float(temp_min),
            'precipitation': float(precipitation),
            'humidity': float(humidity),
            'wind_speed': float(wind_speed),
            'confidence': confidence_decay
        }
    
    def analog_forecast(
        self, 
        historical_data: List[HistoricalWeatherData],
        recent_conditions: List[HistoricalWeatherData],
        forecast_date: date
    ) -> Dict[str, float]:
        """Find similar historical patterns for forecasting"""
        
        if len(recent_conditions) < 3:
            return self.persistence_forecast(recent_conditions, forecast_date)
        
        # Create pattern signature from recent conditions
        recent_temps = [d.temperature_max + d.temperature_min for d in recent_conditions[-3:]]
        recent_precip = [d.precipitation for d in recent_conditions[-3:]]
        
        best_matches = []
        
        # Search for similar 3-day patterns in historical data
        for i in range(len(historical_data) - 4):
            hist_sequence = historical_data[i:i+3]
            
            # Skip if dates don't match season (within 45 days of year)
            target_doy = forecast_date.timetuple().tm_yday
            hist_doy = hist_sequence[0].date.timetuple().tm_yday
            
            if min(abs(hist_doy - target_doy), 365 - abs(hist_doy - target_doy)) > 45:
                continue
            
            # Calculate pattern similarity
            hist_temps = [d.temperature_max + d.temperature_min for d in hist_sequence]
            hist_precip = [d.precipitation for d in hist_sequence]
            
            temp_similarity = 1.0 / (1.0 + np.mean(np.abs(np.array(recent_temps) - np.array(hist_temps))))
            precip_similarity = 1.0 / (1.0 + np.mean(np.abs(np.array(recent_precip) - np.array(hist_precip))))
            
            overall_similarity = (temp_similarity + precip_similarity) / 2
            
            if overall_similarity > 0.3:  # Threshold for acceptable match
                # Get the day that followed this pattern
                if i + 3 < len(historical_data):
                    next_day = historical_data[i + 3]
                    best_matches.append((overall_similarity, next_day))
        
        if not best_matches:
            return self.persistence_forecast(recent_conditions, forecast_date)
        
        # Weight by similarity and average
        best_matches.sort(key=lambda x: x[0], reverse=True)
        top_matches = best_matches[:5]  # Use top 5 matches
        
        weights = np.array([match[0] for match in top_matches])
        weights = weights / weights.sum()
        
        temp_max = sum(w * match[1].temperature_max for w, match in zip(weights, top_matches))
        temp_min = sum(w * match[1].temperature_min for w, match in zip(weights, top_matches))
        precipitation = sum(w * match[1].precipitation for w, match in zip(weights, top_matches))
        humidity = sum(w * match[1].humidity for w, match in zip(weights, top_matches))
        wind_speed = sum(w * match[1].wind_speed for w, match in zip(weights, top_matches))
        
        return {
            'temp_max': float(temp_max),
            'temp_min': float(temp_min),
            'precipitation': float(precipitation),
            'humidity': float(humidity),
            'wind_speed': float(wind_speed),
            'confidence': float(np.mean(weights))
        }
    
    def determine_weather_conditions(
        self, 
        temp_max: float, 
        temp_min: float, 
        precipitation: float, 
        humidity: float, 
        wind_speed: float
    ) -> WeatherCondition:
        """Determine general weather conditions from parameters"""
        
        if precipitation > 20:
            return WeatherCondition.HEAVY_RAIN
        elif precipitation > 5:
            return WeatherCondition.MODERATE_RAIN
        elif precipitation > 0.5:
            return WeatherCondition.LIGHT_RAIN
        elif wind_speed > 15:
            return WeatherCondition.WINDY
        elif humidity > 90:
            return WeatherCondition.FOG
        elif humidity < 30:
            if (temp_max + temp_min) / 2 > 25:
                return WeatherCondition.SUNNY
            else:
                return WeatherCondition.PARTLY_CLOUDY
        elif humidity > 80:
            return WeatherCondition.OVERCAST
        elif humidity > 60:
            return WeatherCondition.CLOUDY
        else:
            return WeatherCondition.PARTLY_CLOUDY
    
    def determine_wind_direction(
        self, 
        historical_data: List[HistoricalWeatherData], 
        forecast_date: date
    ) -> WindDirection:
        """Determine most likely wind direction based on climatology"""
        
        # Get seasonal wind direction patterns
        target_month = forecast_date.month
        
        seasonal_directions = []
        for record in historical_data:
            if (record.date.month == target_month or 
                abs(record.date.month - target_month) <= 1) and record.wind_direction:
                seasonal_directions.append(record.wind_direction)
        
        if seasonal_directions:
            # Return most common direction for the season
            from collections import Counter
            direction_counts = Counter(seasonal_directions)
            return direction_counts.most_common(1)[0][0]
        
        # Default to prevailing wind direction if no seasonal data
        return WindDirection.W  # Westerly winds are most common globally
    
    def calculate_confidence_level(
        self, 
        forecast_method: str, 
        days_ahead: int, 
        data_quality: float,
        pattern_strength: float = 0.5
    ) -> ConfidenceLevel:
        """Calculate confidence level for forecast"""
        
        # Base confidence by method
        method_confidence = {
            'persistence': 0.8,
            'climatology': 0.7,
            'analog': 0.6,
            'trend': 0.5
        }
        
        base_conf = method_confidence.get(forecast_method, 0.5)
        
        # Decay confidence with forecast length
        time_decay = max(0.2, 1.0 - (days_ahead - 1) * 0.02)
        
        # Data quality factor
        data_factor = data_quality / 100.0
        
        # Pattern strength factor
        pattern_factor = max(0.3, pattern_strength)
        
        overall_confidence = base_conf * time_decay * data_factor * pattern_factor
        
        if overall_confidence > 0.8:
            return ConfidenceLevel.HIGH
        elif overall_confidence > 0.6:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW
    
    def seasonal_decomposition(
        self, 
        historical_data: List[HistoricalWeatherData]
    ) -> Dict[str, Any]:
        """Decompose time series into trend, seasonal, and residual components"""
        
        df = pd.DataFrame([
            {
                'date': d.date,
                'temp_max': d.temperature_max,
                'temp_min': d.temperature_min,
                'precipitation': d.precipitation
            }
            for d in historical_data
        ])
        
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        components = {}
        
        for param in ['temp_max', 'temp_min', 'precipitation']:
            # Simple seasonal decomposition
            # Calculate annual mean for trend
            yearly_means = df.groupby(df.index.year)[param].mean()
            
            # Calculate monthly seasonal component
            monthly_means = df.groupby(df.index.month)[param].mean()
            overall_mean = df[param].mean()
            seasonal_component = monthly_means - overall_mean
            
            # Linear trend
            years = np.array([d.year for d in df.index])
            values = df[param].values
            slope, intercept = np.polyfit(years, values, 1)
            
            components[param] = {
                'trend_slope': float(slope),
                'trend_intercept': float(intercept),
                'seasonal_cycle': seasonal_component.to_dict(),
                'overall_mean': float(overall_mean)
            }
        
        return components