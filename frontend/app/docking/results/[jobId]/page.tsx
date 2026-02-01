'use client';

import { useParams, useRouter } from 'next/navigation';
import { ArrowLeft, Atom } from 'lucide-react';
import DockingResultsViewer from '@/components/DockingResultsViewer';

export default function DockingResultsPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.jobId as string;

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
          
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg">
              <Atom className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Docking Results</h1>
              <p className="text-gray-600">
                View molecular docking analysis and binding poses
              </p>
            </div>
          </div>
        </div>

        {/* Results Viewer */}
        <DockingResultsViewer jobId={jobId} />

        {/* Help Text */}
        <div className="mt-6 text-sm text-gray-500 bg-white/50 rounded-lg px-4 py-3">
          <p>
            <strong>Tip:</strong> Use the pose selector to switch between different binding conformations.
            Lower binding affinity values (more negative) indicate stronger binding.
            Toggle interactions to see hydrogen bonds and hydrophobic contacts.
          </p>
        </div>
      </div>
    </div>
  );
}
