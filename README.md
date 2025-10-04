<div align="center">


# Will it Rain on My Parade? (Climatech Monorepo Skeleton)

Skeleton monorepo for the NASA Space Apps Challenge project "Will it Rain on My Parade?".
This repository contains a FastAPI backend (Python) and a React + Vite + Tailwind frontend prepared for rapid iteration on precipitation probability modeling using NASA data sources (e.g., GPM).

> Current Status: SCAFFOLD ONLY – All predictive, data ingestion, and model logic are placeholders awaiting implementation.

---

## Repository Structure

```
.
├── server/                  # FastAPI backend (prediction API placeholder)
│   ├── main.py              # App entrypoint with /api/predict-rain mock endpoint
│   ├── requirements.txt     # Python dependencies (ML libs commented out)
│   ├── models/
│   │   └── prediction.py    # Pydantic request/response models (response TBD)
│   └── ml/
│       ├── data_handler.py  # TODO: data fetching & preprocessing
│       └── predictor.py     # TODO: model loading & inference
├── client/                  # React (Vite) frontend skeleton
│   ├── index.html
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.js
│   └── src/
│       ├── main.jsx
│       ├── App.jsx          # Form + state placeholders
│       ├── index.css        # Tailwind directives + dark theme base
│       ├── components/      # Placeholder UI components
│       │   ├── LocationInput.jsx
│       │   ├── EventDatePicker.jsx
│       │   ├── ResultsDisplay.jsx
│       │   └── Loader.jsx
│       └── services/
│           └── api.js       # Axios instance + TODO for getRainPrediction
├── .gitignore
└── README.md (this file)
```

---

## Backend Server (Python / FastAPI)

### Features (Planned)
- NASA GPM precipitation + auxiliary climate data ingestion.
- Feature engineering (seasonality, anomalies, climatology baselines).
- ML model inference service with confidence metrics.
- Structured JSON response for frontend consumption.

### Current State
`/api/predict-rain` returns a hardcoded mock object. Data + ML layers are not implemented.

### Setup & Run

```bash
cd server

# (Recommended) Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run development server (auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Test the Mock Endpoint
```bash
curl -X POST http://127.0.0.1:8000/api/predict-rain \
	-H 'Content-Type: application/json' \
	-d '{"latitude":40.71,"longitude":-74.00,"eventDate":"2025-10-26"}'
```

### Next Implementation Steps
1. Define `PredictionResponse` model schema in `models/prediction.py`.
2. Implement `fetch_weather_data` + `preprocess_data` with NASA GPM integration.
3. Add `load_model` + `predict` logic with a persisted model artifact.
4. Add error handling & logging (422 validation, 500 internal, structured logs).
5. Introduce tests (pytest + httpx AsyncClient) for /health and /api/predict-rain.
6. Add environment variable management (`.env` + python-dotenv) for API keys.

---

## Frontend Client (React / Vite / Tailwind)

### Features (Planned)
- Input form for location (lat/lon or geocoded search) and event date.
- API call to backend prediction endpoint.
- Result visualization (probability, confidence, narrative summary).
- Dark theme with space/climate aesthetic.

### Current State
Form + state placeholders only. Components and API service are stubs.

### Setup & Run
```bash
cd client

# Install Node dependencies
npm install

# Start Vite dev server (default: http://localhost:5173)
npm run dev
```

### Build Production Bundle
```bash
cd client
npm run build
npm run preview  # Preview static build
```

### Next Implementation Steps
1. Implement `getRainPrediction` in `src/services/api.js`.
2. Replace inline inputs in `App.jsx` with `<LocationInput />` + `<EventDatePicker />`.
3. Add conditional rendering (Loader, ResultsDisplay, error states).
4. Flesh out `ResultsDisplay` with probability visualization & confidence badge.
5. Add basic input validation (lat ∈ [-90,90], lon ∈ [-180,180]).
6. Introduce global state or React Query if complexity grows.

---

## Running Both Concurrently
Open two terminals:

Terminal 1 (backend):
```bash
cd server
source .venv/bin/activate  # if created
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 (frontend):
```bash
cd client
npm run dev
```

The frontend will call the backend at `http://127.0.0.1:8000/api/predict-rain` (adjust if changing ports or host).

---

## Suggested Future Enhancements
- Add Docker Compose for unified dev environment.
- Add Makefile (e.g., `make dev`, `make test`, `make lint`).
- Introduce authentication / rate limiting if exposed publicly.
- Implement monitoring (Prometheus metrics + frontend analytics for usage patterns).
- Add CI pipeline (lint + test + build) via GitHub Actions.
- Model versioning & experiment tracking (MLflow or Weights & Biases).

