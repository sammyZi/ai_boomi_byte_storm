'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Maximize2,
  Minimize2,
  Download,
  ChevronDown,
  Eye,
  EyeOff,
  RefreshCw,
  AlertCircle,
  Loader2,
  FileDown,
  Table,
  Atom,
  Trophy,
  Sparkles,
} from 'lucide-react';
import { DockingJobResult, DockingPose } from '@/types';
import { dockingApi, DockingApiError } from '@/lib/docking-api';

interface DockingResultsViewerProps {
  // Either provide a jobId to fetch, or a result object directly
  jobId?: string;
  result?: DockingJobResult;
  showVisualization?: boolean;
  onError?: (error: string) => void;
}

// Status colors for binding affinity quality
const getAffinityColor = (affinity: number): string => {
  if (affinity <= -9) return 'text-emerald-600'; // Excellent
  if (affinity <= -7) return 'text-green-600'; // Good
  if (affinity <= -5) return 'text-yellow-600'; // Moderate
  return 'text-orange-600'; // Weak
};

const getAffinityLabel = (affinity: number): string => {
  if (affinity <= -9) return 'Excellent';
  if (affinity <= -7) return 'Good';
  if (affinity <= -5) return 'Moderate';
  return 'Weak';
};

const getAffinityBgColor = (affinity: number): string => {
  if (affinity <= -9) return 'bg-emerald-100 border-emerald-300';
  if (affinity <= -7) return 'bg-green-100 border-green-300';
  if (affinity <= -5) return 'bg-yellow-100 border-yellow-300';
  return 'bg-orange-100 border-orange-300';
};

