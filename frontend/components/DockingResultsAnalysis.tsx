'use client';

import { useMemo } from 'react';
import {
  Trophy,
  TrendingUp,
  TrendingDown,
  Minus,
  BarChart3,
  Target,
  Sparkles,
  AlertCircle,
  CheckCircle,
  Info,
} from 'lucide-react';
import { DockingJobResult, DockingPose, DrugCandidate } from '@/types';

interface DockingResultsAnalysisProps {
  results: DockingJobResult;
  candidate?: DrugCandidate;
  predictedAffinity?: number;
}

// Affinity quality thresholds
const getAffinityQuality = (affinity: number): { label: string; color: string; bgColor: string } => {
  if (affinity <= -9) return { label: 'Excellent', color: 'text-emerald-600', bgColor: 'bg-emerald-100' };
  if (affinity <= -7) return { label: 'Good', color: 'text-green-600', bgColor: 'bg-green-100' };
  if (affinity <= -5) return { label: 'Moderate', color: 'text-yellow-600', bgColor: 'bg-yellow-100' };
  return { label: 'Weak', color: 'text-orange-600', bgColor: 'bg-orange-100' };
};

// Calculate improvement from prediction
const calculateImprovement = (actual: number, predicted: number): { 
  value: number; 
  percent: number; 
  direction: 'better' | 'worse' | 'same';
} => {
  const diff = actual - predicted;
  const percent = predicted !== 0 ? Math.abs((diff / predicted) * 100) : 0;
  
  // Lower (more negative) is better for binding affinity
  if (diff < -0.5) return { value: Math.abs(diff), percent, direction: 'better' };
  if (diff > 0.5) return { value: Math.abs(diff), percent, direction: 'worse' };
  return { value: 0, percent: 0, direction: 'same' };
};

// Calculate composite score with docking
const calculateUpdatedCompositeScore = (
  originalScore: number,
  dockingAffinity: number,
  dockingWeight: number = 0.3
): number => {
  // Normalize docking affinity to 0-10 scale
  // -12 kcal/mol = 10, 0 kcal/mol = 0
  const normalizedDocking = Math.min(10, Math.max(0, (-dockingAffinity / 12) * 10));
  
  // Blend original score with docking score
  const updatedScore = originalScore * (1 - dockingWeight) + normalizedDocking * dockingWeight;
  return Math.round(updatedScore * 10) / 10;
};

