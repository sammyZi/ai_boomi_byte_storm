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
