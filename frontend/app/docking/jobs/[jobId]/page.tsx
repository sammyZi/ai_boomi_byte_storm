'use client';

import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import DockingJobTracker from '@/components/DockingJobTracker';

export default function DockingJobPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;

  const handleComplete = (completedJobId: string) => {
    // Optionally auto-redirect to results after a short delay
    // setTimeout(() => router.push(`/docking/results/${completedJobId}`), 2000);
  };

  const handleCancel = (cancelledJobId: string) => {
    // Job was cancelled, could show a notification or redirect
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50 to-indigo-50 pt-24 pb-12">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Back Button */}
        <button
          onClick={() => router.back()}
          className="flex items-center gap-2 text-gray-600 hover:text-gray-900 mb-6 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm font-medium">Back</span>
        </button>

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
            Docking simulations typically take 5-15 minutes depending on molecule complexity.
          </p>
          <p className="mt-1">
            You can close this page and return later - your job will continue running.
          </p>
        </div>
      </div>
    </div>
  );
}
