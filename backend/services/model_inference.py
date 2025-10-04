import os
import sys
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import pandas as pd

from utils.logging import get_logger

# Add ML directory to path
ml_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'ml')
sys.path.append(ml_dir)

logger = get_logger(__name__)


class ModelInferenceService:
    """Service for ML model inference and predictions."""
    
    def __init__(self):
        self.ml_service = None
        self.models_loaded = False
        
        # Try to load ML models
        self._initialize_ml_models()
        
    def _initialize_ml_models(self):
        """Initialize ML models if available."""
        try:
            # Import ML inference service
            from model_inference import ModelInferenceService as MLService
            
            self.ml_service = MLService()
            self.models_loaded = True
            logger.info("ML models loaded successfully")
            
        except ImportError as e:
            logger.warning(f"ML models not available: {e}")
            self.models_loaded = False
        except Exception as e:
            logger.error(f"Failed to load ML models: {e}")
            self.models_loaded = False
        
    async def predict_precipitation(
        self,
        location_data: Dict[str, Any],
        weather_data: List[Dict[str, Any]],
        forecast_horizons: List[int] = None
    ) -> Dict[str, Any]:
        """
        Generate precipitation forecasts using ML models.
        
        Args:
            location_data: Location information (lat, lng, elevation, etc.)
            weather_data: Historical/current weather data for features
            forecast_horizons: List of forecast horizons in hours
            
        Returns:
            Dictionary with forecasts for each horizon
        """
        if forecast_horizons is None:
            forecast_horizons = [1, 3, 6, 12, 24, 48, 72]
        
        logger.info(f"Generating forecasts for {len(forecast_horizons)} horizons")
        
        try:
            if self.models_loaded and self.ml_service:
                # Use trained ML models
                return await self._predict_with_ml_models(
                    location_data, weather_data, forecast_horizons
                )
            else:
                # Fall back to heuristic models
                return await self._predict_with_heuristics(
                    location_data, weather_data, forecast_horizons
                )
                
        except Exception as e:
            logger.error(f"Forecast generation failed: {e}")
            return self._generate_fallback_forecasts(forecast_horizons)
    
    async def _predict_with_ml_models(
        self,
        location_data: Dict[str, Any],
        weather_data: List[Dict[str, Any]],
        forecast_horizons: List[int]
    ) -> Dict[str, Any]:
        """Use trained ML models for predictions."""
        logger.info("Using trained ML models for prediction")
        
        # Prepare current weather conditions
        current_conditions = weather_data[-1] if weather_data else {}
        
        # Convert to format expected by ML service
        current_weather = {
            'datetime': current_conditions.get('datetime', datetime.now()),
            'temperature': current_conditions.get('temperature_c', 20.0),
            'humidity': current_conditions.get('humidity_percent', 60.0),
            'pressure': current_conditions.get('pressure_hpa', 1013.25),
            'precipitation': current_conditions.get('precipitation_mm', 0.0),
            'wind_speed': current_conditions.get('wind_speed_ms', 5.0),
            'wind_direction': current_conditions.get('wind_direction_deg', 180.0),
            'cloud_cover': current_conditions.get('cloud_cover_percent', 50.0)
        }
        
        # Prepare historical data for lagged features
        historical_data = None
        if len(weather_data) > 1:
            # Convert historical data to DataFrame
            hist_records = []
            for record in weather_data[:-1]:  # Exclude current
                hist_records.append({
                    'datetime': pd.Timestamp(record.get('datetime', datetime.now())),
                    'precipitation_mm': record.get('precipitation_mm', 0.0),
                    'temperature_c': record.get('temperature_c', 20.0),
                    'humidity_percent': record.get('humidity_percent', 60.0),
                    'pressure_hpa': record.get('pressure_hpa', 1013.25),
                    'wind_speed_ms': record.get('wind_speed_ms', 5.0),
                    'wind_direction_deg': record.get('wind_direction_deg', 180.0),
                    'cloud_cover_percent': record.get('cloud_cover_percent', 50.0)
                })
            
            if hist_records:
                historical_data = pd.DataFrame(hist_records)
        
        # Get ML predictions
        ml_forecasts = self.ml_service.predict_precipitation(
            current_weather=current_weather,
            location_info=location_data,
            forecast_horizons=forecast_horizons,
            historical_data=historical_data
        )
        
        # Convert ML format to API format
        forecasts = {}
        
        for horizon in forecast_horizons:
            horizon_key = f"{horizon}h"
            if horizon_key in ml_forecasts:
                ml_forecast = ml_forecasts[horizon_key]
                
                forecasts[horizon_key] = {
                    "precipitation_mm": round(ml_forecast.get('precipitation_mm', 0.0), 2),
                    "probability": round(ml_forecast.get('precipitation_probability', 0.0), 3),
                    "confidence": ml_forecast.get('confidence', 'medium'),
                    "horizon_hours": horizon,
                    "model_type": ml_forecast.get('model_used', 'ml')
                }
        
        # Add metadata
        forecasts["metadata"] = {
            "model_type": "trained_ml",
            "forecast_time": datetime.utcnow().isoformat(),
            "location": location_data,
            "data_points_used": len(weather_data),
            "ml_metadata": ml_forecasts.get('metadata', {})
        }
        
        logger.info(f"Generated ML forecasts for {len(forecast_horizons)} horizons")
        return forecasts
    
    async def _predict_with_heuristics(
        self,
        location_data: Dict[str, Any],
        weather_data: List[Dict[str, Any]],
        forecast_horizons: List[int]
    ) -> Dict[str, Any]:
        """Use heuristic models when ML models unavailable."""
        logger.info("Using heuristic models for prediction")
        
        current_conditions = weather_data[-1] if weather_data else {}
        
        forecasts = {}
        
        for horizon in forecast_horizons:
            forecast = self._generate_heuristic_forecast(
                current_conditions, location_data, horizon
            )
            forecasts[f"{horizon}h"] = forecast
        
        # Add metadata
        forecasts["metadata"] = {
            "model_type": "heuristic_baseline",
            "forecast_time": datetime.utcnow().isoformat(),
            "location": location_data,
            "data_points_used": len(weather_data)
        }
        
        logger.info(f"Generated heuristic forecasts for {len(forecast_horizons)} horizons")
        return forecasts
    
    def _generate_heuristic_forecast(
        self,
        current_conditions: Dict[str, Any],
        location_data: Dict[str, Any],
        horizon_hours: int
    ) -> Dict[str, Any]:
        """
        Generate a simple heuristic-based forecast.
        This is a placeholder for actual ML model predictions.
        """
        # Extract current conditions
        temp = current_conditions.get("temperature_c", 20.0)
        humidity = current_conditions.get("humidity_percent", 60.0)
        pressure = current_conditions.get("pressure_hpa", 1013.25)
        current_precip = current_conditions.get("precipitation_mm", 0.0)
        
        # Simple heuristic rules
        base_probability = 0.1  # Base 10% chance
        
        # Increase probability with:
        if humidity > 80:
            base_probability += 0.3
        elif humidity > 60:
            base_probability += 0.1
        
        if pressure < 1000:
            base_probability += 0.2
        elif pressure < 1010:
            base_probability += 0.1
        
        if temp > 25:  # Higher chance in warm weather
            base_probability += 0.1
        
        # Current precipitation persistence
        if current_precip > 0:
            persistence_factor = max(0.1, 1.0 - horizon_hours / 24.0)
            base_probability += 0.4 * persistence_factor
        
        # Seasonal adjustment (simple)
        month = datetime.now().month
        if month in [6, 7, 8]:  # Summer - less frequent but potentially heavier
            seasonal_factor = 0.8
            intensity_factor = 1.5
        elif month in [12, 1, 2]:  # Winter
            seasonal_factor = 1.2
            intensity_factor = 0.8
        else:  # Spring/Fall
            seasonal_factor = 1.0
            intensity_factor = 1.0
        
        # Apply seasonal adjustment
        probability = min(0.9, base_probability * seasonal_factor)
        
        # Estimate precipitation amount
        if probability > 0.5:
            # Heavier precipitation likely
            precip_mm = max(0.1, (probability - 0.5) * 20 * intensity_factor)
        else:
            # Light precipitation
            precip_mm = probability * 5 * intensity_factor
        
        # Distance-based decay for longer horizons
        decay_factor = max(0.1, 1.0 - horizon_hours / 168.0)  # Week decay
        precip_mm *= decay_factor
        
        return {
            "precipitation_mm": round(precip_mm, 2),
            "probability": round(probability, 3),
            "confidence": "medium" if horizon_hours <= 24 else "low",
            "horizon_hours": horizon_hours,
            "model_type": "heuristic"
        }
    
    def _generate_fallback_forecasts(
        self,
        forecast_horizons: List[int]
    ) -> Dict[str, Any]:
        """Generate simple fallback forecasts when model inference fails."""
        logger.warning("Using fallback forecast generation")
        
        forecasts = {}
        
        for horizon in forecast_horizons:
            # Very simple fallback: decreasing probability over time
            probability = max(0.05, 0.3 - (horizon / 168.0))  # Decay over a week
            precip_mm = probability * 8.0  # Simple scaling
            
            forecasts[f"{horizon}h"] = {
                "precipitation_mm": round(precip_mm, 2),
                "probability": round(probability, 3),
                "confidence": "very_low",
                "horizon_hours": horizon,
                "model_type": "fallback"
            }
        
        forecasts["metadata"] = {
            "model_type": "fallback",
            "forecast_time": datetime.utcnow().isoformat(),
            "warning": "Using fallback predictions due to model failure"
        }
        
        return forecasts


# Global service instance
inference_service = ModelInferenceService()
    
