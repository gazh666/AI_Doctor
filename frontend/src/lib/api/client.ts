import axios, { AxiosInstance, InternalAxiosRequestConfig, AxiosResponse } from 'axios';
import { getApiBaseUrl } from './base-url';

/**
 * Modern Axios Client (2026 Standard)
 * Configured for Next.js 15+ and FastAPI backend synchronization.
 */
const apiClient: AxiosInstance = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
  // Increased timeout to 90s for heavy AI/Medical Image processing
  timeout: 90000, 
});

// Request Interceptor: Attach Clinical Authentication
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (config.data instanceof FormData && config.headers) {
      delete (config.headers as any)['Content-Type'];
      delete (config.headers as any)['content-type'];
    }

    // Synchronized with the key used in your project's security utilities
    const token = localStorage.getItem('access_token');
    
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor: Global Error & Session Management
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error) => {
    const status = error.response?.status;

    // Handle Session Expiry (401 Unauthorized)
    if (status === 401) {
      console.warn('Session expired or unauthorized. Redirecting to login...');
      localStorage.removeItem('access_token');
      if (typeof document !== 'undefined') {
        document.cookie = 'rural_ai_auth=; Path=/; Max-Age=0; SameSite=Lax';
      }
      
      // Prevent redirect loop if already on login page
      if (typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
        window.location.href = '/login';
      }
    }

    // Handle Forbidden (403) - e.g., non-admin accessing admin routes
    if (status === 403) {
      console.error('Permission denied: Insufficient privileges.');
    }

    // Centralized logging for clinical debugging
    const errorMessage = error.response?.data?.detail || error.message;
    console.error(`[API Error ${status || 'Network'}]:`, errorMessage);

    return Promise.reject(error);
  }
);

export default apiClient;
