from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models.prediction import PredictionRequest, PredictionResponse
from typing import Any

app = FastAPI(title="Will it Rain on My Parade? API", version="0.1.0")

# Configure CORS to allow the Vite dev server origin
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/predict-rain")
async def predict_rain(payload: PredictionRequest) -> Any:  # Eventually: -> PredictionResponse
    """Predict the probability of rain for a given location and date.

    TODO (Data Acquisition):
    - Use fetch_weather_data() to retrieve historical + near-term forecast precipitation data
      from NASA GPM and potentially other supplementary sources.

    TODO (Preprocessing):
    - Clean and engineer features via preprocess_data().

    TODO (Model Inference):
    - Load model with load_model() (cached) and run predict().
    - Calibrate probabilities and attach confidence metrics.

    TODO (Explainability & Output):
    - Add fields for confidence, contributing factors (e.g., seasonal norms), and disclaimers.

    TODO (Error Handling):
    - Handle invalid coordinates, unsupported date ranges, and upstream API outages gracefully.
    """

    # Mock response for frontend integration while backend logic is under development
    mock_response = {
        "location": {"lat": payload.latitude, "lon": payload.longitude},
        "eventDate": payload.eventDate,
        "rainProbability": 0.45,  # Placeholder probability
        "confidence": "Medium",
        "summary": (
            "Based on placeholder historical patterns, there is a moderate chance of scattered showers. "
            "Forecast model integration pending implementation."
        ),
    }
    return mock_response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
