import React, { useState } from 'react';
import LocationMap from './components/Map.jsx';
import LocationInput from './components/LocationInput.jsx';
import EventDatePicker from './components/EventDatePicker.jsx';
import ResultsDisplay from './components/ResultsDisplay.jsx';
import Loader from './components/Loader.jsx';
import { getForecast } from './services/api.js';

function App() {
  // Location state
  const [latitude, setLatitude] = useState(null);
  const [longitude, setLongitude] = useState(null);
  const [searchResult, setSearchResult] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);
  
  // Date state
  const [startDate, setStartDate] = useState(null);
  const [endDate, setEndDate] = useState(null);
  const [horizonHours, setHorizonHours] = useState(168);

  // API interaction state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  // Location handlers
  const handleLocationChange = (lat, lng) => {
    setLatitude(lat);
    setLongitude(lng);
    setSearchResult(null);
    setError(null);
  };

  const handleMapLocationSelect = (lat, lng) => {
    handleLocationChange(lat, lng);
  };

  const handleSearch = async (query) => {
    setIsSearching(true);
    setSearchError(null);
    
    try {
      // Use Nominatim geocoding API
      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`
      );
      
      if (!response.ok) {
        throw new Error('Search failed');
      }
      
      const results = await response.json();
      
      if (results.length === 0) {
        throw new Error('Location not found');
      }
      
      const result = results[0];
      const lat = parseFloat(result.lat);
      const lng = parseFloat(result.lon);
      
      setSearchResult([lat, lng]);
    } catch (err) {
      setSearchError(err.message);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearchResultSelect = () => {
    if (searchResult) {
      handleLocationChange(searchResult[0], searchResult[1]);
    }
  };

  // Date handlers
  const handleDateChange = ({ startDate: start, endDate: end, horizonHours: horizon }) => {
    setStartDate(start);
    setEndDate(end);
    setHorizonHours(horizon);
    setError(null);
  };

  // Forecast submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!latitude || !longitude) {
      setError('Please select a location');
      return;
    }
    
    if (!startDate) {
      setError('Please select a start date and time');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const requestParams = {
        latitude,
        longitude,
        start_datetime_utc: startDate.toISOString(),
        horizon_hours: horizonHours
      };
      
      console.log('Sending forecast request with params:', requestParams);
      
      const forecastData = await getForecast(requestParams);
      
      // Transform backend data to match frontend expectations
      const transformedData = {
        ...forecastData,
        forecast: {
          hourly: forecastData.forecast?.hourly_data || [],
          summary: {
            probability_any_rain: forecastData.forecast?.summary?.average_probability || 0,
            total_expected_mm: forecastData.forecast?.summary?.total_precipitation_mm || 0,
            peak_risk_window: forecastData.forecast?.hourly_data?.[forecastData.forecast?.summary?.peak_intensity_hour || 0]?.datetime_utc || new Date().toISOString(),
            confidence_level: forecastData.forecast?.summary?.confidence_score > 0.7 ? 'high' : 
                             forecastData.forecast?.summary?.confidence_score > 0.4 ? 'moderate' : 'low',
            recommendation: forecastData.forecast?.summary?.weather_summary || 'Forecast generated successfully'
          }
        }
      };
      
      setResult(transformedData);
    } catch (err) {
      setError(err.message || 'Failed to generate forecast');
    } finally {
      setLoading(false);
    }
  };

  // Export handlers
  const handleExport = () => {
    if (!result || !result.forecast || !result.forecast.hourly) {
      return;
    }
    
    const csvContent = [
      ['DateTime UTC', 'DateTime Local', 'Precipitation Probability', 'Precipitation Amount (mm)', 'Confidence Low', 'Confidence High', 'Temperature C', 'Humidity %'].join(','),
      ...result.forecast.hourly.map(hour => [
        hour.datetime_utc,
        hour.datetime_local,
        hour.precipitation_probability,
        hour.precipitation_amount_mm,
        hour.confidence_low,
        hour.confidence_high,
        hour.temperature_c || '',
        hour.humidity_percent || ''
      ].join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `precipitation_forecast_${latitude}_${longitude}_${startDate?.toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const isFormValid = latitude && longitude && startDate;

  return (
    <div className="min-h-screen px-4 py-6 md:px-8 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <header className="max-w-6xl mx-auto mb-8 text-center">
        <h1 className="text-4xl md:text-6xl font-bold text-white tracking-tight mb-4 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
        GeoClime 🌧️
        </h1>
        <p className="text-lg text-gray-400 mb-2">
          Advanced precipitation forecasting using NASA data & machine learning
        </p>
        <p className="text-sm text-gray-500">
          Get hourly probability forecasts up to 30 days ahead
        </p>
      </header>

      <main className="max-w-6xl mx-auto space-y-8">
        {/* Map Section */}
        <section className="bg-slate-800 p-6 rounded-xl shadow-2xl border border-slate-700">
          <h2 className="text-xl font-semibold mb-4 text-slate-100 flex items-center gap-2">
            🗺️ Select Location
          </h2>
          <LocationMap
            selectedPosition={latitude && longitude ? [latitude, longitude] : null}
            onLocationSelect={handleMapLocationSelect}
            searchResult={searchResult}
            onSearchResultSelect={handleSearchResultSelect}
            className="h-80 w-full rounded-lg overflow-hidden border border-slate-600"
          />
        </section>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Input Section */}
          <div className="space-y-6">
            <section className="bg-slate-800 p-6 rounded-xl shadow-2xl border border-slate-700">
              <h2 className="text-xl font-semibold mb-4 text-slate-100 flex items-center gap-2">
                📍 Location Details
              </h2>
              <LocationInput
                latitude={latitude}
                longitude={longitude}
                onLocationChange={handleLocationChange}
                onSearch={handleSearch}
                isSearching={isSearching}
                searchError={searchError}
              />
            </section>

            <section className="bg-slate-800 p-6 rounded-xl shadow-2xl border border-slate-700">
              <h2 className="text-xl font-semibold mb-4 text-slate-100 flex items-center gap-2">
                📅 Event Timing
              </h2>
              <EventDatePicker
                startDate={startDate}
                endDate={endDate}
                onDateChange={handleDateChange}
              />
            </section>

            <section className="bg-slate-800 p-6 rounded-xl shadow-2xl border border-slate-700">
              <h2 className="text-xl font-semibold mb-4 text-slate-100 flex items-center gap-2">
                ⚡ Generate Forecast
              </h2>
              <form onSubmit={handleSubmit} className="space-y-4">
                <button
                  type="submit"
                  disabled={!isFormValid || loading}
                  className="w-full py-3 px-6 rounded-lg bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Generating Forecast...
                    </>
                  ) : (
                    <>
                      🌦️ Get Precipitation Forecast
                    </>
                  )}
                </button>
                
                {!isFormValid && (
                  <p className="text-sm text-yellow-400 text-center">
                    Please select a location and event date to generate forecast
                  </p>
                )}
              </form>
            </section>
          </div>

          {/* Results Section */}
          <div>
            <section className="bg-slate-800 p-6 rounded-xl shadow-2xl border border-slate-700">
              <h2 className="text-xl font-semibold mb-4 text-slate-100 flex items-center gap-2">
                📊 Forecast Results
              </h2>
              
              {loading && <Loader message="Generating your precipitation forecast..." />}
              
              {error && (
                <div className="bg-red-500 bg-opacity-10 border border-red-500 border-opacity-30 p-4 rounded-lg">
                  <h4 className="text-red-400 font-semibold mb-2">❌ Error</h4>
                  <p className="text-sm text-red-300">{error}</p>
                </div>
              )}
              
              {result && !loading && (
                <ResultsDisplay data={result} onExport={handleExport} />
              )}
              
              {!result && !loading && !error && (
                <div className="text-center py-12">
                  <div className="text-6xl mb-4">🌤️</div>
                  <p className="text-gray-400 mb-2">Ready to generate your forecast</p>
                  <p className="text-sm text-gray-500">
                    Select a location and date above, then click "Get Precipitation Forecast"
                  </p>
                </div>
              )}
            </section>
          </div>
        </div>
      </main>

      <footer className="mt-16 text-center text-xs text-gray-500 border-t border-slate-700 pt-8">
        <div className="max-w-4xl mx-auto">
          <p className="mb-2">
            <strong>Climatech</strong> - NASA Space Apps Challenge 2025 | Educational & Research Use Only
          </p>
          <p>
            Built with React + FastAPI | Data sources: NASA GPM, NASA POWER, OpenStreetMap
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
