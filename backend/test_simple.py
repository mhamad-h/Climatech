from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import numpy as np
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# CORS configuration for development - allow all origins for Codespace compatibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=False,  # Set to False when using wildcard origins
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["*"],
)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    logger.info(f"Headers: {dict(request.headers)}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code}")
    return response

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@app.get("/api/forecast")
async def forecast_get_handler():
    """Handle GET requests to forecast endpoint (for debugging)"""
    return {"error": "This endpoint expects a POST request with forecast parameters"}

@app.post("/api/forecast")
async def simple_forecast(request: dict):
    """Simple test forecast endpoint"""
    
    # Extract request parameters
    lat = request.get("latitude", 0)
    lon = request.get("longitude", 0)
    hours = request.get("horizon_hours", 24)
    start_datetime_str = request.get("start_datetime_utc", "2025-01-16T15:00:00Z")
    
    # Parse the start datetime from the request
    try:
        from datetime import datetime
        # Remove 'Z' and parse
        if start_datetime_str.endswith('Z'):
            start_datetime_str = start_datetime_str[:-1]
        base_time = datetime.fromisoformat(start_datetime_str)
    except (ValueError, TypeError):
        # Fallback to default if parsing fails
        base_time = datetime(2025, 1, 16, 15, 0, 0)
    
    # Generate simple mock forecast data
    hourly_data = []
    
    # Determine climate zone and base precipitation characteristics
    def get_climate_characteristics(latitude, longitude):
        """Get realistic climate characteristics based on location"""
        
        # Sahara Desert detection
        if 15 <= latitude <= 30 and -17 <= longitude <= 40:
            return {
                'base_precip_prob': 0.02,  # Very dry - 2% chance
                'seasonal_factor': 0.01,   # Minimal seasonal variation
                'base_temp': 35,           # Hot
                'temp_variation': 15,      # Large daily variation
                'humidity_base': 20,       # Very low humidity
                'precip_intensity': 0.5    # Light when it does rain
            }
        
        # Other major deserts (Gobi, Arabian, etc.)
        elif (abs(latitude) > 20 and abs(latitude) < 35) or (longitude > 35 and longitude < 75 and latitude > 20):
            return {
                'base_precip_prob': 0.05,
                'seasonal_factor': 0.03,
                'base_temp': 28,
                'temp_variation': 12,
                'humidity_base': 25,
                'precip_intensity': 1.0
            }
        
        # Tropical regions (near equator, high humidity)
        elif abs(latitude) < 15:
            return {
                'base_precip_prob': 0.35,  # Much higher chance
                'seasonal_factor': 0.25,   # Strong seasonal patterns
                'base_temp': 27,
                'temp_variation': 8,
                'humidity_base': 70,       # High humidity
                'precip_intensity': 5.0    # Heavy tropical rain
            }
        
        # Polar regions
        elif abs(latitude) > 60:
            return {
                'base_precip_prob': 0.15,  # Mostly snow/ice
                'seasonal_factor': 0.1,
                'base_temp': -10 if latitude > 0 else -15,
                'temp_variation': 5,
                'humidity_base': 60,
                'precip_intensity': 1.5
            }
        
        # Temperate regions (default)
        else:
            return {
                'base_precip_prob': 0.2,
                'seasonal_factor': 0.15,
                'base_temp': 15,
                'temp_variation': 10,
                'humidity_base': 55,
                'precip_intensity': 3.0
            }
    
    climate = get_climate_characteristics(lat, lon)
    
    # Set random seed based on location for consistent results
    np.random.seed(int(abs(lat * lon * 1000)) % 2**32)
    
    for i in range(hours):
        hour_time = base_time + timedelta(hours=i)
        
        # Seasonal effects (simplified - based on latitude and time of year)
        day_of_year = hour_time.timetuple().tm_yday
        if lat > 0:  # Northern hemisphere
            seasonal_multiplier = 1 + climate['seasonal_factor'] * np.sin(2 * np.pi * (day_of_year - 80) / 365)
        else:  # Southern hemisphere (seasons flipped)
            seasonal_multiplier = 1 + climate['seasonal_factor'] * np.sin(2 * np.pi * (day_of_year - 80 + 182.5) / 365)
        
        # Diurnal patterns (afternoon/evening precipitation more likely)
        hour_of_day = hour_time.hour
        diurnal_multiplier = 1 + 0.3 * np.sin(2 * np.pi * (hour_of_day - 6) / 24)
        
        # Calculate precipitation probability
        base_prob = climate['base_precip_prob']
        precip_prob = base_prob * seasonal_multiplier * diurnal_multiplier
        precip_prob = max(0.01, min(0.85, precip_prob + np.random.normal(0, 0.05)))
        
        # Precipitation amount (only if probability threshold met)
        if np.random.random() < precip_prob:
            precip_amount = np.random.exponential(climate['precip_intensity'])
        else:
            precip_amount = 0.0
        
        # Temperature calculation
        seasonal_temp_adj = 10 * np.sin(2 * np.pi * (day_of_year - 80) / 365)
        if lat < 0:  # Southern hemisphere
            seasonal_temp_adj *= -1
        
        diurnal_temp_adj = climate['temp_variation'] * np.sin(2 * np.pi * (hour_of_day - 6) / 24)
        temperature = climate['base_temp'] + seasonal_temp_adj + diurnal_temp_adj + np.random.normal(0, 2)
        
        # Humidity (higher when raining, varies with temperature)
        humidity = climate['humidity_base']
        if precip_amount > 0:
            humidity += 20  # Higher humidity when raining
        humidity += np.random.normal(0, 10)
        humidity = max(10, min(95, humidity))
        
        hourly_data.append({
            "datetime_utc": hour_time.isoformat() + "Z",
            "datetime_local": hour_time.isoformat() + "Z",
            "precipitation_probability": round(precip_prob, 3),
            "precipitation_amount_mm": round(precip_amount, 2),
            "confidence_low": round(max(0, precip_amount - 1.0), 2),
            "confidence_high": round(precip_amount + 1.0, 2),
            "temperature_c": round(temperature, 1),
            "humidity_percent": round(humidity, 1)
        })
    
    # Simple forecast summary
    total_precip = sum(h["precipitation_amount_mm"] for h in hourly_data)
    avg_prob = sum(h["precipitation_probability"] for h in hourly_data) / len(hourly_data)
    
    response = {
        "location": {
            "latitude": lat,
            "longitude": lon,
            "elevation": 10.0,
            "timezone": "America/New_York",
            "address": f"Test Location ({lat}, {lon})"
        },
        "forecast": {
            "hourly_data": hourly_data,
            "summary": {
                "total_precipitation_mm": round(total_precip, 2),
                "average_probability": round(avg_prob, 3),
                "confidence_score": 0.75,
                "peak_intensity_hour": 12,
                "weather_summary": "Mixed conditions with occasional precipitation expected"
            }
        },
        "model_info": {
            "primary_model": "simple_test_model",
            "training_period": "2020-2024",
            "last_updated": "2025-01-15T10:30:00Z",
            "features_used": ["location", "time", "climatology"],
            "performance_metrics": {
                "brier_score": 0.185,
                "roc_auc": 0.78,
                "f1_score": 0.65,
                "rmse_mm": 2.3,
                "mae_mm": 1.1,
                "skill_score": 0.23
            }
        },
        "request_id": "test-12345",
        "generated_at": datetime.utcnow().isoformat() + "Z"
    }
    
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)