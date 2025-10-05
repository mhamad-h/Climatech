import React, { useState } from 'react';

const MonthlyOutlook = ({ data, showClimateNormals }) => {
  const [selectedView, setSelectedView] = useState('overview');

  if (!data || !data.monthly_outlooks) {
    return (
      <div className="text-center text-gray-400">
        No monthly outlook data available
      </div>
    );
  }

  const { monthly_outlooks, metadata, seasonal_analysis } = data;

  const getOutlookColor = (tendency) => {
    switch (tendency) {
      case 'above_normal': return 'text-red-400';
      case 'below_normal': return 'text-blue-400';
      case 'near_normal': return 'text-gray-400';
      default: return 'text-gray-400';
    }
  };

  const getOutlookBadge = (tendency) => {
    const colors = {
      'above_normal': 'bg-red-500 text-white',
      'below_normal': 'bg-blue-500 text-white',
      'near_normal': 'bg-gray-500 text-white'
    };
    return colors[tendency] || 'bg-gray-500 text-white';
  };

  const formatMonth = (monthYear) => {
    return new Date(monthYear + '-01').toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long'
    });
  };

  const getConfidenceBadge = (confidence) => {
    const colors = {
      'high': 'bg-green-500 text-white',
      'moderate': 'bg-yellow-500 text-black',
      'low': 'bg-red-500 text-white'
    };
    return colors[confidence] || 'bg-gray-500 text-white';
  };

  const getTendencyText = (tendency) => {
    switch (tendency) {
      case 'above_normal': return 'Above Normal';
      case 'below_normal': return 'Below Normal';
      case 'near_normal': return 'Near Normal';
      default: return 'Unknown';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-slate-700 p-4 rounded-lg">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-lg font-semibold text-white">6-Month Climate Outlook</h3>
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
            <div className="text-white font-medium">{monthly_outlooks.length} months</div>
          </div>
          <div>
            <span className="text-gray-400">Base Period:</span>
            <div className="text-white font-medium">{metadata?.reference_period || '1991-2020'}</div>
          </div>
          <div>
            <span className="text-gray-400">Forecast Method:</span>
            <div className="text-white font-medium">{metadata?.forecast_method || 'Climatological'}</div>
          </div>
        </div>
      </div>

      {/* View toggles */}
      <div className="flex space-x-2">
        <button
          onClick={() => setSelectedView('overview')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            selectedView === 'overview' 
              ? 'bg-green-600 text-white' 
              : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setSelectedView('temperature')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            selectedView === 'temperature' 
              ? 'bg-green-600 text-white' 
              : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          Temperature
        </button>
        <button
          onClick={() => setSelectedView('precipitation')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
            selectedView === 'precipitation' 
              ? 'bg-green-600 text-white' 
              : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
          }`}
        >
          Precipitation
        </button>
      </div>

      {/* Overview */}
      {selectedView === 'overview' && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {monthly_outlooks.map((outlook, index) => (
            <div key={index} className="bg-slate-700 p-4 rounded-lg">
              <div className="flex items-center justify-between mb-3">
                <span className="font-medium text-white">{formatMonth(outlook.month)}</span>
                <span className={`px-2 py-1 rounded text-xs font-medium ${getConfidenceBadge(outlook.confidence_level)}`}>
                  {outlook.confidence_level}
                </span>
              </div>
              
              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">Temperature:</span>
                    <span className={`font-medium ${getOutlookColor(outlook.temperature_tendency)}`}>
                      {getTendencyText(outlook.temperature_tendency)}
                    </span>
                  </div>
                  {showClimateNormals && outlook.temperature_normal && (
                    <div className="text-xs text-gray-500">
                      Normal: {outlook.temperature_normal.toFixed(1)}°C
                    </div>
                  )}
                </div>

                <div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-gray-400">Precipitation:</span>
                    <span className={`font-medium ${getOutlookColor(outlook.precipitation_tendency)}`}>
                      {getTendencyText(outlook.precipitation_tendency)}
                    </span>
                  </div>
                  {showClimateNormals && outlook.precipitation_normal && (
                    <div className="text-xs text-gray-500">
                      Normal: {outlook.precipitation_normal.toFixed(1)}mm
                    </div>
                  )}
                </div>

                <div className="text-xs text-gray-400 mt-2">
                  <div>Key Factors:</div>
                  <div className="text-white">
                    {outlook.key_factors?.join(', ') || 'Seasonal patterns, climate persistence'}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Temperature detailed view */}
      {selectedView === 'temperature' && (
        <div className="space-y-4">
          <div className="bg-slate-700 p-4 rounded-lg">
            <h4 className="font-medium text-white mb-3">Temperature Outlook Details</h4>
            <div className="space-y-3">
              {monthly_outlooks.map((outlook, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-slate-600 rounded">
                  <div>
                    <span className="font-medium text-white">{formatMonth(outlook.month)}</span>
                    {showClimateNormals && outlook.temperature_normal && (
                      <div className="text-sm text-gray-400">
                        Normal: {outlook.temperature_normal.toFixed(1)}°C
                      </div>
                    )}
                  </div>
                  <div className="text-right">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getOutlookBadge(outlook.temperature_tendency)}`}>
                      {getTendencyText(outlook.temperature_tendency)}
                    </span>
                    <div className="text-xs text-gray-400 mt-1">
                      {outlook.temperature_confidence}% confidence
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Precipitation detailed view */}
      {selectedView === 'precipitation' && (
        <div className="space-y-4">
          <div className="bg-slate-700 p-4 rounded-lg">
            <h4 className="font-medium text-white mb-3">Precipitation Outlook Details</h4>
            <div className="space-y-3">
              {monthly_outlooks.map((outlook, index) => (
                <div key={index} className="flex items-center justify-between p-3 bg-slate-600 rounded">
                  <div>
                    <span className="font-medium text-white">{formatMonth(outlook.month)}</span>
                    {showClimateNormals && outlook.precipitation_normal && (
                      <div className="text-sm text-gray-400">
                        Normal: {outlook.precipitation_normal.toFixed(1)}mm
                      </div>
                    )}
                  </div>
                  <div className="text-right">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getOutlookBadge(outlook.precipitation_tendency)}`}>
                      {getTendencyText(outlook.precipitation_tendency)}
                    </span>
                    <div className="text-xs text-gray-400 mt-1">
                      {outlook.precipitation_confidence}% confidence
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Seasonal Analysis */}
      {seasonal_analysis && (
        <div className="bg-slate-700 p-4 rounded-lg">
          <h4 className="font-medium text-white mb-3">Seasonal Analysis & Drivers</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            {seasonal_analysis.dominant_patterns && (
              <div>
                <span className="text-gray-400">Dominant Patterns:</span>
                <div className="text-white font-medium">
                  {seasonal_analysis.dominant_patterns.join(', ')}
                </div>
              </div>
            )}
            
            {seasonal_analysis.climate_drivers && (
              <div>
                <span className="text-gray-400">Climate Drivers:</span>
                <div className="text-white font-medium">
                  {seasonal_analysis.climate_drivers.join(', ')}
                </div>
              </div>
            )}
            
            {seasonal_analysis.historical_analogs && (
              <div>
                <span className="text-gray-400">Similar Years:</span>
                <div className="text-white font-medium">
                  {seasonal_analysis.historical_analogs.join(', ')}
                </div>
              </div>
            )}
            
            {seasonal_analysis.key_uncertainties && (
              <div>
                <span className="text-gray-400">Key Uncertainties:</span>
                <div className="text-white font-medium">
                  {seasonal_analysis.key_uncertainties.join(', ')}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Methodology note */}
      <div className="bg-slate-600 p-3 rounded-lg">
        <div className="text-xs text-gray-300">
          <strong>Note:</strong> Monthly outlooks are based on climatological analysis of historical patterns, 
          seasonal persistence, and analog forecasting. Confidence decreases with lead time. 
          "Above/Below Normal" refers to the upper/lower tercile of the 1991-2020 climate record.
        </div>
      </div>
    </div>
  );
};

export default MonthlyOutlook;