'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Maximize2,
  Minimize2,
  Download,
  RefreshCw,
  AlertCircle,
  Loader2,
  FileDown,
  Atom,
  Trophy,
  Grid3x3,
  List,
  Info,
} from 'lucide-react';
import { DockingJobResult } from '@/types';
import { dockingApi, DockingApiError } from '@/lib/docking-api';
import DockingPoseCard from './DockingPoseCard';
import DockingResultsAnalysis from './DockingResultsAnalysis';

interface IndustryDockingViewerProps {
  jobId?: string;
  result?: DockingJobResult;
  onError?: (error: string) => void;
}

export default function IndustryDockingViewer({
  jobId,
  result: initialResult,
  onError,
}: IndustryDockingViewerProps) {
  const [results, setResults] = useState<DockingJobResult | null>(initialResult || null);
  const [selectedPose, setSelectedPose] = useState<number>(1);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(!initialResult && !!jobId);
  const [error, setError] = useState<string | null>(null);
  const [viewerKey, setViewerKey] = useState(0);

  const effectiveJobId = jobId || initialResult?.job_id || '';

  // Fetch results
  const fetchResults = useCallback(async () => {
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
      const message =
        err instanceof DockingApiError ? err.message : 'Failed to load docking results';
      setError(message);
      onError?.(message);
    } finally {
      setIsLoading(false);
    }
  }, [effectiveJobId, initialResult, onError]);

  useEffect(() => {
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

  // Force viewer refresh when pose changes
  useEffect(() => {
    setViewerKey((prev) => prev + 1);
  }, [selectedPose]);

  // Get selected pose data
  const currentPose = useMemo(() => {
    if (!results) return null;
    return results.poses.find((p) => p.pose_number === selectedPose) || null;
  }, [results, selectedPose]);

  // Sorted poses by affinity
  const sortedPoses = useMemo(() => {
    if (!results) return [];
    return [...results.poses].sort((a, b) => a.binding_affinity - b.binding_affinity);
  }, [results]);

  // Best pose
  const bestPose = sortedPoses[0];

  // Check if we have structure data
  const hasPdbqtData = useMemo(() => {
    return currentPose?.pdbqt_data && currentPose.pdbqt_data.length > 0;
  }, [currentPose]);

  const hasProteinData = useMemo(() => {
    return results?.protein_pdbqt && results.protein_pdbqt.length > 0;
  }, [results]);

  // Download handler
  const handleDownloadComplex = useCallback(() => {
    if (!currentPose?.pdbqt_data || !results?.protein_pdbqt) return;

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
  }, [currentPose, results, effectiveJobId, selectedPose]);

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

  // Generate viewer HTML
  const generateViewerHTML = () => {
    if (!currentPose) return '';

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
    const ligandDataEscaped = escapeForJs(currentPose.pdbqt_data);
    const hasProtein = proteinDataEscaped && proteinDataEscaped.length > 100;
    const hasLigand = ligandDataEscaped && ligandDataEscaped.length > 100;

    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <script src="https://3Dmol.csb.pitt.edu/build/3Dmol-min.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { 
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); 
      overflow: hidden; 
    }
    #viewer { width: 100%; height: 100vh; position: relative; }
    .info { position: absolute; top: 16px; left: 16px; background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); padding: 14px 20px; border-radius: 12px; font-size: 13px; border: 1px solid rgba(226,232,240,0.8); box-shadow: 0 4px 20px rgba(0,0,0,0.12); z-index: 1000; }
    .pose-label { font-weight: 700; color: #1e293b; font-size: 16px; display: block; margin-bottom: 6px; }
    .affinity { color: ${currentPose.binding_affinity <= -9 ? '#059669' : currentPose.binding_affinity <= -7 ? '#16a34a' : currentPose.binding_affinity <= -5 ? '#ca8a04' : '#ea580c'}; font-weight: 600; font-size: 14px; }
    .controls { position: absolute; bottom: 16px; left: 16px; background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); padding: 12px; border-radius: 12px; border: 1px solid rgba(226,232,240,0.8); box-shadow: 0 4px 20px rgba(0,0,0,0.12); z-index: 1000; display: flex; gap: 8px; }
    .btn { padding: 8px 14px; background: white; border: 1px solid #e2e8f0; border-radius: 8px; font-size: 12px; font-weight: 500; cursor: pointer; color: #475569; transition: all 0.2s; }
    .btn:hover { background: #f1f5f9; border-color: #cbd5e1; transform: translateY(-1px); }
    .btn.active { background: #3b82f6; color: white; border-color: #3b82f6; }
    .legend { position: absolute; bottom: 16px; right: 16px; background: rgba(255,255,255,0.95); backdrop-filter: blur(10px); padding: 12px 14px; border-radius: 10px; font-size: 11px; border: 1px solid rgba(226,232,240,0.8); box-shadow: 0 4px 20px rgba(0,0,0,0.12); z-index: 1000; }
    .legend-item { display: flex; align-items: center; gap: 8px; margin: 5px 0; color: #475569; font-weight: 500; }
    .legend-color { width: 16px; height: 16px; border-radius: 4px; border: 1px solid rgba(0,0,0,0.1); }
    .debug { position: absolute; top: 16px; right: 16px; background: rgba(0,0,0,0.8); color: #10b981; padding: 12px; border-radius: 8px; font-family: monospace; font-size: 11px; max-width: 300px; z-index: 1000; }
  </style>
</head>
<body>
  <div id="viewer"></div>
  <div class="info">
    <span class="pose-label">Pose #${currentPose.pose_number}</span>
    <span class="affinity">${currentPose.binding_affinity.toFixed(2)} kcal/mol</span>
  </div>
  <div class="controls">
    <button class="btn active" id="btn-full" onclick="showFullComplex()">Full Complex</button>
    <button class="btn" id="btn-binding" onclick="showBindingSite()">Binding Site</button>
    <button class="btn" id="btn-ligand" onclick="focusLigand()">Focus Ligand</button>
    <button class="btn" id="btn-reset" onclick="resetView()">Reset</button>
  </div>
  <div class="legend">
    <div class="legend-item"><div class="legend-color" style="background: linear-gradient(90deg, #818cf8, #3b82f6);"></div><span>Protein</span></div>
    <div class="legend-item"><div class="legend-color" style="background: #10b981;"></div><span>Ligand (C)</span></div>
    <div class="legend-item"><div class="legend-color" style="background: #3b82f6;"></div><span>Nitrogen</span></div>
    <div class="legend-item"><div class="legend-color" style="background: #ef4444;"></div><span>Oxygen</span></div>
    <div class="legend-item"><div class="legend-color" style="background: #eab308;"></div><span>Sulfur</span></div>
  </div>
  <div class="debug" id="debug">
    <div>Pose: #${currentPose.pose_number}</div>
    <div>Protein: ${hasProtein ? 'LOADED (' + proteinDataEscaped.length + ' chars)' : 'NOT LOADED'}</div>
    <div>Ligand: ${hasLigand ? 'LOADED (' + ligandDataEscaped.length + ' chars)' : 'NOT LOADED'}</div>
  </div>
  <script>
    var viewer = $3Dmol.createViewer("viewer", { backgroundColor: 'white', antialias: true });
    var proteinData = \`${proteinDataEscaped}\`.replace(/\\\\\\\\n/g, '\\n');
    var ligandData = \`${ligandDataEscaped}\`.replace(/\\\\\\\\n/g, '\\n');
    var proteinModel = null;
    var ligandModel = null;
    
    console.log('=== DOCKING VIEWER DEBUG ===');
    console.log('Pose:', ${currentPose.pose_number});
    console.log('Protein data length:', proteinData.length);
    console.log('Ligand data length:', ligandData.length);
    console.log('Has protein:', ${hasProtein});
    console.log('Has ligand:', ${hasLigand});
    
    if (proteinData && proteinData.trim().length > 10) {
      try {
        proteinModel = viewer.addModel(proteinData, "pdbqt");
        viewer.setStyle({model: proteinModel}, { cartoon: { color: 'spectrum', opacity: 0.8, thickness: 0.6 } });
        console.log('✓ Protein loaded');
      } catch(e) { console.error('✗ Protein error:', e); }
    }
    
    if (ligandData && ligandData.trim().length > 10) {
      try {
        ligandModel = viewer.addModel(ligandData, "pdbqt");
        viewer.setStyle({model: ligandModel}, { stick: { colorscheme: 'greenCarbon', radius: 0.3 } });
        viewer.addStyle({model: ligandModel, elem: 'N'}, {sphere: {color: '#3b82f6', radius: 0.4}});
        viewer.addStyle({model: ligandModel, elem: 'O'}, {sphere: {color: '#ef4444', radius: 0.4}});
        viewer.addStyle({model: ligandModel, elem: 'S'}, {sphere: {color: '#eab308', radius: 0.45}});
        console.log('✓ Ligand loaded');
      } catch(e) { console.error('✗ Ligand error:', e); }
    }
    
    viewer.render();
    if (proteinModel !== null && ligandModel !== null) {
      viewer.zoomTo();
      viewer.zoom(1.0, 1000);
      console.log('✓ Showing full complex');
    } else if (ligandModel !== null) {
      viewer.zoomTo({model: ligandModel});
      viewer.zoom(0.8, 1000);
      console.log('⚠ Ligand only');
    }
    
    setTimeout(function() { viewer.rotate(20, {x:0, y:1, z:0}, 500); viewer.render(); }, 1200);
    setTimeout(function() { document.getElementById('debug').style.display = 'none'; }, 5000);
    
    function showFullComplex() {
      updateButtons('btn-full');
      if (proteinModel) viewer.setStyle({model: proteinModel}, { cartoon: { color: 'spectrum', opacity: 0.8, thickness: 0.6 } });
      viewer.zoomTo();
      viewer.zoom(1.0, 800);
      viewer.render();
    }
    
    function showBindingSite() {
      updateButtons('btn-binding');
      if (proteinModel && ligandModel) {
        viewer.setStyle({model: proteinModel}, {});
        viewer.setStyle({model: proteinModel, byres: true, within: {distance: 5, sel: {model: ligandModel}}}, { stick: { colorscheme: 'amino', radius: 0.2 }, cartoon: { color: 'spectrum', opacity: 0.5 } });
        viewer.zoomTo({model: ligandModel});
        viewer.zoom(0.7, 800);
        viewer.render();
      }
    }
    
    function focusLigand() {
      updateButtons('btn-ligand');
      if (ligandModel) { viewer.zoomTo({model: ligandModel}); viewer.zoom(0.6, 800); viewer.render(); }
    }
    
    function resetView() { showFullComplex(); }
    
    function updateButtons(activeId) {
      ['btn-full', 'btn-binding', 'btn-ligand'].forEach(function(id) {
        var btn = document.getElementById(id);
        if (btn) btn.classList.toggle('active', id === activeId);
      });
    }
  </script>
</body>
</html>`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-2xl border border-indigo-200 p-6">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-indigo-600 rounded-xl flex items-center justify-center shadow-lg">
              <Atom className="w-7 h-7 text-white" />
            </div>
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Docking Results</h2>
              <p className="text-sm text-gray-600 font-mono mt-1">Job: {effectiveJobId.slice(0, 12)}...</p>
            </div>
          </div>

          {bestPose && (
            <div className="bg-white rounded-xl border border-indigo-300 px-6 py-3 shadow-sm">
              <div className="flex items-center gap-3">
                <Trophy className="w-5 h-5 text-amber-500" />
                <div>
                  <p className="text-xs text-gray-600 font-medium">Best Affinity</p>
                  <p className="text-2xl font-bold text-emerald-600">
                    {bestPose.binding_affinity.toFixed(2)}
                  </p>
                  <p className="text-xs text-gray-500">kcal/mol</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Debug Info */}
      {results && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
            <div className="text-sm text-blue-900">
              <p className="font-semibold mb-1">Data Status:</p>
              <p>Protein structure: {hasProteinData ? `✓ Loaded (${results.protein_pdbqt?.length} chars)` : '✗ Not available'}</p>
              <p>Ligand poses: ✓ {results.poses.length} poses loaded</p>
              <p className="mt-2 text-xs text-blue-700">
                Open browser console (F12) for detailed debugging information
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Analysis Section */}
      <div className="bg-white rounded-2xl border border-gray-200 p-6">
        <DockingResultsAnalysis results={results} />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Pose Selection */}
        <div className="lg:col-span-1 space-y-4">
          <h3 className="text-lg font-bold text-gray-900">Binding Poses</h3>
          <div className="space-y-3 max-h-[800px] overflow-y-auto pr-2">
            {sortedPoses.map((pose, index) => (
              <DockingPoseCard
                key={pose.pose_number}
                pose={pose}
                isBest={index === 0}
                isSelected={selectedPose === pose.pose_number}
                onSelect={() => setSelectedPose(pose.pose_number)}
                rank={index + 1}
              />
            ))}
          </div>
        </div>

        {/* Right: 3D Viewer */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
            {/* Viewer Header */}
            <div className="bg-gray-50 border-b border-gray-200 px-4 py-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <h4 className="font-semibold text-gray-900">3D Structure Viewer</h4>
                  <span className="px-2 py-1 bg-indigo-100 text-indigo-700 text-xs font-medium rounded-full">
                    Pose #{selectedPose}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {hasProteinData && hasPdbqtData && (
                    <button
                      onClick={handleDownloadComplex}
                      className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm"
                    >
                      <FileDown className="w-4 h-4" />
                      Download
                    </button>
                  )}
                  <button
                    onClick={() => setIsExpanded(!isExpanded)}
                    className="p-2 text-gray-600 hover:bg-gray-200 rounded-lg transition-colors"
                    title={isExpanded ? 'Minimize' : 'Maximize'}
                  >
                    {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                  </button>
                </div>
              </div>
            </div>

            {/* 3D Viewer */}
            <div
              className={`relative bg-gradient-to-br from-gray-50 to-gray-100 transition-all duration-300 ${
                isExpanded ? 'h-[700px]' : 'h-[500px]'
              }`}
            >
              {hasPdbqtData && currentPose ? (
                <iframe
                  key={`viewer-${viewerKey}-pose-${currentPose.pose_number}`}
                  srcDoc={generateViewerHTML()}
                  className="w-full h-full border-0"
                  title={`3D structure of pose ${currentPose.pose_number}`}
                  sandbox="allow-scripts allow-same-origin"
                />
              ) : (
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <Atom className="w-16 h-16 mb-4 text-gray-300" />
                  <p className="text-lg font-medium text-gray-600">No structure data available</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
