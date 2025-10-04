import axios from 'axios';

// Axios instance configured for backend API base URL
export const api = axios.create({
  baseURL: 'http://127.0.0.1:8000/api', // FastAPI backend base
  timeout: 15000,
});

export async function getRainPrediction(data) {
  // TODO: Implement POST request to /predict-rain with the provided data.
  // Example:
  // const response = await api.post('/predict-rain', data);
  // return response.data;
  throw new Error('getRainPrediction not implemented yet');
}
