import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import { ErrorResponse } from '@/types';

class APIClient {
  private client: AxiosInstance;
  private maxRetries: number = 3;
  private retryDelay: number = 1000;

  constructor() {
    const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

    this.client = axios.create({
      baseURL,
      timeout: 120000, // 2 minutes for long-running discovery requests
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        // Add any auth tokens or custom headers here if needed
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        return response;
      },
      async (error: AxiosError) => {
        const config = error.config as AxiosRequestConfig & { _retry?: number };

        // Handle retry logic for network errors
        if (
          error.code === 'ECONNABORTED' ||
          error.code === 'ERR_NETWORK' ||
          (error.response?.status && error.response.status >= 500)
        ) {
          config._retry = config._retry || 0;

          if (config._retry < this.maxRetries) {
            config._retry += 1;
            const delay = this.retryDelay * Math.pow(2, config._retry - 1);

            await new Promise((resolve) => setTimeout(resolve, delay));
            return this.client(config);
          }
        }

        return Promise.reject(this.handleError(error));
      }
    );
  }

  private handleError(error: AxiosError): ErrorResponse {
    if (error.response) {
      // Server responded with error
      const data = error.response.data as ErrorResponse | Record<string, unknown>;
      if (data && typeof data === 'object' && 'error_code' in data) {
        return data as ErrorResponse;
      }
      return {
        error_code: 'SERVER_ERROR',
        message: 'An error occurred on the server',
        timestamp: new Date().toISOString(),
      };
    } else if (error.request) {
      // Request made but no response
      return {
        error_code: 'NETWORK_ERROR',
        message: 'Unable to connect to the server. Please check your connection.',
        timestamp: new Date().toISOString(),
      };
    } else {
      // Something else happened
      return {
        error_code: 'CLIENT_ERROR',
        message: error.message || 'An unexpected error occurred',
        timestamp: new Date().toISOString(),
      };
    }
  }

  public getClient(): AxiosInstance {
    return this.client;
  }
}

// Export singleton instance
export const apiClient = new APIClient();
export default apiClient.getClient();