---

## Contributing Workflow (Proposed)
1. Create feature branch: `feat/<area>-<short-desc>`
2. Implement + add tests.
3. Run linters & formatters.
4. Open PR with checklist referencing README tasks.
5. Require at least one review before merge to `main`.

---

## License
Add your chosen license (MIT / Apache-2.0 / NASA Open Source Agreement) here.

---

## Disclaimer
This is an initial scaffold. No real precipitation forecasts are produced yet. Do **not** use outputs for operational or safety-critical decisions.


</div>

---

## 📁 Repository Structure

```
.
├── client/           # React + Vite + Tailwind frontend
├── server/           # FastAPI backend (prediction API - skeleton)
├── README.md         # This file
└── .gitignore        # Git ignore rules for Python + Node
```

---

## 🚀 Quick Start (Both Services)

Open two terminals (or use a process manager):

1. Backend API at http://127.0.0.1:8000
2. Frontend at http://localhost:5173

See detailed instructions below.

---

## 🧠 Backend Server (Python – FastAPI)

Location: `server/`

### Features (Current Skeleton)
- FastAPI app with CORS enabled for the Vite dev origin.
- `/api/predict-rain` POST endpoint accepting `latitude`, `longitude`, `eventDate`.
- Returns a mock JSON response (to be replaced with real data & ML logic).
- Placeholder modules under `ml/` and `models/` for future development.

### Install & Run

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Test Health Check
```bash
curl http://127.0.0.1:8000/health
```

### Example Predict Request (Mock Response)
```bash
curl -X POST http://127.0.0.1:8000/api/predict-rain \
	-H 'Content-Type: application/json' \
	-d '{"latitude":29.76, "longitude":-95.36, "eventDate":"2025-10-26"}'
```

### Backend TODO Roadmap (High-Level)
- [ ] Implement `fetch_weather_data` using NASA GPM + auxiliary APIs.
- [ ] Add data caching & retry logic.
- [ ] Build feature engineering pipeline in `preprocess_data`.
- [ ] Train & persist ML model (baseline: climatology + simple classifier/regressor).
- [ ] Implement `predict` with uncertainty estimation.
- [ ] Extend `PredictionResponse` schema with probability, confidence, summary.
- [ ] Add authentication / rate limiting (if public).
- [ ] Add automated tests (pytest) & CI.

---

## 💻 Frontend Client (React + Vite + Tailwind)

Location: `client/`

### Features (Current Skeleton)
- Vite + React project with Tailwind configured.
- Dark theme foundation with custom space-inspired palette.
- `App.jsx` contains placeholder form & state logic.
- Components scaffolded under `src/components/` (all contain TODO notes).
- `src/services/api.js` prepared with Axios instance.

### Install & Run
```bash
cd client
npm install
npm run dev
```

Visit: http://localhost:5173

### Frontend TODO Roadmap
- [ ] Implement `LocationInput` (lat/lon validation or geocoding search).
- [ ] Replace date input with richer date picker component.
- [ ] Wire `handleSubmit` to `getRainPrediction` API.
- [ ] Show `Loader` during pending requests.
- [ ] Style `ResultsDisplay` with probability gauge & info cards.
- [ ] Add global error + toast notifications.
- [ ] Add environment-based API URL handling.
- [ ] Write unit tests (React Testing Library) & lint rules.

---

## 🔄 Concurrent Development (Optional Convenience)

You can run both services together using two shells, or create a simple helper script / use tools like `concurrently` or `tmux`. Example (optional, not yet added):

```bash
# From repo root (after manual backend venv activation):
(cd server && uvicorn main:app --reload) &
(cd client && npm run dev)
```

---

## 🧪 Future Enhancements
- Add Dockerfiles & docker-compose for reproducible deployment.
- Add Makefile with common tasks (setup, lint, test, run).
- Introduce logging & observability (structlog / OpenTelemetry).
- Add model version endpoint `/api/model-info`.
- Implement CI pipeline (GitHub Actions) for format + test + build.

---

## 📜 License
Add a suitable open-source license (MIT / Apache-2.0) — TODO.

---

## 🤝 Contributing
Create feature branches, open PRs with clear descriptions, link to related issues, and ensure lint/tests pass before requesting review.

---

Happy building! 🚀

