# Climatech - Precipitation Forecasting App

A comprehensive precipitation forecasting application built for the NASA Space Apps Challenge. This app provides real-time precipitation forecasts using machine learning models trained on NASA weather data, featuring an interactive map interface for event planning.

## Features

- 🌧️ **Real-time precipitation forecasting** up to 30 days ahead
- 🗺️ **Interactive map interface** with location selection
- 🎯 **Event-specific recommendations** for outdoor activities
- 📊 **Probabilistic forecasts** with confidence intervals
- 🤖 **Machine learning models** trained on NASA data
- ⚡ **Fast API backend** with caching and error handling
- 📱 **Responsive web interface** built with React

## Technology Stack

### Frontend
- **React 18** with Vite for fast development
- **Tailwind CSS** for styling
- **Leaflet** for interactive maps
- **Recharts** for data visualization

### Backend
- **FastAPI** for high-performance API
- **Python 3.8+** with async/await support
- **Pydantic** for data validation
- **NASA POWER API** integration

### Machine Learning
- **Scikit-learn** for baseline models
- **LightGBM & XGBoost** for gradient boosted trees
- **Comprehensive feature engineering** pipeline
- **Model evaluation** and performance metrics

## Quick Start

### Prerequisites
- Python 3.8 or higher
- Node.js 18 or higher
- Git

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Climatech
```

### 2. Complete Setup (Recommended)
```bash
# Run the automated setup and training pipeline
python train_models.py
```

This will:
- Install all Python dependencies
- Download and prepare training data
- Train machine learning models
- Generate evaluation reports
- Set up all necessary directories

### 3. Manual Setup

#### Backend Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r server/requirements.txt

# Start the backend server
cd server
python main.py
```

#### Frontend Setup
```bash
# Install dependencies
cd client
npm install

# Start the development server
npm run dev
```

### 4. Access the Application
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Machine Learning Pipeline

### Training Your Own Models

1. **Quick Training** (Recommended):
   ```bash
   python train_models.py
   ```

2. **Manual Training Steps**:
   ```bash
   cd ml
   
   # Download training data
   python download_data.py
   
   # Build ML dataset with feature engineering
   python build_dataset.py
   
   # Train baseline and gradient boosted models
   python train.py
   
   # Evaluate model performance
   python evaluate.py
   ```

### Model Architecture

The app uses a multi-model ensemble approach:

1. **Baseline Models**
   - **Climatology**: Seasonal averages and historical patterns
   - **Persistence**: Current condition extrapolation

2. **Advanced Models**
   - **LightGBM**: Gradient boosted decision trees
   - **XGBoost**: Extreme gradient boosting

3. **Feature Engineering**
   - **Temporal Features**: Hour, day, month, season cycles
   - **Location Features**: Latitude, longitude, elevation effects
   - **Lagged Features**: Historical precipitation patterns (1h to 72h)
   - **Meteorological Features**: Temperature, humidity, pressure interactions
   - **Climatology Features**: Long-term averages and anomalies

### Model Performance

After training, check the evaluation reports in the `evaluation/` directory:
- `evaluation_report.json`: Detailed metrics and performance
- `evaluation_summary.md`: Human-readable summary
- `visualizations/`: Performance plots and feature importance

## API Documentation

### Main Endpoint

**POST** `/api/v1/forecast`

Generate precipitation forecasts for a specific location and time range.

**Request Body:**
```json
{
  "latitude": 40.7128,
  "longitude": -74.0060,
  "start_datetime": "2024-01-15T12:00:00Z",
  "duration_hours": 72,
  "forecast_type": "probabilistic"
}
```

**Response:**
```json
{
  "location": {
    "latitude": 40.7128,
    "longitude": -74.0060,
    "name": "New York, NY, USA",
    "elevation": 10
  },
  "forecast": {
    "1h": {
      "precipitation_mm": 0.5,
      "probability": 0.25,
      "confidence": "high",
      "model_type": "lightgbm"
    },
    "24h": {
      "precipitation_mm": 2.3,
      "probability": 0.45,
      "confidence": "medium", 
      "model_type": "lightgbm"
    }
  },
  "metadata": {
    "forecast_time": "2024-01-15T10:00:00Z",
    "model_type": "trained_ml",
    "data_points_used": 168
  }
}
```

## Project Structure

