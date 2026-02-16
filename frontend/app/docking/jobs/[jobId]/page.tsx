'use client';

import { useParams } from 'next/navigation';
import DockingJobTracker from '@/components/DockingJobTracker';
import CompactNav from '@/components/CompactNav';

export default function DockingJobPage() {
  const params = useParams();
  const jobId = params.jobId as string;

  const handleComplete = (completedJobId: string) => {
    // Optionally auto-redirect to results after a short delay
    // setTimeout(() => router.push(`/docking/results/${completedJobId}`), 2000);
  };

  const handleCancel = (cancelledJobId: string) => {
    // Job was cancelled, could show a notification or redirect
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50">
      <CompactNav title="Docking Job Status" />
      
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Page Title */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Docking Job Status</h1>
          <p className="text-gray-600 mt-2">
            Track the progress of your molecular docking simulation.
          </p>
        </div>

        {/* Job Tracker */}
        <DockingJobTracker
          jobId={jobId}
          onComplete={handleComplete}
          onCancel={handleCancel}
        />

        {/* Help Text */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>
            Docking simulations typically take 2-5 minutes depending on molecule complexity.
          </p>
          <p className="mt-1">
            You can close this page and return later - your job will continue running.
          </p>
        </div>
      </div>
    </div>
  );
}
