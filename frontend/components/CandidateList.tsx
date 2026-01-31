'use client';

import { useState, useMemo } from 'react';
import { DrugCandidate } from '@/types';
import CandidateCard from './CandidateCard';
import { Filter } from 'lucide-react';

interface CandidateListProps {
  candidates: DrugCandidate[];
}

type SortOption = 'score' | 'name' | 'risk';
type FilterOption = 'all' | 'low' | 'medium' | 'high';

export default function CandidateList({ candidates }: CandidateListProps) {
  const [sortBy, setSortBy] = useState<SortOption>('score');
  const [filterRisk, setFilterRisk] = useState<FilterOption>('all');

  const filteredAndSortedCandidates = useMemo(() => {
    let result = [...candidates];

    // Filter by risk level
    if (filterRisk !== 'all') {
      result = result.filter((c) => c.toxicity.risk_level === filterRisk);
    }

    // Sort
    result.sort((a, b) => {
      switch (sortBy) {
        case 'score':
          return b.composite_score - a.composite_score;
        case 'name':
          return a.molecule.name.localeCompare(b.molecule.name);
        case 'risk':
          const riskOrder = { low: 0, medium: 1, high: 2 };
          return riskOrder[a.toxicity.risk_level] - riskOrder[b.toxicity.risk_level];
        default:
          return 0;
      }
    });

    return result;
  }, [candidates, sortBy, filterRisk]);

  return (
    <div className="space-y-4">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between bg-white p-4 rounded-lg border border-gray-200">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-gray-600" />
          <span className="text-sm font-medium text-gray-700">Filter & Sort</span>
        </div>

        <div className="flex flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <label htmlFor="sort" className="text-sm text-gray-600">
              Sort by:
            </label>
            <select
              id="sort"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="score">Score</option>
              <option value="name">Name</option>
              <option value="risk">Risk Level</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="filter" className="text-sm text-gray-600">
              Risk:
            </label>
            <select
              id="filter"
              value={filterRisk}
              onChange={(e) => setFilterRisk(e.target.value as FilterOption)}
              className="px-3 py-1 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">All</option>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results Count */}
      <p className="text-sm text-gray-600">
        Showing {filteredAndSortedCandidates.length} of {candidates.length} candidates
      </p>

      {/* Candidate Cards */}
      <div className="space-y-4">
        {filteredAndSortedCandidates.map((candidate) => (
          <CandidateCard key={candidate.molecule.chembl_id} candidate={candidate} />
        ))}
      </div>

      {filteredAndSortedCandidates.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-600">No candidates match the selected filters.</p>
        </div>
      )}
    </div>
  );
}
