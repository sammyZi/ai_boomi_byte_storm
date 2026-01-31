'use client';

import { AlertCircle, RefreshCw } from 'lucide-react';
import { ErrorResponse } from '@/types';

interface ErrorMessageProps {
  error: ErrorResponse;
  onRetry?: () => void;
}

export default function ErrorMessage({ error, onRetry }: ErrorMessageProps) {
  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="bg-red-50 border-2 border-red-200 rounded-lg p-6">
        <div className="flex items-start gap-4">
          <AlertCircle className="w-8 h-8 text-red-600 flex-shrink-0 mt-1" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-red-900 mb-2">Error Occurred</h3>
            <p className="text-red-800 mb-4">{error.message}</p>

            {error.details && (
              <div className="bg-red-100 rounded p-3 mb-4">
                <p className="text-sm font-medium text-red-900 mb-1">Details:</p>
                <pre className="text-xs text-red-800 overflow-x-auto">
                  {JSON.stringify(error.details, null, 2)}
                </pre>
              </div>
            )}

            <div className="flex items-center gap-3">
              {onRetry && (
                <button
                  onClick={onRetry}
                  className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors"
                >
                  <RefreshCw className="w-4 h-4" />
                  Try Again
                </button>
              )}
              <p className="text-xs text-red-600">Error Code: {error.error_code}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
