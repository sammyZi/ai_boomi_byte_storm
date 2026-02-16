'use client';

import { useState, useEffect } from 'react';
import { Maximize2, Minimize2, FlaskConical, RotateCcw, Eye, AlertCircle } from 'lucide-react';

interface MoleculeViewer3DProps {
  smiles: string;
  moleculeName: string;
}

export default function MoleculeViewer3D({ smiles, moleculeName }: MoleculeViewer3DProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [viewerKey, setViewerKey] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const resetViewer = () => {
    setViewerKey(prev => prev + 1);
    setLoading(true);
    setError(null);
  };

  // Generate viewer HTML with multiple representation options
  const getViewerHtml = () => {
    const encodedSmiles = encodeURIComponent(smiles);
    
    return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <script src="https://3Dmol.org/build/3Dmol-min.js"></script>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    html, body { width: 100%; height: 100%; overflow: hidden; background: #fafafa; }
    #container { width: 100%; height: 100%; position: relative; }
    #viewer { width: 100%; height: 100%; }
    
    .toolbar {
      position: absolute;
      bottom: 12px;
      left: 50%;
      transform: translateX(-50%);
      display: flex;
      gap: 4px;
      padding: 6px 10px;
      background: rgba(255,255,255,0.95);
      backdrop-filter: blur(8px);
      border-radius: 10px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.12);
      z-index: 100;
    }
    
    .btn {
      padding: 6px 12px;
      background: #f1f5f9;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 11px;
      font-weight: 600;
      cursor: pointer;
      color: #475569;
      font-family: system-ui, sans-serif;
      transition: all 0.15s;
    }
    
    .btn:hover { background: #e2e8f0; }
    .btn.active { background: #0d9488; color: white; border-color: #0d9488; }
    
    .info-badge {
      position: absolute;
      top: 10px;
      left: 10px;
      background: rgba(255,255,255,0.95);
      backdrop-filter: blur(8px);
      padding: 8px 12px;
      border-radius: 8px;
      font-size: 11px;
      font-weight: 600;
      color: #0d9488;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      z-index: 100;
      font-family: system-ui, sans-serif;
    }
    
    .legend {
      position: absolute;
      top: 10px;
      right: 10px;
      background: rgba(255,255,255,0.95);
      backdrop-filter: blur(8px);
      padding: 10px 12px;
      border-radius: 8px;
      font-size: 10px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
      z-index: 100;
      font-family: system-ui, sans-serif;
    }
    
    .legend-title { font-weight: 700; color: #0d9488; margin-bottom: 6px; font-size: 11px; }
    .legend-item { display: flex; align-items: center; gap: 6px; margin-top: 4px; color: #334155; }
    .legend-color { width: 12px; height: 12px; border-radius: 50%; border: 1px solid rgba(0,0,0,0.1); }
    
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
      width: 36px;
      height: 36px;
      border: 3px solid #e2e8f0;
      border-top-color: #0d9488;
      border-radius: 50%;
      animation: spin 1s linear infinite;
      margin: 0 auto 10px;
    }
    
    @keyframes spin { to { transform: rotate(360deg); } }
  </style>
</head>
<body>
  <div id="container">
    <div id="viewer"></div>
    <div id="loading" class="loading">
      <div class="loading-spinner"></div>
      <div>Loading molecule...</div>
    </div>
    
    <div class="info-badge" id="info" style="display:none;">
      Drug Molecule
    </div>
    
    <div class="legend" id="legend" style="display:none;">
      <div class="legend-title">Element Colors</div>
      <div class="legend-item"><span class="legend-color" style="background:#909090"></span>Carbon (C)</div>
      <div class="legend-item"><span class="legend-color" style="background:#3050F8"></span>Nitrogen (N)</div>
      <div class="legend-item"><span class="legend-color" style="background:#FF0D0D"></span>Oxygen (O)</div>
      <div class="legend-item"><span class="legend-color" style="background:#FFFF30"></span>Sulfur (S)</div>
      <div class="legend-item"><span class="legend-color" style="background:#FFFFFF; border-color:#ccc"></span>Hydrogen (H)</div>
    </div>
    
    <div class="toolbar" id="toolbar" style="display:none;">
      <button class="btn active" id="btn-ball" onclick="setStyle('ball')">Ball & Stick</button>
      <button class="btn" id="btn-stick" onclick="setStyle('stick')">Sticks</button>
      <button class="btn" id="btn-sphere" onclick="setStyle('sphere')">Spheres</button>
      <button class="btn" id="btn-surface" onclick="setStyle('surface')">Surface</button>
      <button class="btn" onclick="resetView()">Reset</button>
      <button class="btn" onclick="toggleSpin()">Spin</button>
    </div>
  </div>
  
  <script>
    var viewer = null;
    var currentStyle = 'ball';
    var spinning = false;
    
    function init() {
      var element = document.getElementById('viewer');
      viewer = $3Dmol.createViewer(element, {
        backgroundColor: 0xfafafa,
        antialias: true
      });
      
      loadMolecule();
    }
    
    function loadMolecule() {
      var smiles = decodeURIComponent('${encodedSmiles}');
      
      function showSuccess() {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('toolbar').style.display = 'flex';
        document.getElementById('legend').style.display = 'block';
        document.getElementById('info').style.display = 'block';
        window.parent.postMessage({ type: 'moleculeLoaded' }, '*');
      }
      
      function showError(msg) {
        document.getElementById('loading').innerHTML = 
          '<div style="color:#dc2626;">' + msg + '</div>' +
          '<div style="font-size:10px;margin-top:8px;color:#64748b;">SMILES: ' + smiles.substring(0, 40) + '...</div>';
        window.parent.postMessage({ type: 'moleculeError' }, '*');
      }
      
      function displayModel(data, format) {
        try {
          viewer.addModel(data, format);
          applyStyle();
          viewer.zoomTo();
          viewer.render();
          showSuccess();
          return true;
        } catch (e) {
          console.error('Failed to display model:', e);
          return false;
        }
      }
      
      // Try NCI CACTUS first (most reliable for SMILES to 3D)
      function tryCactus() {
        var url = 'https://cactus.nci.nih.gov/chemical/structure/' + encodeURIComponent(smiles) + '/sdf';
        return fetch(url, { signal: AbortSignal.timeout(8000) })
          .then(function(r) { 
            if (!r.ok) throw new Error('Not OK');
            return r.text(); 
          })
          .then(function(sdf) {
            if (!sdf || sdf.length < 100 || sdf.includes('Page not found')) {
              throw new Error('Invalid response');
            }
            return displayModel(sdf, 'sdf');
          });
      }
      
      // Try PubChem (good fallback)
      function tryPubChem() {
        // First get compound ID from SMILES
        var searchUrl = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/' + encodeURIComponent(smiles) + '/cids/JSON';
        return fetch(searchUrl, { signal: AbortSignal.timeout(8000) })
          .then(function(r) { 
            if (!r.ok) throw new Error('Not OK');
            return r.json(); 
          })
          .then(function(data) {
            if (!data.IdentifierList || !data.IdentifierList.CID || !data.IdentifierList.CID[0]) {
              throw new Error('No CID found');
            }
            var cid = data.IdentifierList.CID[0];
            // Get 3D SDF
            var sdfUrl = 'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/' + cid + '/SDF?record_type=3d';
            return fetch(sdfUrl, { signal: AbortSignal.timeout(8000) });
          })
          .then(function(r) { 
            if (!r.ok) throw new Error('SDF fetch failed');
            return r.text(); 
          })
          .then(function(sdf) {
            return displayModel(sdf, 'sdf');
          });
      }
      
      // Try ChemSpider/Open Babel as last resort (2D only)
      function tryOpenBabel() {
        // Generate simple 2D coordinates locally using basic heuristics
        // This is a placeholder - in reality we'd need a proper converter
        showError('Could not generate 3D structure');
        return Promise.resolve(false);
      }
      
      // Chain the attempts
      document.getElementById('loading').innerHTML = 
        '<div class="loading-spinner"></div><div>Fetching 3D structure...</div>';
      
      tryCactus()
        .catch(function(e) {
          console.warn('CACTUS failed:', e.message);
          document.getElementById('loading').innerHTML = 
            '<div class="loading-spinner"></div><div>Trying PubChem...</div>';
          return tryPubChem();
        })
        .catch(function(e) {
          console.warn('PubChem failed:', e.message);
          return tryOpenBabel();
        })
        .catch(function(e) {
          console.error('All methods failed:', e);
          showError('Could not load molecule');
        });
    }
    
    function applyStyle() {
      if (!viewer) return;
      
      viewer.removeAllSurfaces();
      viewer.setStyle({}, {});
      
      if (currentStyle === 'ball') {
        viewer.setStyle({}, { 
          stick: { radius: 0.15, colorscheme: 'Jmol' },
          sphere: { radius: 0.4, colorscheme: 'Jmol' }
        });
      } else if (currentStyle === 'stick') {
        viewer.setStyle({}, { 
          stick: { radius: 0.2, colorscheme: 'Jmol' }
        });
      } else if (currentStyle === 'sphere') {
        viewer.setStyle({}, { 
          sphere: { colorscheme: 'Jmol' }
        });
      } else if (currentStyle === 'surface') {
        viewer.setStyle({}, { 
          stick: { radius: 0.1, colorscheme: 'Jmol' }
        });
        viewer.addSurface($3Dmol.SurfaceType.VDW, { 
          opacity: 0.85,
          colorscheme: 'Jmol'
        });
      }
      
      viewer.render();
    }
    
    function setStyle(style) {
      currentStyle = style;
      ['ball', 'stick', 'sphere', 'surface'].forEach(function(s) {
        var btn = document.getElementById('btn-' + s);
        if (btn) btn.classList.toggle('active', s === style);
      });
      applyStyle();
    }
    
    function resetView() {
      if (!viewer) return;
      viewer.zoomTo();
      viewer.render();
    }
    
    function toggleSpin() {
      if (!viewer) return;
      spinning = !spinning;
      viewer.spin(spinning ? 'y' : false);
    }
    
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', init);
    } else {
      init();
    }
  </script>
</body>
</html>`;
  };

  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      if (event.data?.type === 'moleculeLoaded') {
        setLoading(false);
        setError(null);
      } else if (event.data?.type === 'moleculeError') {
        setLoading(false);
        setError('Failed to load molecule structure');
      }
    };

    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-lg overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 bg-teal-50">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-teal-600 rounded-lg">
              <FlaskConical className="w-5 h-5 text-white" />
            </div>
            <div>
              <h3 className="font-bold text-gray-900">Drug Molecule Structure</h3>
              <p className="text-sm text-gray-600 truncate max-w-md">{moleculeName}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={resetViewer}
              className="p-2 text-gray-500 hover:text-teal-600 hover:bg-white rounded-lg transition-all"
              title="Reload viewer"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-2 text-gray-500 hover:text-teal-600 hover:bg-white rounded-lg transition-all"
            >
              {isExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>

      {/* Viewer */}
      <div className={`relative bg-gray-50 transition-all duration-300 ${isExpanded ? 'h-[550px]' : 'h-[400px]'}`}>
        <iframe
          key={viewerKey}
          srcDoc={getViewerHtml()}
          className="w-full h-full border-0"
          title={`3D structure of ${moleculeName}`}
          sandbox="allow-scripts allow-same-origin"
        />
      </div>

      {/* Footer */}
      <div className="px-5 py-3 border-t border-gray-100 bg-gray-50">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>Drag to rotate • Scroll to zoom</span>
          <span>Powered by 3Dmol.js</span>
        </div>
      </div>
    </div>
  );
}
