import axios from 'axios';
import { apiClient } from '@/lib/api-client';

// Mock axios
jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should create axios instance with correct config', () => {
    expect(mockedAxios.create).toHaveBeenCalled();
  });

  it('should handle successful requests', async () => {
    const mockData = { message: 'success' };
    const mockResponse = { data: mockData };

    mockedAxios.create.mockReturnValue({
      get: jest.fn().mockResolvedValue(mockResponse),
      interceptors: {
        request: { use: jest.fn() },
        response: { use: jest.fn() },
      },
    } as any);

    const client = apiClient.getClient();
    const response = await client.get('/test');

    expect(response.data).toEqual(mockData);
  });

  it('should handle network errors', async () => {
    const mockError = {
      code: 'ERR_NETWORK',
      message: 'Network Error',
      request: {},
    };

    mockedAxios.create.mockReturnValue({
      get: jest.fn().mockRejectedValue(mockError),
      interceptors: {
        request: { use: jest.fn() },
        response: { use: jest.fn() },
      },
    } as any);

    const client = apiClient.getClient();

    await expect(client.get('/test')).rejects.toMatchObject({
      error_code: expect.any(String),
      message: expect.any(String),
    });
  });

  it('should handle server errors', async () => {
    const mockError = {
      response: {
        status: 500,
        data: {
          error_code: 'SERVER_ERROR',
          message: 'Internal server error',
        },
      },
    };

    mockedAxios.create.mockReturnValue({
      get: jest.fn().mockRejectedValue(mockError),
      interceptors: {
        request: { use: jest.fn() },
        response: { use: jest.fn() },
      },
    } as any);

    const client = apiClient.getClient();

    await expect(client.get('/test')).rejects.toMatchObject({
      error_code: 'SERVER_ERROR',
      message: 'Internal server error',
    });
  });
});
