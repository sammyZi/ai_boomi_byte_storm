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
    <div className="relative w-full max-w-2xl">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
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
            className={`w-full px-4 py-3 pl-12 pr-4 text-lg border-2 rounded-lg focus:outline-none focus:ring-2 transition-all ${
              showError
                ? 'border-red-300 focus:border-red-500 focus:ring-red-200'
                : 'border-gray-300 focus:border-blue-500 focus:ring-blue-200'
            } ${isLoading ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'}`}
          />
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
        </div>

        {showError && (
          <p className="mt-2 text-sm text-red-600">
            Disease name must be between 2 and 200 characters
          </p>
        )}

        <button
          type="submit"
          disabled={!isValid || isLoading}
          className="mt-3 w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
        >
          {isLoading ? 'Searching...' : 'Discover Drug Candidates'}
        </button>
      </form>

      {/* Autocomplete Dropdown */}
      {showAutocomplete && filteredDiseases.length > 0 && (
        <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {filteredDiseases.map((disease, index) => (
            <button
              key={disease}
              type="button"
              onClick={() => handleSelect(disease)}
              className={`w-full text-left px-4 py-2 hover:bg-blue-50 transition-colors ${
                index === selectedIndex ? 'bg-blue-100' : ''
              }`}
            >
              <span
                dangerouslySetInnerHTML={{
                  __html: disease.replace(
                    new RegExp(query, 'gi'),
                    (match) => `<strong class="text-blue-600">${match}</strong>`
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
