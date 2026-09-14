import axios from 'axios';

const request = axios.create({
  baseURL: import.meta.env.VITE_AJAX_BASE_URL,
  timeout: 30000,
  withCredentials: true,
});

request.interceptors.request.use(
  (config) => config,
  (error) => Promise.reject(error),
);

request.interceptors.response.use(
  (response) => response,
  (error) => Promise.reject(error),
);

export default request;
