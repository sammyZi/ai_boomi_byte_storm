'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Search, Check, AlertCircle, HelpCircle, Loader2, ChevronDown, Target, Sparkles, X } from 'lucide-react';

// Types
interface DiseaseSuggestion {
  disease_id: string;
  disease_name: string;
  match_type: 'exact' | 'synonym' | 'typo_corrected' | 'semantic' | 'hierarchical' | 'fallback' | 'partial';
  confidence: number;
  confidence_level: 'high' | 'medium' | 'low';
  target_count: number;
  synonyms: string[];
  description: string;
  correction_applied: string;
  parent_diseases: string[];
}

interface SuggestionResponse {
  query: string;
  suggestions: DiseaseSuggestion[];
  confidence_level: 'high' | 'medium' | 'low';
  message: string;
  processing_time_ms: number;
}

interface SmartDiseaseSearchProps {
  onSearch: (query: string, diseaseId?: string) => void;
  isLoading?: boolean;
  initialValue?: string;
  placeholder?: string;
}

// Debounce hook
function useDebounce<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);

  return debouncedValue;
}

// Confidence level colors and icons
const confidenceStyles = {
  high: {
    bg: 'bg-green-50',
    border: 'border-green-400',
    text: 'text-green-700',
    icon: Check,
    iconColor: 'text-green-500',
    badge: 'bg-green-100 text-green-700',
  },
  medium: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-400',
    text: 'text-yellow-700',
    icon: AlertCircle,
    iconColor: 'text-yellow-500',
    badge: 'bg-yellow-100 text-yellow-700',
  },
  low: {
    bg: 'bg-red-50',
    border: 'border-red-400',
    text: 'text-red-700',
    icon: HelpCircle,
    iconColor: 'text-red-500',
    badge: 'bg-red-100 text-red-700',
  },
};

// Match type descriptions
const matchTypeLabels: Record<string, string> = {
  exact: 'Exact match',
  synonym: 'Synonym',
  typo_corrected: 'Corrected',
  semantic: 'Similar',
  hierarchical: 'Broader term',
  fallback: 'Suggested',
  partial: 'Partial match',
};