```
Climatech/
├── client/                     # React frontend
│   ├── src/
│   │   ├── components/         # UI components
│   │   │   ├── Map.jsx         # Interactive map
│   │   │   ├── LocationInput.jsx
│   │   │   ├── EventDatePicker.jsx
│   │   │   └── ResultsDisplay.jsx
│   │   ├── services/
│   │   │   └── api.js         # API integration
│   │   └── App.jsx            # Main application
│   ├── package.json
│   └── vite.config.js
├── backend/                    # FastAPI backend
│   ├── routers/
│   │   └── forecast.py        # Main API endpoints
│   ├── services/
│   │   ├── data_fetch.py      # NASA API integration
│   │   ├── feature_engineering.py # ML features
│   │   └── model_inference.py # Model predictions
│   ├── utils/
│   │   ├── config.py          # Configuration
│   │   └── logging.py         # Structured logging
│   ├── app.py                 # FastAPI application
│   └── requirements.txt
├── ml/                         # Machine learning pipeline
│   ├── models/                # Trained model files
│   ├── data/                  # Training datasets
│   ├── download_data.py       # Data acquisition
│   ├── feature_defs.py        # Feature engineering definitions
│   ├── build_dataset.py       # Dataset preparation
│   ├── train.py               # Model training
│   ├── evaluate.py            # Model evaluation
│   └── model_inference.py     # Real-time inference
├── train_models.py            # Automated training pipeline
└── README.md
```

## Development

### Environment Variables
Create a `.env` file in the backend directory:
```bash
# NASA API (optional - falls back to synthetic data)
NASA_API_KEY=your_nasa_api_key

# Database (optional - uses in-memory cache)
DATABASE_URL=sqlite:///./climatech.db

# Logging
LOG_LEVEL=INFO

# Model settings
MODEL_CACHE_TTL=3600
MAX_FORECAST_HORIZON=720
```

### Running Tests
```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
cd client
npm test

# ML pipeline tests
cd ml
python -m pytest
```

### Model Retraining
```bash
# Retrain models with new data
python train_models.py

# Or run individual steps
cd ml
python download_data.py --update  # Download new data
python train.py --retrain         # Retrain existing models
```

## Deployment

### Docker (Recommended)
```bash
# Build and run with Docker Compose
docker-compose up --build
```

### Manual Deployment

1. **Train Models**:
   ```bash
   python train_models.py
   ```

2. **Build Frontend**:
   ```bash
   cd client
   npm run build
   ```

3. **Deploy Backend** (example for Heroku):
   ```bash
   # Add Procfile with: web: uvicorn backend.app:app --host=0.0.0.0 --port=${PORT:-5000}
   git add .
   git commit -m "Deploy to production"
   git push heroku main
   ```

### GitHub Codespaces

This project is fully compatible with GitHub Codespaces:

1. Open in Codespace
2. Run: `python train_models.py`
3. Start services: `cd backend && python app.py` and `cd client && npm run dev`
4. Use port forwarding to access the application

## Model Performance

Expected performance metrics after training:

- **Binary Classification** (Rain/No Rain): AUC-ROC > 0.75
- **Regression** (Precipitation Amount): R² > 0.4 for short-term forecasts
- **Skill Scores**: Significant improvement over climatology baseline
- **Forecast Horizons**: Reliable predictions up to 72 hours, informative up to 720 hours

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Train models: `python train_models.py`
4. Make your changes and add tests
5. Commit your changes: `git commit -am 'Add feature'`
6. Push to the branch: `git push origin feature-name`
7. Submit a pull request

## Troubleshooting

### Common Issues

1. **Models not loading**: Run `python train_models.py` to train models
2. **NASA API errors**: The app will use synthetic data if NASA API is unavailable
3. **Memory issues during training**: Reduce dataset size in `download_data.py`
4. **Port conflicts**: Change ports in `backend/app.py` and `client/vite.config.js`

### Getting Help

- Check the `evaluation/` directory for model performance reports
- Review logs in the console output
- Ensure all dependencies are installed with correct versions

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- NASA for providing weather data through the POWER API
- OpenStreetMap for geocoding services
- The machine learning community for gradient boosting algorithms
- The open-source community for excellent tools and libraries

## NASA Space Apps Challenge

This project was created for the NASA Space Apps Challenge, addressing the challenge of providing accurate precipitation forecasts for event planning. It combines:

- NASA Earth observation data
- Advanced machine learning techniques
- User-friendly web interface
- Real-world applicability for outdoor event planning

The system provides both probabilistic and deterministic forecasts with uncertainty quantification, making it valuable for decision-making in weather-dependent activities.