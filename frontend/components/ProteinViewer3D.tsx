'use client';

import { useState } from 'react';
import { Maximize2, Minimize2, ExternalLink } from 'lucide-react';

interface ProteinViewer3DProps {
  uniprotId: string;
  proteinName: string;
}

export default function ProteinViewer3D({ uniprotId, proteinName }: ProteinViewer3DProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const viewerUrl = `https://alphafold.ebi.ac.uk/entry/${uniprotId}`;

  // Alternative: Use AlphaFold's own embed
  const alphafoldEmbed = `https://alphafold.ebi.ac.uk/entry/${uniprotId}`;

  return (
    <div className="bg-blue-50 rounded-xl p-6 border-2 border-blue-200 shadow-md">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-lg font-bold text-gray-900 flex items-center gap-2">
          <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
          3D Protein Structure
        </h4>
        <div className="flex items-center gap-2">
          <a
            href={viewerUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all shadow-md"
          >
            <ExternalLink className="w-4 h-4" />
            View Full
          </a>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 text-gray-700 hover:text-blue-600 hover:bg-white rounded-lg transition-all"
            aria-label={isExpanded ? 'Minimize' : 'Maximize'}
          >
            {isExpanded ? (
              <Minimize2 className="w-5 h-5" />
            ) : (
              <Maximize2 className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>

      <div className="mb-3 text-sm text-gray-700 bg-white/80 px-4 py-2 rounded-lg">
        <span className="font-semibold">{proteinName}</span>
        <span className="text-gray-500 ml-2 font-mono text-xs">({uniprotId})</span>
      </div>

      {/* 3D Viewer Container */}
      <div
        className={`relative bg-white rounded-xl overflow-hidden border-2 border-gray-200 shadow-inner transition-all duration-300 ${isExpanded ? 'h-[600px]' : 'h-[500px]'
          }`}
      >
        {/* Use Mol* Viewer hosted instance which is reliable and free */}
        <iframe
          src={`https://molstar.org/viewer/?url=https://alphafold.ebi.ac.uk/files/AF-${uniprotId}-F1-model_v4.pdb&hide-controls=1&bg=white`}
          className="w-full h-full border-0"
          title={`3D structure of ${proteinName}`}
          allow="fullscreen; accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
        />

        {/* Helper overlay if viewer fails to load (fallback logic or just informational) */}
        <div className="absolute top-2 left-2 pointer-events-none">
          <div className="bg-white/80 backdrop-blur px-2 py-1 rounded text-[10px] text-gray-500 border border-gray-200">
            Powered by Mol*
          </div>
        </div>
      </div>

      <div className="mt-4 text-xs text-gray-600 bg-white/80 px-4 py-3 rounded-lg">
        <p className="font-medium">
          🧬 AlphaFold predicted structure with confidence coloring
        </p>
        <p className="mt-1">
          Click &quot;View Full&quot; for interactive controls and detailed analysis
        </p>
      </div>
    </div>
  );
}
