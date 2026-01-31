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
    <div className="bg-blue-600 border-b border-blue-700 px-6 py-6 shadow-lg">
      <div className="max-w-7xl mx-auto">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-white mb-3">
              Results for: <span className="text-blue-100">{data.query}</span>
            </h1>
            <div className="flex flex-wrap items-center gap-4 text-sm text-blue-100">
              <div className="flex items-center gap-2 bg-white/20 px-4 py-2 rounded-xl backdrop-blur-sm">
                <Target className="w-5 h-5" />
                <span className="font-semibold">
                  {data.candidates.length} candidate{data.candidates.length !== 1 ? 's' : ''}
                </span>
              </div>
              <div className="flex items-center gap-2 bg-white/20 px-4 py-2 rounded-xl backdrop-blur-sm">
                <Clock className="w-5 h-5" />
                <span className="font-semibold">
                  {data.processing_time_seconds.toFixed(1)}s
                </span>
              </div>
              <div className="text-xs text-blue-200 bg-white/10 px-3 py-2 rounded-xl">
                {new Date(data.timestamp).toLocaleString()}
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => exportToJSON(data)}
              disabled={isExporting}
              className="flex items-center gap-2 px-5 py-3 bg-white text-blue-600 rounded-xl hover:bg-blue-50 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all font-semibold shadow-md"
            >
              <Download className="w-5 h-5" />
              JSON
            </button>
            <button
              onClick={() => exportToCSV(data)}
              disabled={isExporting}
              className="flex items-center gap-2 px-5 py-3 bg-white text-green-600 rounded-xl hover:bg-green-50 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all font-semibold shadow-md"
            >
              <Download className="w-5 h-5" />
              CSV
            </button>
          </div>
        </div>

        {data.warnings && data.warnings.length > 0 && (
          <div className="mt-6 p-4 bg-yellow-50 border-l-4 border-yellow-400 rounded-lg shadow-sm">
            <p className="text-sm font-bold text-yellow-800 mb-2">⚠️ Warnings:</p>
            <ul className="text-sm text-yellow-700 space-y-1">
              {data.warnings.map((warning, index) => (
                <li key={index} className="flex items-start gap-2">
                  <span className="text-yellow-500 mt-0.5">•</span>
                  <span>{warning}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
