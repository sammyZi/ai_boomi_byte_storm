'use client';

import { useState, useEffect } from 'react';
import { Maximize2, Minimize2, Beaker } from 'lucide-react';

interface MoleculeViewer3DProps {
  smiles: string;
  moleculeName: string;
}

export default function MoleculeViewer3D({ smiles, moleculeName }: MoleculeViewer3DProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [viewerHtml, setViewerHtml] = useState('');

  useEffect(() => {
    // Create a simple 3Dmol.js viewer HTML
    const html = `
<!DOCTYPE html>
<html>
<head>
  <script src="https://3Dmol.csb.pitt.edu/build/3Dmol-min.js"></script>
  <style>
    body { margin: 0; padding: 0; overflow: hidden; }
    #viewer { width: 100%; height: 100vh; position: relative; }
  </style>
</head>
<body>
  <div id="viewer"></div>
  <script>
    let viewer = $3Dmol.createViewer("viewer", {
      backgroundColor: 'white'
    });
    
    // Add molecule from SMILES
    $3Dmol.get('https://cactus.nci.nih.gov/chemical/structure/${encodeURIComponent(smiles)}/sdf', function(data) {
      viewer.addModel(data, "sdf");
      viewer.setStyle({}, {stick: {colorscheme: 'Jmol'}});
      viewer.addSurface($3Dmol.SurfaceType.VDW, {opacity: 0.7, color: 'lightblue'});
      viewer.zoomTo();
      viewer.render();
      viewer.zoom(1.2, 1000);
    });
  </script>
</body>
</html>`;
    
    setViewerHtml(html);
  }, [smiles]);

  return (
    <div className="space-y-3">
      {/* 3D Viewer Container */}
      <div
        className={`relative bg-gradient-to-br from-purple-50 to-pink-50 rounded-lg overflow-hidden border border-gray-200 shadow-sm transition-all duration-300 ${
          isExpanded ? 'h-[500px]' : 'h-[350px]'
        }`}
      >
        {viewerHtml ? (
          <iframe
            srcDoc={viewerHtml}
            className="w-full h-full border-0"
            title={`3D structure of ${moleculeName}`}
            sandbox="allow-scripts allow-same-origin"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <div className="text-center text-gray-500">
              <Beaker className="w-8 h-8 mx-auto mb-2 animate-pulse" />
              <p className="text-sm">Loading 3D structure...</p>
            </div>
          </div>
        )}
        
        {/* Helper overlay */}
        <div className="absolute top-2 left-2 pointer-events-none z-10">
          <div className="bg-white/90 backdrop-blur px-2 py-1 rounded text-[10px] text-gray-500 border border-gray-200 shadow-sm">
            3Dmol.js Viewer
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs text-gray-600">
          <p className="font-medium flex items-center gap-1.5">
            <Beaker className="w-3.5 h-3.5" />
            Interactive 3D molecule
          </p>
        </div>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-1.5 text-gray-600 hover:text-purple-600 hover:bg-purple-50 rounded-lg transition-all text-xs flex items-center gap-1"
          aria-label={isExpanded ? 'Minimize' : 'Maximize'}
        >
          {isExpanded ? (
            <>
              <Minimize2 className="w-3.5 h-3.5" />
              <span>Minimize</span>
            </>
          ) : (
            <>
              <Maximize2 className="w-3.5 h-3.5" />
              <span>Expand</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
}
