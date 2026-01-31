'use client';

import { useState, useCallback } from 'react';
import { X, Play, Settings, Loader2, Clock, AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import { DrugCandidate, DockingSubmitRequest, GridBoxParams, DockingParams } from '@/types';
import { dockingApi, DockingApiError } from '@/lib/docking-api';

interface DockingSubmissionModalProps {
  candidate: DrugCandidate;
  onClose: () => void;
  onSubmitSuccess: (jobIds: string[]) => void;
}

const DEFAULT_GRID_PARAMS: GridBoxParams = {
  center_x: 0,
  center_y: 0,
  center_z: 0,
  size_x: 20,
  size_y: 20,
  size_z: 20,
};

const DEFAULT_DOCKING_PARAMS: DockingParams = {
  exhaustiveness: 8,
  num_modes: 9,
  energy_range: 3,
};

export default function DockingSubmissionModal({
  candidate,
  onClose,
  onSubmitSuccess,
}: DockingSubmissionModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [useCustomGrid, setUseCustomGrid] = useState(false);
  const [useCustomDocking, setUseCustomDocking] = useState(false);
  const [gridParams, setGridParams] = useState<GridBoxParams>(DEFAULT_GRID_PARAMS);
  const [dockingParams, setDockingParams] = useState<DockingParams>(DEFAULT_DOCKING_PARAMS);

  const estimatedTime = '5-15 minutes';

  const handleSubmit = useCallback(async () => {
    setIsSubmitting(true);
    setError(null);

    // Validate required fields
    if (!candidate.molecule?.chembl_id) {
      setError('Missing molecule ChEMBL ID');
      setIsSubmitting(false);
      return;
    }

    if (!candidate.target?.uniprot_id) {
      setError('Missing target UniProt ID');
      setIsSubmitting(false);
      return;
    }

    if (!candidate.molecule?.smiles) {
      setError('Missing molecule SMILES structure');
      setIsSubmitting(false);
      return;
    }

    const request: DockingSubmitRequest = {
      candidate_id: candidate.molecule.chembl_id,
      target_uniprot_id: candidate.target.uniprot_id,
      disease_name: candidate.target.disease_association || 'Unknown disease',
      smiles: candidate.molecule.smiles,
    };

    if (useCustomGrid) {
      request.grid_params = gridParams;
    }

    if (useCustomDocking) {
      request.docking_params = dockingParams;
    }

    console.log('Submitting docking request:', JSON.stringify(request, null, 2));

    try {
      const response = await dockingApi.submitDockingJobs(request);
      onSubmitSuccess([response.job_id]);
    } catch (err) {
      console.error('Docking submission error:', err);
      if (err instanceof DockingApiError) {
        setError(err.message);
      } else {
        setError('An unexpected error occurred. Please try again.');
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [candidate, gridParams, dockingParams, useCustomGrid, useCustomDocking, onSubmitSuccess]);

  const handleGridChange = (field: keyof GridBoxParams, value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      setGridParams((prev) => ({ ...prev, [field]: numValue }));
    }
  };

  const handleDockingChange = (field: keyof DockingParams, value: string) => {
    const numValue = parseFloat(value);
    if (!isNaN(numValue)) {
      setDockingParams((prev) => ({ ...prev, [field]: numValue }));
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-xl font-bold text-gray-900">Run Molecular Docking</h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh]">
          {/* Candidate Summary */}
          <div className="bg-blue-50 rounded-xl p-4 mb-6">
            <h3 className="text-sm font-semibold text-blue-900 mb-3">Candidate Summary</h3>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-blue-600 font-medium">Molecule:</span>
                <p className="text-blue-900 font-semibold truncate">{candidate.molecule.name}</p>
              </div>
              <div>
                <span className="text-blue-600 font-medium">ChEMBL ID:</span>
                <p className="text-blue-900 font-mono">{candidate.molecule.chembl_id}</p>
              </div>
              <div>
                <span className="text-blue-600 font-medium">Target:</span>
                <p className="text-blue-900">{candidate.target.gene_symbol}</p>
              </div>
              <div>
                <span className="text-blue-600 font-medium">Composite Score:</span>
                <p className="text-blue-900 font-bold">{candidate.composite_score.toFixed(2)}</p>
              </div>
            </div>
          </div>

          {/* Estimated Time */}
          <div className="flex items-center gap-3 p-4 bg-amber-50 rounded-xl mb-6">
            <Clock className="w-5 h-5 text-amber-600" />
            <div>
              <p className="text-sm font-medium text-amber-900">Estimated Time: {estimatedTime}</p>
              <p className="text-xs text-amber-700">
                Docking simulations run in the background. You'll be notified when complete.
              </p>
            </div>
          </div>

          {/* Advanced Options Toggle */}
          <button
            onClick={() => setShowAdvanced(!showAdvanced)}
            className="flex items-center gap-2 text-sm font-medium text-gray-600 hover:text-gray-900 mb-4"
          >
            <Settings className="w-4 h-4" />
            Advanced Options
            {showAdvanced ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>

          {/* Advanced Options Panel */}
          {showAdvanced && (
            <div className="space-y-6 bg-gray-50 rounded-xl p-4">
              {/* Grid Box Parameters */}
              <div>
                <label className="flex items-center gap-2 mb-3">
                  <input
                    type="checkbox"
                    checked={useCustomGrid}
                    onChange={(e) => setUseCustomGrid(e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm font-medium text-gray-700">Custom Grid Box Parameters</span>
                </label>
                {useCustomGrid && (
                  <div className="grid grid-cols-3 gap-3 ml-6">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Center X (Å)</label>
                      <input
                        type="number"
                        value={gridParams.center_x}
                        onChange={(e) => handleGridChange('center_x', e.target.value)}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Center Y (Å)</label>
                      <input
                        type="number"
                        value={gridParams.center_y}
                        onChange={(e) => handleGridChange('center_y', e.target.value)}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Center Z (Å)</label>
                      <input
                        type="number"
                        value={gridParams.center_z}
                        onChange={(e) => handleGridChange('center_z', e.target.value)}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Size X (Å)</label>
                      <input
                        type="number"
                        value={gridParams.size_x}
                        onChange={(e) => handleGridChange('size_x', e.target.value)}
                        min={1}
                        max={50}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Size Y (Å)</label>
                      <input
                        type="number"
                        value={gridParams.size_y}
                        onChange={(e) => handleGridChange('size_y', e.target.value)}
                        min={1}
                        max={50}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Size Z (Å)</label>
                      <input
                        type="number"
                        value={gridParams.size_z}
                        onChange={(e) => handleGridChange('size_z', e.target.value)}
                        min={1}
                        max={50}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Docking Parameters */}
              <div>
                <label className="flex items-center gap-2 mb-3">
                  <input
                    type="checkbox"
                    checked={useCustomDocking}
                    onChange={(e) => setUseCustomDocking(e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="text-sm font-medium text-gray-700">Custom Docking Parameters</span>
                </label>
                {useCustomDocking && (
                  <div className="grid grid-cols-3 gap-3 ml-6">
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Exhaustiveness</label>
                      <input
                        type="number"
                        value={dockingParams.exhaustiveness}
                        onChange={(e) => handleDockingChange('exhaustiveness', e.target.value)}
                        min={1}
                        max={32}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Num Modes</label>
                      <input
                        type="number"
                        value={dockingParams.num_modes}
                        onChange={(e) => handleDockingChange('num_modes', e.target.value)}
                        min={1}
                        max={20}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-gray-500 mb-1">Energy Range</label>
                      <input
                        type="number"
                        value={dockingParams.energy_range}
                        onChange={(e) => handleDockingChange('energy_range', e.target.value)}
                        min={1}
                        max={10}
                        step={0.5}
                        className="w-full px-3 py-2 text-sm border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="flex items-center gap-3 p-4 bg-red-50 rounded-xl mt-4">
              <AlertTriangle className="w-5 h-5 text-red-600 flex-shrink-0" />
              <p className="text-sm text-red-700">{error}</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={isSubmitting}
            className="flex items-center gap-2 px-6 py-2 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 rounded-lg shadow-md hover:shadow-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Submitting...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Docking
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
