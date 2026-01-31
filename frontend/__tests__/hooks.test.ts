import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useDiscovery } from '@/hooks/useDiscovery';
import { useExport } from '@/hooks/useExport';
import DiscoveryAPI from '@/lib/discovery-api';

// Mock the API
jest.mock('@/lib/discovery-api');
const mockedAPI = DiscoveryAPI as jest.Mocked<typeof DiscoveryAPI>;

// Create a wrapper for React Query
const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('useDiscovery hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should initialize with correct default state', () => {
    const { result } = renderHook(() => useDiscovery(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.isError).toBe(false);
    expect(result.current.data).toBeUndefined();
  });

  it('should handle successful search', async () => {
    const mockData = {
      query: 'test disease',
      timestamp: '2026-01-31T12:00:00Z',
      processing_time_seconds: 8.5,
      candidates: [],
      metadata: {
        targets_found: 5,
        molecules_analyzed: 100,
        api_version: '1.0.0',
      },
      warnings: [],
    };

    mockedAPI.discoverDrugs.mockResolvedValue(mockData);

    const { result } = renderHook(() => useDiscovery(), {
      wrapper: createWrapper(),
    });

    result.current.search('test disease');

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.data).toEqual(mockData);
  });

  it('should handle search errors', async () => {
    const mockError = {
      error_code: 'INVALID_INPUT',
      message: 'Invalid disease name',
      timestamp: '2026-01-31T12:00:00Z',
    };

    mockedAPI.discoverDrugs.mockRejectedValue(mockError);

    const { result } = renderHook(() => useDiscovery(), {
      wrapper: createWrapper(),
    });

    result.current.search('');

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });
  });
});

describe('useExport hook', () => {
  beforeEach(() => {
    // Mock DOM methods
    global.URL.createObjectURL = jest.fn(() => 'mock-url');
    global.URL.revokeObjectURL = jest.fn();
    document.body.appendChild = jest.fn();
    document.body.removeChild = jest.fn();
  });

  it('should export to JSON', () => {
    const { result } = renderHook(() => useExport());

    const mockData = {
      query: 'test',
      timestamp: '2026-01-31T12:00:00Z',
      processing_time_seconds: 8.5,
      candidates: [],
      metadata: {
        targets_found: 5,
        molecules_analyzed: 100,
        api_version: '1.0.0',
      },
      warnings: [],
    };

    result.current.exportToJSON(mockData);

    expect(global.URL.createObjectURL).toHaveBeenCalled();
    expect(result.current.isExporting).toBe(false);
    expect(result.current.error).toBeNull();
  });

  it('should export to CSV', () => {
    const { result } = renderHook(() => useExport());

    const mockData = {
      query: 'test',
      timestamp: '2026-01-31T12:00:00Z',
      processing_time_seconds: 8.5,
      candidates: [],
      metadata: {
        targets_found: 5,
        molecules_analyzed: 100,
        api_version: '1.0.0',
      },
      warnings: [],
    };

    result.current.exportToCSV(mockData);

    expect(global.URL.createObjectURL).toHaveBeenCalled();
    expect(result.current.isExporting).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
