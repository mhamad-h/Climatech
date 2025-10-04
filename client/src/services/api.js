import axios from 'axios';

// Get API base URL from environment or default  
// Use localhost since we're running in the same Codespace environment
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Axios instance configured for backend API
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.baseURL}${config.url}`);
    console.log('API Base URL:', API_BASE_URL);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Response Error:', error);
    
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.error || error.response.data?.detail || 'Server error';
      throw new Error(message);
    } else if (error.request) {
      // Network error
      throw new Error('Network error - please check your connection');
    } else {
      // Other error
      throw new Error(error.message || 'An unexpected error occurred');
    }
  }
);

/**
 * Get precipitation forecast for a location and time period
 * @param {Object} params - Forecast parameters
 * @param {number} params.latitude - Latitude in decimal degrees
 * @param {number} params.longitude - Longitude in decimal degrees  
 * @param {string} params.start_datetime_utc - Start datetime in ISO format
 * @param {number} params.horizon_hours - Forecast horizon in hours
 * @returns {Promise<Object>} Forecast response
 */
export async function getForecast(params) {
  const response = await api.post('/forecast', params);
  console.log('Forecast response:', response.data);
  return response.data;
}

/**
 * Get model information
 * @returns {Promise<Object>} Model info
 */
export async function getModelInfo() {
  const response = await api.get('/models/info');
  return response.data;
}

/**
 * Get data sources information
 * @returns {Promise<Object>} Data sources info
 */
export async function getDataSources() {
  const response = await api.get('/data/sources');
  return response.data;
}

/**
 * Check API health
 * @returns {Promise<Object>} Health status
 */
export async function checkHealth() {
  const response = await api.get('/health');
  return response.data;
}

// Legacy function for backward compatibility
export const getRainPrediction = getForecast;
