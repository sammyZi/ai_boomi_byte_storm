'use client';

import { useState } from 'react';
import { DockingPose } from '@/types';
import { Trophy, ChevronDown, ChevronUp, Atom, Activity } from 'lucide-react';

interface DockingPoseCardProps {
  pose: DockingPose;
  isBest: boolean;
  isSelected: boolean;
  onSelect: () => void;
  rank: number;
}

interface AtomInfo {
  element: string;
  count: number;
  color: string;
}

const getAffinityColor = (affinity: number): string => {
  if (affinity <= -9) return 'text-emerald-600';
  if (affinity <= -7) return 'text-green-600';
  if (affinity <= -5) return 'text-yellow-600';
  return 'text-orange-600';
};

const getAffinityBg = (affinity: number): string => {
  if (affinity <= -9) return 'bg-emerald-50 border-emerald-200';
  if (affinity <= -7) return 'bg-green-50 border-green-200';
  if (affinity <= -5) return 'bg-yellow-50 border-yellow-200';
  return 'bg-orange-50 border-orange-200';
};

const getAffinityLabel = (affinity: number): string => {
  if (affinity <= -9) return 'Excellent';
  if (affinity <= -7) return 'Good';
  if (affinity <= -5) return 'Moderate';
  return 'Weak';
};

// Parse PDBQT data to extract atom information
const parseAtomInfo = (pdbqtData: string): AtomInfo[] => {
  if (!pdbqtData) return [];
  
  const atomCounts: Record<string, number> = {};
  const lines = pdbqtData.split('\n');
  
  for (const line of lines) {
    if (line.startsWith('ATOM') || line.startsWith('HETATM')) {
      // PDBQT format: element is typically at position 77-78 or can be parsed from atom name
      const element = line.substring(77, 79).trim() || line.substring(12, 16).trim().replace(/[0-9]/g, '')[0];
      if (element) {
        atomCounts[element] = (atomCounts[element] || 0) + 1;
      }
    }
  }
  
  const elementColors: Record<string, string> = {
    'C': '#10b981', // Green
    'N': '#3b82f6', // Blue
    'O': '#ef4444', // Red
    'S': '#eab308', // Yellow
    'P': '#f97316', // Orange
    'F': '#22c55e', // Light green
    'Cl': '#22c55e', // Light green
    'Br': '#a855f7', // Purple
    'I': '#9333ea', // Dark purple
    'H': '#9ca3af', // Gray
  };
  
  return Object.entries(atomCounts)
    .map(([element, count]) => ({
      element,
      count,
      color: elementColors[element] || '#6b7280',
    }))
    .sort((a, b) => b.count - a.count);
};