export default function SmartDiseaseSearch({
  onSearch,
  isLoading = false,
  initialValue = '',
  placeholder = 'Enter disease name (e.g., Alzheimer\'s, AD, parkinsons)',
}: SmartDiseaseSearchProps) {
  const [query, setQuery] = useState(initialValue);
  const [suggestions, setSuggestions] = useState<DiseaseSuggestion[]>([]);
  const [selectedSuggestion, setSelectedSuggestion] = useState<DiseaseSuggestion | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isFetching, setIsFetching] = useState(false);
  const [responseMessage, setResponseMessage] = useState('');
  const [overallConfidence, setOverallConfidence] = useState<'high' | 'medium' | 'low'>('high');
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [processingTime, setProcessingTime] = useState(0);

  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const debouncedQuery = useDebounce(query, 300);

  // Fetch suggestions from API
  const fetchSuggestions = useCallback(async (searchQuery: string) => {
    if (!searchQuery || searchQuery.length < 2) {
      setSuggestions([]);
      setIsOpen(false);
      return;
    }

    setIsFetching(true);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/diseases/suggest?q=${encodeURIComponent(searchQuery)}&max_results=8`
      );

      if (!response.ok) {
        throw new Error('Failed to fetch suggestions');
      }

      const data: SuggestionResponse = await response.json();
      setSuggestions(data.suggestions);
      setResponseMessage(data.message);
      setOverallConfidence(data.confidence_level);
      setProcessingTime(data.processing_time_ms);
      setIsOpen(data.suggestions.length > 0);
      setSelectedIndex(-1);
    } catch (error) {
      console.error('Error fetching suggestions:', error);
      setSuggestions([]);
    } finally {
      setIsFetching(false);
    }
  }, []);

  // Fetch when debounced query changes
  useEffect(() => {
    if (debouncedQuery && !selectedSuggestion) {
      fetchSuggestions(debouncedQuery);
    }
  }, [debouncedQuery, fetchSuggestions, selectedSuggestion]);

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    setSelectedSuggestion(null);
  };

  // Handle suggestion selection
  const handleSelectSuggestion = (suggestion: DiseaseSuggestion) => {
    setQuery(suggestion.disease_name);
    setSelectedSuggestion(suggestion);
    setIsOpen(false);
    setSelectedIndex(-1);
  };

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim().length >= 2) {
      // If we have a selected suggestion, use its ID
      if (selectedSuggestion) {
        onSearch(selectedSuggestion.disease_name, selectedSuggestion.disease_id);
      } else if (suggestions.length > 0 && selectedIndex >= 0) {
        const selected = suggestions[selectedIndex];
        onSearch(selected.disease_name, selected.disease_id);
      } else {
        onSearch(query.trim());
      }
      setIsOpen(false);
    }
  };

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen || suggestions.length === 0) {
      if (e.key === 'Enter') {
        handleSubmit(e);
      }
      return;
    }

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, suggestions.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, -1));
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0) {
          handleSelectSuggestion(suggestions[selectedIndex]);
          // Auto-submit on selection
          setTimeout(() => {
            const selected = suggestions[selectedIndex];
            onSearch(selected.disease_name, selected.disease_id);
          }, 50);
        } else if (suggestions.length > 0) {
          // Select top suggestion if none selected
          handleSelectSuggestion(suggestions[0]);
          setTimeout(() => {
            onSearch(suggestions[0].disease_name, suggestions[0].disease_id);
          }, 50);
        }
        break;
      case 'Escape':
        setIsOpen(false);
        setSelectedIndex(-1);
        break;
      case 'Tab':
        if (suggestions.length > 0 && selectedIndex === -1) {
          e.preventDefault();
          setSelectedIndex(0);
        }
        break;
    }
  };

  // Clear input
  const handleClear = () => {
    setQuery('');
    setSelectedSuggestion(null);
    setSuggestions([]);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  // Click outside to close
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Get current status indicator
  const getStatusIndicator = () => {
    if (isFetching) {
      return (
        <div className="flex items-center gap-2 text-blue-600">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">Searching...</span>
        </div>
      );
    }

    if (selectedSuggestion) {
      const style = confidenceStyles[selectedSuggestion.confidence_level];
      const Icon = style.icon;
      return (
        <div className={`flex items-center gap-2 ${style.text}`}>
          <Icon className={`w-4 h-4 ${style.iconColor}`} />
          <span className="text-sm font-medium">
            {selectedSuggestion.target_count > 0
              ? `${selectedSuggestion.target_count.toLocaleString()} targets`
              : 'Selected'}
          </span>
        </div>
      );
    }

    if (query.length >= 2 && suggestions.length > 0) {
      const style = confidenceStyles[overallConfidence];
      return (
        <div className={`flex items-center gap-2 ${style.text}`}>
          <span className="text-sm">{responseMessage}</span>
        </div>
      );
    }

    return null;
  };

  // Determine input border color
  const getInputBorderClass = () => {
    if (selectedSuggestion) {
      return confidenceStyles[selectedSuggestion.confidence_level].border;
    }
    if (query.length >= 2 && suggestions.length > 0) {
      return confidenceStyles[overallConfidence].border;
    }
    return 'border-blue-200 focus-within:border-blue-500';
  };

  return (
    <div className="relative w-full max-w-3xl">
      <form onSubmit={handleSubmit} className="relative">
        {/* Input Container */}
        <div
          className={`relative flex items-center bg-white rounded-xl border-2 transition-all shadow-md hover:shadow-lg ${getInputBorderClass()}`}
        >
          {/* Search Icon */}
          <div className="absolute left-4 flex items-center justify-center w-8 h-8 bg-blue-600 rounded-lg">
            <Search className="w-4 h-4 text-white" strokeWidth={2.5} />
          </div>

          {/* Input */}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            onFocus={() => query.length >= 2 && suggestions.length > 0 && setIsOpen(true)}
            placeholder={placeholder}
            disabled={isLoading}
            className="w-full py-4 pl-16 pr-24 text-base bg-transparent focus:outline-none placeholder-gray-400"
            autoComplete="off"
            spellCheck="false"
          />

          {/* Right Side Actions */}
          <div className="absolute right-4 flex items-center gap-2">
            {/* Fetching indicator */}
            {isFetching && (
              <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
            )}

            {/* Clear button */}
            {query && !isFetching && (
              <button
                type="button"
                onClick={handleClear}
                className="p-1 rounded-full hover:bg-gray-100 transition-colors"
              >
                <X className="w-4 h-4 text-gray-400" />
              </button>
            )}

            {/* Dropdown indicator */}
            {suggestions.length > 0 && (
              <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="p-1 rounded-full hover:bg-gray-100 transition-colors"
              >
                <ChevronDown
                  className={`w-5 h-5 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                />
              </button>
            )}
          </div>
        </div>

        {/* Status Indicator */}
        <div className="mt-2 h-6 flex items-center justify-between px-1">
          <div>{getStatusIndicator()}</div>
          {processingTime > 0 && query.length >= 2 && !isFetching && (
            <span className="text-xs text-gray-400">{processingTime}ms</span>
          )}
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={query.length < 2 || isLoading}
          className="mt-2 w-full bg-blue-600 text-white py-3 px-6 rounded-xl font-semibold text-base hover:bg-blue-700 focus:outline-none focus:ring-4 focus:ring-blue-200 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all shadow-md hover:shadow-lg flex items-center justify-center gap-2"
        >
          {isLoading ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              <span>Discovering...</span>
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              <span>Discover Drug Candidates</span>
            </>
          )}
        </button>
      </form>

      {/* Suggestions Dropdown */}
      {isOpen && suggestions.length > 0 && (
        <div
          ref={dropdownRef}
          className="absolute z-50 w-full mt-2 bg-white border-2 border-gray-200 rounded-xl shadow-2xl max-h-96 overflow-y-auto"
        >
          {/* Header */}
          <div className="px-4 py-2 border-b border-gray-100 bg-gray-50 rounded-t-xl">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">
                {suggestions.length} suggestion{suggestions.length !== 1 ? 's' : ''} found
              </span>
              {responseMessage && (
                <span className={`text-sm ${confidenceStyles[overallConfidence].text}`}>
                  {responseMessage}
                </span>
              )}
            </div>
          </div>

          {/* Suggestions List */}
          <ul className="py-1">
            {suggestions.map((suggestion, index) => {
              const style = confidenceStyles[suggestion.confidence_level];
              const Icon = style.icon;
              const isSelected = index === selectedIndex;

              return (
                <li key={suggestion.disease_id || index}>
                  <button
                    type="button"
                    onClick={() => handleSelectSuggestion(suggestion)}
                    className={`w-full text-left px-4 py-3 transition-colors border-b border-gray-50 last:border-b-0 ${
                      isSelected ? 'bg-blue-50' : 'hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-3">
                      {/* Left: Disease Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <Icon className={`w-4 h-4 flex-shrink-0 ${style.iconColor}`} />
                          <span className="font-medium text-gray-900 truncate">
                            {suggestion.disease_name}
                          </span>
                        </div>

                        {/* Correction or Match Type */}
                        {suggestion.correction_applied && (
                          <p className="mt-1 text-sm text-blue-600 pl-6 flex items-center gap-1">
                            <Check className="w-3 h-3" />
                            <span>{suggestion.correction_applied}</span>
                          </p>
                        )}

                        {/* Description */}
                        {suggestion.description && (
                          <p className="mt-1 text-sm text-gray-500 pl-6 line-clamp-2">
                            {suggestion.description}
                          </p>
                        )}

                        {/* Synonyms */}
                        {suggestion.synonyms.length > 0 && (
                          <p className="mt-1 text-xs text-gray-400 pl-6">
                            Also known as: {suggestion.synonyms.slice(0, 3).join(', ')}
                          </p>
                        )}
                      </div>

                      {/* Right: Badges */}
                      <div className="flex flex-col items-end gap-1 flex-shrink-0">
                        {/* Target Count */}
                        {suggestion.target_count > 0 && (
                          <div className="flex items-center gap-1 px-2 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                            <Target className="w-3 h-3" />
                            <span>{suggestion.target_count.toLocaleString()}</span>
                          </div>
                        )}

                        {/* Match Type */}
                        <span className={`px-2 py-0.5 rounded-full text-xs ${style.badge}`}>
                          {matchTypeLabels[suggestion.match_type] || suggestion.match_type}
                        </span>

                        {/* Confidence */}
                        <span className="text-xs text-gray-400">
                          {Math.round(suggestion.confidence * 100)}% match
                        </span>
                      </div>
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>

          {/* Footer Hint */}
          <div className="px-4 py-2 border-t border-gray-100 bg-gray-50 rounded-b-xl">
            <p className="text-xs text-gray-500 text-center">
              Press <kbd className="px-1.5 py-0.5 bg-gray-200 rounded text-gray-600">↵</kbd> to select top result,{' '}
              <kbd className="px-1.5 py-0.5 bg-gray-200 rounded text-gray-600">↑↓</kbd> to navigate
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
