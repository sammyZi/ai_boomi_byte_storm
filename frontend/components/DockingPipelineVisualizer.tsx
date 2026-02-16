'use client';

import { useMemo } from 'react';
import {
  FlaskConical,
  Atom,
  Dna,
  Cpu,
  Brain,
  CheckCircle2,
  Loader2,
  XCircle,
  Circle,
  ArrowRight,
} from 'lucide-react';

interface PipelineStep {
  id: string;
  name: string;
  tool: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  duration?: number;
}

interface DockingPipelineVisualizerProps {
  currentStep?: string;
  progressPercent?: number;
  steps?: PipelineStep[];
}

// Default pipeline steps
const DEFAULT_PIPELINE: PipelineStep[] = [
  {
    id: 'rdkit',
    name: 'RDKit',
    tool: 'RDKit/OpenBabel',
    description: 'Ligand preparation & 3D conformer',
    status: 'pending',
  },
  {
    id: 'openbabel',
    name: 'OpenBabel',
    tool: 'OpenBabel',
    description: 'Protein PDBQT conversion',
    status: 'pending',
  },
  {
    id: 'smina',
    name: 'Smina',
    tool: 'Smina/Vina',
    description: 'Molecular docking engine',
    status: 'pending',
  },
  {
    id: 'vina',
    name: 'Vina',
    tool: 'AutoDock Vina',
    description: 'Fallback docking engine',
    status: 'pending',
  },
  {
    id: 'gnina',
    name: 'GNINA',
    tool: 'GNINA',
    description: 'CNN-based scoring',
    status: 'pending',
  },
  {
    id: 'dl',
    name: 'DL Re-score',
    tool: 'Deep Learning',
    description: 'Re-scoring with neural network',
    status: 'pending',
  },
];

const STEP_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  rdkit: FlaskConical,
  openbabel: Atom,
  smina: Dna,
  vina: Dna,
  gnina: Cpu,
  dl: Brain,
};

type StepStatus = 'pending' | 'running' | 'completed' | 'skipped';

function getStatusFromProgress(stepId: string, currentStep?: string, progress?: number): StepStatus {
  if (!currentStep || progress === undefined) return 'pending';
  
  const stepOrder = ['rdkit', 'openbabel', 'smina', 'vina', 'gnina', 'dl'];
  
  // Map progress percentage to steps
  const progressSteps: Record<string, number> = {
    'rdkit': 10,
    'openbabel': 25,
    'smina': 50,
    'vina': 60,
    'gnina': 75,
    'dl': 90,
  };
  
  const stepProgress = progressSteps[stepId] || 0;
  
  if (progress >= 100) return 'completed';
  if (progress > stepProgress) return 'completed';
  if (progress === stepProgress || currentStep.toLowerCase().includes(stepId)) return 'running';
  
  // Skip Vina if Smina succeeded
  if (stepId === 'vina' && progress > 60) return 'skipped';
  
  return 'pending';
}

export default function DockingPipelineVisualizer({
  currentStep,
  progressPercent,
  steps = DEFAULT_PIPELINE,
}: DockingPipelineVisualizerProps) {
  // Derive step statuses from current progress
  const pipelineSteps = useMemo(() => {
    return steps.map(step => ({
      ...step,
      status: getStatusFromProgress(step.id, currentStep, progressPercent),
    }));
  }, [steps, currentStep, progressPercent]);

  return (
    <div className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl p-6 border border-slate-700">
      {/* Title */}
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-white font-bold text-lg">Docking Pipeline</h3>
        <span className="text-xs text-slate-400 bg-slate-700/50 px-2 py-1 rounded">
          RDKit → OpenBabel → Smina → Vina → GNINA → DL
        </span>
      </div>

      {/* Pipeline Steps */}
      <div className="flex items-center justify-between gap-2">
        {pipelineSteps.map((step, index) => {
          const Icon = STEP_ICONS[step.id] || Circle;
          const isLast = index === pipelineSteps.length - 1;
          
          let statusColor = 'text-slate-500';
          let bgColor = 'bg-slate-700/50';
          
          if (step.status === 'completed') {
            statusColor = 'text-emerald-400';
            bgColor = 'bg-emerald-500/20';
          } else if (step.status === 'running') {
            statusColor = 'text-blue-400';
            bgColor = 'bg-blue-500/20';
          } else if (step.status === 'skipped') {
            statusColor = 'text-slate-600';
            bgColor = 'bg-slate-800/50';
          }
          
          return (
            <div key={step.id} className="flex items-center flex-1">
              {/* Step */}
              <div 
                className={`flex flex-col items-center flex-1 p-3 rounded-xl transition-all ${bgColor}`}
                title={step.description}
              >
                {/* Icon with status indicator */}
                <div className="relative">
                  <Icon className={`w-6 h-6 ${statusColor}`} />
                  {step.status === 'running' && (
                    <div className="absolute -top-1 -right-1">
                      <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />
                    </div>
                  )}
                  {step.status === 'completed' && (
                    <div className="absolute -top-1 -right-1">
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    </div>
                  )}
                </div>
                
                {/* Label */}
                <span className={`text-xs font-medium mt-2 ${statusColor}`}>
                  {step.name}
                </span>
                
                {/* Duration if completed */}
                {step.status === 'completed' && step.duration && (
                  <span className="text-[10px] text-slate-500 mt-0.5">
                    {step.duration.toFixed(1)}s
                  </span>
                )}
              </div>
              
              {/* Arrow connector */}
              {!isLast && (
                <ArrowRight className={`w-4 h-4 mx-1 flex-shrink-0 ${
                  step.status === 'completed' ? 'text-emerald-500/50' : 'text-slate-600'
                }`} />
              )}
            </div>
          );
        })}
      </div>

      {/* Current Step Info */}
      {currentStep && (
        <div className="mt-4 pt-4 border-t border-slate-700">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
            <span className="text-sm text-slate-300">
              {currentStep}
            </span>
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="mt-4 pt-4 border-t border-slate-700 flex items-center justify-center gap-6 text-xs">
        <div className="flex items-center gap-1.5">
          <Circle className="w-3 h-3 text-slate-500" />
          <span className="text-slate-500">Pending</span>
        </div>
        <div className="flex items-center gap-1.5">
          <Loader2 className="w-3 h-3 text-blue-400" />
          <span className="text-slate-400">Running</span>
        </div>
        <div className="flex items-center gap-1.5">
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          <span className="text-slate-400">Done</span>
        </div>
        <div className="flex items-center gap-1.5">
          <XCircle className="w-3 h-3 text-red-400" />
          <span className="text-slate-400">Failed</span>
        </div>
      </div>
    </div>
  );
}
