import {
  DockingSubmitRequest,
  DockingSubmitResponse,
  DockingJobStatusResponse,
  DockingJobResult,
} from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Job history filter options
export interface DockingJobHistoryFilter {
  status?: string;
  start_date?: string;
  end_date?: string;
  target_id?: string;
  candidate_id?: string;
  page?: number;
  page_size?: number;
}

// Job history item
export interface DockingJobHistoryItem {
  job_id: string;
  candidate_id: string;
  candidate_name?: string;
  target_uniprot_id: string;
  target_name?: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';
  best_affinity?: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

// Paginated job history response
export interface DockingJobHistoryResponse {
  jobs: DockingJobHistoryItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

/**
 * Docking API client for submitting jobs and tracking their status.
 */
export const dockingApi = {
  /**
   * Submit docking jobs for drug candidates.
   */
  async submitDockingJobs(request: DockingSubmitRequest): Promise<DockingSubmitResponse> {
    const response = await fetch(`${API_BASE_URL}/api/docking/submit`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new DockingApiError(
        errorData.detail?.message || 'Failed to submit docking jobs',
        errorData.detail?.error_code || 'SUBMISSION_FAILED',
        response.status
      );
    }

    return response.json();
  },

  /**
   * Get the status of a docking job.
   */
  async getJobStatus(jobId: string): Promise<DockingJobStatusResponse> {
    const response = await fetch(`${API_BASE_URL}/api/docking/status/${jobId}`);

    if (!response.ok) {
      const errorData = await response.json();
      throw new DockingApiError(
        errorData.detail?.message || 'Failed to get job status',
        errorData.detail?.error_code || 'STATUS_FAILED',
        response.status
      );
    }

    // Transform backend response to frontend format
    const data = await response.json();
    const job = data.job;
    
    return {
      job_id: job.id,
      status: job.status,
      progress_percent: job.status === 'completed' ? 100 : 
                        job.status === 'running' ? 50 : 
                        job.status === 'failed' ? 100 : 0,
      current_step: job.status === 'queued' ? 'Waiting in queue' :
                    job.status === 'running' ? 'Running docking simulation' :
                    job.status === 'completed' ? 'Docking complete' :
                    job.status === 'failed' ? 'Docking failed' : undefined,
      estimated_time_remaining_seconds: job.status === 'queued' ? 300 : 
                                         job.status === 'running' ? 150 : undefined,
      queue_position: data.queue_position,
      error_message: job.error_message,
      created_at: job.created_at,
      started_at: job.started_at,
      completed_at: job.completed_at,
    };
  },

  /**
   * Get the results of a completed docking job.
   */
  async getJobResults(jobId: string): Promise<DockingJobResult> {
    const response = await fetch(`${API_BASE_URL}/api/docking/jobs/${jobId}/results`);

    if (!response.ok) {
      const errorData = await response.json();
      throw new DockingApiError(
        errorData.detail?.message || 'Failed to get job results',
        errorData.detail?.error_code || 'RESULTS_FAILED',
        response.status
      );
    }

    return response.json();
  },

  /**
   * Cancel a docking job.
   */
  async cancelJob(jobId: string): Promise<{ job_id: string; status: string; message: string }> {
    const response = await fetch(`${API_BASE_URL}/api/docking/jobs/${jobId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new DockingApiError(
        errorData.detail?.message || 'Failed to cancel job',
        errorData.detail?.error_code || 'CANCEL_FAILED',
        response.status
      );
    }

    return response.json();
  },

  /**
   * Get job history with optional filters.
   */
  async getJobHistory(filters?: DockingJobHistoryFilter): Promise<DockingJobHistoryResponse> {
    const params = new URLSearchParams();
    
    if (filters?.status) params.append('status', filters.status);
    if (filters?.start_date) params.append('start_date', filters.start_date);
    if (filters?.end_date) params.append('end_date', filters.end_date);
    if (filters?.target_id) params.append('target_id', filters.target_id);
    if (filters?.candidate_id) params.append('candidate_id', filters.candidate_id);
    if (filters?.page) params.append('page', filters.page.toString());
    if (filters?.page_size) params.append('page_size', filters.page_size.toString());

    const url = `${API_BASE_URL}/api/docking/jobs${params.toString() ? '?' + params.toString() : ''}`;
    const response = await fetch(url);

    if (!response.ok) {
      const errorData = await response.json();
      throw new DockingApiError(
        errorData.detail?.message || 'Failed to get job history',
        errorData.detail?.error_code || 'HISTORY_FAILED',
        response.status
      );
    }

    return response.json();
  },

  /**
   * Re-run a failed docking job.
   */
  async rerunJob(jobId: string): Promise<DockingSubmitResponse> {
    const response = await fetch(`${API_BASE_URL}/api/docking/jobs/${jobId}/rerun`, {
      method: 'POST',
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new DockingApiError(
        errorData.detail?.message || 'Failed to re-run job',
        errorData.detail?.error_code || 'RERUN_FAILED',
        response.status
      );
    }

    return response.json();
  },
};

/**
 * Custom error class for docking API errors.
 */
export class DockingApiError extends Error {
  constructor(
    message: string,
    public errorCode: string,
    public statusCode: number
  ) {
    super(message);
    this.name = 'DockingApiError';
  }
}
