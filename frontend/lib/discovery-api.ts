import apiClient from './api-client';
import { DiscoveryRequest, DiscoveryResponse, DrugCandidate } from '@/types';

export interface AnalyzeCandidateResponse {
  ai_analysis: string | null;
  success: boolean;
  message: string;
}

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
   * Generate AI analysis for a single drug candidate on-demand
   * @param candidate - The drug candidate to analyze
   * @returns Promise with AI analysis response
   */
  static async analyzeCandidate(candidate: DrugCandidate): Promise<AnalyzeCandidateResponse> {
    const request = {
      molecule: candidate.molecule,
      target: candidate.target,
      properties: candidate.properties,
      toxicity: candidate.toxicity,
    };

    const response = await apiClient.post<AnalyzeCandidateResponse>('/api/analyze-candidate', request);
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
