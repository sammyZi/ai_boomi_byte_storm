'use client';

import { useState, useEffect } from 'react';
import { Maximize2, Minimize2, ExternalLink, Loader2 } from 'lucide-react';

interface ProteinViewer3DProps {
  uniprotId: string;
  proteinName: string;
}

export default function ProteinViewer3D({ uniprotId, proteinName }: ProteinViewer3DProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [pdbUrl, setPdbUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    const fetchAlphaFoldData = async () => {
      try {
        setLoading(true);
        // Fetch the correct file URL from the API
        const response = await fetch(`https://alphafold.ebi.ac.uk/api/prediction/${uniprotId.toUpperCase()}`);
        
        if (!response.ok) throw new Error('Protein not found');
        
        const data = await response.json();
        
        if (data && data.length > 0) {
          setPdbUrl(data[0].pdbUrl);
        } else {
          setError(true);
        }
      } catch (err) {
        console.error("AlphaFold API Error:", err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };

    if (uniprotId) {
      fetchAlphaFoldData();
    }
  }, [uniprotId]);

  // FIX: Define the style as a rigorous JSON object
  // This is much more robust than the "cartoon:color=spectrum" string
  const viewerStyle = {
    cartoon: {
      color: 'spectrum', // Forces Rainbow coloring
    },
  };
  
  // We serialize and encode the JSON style
  const styleParam = encodeURIComponent(JSON.stringify(viewerStyle));
  
  // We add 'select=all' to ensure the style applies to the whole model
  const viewerSrc = pdbUrl 
    ? `https://3dmol.org/viewer.html?url=${encodeURIComponent(pdbUrl)}&select=all&style=${styleParam}` 
    : '';

  return (
    <div className="bg-blue-50 rounded-xl p-6 border-2 border-blue-200 shadow-md">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-lg font-bold text-gray-900 flex items-center gap-2">
          <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
          3D Protein Structure
        </h4>
        <div className="flex items-center gap-2">
          <a
            href={`https://alphafold.ebi.ac.uk/entry/${uniprotId}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-all shadow-md"
          >
            <ExternalLink className="w-4 h-4" />
            Full Analysis
          </a>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-2 text-gray-700 hover:text-blue-600 hover:bg-white rounded-lg transition-all"
          >
            {isExpanded ? <Minimize2 className="w-5 h-5" /> : <Maximize2 className="w-5 h-5" />}
          </button>
        </div>
      </div>

      <div className="mb-3 text-sm text-gray-700 bg-white/80 px-4 py-2 rounded-lg">
        <span className="font-semibold">{proteinName}</span>
        <span className="text-gray-500 ml-2 font-mono text-xs">({uniprotId.toUpperCase()})</span>
      </div>

      <div
        className={`relative bg-white rounded-xl overflow-hidden border-2 border-gray-200 shadow-inner transition-all duration-300 ${
          isExpanded ? 'h-[600px]' : 'h-[500px]'
        }`}
      >
        {loading ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50 text-gray-500">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600 mb-2" />
            <span className="text-xs font-medium">Fetching AlphaFold Model...</span>
          </div>
        ) : error ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center bg-gray-50 text-red-500">
            <span className="text-sm font-bold">Structure Not Found</span>
            <span className="text-xs mt-1">AlphaFold may not have a model for this ID.</span>
          </div>
        ) : (
          <iframe
            src={viewerSrc}
            className="w-full h-full border-0"
            title={`3D structure of ${proteinName}`}
            // No XR permissions needed for 3Dmol.js
            allow="fullscreen; accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            sandbox="allow-scripts allow-same-origin allow-popups allow-forms"
          />
        )}
      </div>

      <div className="mt-4 text-xs text-gray-600 bg-white/80 px-4 py-3 rounded-lg">
        <p className="font-medium">🧬 3Dmol.js Visualization</p>
        <p className="mt-1">
          Rainbow coloring (N-term to C-term). Click and drag to rotate.
        </p>
      </div>
    </div>
  );
}