export default function DockingResultsAnalysis({
  results,
  candidate,
  predictedAffinity,
}: DockingResultsAnalysisProps) {
  // Sorted poses by binding affinity (best first)
  const sortedPoses = useMemo(() => {
    return [...results.poses].sort((a, b) => a.binding_affinity - b.binding_affinity);
  }, [results.poses]);

  // Best pose
  const bestPose = sortedPoses[0];

  // Statistics
  const stats = useMemo(() => {
    const affinities = results.poses.map(p => p.binding_affinity);
    const mean = affinities.reduce((a, b) => a + b, 0) / affinities.length;
    const variance = affinities.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / affinities.length;
    const stdDev = Math.sqrt(variance);
    const range = Math.max(...affinities) - Math.min(...affinities);
    
    return {
      mean: mean.toFixed(2),
      stdDev: stdDev.toFixed(2),
      range: range.toFixed(2),
      best: Math.min(...affinities).toFixed(2),
      worst: Math.max(...affinities).toFixed(2),
    };
  }, [results.poses]);

  // Comparison with prediction
  const comparison = useMemo(() => {
    if (predictedAffinity === undefined || !bestPose) return null;
    return calculateImprovement(bestPose.binding_affinity, predictedAffinity);
  }, [bestPose, predictedAffinity]);

  // Updated composite score
  const updatedScore = useMemo(() => {
    if (!candidate || !bestPose) return null;
    return calculateUpdatedCompositeScore(candidate.composite_score, bestPose.binding_affinity);
  }, [candidate, bestPose]);

  // Score change
  const scoreChange = useMemo(() => {
    if (!candidate || updatedScore === null) return null;
    const diff = updatedScore - candidate.composite_score;
    return {
      value: Math.abs(diff).toFixed(1),
      direction: diff > 0.1 ? 'up' : diff < -0.1 ? 'down' : 'same',
    };
  }, [candidate, updatedScore]);

  const bestQuality = bestPose ? getAffinityQuality(bestPose.binding_affinity) : null;

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Best Affinity Card */}
        <div className="bg-gradient-to-br from-indigo-50 to-purple-50 rounded-2xl p-5 border border-indigo-200 shadow-sm">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-medium text-gray-600 mb-1">Best Binding Affinity</p>
              <p className="text-3xl font-bold text-indigo-600">
                {bestPose?.binding_affinity.toFixed(2)}
              </p>
              <p className="text-sm text-gray-500 mt-1">kcal/mol</p>
            </div>
            <div className={`px-3 py-1.5 rounded-lg ${bestQuality?.bgColor}`}>
              <span className={`text-sm font-bold ${bestQuality?.color}`}>
                {bestQuality?.label}
              </span>
            </div>
          </div>
          <div className="mt-4 flex items-center gap-2 text-xs text-gray-600">
            <Trophy className="w-4 h-4 text-amber-500" />
            <span>Pose #{bestPose?.pose_number} of {results.num_poses}</span>
          </div>
        </div>

        {/* Statistical Summary Card */}
        <div className="bg-white rounded-2xl p-5 border border-gray-200 shadow-sm">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-5 h-5 text-blue-500" />
            <p className="text-sm font-semibold text-gray-900">Statistical Summary</p>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Mean Affinity</span>
              <span className="font-mono font-bold">{stats.mean}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Std. Deviation</span>
              <span className="font-mono font-bold">±{stats.stdDev}</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Range</span>
              <span className="font-mono font-bold">{stats.range}</span>
            </div>
          </div>
        </div>

        {/* Prediction Comparison Card */}
        {comparison && predictedAffinity !== undefined && (
          <div className={`rounded-2xl p-5 border shadow-sm ${
            comparison.direction === 'better' ? 'bg-emerald-50 border-emerald-200' :
            comparison.direction === 'worse' ? 'bg-orange-50 border-orange-200' :
            'bg-gray-50 border-gray-200'
          }`}>
            <div className="flex items-center gap-2 mb-3">
              <Target className="w-5 h-5 text-gray-600" />
              <p className="text-sm font-semibold text-gray-900">vs Prediction</p>
            </div>
            <div className="flex items-center gap-3">
              {comparison.direction === 'better' ? (
                <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center">
                  <TrendingUp className="w-5 h-5 text-emerald-600" />
                </div>
              ) : comparison.direction === 'worse' ? (
                <div className="w-10 h-10 bg-orange-100 rounded-full flex items-center justify-center">
                  <TrendingDown className="w-5 h-5 text-orange-600" />
                </div>
              ) : (
                <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center">
                  <Minus className="w-5 h-5 text-gray-600" />
                </div>
              )}
              <div>
                <p className={`text-lg font-bold ${
                  comparison.direction === 'better' ? 'text-emerald-600' :
                  comparison.direction === 'worse' ? 'text-orange-600' :
                  'text-gray-600'
                }`}>
                  {comparison.direction === 'same' ? 'On Target' : 
                   `${comparison.value.toFixed(1)} kcal/mol ${comparison.direction}`}
                </p>
                <p className="text-xs text-gray-500">
                  Predicted: {predictedAffinity.toFixed(2)} kcal/mol
                </p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Score Update Section */}
      {candidate && updatedScore !== null && scoreChange && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-2xl p-5 border border-blue-200">
          <div className="flex items-center gap-2 mb-4">
            <Sparkles className="w-5 h-5 text-blue-500" />
            <h4 className="text-sm font-bold text-gray-900">Updated Composite Score</h4>
          </div>
          
          <div className="flex items-center gap-8">
            {/* Original Score */}
            <div className="text-center">
              <p className="text-xs text-gray-500 mb-1">Original</p>
              <p className="text-2xl font-bold text-gray-400">
                {candidate.composite_score.toFixed(1)}
              </p>
            </div>
            
            {/* Arrow */}
            <div className="flex items-center">
              <div className="w-8 h-0.5 bg-gray-300"></div>
              <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                scoreChange.direction === 'up' ? 'bg-emerald-100' :
                scoreChange.direction === 'down' ? 'bg-orange-100' :
                'bg-gray-100'
              }`}>
                {scoreChange.direction === 'up' ? (
                  <TrendingUp className="w-4 h-4 text-emerald-600" />
                ) : scoreChange.direction === 'down' ? (
                  <TrendingDown className="w-4 h-4 text-orange-600" />
                ) : (
                  <Minus className="w-4 h-4 text-gray-500" />
                )}
              </div>
              <div className="w-8 h-0.5 bg-gray-300"></div>
            </div>
            
            {/* Updated Score */}
            <div className="text-center">
              <p className="text-xs text-gray-500 mb-1">Updated</p>
              <p className="text-2xl font-bold text-blue-600">
                {updatedScore.toFixed(1)}
              </p>
            </div>
            
            {/* Change Badge */}
            <div className={`px-3 py-1.5 rounded-lg ${
              scoreChange.direction === 'up' ? 'bg-emerald-100 text-emerald-700' :
              scoreChange.direction === 'down' ? 'bg-orange-100 text-orange-700' :
              'bg-gray-100 text-gray-600'
            }`}>
              <span className="text-sm font-bold">
                {scoreChange.direction === 'up' ? '+' : scoreChange.direction === 'down' ? '-' : ''}
                {scoreChange.value}
              </span>
            </div>
          </div>
          
          <p className="text-xs text-gray-500 mt-4 flex items-center gap-1">
            <Info className="w-3 h-3" />
            Score updated with 30% weight from docking results
          </p>
        </div>
      )}

      {/* Poses Ranking Table */}
      <div className="bg-white rounded-2xl border border-gray-200 shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-200 bg-gray-50">
          <h4 className="font-semibold text-gray-900 flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-gray-600" />
            Binding Poses Ranked by Affinity
          </h4>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 text-xs text-gray-600 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Rank</th>
                <th className="px-4 py-3 text-left">Pose</th>
                <th className="px-4 py-3 text-left">Binding Affinity</th>
                <th className="px-4 py-3 text-left">Quality</th>
                <th className="px-4 py-3 text-left">RMSD (LB)</th>
                <th className="px-4 py-3 text-left">RMSD (UB)</th>
                <th className="px-4 py-3 text-left">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {sortedPoses.map((pose, index) => {
                const quality = getAffinityQuality(pose.binding_affinity);
                const isBest = index === 0;
                
                return (
                  <tr
                    key={pose.pose_number}
                    className={`hover:bg-gray-50 transition-colors ${isBest ? 'bg-amber-50/50' : ''}`}
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                          index === 0 ? 'bg-amber-100 text-amber-700' :
                          index === 1 ? 'bg-gray-200 text-gray-700' :
                          index === 2 ? 'bg-orange-100 text-orange-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>
                          {index + 1}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-medium">#{pose.pose_number}</td>
                    <td className="px-4 py-3">
                      <span className={`font-bold ${quality.color}`}>
                        {pose.binding_affinity.toFixed(2)} kcal/mol
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${quality.bgColor} ${quality.color}`}>
                        {quality.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 font-mono text-sm">
                      {pose.rmsd_lb.toFixed(3)} Å
                    </td>
                    <td className="px-4 py-3 text-gray-600 font-mono text-sm">
                      {pose.rmsd_ub.toFixed(3)} Å
                    </td>
                    <td className="px-4 py-3">
                      {isBest ? (
                        <span className="flex items-center gap-1 text-amber-600 text-sm font-medium">
                          <Trophy className="w-4 h-4" />
                          Best
                        </span>
                      ) : pose.rmsd_lb < 2 ? (
                        <span className="flex items-center gap-1 text-green-600 text-sm">
                          <CheckCircle className="w-4 h-4" />
                          Similar
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-gray-500 text-sm">
                          <AlertCircle className="w-4 h-4" />
                          Distinct
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        
        {/* Table Footer */}
        <div className="px-5 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">
          <p>
            <strong>Note:</strong> RMSD values show structural deviation from the best pose. 
            Lower RMSD indicates similar binding geometry.
          </p>
        </div>
      </div>

      {/* Interpretation Guide */}
      <div className="bg-blue-50 rounded-xl p-4 border border-blue-200">
        <h5 className="text-sm font-semibold text-blue-900 mb-2 flex items-center gap-2">
          <Info className="w-4 h-4" />
          Interpretation Guide
        </h5>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
            <span className="text-gray-700">Excellent: ≤ -9 kcal/mol</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500"></div>
            <span className="text-gray-700">Good: -9 to -7 kcal/mol</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
            <span className="text-gray-700">Moderate: -7 to -5 kcal/mol</span>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-full bg-orange-500"></div>
            <span className="text-gray-700">Weak: &gt; -5 kcal/mol</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// Export utility functions for use in other components
export { calculateUpdatedCompositeScore, getAffinityQuality, calculateImprovement };
