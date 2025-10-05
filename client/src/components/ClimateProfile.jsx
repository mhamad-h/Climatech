import React, { useState } from 'react';

const ClimateProfile = ({ data }) => {
  const [selectedView, setSelectedView] = useState('overview');
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);

  if (!data) {
    return (
      <div className="text-center text-gray-400">
        No climate profile data available
      </div>
    );
  }

  const { climate_normals, historical_data, location } = data;

  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  const formatTemperature = (temp) => temp ? `${temp.toFixed(1)}°C` : 'N/A';
  const formatPrecipitation = (precip) => precip ? `${precip.toFixed(1)}mm` : 'N/A';
  const formatHumidity = (humidity) => humidity ? `${humidity.toFixed(0)}%` : 'N/A';
  const formatWindSpeed = (speed) => speed ? `${speed.toFixed(1)} km/h` : 'N/A';

  // Get monthly climate normal for selected month
  const getMonthlyNormal = (month) => {
    if (!climate_normals?.monthly_normals) return null;
    return climate_normals.monthly_normals.find(normal => normal.month === month);
  };

  const selectedMonthData = getMonthlyNormal(selectedMonth);

  // Calculate climate statistics
  const getClimateStats = () => {
    if (!climate_normals?.monthly_normals) return null;
    
    const temps = climate_normals.monthly_normals.map(m => m.avg_temperature_c);
    const precips = climate_normals.monthly_normals.map(m => m.total_precipitation_mm);
    
    return {
      annual_avg_temp: temps.reduce((a, b) => a + b, 0) / temps.length,
      annual_precip: precips.reduce((a, b) => a + b, 0),
      warmest_month: climate_normals.monthly_normals.find(m => m.avg_temperature_c === Math.max(...temps)),
      coldest_month: climate_normals.monthly_normals.find(m => m.avg_temperature_c === Math.min(...temps)),
      wettest_month: climate_normals.monthly_normals.find(m => m.total_precipitation_mm === Math.max(...precips)),
      driest_month: climate_normals.monthly_normals.find(m => m.total_precipitation_mm === Math.min(...precips))
    };
  };

  const climateStats = getClimateStats();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-700 p-4 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-white">Climate Profile & Analysis</h3>
          <span className="px-3 py-1 bg-purple-600 text-white rounded-full text-sm font-medium">
            Long-term Data
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Location:</span>
            <div className="text-white font-medium">
              {location?.latitude?.toFixed(2)}°, {location?.longitude?.toFixed(2)}°
            </div>
          </div>
          <div>
            <span className="text-gray-400">Reference Period:</span>
            <div className="text-white font-medium">
              {climate_normals?.reference_period || '1991-2020'}
            </div>
          </div>
          <div>
            <span className="text-gray-400">Data Source:</span>
            <div className="text-white font-medium">NASA POWER</div>
          </div>
          <div>
            <span className="text-gray-400">Climate Zone:</span>
            <div className="text-white font-medium">
              {climate_normals?.climate_classification || 'Analyzing...'}
            </div>
          </div>
        </div>
      </div>

      {/* View toggles */}
      <div className="flex space-x-2">
        <button
          onClick={() => setSelectedView('overview')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            selectedView === 'overview' 
              ? 'bg-purple-600 text-white' 
              : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setSelectedView('monthly')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            selectedView === 'monthly' 
              ? 'bg-purple-600 text-white' 
              : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          Monthly Details
        </button>
        <button
          onClick={() => setSelectedView('trends')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            selectedView === 'trends' 
              ? 'bg-purple-600 text-white' 
              : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          Trends
        </button>
      </div>

      {/* Overview */}
      {selectedView === 'overview' && climateStats && (
        <div className="space-y-4">
          {/* Annual Summary */}
          <div className="bg-slate-700 p-4 rounded-lg">
            <h4 className="font-medium text-white mb-3">Annual Climate Summary</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Annual Avg Temp:</span>
                <div className="text-white font-medium">{formatTemperature(climateStats.annual_avg_temp)}</div>
              </div>
              <div>
                <span className="text-gray-400">Annual Precipitation:</span>
                <div className="text-white font-medium">{formatPrecipitation(climateStats.annual_precip)}</div>
              </div>
              <div>
                <span className="text-gray-400">Temperature Range:</span>
                <div className="text-white font-medium">
                  {formatTemperature(climateStats.coldest_month?.avg_temperature_c)} to {formatTemperature(climateStats.warmest_month?.avg_temperature_c)}
                </div>
              </div>
              <div>
                <span className="text-gray-400">Seasonal Variation:</span>
                <div className="text-white font-medium">
                  {((climateStats.warmest_month?.avg_temperature_c || 0) - (climateStats.coldest_month?.avg_temperature_c || 0)).toFixed(1)}°C
                </div>
              </div>
            </div>
          </div>

          {/* Seasonal Highlights */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="bg-slate-700 p-4 rounded-lg">
              <h4 className="font-medium text-white mb-3">Temperature Extremes</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Warmest Month:</span>
                  <span className="text-white font-medium">
                    {months[climateStats.warmest_month?.month - 1]} ({formatTemperature(climateStats.warmest_month?.avg_temperature_c)})
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Coldest Month:</span>
                  <span className="text-white font-medium">
                    {months[climateStats.coldest_month?.month - 1]} ({formatTemperature(climateStats.coldest_month?.avg_temperature_c)})
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-slate-700 p-4 rounded-lg">
              <h4 className="font-medium text-white mb-3">Precipitation Patterns</h4>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-400">Wettest Month:</span>
                  <span className="text-white font-medium">
                    {months[climateStats.wettest_month?.month - 1]} ({formatPrecipitation(climateStats.wettest_month?.total_precipitation_mm)})
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Driest Month:</span>
                  <span className="text-white font-medium">
                    {months[climateStats.driest_month?.month - 1]} ({formatPrecipitation(climateStats.driest_month?.total_precipitation_mm)})
                  </span>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Monthly Details */}
      {selectedView === 'monthly' && climate_normals?.monthly_normals && (
        <div className="space-y-4">
          {/* Month selector */}
          <div className="flex flex-wrap gap-2">
            {months.map((month, index) => (
              <button
                key={month}
                onClick={() => setSelectedMonth(index + 1)}
                className={`px-3 py-1 rounded-lg text-sm font-medium transition ${
                  selectedMonth === index + 1
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
                }`}
              >
                {month.slice(0, 3)}
              </button>
            ))}
          </div>

          {/* Selected month details */}
          {selectedMonthData && (
            <div className="bg-slate-700 p-4 rounded-lg">
              <h4 className="font-medium text-white mb-3">
                {months[selectedMonth - 1]} Climate Normal
              </h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Avg Temperature:</span>
                  <div className="text-white font-medium">{formatTemperature(selectedMonthData.avg_temperature_c)}</div>
                </div>
                <div>
                  <span className="text-gray-400">Max Temperature:</span>
                  <div className="text-white font-medium">{formatTemperature(selectedMonthData.max_temperature_c)}</div>
                </div>
                <div>
                  <span className="text-gray-400">Min Temperature:</span>
                  <div className="text-white font-medium">{formatTemperature(selectedMonthData.min_temperature_c)}</div>
                </div>
                <div>
                  <span className="text-gray-400">Precipitation:</span>
                  <div className="text-white font-medium">{formatPrecipitation(selectedMonthData.total_precipitation_mm)}</div>
                </div>
                <div>
                  <span className="text-gray-400">Avg Humidity:</span>
                  <div className="text-white font-medium">{formatHumidity(selectedMonthData.avg_humidity_percent)}</div>
                </div>
                <div>
                  <span className="text-gray-400">Avg Wind Speed:</span>
                  <div className="text-white font-medium">{formatWindSpeed(selectedMonthData.avg_wind_speed_kmh)}</div>
                </div>
                <div>
                  <span className="text-gray-400">Rainy Days:</span>
                  <div className="text-white font-medium">{selectedMonthData.rainy_days || 'N/A'}</div>
                </div>
                <div>
                  <span className="text-gray-400">Sunshine Hours:</span>
                  <div className="text-white font-medium">{selectedMonthData.sunshine_hours || 'N/A'}</div>
                </div>
              </div>
            </div>
          )}

          {/* All months overview */}
          <div className="bg-slate-700 p-4 rounded-lg">
            <h4 className="font-medium text-white mb-3">Year-Round Climate</h4>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-400 border-b border-slate-600">
                    <th className="text-left p-2">Month</th>
                    <th className="text-right p-2">Avg Temp</th>
                    <th className="text-right p-2">Precipitation</th>
                    <th className="text-right p-2">Humidity</th>
                  </tr>
                </thead>
                <tbody>
                  {climate_normals.monthly_normals.map((normal, index) => (
                    <tr key={index} className="text-white border-b border-slate-600">
                      <td className="p-2 font-medium">{months[normal.month - 1]}</td>
                      <td className="text-right p-2">{formatTemperature(normal.avg_temperature_c)}</td>
                      <td className="text-right p-2">{formatPrecipitation(normal.total_precipitation_mm)}</td>
                      <td className="text-right p-2">{formatHumidity(normal.avg_humidity_percent)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Trends */}
      {selectedView === 'trends' && historical_data && (
        <div className="space-y-4">
          <div className="bg-slate-700 p-4 rounded-lg">
            <h4 className="font-medium text-white mb-3">Historical Trends & Variability</h4>
            
            {historical_data.trends && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Temperature Trend:</span>
                  <div className="text-white font-medium">
                    {historical_data.trends.temperature > 0 ? '+' : ''}{historical_data.trends.temperature?.toFixed(2)}°C/decade
                  </div>
                </div>
                <div>
                  <span className="text-gray-400">Precipitation Trend:</span>
                  <div className="text-white font-medium">
                    {historical_data.trends.precipitation > 0 ? '+' : ''}{historical_data.trends.precipitation?.toFixed(1)}mm/decade
                  </div>
                </div>
              </div>
            )}

            {historical_data.variability && (
              <div className="mt-4">
                <h5 className="text-white font-medium mb-2">Climate Variability</h5>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400">Temperature Std Dev:</span>
                    <div className="text-white font-medium">±{historical_data.variability.temperature?.toFixed(1)}°C</div>
                  </div>
                  <div>
                    <span className="text-gray-400">Precipitation CV:</span>
                    <div className="text-white font-medium">{historical_data.variability.precipitation?.toFixed(1)}%</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {historical_data.extremes && (
            <div className="bg-slate-700 p-4 rounded-lg">
              <h4 className="font-medium text-white mb-3">Historical Extremes</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-gray-400">Highest Temp:</span>
                  <div className="text-white font-medium">{formatTemperature(historical_data.extremes.max_temperature)}</div>
                </div>
                <div>
                  <span className="text-gray-400">Lowest Temp:</span>
                  <div className="text-white font-medium">{formatTemperature(historical_data.extremes.min_temperature)}</div>
                </div>
                <div>
                  <span className="text-gray-400">Wettest Month:</span>
                  <div className="text-white font-medium">{formatPrecipitation(historical_data.extremes.max_precipitation)}</div>
                </div>
                <div>
                  <span className="text-gray-400">Driest Month:</span>
                  <div className="text-white font-medium">{formatPrecipitation(historical_data.extremes.min_precipitation)}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Data source note */}
      <div className="bg-slate-600 p-3 rounded-lg">
        <div className="text-xs text-gray-300">
          <strong>Data Source:</strong> Climate normals based on NASA POWER reanalysis data. 
          Historical trends calculated from multi-year observations. 
          Climate classification follows Köppen-Geiger system where applicable.
        </div>
      </div>
    </div>
  );
};

export default ClimateProfile;