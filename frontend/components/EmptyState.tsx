'use client';

import { Search } from 'lucide-react';

interface EmptyStateProps {
  onSearchAgain?: () => void;
}

export default function EmptyState({ onSearchAgain }: EmptyStateProps) {
  return (
    <div className="max-w-2xl mx-auto p-12 text-center">
      <div className="inline-flex items-center justify-center w-20 h-20 bg-gray-100 rounded-full mb-6">
        <Search className="w-10 h-10 text-gray-400" />
      </div>
      <h3 className="text-2xl font-semibold text-gray-900 mb-3">No Results Found</h3>
      <p className="text-gray-600 mb-6">
        We couldn't find any drug candidates for this disease. This could be because:
      </p>
      <ul className="text-left text-gray-600 space-y-2 mb-8 max-w-md mx-auto">
        <li>• The disease name might be misspelled</li>
        <li>• No targets are associated with this disease in our database</li>
        <li>• No bioactive molecules are available for the identified targets</li>
      </ul>
      {onSearchAgain && (
        <button
          onClick={onSearchAgain}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Search Again
        </button>
      )}
    </div>
  );
}
