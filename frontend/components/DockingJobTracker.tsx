'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Ban,
  RefreshCw,
  ArrowRight,
} from 'lucide-react';
import { DockingJobStatusResponse, DockingJobStatus } from '@/types';
import { dockingApi, DockingApiError } from '@/lib/docking-api';

interface DockingJobTrackerProps {
  jobId: string;
  onComplete?: (jobId: string) => void;
  onCancel?: (jobId: string) => void;
}

const POLL_INTERVAL_MS = 5000; // 5 seconds

const STATUS_CONFIG: Record<
  DockingJobStatus,
  {
    icon: React.ComponentType<{ className?: string }>;
    color: string;
    bgColor: string;
    borderColor: string;
    label: string;
  }
> = {
  queued: {
    icon: Clock,
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    borderColor: 'border-amber-200',
    label: 'Queued',
  },
  running: {
    icon: Loader2,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    label: 'Running',
  },
  completed: {
    icon: CheckCircle2,
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    borderColor: 'border-emerald-200',
    label: 'Completed',
  },
  failed: {
    icon: XCircle,
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    borderColor: 'border-red-200',
    label: 'Failed',
  },
  cancelled: {
    icon: Ban,
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    borderColor: 'border-gray-200',
    label: 'Cancelled',
  },
};

function formatTime(seconds: number): string {
  if (seconds < 60) {
    return `${Math.round(seconds)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.round(seconds % 60);
  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

export default function DockingJobTracker({
  jobId,
  onComplete,
  onCancel,
}: DockingJobTrackerProps) {
  const router = useRouter();
  const [status, setStatus] = useState<DockingJobStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCancelling, setIsCancelling] = useState(false);

  const fetchStatus = useCallback(async () => {
    try {
      const response = await dockingApi.getJobStatus(jobId);
      setStatus(response);
      setError(null);

      // Handle completion
      if (response.status === 'completed') {
        onComplete?.(jobId);
      }

      return response;
    } catch (err) {
      if (err instanceof DockingApiError) {
        setError(err.message);
      } else {
        setError('Failed to fetch job status');
      }
      return null;
    } finally {
      setIsLoading(false);
    }
  }, [jobId, onComplete]);

  // Initial fetch and polling
  useEffect(() => {
    fetchStatus();

    const interval = setInterval(async () => {
      const response = await fetchStatus();
      
      // Stop polling if job is in terminal state
      if (
        response &&
        (response.status === 'completed' ||
          response.status === 'failed' ||
          response.status === 'cancelled')
      ) {
        clearInterval(interval);
      }
    }, POLL_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [fetchStatus]);

  const handleCancel = async () => {
    if (!status || isCancelling) return;

    setIsCancelling(true);
    try {
      await dockingApi.cancelJob(jobId);
      await fetchStatus();
      onCancel?.(jobId);
    } catch (err) {
      if (err instanceof DockingApiError) {
        setError(err.message);
      } else {
        setError('Failed to cancel job');
      }
    } finally {
      setIsCancelling(false);
    }
  };

  const handleViewResults = () => {
    router.push(`/docking/results/${jobId}`);
  };

  const handleRetry = () => {
    setError(null);
    setIsLoading(true);
    fetchStatus();
  };

  // Loading state
  if (isLoading && !status) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 p-8 shadow-sm">
        <div className="flex flex-col items-center justify-center gap-4">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin" />
          <p className="text-gray-600 font-medium">Loading job status...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error && !status) {
    return (
      <div className="bg-white rounded-2xl border border-red-200 p-8 shadow-sm">
        <div className="flex flex-col items-center justify-center gap-4">
          <AlertTriangle className="w-10 h-10 text-red-500" />
          <p className="text-red-700 font-medium">{error}</p>
          <button
            onClick={handleRetry}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!status) return null;

  const statusConfig = STATUS_CONFIG[status.status];
  const StatusIcon = statusConfig.icon;
  const canCancel = status.status === 'queued' || status.status === 'running';
  const isTerminal =
    status.status === 'completed' ||
    status.status === 'failed' ||
    status.status === 'cancelled';

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className={`${statusConfig.bgColor} ${statusConfig.borderColor} border-b px-6 py-4`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <StatusIcon
              className={`w-6 h-6 ${statusConfig.color} ${
                status.status === 'running' ? 'animate-spin' : ''
              }`}
            />
            <div>
              <h3 className={`text-lg font-bold ${statusConfig.color}`}>
                {statusConfig.label}
              </h3>
              <p className="text-sm text-gray-600 font-mono">Job ID: {jobId}</p>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-3">
            {canCancel && (
              <button
                onClick={handleCancel}
                disabled={isCancelling}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 rounded-lg transition-colors disabled:opacity-50"
              >
                {isCancelling ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Ban className="w-4 h-4" />
                )}
                Cancel
              </button>
            )}

            {status.status === 'completed' && (
              <button
                onClick={handleViewResults}
                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 rounded-lg shadow-md transition-all"
              >
                View Results
                <ArrowRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-6 space-y-6">
        {/* Progress Bar */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Progress</span>
            <span className="text-sm font-bold text-gray-900">
              {status.progress_percent}%
            </span>
          </div>
          <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-500 ease-out rounded-full ${
                status.status === 'completed'
                  ? 'bg-gradient-to-r from-emerald-400 to-emerald-500'
                  : status.status === 'failed'
                  ? 'bg-gradient-to-r from-red-400 to-red-500'
                  : 'bg-gradient-to-r from-blue-400 to-indigo-500'
              }`}
              style={{ width: `${status.progress_percent}%` }}
            />
          </div>
        </div>

        {/* Current Step */}
        {status.current_step && (
          <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-xl">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            <p className="text-sm text-gray-700">{status.current_step}</p>
          </div>
        )}

        {/* Time Information */}
        <div className="grid grid-cols-2 gap-4">
          {status.queue_position !== undefined && status.queue_position > 0 && (
            <div className="p-4 bg-amber-50 rounded-xl border border-amber-100">
              <p className="text-xs text-amber-600 uppercase tracking-wider font-semibold mb-1">
                Queue Position
              </p>
              <p className="text-2xl font-bold text-amber-700">
                #{status.queue_position}
              </p>
            </div>
          )}

          {status.estimated_time_remaining_seconds !== undefined &&
            status.estimated_time_remaining_seconds > 0 && (
              <div className="p-4 bg-blue-50 rounded-xl border border-blue-100">
                <p className="text-xs text-blue-600 uppercase tracking-wider font-semibold mb-1">
                  Est. Time Remaining
                </p>
                <p className="text-2xl font-bold text-blue-700">
                  {formatTime(status.estimated_time_remaining_seconds)}
                </p>
              </div>
            )}
        </div>

        {/* Error Message */}
        {status.error_message && (
          <div className="flex items-start gap-3 p-4 bg-red-50 rounded-xl border border-red-200">
            <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-red-800">Error</p>
              <p className="text-sm text-red-700 mt-1">{status.error_message}</p>
            </div>
          </div>
        )}

        {/* Timestamps */}
        <div className="pt-4 border-t border-gray-100">
          <div className="grid grid-cols-3 gap-4 text-center text-sm">
            <div>
              <p className="text-gray-500 font-medium">Created</p>
              <p className="text-gray-900 mt-1">
                {new Date(status.created_at).toLocaleTimeString()}
              </p>
            </div>
            {status.started_at && (
              <div>
                <p className="text-gray-500 font-medium">Started</p>
                <p className="text-gray-900 mt-1">
                  {new Date(status.started_at).toLocaleTimeString()}
                </p>
              </div>
            )}
            {status.completed_at && (
              <div>
                <p className="text-gray-500 font-medium">Completed</p>
                <p className="text-gray-900 mt-1">
                  {new Date(status.completed_at).toLocaleTimeString()}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Polling indicator */}
        {!isTerminal && (
          <div className="flex items-center justify-center gap-2 text-xs text-gray-400">
            <RefreshCw className="w-3 h-3 animate-spin" />
            <span>Auto-refreshing every 5 seconds</span>
          </div>
        )}
      </div>
    </div>
  );
}
