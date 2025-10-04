import React, { useState } from 'react';

const ResultsDisplay = ({ data, onExport }) => {
  const [activeTab, setActiveTab] = useState('summary');

  if (!data || !data.forecast) {
    return (
      <div className="text-center py-8">
        <div className="text-gray-400 mb-4">
          <svg className="w-16 h-16 mx-auto mb-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
          </svg>
        </div>
        <p className="text-gray-400">No forecast data to display</p>
        <p className="text-sm text-gray-500 mt-2">Select a location and date to generate a forecast</p>
      </div>
    );
  }

  const { forecast, location, model_info } = data;
  const { summary, hourly } = forecast;

  const getRiskColor = (probability) => {
    if (probability < 0.2) return 'text-green-400';
    if (probability < 0.5) return 'text-yellow-400';
    if (probability < 0.8) return 'text-orange-400';
    return 'text-red-400';
  };

  const getRiskBgColor = (probability) => {
    if (probability < 0.2) return 'bg-green-500';
    if (probability < 0.5) return 'bg-yellow-500';
    if (probability < 0.8) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const tabs = [
    { id: 'summary', label: 'Summary', icon: '📊' },
    { id: 'hourly', label: 'Hourly', icon: '🕐' },
    { id: 'details', label: 'Details', icon: '📋' }
  ];

  return (
    <div className="space-y-6">
      {/* Location Info */}
      <div className="bg-slate-700 p-4 rounded-lg border border-slate-600">
        <h3 className="text-lg font-semibold text-white mb-2">📍 Location</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-400">Coordinates:</span>
            <span className="text-white ml-2">
              {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
            </span>
          </div>
          {location.elevation && (
            <div>
              <span className="text-gray-400">Elevation:</span>
              <span className="text-white ml-2">{location.elevation}m</span>
            </div>
          )}
          {location.address && (
            <div className="col-span-2">
              <span className="text-gray-400">Address:</span>
              <span className="text-white ml-2">{location.address}</span>
            </div>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-slate-600">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-gray-300 hover:border-gray-300'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Summary Tab */}
      {activeTab === 'summary' && (
        <div className="space-y-6">
          {/* Main Risk Assessment */}
          <div className="bg-slate-700 p-6 rounded-lg border border-slate-600">
            <div className="text-center">
              <div className="mb-4">
                <div className={`inline-flex items-center justify-center w-20 h-20 rounded-full ${getRiskBgColor(summary.probability_any_rain)} bg-opacity-20 border-4`}>
                  <span className="text-2xl font-bold text-white">
                    {Math.round(summary.probability_any_rain * 100)}%
                  </span>
                </div>
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">
                Precipitation Probability
              </h3>
              <p className={`text-lg font-medium ${getRiskColor(summary.probability_any_rain)}`}>
                {summary.recommendation}
              </p>
            </div>
          </div>

          {/* Key Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-slate-700 p-4 rounded-lg border border-slate-600">
              <h4 className="text-sm font-medium text-gray-400 mb-1">Total Expected</h4>
              <p className="text-2xl font-bold text-blue-400">{summary.total_expected_mm} mm</p>
              <p className="text-xs text-gray-500">of precipitation</p>
            </div>
            
            <div className="bg-slate-700 p-4 rounded-lg border border-slate-600">
              <h4 className="text-sm font-medium text-gray-400 mb-1">Peak Risk Window</h4>
              <p className="text-sm font-semibold text-yellow-400">
                {new Date(summary.peak_risk_window).toLocaleDateString()} at{' '}
                {new Date(summary.peak_risk_window).toLocaleTimeString([], { 
                  hour: '2-digit', 
                  minute: '2-digit' 
                })}
              </p>
            </div>
            
            <div className="bg-slate-700 p-4 rounded-lg border border-slate-600">
              <h4 className="text-sm font-medium text-gray-400 mb-1">Confidence</h4>
              <p className={`text-lg font-semibold ${
                summary.confidence_level === 'high' ? 'text-green-400' :
                summary.confidence_level === 'moderate' ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {summary.confidence_level.charAt(0).toUpperCase() + summary.confidence_level.slice(1)}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Hourly Tab */}
      {activeTab === 'hourly' && (
        <div className="space-y-4">
          <div className="bg-slate-700 p-4 rounded-lg border border-slate-600">
            <h3 className="text-lg font-semibold text-white mb-4">📈 Hourly Forecast</h3>
            
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {hourly?.slice(0, 48).map((hour, index) => ( // Show first 48 hours
                <div key={index} className="flex items-center justify-between py-2 px-3 bg-slate-800 rounded border border-slate-600">
                  <div className="flex items-center space-x-4">
                    <span className="text-sm text-gray-300 w-20">
                      {new Date(hour.datetime_utc).toLocaleString([], { 
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit'
                      })}
                    </span>
                    
                    <div className="flex items-center space-x-2">
                      <div className={`w-3 h-3 rounded-full ${getRiskBgColor(hour.precipitation_probability)}`}></div>
                      <span className="text-sm font-medium text-white w-12">
                        {Math.round(hour.precipitation_probability * 100)}%
                      </span>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <span className="text-sm font-medium text-blue-400">
                      {hour.precipitation_amount_mm.toFixed(1)} mm
                    </span>
                    <div className="text-xs text-gray-500">
                      ±{((hour.confidence_high - hour.confidence_low) / 2).toFixed(1)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            
            {hourly && hourly.length > 48 && (
              <p className="text-sm text-gray-400 text-center mt-4">
                Showing first 48 hours of {hourly.length} hour forecast
              </p>
            )}
          </div>
        </div>
      )}

      {/* Details Tab */}
      {activeTab === 'details' && (
        <div className="space-y-4">
          <div className="bg-slate-700 p-4 rounded-lg border border-slate-600">
            <h3 className="text-lg font-semibold text-white mb-4">🔬 Model Information</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Primary Model:</span>
                <span className="text-white ml-2">{model_info.primary_model}</span>
              </div>
              <div>
                <span className="text-gray-400">Training Period:</span>
                <span className="text-white ml-2">{model_info.training_period}</span>
              </div>
              <div>
                <span className="text-gray-400">Last Updated:</span>
                <span className="text-white ml-2">
                  {new Date(model_info.last_updated).toLocaleDateString()}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Features Used:</span>
                <span className="text-white ml-2">{model_info.features_used?.length || 0}</span>
              </div>
            </div>
          </div>
          
          <div className="bg-slate-700 p-4 rounded-lg border border-slate-600">
            <h3 className="text-lg font-semibold text-white mb-4">📊 Performance Metrics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="text-center">
                <div className="text-2xl font-bold text-green-400">
                  {model_info.performance_metrics?.roc_auc?.toFixed(2) || 'N/A'}
                </div>
                <div className="text-gray-400">ROC-AUC</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-400">
                  {model_info.performance_metrics?.brier_score?.toFixed(3) || 'N/A'}
                </div>
                <div className="text-gray-400">Brier Score</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-400">
                  {model_info.performance_metrics?.rmse_mm?.toFixed(1) || 'N/A'}mm
                </div>
                <div className="text-gray-400">RMSE</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-purple-400">
                  {model_info.performance_metrics?.skill_score?.toFixed(2) || 'N/A'}
                </div>
                <div className="text-gray-400">Skill Score</div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Export Button */}
      <div className="flex justify-end">
        <button
          onClick={onExport}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Export CSV
        </button>
      </div>

      {/* Disclaimer */}
      <div className="bg-yellow-500 bg-opacity-10 border border-yellow-500 border-opacity-30 p-4 rounded-lg">
        <h4 className="text-yellow-400 font-semibold mb-2">⚠️ Important Disclaimer</h4>
        <p className="text-sm text-yellow-300">
          This forecast is for educational and research purposes only. Do not use for safety-critical decisions. 
          Always consult official meteorological services for authoritative weather information.
        </p>
      </div>
    </div>
  );
};

export default ResultsDisplay;
