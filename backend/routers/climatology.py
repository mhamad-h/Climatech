from fastapi import APIRouter, HTTPException, BackgroundTasks
from datetime import date, datetime, timedelta
from typing import Optional
import logging

from services.forecast_service import ForecastService
from services.historical_data_service import HistoricalDataService
from services.climatology_service import ClimatologyService
from models.forecast_models import (
    ExtendedForecastRequest, QuickForecastRequest, 
    HistoricalDataRequest, ClimatologyRequest
)
from models.weather_data import ExtendedForecastResponse

logger = logging.getLogger(__name__)
router = APIRouter()

# Initialize services
forecast_service = ForecastService()
historical_service = HistoricalDataService()
climatology_service = ClimatologyService()


@router.post("/forecast/extended", response_model=ExtendedForecastResponse)
async def get_extended_forecast(request: ExtendedForecastRequest):
    """Get extended weather forecast (up to 6 months) using climatology methods"""
    
    try:
        logger.info(f"Extended forecast request: {request.latitude}, {request.longitude} for {request.forecast_days} days")
        
        result = await forecast_service.generate_extended_forecast(
            latitude=request.latitude,
            longitude=request.longitude,
            start_date=request.start_date,
            forecast_days=request.forecast_days,
            include_climate_context=request.include_climate_context
        )
        
        return result
        
    except ValueError as e:
        logger.error(f"Validation error in extended forecast: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating extended forecast: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate forecast")


@router.post("/forecast/quick")
async def get_quick_forecast(request: QuickForecastRequest):
    """Get quick forecast (1-30 days) for immediate needs"""
    
    try:
        extended_request = ExtendedForecastRequest(
            latitude=request.latitude,
            longitude=request.longitude,
            start_date=date.today(),
            forecast_days=min(request.days_ahead, 30),
            include_daily=True,
            include_monthly=False,
            include_climate_context=False,
            include_uncertainty=True
        )
        
        result = await forecast_service.generate_extended_forecast(
            latitude=extended_request.latitude,
            longitude=extended_request.longitude,
            start_date=extended_request.start_date,
            forecast_days=extended_request.forecast_days,
            include_climate_context=False
        )
        
        # Return only daily forecasts for quick response
        return {
            "location": result.location,
            "forecast_generated": result.forecast_generated,
            "daily_forecasts": result.daily_forecasts[:request.days_ahead],
            "overall_confidence": result.overall_confidence,
            "methodology": "Quick climatology-based forecast"
        }
        
    except Exception as e:
        logger.error(f"Error generating quick forecast: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate quick forecast")


@router.get("/historical/{latitude}/{longitude}")
async def get_historical_data(
    latitude: float, 
    longitude: float,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    years: Optional[int] = 5
):
    """Get historical weather data for a location"""
    
    try:
        if start_date and end_date:
            start = datetime.strptime(start_date, "%Y-%m-%d").date()
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
            
            historical_data = await historical_service.fetch_historical_data(
                latitude, longitude, start, end
            )
        else:
            historical_data = await historical_service.get_last_n_years_data(
                latitude, longitude, years or 5
            )
        
        # Convert to dict format for JSON response
        data_dict = [
            {
                "date": record.date.isoformat(),
                "temperature_max": record.temperature_max,
                "temperature_min": record.temperature_min,
                "precipitation": record.precipitation,
                "humidity": record.humidity,
                "wind_speed": record.wind_speed,
                "wind_direction": record.wind_direction.value if record.wind_direction else None,
                "pressure": record.pressure
            }
            for record in historical_data
        ]
        
        data_quality = historical_service.validate_data_quality(historical_data)
        
        return {
            "location": {"latitude": latitude, "longitude": longitude},
            "data_period": {
                "start_date": min(d.date for d in historical_data).isoformat() if historical_data else None,
                "end_date": max(d.date for d in historical_data).isoformat() if historical_data else None,
                "record_count": len(historical_data)
            },
            "data_quality": data_quality,
            "data": data_dict
        }
        
    except Exception as e:
        logger.error(f"Error fetching historical data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch historical data")


