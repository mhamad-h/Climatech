"""
Feature definitions for precipitation forecasting.
Defines all the feature engineering functions used across the pipeline.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple


class FeatureDefinitions:
    """Centralized feature definitions for precipitation forecasting."""
    
    @staticmethod
    def temporal_features(df: pd.DataFrame, datetime_col: str = 'datetime') -> pd.DataFrame:
        """
        Add temporal cyclical features.
        
        Args:
            df: DataFrame with datetime column
            datetime_col: Name of datetime column
            
        Returns:
            DataFrame with added temporal features
        """
        df = df.copy()
        dt = pd.to_datetime(df[datetime_col])
        
        # Hour of day (0-23) - cyclical encoding
        df['hour_of_day_sin'] = np.sin(2 * np.pi * dt.dt.hour / 24)
        df['hour_of_day_cos'] = np.cos(2 * np.pi * dt.dt.hour / 24)
        
        # Day of year (1-366) - cyclical encoding
        df['day_of_year_sin'] = np.sin(2 * np.pi * dt.dt.dayofyear / 365.25)
        df['day_of_year_cos'] = np.cos(2 * np.pi * dt.dt.dayofyear / 365.25)
        
        # Day of week (0-6) - cyclical encoding
        df['day_of_week_sin'] = np.sin(2 * np.pi * dt.dt.dayofweek / 7)
        df['day_of_week_cos'] = np.cos(2 * np.pi * dt.dt.dayofweek / 7)
        
        # Month (1-12) - cyclical encoding
        df['month_sin'] = np.sin(2 * np.pi * dt.dt.month / 12)
        df['month_cos'] = np.cos(2 * np.pi * dt.dt.month / 12)
        
        # Week of year
        df['week_of_year'] = dt.dt.isocalendar().week
        
        # Is weekend
        df['is_weekend'] = (dt.dt.dayofweek >= 5).astype(int)
        
        # Season (meteorological seasons)
        month = dt.dt.month
        df['season_spring'] = ((month >= 3) & (month <= 5)).astype(int)
        df['season_summer'] = ((month >= 6) & (month <= 8)).astype(int)
        df['season_autumn'] = ((month >= 9) & (month <= 11)).astype(int)
        df['season_winter'] = ((month == 12) | (month <= 2)).astype(int)
        
        return df
    
    @staticmethod
    def location_features(df: pd.DataFrame, latitude: float, longitude: float, elevation: float = None) -> pd.DataFrame:
        """
        Add location-based features.
        
        Args:
            df: DataFrame to add features to
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            elevation: Elevation in meters (optional)
            
        Returns:
            DataFrame with added location features
        """
        df = df.copy()
        
        # Basic coordinates
        df['latitude'] = latitude
        df['longitude'] = longitude
        df['elevation'] = elevation or 0.0
        
        # Derived location features
        df['abs_latitude'] = abs(latitude)
        df['northern_hemisphere'] = (latitude >= 0).astype(int)
        
        # Distance from equator (affects climate patterns)
        df['distance_from_equator'] = abs(latitude)
        
        # Rough continental vs oceanic influence
        # (This is simplified - real implementation would use land/ocean masks)
        df['continental_influence'] = np.clip(abs(longitude) / 180, 0, 1)
        
        # Elevation effects
        df['elevation_km'] = df['elevation'] / 1000
        df['high_elevation'] = (df['elevation'] > 1000).astype(int)
        
        return df
    
    @staticmethod
    def lagged_features(
        df: pd.DataFrame, 
        target_col: str = 'precipitation_mm', 
        lags: List[int] = None
    ) -> pd.DataFrame:
        """
        Add lagged precipitation features.
        
        Args:
            df: DataFrame with precipitation data (sorted by time)
            target_col: Name of precipitation column
            lags: List of lag periods in hours
            
        Returns:
            DataFrame with added lagged features
        """
        if lags is None:
            lags = [1, 3, 6, 12, 24, 48, 72, 168]  # 1h to 1 week
        
        df = df.copy()
        
        for lag in lags:
            # Simple lag
            df[f'{target_col}_lag_{lag}h'] = df[target_col].shift(lag)
            
            # Rolling sums (accumulated precipitation)
            df[f'{target_col}_sum_{lag}h'] = df[target_col].rolling(
                window=lag, min_periods=1
            ).sum().shift(1)  # Shift to avoid lookahead
            
            # Rolling means
            df[f'{target_col}_mean_{lag}h'] = df[target_col].rolling(
                window=lag, min_periods=1
            ).mean().shift(1)
            
            # Rolling max
            df[f'{target_col}_max_{lag}h'] = df[target_col].rolling(
                window=lag, min_periods=1
            ).max().shift(1)
        
        # Additional precipitation features
        # Dry spell length (consecutive hours without rain)
        dry_spell = (df[target_col] <= 0.1).astype(int)
        df['dry_spell_length'] = dry_spell.groupby((dry_spell != dry_spell.shift()).cumsum()).cumsum()
        
        # Wet spell length (consecutive hours with rain)
        wet_spell = (df[target_col] > 0.1).astype(int)
        df['wet_spell_length'] = wet_spell.groupby((wet_spell != wet_spell.shift()).cumsum()).cumsum()
        
        return df
    
    @staticmethod
    def meteorological_features(df: pd.DataFrame) -> pd.DataFrame:
        """
        Add meteorological features and transformations.
        
        Args:
            df: DataFrame with basic meteorological variables
            
        Returns:
            DataFrame with added meteorological features
        """
        df = df.copy()
        
        # Temperature features
        if 'temperature_c' in df.columns:
            df['temperature_k'] = df['temperature_c'] + 273.15  # Kelvin
            df['temperature_squared'] = df['temperature_c'] ** 2
            df['freezing_point'] = (df['temperature_c'] <= 0).astype(int)
            
            # Temperature trends
            df['temperature_trend_1h'] = df['temperature_c'].diff(1)
            df['temperature_trend_3h'] = df['temperature_c'].diff(3)
            df['temperature_trend_6h'] = df['temperature_c'].diff(6)
        
        # Humidity features
        if 'humidity_percent' in df.columns:
            df['humidity_fraction'] = df['humidity_percent'] / 100
            df['humidity_squared'] = df['humidity_percent'] ** 2
            df['high_humidity'] = (df['humidity_percent'] > 80).astype(int)
            
            # Humidity trends
            df['humidity_trend_1h'] = df['humidity_percent'].diff(1)
            df['humidity_trend_3h'] = df['humidity_percent'].diff(3)
        
        # Pressure features
        if 'pressure_hpa' in df.columns:
            df['pressure_normalized'] = (df['pressure_hpa'] - 1013.25) / 50  # Normalize around sea level
            df['low_pressure'] = (df['pressure_hpa'] < 1000).astype(int)
            df['high_pressure'] = (df['pressure_hpa'] > 1020).astype(int)
            
            # Pressure trends (important for weather prediction)
            df['pressure_trend_1h'] = df['pressure_hpa'].diff(1)
            df['pressure_trend_3h'] = df['pressure_hpa'].diff(3)
            df['pressure_trend_6h'] = df['pressure_hpa'].diff(6)
            df['pressure_trend_12h'] = df['pressure_hpa'].diff(12)
            
            # Pressure change rate
            df['pressure_change_rate_3h'] = df['pressure_trend_3h'] / 3
            df['pressure_falling_fast'] = (df['pressure_trend_3h'] < -3).astype(int)
            df['pressure_rising_fast'] = (df['pressure_trend_3h'] > 3).astype(int)
        
        # Combined meteorological features
        if all(col in df.columns for col in ['temperature_c', 'humidity_percent']):
            # Apparent temperature (feels like)
            df['apparent_temperature'] = df['temperature_c'] + 0.33 * (
                df['humidity_percent'] / 100 * 6.105 * np.exp(17.27 * df['temperature_c'] / (237.7 + df['temperature_c']))
            ) - 0.70 * 2.0 - 4.00  # Simplified heat index
        
        if all(col in df.columns for col in ['temperature_c', 'humidity_percent', 'pressure_hpa']):
            # Atmospheric instability indicators
            df['instability_index'] = (
                df['temperature_c'] * df['humidity_fraction'] / (df['pressure_hpa'] / 1013.25)
            )
        
        return df
    
    @staticmethod
    def climatology_features(
        df: pd.DataFrame, 
        historical_data: pd.DataFrame, 
        target_col: str = 'precipitation_mm'
    ) -> pd.DataFrame:
        """
        Add climatological features based on historical data.
        
        Args:
            df: DataFrame to add features to
            historical_data: Historical weather data for climatology
            target_col: Target precipitation column
            
        Returns:
            DataFrame with added climatology features
        """
        df = df.copy()
        
        if historical_data.empty or target_col not in historical_data.columns:
            # Fallback values
            df['climatology_precip_mean'] = 0.5
            df['climatology_precip_std'] = 1.0
            df['climatology_precip_prob'] = 0.2
            df['climatology_precip_p75'] = 1.0
            df['climatology_precip_p90'] = 3.0
            return df
        
        # Ensure historical data has required time components
        hist_df = historical_data.copy()
        if 'datetime' not in hist_df.columns:
            hist_df = hist_df.reset_index()
        
        hist_df['datetime'] = pd.to_datetime(hist_df['datetime'])
        hist_df['hour'] = hist_df['datetime'].dt.hour
        hist_df['dayofyear'] = hist_df['datetime'].dt.dayofyear
        hist_df['month'] = hist_df['datetime'].dt.month
        
        # Current time components
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['hour'] = df['datetime'].dt.hour
        df['dayofyear'] = df['datetime'].dt.dayofyear
        df['month'] = df['datetime'].dt.month
        
        # Hourly climatology (by hour of day)
        hourly_clim = hist_df.groupby('hour')[target_col].agg([
            'mean', 'std', 'count',
            lambda x: (x > 0.1).mean(),  # Probability of precipitation
            lambda x: np.percentile(x[x > 0.1], 75) if (x > 0.1).sum() > 0 else 0,  # P75 of wet days
            lambda x: np.percentile(x[x > 0.1], 90) if (x > 0.1).sum() > 0 else 0,  # P90 of wet days
        ]).reset_index()
        hourly_clim.columns = ['hour', 'hourly_mean', 'hourly_std', 'hourly_count', 
                              'hourly_prob', 'hourly_p75', 'hourly_p90']
        
        df = df.merge(hourly_clim, on='hour', how='left')
        
        # Daily climatology (by day of year, with smoothing window)
        daily_clim_list = []
        for doy in range(1, 367):
            # Use ±7 day window for smoothing
            window_days = [(doy - 7 + i) % 366 for i in range(15)]
            window_days = [d if d != 0 else 366 for d in window_days]  # Handle day 0
            
            window_data = hist_df[hist_df['dayofyear'].isin(window_days)][target_col]
            
            if len(window_data) > 0:
                daily_clim_list.append({
                    'dayofyear': doy,
                    'daily_mean': window_data.mean(),
                    'daily_std': window_data.std(),
                    'daily_prob': (window_data > 0.1).mean(),
                    'daily_p75': np.percentile(window_data[window_data > 0.1], 75) if (window_data > 0.1).sum() > 0 else 0,
                    'daily_p90': np.percentile(window_data[window_data > 0.1], 90) if (window_data > 0.1).sum() > 0 else 0,
                })
        
        daily_clim = pd.DataFrame(daily_clim_list)
        df = df.merge(daily_clim, on='dayofyear', how='left')
        
        # Monthly climatology
        monthly_clim = hist_df.groupby('month')[target_col].agg([
            'mean', 'std',
            lambda x: (x > 0.1).mean(),
        ]).reset_index()
        monthly_clim.columns = ['month', 'monthly_mean', 'monthly_std', 'monthly_prob']
        
        df = df.merge(monthly_clim, on='month', how='left')
        
        # Overall climatology
        overall_mean = hist_df[target_col].mean()
        overall_std = hist_df[target_col].std()
        overall_prob = (hist_df[target_col] > 0.1).mean()
        
        # Fill missing values with overall statistics
        df['climatology_precip_mean'] = df['hourly_mean'].fillna(overall_mean)
        df['climatology_precip_std'] = df['hourly_std'].fillna(overall_std)
        df['climatology_precip_prob'] = df['hourly_prob'].fillna(overall_prob)
        df['climatology_precip_p75'] = df['hourly_p75'].fillna(overall_mean * 2)
        df['climatology_precip_p90'] = df['hourly_p90'].fillna(overall_mean * 4)
        
        # Clean up temporary columns
        df = df.drop(columns=[
            'hour', 'dayofyear', 'month',
            'hourly_mean', 'hourly_std', 'hourly_count', 'hourly_prob', 'hourly_p75', 'hourly_p90',
            'daily_mean', 'daily_std', 'daily_prob', 'daily_p75', 'daily_p90',
            'monthly_mean', 'monthly_std', 'monthly_prob'
        ], errors='ignore')
        
        return df
    
    @staticmethod
    def anomaly_features(
        df: pd.DataFrame,
        historical_data: pd.DataFrame,
        variables: List[str] = None
    ) -> pd.DataFrame:
        """
        Add anomaly features (deviation from climatology).
        
        Args:
            df: DataFrame to add features to
            historical_data: Historical data for computing climatology
            variables: List of variables to compute anomalies for
            
        Returns:
            DataFrame with added anomaly features
        """
        if variables is None:
            variables = ['precipitation_mm', 'temperature_c', 'humidity_percent', 'pressure_hpa']
        
        df = df.copy()
        
        if historical_data.empty:
            # Add zero anomalies if no historical data
            for var in variables:
                if var in df.columns:
                    df[f'{var}_anomaly_recent'] = 0.0
                    df[f'{var}_anomaly_seasonal'] = 0.0
            return df
        
        # Compute recent anomalies (last 24 hours vs historical mean)
        for var in variables:
            if var in df.columns and var in historical_data.columns:
                hist_mean = historical_data[var].mean()
                
                # Recent 24-hour mean
                df[f'{var}_recent_24h'] = df[var].rolling(window=24, min_periods=1).mean()
                df[f'{var}_anomaly_recent'] = df[f'{var}_recent_24h'] - hist_mean
                
                # Seasonal anomaly (current month vs historical same month)
                df['month'] = pd.to_datetime(df['datetime']).dt.month
                
                # Historical monthly means
                hist_df_temp = historical_data.copy()
                hist_df_temp['month'] = pd.to_datetime(hist_df_temp['datetime']).dt.month
                monthly_means = hist_df_temp.groupby('month')[var].mean().to_dict()
                
                df[f'{var}_seasonal_mean'] = df['month'].map(monthly_means)
                df[f'{var}_anomaly_seasonal'] = df[var] - df[f'{var}_seasonal_mean']
                
                # Clean up
                df = df.drop(columns=[f'{var}_recent_24h', f'{var}_seasonal_mean'], errors='ignore')
        
        df = df.drop(columns=['month'], errors='ignore')
        
        return df
    
    @staticmethod
    def get_feature_list() -> Dict[str, List[str]]:
        """
        Get comprehensive list of all features by category.
        
        Returns:
            Dictionary mapping feature categories to feature names
        """
        return {
            'temporal': [
                'hour_of_day_sin', 'hour_of_day_cos',
                'day_of_year_sin', 'day_of_year_cos',
                'day_of_week_sin', 'day_of_week_cos',
                'month_sin', 'month_cos',
                'week_of_year', 'is_weekend',
                'season_spring', 'season_summer', 'season_autumn', 'season_winter'
            ],
            'location': [
                'latitude', 'longitude', 'elevation', 'abs_latitude',
                'northern_hemisphere', 'distance_from_equator',
                'continental_influence', 'elevation_km', 'high_elevation'
            ],
            'lagged_precipitation': [
                'precipitation_mm_lag_1h', 'precipitation_mm_lag_3h', 'precipitation_mm_lag_6h',
                'precipitation_mm_lag_12h', 'precipitation_mm_lag_24h', 'precipitation_mm_lag_48h',
                'precipitation_mm_lag_72h', 'precipitation_mm_lag_168h',
                'precipitation_mm_sum_1h', 'precipitation_mm_sum_3h', 'precipitation_mm_sum_6h',
                'precipitation_mm_sum_12h', 'precipitation_mm_sum_24h', 'precipitation_mm_sum_48h',
                'precipitation_mm_sum_72h', 'precipitation_mm_sum_168h',
                'dry_spell_length', 'wet_spell_length'
            ],
            'meteorological': [
                'temperature_c', 'temperature_k', 'temperature_squared', 'freezing_point',
                'temperature_trend_1h', 'temperature_trend_3h', 'temperature_trend_6h',
                'humidity_percent', 'humidity_fraction', 'humidity_squared', 'high_humidity',
                'humidity_trend_1h', 'humidity_trend_3h',
                'pressure_hpa', 'pressure_normalized', 'low_pressure', 'high_pressure',
                'pressure_trend_1h', 'pressure_trend_3h', 'pressure_trend_6h', 'pressure_trend_12h',
                'pressure_change_rate_3h', 'pressure_falling_fast', 'pressure_rising_fast',
                'apparent_temperature', 'instability_index'
            ],
            'climatology': [
                'climatology_precip_mean', 'climatology_precip_std', 'climatology_precip_prob',
                'climatology_precip_p75', 'climatology_precip_p90'
            ],
            'anomalies': [
                'precipitation_mm_anomaly_recent', 'precipitation_mm_anomaly_seasonal',
                'temperature_c_anomaly_recent', 'temperature_c_anomaly_seasonal',
                'humidity_percent_anomaly_recent', 'humidity_percent_anomaly_seasonal',
                'pressure_hpa_anomaly_recent', 'pressure_hpa_anomaly_seasonal'
            ]
        }