export default function DockingResultsViewer({ jobId, result: initialResult, showVisualization = true, onError }: DockingResultsViewerProps) {
  const [results, setResults] = useState<DockingJobResult | null>(initialResult || null);
  const [selectedPose, setSelectedPose] = useState<number>(1);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(!initialResult && !!jobId);
  const [error, setError] = useState<string | null>(null);
  const [showInteractions, setShowInteractions] = useState(true);
  const [showHBonds, setShowHBonds] = useState(true);
  const [showHydrophobic, setShowHydrophobic] = useState(true);
  const [isPoseDropdownOpen, setIsPoseDropdownOpen] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);

  // Derive the effective job ID
  const effectiveJobId = jobId || initialResult?.job_id || '';

  // Fetch results (only if not provided directly)
  const fetchResults = useCallback(async () => {
    // Skip fetching if we have initial results or no job ID
    if (initialResult || !effectiveJobId) {
      setIsLoading(false);
      return;
    }
    
    setIsLoading(true);
    setError(null);

    try {
      const data = await dockingApi.getJobResults(effectiveJobId);
      setResults(data);
      
      if (data.poses.length > 0) {
        setSelectedPose(1);
      }
    } catch (err) {
      const message = err instanceof DockingApiError 
        ? err.message 
        : 'Failed to load docking results';
      setError(message);
      onError?.(message);
    } finally {
      setIsLoading(false);
    }
  }, [effectiveJobId, initialResult, onError]);

  useEffect(() => {
    // If initial result provided, use it directly
    if (initialResult) {
      setResults(initialResult);
      if (initialResult.poses?.length > 0) {
        setSelectedPose(1);
      }
      setIsLoading(false);
    } else if (effectiveJobId) {
      fetchResults();
    }
  }, [initialResult, effectiveJobId, fetchResults]);

  // Get selected pose data
  const currentPose = useMemo(() => {
    if (!results) return null;
    return results.poses.find(p => p.pose_number === selectedPose) || null;
  }, [results, selectedPose]);

  // Best pose (lowest/most negative affinity)
  const bestPose = useMemo(() => {
    if (!results || results.poses.length === 0) return null;
    return results.poses.reduce((best, pose) => 
      pose.binding_affinity < best.binding_affinity ? pose : best
    );
  }, [results]);

  // Check if we have PDBQT structure data available
  const hasPdbqtData = useMemo(() => {
    return currentPose?.pdbqt_data && currentPose.pdbqt_data.length > 0;
  }, [currentPose]);

  // Handle PDBQT download - download the actual PDBQT data
  const handleDownloadPDBQT = useCallback(() => {
    if (!currentPose?.pdbqt_data) return;
    
    setIsDownloading(true);
    try {
      const blob = new Blob([currentPose.pdbqt_data], { type: 'chemical/x-pdbqt' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `docking_${effectiveJobId}_pose${selectedPose}.pdbqt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download failed:', err);
    } finally {
      setIsDownloading(false);
    }
  }, [currentPose, effectiveJobId, selectedPose]);

  // Handle CSV download
  const handleDownloadCSV = useCallback(() => {
    if (!results) return;
    
    // Generate CSV content
    const headers = ['Pose', 'Binding Affinity (kcal/mol)', 'RMSD Lower Bound', 'RMSD Upper Bound'];
    const rows = results.poses.map(pose => [
      pose.pose_number,
      pose.binding_affinity.toFixed(2),
      pose.rmsd_lb.toFixed(3),
      pose.rmsd_ub.toFixed(3),
    ]);
    
    const csvContent = [
      `# Docking Results for Job ${effectiveJobId}`,
      `# Candidate: ${results.candidate_id}`,
      `# Target: ${results.target_uniprot_id}`,
      `# Best Affinity: ${results.best_affinity?.toFixed(2)} kcal/mol`,
      '',
      headers.join(','),
      ...rows.map(row => row.join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `docking_${effectiveJobId}_results.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  }, [results, effectiveJobId]);

  // Loading state
  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
        <div className="flex flex-col items-center justify-center h-64">
          <Loader2 className="w-10 h-10 text-blue-500 animate-spin mb-4" />
          <p className="text-gray-600 font-medium">Loading docking results...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
        <div className="flex flex-col items-center justify-center h-64">
          <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mb-4">
            <AlertCircle className="w-8 h-8 text-red-500" />
          </div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Failed to Load Results</h3>
          <p className="text-gray-600 text-center mb-4">{error}</p>
          <button
            onClick={fetchResults}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      </div>
    );
  }

  // No results state
  if (!results) {
    return (
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm p-8">
        <div className="flex flex-col items-center justify-center h-64">
          <p className="text-gray-600">No results available</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-indigo-500 to-purple-500 rounded-xl flex items-center justify-center shadow-lg">
              <Atom className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">Docking Results</h3>
              <p className="text-sm text-gray-600 font-mono">Job: {effectiveJobId.slice(0, 8)}...</p>
            </div>
          </div>
          
          {/* Best Affinity Badge */}
          {bestPose && (
            <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border ${getAffinityBgColor(bestPose.binding_affinity)}`}>
              <Trophy className="w-4 h-4 text-amber-500" />
              <div>
                <p className="text-xs text-gray-600 font-medium">Best Affinity</p>
                <p className={`text-lg font-bold ${getAffinityColor(bestPose.binding_affinity)}`}>
                  {bestPose.binding_affinity.toFixed(2)} kcal/mol
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="p-6 space-y-6">
        {/* Controls Row */}
        <div className="flex flex-wrap items-center gap-4">
          {/* Pose Selector */}
          <div className="relative">
            <label className="block text-xs font-medium text-gray-500 mb-1">Select Pose</label>
            <button
              onClick={() => setIsPoseDropdownOpen(!isPoseDropdownOpen)}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:border-blue-400 transition-colors min-w-[160px]"
            >
              <span className="font-medium">
                Pose {selectedPose}
                {bestPose?.pose_number === selectedPose && (
                  <span className="ml-2 text-xs text-emerald-600">(Best)</span>
                )}
              </span>
              <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${isPoseDropdownOpen ? 'rotate-180' : ''}`} />
            </button>
            
            {isPoseDropdownOpen && (
              <div className="absolute top-full left-0 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg z-20 max-h-60 overflow-y-auto">
                {results.poses.map((pose) => (
                  <button
                    key={pose.pose_number}
                    onClick={() => {
                      setSelectedPose(pose.pose_number);
                      setIsPoseDropdownOpen(false);
                    }}
                    className={`w-full px-4 py-2 text-left hover:bg-gray-50 flex items-center justify-between ${
                      selectedPose === pose.pose_number ? 'bg-blue-50 text-blue-700' : ''
                    }`}
                  >
                    <span>Pose {pose.pose_number}</span>
                    <span className={`text-sm font-medium ${getAffinityColor(pose.binding_affinity)}`}>
                      {pose.binding_affinity.toFixed(2)}
                    </span>
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Interaction Toggles */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setShowInteractions(!showInteractions)}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
                showInteractions
                  ? 'bg-blue-50 border-blue-300 text-blue-700'
                  : 'bg-gray-50 border-gray-300 text-gray-600'
              }`}
              title="Toggle all interactions"
            >
              {showInteractions ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
              <span className="text-sm font-medium">Interactions</span>
            </button>
            
            {showInteractions && (
              <>
                <button
                  onClick={() => setShowHBonds(!showHBonds)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors ${
                    showHBonds
                      ? 'bg-cyan-50 border-cyan-300 text-cyan-700'
                      : 'bg-gray-50 border-gray-300 text-gray-600'
                  }`}
                  title="Toggle hydrogen bonds"
                >
                  <div className="w-3 h-0.5 bg-cyan-500 rounded" />
                  H-Bonds
                </button>
                
                <button
                  onClick={() => setShowHydrophobic(!showHydrophobic)}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-sm transition-colors ${
                    showHydrophobic
                      ? 'bg-amber-50 border-amber-300 text-amber-700'
                      : 'bg-gray-50 border-gray-300 text-gray-600'
                  }`}
                  title="Toggle hydrophobic contacts"
                >
                  <div className="w-3 h-3 bg-amber-400 rounded-full opacity-70" />
                  Hydrophobic
                </button>
              </>
            )}
          </div>

          {/* Expand Button */}
          <div className="flex-1" />
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
            title={isExpanded ? 'Collapse viewer' : 'Expand viewer'}
          >
            {isExpanded ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
          </button>
        </div>

        {/* 3D Structure Info Panel */}
        {showVisualization && (
          <div
            className={`relative bg-gradient-to-br from-gray-900 to-indigo-900 rounded-xl overflow-hidden border border-gray-300 transition-all duration-300 ${
              isExpanded ? 'h-[400px]' : 'h-[250px]'
            }`}
          >
            <div className="absolute inset-0 flex flex-col items-center justify-center text-gray-300">
              <Atom className="w-16 h-16 mb-4 opacity-70 text-indigo-400" />
              <p className="text-lg font-medium text-white">Ligand Pose #{selectedPose}</p>
              {hasPdbqtData ? (
                <>
                  <p className="text-sm mt-2 text-indigo-300">
                    PDBQT structure data available ({Math.round((currentPose?.pdbqt_data?.length || 0) / 1024)} KB)
                  </p>
                  <p className="text-xs mt-1 text-gray-400">
                    Download the PDBQT file to view in molecular visualization software
                  </p>
                  <button
                    onClick={handleDownloadPDBQT}
                    className="mt-4 flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition-colors"
                  >
                    <FileDown className="w-4 h-4" />
                    Download Pose #{selectedPose} PDBQT
                  </button>
                </>
              ) : (
                <p className="text-sm mt-2 text-gray-400">
                  Structure coordinates not available for this pose
                </p>
              )}
            </div>
            
            {/* Structure Info Badge */}
            {hasPdbqtData && (
              <div className="absolute top-4 right-4 bg-emerald-500/20 backdrop-blur-sm rounded-lg px-3 py-2 text-emerald-300 text-xs border border-emerald-500/30">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
                  <span>Structure Available</span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Selected Pose Info */}
        {currentPose && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className={`p-4 rounded-xl border ${getAffinityBgColor(currentPose.binding_affinity)}`}>
              <p className="text-xs font-medium text-gray-600 mb-1">Binding Affinity</p>
              <p className={`text-2xl font-bold ${getAffinityColor(currentPose.binding_affinity)}`}>
                {currentPose.binding_affinity.toFixed(2)}
              </p>
              <p className="text-xs text-gray-500 mt-1">kcal/mol • {getAffinityLabel(currentPose.binding_affinity)}</p>
            </div>
            
            <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
              <p className="text-xs font-medium text-gray-600 mb-1">RMSD (Lower Bound)</p>
              <p className="text-2xl font-bold text-gray-900">
                {currentPose.rmsd_lb.toFixed(3)}
              </p>
              <p className="text-xs text-gray-500 mt-1">Ångströms</p>
            </div>
            
            <div className="p-4 bg-gray-50 rounded-xl border border-gray-200">
              <p className="text-xs font-medium text-gray-600 mb-1">RMSD (Upper Bound)</p>
              <p className="text-2xl font-bold text-gray-900">
                {currentPose.rmsd_ub.toFixed(3)}
              </p>
              <p className="text-xs text-gray-500 mt-1">Ångströms</p>
            </div>
            
            <div className="p-4 bg-indigo-50 rounded-xl border border-indigo-200">
              <p className="text-xs font-medium text-gray-600 mb-1">Pose Rank</p>
              <p className="text-2xl font-bold text-indigo-600">
                #{currentPose.pose_number}
              </p>
              <p className="text-xs text-gray-500 mt-1">of {results.poses.length} poses</p>
            </div>
          </div>
        )}

        {/* Poses Table */}
        <div className="border border-gray-200 rounded-xl overflow-hidden">
          <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
            <div className="flex items-center gap-2">
              <Table className="w-4 h-4 text-gray-500" />
              <h4 className="font-semibold text-gray-900">All Binding Poses</h4>
              <span className="text-sm text-gray-500">({results.poses.length} poses)</span>
            </div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 text-xs text-gray-600 uppercase">
                <tr>
                  <th className="px-4 py-3 text-left">Pose</th>
                  <th className="px-4 py-3 text-left">Binding Affinity</th>
                  <th className="px-4 py-3 text-left">Quality</th>
                  <th className="px-4 py-3 text-left">RMSD (LB)</th>
                  <th className="px-4 py-3 text-left">RMSD (UB)</th>
                  <th className="px-4 py-3 text-left">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {results.poses.map((pose) => (
                  <tr
                    key={pose.pose_number}
                    className={`hover:bg-gray-50 transition-colors ${
                      selectedPose === pose.pose_number ? 'bg-blue-50' : ''
                    }`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">#{pose.pose_number}</span>
                        {bestPose?.pose_number === pose.pose_number && (
                          <span className="px-2 py-0.5 bg-amber-100 text-amber-700 text-xs font-medium rounded-full flex items-center gap-1">
                            <Trophy className="w-3 h-3" />
                            Best
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`font-bold ${getAffinityColor(pose.binding_affinity)}`}>
                        {pose.binding_affinity.toFixed(2)} kcal/mol
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${getAffinityBgColor(pose.binding_affinity)} ${getAffinityColor(pose.binding_affinity)}`}>
                        {getAffinityLabel(pose.binding_affinity)}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600">{pose.rmsd_lb.toFixed(3)} Å</td>
                    <td className="px-4 py-3 text-gray-600">{pose.rmsd_ub.toFixed(3)} Å</td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => setSelectedPose(pose.pose_number)}
                        className={`px-3 py-1 text-sm font-medium rounded-lg transition-colors ${
                          selectedPose === pose.pose_number
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {selectedPose === pose.pose_number ? 'Viewing' : 'View'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Download Section */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-200">
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <Sparkles className="w-4 h-4 text-indigo-500" />
            <span>Download results for offline analysis</span>
          </div>
          
          <div className="flex items-center gap-3">
            <button
              onClick={handleDownloadCSV}
              className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 hover:border-gray-400 transition-colors"
            >
              <Table className="w-4 h-4" />
              Download CSV
            </button>
            
            <button
              onClick={handleDownloadPDBQT}
              disabled={!hasPdbqtData || isDownloading}
              className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-lg hover:from-indigo-600 hover:to-purple-600 transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isDownloading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <FileDown className="w-4 h-4" />
              )}
              Download PDBQT
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
