'use client';

import { useState, useEffect } from 'react';
import { Maximize2, Minimize2, ExternalLink, Loader2, RotateCcw, Eye, Box, Download, ZoomIn, ZoomOut, Move3D } from 'lucide-react';

interface ProteinViewer3DProps {
  uniprotId: string;
  proteinName: string;
}

interface ProteinStructureResponse {
  uniprot_id: string;
  pdb_data: string;
  plddt_score: number;
  is_low_confidence: boolean;
  confidence_category: 'very_high' | 'high' | 'low' | 'very_low';
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export default function ProteinViewer3D({ uniprotId, proteinName }: ProteinViewer3DProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [plddtScore, setPlddtScore] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [structureStats, setStructureStats] = useState<{atoms: number, residues: number, chains: number} | null>(null);
  const [viewerKey, setViewerKey] = useState(0);
  const [pdbData, setPdbData] = useState<string | null>(null);

  useEffect(() => {
    const fetchProteinStructure = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch(`${API_BASE_URL}/api/protein/${uniprotId.toUpperCase()}/structure`);
        
        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('Protein structure not found in AlphaFold database');
          }
          throw new Error('Failed to fetch structure');
        }
        
        const data: ProteinStructureResponse = await response.json();
        
        if (data.pdb_data && data.pdb_data.includes('ATOM')) {
          setPdbData(data.pdb_data);
          setPlddtScore(data.plddt_score);
          
          // Parse structure stats from PDB
          const lines = data.pdb_data.split('\n');
          const atomLines = lines.filter(l => l.startsWith('ATOM') || l.startsWith('HETATM'));
          const residues = new Set(atomLines.map(l => l.substring(22, 27).trim()));
          const chains = new Set(atomLines.map(l => l.substring(21, 22).trim()));
          setStructureStats({
            atoms: atomLines.length,
            residues: residues.size,
            chains: chains.size
          });
        } else {
          throw new Error('Invalid structure data received');
        }
      } catch (err) {
        console.error("Protein structure fetch error:", err);
        setError(err instanceof Error ? err.message : 'Failed to load');
      } finally {
        setLoading(false);
      }
    };

    if (uniprotId) {
      fetchProteinStructure();
    }
  }, [uniprotId]);

  const resetViewer = () => {
    setViewerKey(prev => prev + 1);
  };

  const getConfidenceBadge = () => {
    if (!plddtScore) return null;
    if (plddtScore >= 90) return { label: 'Very High', color: 'bg-blue-600 text-white' };
    if (plddtScore >= 70) return { label: 'High', color: 'bg-cyan-500 text-white' };
    if (plddtScore >= 50) return { label: 'Low', color: 'bg-yellow-500 text-black' };
    return { label: 'Very Low', color: 'bg-orange-500 text-white' };
  };

  const downloadPdb = () => {
    if (!pdbData) return;
    const blob = new Blob([pdbData], { type: 'chemical/x-pdb' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${uniprotId}_alphafold.pdb`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Create enhanced 3Dmol.js viewer HTML
  const getViewerHtml = () => {
    if (!pdbData) return '';
    
    // Encode PDB data as base64 to avoid escaping issues
    const pdbBase64 = btoa(unescape(encodeURIComponent(pdbData)));
    
    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { width: 100%; height: 100%; overflow: hidden; background: #f8fafc; }
    #container { width: 100%; height: 100%; position: relative; }
    #viewer { width: 100%; height: 100%; }
    
    .controls {
      position: absolute;
      bottom: 16px;
      left: 50%;
      transform: translateX(-50%);
      display: flex;
      gap: 6px;
      padding: 8px 12px;
      background: rgba(255,255,255,0.98);
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.15);
      z-index: 100;
    }
    
    .btn {
      padding: 8px 14px;
      background: #f1f5f9;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      color: #475569;
      font-family: system-ui, sans-serif;
      transition: all 0.2s;
      display: flex;
      align-items: center;
      gap: 4px;
    }
    
    .btn:hover { background: #e2e8f0; transform: translateY(-1px); }
    .btn.active { background: #3b82f6; color: white; border-color: #3b82f6; }
    .btn.active:hover { background: #2563eb; }
    
    .btn-icon {
      padding: 8px;
      min-width: 36px;
      justify-content: center;
    }
    
    .legend {
      position: absolute;
      top: 12px;
      right: 12px;
      background: rgba(255,255,255,0.98);
      padding: 14px 16px;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.12);
      z-index: 100;
      font-family: system-ui, sans-serif;
    }
    
    .legend-title { 
      font-weight: 700; 
      color: #1e40af; 
      margin-bottom: 10px; 
      font-size: 12px;
      display: flex;
      align-items: center;
      gap: 6px;
    }
    
    .legend-item { 
      display: flex; 
      align-items: center; 
      gap: 10px; 
      margin-top: 6px; 
      color: #334155;
      font-size: 11px;
    }
    
    .legend-color { 
      width: 24px; 
      height: 12px; 
      border-radius: 3px;
      box-shadow: inset 0 1px 2px rgba(0,0,0,0.1);
    }
    
    .info-panel {
      position: absolute;
      top: 12px;
      left: 12px;
      background: rgba(255,255,255,0.98);
      padding: 12px 14px;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.12);
      z-index: 100;
      font-family: system-ui, sans-serif;
      min-width: 180px;
      display: none;
    }
    
    .info-title {
      font-weight: 700;
      color: #1e40af;
      font-size: 13px;
      margin-bottom: 8px;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 6px;
    }
    
    .info-row {
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: #475569;
      margin-top: 4px;
    }
    
    .info-value {
      font-weight: 600;
      color: #1e293b;
    }
    
    .info-plddt {
      margin-top: 8px;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      text-align: center;
    }
    
    .hover-tooltip {
      position: absolute;
      background: rgba(15,23,42,0.95);
      color: white;
      padding: 10px 14px;
      border-radius: 10px;
      font-size: 12px;
      font-family: system-ui, sans-serif;
      pointer-events: none;
      z-index: 200;
      display: none;
      max-width: 260px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }
    
    .hover-tooltip .res-name { 
      font-weight: 700; 
      color: #60a5fa;
      font-size: 13px;
    }
    
    .hover-tooltip .chain { color: #94a3b8; }
    
    .hover-tooltip .plddt-bar {
      margin-top: 8px;
      height: 6px;
      background: #334155;
      border-radius: 3px;
      overflow: hidden;
    }
    
    .hover-tooltip .plddt-fill {
      height: 100%;
      border-radius: 3px;
      transition: width 0.2s;
    }
    
    .loading {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      text-align: center;
      font-family: system-ui, sans-serif;
      color: #64748b;
    }
    
    .loading-spinner {
      width: 44px;
      height: 44px;
      border: 4px solid #e2e8f0;
      border-top-color: #3b82f6;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin: 0 auto 14px;
    }
    
    @keyframes spin { to { transform: rotate(360deg); } }
    
    .zoom-controls {
      position: absolute;
      right: 12px;
      bottom: 16px;
      display: flex;
      flex-direction: column;
      gap: 4px;
      z-index: 100;
    }
    
    .zoom-btn {
      width: 36px;
      height: 36px;
      background: rgba(255,255,255,0.98);
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
      color: #475569;
      transition: all 0.2s;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    .zoom-btn:hover { background: #f1f5f9; transform: scale(1.05); }
    .zoom-btn:active { transform: scale(0.95); }
  </style>
</head>
<body>
  <div id="container">
    <div id="viewer"></div>
    <div id="loading" class="loading">
      <div class="loading-spinner"></div>
      <div style="font-weight:600;">Rendering protein structure...</div>
    </div>
    
    <div id="hover-tooltip" class="hover-tooltip"></div>
    
    <div id="info-panel" class="info-panel">
      <div class="info-title">Selected Residue</div>
      <div id="info-content">Click a residue for details</div>
    </div>
    
    <div class="legend" id="legend" style="display:none;">
      <div class="legend-title">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"/>
          <path d="M12 16v-4M12 8h.01"/>
        </svg>
        pLDDT Confidence
      </div>
      <div class="legend-item">
        <span class="legend-color" style="background: #0053d6;"></span>
        Very high (&gt;90)
      </div>
      <div class="legend-item">
        <span class="legend-color" style="background: #65cbf3;"></span>
        Confident (70-90)
      </div>
      <div class="legend-item">
        <span class="legend-color" style="background: #ffdb13;"></span>
        Low (50-70)
      </div>
      <div class="legend-item">
        <span class="legend-color" style="background: #ff7d45;"></span>
        Very low (&lt;50)
      </div>
    </div>
    
    <div class="controls" id="controls" style="display:none;">
      <button class="btn active" id="btn-cartoon" onclick="setStyle('cartoon')">Cartoon</button>
      <button class="btn" id="btn-detailed" onclick="setStyle('detailed')">Detailed</button>
      <button class="btn" id="btn-atoms" onclick="setStyle('atoms')">All Atoms</button>
      <button class="btn" id="btn-surface" onclick="setStyle('surface')">Surface</button>
      <button class="btn" id="btn-spheres" onclick="setStyle('spheres')">Spheres</button>
      <button class="btn" onclick="toggleSpin()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 12a9 9 0 11-9-9"/>
        </svg>
        Spin
      </button>
      <button class="btn" onclick="resetView()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12a9 9 0 019-9 9.75 9.75 0 016.74 2.74L21 8"/>
          <path d="M21 3v5h-5"/>
          <path d="M21 12a9 9 0 01-9 9 9.75 9.75 0 01-6.74-2.74L3 16"/>
          <path d="M8 16H3v5"/>
        </svg>
        Reset
      </button>
    </div>
    
    <div class="zoom-controls" id="zoom-controls" style="display:none;">
      <button class="zoom-btn" onclick="zoomIn()" title="Zoom In">+</button>
      <button class="zoom-btn" onclick="zoomOut()" title="Zoom Out">−</button>
      <button class="zoom-btn" onclick="centerView()" title="Center">⊙</button>
    </div>
  </div>
  
  <script>
    var viewer = null;
    var currentStyle = 'cartoon';
    var spinning = false;
    var selectedAtom = null;
    
    // Amino acid full names
    var aaNames = {
      'ALA': 'Alanine', 'ARG': 'Arginine', 'ASN': 'Asparagine', 'ASP': 'Aspartic Acid',
      'CYS': 'Cysteine', 'GLN': 'Glutamine', 'GLU': 'Glutamic Acid', 'GLY': 'Glycine',
      'HIS': 'Histidine', 'ILE': 'Isoleucine', 'LEU': 'Leucine', 'LYS': 'Lysine',
      'MET': 'Methionine', 'PHE': 'Phenylalanine', 'PRO': 'Proline', 'SER': 'Serine',
      'THR': 'Threonine', 'TRP': 'Tryptophan', 'TYR': 'Tyrosine', 'VAL': 'Valine'
    };
    
    // Decode PDB from base64
    var pdbBase64 = "${pdbBase64}";
    var pdbData = decodeURIComponent(escape(atob(pdbBase64)));
    
    function getPlddtColor(bfactor) {
      if (bfactor >= 90) return '#0053d6';
      if (bfactor >= 70) return '#65cbf3';
      if (bfactor >= 50) return '#ffdb13';
      return '#ff7d45';
    }
    
    function getPlddtCategory(bfactor) {
      if (bfactor >= 90) return 'Very High';
      if (bfactor >= 70) return 'Confident';
      if (bfactor >= 50) return 'Low';
      return 'Very Low';
    }
    
    function init() {
      try {
        var element = document.getElementById('viewer');
        viewer = $3Dmol.createViewer(element, {
          backgroundColor: 0xf8fafc,
          antialias: true,
          disableFog: true
        });
        
        // Add model with all atoms including HETATM
        viewer.addModel(pdbData, "pdb", { keepH: true });
        
        // Apply initial style
        applyStyle();
        
        // Setup interactions
        setupHover();
        setupClick();
        
        // Center and zoom
        viewer.zoomTo();
        viewer.zoom(0.9);
        viewer.render();
        
        // Show UI
        document.getElementById('loading').style.display = 'none';
        document.getElementById('legend').style.display = 'block';
        document.getElementById('controls').style.display = 'flex';
        document.getElementById('zoom-controls').style.display = 'flex';
        
      } catch (e) {
        console.error('Viewer error:', e);
        document.getElementById('loading').innerHTML = 
          '<div style="color:#dc2626;font-weight:600;">Failed to load structure</div>' +
          '<div style="font-size:11px;margin-top:8px;color:#64748b;">' + e.message + '</div>';
      }
    }
    
    function setupHover() {
      var tooltip = document.getElementById('hover-tooltip');
      
      viewer.setHoverable({}, true,
        function(atom, viewer, event, container) {
          if (!atom) return;
          
          var plddt = atom.b || 0;
          var color = getPlddtColor(plddt);
          var category = getPlddtCategory(plddt);
          var resName = aaNames[atom.resn] || atom.resn;
          
          tooltip.innerHTML = 
            '<span class="res-name">' + resName + '</span> ' +
            '<span style="color:#94a3b8">' + atom.resi + '</span>' +
            '<span class="chain"> • Chain ' + (atom.chain || 'A') + '</span><br>' +
            '<span style="color:#94a3b8;font-size:11px;">Atom: ' + atom.atom + ' (' + atom.elem + ')</span>' +
            '<div style="margin-top:6px;font-size:11px;">' +
            '<span style="color:' + color + ';font-weight:600;">pLDDT: ' + plddt.toFixed(1) + '</span>' +
            ' <span style="color:#94a3b8;">(' + category + ')</span></div>' +
            '<div class="plddt-bar"><div class="plddt-fill" style="width:' + plddt + '%;background:' + color + '"></div></div>';
          
          tooltip.style.left = (event.offsetX + 16) + 'px';
          tooltip.style.top = (event.offsetY + 16) + 'px';
          tooltip.style.display = 'block';
        },
        function() {
          tooltip.style.display = 'none';
        }
      );
    }
    
    function setupClick() {
      var infoPanel = document.getElementById('info-panel');
      var infoContent = document.getElementById('info-content');
      
      viewer.setClickable({}, true, function(atom, viewer, event) {
        if (!atom) return;
        
        // Clear previous selection highlight
        applyStyle();
        
        selectedAtom = atom;
        var plddt = atom.b || 0;
        var color = getPlddtColor(plddt);
        var category = getPlddtCategory(plddt);
        var resName = aaNames[atom.resn] || atom.resn;
        
        // Show info panel
        infoPanel.style.display = 'block';
        infoContent.innerHTML = 
          '<div class="info-row"><span>Residue</span><span class="info-value">' + resName + '</span></div>' +
          '<div class="info-row"><span>Position</span><span class="info-value">' + atom.resi + '</span></div>' +
          '<div class="info-row"><span>Chain</span><span class="info-value">' + (atom.chain || 'A') + '</span></div>' +
          '<div class="info-row"><span>Atom</span><span class="info-value">' + atom.atom + ' (' + atom.elem + ')</span></div>' +
          '<div class="info-plddt" style="background:' + color + ';color:' + (plddt >= 50 && plddt < 70 ? '#000' : '#fff') + '">' +
          'pLDDT: ' + plddt.toFixed(1) + ' (' + category + ')</div>';
        
        // Highlight selected residue
        viewer.setStyle({resi: atom.resi, chain: atom.chain}, {
          cartoon: { color: '#ec4899' },
          stick: { radius: 0.25, color: '#ec4899' }
        });
        
        // Add label
        viewer.addLabel(atom.resn + ' ' + atom.resi, {
          position: atom,
          backgroundColor: 'rgba(236,72,153,0.9)',
          fontColor: 'white',
          fontSize: 12,
          borderRadius: 6,
          padding: 6,
          showBackground: true
        });
        
        viewer.render();
      });
    }
    
    function applyStyle() {
      if (!viewer) return;
      
      viewer.removeAllLabels();
      viewer.removeAllSurfaces();
      viewer.setStyle({}, {});
      
      // pLDDT color function
      var colorFunc = function(atom) {
        return getPlddtColor(atom.b);
      };
      
      // Main protein rendering based on style
      if (currentStyle === 'cartoon') {
        // Standard cartoon view
        viewer.setStyle({}, { 
          cartoon: { 
            colorfunc: colorFunc,
            thickness: 0.4,
            arrows: true,
            tubes: true
          }
        });
      } else if (currentStyle === 'detailed') {
        // AlphaFold-style: Cartoon with sidechain atoms visible
        viewer.setStyle({}, { 
          cartoon: { 
            colorfunc: colorFunc,
            thickness: 0.35,
            arrows: true,
            tubes: true
          },
          stick: {
            colorfunc: colorFunc,
            radius: 0.12,
            singleBonds: true
          }
        });
      } else if (currentStyle === 'atoms') {
        // Full atomic detail - all atoms as sticks with cartoon backbone
        viewer.setStyle({}, { 
          cartoon: { 
            colorfunc: colorFunc,
            thickness: 0.25,
            opacity: 0.7
          },
          stick: {
            colorfunc: colorFunc,
            radius: 0.15
          },
          sphere: {
            colorfunc: colorFunc,
            radius: 0.25
          }
        });
      } else if (currentStyle === 'surface') {
        viewer.setStyle({}, { 
          cartoon: { 
            colorfunc: colorFunc, 
            opacity: 0.15,
            thickness: 0.25
          },
          stick: {
            colorfunc: colorFunc,
            radius: 0.1
          }
        });
        viewer.addSurface($3Dmol.SurfaceType.MS, { 
          opacity: 0.88, 
          colorfunc: colorFunc 
        });
      } else if (currentStyle === 'spheres') {
        // Space-filling model
        viewer.setStyle({}, { 
          sphere: { 
            colorfunc: colorFunc
          }
        });
      }
      
      // Render heteroatoms/ligands with distinct style
      viewer.setStyle({hetflag: true}, {
        stick: { radius: 0.25, colorscheme: 'greenCarbon' },
        sphere: { radius: 0.4, colorscheme: 'greenCarbon' }
      });
      
      // Render nucleic acids if present
      viewer.setStyle({resn: ['A','C','G','T','U','DA','DC','DG','DT']}, {
        cartoon: {
          colorfunc: colorFunc,
          arrows: true
        },
        stick: {
          colorfunc: colorFunc,
          radius: 0.15
        }
      });
      
      viewer.render();
    }
    
    function setStyle(style) {
      currentStyle = style;
      ['cartoon', 'detailed', 'atoms', 'surface', 'spheres'].forEach(function(s) {
        var btn = document.getElementById('btn-' + s);
        if (btn) btn.classList.toggle('active', s === style);
      });
      applyStyle();
    }
    
    function toggleSpin() {
      spinning = !spinning;
      viewer.spin(spinning ? 'y' : false);
    }
    
    function resetView() {
      if (!viewer) return;
      spinning = false;
      viewer.spin(false);
      viewer.removeAllLabels();
      document.getElementById('info-panel').style.display = 'none';
      applyStyle();
      viewer.zoomTo();
      viewer.zoom(0.9);
      viewer.render();
    }
    
    function zoomIn() {
      if (!viewer) return;
      viewer.zoom(1.3, 300);
    }
    
    function zoomOut() {
      if (!viewer) return;
      viewer.zoom(0.7, 300);
    }
    
    function centerView() {
      if (!viewer) return;
      viewer.zoomTo();
      viewer.zoom(0.9, 300);
    }
    
    // Initialize when ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  </script>
</body>
</html>`;
  };

  const badge = getConfidenceBadge();

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-lg overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 bg-blue-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-600 rounded-lg">
              <Box className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-bold text-gray-900">Target Protein Structure</h3>
              <p className="text-sm text-gray-600 truncate max-w-md">{proteinName}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {badge && (
              <span className={`px-3 py-1.5 rounded-lg text-xs font-bold ${badge.color}`}>
                pLDDT: {plddtScore?.toFixed(1)} ({badge.label})
              </span>
            )}
            {pdbData && (
              <button
                onClick={downloadPdb}
                className="p-2 text-gray-500 hover:text-blue-600 hover:bg-white rounded-lg transition-all"
                title="Download PDB"
              >
                <Download className="w-4 h-4" />
              </button>
            )}
            <button
              onClick={resetViewer}
              className="p-2 text-gray-500 hover:text-blue-600 hover:bg-white rounded-lg transition-all"
              title="Reload viewer"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <a
              href={`https://alphafold.ebi.ac.uk/entry/${uniprotId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              AlphaFold
            </a>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-2 text-gray-500 hover:text-blue-600 hover:bg-white rounded-lg transition-all"
            >
              {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </div>
        </div>
        <div className="mt-2 flex items-center gap-4 text-xs text-gray-500">
          <span className="font-mono">UniProt: {uniprotId.toUpperCase()}</span>
          {structureStats && (
            <>
              <span>•</span>
              <span>{structureStats.atoms.toLocaleString()} atoms</span>
              <span>•</span>
              <span>{structureStats.residues} residues</span>
              <span>•</span>
              <span>{structureStats.chains} chain{structureStats.chains > 1 ? 's' : ''}</span>
            </>
          )}
        </div>
      </div>

      {/* Viewer */}
      <div className={`relative bg-slate-50 transition-all duration-300 ${isExpanded ? 'h-[700px]' : 'h-[520px]'}`}>
        {loading ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50">
            <Loader2 className="w-10 h-10 animate-spin text-blue-600 mb-3" />
            <span className="text-sm font-medium text-gray-600">Loading AlphaFold structure...</span>
            <span className="text-xs text-gray-400 mt-1">{uniprotId.toUpperCase()}</span>
          </div>
        ) : error ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-slate-50 p-6">
            <Eye className="w-12 h-12 text-gray-300 mb-3" />
            <span className="font-semibold text-gray-600 mb-1">Structure Not Available</span>
            <span className="text-sm text-gray-500 text-center mb-4">{error}</span>
            <a
              href={`https://alphafold.ebi.ac.uk/entry/${uniprotId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-blue-600 hover:underline flex items-center gap-1"
            >
              <ExternalLink className="w-4 h-4" />
              Check AlphaFold Database
            </a>
          </div>
        ) : (
          <iframe
            key={viewerKey}
            srcDoc={getViewerHtml()}
            className="w-full h-full border-0"
            title={`AlphaFold structure of ${proteinName}`}
            sandbox="allow-scripts allow-same-origin"
          />
        )}
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-100 bg-gray-50">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center gap-4">
            <span className="flex items-center gap-1.5">
              <Move3D className="w-3.5 h-3.5" />
              Drag to rotate
            </span>
            <span className="flex items-center gap-1.5">
              <ZoomIn className="w-3.5 h-3.5" />
              Scroll to zoom
            </span>
            <span>Click residue for details</span>
          </div>
          <span>Powered by 3Dmol.js • AlphaFold</span>
        </div>
      </div>
    </div>
  );
}
