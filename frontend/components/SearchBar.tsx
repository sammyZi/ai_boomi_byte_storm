'use client';

import { useState, useEffect, useRef } from 'react';
import { Search } from 'lucide-react';

interface SearchBarProps {
  onSearch: (query: string) => void;
  isLoading?: boolean;
  initialValue?: string;
}

const COMMON_DISEASES = [
  "Alzheimer's disease",
  "Parkinson's disease",
  'Type 2 diabetes',
  'Breast cancer',
  'Lung cancer',
  'Rheumatoid arthritis',
  'Multiple sclerosis',
  "Crohn's disease",
  'Asthma',
  'Depression',
];

export default function SearchBar({ onSearch, isLoading, initialValue = '' }: SearchBarProps) {
  const [query, setQuery] = useState(initialValue);
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [filteredDiseases, setFilteredDiseases] = useState<string[]>([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (query.length >= 2) {
      const filtered = COMMON_DISEASES.filter((disease) =>
        disease.toLowerCase().includes(query.toLowerCase())
      );
      setFilteredDiseases(filtered);
      setShowAutocomplete(filtered.length > 0);
    } else {
      setShowAutocomplete(false);
      setFilteredDiseases([]);
    }
  }, [query]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim().length >= 2 && query.trim().length <= 200) {
      onSearch(query.trim());
      setShowAutocomplete(false);
    }
  };

  const handleSelect = (disease: string) => {
    setQuery(disease);
    setShowAutocomplete(false);
    onSearch(disease);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!showAutocomplete) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev < filteredDiseases.length - 1 ? prev + 1 : prev));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
    } else if (e.key === 'Enter' && selectedIndex >= 0) {
      e.preventDefault();
      handleSelect(filteredDiseases[selectedIndex]);
    } else if (e.key === 'Escape') {
      setShowAutocomplete(false);
    }
  };

  const isValid = query.length >= 2 && query.length <= 200;
  const showError = query.length > 0 && !isValid;

  return (
    <div className="relative w-full max-w-3xl">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative group">
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            onFocus={() => query.length >= 2 && setShowAutocomplete(true)}
            onBlur={() => setTimeout(() => setShowAutocomplete(false), 200)}
            placeholder="Enter disease name (e.g., Alzheimer's disease)"
            disabled={isLoading}
            className={`w-full px-5 py-3 pl-12 pr-5 text-base border-2 rounded-xl focus:outline-none focus:ring-4 transition-all shadow-md ${
              showError
                ? 'border-red-300 focus:border-red-500 focus:ring-red-100 bg-white'
                : 'border-blue-200 focus:border-blue-500 focus:ring-blue-100 group-hover:border-blue-400 bg-white/95 backdrop-blur-sm'
            } ${isLoading ? 'bg-gray-50 cursor-not-allowed' : ''}`}
          />
          <div className="absolute left-4 top-1/2 transform -translate-y-1/2 w-7 h-7 flex items-center justify-center bg-gradient-to-br from-blue-500 to-indigo-600 rounded-lg shadow-md shadow-blue-500/30">
            <Search className="w-4 h-4 text-white" strokeWidth={2.5} />
          </div>
        </div>

        {showError && (
          <p className="mt-3 text-sm text-red-600 font-medium flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-red-500 rounded-full"></span>
            Disease name must be between 2 and 200 characters
          </p>
        )}

        <button
          type="submit"
          disabled={!isValid || isLoading}
          className="mt-3 w-auto mx-auto block bg-blue-500 text-white py-2 px-6 rounded-lg font-medium text-sm hover:bg-blue-600 focus:outline-none focus:ring-4 focus:ring-blue-200 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg"
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              Searching...
            </span>
          ) : (
            'Discover Drug Candidates'
          )}
        </button>
      </form>

      {/* Autocomplete Dropdown */}
      {showAutocomplete && filteredDiseases.length > 0 && (
        <div className="absolute z-10 w-full mt-2 bg-white border-2 border-gray-200 rounded-xl shadow-2xl max-h-72 overflow-y-auto">
          {filteredDiseases.map((disease, index) => (
            <button
              key={disease}
              type="button"
              onClick={() => handleSelect(disease)}
              className={`w-full text-left px-6 py-3 hover:bg-blue-50 transition-colors border-b border-gray-100 last:border-b-0 ${
                index === selectedIndex ? 'bg-blue-100' : ''
              }`}
            >
              <span
                className="text-base"
                dangerouslySetInnerHTML={{
                  __html: disease.replace(
                    new RegExp(query, 'gi'),
                    (match) => `<strong class="text-blue-600 font-semibold">${match}</strong>`
                  ),
                }}
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