@router.post("/climate-normal/{latitude}/{longitude}")
async def get_climate_normal(
    latitude: float, 
    longitude: float, 
    request: ClimatologyRequest
):
    """Calculate climate normal values for a location and date"""
    
    try:
        target_date = request.analysis_date or date.today()
        
        # Get historical data
        historical_data = await historical_service.get_last_n_years_data(
            latitude, longitude, request.years_of_data
        )
        
        if not historical_data:
            raise ValueError("No historical data available for climate normal calculation")
        
        # Calculate climate normal
        climate_normal = climatology_service.calculate_day_of_year_climatology(
            historical_data, target_date
        )
        
        # Calculate seasonal trends
        seasonal_trends = climatology_service.calculate_seasonal_trends(historical_data)
        
        return {
            "location": {"latitude": latitude, "longitude": longitude},
            "analysis_date": target_date.isoformat(),
            "years_of_data": request.years_of_data,
            "climate_normal": {
                "temperature_max_normal": climate_normal.temperature_max_normal,
                "temperature_min_normal": climate_normal.temperature_min_normal,
                "precipitation_normal": climate_normal.precipitation_normal,
                "humidity_normal": climate_normal.humidity_normal,
                "wind_speed_normal": climate_normal.wind_speed_normal,
                "precipitation_probability_normal": climate_normal.precipitation_probability_normal
            },
            "seasonal_context": seasonal_trends,
            "data_quality": historical_service.validate_data_quality(historical_data)
        }
        
    except Exception as e:
        logger.error(f"Error calculating climate normal: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to calculate climate normal")


@router.get("/forecast/monthly-outlook/{latitude}/{longitude}")
async def get_monthly_outlook(
    latitude: float,
    longitude: float,
    start_month: Optional[str] = None,
    months_ahead: int = 6
):
    """Get monthly weather outlook for the next several months"""
    
    try:
        if start_month:
            start_date = datetime.strptime(start_month, "%Y-%m").date().replace(day=1)
        else:
            today = date.today()
            start_date = today.replace(day=1)
        
        # Generate forecast for the requested months
        forecast_days = months_ahead * 30  # Approximate
        
        result = await forecast_service.generate_extended_forecast(
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            forecast_days=min(forecast_days, 180),  # Max 6 months
            include_climate_context=True
        )
        
        return {
            "location": result.location,
            "forecast_generated": result.forecast_generated,
            "monthly_outlooks": result.monthly_outlooks,
            "overall_confidence": result.overall_confidence,
            "seasonal_outlook": result.seasonal_outlook,
            "notable_patterns": result.notable_patterns
        }
        
    except Exception as e:
        logger.error(f"Error generating monthly outlook: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate monthly outlook")


@router.get("/location/climate-profile/{latitude}/{longitude}")
async def get_location_climate_profile(latitude: float, longitude: float):
    """Get comprehensive climate profile for a location"""
    
    try:
        # Get comprehensive historical data
        historical_data = await historical_service.get_last_n_years_data(
            latitude, longitude, years=10
        )
        
        if not historical_data:
            raise ValueError("Insufficient data for climate profile")
        
        # Calculate comprehensive climate statistics
        seasonal_trends = climatology_service.calculate_seasonal_trends(historical_data)
        
        # Calculate extremes
        temps_max = [d.temperature_max for d in historical_data]
        temps_min = [d.temperature_min for d in historical_data]
        precip_values = [d.precipitation for d in historical_data]
        
        # Annual precipitation by year
        annual_precip = {}
        for record in historical_data:
            year = record.date.year
            if year not in annual_precip:
                annual_precip[year] = 0
            annual_precip[year] += record.precipitation
        
        # Determine wet and dry seasons
        monthly_precip = seasonal_trends["monthly_climatology"]["precipitation"]
        wet_months = [month for month, precip in monthly_precip.items() if precip > sum(monthly_precip.values())/12]
        dry_months = [month for month, precip in monthly_precip.items() if precip < sum(monthly_precip.values())/12]
        
        return {
            "location": {"latitude": latitude, "longitude": longitude},
            "analysis_period": {
                "start_year": min(d.date.year for d in historical_data),
                "end_year": max(d.date.year for d in historical_data),
                "data_years": len(set(d.date.year for d in historical_data))
            },
            "temperature_profile": {
                "annual_mean_max": round(sum(temps_max) / len(temps_max), 1),
                "annual_mean_min": round(sum(temps_min) / len(temps_min), 1),
                "absolute_maximum": round(max(temps_max), 1),
                "absolute_minimum": round(min(temps_min), 1),
                "monthly_normals": seasonal_trends["monthly_climatology"]
            },
            "precipitation_profile": {
                "annual_total_mean": round(sum(annual_precip.values()) / len(annual_precip), 1),
                "wettest_year": max(annual_precip.values()),
                "driest_year": min(annual_precip.values()),
                "daily_maximum": round(max(precip_values), 1),
                "wet_season_months": wet_months,
                "dry_season_months": dry_months
            },
            "climate_trends": seasonal_trends["annual_trends"],
            "data_quality": historical_service.validate_data_quality(historical_data)
        }
        
    except Exception as e:
        logger.error(f"Error generating climate profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to generate climate profile")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Climatech Climatology API",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "capabilities": [
            "6-month extended forecasting",
            "climatology-based predictions",
            "historical weather data",
            "climate normal calculations",
            "seasonal trend analysis"
        ]
    }