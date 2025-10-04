import React, { useEffect, useRef } from 'react';
import { MapContainer, TileLayer, Marker, Popup, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Fix for default markers in React Leaflet
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
});

// Component to handle map clicks
function MapClickHandler({ onLocationSelect }) {
  useMapEvents({
    click: (e) => {
      const { lat, lng } = e.latlng;
      onLocationSelect(lat, lng);
    },
  });
  return null;
}

// Component to handle search results
function SearchResultMarker({ position, onSelect }) {
  if (!position) return null;
  
  return (
    <Marker position={position}>
      <Popup>
        <div className="text-center">
          <p className="mb-2">Click to select this location</p>
          <button
            onClick={onSelect}
            className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
          >
            Select Location
          </button>
        </div>
      </Popup>
    </Marker>
  );
}

const LocationMap = ({ 
  selectedPosition, 
  onLocationSelect, 
  searchResult,
  onSearchResultSelect,
  className = "h-96 w-full rounded-lg overflow-hidden border border-slate-600"
}) => {
  const mapRef = useRef(null);

  // Fly to search result when it changes
  useEffect(() => {
    if (searchResult && mapRef.current) {
      mapRef.current.flyTo(searchResult, 10);
    }
  }, [searchResult]);

  // Fly to selected position
  useEffect(() => {
    if (selectedPosition && mapRef.current) {
      mapRef.current.flyTo(selectedPosition, 10);
    }
  }, [selectedPosition]);

  return (
    <div className={className}>
      <MapContainer
        ref={mapRef}
        center={[40.7128, -74.0060]} // Default to NYC
        zoom={3}
        style={{ height: '100%', width: '100%' }}
        className="z-0"
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        
        {/* Handle map clicks */}
        <MapClickHandler onLocationSelect={onLocationSelect} />
        
        {/* Show selected location */}
        {selectedPosition && (
          <Marker position={selectedPosition}>
            <Popup>
              <div className="text-center">
                <h3 className="font-semibold mb-1">Selected Location</h3>
                <p className="text-sm text-gray-600">
                  Lat: {selectedPosition[0].toFixed(4)}<br />
                  Lng: {selectedPosition[1].toFixed(4)}
                </p>
              </div>
            </Popup>
          </Marker>
        )}
        
        {/* Show search result */}
        {searchResult && searchResult !== selectedPosition && (
          <SearchResultMarker 
            position={searchResult} 
            onSelect={onSearchResultSelect}
          />
        )}
      </MapContainer>
    </div>
  );
};

export default LocationMap;