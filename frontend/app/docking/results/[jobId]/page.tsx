'use client';

import { useParams } from 'next/navigation';
import { Atom } from 'lucide-react';
import IndustryDockingViewer from '@/components/IndustryDockingViewer';
import CompactNav from '@/components/CompactNav';

export default function DockingResultsPage() {
  const params = useParams();
  const jobId = params.jobId as string;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-blue-50/30">
      <CompactNav title="Docking Results" />
      
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Results Viewer */}
        <IndustryDockingViewer jobId={jobId} />

        {/* Help Text */}
        <div className="mt-6 text-sm text-gray-500 bg-white/50 rounded-lg px-4 py-3">
          <p>
            <strong>Tip:</strong> Click on any pose card to view it in 3D. 
            Use the view controls to switch between full complex, binding site, and ligand focus.
            Lower binding affinity values (more negative) indicate stronger binding.
          </p>
        </div>
      </div>
    </div>
  );
}
