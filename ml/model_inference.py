"""
Model inference service for real-time precipitation forecasting.
Loads trained models and provides prediction capabilities.
"""

import os
import sys
import json
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging

import pandas as pd
import numpy as np
import lightgbm as lgb

# Add backend to path  
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))
from utils.logging import get_logger

# Import feature engineering
from feature_defs import FeatureDefinitions

logger = get_logger(__name__)


class ModelInferenceService:
    """Service for loading models and making real-time predictions."""
    
    def __init__(self, models_dir: str = None):
        if models_dir is None:
            models_dir = os.path.join(os.path.dirname(__file__), "models")
        
        self.models_dir = Path(models_dir)
        self.feature_defs = FeatureDefinitions()
        
        # Model storage
        self.baseline_models = {}
        self.gb_models = {}
        self.model_metadata = {}
        self.feature_columns = []
        
        # Load models on initialization
        self.load_models()
    
    def load_models(self):
        """Load all trained models."""
        logger.info(f"Loading models from {self.models_dir}")
        
        try:
            # Load baseline models
            baseline_path = self.models_dir / "baseline_models.pkl"
            if baseline_path.exists():
                with open(baseline_path, 'rb') as f:
                    self.baseline_models = pickle.load(f)
                logger.info(f"Loaded {len(self.baseline_models)} baseline models")
            
            # Load gradient boosted models  
            gb_path = self.models_dir / "gradient_boosted_models.pkl"
            if gb_path.exists():
                with open(gb_path, 'rb') as f:
                    self.gb_models = pickle.load(f)
                logger.info(f"Loaded {len(self.gb_models)} gradient boosted models")
            
            # Load model metadata
            metadata_path = self.models_dir / "model_metadata.json"
            if metadata_path.exists():
                with open(metadata_path, 'r') as f:
                    self.model_metadata = json.load(f)
                    self.feature_columns = self.model_metadata.get('feature_columns', [])
                logger.info(f"Loaded metadata with {len(self.feature_columns)} features")
            
            if not (self.baseline_models or self.gb_models):
                logger.warning("No models loaded - using fallback predictions")
                
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            # Continue with empty models - will use fallbacks
    
    def prepare_features(
        self, 
        current_weather: Dict[str, Any],
        location_info: Dict[str, Any],
        historical_data: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Prepare features for model inference.
        
        Args:
            current_weather: Current weather conditions
            location_info: Location metadata (lat, lng, elevation, etc.)
            historical_data: Recent historical data for lagged features
            
        Returns:
            DataFrame with engineered features
        """
        try:
            # Create base dataframe with current conditions
            base_data = {
                'datetime': [pd.Timestamp(current_weather.get('datetime', datetime.now()))],
                'precipitation_mm': [current_weather.get('precipitation', 0.0)],
                'temperature_c': [current_weather.get('temperature', 20.0)],
                'humidity_percent': [current_weather.get('humidity', 60.0)],
                'pressure_hpa': [current_weather.get('pressure', 1013.25)],
                'wind_speed_ms': [current_weather.get('wind_speed', 5.0)],
                'wind_direction_deg': [current_weather.get('wind_direction', 180.0)],
                'cloud_cover_percent': [current_weather.get('cloud_cover', 50.0)]
            }
            
            df = pd.DataFrame(base_data)
            
            # Add location info
            lat = location_info.get('latitude', 0.0)
            lng = location_info.get('longitude', 0.0)
            elevation = location_info.get('elevation', 0.0)
            
            # Generate temporal features
            df = self.feature_defs.temporal_features(df)
            
            # Generate location features
            df = self.feature_defs.location_features(df, lat, lng, elevation)
            
            # Generate meteorological features
            df = self.feature_defs.meteorological_features(df)
            
            # Add lagged features (use historical data if available)
            if historical_data is not None and len(historical_data) > 0:
                # Combine historical and current data for lag calculation
                combined_df = pd.concat([historical_data, df], ignore_index=True)
                combined_df = combined_df.sort_values('datetime')
                combined_df = self.feature_defs.lagged_features(combined_df, 'precipitation_mm')
                
                # Extract features for current time (last row)
                df = combined_df.tail(1).copy()
            else:
                # Use default lag values when no historical data
                self._add_default_lag_features(df)
            
            # Add climatology features (use simple defaults)
            self._add_default_climatology_features(df, current_weather)
            
            # Add anomaly features (use defaults)
            self._add_default_anomaly_features(df, current_weather)
            
            # Ensure all required features are present
            df = self._ensure_required_features(df)
            
            logger.debug(f"Prepared features: {df.shape[1]} columns")
            
            return df
            
        except Exception as e:
            logger.error(f"Feature preparation failed: {e}")
            # Return minimal feature set
            return self._create_minimal_features(current_weather, location_info)
    
    def _add_default_lag_features(self, df: pd.DataFrame):
        """Add default lagged features when historical data unavailable."""
        current_precip = df['precipitation_mm'].iloc[0]
        
        # Add lag features with current values as defaults
        lag_hours = [1, 3, 6, 12, 24, 48, 72]
        
        for lag in lag_hours:
            df[f'precipitation_mm_lag_{lag}h'] = current_precip * 0.8  # Assume slight decay
        
        # Add rolling statistics
        for window in [6, 12, 24, 48]:
            df[f'precipitation_mm_sum_{window}h'] = current_precip * min(window, 12)
            df[f'precipitation_mm_mean_{window}h'] = current_precip
            df[f'precipitation_mm_max_{window}h'] = current_precip * 1.2
    
    def _add_default_climatology_features(self, df: pd.DataFrame, current_weather: Dict):
        """Add default climatology features."""
        # Use simple seasonal patterns
        month = df['month'].iloc[0]
        
        # Rough climatology based on month (Northern Hemisphere bias)
        if month in [6, 7, 8]:  # Summer
            clim_mean = 2.0
            clim_prob = 0.3
        elif month in [12, 1, 2]:  # Winter
            clim_mean = 3.0
            clim_prob = 0.4
        else:  # Spring/Fall
            clim_mean = 2.5
            clim_prob = 0.35
        
        df['climatology_precip_mean'] = clim_mean
        df['climatology_precip_std'] = clim_mean * 0.8
        df['climatology_precip_prob'] = clim_prob
        df['climatology_precip_p75'] = clim_mean * 1.5
        df['climatology_precip_p90'] = clim_mean * 2.5
    
    def _add_default_anomaly_features(self, df: pd.DataFrame, current_weather: Dict):
        """Add default anomaly features."""
        # Simple anomaly calculation relative to typical values
        temp = current_weather.get('temperature', 20.0)
        humidity = current_weather.get('humidity', 60.0)
        pressure = current_weather.get('pressure', 1013.25)
        precip = current_weather.get('precipitation', 0.0)
        
        # Typical values for normalization
        typical_temp = 20.0
        typical_humidity = 60.0
        typical_pressure = 1013.25
        typical_precip = 2.0
        
        df['temperature_anomaly'] = temp - typical_temp
        df['humidity_anomaly'] = humidity - typical_humidity
        df['pressure_anomaly'] = pressure - typical_pressure
        df['precipitation_anomaly'] = precip - typical_precip
    
    def _ensure_required_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ensure all required features are present with defaults."""
        if not self.feature_columns:
            return df
        
        for feature in self.feature_columns:
            if feature not in df.columns:
                # Add missing feature with default value
                if 'temperature' in feature:
                    df[feature] = 20.0
                elif 'humidity' in feature:
                    df[feature] = 60.0
                elif 'pressure' in feature:
                    df[feature] = 1013.25
                elif 'precipitation' in feature:
                    df[feature] = 0.0
                elif 'wind' in feature:
                    df[feature] = 5.0
                elif 'cloud' in feature:
                    df[feature] = 50.0
                else:
                    df[feature] = 0.0
        
        # Return only required features in correct order
        available_features = [f for f in self.feature_columns if f in df.columns]
        if available_features:
            return df[available_features]
        else:
            return df
    
    def _create_minimal_features(
        self, 
        current_weather: Dict[str, Any], 
        location_info: Dict[str, Any]
    ) -> pd.DataFrame:
        """Create minimal feature set for fallback predictions."""
        features = {
            'temperature_c': [current_weather.get('temperature', 20.0)],
            'humidity_percent': [current_weather.get('humidity', 60.0)],
            'pressure_hpa': [current_weather.get('pressure', 1013.25)],
            'precipitation_mm': [current_weather.get('precipitation', 0.0)],
            'wind_speed_ms': [current_weather.get('wind_speed', 5.0)],
            'latitude': [location_info.get('latitude', 0.0)],
            'longitude': [location_info.get('longitude', 0.0)]
        }
        
        return pd.DataFrame(features)
    
    def predict_precipitation(
        self,
        current_weather: Dict[str, Any],
        location_info: Dict[str, Any],
        forecast_horizons: List[int] = None,
        model_preference: str = 'lightgbm',
        historical_data: Optional[pd.DataFrame] = None
    ) -> Dict[str, Any]:
        """
        Make precipitation forecasts for multiple horizons.
        
        Args:
            current_weather: Current weather conditions
            location_info: Location metadata
            forecast_horizons: List of forecast horizons in hours
            model_preference: Preferred model type ('lightgbm', 'xgboost', 'persistence', 'climatology')
            historical_data: Recent historical data for improved predictions
            
        Returns:
            Dictionary with forecasts for each horizon
        """
        if forecast_horizons is None:
            forecast_horizons = [1, 3, 6, 12, 24, 48, 72, 168, 336, 720]
        
        logger.info(f"Making predictions for {len(forecast_horizons)} horizons")
        
        try:
            # Prepare features
            features_df = self.prepare_features(current_weather, location_info, historical_data)
            
            forecasts = {}
            
            for horizon in forecast_horizons:
                horizon_forecasts = {}
                
                # Target names for this horizon
                precip_target = f'target_precip_{horizon}h'
                binary_target = f'target_precip_binary_{horizon}h'
                
                # Try preferred model first
                success = False
                
                # Gradient boosted models
                if model_preference in ['lightgbm', 'xgboost'] and self.gb_models:
                    precip_model_name = f'{model_preference}_{precip_target}'
                    binary_model_name = f'{model_preference}_{binary_target}'
                    
                    if precip_model_name in self.gb_models and binary_model_name in self.gb_models:
                        try:
                            # Continuous prediction
                            precip_pred = self._predict_with_gb_model(
                                self.gb_models[precip_model_name], features_df
                            )
                            
                            # Binary prediction (probability)
                            binary_pred = self._predict_with_gb_model(
                                self.gb_models[binary_model_name], features_df
                            )
                            
                            horizon_forecasts = {
                                'precipitation_mm': max(0, float(precip_pred[0])),
                                'precipitation_probability': float(np.clip(binary_pred[0], 0, 1)),
                                'model_used': model_preference,
                                'confidence': 'high'
                            }
                            success = True
                            
                        except Exception as e:
                            logger.warning(f"GB model prediction failed for {horizon}h: {e}")
                
                # Fallback to baseline models
                if not success:
                    horizon_forecasts = self._predict_with_baseline(
                        current_weather, precip_target, binary_target
                    )
                
                forecasts[f'{horizon}h'] = horizon_forecasts
            
            # Add metadata
            forecasts['metadata'] = {
                'forecast_time': datetime.now().isoformat(),
                'location': location_info,
                'models_available': {
                    'baseline': len(self.baseline_models),
                    'gradient_boosted': len(self.gb_models)
                }
            }
            
            logger.info(f"Generated forecasts for {len(forecast_horizons)} horizons")
            
            return forecasts
            
        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return self._generate_fallback_forecasts(current_weather, forecast_horizons)
    
    def _predict_with_gb_model(self, model, features_df: pd.DataFrame) -> np.ndarray:
        """Make prediction with gradient boosted model."""
        if isinstance(model, lgb.Booster):
            return model.predict(features_df.values)
        else:
            # XGBoost or sklearn model
            if hasattr(model, 'predict_proba') and 'binary' in str(model):
                return model.predict_proba(features_df.values)[:, 1]
            else:
                return model.predict(features_df.values)
    
    def _predict_with_baseline(
        self, 
        current_weather: Dict[str, Any], 
        precip_target: str, 
        binary_target: str
    ) -> Dict[str, Any]:
        """Make prediction with baseline models."""
        current_precip = current_weather.get('precipitation', 0.0)
        
        # Persistence model (use current conditions)
        persistence_precip = current_precip * 0.8  # Assume slight decay
        persistence_prob = 0.7 if current_precip > 0.1 else 0.2
        
        # Climatology model (use seasonal average)
        month = datetime.now().month
        if month in [6, 7, 8]:  # Summer
            clim_precip = 1.5
            clim_prob = 0.25
        elif month in [12, 1, 2]:  # Winter  
            clim_precip = 2.5
            clim_prob = 0.4
        else:
            clim_precip = 2.0
            clim_prob = 0.3
        
        # Blend persistence and climatology
        blended_precip = 0.6 * persistence_precip + 0.4 * clim_precip
        blended_prob = 0.6 * persistence_prob + 0.4 * clim_prob
        
        return {
            'precipitation_mm': max(0, blended_precip),
            'precipitation_probability': np.clip(blended_prob, 0, 1),
            'model_used': 'baseline_blend',
            'confidence': 'medium'
        }
    
    def _generate_fallback_forecasts(
        self, 
        current_weather: Dict[str, Any], 
        forecast_horizons: List[int]
    ) -> Dict[str, Any]:
        """Generate simple fallback forecasts when models fail."""
        logger.warning("Using fallback forecast generation")
        
        current_precip = current_weather.get('precipitation', 0.0)
        base_prob = 0.3 if current_precip > 0.1 else 0.2
        
        forecasts = {}
        
        for horizon in forecast_horizons:
            # Simple decay model
            decay_factor = np.exp(-horizon / 48.0)  # 48-hour half-life
            
            forecasts[f'{horizon}h'] = {
                'precipitation_mm': max(0, current_precip * decay_factor + 1.0),
                'precipitation_probability': base_prob * decay_factor + 0.15,
                'model_used': 'fallback',
                'confidence': 'low'
            }
        
        forecasts['metadata'] = {
            'forecast_time': datetime.now().isoformat(),
            'warning': 'Using fallback predictions - models not available'
        }
        
        return forecasts
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about loaded models."""
        return {
            'baseline_models': list(self.baseline_models.keys()),
            'gradient_boosted_models': list(self.gb_models.keys()),
            'feature_count': len(self.feature_columns),
            'metadata': self.model_metadata
        }


# Global inference service instance
_inference_service = None


def get_inference_service() -> ModelInferenceService:
    """Get singleton inference service instance."""
    global _inference_service
    
    if _inference_service is None:
        _inference_service = ModelInferenceService()
    
    return _inference_service


def predict_precipitation(
    current_weather: Dict[str, Any],
    location_info: Dict[str, Any],
    forecast_horizons: List[int] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Convenience function for making precipitation predictions.
    
    Args:
        current_weather: Current weather conditions
        location_info: Location metadata
        forecast_horizons: List of forecast horizons in hours
        **kwargs: Additional arguments passed to inference service
        
    Returns:
        Dictionary with forecasts
    """
    service = get_inference_service()
    return service.predict_precipitation(
        current_weather, location_info, forecast_horizons, **kwargs
    )


if __name__ == "__main__":
    # Test the inference service
    from utils.logging import setup_logging
    
    setup_logging()
    
    # Test data
    test_weather = {
        'datetime': datetime.now(),
        'temperature': 22.5,
        'humidity': 65.0,
        'pressure': 1015.0,
        'precipitation': 0.5,
        'wind_speed': 8.0,
        'wind_direction': 225.0,
        'cloud_cover': 70.0
    }
    
    test_location = {
        'latitude': 40.7128,
        'longitude': -74.0060,
        'elevation': 10.0,
        'name': 'New York City'
    }
    
    # Make prediction
    service = ModelInferenceService()
    forecasts = service.predict_precipitation(test_weather, test_location)
    
    print("Test Forecasts:")
    for horizon, forecast in forecasts.items():
        if horizon != 'metadata':
            print(f"  {horizon}: {forecast['precipitation_mm']:.2f} mm "
                  f"({forecast['precipitation_probability']:.1%} probability)")