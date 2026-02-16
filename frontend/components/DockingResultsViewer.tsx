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

  // Check if we have protein structure data
  const hasProteinData = useMemo(() => {
    return results?.protein_pdbqt && results.protein_pdbqt.length > 0;
  }, [results]);

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

  // Download the full protein-ligand complex
  const handleDownloadComplex = useCallback(() => {
    if (!currentPose?.pdbqt_data || !results?.protein_pdbqt) return;
    
    setIsDownloading(true);
    try {
      // Combine protein and ligand PDBQT data with clear separation
      const complexData = `REMARK  Protein-Ligand Docking Complex
REMARK  Job ID: ${effectiveJobId}
REMARK  Pose: ${selectedPose}
REMARK  Binding Affinity: ${currentPose.binding_affinity} kcal/mol
REMARK  ==================== PROTEIN ====================
${results.protein_pdbqt}
REMARK  ==================== LIGAND ====================
${currentPose.pdbqt_data}
END`;
      
      const blob = new Blob([complexData], { type: 'chemical/x-pdbqt' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `complex_${effectiveJobId}_pose${selectedPose}.pdbqt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Download complex failed:', err);
    } finally {
      setIsDownloading(false);
    }
  }, [currentPose, results, effectiveJobId, selectedPose]);

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
      <div className="bg-indigo-50 border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-indigo-600 rounded-xl flex items-center justify-center shadow-sm">
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

        {/* 3D Molecular Viewer with 3Dmol.js */}
        {showVisualization && (
          <div
            className={`relative bg-white rounded-xl overflow-hidden border border-gray-300 transition-all duration-300 ${
              isExpanded ? 'h-[600px]' : 'h-[450px]'
            }`}
          >
            {hasPdbqtData ? (
              <>
                <iframe
                  key={`pose-${selectedPose}-${effectiveJobId}-${hasProteinData}-${showHBonds}-${showHydrophobic}`}
                  srcDoc={(() => {
                    // Safely escape the data for embedding
                    const escapeForJs = (str: string | undefined) => {
                      if (!str) return '';
                      return str
                        .replace(/\\/g, '\\\\')
                        .replace(/`/g, '\\`')
                        .replace(/\$/g, '\\$')
                        .replace(/\r\n/g, '\\n')
                        .replace(/\n/g, '\\n');
                    };
                    
                    const proteinDataEscaped = escapeForJs(results?.protein_pdbqt);
                    const ligandDataEscaped = escapeForJs(currentPose?.pdbqt_data);
                    
                    return `
<!DOCTYPE html>
<html>
<head>
  <script src="https://3Dmol.csb.pitt.edu/build/3Dmol-min.js"><\/script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      font-family: system-ui, -apple-system, sans-serif;
      background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
      overflow: hidden; 
    }
    #viewer { width: 100%; height: 100vh; position: relative; }
    
    .controls-panel {
      position: absolute;
      bottom: 12px;
      left: 12px;
      right: 12px;
      z-index: 100;
      background: rgba(255,255,255,0.97);
      backdrop-filter: blur(10px);
      border-radius: 14px;
      padding: 14px 16px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.12);
      border: 1px solid rgba(255,255,255,0.8);
    }
    
    .controls-section {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 8px;
      margin-bottom: 10px;
    }
    
    .controls-section:last-child { margin-bottom: 0; }
    
    .section-label {
      font-size: 10px;
      font-weight: 700;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      min-width: 75px;
      padding-right: 8px;
      border-right: 2px solid #e2e8f0;
      margin-right: 8px;
    }
    
    .btn-group {
      display: flex;
      gap: 4px;
      flex-wrap: wrap;
    }
    
    .control-btn {
      padding: 6px 12px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      font-size: 11px;
      font-weight: 500;
      cursor: pointer;
      color: #475569;
      transition: all 0.15s ease;
      white-space: nowrap;
    }
    
    .control-btn:hover {
      background: #f1f5f9;
      border-color: #cbd5e1;
      color: #1e293b;
      transform: translateY(-1px);
    }
    
    .control-btn.active {
      background: #3b82f6;
      color: white;
      border-color: #3b82f6;
      box-shadow: 0 2px 8px rgba(59,130,246,0.3);
    }
    
    .control-btn.active-cyan {
      background: #06b6d4;
      color: white;
      border-color: #06b6d4;
    }
    
    .control-btn.active-amber {
      background: #f59e0b;
      color: white;
      border-color: #f59e0b;
    }
    
    .control-btn.active-green {
      background: #10b981;
      color: white;
      border-color: #10b981;
    }
    
    .info-badge {
      position: absolute;
      top: 12px;
      left: 12px;
      background: rgba(255,255,255,0.97);
      backdrop-filter: blur(10px);
      padding: 12px 16px;
      border-radius: 12px;
      font-size: 12px;
      border: 1px solid rgba(255,255,255,0.8);
      box-shadow: 0 4px 16px rgba(0,0,0,0.1);
      z-index: 100;
    }
    
    .pose-label {
      font-weight: 700;
      color: #1e293b;
      font-size: 14px;
    }
    
    .affinity {
      color: #059669;
      font-weight: 600;
      margin-left: 8px;
    }
    
    .legend {
      margin-top: 8px;
      font-size: 10px;
      color: #64748b;
    }
    
    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-top: 4px;
    }
    
    .legend-color {
      width: 12px;
      height: 12px;
      border-radius: 3px;
    }
    
    .legend-line {
      width: 16px;
      height: 3px;
      border-radius: 2px;
    }
    
    .status-badge {
      position: absolute;
      top: 12px;
      right: 12px;
      background: rgba(16,185,129,0.95);
      color: white;
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 10px;
      font-weight: 600;
      z-index: 100;
      box-shadow: 0 2px 8px rgba(16,185,129,0.3);
    }
  </style>
</head>
<body>
  <div id="viewer"></div>
  
  <div class="info-badge">
    <div>
      <span class="pose-label">Pose #${selectedPose}</span>
      <span class="affinity">${currentPose?.binding_affinity?.toFixed(2)} kcal/mol</span>
    </div>
    <div class="legend">
      <div class="legend-item"><span class="legend-color" style="background:linear-gradient(90deg,#818cf8,#3b82f6,#06b6d4)"></span> Protein</div>
      <div class="legend-item"><span class="legend-color" style="background:#10b981"></span> Ligand</div>
      <div class="legend-item"><span class="legend-line" style="background:#06b6d4"></span> H-Bonds</div>
      <div class="legend-item"><span class="legend-line" style="background:#f59e0b"></span> Hydrophobic</div>
    </div>
  </div>
  
  <div id="statusBadge" class="status-badge" style="display:none;">Protein Loaded</div>
  
  <div class="controls-panel">
    <div class="controls-section">
      <span class="section-label">Protein</span>
      <div class="btn-group">
        <button class="control-btn active" id="btn-cartoon" onclick="setProteinStyle('cartoon')">Cartoon</button>
        <button class="control-btn" id="btn-ribbon" onclick="setProteinStyle('ribbon')">Ribbon</button>
        <button class="control-btn" id="btn-surface" onclick="setProteinStyle('surface')">Surface</button>
        <button class="control-btn" id="btn-stick-p" onclick="setProteinStyle('stick')">Stick</button>
      </div>
    </div>
    
    <div class="controls-section">
      <span class="section-label">Ligand</span>
      <div class="btn-group">
        <button class="control-btn active-green" id="btn-stick-l" onclick="setLigandStyle('stick')">Stick</button>
        <button class="control-btn" id="btn-sphere-l" onclick="setLigandStyle('sphere')">Sphere</button>
        <button class="control-btn" id="btn-ballstick" onclick="setLigandStyle('ballstick')">Ball+Stick</button>
      </div>
    </div>
    
    <div class="controls-section">
      <span class="section-label">Interactions</span>
      <div class="btn-group">
        <button class="control-btn ${showHBonds ? 'active-cyan' : ''}" id="btn-hbonds" onclick="toggleHBonds()">H-Bonds</button>
        <button class="control-btn ${showHydrophobic ? 'active-amber' : ''}" id="btn-hydro" onclick="toggleHydrophobic()">Hydrophobic</button>
        <button class="control-btn" id="btn-binding" onclick="showBindingSite()">Binding Site</button>
      </div>
    </div>
    
    <div class="controls-section">
      <span class="section-label">View</span>
      <div class="btn-group">
        <button class="control-btn" onclick="resetView()">Reset</button>
        <button class="control-btn" onclick="zoomLigand()">Focus Ligand</button>
        <button class="control-btn" onclick="toggleSpin()">Spin</button>
      </div>
    </div>
  </div>
  
  <script>
    var viewer = $3Dmol.createViewer("viewer", {
      backgroundColor: 'white',
      antialias: true
    });
    
    var proteinData = \`${proteinDataEscaped}\`;
    var ligandData = \`${ligandDataEscaped}\`;
    
    var proteinModel = null;
    var ligandModel = null;
    var proteinStyle = 'cartoon';
    var ligandStyle = 'stick';
    var hbondsVisible = ${showHBonds};
    var hydrophobicVisible = ${showHydrophobic};
    var bindingSiteActive = false;
    var spinning = false;
    var surfaceObj = null;
    
    // Parse newlines back
    proteinData = proteinData.replace(/\\\\n/g, '\\n');
    ligandData = ligandData.replace(/\\\\n/g, '\\n');
    
    // Add protein model
    if (proteinData && proteinData.trim().length > 10) {
      try {
        proteinModel = viewer.addModel(proteinData, "pdbqt");
        viewer.setStyle({model: proteinModel}, {
          cartoon: { color: 'spectrum', opacity: 0.9 }
        });
        document.getElementById('statusBadge').style.display = 'block';
        setTimeout(function() {
          document.getElementById('statusBadge').style.display = 'none';
        }, 2000);
      } catch(e) {
        console.error('Protein load error:', e);
      }
    }
    
    // Add ligand model
    if (ligandData && ligandData.trim().length > 10) {
      try {
        ligandModel = viewer.addModel(ligandData, "pdbqt");
        viewer.setStyle({model: ligandModel}, {
          stick: { colorscheme: 'greenCarbon', radius: 0.2 }
        });
        // Highlight heteroatoms
        viewer.addStyle({model: ligandModel, elem: 'N'}, {sphere: {color: '#3b82f6', radius: 0.3}});
        viewer.addStyle({model: ligandModel, elem: 'O'}, {sphere: {color: '#ef4444', radius: 0.3}});
        viewer.addStyle({model: ligandModel, elem: 'S'}, {sphere: {color: '#eab308', radius: 0.35}});
        viewer.addStyle({model: ligandModel, elem: 'F'}, {sphere: {color: '#22c55e', radius: 0.25}});
        viewer.addStyle({model: ligandModel, elem: 'Cl'}, {sphere: {color: '#22c55e', radius: 0.4}});
        viewer.addStyle({model: ligandModel, elem: 'Br'}, {sphere: {color: '#a855f7', radius: 0.45}});
      } catch(e) {
        console.error('Ligand load error:', e);
      }
    }
    
    viewer.zoomTo();
    viewer.render();
    viewer.zoom(0.9, 500);
    
    // Show initial interactions
    if (hbondsVisible) showHBonds();
    if (hydrophobicVisible) showHydrophobicContacts();
    
    function setProteinStyle(style) {
      if (!proteinModel) return;
      proteinStyle = style;
      
      // Clear surface if exists
      if (surfaceObj) {
        viewer.removeSurface(surfaceObj);
        surfaceObj = null;
      }
      
      // Update button states
      ['cartoon', 'ribbon', 'surface', 'stick-p'].forEach(function(s) {
        var btn = document.getElementById('btn-' + s);
        if (btn) btn.classList.remove('active');
      });
      document.getElementById('btn-' + style).classList.add('active');
      
      if (style === 'cartoon') {
        viewer.setStyle({model: proteinModel}, {
          cartoon: { color: 'spectrum', opacity: 0.9 }
        });
      } else if (style === 'ribbon') {
        viewer.setStyle({model: proteinModel}, {
          ribbon: { color: 'spectrum', opacity: 0.9 }
        });
      } else if (style === 'surface') {
        viewer.setStyle({model: proteinModel}, {
          cartoon: { color: 'spectrum', opacity: 0.3 }
        });
        surfaceObj = viewer.addSurface($3Dmol.SurfaceType.MS, {
          opacity: 0.75,
          color: 'white'
        }, {model: proteinModel});
      } else if (style === 'stick-p') {
        viewer.setStyle({model: proteinModel}, {
          stick: { colorscheme: 'amino', radius: 0.12 }
        });
      }
      
      viewer.render();
    }
    
    function setLigandStyle(style) {
      if (!ligandModel) return;
      ligandStyle = style;
      
      // Update button states
      ['stick-l', 'sphere-l', 'ballstick'].forEach(function(s) {
        var btn = document.getElementById('btn-' + s);
        if (btn) {
          btn.classList.remove('active-green');
          btn.classList.remove('active');
        }
      });
      
      var btnId = style === 'stick' ? 'btn-stick-l' : (style === 'sphere' ? 'btn-sphere-l' : 'btn-ballstick');
      document.getElementById(btnId).classList.add('active-green');
      
      if (style === 'stick') {
        viewer.setStyle({model: ligandModel}, {
          stick: { colorscheme: 'greenCarbon', radius: 0.2 }
        });
        viewer.addStyle({model: ligandModel, elem: 'N'}, {sphere: {color: '#3b82f6', radius: 0.3}});
        viewer.addStyle({model: ligandModel, elem: 'O'}, {sphere: {color: '#ef4444', radius: 0.3}});
      } else if (style === 'sphere') {
        viewer.setStyle({model: ligandModel}, {
          sphere: { colorscheme: 'greenCarbon', scale: 0.4 }
        });
      } else if (style === 'ballstick') {
        viewer.setStyle({model: ligandModel}, {
          stick: { colorscheme: 'greenCarbon', radius: 0.15 },
          sphere: { colorscheme: 'greenCarbon', scale: 0.25 }
        });
      }
      
      viewer.render();
    }
    
    function toggleHBonds() {
      hbondsVisible = !hbondsVisible;
      var btn = document.getElementById('btn-hbonds');
      if (hbondsVisible) {
        btn.classList.add('active-cyan');
        showHBonds();
      } else {
        btn.classList.remove('active-cyan');
        // Remove H-bond visualizations
        viewer.removeAllShapes();
        if (hydrophobicVisible) showHydrophobicContacts();
      }
    }
    
    function showHBonds() {
      if (!proteinModel || !ligandModel) return;
      
      // Get atoms that can form H-bonds (N, O donors/acceptors)
      var proteinAtoms = viewer.getModel(proteinModel).selectedAtoms({elem: ['N', 'O']});
      var ligandAtoms = viewer.getModel(ligandModel).selectedAtoms({elem: ['N', 'O']});
      
      // Find potential H-bonds (distance < 3.5 Angstroms)
      for (var i = 0; i < ligandAtoms.length; i++) {
        for (var j = 0; j < proteinAtoms.length; j++) {
          var la = ligandAtoms[i];
          var pa = proteinAtoms[j];
          var dist = Math.sqrt(
            Math.pow(la.x - pa.x, 2) + 
            Math.pow(la.y - pa.y, 2) + 
            Math.pow(la.z - pa.z, 2)
          );
          if (dist < 3.5 && dist > 1.5) {
            viewer.addCylinder({
              start: {x: la.x, y: la.y, z: la.z},
              end: {x: pa.x, y: pa.y, z: pa.z},
              radius: 0.08,
              color: '#06b6d4',
              dashed: true,
              dashLength: 0.2,
              gapLength: 0.1
            });
          }
        }
      }
      viewer.render();
    }
    
    function toggleHydrophobic() {
      hydrophobicVisible = !hydrophobicVisible;
      var btn = document.getElementById('btn-hydro');
      if (hydrophobicVisible) {
        btn.classList.add('active-amber');
        showHydrophobicContacts();
      } else {
        btn.classList.remove('active-amber');
        viewer.removeAllShapes();
        if (hbondsVisible) showHBonds();
      }
    }
    
    function showHydrophobicContacts() {
      if (!proteinModel || !ligandModel) return;
      
      // Get hydrophobic atoms (C atoms)
      var proteinAtoms = viewer.getModel(proteinModel).selectedAtoms({elem: 'C'});
      var ligandAtoms = viewer.getModel(ligandModel).selectedAtoms({elem: 'C'});
      
      // Find hydrophobic contacts (3.5-4.5 Angstroms)
      for (var i = 0; i < ligandAtoms.length; i++) {
        for (var j = 0; j < proteinAtoms.length; j++) {
          var la = ligandAtoms[i];
          var pa = proteinAtoms[j];
          var dist = Math.sqrt(
            Math.pow(la.x - pa.x, 2) + 
            Math.pow(la.y - pa.y, 2) + 
            Math.pow(la.z - pa.z, 2)
          );
          if (dist < 4.5 && dist > 3.0) {
            viewer.addCylinder({
              start: {x: la.x, y: la.y, z: la.z},
              end: {x: pa.x, y: pa.y, z: pa.z},
              radius: 0.05,
              color: '#f59e0b',
              opacity: 0.6
            });
          }
        }
      }
      viewer.render();
    }
    
    function showBindingSite() {
      bindingSiteActive = !bindingSiteActive;
      var btn = document.getElementById('btn-binding');
      
      if (bindingSiteActive) {
        btn.classList.add('active');
        if (proteinModel && ligandModel) {
          // Show residues within 5A of ligand
          viewer.setStyle({model: proteinModel}, {});
          viewer.setStyle(
            {model: proteinModel, byres: true, within: {distance: 5, sel: {model: ligandModel}}},
            {
              stick: { colorscheme: 'amino', radius: 0.15 },
              cartoon: { color: 'spectrum', opacity: 0.3 }
            }
          );
          viewer.zoomTo({model: ligandModel});
          viewer.zoom(0.7, 500);
        }
      } else {
        btn.classList.remove('active');
        setProteinStyle(proteinStyle);
        resetView();
      }
      viewer.render();
    }
    
    function resetView() {
      viewer.zoomTo();
      viewer.zoom(0.9, 500);
    }
    
    function zoomLigand() {
      if (ligandModel) {
        viewer.zoomTo({model: ligandModel});
        viewer.zoom(0.7, 500);
      }
    }
    
    function toggleSpin() {
      spinning = !spinning;
      if (spinning) {
        viewer.spin('y', 1);
      } else {
        viewer.spin(false);
      }
    }
  <\/script>
</body>
</html>`;
                  })()}
                  className="w-full h-full border-0"
                  title={`3D structure of protein-ligand complex pose ${selectedPose}`}
                  sandbox="allow-scripts allow-same-origin"
                />
                
                {/* Download button overlay */}
                <div className="absolute top-3 right-3 z-10 flex flex-col gap-2">
                  <button
                    onClick={handleDownloadPDBQT}
                    className="flex items-center gap-2 px-3 py-2 bg-white/95 backdrop-blur border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium shadow-sm"
                    title="Download ligand pose only"
                  >
                    <FileDown className="w-4 h-4" />
                    Ligand PDBQT
                  </button>
                  {hasProteinData && (
                    <button
                      onClick={handleDownloadComplex}
                      className="flex items-center gap-2 px-3 py-2 bg-blue-500 backdrop-blur border border-blue-600 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm font-medium shadow-sm"
                      title="Download protein-ligand complex"
                    >
                      <FileDown className="w-4 h-4" />
                      Complex PDBQT
                    </button>
                  )}
                </div>
              </>
            ) : (
              <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50">
                <Atom className="w-16 h-16 mb-4 text-gray-300" />
                <p className="text-lg font-medium text-gray-600">Ligand Pose #{selectedPose}</p>
                <p className="text-sm mt-2 text-gray-400">
                  Structure coordinates not available for this pose
                </p>
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

        {/* Console Output / Execution Log */}
        {results.console_output && (
          <div className="border border-gray-200 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 bg-gray-800 text-white">
              <div className="flex items-center gap-2">
                <Table className="w-4 h-4" />
                <span className="text-sm font-medium">Execution Log</span>
              </div>
              {results.execution_time_seconds && (
                <span className="text-xs text-gray-400">
                  Completed in {results.execution_time_seconds.toFixed(1)}s
                </span>
              )}
            </div>
            <pre className="bg-gray-900 text-green-400 p-4 text-xs font-mono overflow-x-auto max-h-48 overflow-y-auto whitespace-pre-wrap">
              {results.console_output}
            </pre>
          </div>
        )}

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
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
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
