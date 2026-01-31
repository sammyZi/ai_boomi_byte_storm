'use client';

import { useState } from 'react';
import { ChevronDown, ChevronUp, Award, AlertTriangle } from 'lucide-react';
import { DrugCandidate } from '@/types';
import ScoreDisplay from './ScoreDisplay';

interface CandidateCardProps {
  candidate: DrugCandidate;
}

export default function CandidateCard({ candidate }: CandidateCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'low':
        return 'bg-green-100 text-green-800 border-green-300';
      case 'medium':
        return 'bg-yellow-100 text-yellow-800 border-yellow-300';
      case 'high':
        return 'bg-red-100 text-red-800 border-red-300';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-300';
    }
  };

  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow">
      {/* Card Header */}
      <div className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <div className="flex items-center justify-center w-10 h-10 bg-blue-100 text-blue-600 rounded-full font-bold">
                #{candidate.rank}
              </div>
              <div>
                <h3 className="text-lg font-semibold text-gray-900">
                  {candidate.molecule.name}
                </h3>
                <p className="text-sm text-gray-600">{candidate.molecule.chembl_id}</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 mt-3">
              <div className="flex items-center gap-1 px-3 py-1 bg-blue-50 text-blue-700 rounded-full text-sm font-medium">
                <Award className="w-4 h-4" />
                Score: {candidate.composite_score.toFixed(2)}
              </div>
              <div
                className={`flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium border ${getRiskColor(
                  candidate.toxicity.risk_level
                )}`}
              >
                <AlertTriangle className="w-4 h-4" />
                {candidate.toxicity.risk_level.charAt(0).toUpperCase() +
                  candidate.toxicity.risk_level.slice(1)}{' '}
                Risk
              </div>
            </div>
          </div>

          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-1 px-3 py-2 text-sm text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
          >
            {isExpanded ? (
              <>
                <ChevronUp className="w-4 h-4" />
                Less
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" />
                More
              </>
            )}
          </button>
        </div>

        {/* Score Display */}
        <div className="mt-4">
          <ScoreDisplay candidate={candidate} />
        </div>
      </div>

      {/* Expanded Details */}
      {isExpanded && (
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Target Information */}
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-2">Target Information</h4>
              <dl className="space-y-1 text-sm">
                <div>
                  <dt className="inline font-medium text-gray-700">Gene: </dt>
                  <dd className="inline text-gray-600">{candidate.target.gene_symbol}</dd>
                </div>
                <div>
                  <dt className="inline font-medium text-gray-700">Protein: </dt>
                  <dd className="inline text-gray-600">{candidate.target.protein_name}</dd>
                </div>
                <div>
                  <dt className="inline font-medium text-gray-700">Confidence: </dt>
                  <dd className="inline text-gray-600">
                    {(candidate.target.confidence_score * 100).toFixed(0)}%
                  </dd>
                </div>
              </dl>
            </div>

            {/* Molecular Properties */}
            <div>
              <h4 className="text-sm font-semibold text-gray-900 mb-2">
                Molecular Properties
              </h4>
              <dl className="space-y-1 text-sm">
                <div>
                  <dt className="inline font-medium text-gray-700">MW: </dt>
                  <dd className="inline text-gray-600">
                    {candidate.properties.molecular_weight.toFixed(2)} Da
                  </dd>
                </div>
                <div>
                  <dt className="inline font-medium text-gray-700">LogP: </dt>
                  <dd className="inline text-gray-600">
                    {candidate.properties.logp.toFixed(2)}
                  </dd>
                </div>
                <div>
                  <dt className="inline font-medium text-gray-700">TPSA: </dt>
                  <dd className="inline text-gray-600">
                    {candidate.properties.tpsa.toFixed(2)} Ų
                  </dd>
                </div>
                <div>
                  <dt className="inline font-medium text-gray-700">Lipinski Violations: </dt>
                  <dd className="inline text-gray-600">
                    {candidate.properties.lipinski_violations}
                  </dd>
                </div>
              </dl>
            </div>
          </div>

          {/* AI Analysis */}
          {candidate.ai_analysis && (
            <div className="mt-4">
              <h4 className="text-sm font-semibold text-gray-900 mb-2">AI Analysis</h4>
              <p className="text-sm text-gray-700 whitespace-pre-line">
                {candidate.ai_analysis}
              </p>
            </div>
          )}

          {/* Toxicity Warnings */}
          {candidate.toxicity.detected_toxicophores.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-semibold text-gray-900 mb-2">
                Detected Toxicophores
              </h4>
              <div className="flex flex-wrap gap-2">
                {candidate.toxicity.detected_toxicophores.map((toxicophore, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 bg-red-100 text-red-700 text-xs rounded-full"
                  >
                    {toxicophore}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
