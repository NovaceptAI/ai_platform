// src/utils/axiosInstance.js
import axios from 'axios';
import config from '../config'; // adjust the path as needed
import { getAuthToken } from './auth';

const instance = axios.create({
  baseURL: config.API_BASE_URL
});

// Attach the token to every request automatically
instance.interceptors.request.use(
  config => {
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

export default instance;