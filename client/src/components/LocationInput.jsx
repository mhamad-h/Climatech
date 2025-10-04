import React, { useState } from 'react';

const LocationInput = ({ 
  latitude, 
  longitude, 
  onLocationChange,
  onSearch,
  isSearching = false,
  searchError = null,
  className = ""
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [latInput, setLatInput] = useState(latitude || '');
  const [lngInput, setLngInput] = useState(longitude || '');

  const handleCoordinateChange = () => {
    const lat = parseFloat(latInput);
    const lng = parseFloat(lngInput);
    
    if (isValidCoordinate(lat, lng)) {
      onLocationChange(lat, lng);
    }
  };

  const handleSearch = (e) => {
    e.preventDefault();
    if (searchQuery.trim() && onSearch) {
      onSearch(searchQuery.trim());
    }
  };

  const isValidCoordinate = (lat, lng) => {
    return !isNaN(lat) && !isNaN(lng) && 
           lat >= -90 && lat <= 90 && 
           lng >= -180 && lng <= 180;
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Search by place name */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Search Location
        </label>
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search for a city, address, or landmark..."
            className="flex-1 rounded bg-slate-800 border border-slate-600 px-3 py-2 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={!searchQuery.trim() || isSearching}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {isSearching ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                Searching...
              </>
            ) : (
              'Search'
            )}
          </button>
        </form>
        {searchError && (
          <p className="mt-2 text-sm text-red-400">{searchError}</p>
        )}
      </div>

      {/* Manual coordinate input */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Or Enter Coordinates Manually
        </label>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              Latitude (-90 to 90)
            </label>
            <input
              type="number"
              step="any"
              min="-90"
              max="90"
              value={latInput}
              onChange={(e) => {
                setLatInput(e.target.value);
                if (e.target.value && lngInput) {
                  setTimeout(handleCoordinateChange, 100);
                }
              }}
              className="w-full rounded bg-slate-800 border border-slate-600 px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="40.7128"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">
              Longitude (-180 to 180)
            </label>
            <input
              type="number"
              step="any"
              min="-180"
              max="180"
              value={lngInput}
              onChange={(e) => {
                setLngInput(e.target.value);
                if (e.target.value && latInput) {
                  setTimeout(handleCoordinateChange, 100);
                }
              }}
              className="w-full rounded bg-slate-800 border border-slate-600 px-3 py-2 text-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="-74.0060"
            />
          </div>
        </div>
        
        {latitude && longitude && (
          <div className="mt-2 p-2 bg-slate-700 rounded text-sm text-gray-300">
            Selected: {latitude.toFixed(4)}, {longitude.toFixed(4)}
          </div>
        )}
      </div>

      <div className="text-xs text-gray-500 bg-slate-800 p-3 rounded border border-slate-700">
        <strong>Tip:</strong> Click on the map above to select a location, search for a place name, 
        or enter coordinates manually.
      </div>
    </div>
  );
};

export default LocationInput;
