import axios from 'axios';

// Get API base URL from environment or default  
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (import.meta.env.MODE === 'production' ? '/api' : 'http://192.168.164.97:8000/api');

// Axios instance configured for backend API
export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // Increased timeout for climatology calculations
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
 * Get extended climate forecast (up to 6 months)
 * @param {Object} params - Forecast parameters
 * @param {number} params.lat - Latitude in decimal degrees
 * @param {number} params.lng - Longitude in decimal degrees  
 * @param {string} params.start_date - Start date in YYYY-MM-DD format
 * @param {number} params.forecast_days - Number of days to forecast (1-180)
 * @param {Array} params.parameters - Parameters to include in forecast
 * @returns {Promise<Object>} Extended forecast response
 */
export async function getExtendedForecast(params) {
  const requestBody = {
    latitude: params.lat,
    longitude: params.lng,
    start_date: params.start_date,
    forecast_days: params.forecast_days,
    include_daily: true,
    include_monthly: true,
    include_climate_context: true,
    include_uncertainty: true
  };
  const response = await api.post('/forecast/extended', requestBody);
  console.log('Extended forecast response:', response.data);
  return response.data;
}

/**
 * Get quick forecast (1-30 days)
 * @param {Object} params - Forecast parameters
 * @param {number} params.lat - Latitude in decimal degrees
 * @param {number} params.lng - Longitude in decimal degrees  
 * @param {number} params.days_ahead - Days ahead to forecast (1-30)
 * @returns {Promise<Object>} Quick forecast response
 */
export async function getQuickForecast(params) {
  const requestBody = {
    latitude: params.lat,
    longitude: params.lng,
    days_ahead: params.days_ahead || 7
  };
  const response = await api.post('/forecast/quick', requestBody);
  console.log('Quick forecast response:', response.data);
  return response.data;
}

/**
 * Get historical weather data for a location
 * @param {Object} params - Parameters object
 * @param {number} params.lat - Latitude in decimal degrees
 * @param {number} params.lng - Longitude in decimal degrees
 * @param {number} params.years - Years of data (default: 10)
 * @returns {Promise<Object>} Historical data response
 */
export async function getHistoricalData(params) {
  const queryParams = new URLSearchParams();
  if (params.years) queryParams.append('years', params.years);
  
  const response = await api.get(`/historical/${params.lat}/${params.lng}?${queryParams}`);
  console.log('Historical data response:', response.data);
  return response.data;
}

/**
 * Get climate normal values for a location
 * @param {Object} params - Parameters object
 * @param {number} params.lat - Latitude in decimal degrees
 * @param {number} params.lng - Longitude in decimal degrees
 * @returns {Promise<Object>} Climate normal response
 */
export async function getClimateNormal(params) {
  const requestBody = {
    latitude: params.lat,
    longitude: params.lng,
    years_of_data: 30
  };
  const response = await api.post(`/climate-normal/${params.lat}/${params.lng}`, requestBody);
  console.log('Climate normal response:', response.data);
  return response.data;
}

/**
 * Get monthly weather outlook
 * @param {Object} params - Parameters object
 * @param {number} params.lat - Latitude in decimal degrees
 * @param {number} params.lng - Longitude in decimal degrees
 * @param {string} params.start_date - Start date for outlook
 * @param {number} params.months - Number of months (default: 6)
 * @returns {Promise<Object>} Monthly outlook response
 */
export async function getMonthlyOutlook(params) {
  const queryParams = new URLSearchParams();
  if (params.start_date) queryParams.append('start_date', params.start_date);
  if (params.months) queryParams.append('months', params.months);
  
  const response = await api.get(`/forecast/monthly-outlook/${params.lat}/${params.lng}?${queryParams}`);
  console.log('Monthly outlook response:', response.data);
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
export const getForecast = getQuickForecast;
export const getRainPrediction = getQuickForecast;
