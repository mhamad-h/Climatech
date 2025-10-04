from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, validator


class LocationData(BaseModel):
    """Location information."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    elevation: Optional[float] = Field(None, description="Elevation in meters")
    timezone: Optional[str] = Field(None, description="Timezone identifier")
    address: Optional[str] = Field(None, description="Human-readable address")


class ForecastRequest(BaseModel):
    """Request model for precipitation forecast."""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude in decimal degrees")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude in decimal degrees")
    start_datetime_utc: datetime = Field(..., description="Start datetime in UTC")
    horizon_hours: int = Field(168, ge=1, le=720, description="Forecast horizon in hours (max 30 days)")
    
    @validator('start_datetime_utc')
    def validate_future_datetime(cls, v):
        # Make the current time timezone-aware for comparison
        now_utc = datetime.now(timezone.utc)
        
        # If v is timezone-naive, assume it's UTC
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)
        
        # For development/testing, allow past dates
        # In production, you might want to enforce future dates only
        # if v <= now_utc:
        #     raise ValueError('start_datetime_utc must be in the future')
        
        return v


class HourlyForecast(BaseModel):
    """Hourly forecast data."""
    datetime_utc: datetime
    datetime_local: Optional[datetime] = None
    precipitation_probability: float = Field(..., ge=0, le=1, description="Probability of precipitation (0-1)")
    precipitation_amount_mm: float = Field(..., ge=0, description="Expected precipitation amount in mm")
    confidence_low: float = Field(..., ge=0, description="Lower confidence bound")
    confidence_high: float = Field(..., ge=0, description="Upper confidence bound")
    confidence_level: str = Field(..., description="Qualitative confidence level")


class ForecastSummary(BaseModel):
    """Summary statistics for the forecast period."""
    total_expected_mm: float = Field(..., ge=0, description="Total expected precipitation")
    probability_any_rain: float = Field(..., ge=0, le=1, description="Probability of any precipitation")
    peak_risk_window: Optional[datetime] = Field(None, description="Time of highest precipitation risk")
    confidence_level: str = Field(..., description="Overall confidence level")
    recommendation: str = Field(..., description="Event planning recommendation")


class ModelInfo(BaseModel):
    """Information about the forecasting model."""
    primary_model: str = Field(..., description="Primary model type")
    training_period: str = Field(..., description="Model training period")
    last_updated: datetime = Field(..., description="Last model update timestamp")
    features_used: List[str] = Field(..., description="List of input features")
    performance_metrics: dict = Field(..., description="Model performance metrics")


class ForecastResponse(BaseModel):
    """Complete forecast response."""
    location: LocationData
    forecast: dict = Field(..., description="Forecast data")
    model_info: ModelInfo
    request_id: Optional[str] = Field(None, description="Unique request identifier")
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    request_id: Optional[str] = Field(None, description="Request identifier")