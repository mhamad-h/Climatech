import React, { useState, useEffect } from 'react';
import LocationMap from './components/Map.jsx';
import LocationInput from './components/LocationInput.jsx';
import DateRangeSelector from './components/DateRangeSelector.jsx';
import ExtendedForecast from './components/ExtendedForecast.jsx';
import MonthlyOutlook from './components/MonthlyOutlook.jsx';
import Loader from './components/Loader.jsx';
import { getExtendedForecast, getMonthlyOutlook, getClimateNormal, getHistoricalData } from './services/api.js';

function App() {
  // Location state
  const [latitude, setLatitude] = useState(null);
  const [longitude, setLongitude] = useState(null);
  const [searchResult, setSearchResult] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState(null);
  
  // Date and forecast state
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [forecastDays, setForecastDays] = useState(30);
  const [forecastType, setForecastType] = useState('extended'); // 'extended', 'monthly'

  // API interaction state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [extendedForecast, setExtendedForecast] = useState(null);
  const [monthlyOutlook, setMonthlyOutlook] = useState(null);
  
  // Display preferences
  const [showClimateNormals, setShowClimateNormals] = useState(true);
  const [selectedParameters, setSelectedParameters] = useState(['temperature', 'precipitation_chance', 'humidity', 'wind']);
  
  // Show detected API URL info
  const showApiInfo = () => {
    const detectedUrl = window.API_BASE_URL || 'Auto-detecting...';
    alert(`🔍 Auto-detected API URL:\n${detectedUrl}\n\nFrontend: ${window.location.href}\nHostname: ${window.location.hostname}`);
  };

  // Location handlers
  const handleLocationChange = (lat, lng) => {
    setLatitude(lat);
    setLongitude(lng);
    setSearchResult(null);
    setError(null);
    // Clear previous forecasts when location changes
    setExtendedForecast(null);
    setMonthlyOutlook(null);
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

  // Date handlers
  const handleDateRangeChange = ({ startDate: start, forecastDays: days }) => {
    setStartDate(start);
    setForecastDays(days);
    setError(null);
  };

  // Forecast type handlers
  const handleForecastTypeChange = (type) => {
    setForecastType(type);
    setError(null);
  };

  // Extended forecast handler
  const handleExtendedForecast = async () => {
    if (!latitude || !longitude) {
      setError('Please select a location');
      return;
    }

    setLoading(true);
    setError(null);
    setForecastType('extended');
    
    try {
      const requestParams = {
        lat: latitude,
        lng: longitude,
        start_date: startDate,
        forecast_days: forecastDays,
        parameters: selectedParameters
      };
      
      console.log('Sending extended forecast request:', requestParams);
      
      const forecastData = await getExtendedForecast(requestParams);
      setExtendedForecast(forecastData);
      setMonthlyOutlook(null);
    } catch (err) {
      setError(err.message || 'Failed to generate extended forecast');
    } finally {
      setLoading(false);
    }
  };

  // Monthly outlook handler
  const handleMonthlyOutlook = async () => {
    if (!latitude || !longitude) {
      setError('Please select a location');
      return;
    }

    setLoading(true);
    setError(null);
    setForecastType('monthly');
    
    try {
      const requestParams = {
        lat: latitude,
        lng: longitude,
        start_date: startDate,
        months: Math.ceil(forecastDays / 30)
      };
      
      console.log('Sending monthly outlook request:', requestParams);
      
      const outlookData = await getMonthlyOutlook(requestParams);
      setMonthlyOutlook(outlookData);
      setExtendedForecast(null);
    } catch (err) {
      setError(err.message || 'Failed to generate monthly outlook');
    } finally {
      setLoading(false);
    }
  };

  // Export handlers
  const handleExport = () => {
    let data = null;
    let filename = '';
    
    switch (forecastType) {
      case 'extended':
        data = extendedForecast;
        filename = `extended_forecast_${latitude}_${longitude}_${startDate}.json`;
        break;
      case 'monthly':
        data = monthlyOutlook;
        filename = `monthly_outlook_${latitude}_${longitude}_${startDate}.json`;
        break;
      default:
        return;
    }
    
    if (!data) return;
    
    const jsonContent = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonContent], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const isFormValid = latitude && longitude && startDate;
  const hasResults = extendedForecast || monthlyOutlook;

  return (
    <div className="min-h-screen px-4 py-6 md:px-8" style={{
      background: 'linear-gradient(135deg, #293132 0%, #474044 50%, #4F5365 100%)'
    }}>
      {/* Rain Effect Styles */}
      <style>{`
        .rain-container {
          position: relative;
          overflow: hidden;
        }
        .rain-effect {
          pointer-events: none;
          position: absolute;
          top: 0; 
          left: 0; 
          width: 100%; 
          height: 200px;
          z-index: 1;
          overflow: hidden;
        }
        .rain-drop {
          position: absolute;
          width: 2px;
          height: 20px;
          background: linear-gradient(to bottom, rgba(165, 180, 252, 0.8) 0%, rgba(165, 180, 252, 0.3) 70%, transparent 100%);
          border-radius: 1px;
          animation: rain-fall linear infinite;
        }
        @keyframes rain-fall {
          0% { 
            transform: translateY(-30px); 
            opacity: 0.8; 
          }
          100% { 
            transform: translateY(220px); 
            opacity: 0; 
          }
        }
      `}</style>
      
      <div className="rain-container">
        <div className="rain-effect">
          {Array.from({ length: 80 }).map((_, i) => (
            <div
              key={i}
              className="rain-drop"
              style={{
                left: `${Math.random() * 100}%`,
                animationDuration: `${0.8 + Math.random() * 0.8}s`,
                animationDelay: `${Math.random() * 2}s`,
                height: `${15 + Math.random() * 10}px`,
                opacity: 0.4 + Math.random() * 0.4,
              }}
            />
          ))}
        </div>
        
        <header className="max-w-6xl mx-auto mb-8 text-center relative z-10">
          <div className="flex justify-end mb-2">
            <button
              onClick={showApiInfo}
              className="px-3 py-1 text-xs bg-purple-gray hover:bg-geo-blue text-white rounded-lg transition"
              title="Show Auto-detected API URL"
            >
              🔍 API Info
            </button>
          </div>
          <h1
            className="text-4xl md:text-6xl font-bold tracking-tight mb-4"
            style={{
              background: 'linear-gradient(90deg, #547AA5 0%, #50D8D7 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              position: 'relative',
              zIndex: 2,
              padding: '0.5rem 0',
              textShadow: '0 2px 8px rgba(30,64,175,0.3)',
            }}
          >
            GeoClime
          </h1>
          <div className="inline-block px-6 py-3 rounded-xl bg-brown-gray/90 backdrop-blur-sm border border-purple-gray/50">
            <p className="text-lg text-gray-200 mb-2">
              Advanced climatology-based weather forecasting using NASA historical data
            </p>
            <p className="text-sm text-gray-400">
              Get extended forecasts up to 6 months ahead with climate analysis
            </p>
          </div>
        </header>
      </div>

      <main className="max-w-6xl mx-auto space-y-8">
        {/* Map Section */}
        <section className="bg-brown-gray p-6 rounded-xl shadow-2xl border border-purple-gray">
          <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
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
            <section className="bg-brown-gray p-6 rounded-xl shadow-2xl border border-purple-gray">
              <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
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

            <section className="bg-brown-gray p-6 rounded-xl shadow-2xl border border-purple-gray">
              <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
                📅 Forecast Period
              </h2>
              <DateRangeSelector
                startDate={startDate}
                forecastDays={forecastDays}
                onDateRangeChange={handleDateRangeChange}
              />
            </section>

            <section className="bg-brown-gray p-6 rounded-xl shadow-2xl border border-purple-gray">
              <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
                🎯 Forecast Type
              </h2>
              
              <div className="grid grid-cols-1 gap-4">
                <button
                  onClick={handleExtendedForecast}
                  disabled={!isFormValid || loading}
                  className="w-full py-3 px-6 rounded-lg bg-gradient-to-r from-geo-blue to-geo-cyan hover:from-geo-blue/80 hover:to-geo-cyan/80 text-white font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading && forecastType === 'extended' ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Generating...
                    </>
                  ) : (
                    <>
                      🌦️ Extended Forecast ({forecastDays} days)
                    </>
                  )}
                </button>

                <button
                  onClick={handleMonthlyOutlook}
                  disabled={!isFormValid || loading}
                  className="w-full py-3 px-6 rounded-lg bg-gradient-to-r from-purple-gray to-geo-blue hover:from-purple-gray/80 hover:to-geo-blue/80 text-white font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {loading && forecastType === 'monthly' ? (
                    <>
                      <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Generating...
                    </>
                  ) : (
                    <>
                      📊 Monthly Outlook (6 months)
                    </>
                  )}
                </button>


              </div>
              
              {!isFormValid && (
                <p className="text-sm text-geo-cyan text-center mt-4">
                  Please select a location and date to generate forecasts
                </p>
              )}
            </section>

            {/* Parameter Selection */}
            {(forecastType === 'extended' || forecastType === 'monthly') && (
              <section className="bg-brown-gray p-6 rounded-xl shadow-2xl border border-purple-gray">
                <h2 className="text-xl font-semibold mb-4 text-white flex items-center gap-2">
                  ⚙️ Parameters
                </h2>
                
                <div className="grid grid-cols-2 gap-3">
                  {['temperature', 'precipitation_chance', 'humidity', 'wind'].map(param => (
                    <label key={param} className="flex items-center space-x-2 text-sm text-white">
                      <input
                        type="checkbox"
                        checked={selectedParameters.includes(param)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedParameters([...selectedParameters, param]);
                          } else {
                            setSelectedParameters(selectedParameters.filter(p => p !== param));
                          }
                        }}
                        className="rounded border-gray-600 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="capitalize">
                        {param === 'precipitation_chance' ? 'Precipitation Chance' : param}
                      </span>
                    </label>
                  ))}
                </div>

                <div className="mt-4">
                  <label className="flex items-center space-x-2 text-sm text-gray-300">
                    <input
                      type="checkbox"
                      checked={showClimateNormals}
                      onChange={(e) => setShowClimateNormals(e.target.checked)}
                      className="rounded border-gray-600 text-blue-600 focus:ring-blue-500"
                    />
                    <span>Show climate normals comparison</span>
                  </label>
                </div>
              </section>
            )}
          </div>

          {/* Results Section */}
          <div>
            <section className="bg-brown-gray p-6 rounded-xl shadow-2xl border border-purple-gray">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                  📊 Forecast Results
                </h2>
                {hasResults && (
                  <button
                    onClick={handleExport}
                    className="px-4 py-2 bg-purple-gray hover:bg-geo-blue text-white rounded-lg text-sm font-medium transition flex items-center gap-2"
                  >
                    📁 Export Data
                  </button>
                )}
              </div>
              
              {loading && (
                <Loader 
                  message={
                    forecastType === 'extended' ? 'Generating extended forecast using climatology methods...' :
                    forecastType === 'monthly' ? 'Creating monthly outlook with seasonal analysis...' :
                    'Processing your request...'
                  } 
                />
              )}
              
              {error && (
                <div className="bg-red-500 bg-opacity-10 border border-red-500 border-opacity-30 p-4 rounded-lg">
                  <h4 className="text-red-400 font-semibold mb-2">❌ Error</h4>
                  <p className="text-sm text-red-300">{error}</p>
                </div>
              )}
              
              {/* Extended Forecast Display */}
              {extendedForecast && !loading && (
                <ExtendedForecast 
                  data={extendedForecast}
                  showClimateNormals={showClimateNormals}
                  selectedParameters={selectedParameters}
                />
              )}
              
              {/* Monthly Outlook Display */}
              {monthlyOutlook && !loading && (
                <MonthlyOutlook 
                  data={monthlyOutlook}
                  showClimateNormals={showClimateNormals}
                />
              )}
              
              {!hasResults && !loading && !error && (
                <div className="text-center py-12">
                  <div className="text-6xl mb-4">�</div>
                  <p className="text-gray-400 mb-2">Ready to generate your climatology forecast</p>
                  <p className="text-sm text-gray-300">
                    Select a location and date above, then choose your forecast type
                  </p>
                </div>
              )}
            </section>
          </div>
        </div>
      </main>

      <footer className="mt-16 text-center text-xs text-gray-300 border-t border-purple-gray pt-8">
        <div className="max-w-4xl mx-auto">
          <p className="mb-2">
            <strong>Geoclime</strong> - Climatology-based Weather Forecasting | Educational & Research Use Only
          </p>
          <p>
            Built with React + FastAPI | Data sources: NASA POWER, OpenStreetMap | Methods: Persistence, Analog, Climate Normals
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
