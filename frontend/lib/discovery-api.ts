import apiClient from './api-client';
import { DiscoveryRequest, DiscoveryResponse } from '@/types';

export class DiscoveryAPI {
  /**
   * Discover drug candidates for a given disease
   * @param diseaseName - Name of the disease to search for
   * @returns Promise with discovery results
   */
  static async discoverDrugs(diseaseName: string): Promise<DiscoveryResponse> {
    const request: DiscoveryRequest = {
      disease_name: diseaseName,
    };

    const response = await apiClient.post<DiscoveryResponse>('/api/discover', request);
    return response.data;
  }

  /**
   * Health check endpoint
   * @returns Promise with health status
   */
  static async healthCheck(): Promise<{ status: string }> {
    const response = await apiClient.get<{ status: string }>('/health');
    return response.data;
  }
}

export default DiscoveryAPI;
