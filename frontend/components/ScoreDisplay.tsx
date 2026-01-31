'use client';

import { DrugCandidate } from '@/types';

interface ScoreDisplayProps {
  candidate: DrugCandidate;
}

export default function ScoreDisplay({ candidate }: ScoreDisplayProps) {
  const scores = [
    {
      label: 'Binding Affinity',
      value: candidate.binding_affinity_score,
      color: 'bg-purple-500',
    },
    {
      label: 'Drug Likeness',
      value: candidate.properties.drug_likeness_score,
      color: 'bg-blue-500',
    },
    {
      label: 'Safety',
      value: 1 - candidate.toxicity.toxicity_score,
      color: 'bg-green-500',
    },
  ];

  return (
    <div className="space-y-3">
      {scores.map((score) => (
        <div key={score.label}>
          <div className="flex justify-between items-center mb-1">
            <span className="text-sm font-medium text-gray-700">{score.label}</span>
            <span className="text-sm font-semibold text-gray-900">
              {(score.value * 100).toFixed(0)}%
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`${score.color} h-2 rounded-full transition-all duration-500`}
              style={{ width: `${score.value * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
