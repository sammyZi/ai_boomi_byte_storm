'use client';

import { Download, Clock, Target } from 'lucide-react';
import { DiscoveryResponse } from '@/types';
import useExport from '@/hooks/useExport';

interface ResultsHeaderProps {
  data: DiscoveryResponse;
}

export default function ResultsHeader({ data }: ResultsHeaderProps) {
  const { exportToJSON, exportToCSV, isExporting } = useExport();

  return (
    <div className="bg-white border-b border-gray-200 px-6 py-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 mb-2">
              Results for: <span className="text-blue-600">{data.query}</span>
            </h1>
            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
              <div className="flex items-center gap-1">
                <Target className="w-4 h-4" />
                <span>
                  {data.candidates.length} candidate{data.candidates.length !== 1 ? 's' : ''}{' '}
                  found
                </span>
              </div>
              <div className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                <span>Processed in {data.processing_time_seconds.toFixed(1)}s</span>
              </div>
              <div className="text-xs text-gray-500">
                {new Date(data.timestamp).toLocaleString()}
              </div>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => exportToJSON(data)}
              disabled={isExporting}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              <Download className="w-4 h-4" />
              Export JSON
            </button>
            <button
              onClick={() => exportToCSV(data)}
              disabled={isExporting}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          </div>
        </div>

        {data.warnings && data.warnings.length > 0 && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm font-semibold text-yellow-800 mb-1">Warnings:</p>
            <ul className="text-sm text-yellow-700 list-disc list-inside">
              {data.warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
