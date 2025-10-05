import React, { useState } from 'react';

const ExtendedForecast = ({ data, showClimateNormals, selectedParameters }) => {
  const [selectedTimeframe, setSelectedTimeframe] = useState('daily');
  const [selectedParameter, setSelectedParameter] = useState('temperature');

  if (!data || !data.daily_forecasts) {
    return (
      <div className="text-center text-gray-400">
        No extended forecast data available
      </div>
    );
  }

  const { daily_forecasts: forecasts, climate_normals, monthly_outlooks } = data;
  
  // Create metadata from available data
  const metadata = {
    latitude: data.location?.latitude,
    longitude: data.location?.longitude,
    overall_confidence: data.overall_confidence,
    primary_method: data.methodology || 'Climatology',
    forecast_period: data.forecast_period
  };

  const confidence_metrics = {
    data_quality: data.data_completeness || 'Good',
    historical_skill: 'Based on 5-year analysis',
    model_agreement: data.overall_confidence,
    seasonal_factors: data.seasonal_outlook
  };

  // Group forecasts by week for weekly view
  const getWeeklyForecast = () => {
    const weeks = {};
    forecasts.forEach(forecast => {
      const date = new Date(forecast.date);
      const weekStart = new Date(date.getFullYear(), date.getMonth(), date.getDate() - date.getDay());
      const weekKey = weekStart.toISOString().split('T')[0];
      
      if (!weeks[weekKey]) {
        weeks[weekKey] = {
          week_start: weekKey,
          forecasts: [],
          avg_temperature: 0,
          total_precipitation: 0,
          avg_humidity: 0,
          avg_wind_speed: 0
        };
      }
      weeks[weekKey].forecasts.push(forecast);
    });

    // Calculate weekly averages
    Object.keys(weeks).forEach(weekKey => {
      const week = weeks[weekKey];
      const count = week.forecasts.length;
      
      week.avg_temperature = week.forecasts.reduce((sum, f) => sum + ((f.temperature_max + f.temperature_min) / 2), 0) / count;
      week.total_precipitation = week.forecasts.reduce((sum, f) => sum + (f.precipitation_amount || 0), 0);
      week.avg_humidity = week.forecasts.reduce((sum, f) => sum + (f.humidity || 0), 0) / count;
      week.avg_wind_speed = week.forecasts.reduce((sum, f) => sum + (f.wind_speed || 0), 0) / count;
    });

    return Object.values(weeks).sort((a, b) => new Date(a.week_start) - new Date(b.week_start));
  };

  const getConfidenceBadge = (confidence) => {
    const colors = {
      'high': 'bg-green-500 text-white',
      'moderate': 'bg-yellow-500 text-black',
      'low': 'bg-red-500 text-white'
    };
    return colors[confidence] || 'bg-gray-500 text-white';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric'
    });
  };

  const formatTemperature = (temp) => `${Math.round(temp)}°C`;
  const formatPrecipitation = (precip) => `${precip.toFixed(1)}mm`;
  const formatHumidity = (humidity) => `${Math.round(humidity)}%`;
  const formatWindSpeed = (speed) => `${Math.round(speed)} km/h`;

  const weeklyData = getWeeklyForecast();

  return (
    <div className="space-y-6">
      {/* Header with metadata */}
      <div className="bg-slate-700 p-4 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-white">Extended Forecast</h3>
          <span className={`px-3 py-1 rounded-full text-sm font-medium ${getConfidenceBadge(metadata?.overall_confidence)}`}>
            {metadata?.overall_confidence || 'moderate'} confidence
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Location:</span>
            <div className="text-white font-medium">
              {metadata?.latitude?.toFixed(2)}°, {metadata?.longitude?.toFixed(2)}°
            </div>
          </div>
          <div>
            <span className="text-gray-400">Period:</span>
            <div className="text-white font-medium">{forecasts.length} days</div>
          </div>
          <div>
            <span className="text-gray-400">Method:</span>
            <div className="text-white font-medium">{metadata?.primary_method || 'Climatology'}</div>
          </div>
          <div>
            <span className="text-gray-400">Data Quality:</span>
            <div className="text-white font-medium">{confidence_metrics?.data_quality || 'Good'}</div>
          </div>
        </div>
      </div>

      {/* View toggles */}
      <div className="flex space-x-2">
        <button
          onClick={() => setSelectedTimeframe('daily')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            selectedTimeframe === 'daily' 
              ? 'bg-blue-600 text-white' 
              : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          Daily View
        </button>
        <button
          onClick={() => setSelectedTimeframe('weekly')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            selectedTimeframe === 'weekly' 
              ? 'bg-blue-600 text-white' 
              : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          Weekly Summary
        </button>
      </div>

      {/* Parameter selector */}
      {selectedTimeframe === 'daily' && (
        <div className="flex flex-wrap gap-2">
          {selectedParameters.map(param => (
            <button
              key={param}
              onClick={() => setSelectedParameter(param)}
              className={`px-3 py-1 rounded-lg text-sm font-medium transition ${
                selectedParameter === param
                  ? 'bg-indigo-600 text-white'
                  : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
              }`}
            >
              {param.charAt(0).toUpperCase() + param.slice(1)}
            </button>
          ))}
        </div>
      )}

      {/* Daily forecast view */}
      {selectedTimeframe === 'daily' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-96 overflow-y-auto">
          {forecasts.map((forecast, index) => (
            <div key={index} className="bg-slate-700 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="font-medium text-white">{formatDate(forecast.date)}</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${getConfidenceBadge(forecast.confidence_level)}`}>
                  {forecast.confidence_level}
                </span>
              </div>
              
              <div className="space-y-2 text-sm">
                {selectedParameters.includes('temperature') && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Temperature:</span>
                    <span className="text-white font-medium">
                      {Math.round((forecast.temperature_max + forecast.temperature_min) / 2)}°C 
                      ({Math.round(forecast.temperature_min)}° - {Math.round(forecast.temperature_max)}°)
                    </span>
                  </div>
                )}
                
                {selectedParameters.includes('precipitation') && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Precipitation:</span>
                    <span className="text-white font-medium">{Math.round(forecast.precipitation_amount || 0)} mm</span>
                  </div>
                )}
                
                {selectedParameters.includes('humidity') && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Humidity:</span>
                    <span className="text-white font-medium">{Math.round(forecast.humidity || 0)}%</span>
                  </div>
                )}
                
                {selectedParameters.includes('wind') && (
                  <div className="flex justify-between">
                    <span className="text-gray-400">Wind Speed:</span>
                    <span className="text-white font-medium">{Math.round(forecast.wind_speed || 0)} km/h</span>
                  </div>
                )}

                <div className="flex justify-between">
                  <span className="text-gray-400">Conditions:</span>
                  <span className="text-white font-medium">{forecast.weather_condition || 'Partly Cloudy'}</span>
                </div>
              </div>

              {showClimateNormals && forecast.vs_normal && (
                <div className="mt-3 pt-2 border-t border-slate-600">
                  <div className="text-xs text-gray-400">vs. Climate Normal:</div>
                  <div className="flex justify-between text-xs">
                    <span>Temp:</span>
                    <span className={forecast.vs_normal.temperature > 0 ? 'text-red-400' : 'text-blue-400'}>
                      {forecast.vs_normal.temperature > 0 ? '+' : ''}{forecast.vs_normal.temperature.toFixed(1)}°C
                    </span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Weekly summary view */}
      {selectedTimeframe === 'weekly' && (
        <div className="space-y-4">
          {weeklyData.map((week, index) => (
            <div key={index} className="bg-slate-700 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-3">
                <span className="font-medium text-white">
                  Week of {formatDate(week.week_start)}
                </span>
                <span className="text-sm text-gray-400">{week.forecasts.length} days</span>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Avg Temperature:</span>
                  <div className="text-white font-medium">{Math.round(week.avg_temperature || 0)}°C</div>
                </div>
                <div>
                  <span className="text-gray-400">Total Precipitation:</span>
                  <div className="text-white font-medium">{Math.round(week.total_precipitation || 0)} mm</div>
                </div>
                <div>
                  <span className="text-gray-400">Avg Humidity:</span>
                  <div className="text-white font-medium">{Math.round(week.avg_humidity || 0)}%</div>
                </div>
                <div>
                  <span className="text-gray-400">Avg Wind Speed:</span>
                  <div className="text-white font-medium">{Math.round(week.avg_wind_speed || 0)} km/h</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Confidence metrics */}
      {confidence_metrics && (
        <div className="bg-slate-700 p-4 rounded-lg">
          <h4 className="font-medium text-white mb-3">Forecast Confidence Metrics</h4>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Historical Skill:</span>
              <div className="text-white font-medium">{confidence_metrics.historical_skill || 'N/A'}</div>
            </div>
            <div>
              <span className="text-gray-400">Model Agreement:</span>
              <div className="text-white font-medium">{confidence_metrics.model_agreement || 'N/A'}</div>
            </div>
            <div>
              <span className="text-gray-400">Seasonal Factors:</span>
              <div className="text-white font-medium">{confidence_metrics.seasonal_factors || 'N/A'}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ExtendedForecast;