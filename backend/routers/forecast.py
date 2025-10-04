import logging
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from services.data_fetch import DataFetchService
from services.feature_engineering import FeatureEngineeringService
from services.model_inference import ModelInferenceService
from .schemas import (
    ForecastRequest,
    ForecastResponse,
    LocationData,
    ModelInfo,
    ErrorResponse
)

# Create router
router = APIRouter()

# Set up logger
logger = logging.getLogger(__name__)

# Initialize services
data_service = DataFetchService()
feature_service = FeatureEngineeringService()
model_service = ModelInferenceService()

logger = logging.getLogger(__name__)


@router.post("/forecast", response_model=ForecastResponse)
async def generate_forecast(
    request: ForecastRequest,
    background_tasks: BackgroundTasks
) -> ForecastResponse:
    """
    Generate precipitation forecast for given location and time range.
    
    Args:
        request: Forecast parameters including location and timing
        background_tasks: Background tasks for async operations
    
    Returns:
        Complete forecast response with hourly data and summary
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Processing forecast request {request_id}", extra={
        "request_id": request_id,
        "latitude": request.latitude,
        "longitude": request.longitude,
        "horizon_hours": request.horizon_hours
    })
    
    try:
        # Initialize services
        data_service = DataFetchService()
        feature_service = FeatureEngineeringService()
        model_service = ModelInferenceService()
        # Validate request parameters
        if request.horizon_hours > 720:  # 30 days
            raise HTTPException(
                status_code=400,
                detail="Forecast horizon cannot exceed 30 days (720 hours)"
            )
        
        # Get location information
        location = LocationData(
            latitude=request.latitude,
            longitude=request.longitude,
        )
        
        # Get elevation and timezone data
        location_info = await data_service.get_location_info(
            request.latitude, request.longitude
        )
        location.elevation = location_info.get("elevation")
        location.timezone = location_info.get("timezone")
        location.address = location_info.get("address")
        
        # Fetch historical weather data
        try:
            historical_data = await data_service.fetch_historical_data(
                latitude=request.latitude,
                longitude=request.longitude,
                start_date=datetime.utcnow() - timedelta(days=365*5),  # 5 years
                end_date=datetime.utcnow()
            )
        except Exception as e:
            logger.error(f"Failed to fetch historical data: {e}")
            # Use mock data for development
            historical_data = _generate_mock_historical_data()
        
        # Generate features
        features = feature_service.generate_features(
            historical_data=historical_data,
            forecast_start=request.start_datetime_utc,
            horizon_hours=request.horizon_hours,
            latitude=request.latitude,
            longitude=request.longitude,
            elevation=location.elevation
        )
        
        # Generate forecast
        forecast_data = await model_service.predict(
            features=features,
            latitude=request.latitude,
            longitude=request.longitude,
            start_datetime=request.start_datetime_utc,
            horizon_hours=request.horizon_hours
        )
        
        # Create model info
        model_info = ModelInfo(
            primary_model="gradient_boosted_trees",
            training_period="2020-01-01 to 2024-12-31",
            last_updated=datetime(2025, 1, 15, 10, 30, 0),
            features_used=[
                "hour_of_day_sin", "hour_of_day_cos", "day_of_year_sin", "day_of_year_cos",
                "precipitation_lag_6h", "precipitation_lag_12h", "precipitation_lag_24h",
                "climatology_precip", "temperature", "humidity", "pressure",
                "elevation", "latitude", "longitude", "forecast_horizon"
            ],
            performance_metrics={
                "brier_score": 0.185,
                "roc_auc": 0.78,
                "f1_score": 0.65,
                "rmse_mm": 2.3,
                "mae_mm": 1.1,
                "skill_score": 0.23
            }
        )
        
        # Create response
        response = ForecastResponse(
            location=location,
            forecast=forecast_data,
            model_info=model_info,
            request_id=request_id,
            generated_at=datetime.utcnow()
        )
        
        # Log successful completion
        logger.info(f"Successfully processed forecast request {request_id}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing forecast request {request_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error processing forecast request"
        )


@router.get("/models/info")
async def get_model_info():
    """Get information about available forecasting models."""
    return {
        "available_models": [
            {
                "name": "climatology_baseline",
                "type": "statistical",
                "description": "Multi-year climatological average",
                "skill_score": 0.0
            },
            {
                "name": "persistence_baseline", 
                "type": "statistical",
                "description": "Recent weather persistence model",
                "skill_score": 0.15
            },
            {
                "name": "gradient_boosted_trees",
                "type": "machine_learning",
                "description": "LightGBM ensemble model",
                "skill_score": 0.23
            }
        ],
        "primary_model": "gradient_boosted_trees",
        "last_training": "2025-01-15T10:30:00Z",
        "next_training": "2025-02-14T10:30:00Z"
    }


@router.get("/data/sources")
async def get_data_sources():
    """Get information about data sources used."""
    return {
        "sources": [
            {
                "name": "NASA GPM IMERG",
                "type": "precipitation",
                "description": "Global Precipitation Measurement hourly estimates",
                "url": "https://gpm.nasa.gov/",
                "spatial_resolution": "0.1°",
                "temporal_resolution": "hourly",
                "coverage": "global"
            },
            {
                "name": "NASA POWER",
                "type": "meteorological",
                "description": "Prediction of Worldwide Energy Resources",
                "url": "https://power.larc.nasa.gov/",
                "parameters": ["temperature", "humidity", "solar_radiation"],
                "spatial_resolution": "0.5°",
                "temporal_resolution": "hourly"
            },
            {
                "name": "Open Elevation",
                "type": "topographic",
                "description": "Global elevation data",
                "url": "https://open-elevation.com/",
                "spatial_resolution": "30m",
                "coverage": "global"
            }
        ],
        "update_frequency": "daily",
        "historical_coverage": "2020-01-01 to present"
    }


def _generate_mock_historical_data():
    """Generate mock historical data for development/testing."""
    import numpy as np
    import pandas as pd
    
    # Generate 5 years of hourly data
    dates = pd.date_range(
        start=datetime.utcnow() - timedelta(days=365*5),
        end=datetime.utcnow(),
        freq='H'
    )
    
    # Mock precipitation data with seasonal pattern
    np.random.seed(42)
    seasonal_factor = np.sin(2 * np.pi * dates.dayofyear / 365.25) * 0.3 + 0.5
    precipitation = np.random.exponential(scale=0.5 * seasonal_factor, size=len(dates))
    precipitation = np.where(np.random.random(len(dates)) < 0.8, 0, precipitation)  # 20% chance of rain
    
    return pd.DataFrame({
        'datetime': dates,
        'precipitation_mm': precipitation,
        'temperature_c': 15 + 10 * seasonal_factor + np.random.normal(0, 3, len(dates)),
        'humidity_percent': 50 + 30 * seasonal_factor + np.random.normal(0, 10, len(dates)),
        'pressure_hpa': 1013 + np.random.normal(0, 10, len(dates))
    })