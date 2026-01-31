// Core data types matching backend models

export interface Target {
  uniprot_id: string;
  gene_symbol: string;
  protein_name: string;
  confidence_score: number;
  disease_association: string;
}

export interface ProteinStructure {
  uniprot_id: string;
  pdb_data: string;
  plddt_score: number;
  is_low_confidence: boolean;
}

export interface Molecule {
  chembl_id: string;
  name: string;
  smiles: string;
  canonical_smiles: string;
  pchembl_value: number;
  activity_type: string;
  target_ids: string[];
}

export interface MolecularProperties {
  molecular_weight: number;
  logp: number;
  hbd: number;
  hba: number;
  tpsa: number;
  rotatable_bonds: number;
  aromatic_rings: number;
  lipinski_violations: number;
  drug_likeness_score: number;
}

export interface ToxicityAssessment {
  toxicity_score: number;
  risk_level: 'low' | 'medium' | 'high';
  detected_toxicophores: string[];
  warnings: string[];
}

export interface DrugCandidate {
  molecule: Molecule;
  target: Target;
  properties: MolecularProperties;
  toxicity: ToxicityAssessment;
  binding_affinity_score: number;
  binding_confidence: number;
  composite_score: number;
  rank: number;
  ai_analysis?: string;
  structure_2d_svg: string;
}

export interface DiscoveryResult {
  query: string;
  timestamp: string;
  processing_time_seconds: number;
  candidates: DrugCandidate[];
  targets_found: number;
  molecules_analyzed: number;
  api_version: string;
  warnings: string[];
}

export interface DiscoveryRequest {
  disease_name: string;
}

export interface DiscoveryResponse {
  query: string;
  timestamp: string;
  processing_time_seconds: number;
  candidates: DrugCandidate[];
  metadata: {
    targets_found: number;
    molecules_analyzed: number;
    api_version: string;
  };
  warnings: string[];
}

export interface ErrorResponse {
  error_code: string;
  message: string;
  details?: Record<string, any>;
  timestamp: string;
}

// UI-specific types
export interface SearchState {
  query: string;
  isLoading: boolean;
  error: ErrorResponse | null;
  results: DiscoveryResponse | null;
}

export interface UIPreferences {
  theme: 'light' | 'dark';
  disclaimerDismissed: boolean;
}

// Docking-related types
export interface GridBoxParams {
  center_x: number;
  center_y: number;
  center_z: number;
  size_x: number;
  size_y: number;
  size_z: number;
}

export interface DockingParams {
  exhaustiveness: number;
  num_modes: number;
  energy_range: number;
}

export interface DockingSubmitRequest {
  candidate_id: string;
  target_uniprot_id: string;
  disease_name: string;
  smiles: string;
  grid_params?: GridBoxParams;
  docking_params?: DockingParams;
}

export interface DockingSubmitResponse {
  job_id: string;
  status: string;
  message: string;
  estimated_time_seconds?: number;
}

export type DockingJobStatus = 'queued' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface DockingJobStatusResponse {
  job_id: string;
  status: DockingJobStatus;
  progress_percent: number;
  current_step?: string;
  estimated_time_remaining_seconds?: number;
  queue_position?: number;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface DockingPose {
  pose_number: number;
  binding_affinity: number;
  rmsd_lb: number;
  rmsd_ub: number;
}

export interface DockingJobResult {
  job_id: string;
  candidate_id: string;
  target_uniprot_id: string;
  status: DockingJobStatus;
  best_affinity?: number;
  num_poses: number;
  poses: DockingPose[];
  pdbqt_url?: string;
  error_message?: string;
}