export default function DockingPoseCard({
  pose,
  isBest,
  isSelected,
  onSelect,
  rank,
}: DockingPoseCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const atomInfo = parseAtomInfo(pose.pdbqt_data || '');
  const totalAtoms = atomInfo.reduce((sum, atom) => sum + atom.count, 0);

  return (
    <div
      className={`rounded-xl border-2 transition-all ${
        isSelected
          ? 'border-blue-500 bg-blue-50 shadow-lg'
          : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-md'
      }`}
    >
      {/* Card Header */}
      <div
        className="p-4 cursor-pointer"
        onClick={onSelect}
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            {/* Rank Badge */}
            <div
              className={`w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold ${
                rank === 1
                  ? 'bg-amber-100 text-amber-700'
                  : rank === 2
                  ? 'bg-gray-200 text-gray-700'
                  : rank === 3
                  ? 'bg-orange-100 text-orange-700'
                  : 'bg-gray-100 text-gray-600'
              }`}
            >
              {rank}
            </div>
            
            <div>
              <div className="flex items-center gap-2">
                <h4 className="text-lg font-bold text-gray-900">Pose #{pose.pose_number}</h4>
                {isBest && (
                  <span className="flex items-center gap-1 px-2 py-0.5 bg-amber-100 text-amber-700 text-xs font-bold rounded-full">
                    <Trophy className="w-3 h-3" />
                    Best
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 mt-0.5">
                {getAffinityLabel(pose.binding_affinity)} binding affinity
              </p>
            </div>
          </div>
          
          {/* Affinity Score */}
          <div className={`px-4 py-2 rounded-lg border ${getAffinityBg(pose.binding_affinity)}`}>
            <p className="text-xs text-gray-600 font-medium">Affinity</p>
            <p className={`text-xl font-bold ${getAffinityColor(pose.binding_affinity)}`}>
              {pose.binding_affinity.toFixed(2)}
            </p>
            <p className="text-xs text-gray-500">kcal/mol</p>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">RMSD LB</p>
            <p className="text-sm font-bold text-gray-900">{pose.rmsd_lb.toFixed(3)} Å</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">RMSD UB</p>
            <p className="text-sm font-bold text-gray-900">{pose.rmsd_ub.toFixed(3)} Å</p>
          </div>
          <div className="bg-indigo-50 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Total Atoms</p>
            <p className="text-sm font-bold text-indigo-600">{totalAtoms}</p>
          </div>
        </div>
      </div>

      {/* Expandable Atom Details */}
      {atomInfo.length > 0 && (
        <>
          <button
            onClick={(e) => {
              e.stopPropagation();
              setIsExpanded(!isExpanded);
            }}
            className="w-full px-4 py-2 flex items-center justify-between text-sm font-medium text-gray-700 hover:bg-gray-50 border-t border-gray-200 transition-colors"
          >
            <span className="flex items-center gap-2">
              <Atom className="w-4 h-4 text-indigo-500" />
              Atomic Composition
            </span>
            {isExpanded ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {isExpanded && (
            <div className="px-4 pb-4 pt-2 border-t border-gray-100">
              <div className="space-y-2">
                {atomInfo.map((atom) => (
                  <div
                    key={atom.element}
                    className="flex items-center justify-between p-2 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shadow-sm"
                        style={{ backgroundColor: atom.color }}
                      >
                        {atom.element}
                      </div>
                      <div>
                        <p className="text-sm font-semibold text-gray-900">
                          {atom.element === 'C' && 'Carbon'}
                          {atom.element === 'N' && 'Nitrogen'}
                          {atom.element === 'O' && 'Oxygen'}
                          {atom.element === 'S' && 'Sulfur'}
                          {atom.element === 'P' && 'Phosphorus'}
                          {atom.element === 'F' && 'Fluorine'}
                          {atom.element === 'Cl' && 'Chlorine'}
                          {atom.element === 'Br' && 'Bromine'}
                          {atom.element === 'I' && 'Iodine'}
                          {atom.element === 'H' && 'Hydrogen'}
                          {!['C', 'N', 'O', 'S', 'P', 'F', 'Cl', 'Br', 'I', 'H'].includes(atom.element) && atom.element}
                        </p>
                        <p className="text-xs text-gray-500">{atom.element}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-gray-900">{atom.count}</p>
                      <p className="text-xs text-gray-500">
                        {((atom.count / totalAtoms) * 100).toFixed(1)}%
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              {/* Molecular Formula */}
              <div className="mt-3 p-3 bg-indigo-50 rounded-lg border border-indigo-200">
                <p className="text-xs text-gray-600 mb-1 font-medium">Molecular Formula</p>
                <p className="text-sm font-mono font-bold text-indigo-900">
                  {atomInfo
                    .map((atom) => `${atom.element}${atom.count > 1 ? atom.count : ''}`)
                    .join('')}
                </p>
              </div>
            </div>
          )}
        </>
      )}

      {/* Select Button */}
      {!isSelected && (
        <div className="px-4 pb-4">
          <button
            onClick={onSelect}
            className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
          >
            View in 3D
          </button>
        </div>
      )}
    </div>
  );
}
