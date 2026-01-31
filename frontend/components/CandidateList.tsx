'use client';

import { useState, useMemo, useRef, useEffect } from 'react';
import { DrugCandidate } from '@/types';
import CandidateCard from './CandidateCard';
import { Filter, ChevronDown } from 'lucide-react';

interface CandidateListProps {
  candidates: DrugCandidate[];
}

type SortOption = 'score' | 'name' | 'risk';
type FilterOption = 'all' | 'low' | 'medium' | 'high';

export default function CandidateList({ candidates }: CandidateListProps) {
  const [sortBy, setSortBy] = useState<SortOption>('score');
  const [filterRisk, setFilterRisk] = useState<FilterOption>('all');
  const [showSortDropdown, setShowSortDropdown] = useState(false);
  const [showFilterDropdown, setShowFilterDropdown] = useState(false);
  const sortRef = useRef<HTMLDivElement>(null);
  const filterRef = useRef<HTMLDivElement>(null);

  const sortOptions = [
    { value: 'score', label: 'Score (Highest First)' },
    { value: 'name', label: 'Name (A-Z)' },
    { value: 'risk', label: 'Risk Level (Low to High)' },
  ];

  const filterOptions = [
    { value: 'all', label: 'All Risk Levels', color: 'text-gray-700' },
    { value: 'low', label: 'Low Risk', color: 'text-green-600' },
    { value: 'medium', label: 'Medium Risk', color: 'text-yellow-600' },
    { value: 'high', label: 'High Risk', color: 'text-red-600' },
  ];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (sortRef.current && !sortRef.current.contains(event.target as Node)) {
        setShowSortDropdown(false);
      }
      if (filterRef.current && !filterRef.current.contains(event.target as Node)) {
        setShowFilterDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

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

    // Limit to top 20 candidates
    return result.slice(0, 20);
  }, [candidates, sortBy, filterRisk]);

  return (
    <div className="space-y-6">
      {/* Controls */}
      <div className="relative z-30 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between bg-white/80 backdrop-blur-sm p-6 rounded-2xl border border-blue-100 shadow-lg">
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
          {/* Custom Sort Dropdown */}
          <div className="flex items-center gap-2" ref={sortRef}>
            <label className="text-sm font-semibold text-gray-700">
              Sort by:
            </label>
            <div className="relative">
              <button
                onClick={() => setShowSortDropdown(!showSortDropdown)}
                className="min-w-[180px] px-4 py-2.5 border-2 border-blue-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-4 focus:ring-blue-100 focus:border-blue-500 bg-white hover:border-blue-400 hover:bg-blue-50 transition-all shadow-sm cursor-pointer flex items-center justify-between"
              >
                <span>{sortOptions.find(opt => opt.value === sortBy)?.label}</span>
                <ChevronDown className={`w-4 h-4 text-blue-600 transition-transform ${showSortDropdown ? 'rotate-180' : ''}`} />
              </button>
              {showSortDropdown && (
                <div className="absolute z-50 w-full mt-2 bg-white border-2 border-blue-200 rounded-xl shadow-2xl overflow-hidden">
                  {sortOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setSortBy(option.value as SortOption);
                        setShowSortDropdown(false);
                      }}
                      className={`w-full text-left px-4 py-3 text-sm font-medium transition-all ${
                        sortBy === option.value
                          ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-600'
                          : 'text-gray-700 hover:bg-blue-50 hover:text-blue-600'
                      }`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Custom Filter Dropdown */}
          <div className="flex items-center gap-2" ref={filterRef}>
            <label className="text-sm font-semibold text-gray-700">
              Risk:
            </label>
            <div className="relative">
              <button
                onClick={() => setShowFilterDropdown(!showFilterDropdown)}
                className="min-w-[160px] px-4 py-2.5 border-2 border-blue-200 rounded-xl text-sm font-medium focus:outline-none focus:ring-4 focus:ring-blue-100 focus:border-blue-500 bg-white hover:border-blue-400 hover:bg-blue-50 transition-all shadow-sm cursor-pointer flex items-center justify-between"
              >
                <span className={filterOptions.find(opt => opt.value === filterRisk)?.color}>
                  {filterOptions.find(opt => opt.value === filterRisk)?.label}
                </span>
                <ChevronDown className={`w-4 h-4 text-blue-600 transition-transform ${showFilterDropdown ? 'rotate-180' : ''}`} />
              </button>
              {showFilterDropdown && (
                <div className="absolute z-50 w-full mt-2 bg-white border-2 border-blue-200 rounded-xl shadow-2xl overflow-hidden">
                  {filterOptions.map((option) => (
                    <button
                      key={option.value}
                      onClick={() => {
                        setFilterRisk(option.value as FilterOption);
                        setShowFilterDropdown(false);
                      }}
                      className={`w-full text-left px-4 py-3 text-sm font-medium transition-all ${
                        filterRisk === option.value
                          ? 'bg-blue-50 border-l-4 border-blue-600'
                          : 'hover:bg-blue-50'
                      } ${option.color}`}
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
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
