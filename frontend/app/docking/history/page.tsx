'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import {
  History,
  Filter,
  ChevronLeft,
  ChevronRight,
  Eye,
  RefreshCw,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  Loader2,
  Calendar,
  Target,
  ArrowLeft,
  Atom,
} from 'lucide-react';
import { dockingApi, DockingJobHistoryItem, DockingJobHistoryFilter, DockingApiError } from '@/lib/docking-api';

// Status configurations
const STATUS_CONFIG = {
  queued: {
    label: 'Queued',
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    icon: Clock,
  },
  running: {
    label: 'Running',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-100',
    icon: Loader2,
  },
  completed: {
    label: 'Completed',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-100',
    icon: CheckCircle,
  },
  failed: {
    label: 'Failed',
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    icon: XCircle,
  },
  cancelled: {
    label: 'Cancelled',
    color: 'text-gray-600',
    bgColor: 'bg-gray-100',
    icon: AlertCircle,
  },
};

export default function DockingJobHistoryPage() {
  const router = useRouter();
  
  // State
  const [jobs, setJobs] = useState<DockingJobHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalJobs, setTotalJobs] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  
  // Filters
  const [filters, setFilters] = useState<DockingJobHistoryFilter>({
    page: 1,
    page_size: 10,
  });
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [dateRange, setDateRange] = useState<{ start: string; end: string }>({
    start: '',
    end: '',
  });
  const [showFilters, setShowFilters] = useState(false);
  
  // Rerun state
  const [rerunningJob, setRerunningJob] = useState<string | null>(null);

  // Fetch jobs
  const fetchJobs = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const activeFilters: DockingJobHistoryFilter = {
        ...filters,
        status: statusFilter || undefined,
        start_date: dateRange.start || undefined,
        end_date: dateRange.end || undefined,
      };

      const response = await dockingApi.getJobHistory(activeFilters);
      setJobs(response.jobs);
      setTotalJobs(response.total);
      setTotalPages(response.total_pages);
    } catch (err) {
      const message = err instanceof DockingApiError
        ? err.message
        : 'Failed to load job history';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [filters, statusFilter, dateRange]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // Handle pagination
  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setFilters(prev => ({ ...prev, page: newPage }));
    }
  };

  // Handle filter changes
  const applyFilters = () => {
    setFilters(prev => ({ ...prev, page: 1 }));
  };

  const clearFilters = () => {
    setStatusFilter('');
    setDateRange({ start: '', end: '' });
    setFilters({ page: 1, page_size: 10 });
  };

  // Handle view results
  const handleViewResults = (jobId: string) => {
    router.push(`/docking/results/${jobId}`);
  };

  // Handle re-run job
  const handleRerun = async (jobId: string) => {
    setRerunningJob(jobId);
    try {
      const response = await dockingApi.rerunJob(jobId);
      // Navigate to the new job's tracking page
      if (response.job_id) {
        router.push(`/docking/jobs/${response.job_id}`);
      }
    } catch (err) {
      const message = err instanceof DockingApiError
        ? err.message
        : 'Failed to re-run job';
      setError(message);
    } finally {
      setRerunningJob(null);
    }
  };

  // Format date
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 text-gray-600 hover:text-gray-900 transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            <span className="text-sm font-medium">Back</span>
          </button>
          
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
                <History className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Docking Job History</h1>
                <p className="text-gray-600">
                  View and manage your molecular docking jobs
                </p>
              </div>
            </div>
            
            <button
              onClick={fetchJobs}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>
        </div>

        {/* Filters */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm mb-6 overflow-hidden">
          <div
            className="px-6 py-4 flex items-center justify-between cursor-pointer hover:bg-gray-50"
            onClick={() => setShowFilters(!showFilters)}
          >
            <div className="flex items-center gap-2">
              <Filter className="w-5 h-5 text-gray-500" />
              <span className="font-medium text-gray-900">Filters</span>
              {(statusFilter || dateRange.start || dateRange.end) && (
                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded-full">
                  Active
                </span>
              )}
            </div>
            <ChevronRight className={`w-5 h-5 text-gray-500 transition-transform ${showFilters ? 'rotate-90' : ''}`} />
          </div>
          
          {showFilters && (
            <div className="px-6 py-4 border-t border-gray-200 bg-gray-50">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {/* Status Filter */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">All Statuses</option>
                    <option value="queued">Queued</option>
                    <option value="running">Running</option>
                    <option value="completed">Completed</option>
                    <option value="failed">Failed</option>
                    <option value="cancelled">Cancelled</option>
                  </select>
                </div>

                {/* Date Range */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">From Date</label>
                  <input
                    type="date"
                    value={dateRange.start}
                    onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
                  <input
                    type="date"
                    value={dateRange.end}
                    onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>

                {/* Filter Actions */}
                <div className="flex items-end gap-2">
                  <button
                    onClick={applyFilters}
                    className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                  >
                    Apply
                  </button>
                  <button
                    onClick={clearFilters}
                    className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
                  >
                    Clear
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Job Table */}
        <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="w-8 h-8 text-blue-500 animate-spin" />
                <p className="text-gray-600">Loading jobs...</p>
              </div>
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center h-64">
              <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
              <p className="text-gray-900 font-medium mb-2">Failed to load jobs</p>
              <p className="text-gray-600 text-sm mb-4">{error}</p>
              <button
                onClick={fetchJobs}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Retry
              </button>
            </div>
          ) : jobs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64">
              <Atom className="w-12 h-12 text-gray-300 mb-4" />
              <p className="text-gray-900 font-medium mb-2">No docking jobs found</p>
              <p className="text-gray-600 text-sm">
                {statusFilter || dateRange.start || dateRange.end
                  ? 'Try adjusting your filters'
                  : 'Submit a docking job to get started'}
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b border-gray-200">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Job ID</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Candidate</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Target</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Status</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Best Affinity</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Created</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {jobs.map((job) => {
                      const statusConfig = STATUS_CONFIG[job.status];
                      const StatusIcon = statusConfig.icon;
                      
                      return (
                        <tr key={job.job_id} className="hover:bg-gray-50 transition-colors">
                          <td className="px-4 py-4">
                            <span className="font-mono text-sm text-gray-900">
                              {job.job_id.slice(0, 8)}...
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <div>
                              <p className="font-medium text-gray-900">
                                {job.candidate_name || job.candidate_id}
                              </p>
                              {job.candidate_name && (
                                <p className="text-xs text-gray-500 font-mono">{job.candidate_id}</p>
                              )}
                            </div>
                          </td>
                          <td className="px-4 py-4">
                            <div className="flex items-center gap-2">
                              <Target className="w-4 h-4 text-gray-400" />
                              <span className="text-sm text-gray-700">
                                {job.target_name || job.target_uniprot_id}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-4">
                            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${statusConfig.bgColor} ${statusConfig.color}`}>
                              <StatusIcon className={`w-3.5 h-3.5 ${job.status === 'running' ? 'animate-spin' : ''}`} />
                              {statusConfig.label}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            {job.best_affinity !== undefined ? (
                              <span className="font-mono font-medium text-gray-900">
                                {job.best_affinity.toFixed(2)} kcal/mol
                              </span>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                          </td>
                          <td className="px-4 py-4">
                            <div className="flex items-center gap-1.5 text-sm text-gray-600">
                              <Calendar className="w-4 h-4" />
                              {formatDate(job.created_at)}
                            </div>
                          </td>
                          <td className="px-4 py-4">
                            <div className="flex items-center gap-2">
                              {job.status === 'completed' && (
                                <button
                                  onClick={() => handleViewResults(job.job_id)}
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors text-sm font-medium"
                                >
                                  <Eye className="w-4 h-4" />
                                  View
                                </button>
                              )}
                              {job.status === 'failed' && (
                                <button
                                  onClick={() => handleRerun(job.job_id)}
                                  disabled={rerunningJob === job.job_id}
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-50 text-orange-700 rounded-lg hover:bg-orange-100 transition-colors text-sm font-medium disabled:opacity-50"
                                >
                                  {rerunningJob === job.job_id ? (
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  ) : (
                                    <RefreshCw className="w-4 h-4" />
                                  )}
                                  Re-run
                                </button>
                              )}
                              {(job.status === 'queued' || job.status === 'running') && (
                                <button
                                  onClick={() => router.push(`/docking/jobs/${job.job_id}`)}
                                  className="flex items-center gap-1.5 px-3 py-1.5 bg-indigo-50 text-indigo-700 rounded-lg hover:bg-indigo-100 transition-colors text-sm font-medium"
                                >
                                  <Eye className="w-4 h-4" />
                                  Track
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Pagination */}
              <div className="px-4 py-3 border-t border-gray-200 bg-gray-50 flex items-center justify-between">
                <p className="text-sm text-gray-600">
                  Showing {(filters.page! - 1) * filters.page_size! + 1} to{' '}
                  {Math.min(filters.page! * filters.page_size!, totalJobs)} of {totalJobs} jobs
                </p>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handlePageChange(filters.page! - 1)}
                    disabled={filters.page === 1}
                    className="p-2 rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="px-3 py-1 text-sm font-medium text-gray-700">
                    Page {filters.page} of {totalPages}
                  </span>
                  <button
                    onClick={() => handlePageChange(filters.page! + 1)}
                    disabled={filters.page === totalPages}
                    className="p-2 rounded-lg border border-gray-300 hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
