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

    // Limit to top 10 candidates
    return result.slice(0, 10);
  }, [candidates, sortBy, filterRisk]);

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between bg-white p-5 rounded-xl border border-gray-200 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center">
            <Filter className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="text-base font-bold text-gray-900 block">Filter & Sort</span>
            <span className="text-xs text-gray-500">Customize your results</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <label htmlFor="sort" className="text-sm font-medium text-gray-700">
              Sort by:
            </label>
            <select
              id="sort"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="px-4 py-2 border-2 border-gray-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white hover:border-blue-300 transition-colors"
            >
              <option value="score">Score</option>
              <option value="name">Name</option>
              <option value="risk">Risk Level</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="filter" className="text-sm font-medium text-gray-700">
              Risk:
            </label>
            <select
              id="filter"
              value={filterRisk}
              onChange={(e) => setFilterRisk(e.target.value as FilterOption)}
              className="px-4 py-2 border-2 border-gray-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-white hover:border-blue-300 transition-colors"
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
      <div className="flex items-center gap-2 px-4">
        <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
        <p className="text-sm font-medium text-gray-700">
          Showing top {filteredAndSortedCandidates.length} of {candidates.length} candidates
        </p>
      </div>

      {/* Candidate Cards */}
      <div className="space-y-5">
        {filteredAndSortedCandidates.map((candidate) => (
          <CandidateCard key={candidate.molecule.chembl_id} candidate={candidate} />
        ))}
      </div>

      {filteredAndSortedCandidates.length === 0 && (
        <div className="text-center py-16 bg-white rounded-xl border-2 border-dashed border-gray-300">
          <p className="text-gray-600 text-lg font-medium">No candidates match the selected filters.</p>
          <p className="text-gray-500 text-sm mt-2">Try adjusting your filter settings</p>
        </div>
      )}
    </div>
  );
}
