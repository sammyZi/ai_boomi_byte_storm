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
    <div className="max-w-7xl mx-auto px-6">
      <div className="bg-white/80 backdrop-blur-sm rounded-3xl shadow-xl border border-blue-100 p-8">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-gray-900 mb-4">
              Results for: <span className="text-blue-600">{data.query}</span>
            </h1>
            <div className="flex flex-wrap items-center gap-3 text-sm">
              <div className="flex items-center gap-2 bg-blue-50 text-blue-700 px-4 py-2 rounded-xl border border-blue-200">
                <Target className="w-4 h-4" />
                <span className="font-semibold">
                  {data.candidates.length} candidate{data.candidates.length !== 1 ? 's' : ''}
                </span>
              </div>
              <div className="flex items-center gap-2 bg-indigo-50 text-indigo-700 px-4 py-2 rounded-xl border border-indigo-200">
                <Clock className="w-4 h-4" />
                <span className="font-semibold">
                  {data.processing_time_seconds.toFixed(1)}s
                </span>
              </div>
              <div className="text-xs text-gray-500 bg-gray-50 px-3 py-1.5 rounded-xl border border-gray-200">
                {new Date(data.timestamp).toLocaleString()}
              </div>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => exportToJSON(data)}
              disabled={isExporting}
              className="flex items-center gap-2 px-4 py-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all font-semibold shadow-md text-sm"
            >
              <Download className="w-4 h-4" />
              JSON
            </button>
            <button
              onClick={() => exportToCSV(data)}
              disabled={isExporting}
              className="flex items-center gap-2 px-4 py-2.5 bg-green-600 text-white rounded-xl hover:bg-green-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-all font-semibold shadow-md text-sm"
            >
              <Download className="w-4 h-4" />
              CSV
            </button>
          </div>
        </div>

        {data.warnings && data.warnings.length > 0 && (
          <div className="mt-6 p-4 bg-yellow-50 border border-yellow-200 rounded-xl">
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
