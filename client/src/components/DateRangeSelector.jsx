import React from 'react';

const DateRangeSelector = ({ startDate, forecastDays, onDateRangeChange }) => {
  const handleStartDateChange = (e) => {
    const newStartDate = e.target.value;
    onDateRangeChange({
      startDate: newStartDate,
      forecastDays: forecastDays
    });
  };

  const handleForecastDaysChange = (e) => {
    const newForecastDays = parseInt(e.target.value);
    onDateRangeChange({
      startDate: startDate,
      forecastDays: newForecastDays
    });
  };

  // Get min date (today) and max date (6 months from now)
  const today = new Date().toISOString().split('T')[0];
  const maxDate = new Date();
  maxDate.setMonth(maxDate.getMonth() + 6);
  const maxDateString = maxDate.toISOString().split('T')[0];

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Start Date
        </label>
        <input
          type="date"
          value={startDate}
          onChange={handleStartDateChange}
          min={today}
          max={maxDateString}
          className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
        />
        <p className="text-xs text-gray-500 mt-1">
          Select forecast start date (today to 6 months ahead)
        </p>
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Forecast Length: {forecastDays} days
        </label>
        <input
          type="range"
          min="1"
          max="180"
          value={forecastDays}
          onChange={handleForecastDaysChange}
          className="w-full h-2 bg-slate-600 rounded-lg appearance-none cursor-pointer slider"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>1 day</span>
          <span>30 days</span>
          <span>90 days</span>
          <span>180 days</span>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Extended forecasts use climatology methods. Accuracy decreases beyond 30 days.
        </p>
      </div>

      <div className="bg-slate-700 p-3 rounded-lg">
        <div className="text-sm text-gray-300">
          <div className="flex justify-between">
            <span>Period:</span>
            <span className="font-medium text-white">
              {forecastDays <= 7 ? 'Short-term' :
               forecastDays <= 30 ? 'Medium-term' :
               forecastDays <= 90 ? 'Extended' : 'Long-range'}
            </span>
          </div>
          <div className="flex justify-between mt-1">
            <span>Method:</span>
            <span className="font-medium text-white">
              {forecastDays <= 7 ? 'Persistence + Analog' :
               forecastDays <= 30 ? 'Climatology + Trends' :
               'Climate Normals'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DateRangeSelector;