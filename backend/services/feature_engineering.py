import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler

from utils.logging import get_logger

logger = get_logger(__name__)


class FeatureEngineeringService:
    """Service for generating features for precipitation forecasting."""
    
    def __init__(self):
        self.scaler = StandardScaler()
    
    def generate_features(
        self,
        historical_data: pd.DataFrame,
        forecast_start: datetime,
        horizon_hours: int,
        latitude: float,
        longitude: float,
        elevation: float = None
    ) -> pd.DataFrame:
        """
        Generate comprehensive features for precipitation forecasting.
        
        Args:
            historical_data: Historical weather data
            forecast_start: Start time for forecast
            horizon_hours: Number of hours to forecast
            latitude: Location latitude
            longitude: Location longitude
            elevation: Location elevation in meters
            
        Returns:
            DataFrame with engineered features
        """
        logger.info(f"Generating features for forecast starting {forecast_start}")
        
        # Create forecast time grid
        forecast_times = pd.date_range(
            start=forecast_start,
            periods=horizon_hours,
            freq='H'
        )
        
        # Initialize feature DataFrame
        features_df = pd.DataFrame({'datetime': forecast_times})
        
        # Add temporal features
        features_df = self._add_temporal_features(features_df)
        
        # Add location features
        features_df = self._add_location_features(features_df, latitude, longitude, elevation)
        
        # Add climatological features
        features_df = self._add_climatology_features(features_df, historical_data)
        
        # Add lagged precipitation features
        features_df = self._add_lagged_features(features_df, historical_data)
        
        # Add recent anomaly features
        features_df = self._add_anomaly_features(features_df, historical_data)
        
        # Add meteorological features (if available)
        features_df = self._add_meteorological_features(features_df, historical_data)
        
        # Add forecast horizon feature
        features_df['forecast_horizon'] = range(1, horizon_hours + 1)
        
        logger.info(f"Generated {len(features_df.columns)} features for {len(features_df)} time steps")
        
        return features_df
    
    def _add_temporal_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add temporal cyclical features."""
        df = df.copy()
        
        # Hour of day (cyclical)
        df['hour_of_day_sin'] = np.sin(2 * np.pi * df['datetime'].dt.hour / 24)
        df['hour_of_day_cos'] = np.cos(2 * np.pi * df['datetime'].dt.hour / 24)
        
        # Day of year (cyclical)
        df['day_of_year_sin'] = np.sin(2 * np.pi * df['datetime'].dt.dayofyear / 365.25)
        df['day_of_year_cos'] = np.cos(2 * np.pi * df['datetime'].dt.dayofyear / 365.25)
        
        # Week of year
        df['week_of_year'] = df['datetime'].dt.isocalendar().week
        
        # Day of week (cyclical)
        df['day_of_week_sin'] = np.sin(2 * np.pi * df['datetime'].dt.dayofweek / 7)
        df['day_of_week_cos'] = np.cos(2 * np.pi * df['datetime'].dt.dayofweek / 7)
        
        # Is weekend
        df['is_weekend'] = (df['datetime'].dt.dayofweek >= 5).astype(int)
        
        # Month (cyclical)
        df['month_sin'] = np.sin(2 * np.pi * df['datetime'].dt.month / 12)
        df['month_cos'] = np.cos(2 * np.pi * df['datetime'].dt.month / 12)
        
        return df
    
    def _add_location_features(
        self,
        df: pd.DataFrame,
        latitude: float,
        longitude: float,
        elevation: float = None
    ) -> pd.DataFrame:
        """Add location-based features."""
        df = df.copy()
        
        df['latitude'] = latitude
        df['longitude'] = longitude
        df['elevation'] = elevation or 0.0
        
        # Distance from equator
        df['abs_latitude'] = abs(latitude)
        
        # Hemisphere
        df['northern_hemisphere'] = int(latitude >= 0)
        
        # Coastal proximity (rough approximation)
        df['coastal_proximity'] = np.exp(-abs(longitude) / 20)  # Simple approximation
        
        return df
    
    def _add_climatology_features(
        self,
        df: pd.DataFrame,
        historical_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Add climatological baseline features."""
        df = df.copy()
        
        if historical_data.empty:
            # Default values if no historical data
            df['climatology_precip_hourly'] = 0.5
            df['climatology_precip_daily'] = 2.0
            df['climatology_precip_prob'] = 0.2
            return df
        
        # Ensure datetime column
        if 'datetime' not in historical_data.columns:
            historical_data = historical_data.reset_index()
        
        # Convert to datetime if needed
        historical_data['datetime'] = pd.to_datetime(historical_data['datetime'])
        
        # Add hour and day of year to historical data
        historical_data['hour'] = historical_data['datetime'].dt.hour
        historical_data['dayofyear'] = historical_data['datetime'].dt.dayofyear
        
        # Calculate climatological precipitation by hour and day of year
        if 'precipitation_mm' in historical_data.columns:
            # Hourly climatology
            hourly_clim = historical_data.groupby(['dayofyear', 'hour'])['precipitation_mm'].agg([
                'mean', 'std', lambda x: (x > 0).mean()
            ]).reset_index()
            hourly_clim.columns = ['dayofyear', 'hour', 'clim_mean', 'clim_std', 'clim_prob']
            
            # Add to forecast DataFrame
            df['hour'] = df['datetime'].dt.hour
            df['dayofyear'] = df['datetime'].dt.dayofyear
            
            df = df.merge(hourly_clim, on=['dayofyear', 'hour'], how='left')
            
            # Fill missing values with overall means
            overall_mean = historical_data['precipitation_mm'].mean()
            overall_std = historical_data['precipitation_mm'].std()
            overall_prob = (historical_data['precipitation_mm'] > 0).mean()
            
            df['climatology_precip_hourly'] = df['clim_mean'].fillna(overall_mean)
            df['climatology_precip_std'] = df['clim_std'].fillna(overall_std)
            df['climatology_precip_prob'] = df['clim_prob'].fillna(overall_prob)
            
            # Daily climatology (rolling 7-day window)
            daily_clim = historical_data.groupby('dayofyear')['precipitation_mm'].sum().reset_index()
            daily_clim['precip_7day'] = daily_clim['precipitation_mm'].rolling(
                window=7, center=True, min_periods=1
            ).mean()
            
            df = df.merge(daily_clim[['dayofyear', 'precip_7day']], on='dayofyear', how='left')
            df['climatology_precip_daily'] = df['precip_7day'].fillna(overall_mean * 24)
            
            # Clean up temporary columns
            df = df.drop(columns=['clim_mean', 'clim_std', 'clim_prob', 'precip_7day', 'hour'], errors='ignore')
        
        return df
    
    def _add_lagged_features(
        self,
        df: pd.DataFrame,
        historical_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Add lagged precipitation features."""
        df = df.copy()
        
        if historical_data.empty or 'precipitation_mm' not in historical_data.columns:
            # Default values
            for lag in [1, 3, 6, 12, 24, 48, 72]:
                df[f'precip_lag_{lag}h'] = 0.0
                df[f'precip_sum_{lag}h'] = 0.0
            return df
        
        # Get the most recent precipitation data
        historical_data = historical_data.sort_values('datetime')
        most_recent_time = historical_data['datetime'].max()
        
        # Calculate lags relative to forecast start
        forecast_start = df['datetime'].min()
        
        # Ensure timezone compatibility 
        if hasattr(forecast_start, 'tz_localize') and forecast_start.tz is not None:
            # If forecast_start is timezone-aware, make historical data tz-aware too
            if historical_data['datetime'].dt.tz is None:
                historical_data = historical_data.copy()
                historical_data['datetime'] = historical_data['datetime'].dt.tz_localize('UTC')
        
        lag_hours = [1, 3, 6, 12, 24, 48, 72]
        
        for lag in lag_hours:
            lag_time = forecast_start - timedelta(hours=lag)
            
            # Find closest historical observation
            time_diffs = abs(historical_data['datetime'] - lag_time)
            closest_idx = time_diffs.idxmin()
            
            if time_diffs.loc[closest_idx] < timedelta(hours=3):  # Within 3 hours
                lag_value = historical_data.loc[closest_idx, 'precipitation_mm']
            else:
                lag_value = 0.0
            
            df[f'precip_lag_{lag}h'] = lag_value
            
            # Rolling sum for the lag period
            end_time = forecast_start
            start_time = end_time - timedelta(hours=lag)
            
            period_data = historical_data[
                (historical_data['datetime'] >= start_time) & 
                (historical_data['datetime'] < end_time)
            ]
            
            if not period_data.empty:
                rolling_sum = period_data['precipitation_mm'].sum()
            else:
                rolling_sum = 0.0
            
            df[f'precip_sum_{lag}h'] = rolling_sum
        
        return df
    
    def _add_anomaly_features(
        self,
        df: pd.DataFrame,
        historical_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Add recent anomaly features."""
        df = df.copy()
        
        if historical_data.empty or 'precipitation_mm' not in historical_data.columns:
            df['precip_anomaly_24h'] = 0.0
            df['precip_anomaly_7d'] = 0.0
            return df
        
        forecast_start = df['datetime'].min()
        
        # Recent 24-hour precipitation
        recent_24h = historical_data[
            historical_data['datetime'] >= forecast_start - timedelta(hours=24)
        ]['precipitation_mm'].sum()
        
        # Recent 7-day precipitation
        recent_7d = historical_data[
            historical_data['datetime'] >= forecast_start - timedelta(days=7)
        ]['precipitation_mm'].sum()
        
        # Historical averages for same periods
        dayofyear = forecast_start.timetuple().tm_yday
        
        # Get similar days (±7 days) from historical record
        similar_days = historical_data[
            abs(historical_data['datetime'].dt.dayofyear - dayofyear) <= 7
        ]
        
        if not similar_days.empty:
            hist_24h_mean = similar_days.groupby(similar_days['datetime'].dt.date)['precipitation_mm'].sum().mean()
            hist_7d_mean = similar_days['precipitation_mm'].sum() / len(similar_days['datetime'].dt.date.unique()) * 7
        else:
            hist_24h_mean = historical_data['precipitation_mm'].sum() / len(historical_data) * 24
            hist_7d_mean = historical_data['precipitation_mm'].sum() / len(historical_data) * 24 * 7
        
        df['precip_anomaly_24h'] = recent_24h - hist_24h_mean
        df['precip_anomaly_7d'] = recent_7d - hist_7d_mean
        
        return df
    
    def _add_meteorological_features(
        self,
        df: pd.DataFrame,
        historical_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Add meteorological features if available."""
        df = df.copy()
        
        # Default values
        met_features = {
            'temperature_c': 15.0,
            'humidity_percent': 60.0,
            'pressure_hpa': 1013.0,
            'temperature_trend': 0.0,
            'pressure_trend': 0.0
        }
        
        if historical_data.empty:
            for feature, default_val in met_features.items():
                df[feature] = default_val
            return df
        
        # Use most recent meteorological conditions
        historical_data = historical_data.sort_values('datetime')
        latest_data = historical_data.iloc[-1]
        
        # Current conditions (use latest available)
        if 'temperature_c' in historical_data.columns:
            df['temperature_c'] = latest_data.get('temperature_c', 15.0)
        else:
            df['temperature_c'] = 15.0
            
        if 'humidity_percent' in historical_data.columns:
            df['humidity_percent'] = latest_data.get('humidity_percent', 60.0)
        else:
            df['humidity_percent'] = 60.0
            
        if 'pressure_hpa' in historical_data.columns:
            df['pressure_hpa'] = latest_data.get('pressure_hpa', 1013.0)
        else:
            df['pressure_hpa'] = 1013.0
        
        # Trends (change over last 24 hours)
        recent_24h = historical_data[
            historical_data['datetime'] >= historical_data['datetime'].max() - timedelta(hours=24)
        ]
        
        if len(recent_24h) > 1:
            if 'temperature_c' in recent_24h.columns:
                temp_trend = recent_24h['temperature_c'].iloc[-1] - recent_24h['temperature_c'].iloc[0]
                df['temperature_trend'] = temp_trend
            else:
                df['temperature_trend'] = 0.0
                
            if 'pressure_hpa' in recent_24h.columns:
                pressure_trend = recent_24h['pressure_hpa'].iloc[-1] - recent_24h['pressure_hpa'].iloc[0]
                df['pressure_trend'] = pressure_trend
            else:
                df['pressure_trend'] = 0.0
        else:
            df['temperature_trend'] = 0.0
            df['pressure_trend'] = 0.0
        
        return df