import React, { useState, useEffect } from 'react';

const EventDatePicker = ({ 
  startDate, 
  endDate, 
  onDateChange,
  className = ""
}) => {
  const [startDateInput, setStartDateInput] = useState('');
  const [horizonHours, setHorizonHours] = useState(168); // Default 7 days
  const [errors, setErrors] = useState({});

  // Initialize input values
  useEffect(() => {
    if (startDate) {
      const dateStr = startDate.toISOString().slice(0, 16);
      setStartDateInput(dateStr);
    }
  }, [startDate]);

  const validateDates = (start, horizon) => {
    const errors = {};
    const now = new Date();
    const minDate = new Date(now.getTime() + 60 * 60 * 1000); // At least 1 hour from now
    const maxDate = new Date(now.getTime() + 30 * 24 * 60 * 60 * 1000); // Max 30 days ahead

    if (start && start < minDate) {
      errors.startDate = 'Start date must be at least 1 hour in the future';
    }

    if (start && start > maxDate) {
      errors.startDate = 'Start date cannot be more than 30 days in the future';
    }

    if (horizon < 1) {
      errors.horizon = 'Forecast horizon must be at least 1 hour';
    }

    if (horizon > 720) {
      errors.horizon = 'Forecast horizon cannot exceed 30 days (720 hours)';
    }

    return errors;
  };

  const handleStartDateChange = (e) => {
    const value = e.target.value;
    setStartDateInput(value);
    
    if (value) {
      const date = new Date(value);
      const validationErrors = validateDates(date, horizonHours);
      setErrors(validationErrors);
      
      if (!validationErrors.startDate) {
        const endDate = new Date(date.getTime() + horizonHours * 60 * 60 * 1000);
        onDateChange({ 
          startDate: date, 
          endDate: endDate,
          horizonHours 
        });
      }
    }
  };

  const handleHorizonChange = (e) => {
    const hours = parseInt(e.target.value);
    setHorizonHours(hours);
    
    if (startDate) {
      const newEndDate = new Date(startDate.getTime() + hours * 60 * 60 * 1000);
      
      const validationErrors = validateDates(startDate, hours);
      setErrors(validationErrors);
      
      if (!validationErrors.horizon) {
        onDateChange({ startDate, endDate: newEndDate, horizonHours: hours });
      }
    }
  };

  const quickSelectOptions = [
    { label: '6 hours', hours: 6 },
    { label: '24 hours', hours: 24 },
    { label: '3 days', hours: 72 },
    { label: '7 days', hours: 168 },
    { label: '14 days', hours: 336 },
    { label: '30 days', hours: 720 }
  ];

  const formatDateTime = (date) => {
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true
    });
  };

  return (
    <div className={`space-y-4 ${className}`}>
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Event Start Date & Time
        </label>
        <input
          type="datetime-local"
          value={startDateInput}
          onChange={handleStartDateChange}
          min={new Date().toISOString().slice(0, 16)}
          max={new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString().slice(0, 16)}
          className="w-full rounded bg-slate-800 border border-slate-600 px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        {errors.startDate && (
          <p className="mt-1 text-sm text-red-400">{errors.startDate}</p>
        )}
      </div>

      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Forecast Duration
        </label>
        
        {/* Quick select buttons */}
        <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-3">
          {quickSelectOptions.map(({ label, hours }) => (
            <button
              key={hours}
              type="button"
              onClick={() => handleHorizonChange({ target: { value: hours } })}
              className={`px-2 py-1 text-xs rounded transition ${
                horizonHours === hours
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-gray-300 hover:bg-slate-600'
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Custom hours input */}
        <div className="flex gap-2 items-center">
          <input
            type="number"
            min="1"
            max="720"
            value={horizonHours}
            onChange={handleHorizonChange}
            className="flex-1 rounded bg-slate-800 border border-slate-600 px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <span className="text-gray-300 text-sm">hours</span>
        </div>
        
        {errors.horizon && (
          <p className="mt-1 text-sm text-red-400">{errors.horizon}</p>
        )}
      </div>

      {/* Computed end date display */}
      {startDate && horizonHours && (
        <div className="p-3 bg-slate-700 rounded border border-slate-600">
          <h4 className="text-sm font-medium text-gray-300 mb-1">Forecast Period</h4>
          <p className="text-sm text-gray-400">
            From: {formatDateTime(startDate)}
          </p>
          <p className="text-sm text-gray-400">
            To: {formatDateTime(new Date(startDate.getTime() + horizonHours * 60 * 60 * 1000))}
          </p>
          <p className="text-sm text-blue-400 mt-1">
            Duration: {horizonHours} hours ({Math.floor(horizonHours / 24)} days, {horizonHours % 24} hours)
          </p>
        </div>
      )}

      <div className="text-xs text-gray-500 bg-slate-800 p-3 rounded border border-slate-700">
        <strong>Note:</strong> Forecasts are available up to 30 days (720 hours) in advance. 
        Longer forecasts have higher uncertainty.
      </div>
    </div>
  );
};

export default EventDatePicker;
