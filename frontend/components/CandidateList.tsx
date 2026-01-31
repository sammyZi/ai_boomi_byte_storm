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
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between bg-white/80 backdrop-blur-sm p-6 rounded-2xl border border-blue-100 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center shadow-md shadow-blue-500/30">
            <Filter className="w-5 h-5 text-white" />
          </div>
          <div>
            <span className="text-base font-bold text-gray-900 block">Filter & Sort</span>
            <span className="text-xs text-gray-500">Customize your results</span>
          </div>
        </div>

        <div className="flex flex-wrap gap-3">
          <div className="flex items-center gap-2">
            <label htmlFor="sort" className="text-sm font-semibold text-gray-700">
              Sort by:
            </label>
            <select
              id="sort"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as SortOption)}
              className="px-4 py-2.5 border-2 border-blue-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-4 focus:ring-blue-100 focus:border-blue-500 bg-white hover:border-blue-400 transition-all shadow-sm cursor-pointer appearance-none bg-[url('data:image/svg+xml;charset=UTF-8,%3csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27%233b82f6%27 stroke-width=%272%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3e%3cpolyline points=%276 9 12 15 18 9%27%3e%3c/polyline%3e%3c/svg%3e')] bg-[length:1.2em] bg-[right_0.5rem_center] bg-no-repeat pr-10"
            >
              <option value="score">Score</option>
              <option value="name">Name</option>
              <option value="risk">Risk Level</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <label htmlFor="filter" className="text-sm font-semibold text-gray-700">
              Risk:
            </label>
            <select
              id="filter"
              value={filterRisk}
              onChange={(e) => setFilterRisk(e.target.value as FilterOption)}
              className="px-4 py-2.5 border-2 border-blue-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-4 focus:ring-blue-100 focus:border-blue-500 bg-white hover:border-blue-400 transition-all shadow-sm cursor-pointer appearance-none bg-[url('data:image/svg+xml;charset=UTF-8,%3csvg xmlns=%27http://www.w3.org/2000/svg%27 viewBox=%270 0 24 24%27 fill=%27none%27 stroke=%27%233b82f6%27 stroke-width=%272%27 stroke-linecap=%27round%27 stroke-linejoin=%27round%27%3e%3cpolyline points=%276 9 12 15 18 9%27%3e%3c/polyline%3e%3c/svg%3e')] bg-[length:1.2em] bg-[right_0.5rem_center] bg-no-repeat pr-10"
            >
              <option value="all">All Levels</option>
              <option value="low">Low Risk</option>
              <option value="medium">Medium Risk</option>
              <option value="high">High Risk</option>
            </select>
          </div>
        </div>
      </div>

      {/* Results Count */}
      <div className="flex items-center gap-2 px-4">
        <div className="w-2 h-2 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-full animate-pulse"></div>
        <p className="text-sm font-semibold text-gray-700">
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
        <div className="text-center py-16 bg-white/80 backdrop-blur-sm rounded-2xl border-2 border-dashed border-blue-200">
          <p className="text-gray-700 text-lg font-semibold">No candidates match the selected filters.</p>
          <p className="text-gray-500 text-sm mt-2">Try adjusting your filter settings</p>
        </div>
      )}
    </div>
  );
}
