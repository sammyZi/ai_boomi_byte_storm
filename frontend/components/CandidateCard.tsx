'use client';

import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { ArrowRight, Award, AlertTriangle, Activity, Dna } from 'lucide-react';
import { DrugCandidate } from '@/types';
import DockingSubmissionModal from './DockingSubmissionModal';

interface CandidateCardProps {
  candidate: DrugCandidate;
}

export default function CandidateCard({ candidate }: CandidateCardProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const query = searchParams.get('q');
  const [showDockingModal, setShowDockingModal] = useState(false);

  const handleViewDetails = () => {
    // Navigate to the details page with the query param so we can refetch context
    router.push(`/candidates/${candidate.molecule.chembl_id}?disease=${encodeURIComponent(query || '')}`);
  };

  const handleRunDocking = (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click navigation
    setShowDockingModal(true);
  };

  const handleDockingSuccess = (jobIds: string[]) => {
    setShowDockingModal(false);
    // Navigate to job tracking page with the first job ID
    if (jobIds.length > 0) {
      router.push(`/docking/jobs/${jobIds[0]}`);
    }
  };

  // Check if protein structure is available (has uniprot_id)
  const hasProteinStructure = !!candidate.target.uniprot_id;

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low':
        return 'bg-emerald-50 text-emerald-700 border-emerald-200';
      case 'medium':
        return 'bg-amber-50 text-amber-700 border-amber-200';
      case 'high':
        return 'bg-rose-50 text-rose-700 border-rose-200';
      default:
        return 'bg-slate-50 text-slate-700 border-slate-200';
    }
  };

  return (
    <div
      onClick={handleViewDetails}
      className="group relative bg-white border border-gray-200 rounded-2xl p-6 shadow-sm hover:shadow-xl hover:border-blue-300 transition-all duration-300 cursor-pointer overflow-hidden"
    >
      <div className="absolute top-0 right-0 p-4 opacity-0 group-hover:opacity-100 transition-opacity">
        <ArrowRight className="w-5 h-5 text-blue-500 -rotate-45 group-hover:rotate-0 transition-transform duration-300" />
      </div>

      <div className="flex items-start gap-5">
        {/* Rank Badge */}
        <div className="flex-shrink-0 flex flex-col items-center justify-center w-14 h-14 bg-gradient-to-br from-blue-600 to-indigo-600 text-white rounded-xl shadow-md group-hover:scale-110 transition-transform duration-300">
          <span className="text-xs font-medium opacity-80">Rank</span>
          <span className="text-xl font-bold">#{candidate.rank}</span>
        </div>

        <div className="flex-1 min-w-0">
          <h3 className="text-xl font-bold text-gray-900 mb-1 truncate group-hover:text-blue-600 transition-colors">
            {candidate.molecule.name}
          </h3>
          <p className="text-sm text-gray-500 font-mono mb-4">{candidate.molecule.chembl_id}</p>

          <div className="flex flex-wrap items-center gap-3">
            {/* Score Badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg text-sm font-semibold border border-blue-200">
              <Award className="w-4 h-4" />
              <span>Score: {candidate.composite_score.toFixed(2)}</span>
            </div>

            {/* Target Badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-50 text-purple-700 rounded-lg text-sm font-semibold border border-purple-200">
              <Activity className="w-4 h-4" />
              <span className="truncate max-w-[150px]">{candidate.target.gene_symbol}</span>
            </div>

            {/* Risk Badge */}
            <div
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-semibold border ${getRiskColor(
                candidate.toxicity.risk_level
              )}`}
            >
              <AlertTriangle className="w-4 h-4" />
              <span>{candidate.toxicity.risk_level.charAt(0).toUpperCase() + candidate.toxicity.risk_level.slice(1)} Risk</span>
            </div>

            {/* Run Docking Button - Only show if protein structure available */}
            {hasProteinStructure && (
              <button
                onClick={handleRunDocking}
                className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-lg text-sm font-semibold shadow-sm hover:shadow-md hover:from-emerald-600 hover:to-teal-600 transition-all"
                title="Run molecular docking simulation"
              >
                <Dna className="w-4 h-4" />
                <span>Run Docking</span>
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="mt-5 pt-4 border-t border-gray-100">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <span className="block text-xs text-gray-500 uppercase tracking-wider font-semibold">Mol Weight</span>
            <span className="block text-sm font-bold text-gray-900 mt-1">{candidate.properties.molecular_weight.toFixed(0)} Da</span>
          </div>
          <div>
            <span className="block text-xs text-gray-500 uppercase tracking-wider font-semibold">QED Score</span>
            <span className="block text-sm font-bold text-gray-900 mt-1">{candidate.properties.drug_likeness_score.toFixed(2)}</span>
          </div>
          <div>
            <span className="block text-xs text-gray-500 uppercase tracking-wider font-semibold">Target Conf.</span>
            <span className="block text-sm font-bold text-gray-900 mt-1">{(candidate.target.confidence_score * 100).toFixed(0)}%</span>
          </div>
        </div>
      </div>

      {/* Docking Submission Modal */}
      {showDockingModal && (
        <DockingSubmissionModal
          candidate={candidate}
          onClose={() => setShowDockingModal(false)}
          onSubmitSuccess={handleDockingSuccess}
        />
      )}
    </div>
  );
}