'use client';

import { useEffect, useRef, useState } from 'react';
import { Maximize2, Minimize2, ExternalLink, Loader2 } from 'lucide-react';

interface ProteinViewer3DProps {
  uniprotId: string;
  proteinName: string;
}

declare global {
  interface Window {
    $3Dmol: any;
  }
}

export default function ProteinViewer3D({ uniprotId, proteinName }: ProteinViewer3DProps) {
  const viewerRef = useRef<HTMLDivElement>(null);
  const [isExpanded, setIsExpanded] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const viewerInstance = useRef<any>(null);

  const viewerUrl = `https://alphafold.ebi.ac.uk/entry/${uniprotId}`;
  const pdbUrl = `https://alphafold.ebi.ac.uk/files/AF-${uniprotId}-F1-model_v4.pdb`;

  useEffect(() => {
    // Load 3Dmol.js script
    const script = document.createElement('script');
    script.src = 'https://3Dmol.csb.pitt.edu/build/3Dmol-min.js';
    script.async = true;
    
    script.onload = () => {
      initViewer();
    };
    
    script.onerror = () => {
      setError('Failed to load 3Dmol.js library');
      setIsLoading(false);
    };

    document.head.appendChild(script);

    return () => {
      if (viewerInstance.current) {
        try {
          viewerInstance.current.clear();
        } catch (e) {
          // Ignore cleanup errors
        }
      }
    };
  }, [uniprotId]);

  const initViewer = async () => {
    if (!viewerRef.current || !window.$3Dmol) return;

    try {
      setIsLoading(true);
      setError(null);

      // Create viewer
      const config = { backgroundColor: 'white' };
      const viewer = window.$3Dmol.createViewer(viewerRef.current, config);
      viewerInstance.current = viewer;

      // Fetch PDB data from AlphaFold
      const response = await fetch(pdbUrl);
      if (!response.ok) {
        throw new Error('Failed to load protein structure');
      }
      
      const pdbData = await response.text();

      // Add model to viewer
      viewer.addModel(pdbData, 'pdb');
      
      // Style the protein - cartoon representation with color by confidence (pLDDT)
      viewer.setStyle({}, {
        cartoon: {
          color: 'spectrum',
          colorscheme: {
            prop: 'b',
            gradient: 'roygb',
            min: 50,
            max: 90
          }
        }
      });

      // Center and zoom
      viewer.zoomTo();
      viewer.render();
      viewer.zoom(0.8, 1000);

      setIsLoading(false);
    } catch (err) {
      console.error('Error loading protein structure:', err);
      setError(err instanceof Error ? err.message : 'Failed to load structure');
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      {/* 3D Viewer Container */}
      <div
        className={`relative bg-gradient-to-br from-blue-50 to-indigo-50 rounded-lg overflow-hidden border border-gray-200 shadow-sm transition-all duration-300 ${
          isExpanded ? 'h-[600px]' : 'h-[400px]'
        }`}
      >
        {/* 3Dmol.js viewer container */}
        <div 
          ref={viewerRef} 
          className="w-full h-full"
          style={{ position: 'relative' }}
        />

        {/* Loading state */}
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/80 backdrop-blur-sm">
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-2" />
              <p className="text-sm text-gray-600 font-medium">Loading structure...</p>
            </div>
          </div>
        )}

        {/* Error state */}
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/90 backdrop-blur-sm">
            <div className="text-center p-4">
              <p className="text-sm text-red-600 font-medium mb-2">{error}</p>
              <a
                href={viewerUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:underline"
              >
                View on AlphaFold website
              </a>
            </div>
          </div>
        )}

        {/* Helper overlay */}
        {!isLoading && !error && (
          <div className="absolute top-2 left-2 pointer-events-none z-10">
            <div className="bg-white/90 backdrop-blur px-2 py-1 rounded text-[10px] text-gray-500 border border-gray-200 shadow-sm">
              AlphaFold Structure • Drag to rotate
            </div>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs text-gray-600">
          <p className="font-medium">🧬 AlphaFold predicted structure</p>
          <p className="text-[10px] text-gray-500 mt-0.5">Colored by confidence (pLDDT score)</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="p-1.5 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-all text-xs flex items-center gap-1"
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
          <a
            href={viewerUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 px-2.5 py-1.5 text-xs font-semibold bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-all shadow-sm"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            View Full
          </a>
        </div>
      </div>
    </div>
  );
}
