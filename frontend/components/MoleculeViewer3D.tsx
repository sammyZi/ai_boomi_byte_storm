'use client';

import { useState } from 'react';
import { Maximize2, Minimize2, Beaker } from 'lucide-react';

interface MoleculeViewer3DProps {
  smiles: string;
  moleculeName: string;
}

export default function MoleculeViewer3D({ smiles, moleculeName }: MoleculeViewer3DProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Use PubChem's 3D viewer which is more reliable for small molecules
  // Encode SMILES for URL
  const encodedSmiles = encodeURIComponent(smiles);
  
  // Use 3Dmol.js with inline SMILES
  const viewer3DUrl = `https://3dmol.csb.pitt.edu/viewer.html?cid=${encodedSmiles}&style=stick:colorscheme~Jmol&surface=opacity:0.7;color:white`;

  return (
    <div className="bg-purple-50 rounded-xl p-6 border-2 border-purple-200 shadow-md">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-lg font-bold text-gray-900 flex items-center gap-2">
          <div className="w-2 h-2 bg-purple-600 rounded-full animate-pulse"></div>
          3D Molecule Structure
        </h4>
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="p-2 text-gray-700 hover:text-purple-600 hover:bg-white rounded-lg transition-all"
          aria-label={isExpanded ? 'Minimize' : 'Maximize'}
        >
          {isExpanded ? (
            <Minimize2 className="w-5 h-5" />
          ) : (
            <Maximize2 className="w-5 h-5" />
          )}
        </button>
      </div>

      <div className="mb-3 text-sm text-gray-700 bg-white/80 px-4 py-2 rounded-lg">
        <span className="font-semibold">{moleculeName}</span>
      </div>

      {/* 3D Viewer Container */}
      <div
        className={`relative bg-white rounded-xl overflow-hidden border-2 border-gray-200 shadow-inner transition-all duration-300 ${
          isExpanded ? 'h-[500px]' : 'h-[350px]'
        }`}
      >
        <iframe
          src={viewer3DUrl}
          className="w-full h-full border-0"
          title={`3D structure of ${moleculeName}`}
          allow="fullscreen"
          sandbox="allow-scripts allow-same-origin"
        />
      </div>

      <div className="mt-4 text-xs text-gray-600 bg-white/80 px-4 py-3 rounded-lg">
        <p className="font-medium flex items-center gap-2">
          <Beaker className="w-4 h-4" />
          Interactive 3D drug molecule viewer
        </p>
        <p className="mt-1">
          🖱️ Drag to rotate • Scroll to zoom • Stick representation with surface
        </p>
      </div>
    </div>
  );
}
