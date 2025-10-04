from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import numpy as np
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Permissive CORS configuration for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
    
    # Generate simple mock forecast data
    hourly_data = []
    base_time = datetime(2025, 1, 16, 15, 0, 0)
    
    for i in range(hours):
        hour_time = base_time.replace(hour=(base_time.hour + i) % 24)
        
        # Simple mock precipitation data
        precip_prob = 0.2 + 0.3 * np.random.random()  # 20-50% probability
        precip_amount = 0.0 if precip_prob < 0.3 else np.random.exponential(2.0)
        
        hourly_data.append({
            "datetime_utc": hour_time.isoformat() + "Z",
            "datetime_local": hour_time.isoformat() + "Z",
            "precipitation_probability": round(precip_prob, 3),
            "precipitation_amount_mm": round(precip_amount, 2),
            "confidence_low": round(max(0, precip_amount - 1.0), 2),
            "confidence_high": round(precip_amount + 1.0, 2),
            "temperature_c": round(15 + 10 * np.sin(i / 24 * 2 * np.pi), 1),
            "humidity_percent": round(50 + 20 * np.random.random(), 1)
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