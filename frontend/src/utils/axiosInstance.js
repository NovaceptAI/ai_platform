// src/utils/axiosInstance.js
import axios from 'axios';
import config from '../config'; // adjust the path as needed

const instance = axios.create({
  baseURL: config.API_BASE_URL
});

// Attach the token to every request automatically
instance.interceptors.request.use(
  config => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  error => Promise.reject(error)
);

export default instance;