"""Core data models and schemas for the drug discovery platform.

This module defines Pydantic models for all data structures used throughout
the application, including targets, molecules, properties, and results.
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class Target(BaseModel):
    """Protein target associated with disease.
    
    Represents a protein that can be modulated by drugs to treat a disease.
    """
    uniprot_id: str = Field(..., description="UniProt identifier for the protein")
    gene_symbol: str = Field(..., description="Gene symbol (e.g., APOE, BACE1)")
    protein_name: str = Field(..., description="Full protein name")
    confidence_score: float = Field(
        ..., 
        ge=0.5, 
        le=1.0,
        description="Confidence score for disease association (0.5-1.0)"
    )
    disease_association: str = Field(..., description="Description of disease association")


class ProteinStructure(BaseModel):
    """3D protein structure from AlphaFold.
    
    Contains structural data and confidence metrics for protein targets.
    """
    uniprot_id: str = Field(..., description="UniProt identifier")
    pdb_data: str = Field(..., description="PDB format structure data")
    plddt_score: float = Field(
        ..., 
        ge=0.0, 
        le=100.0,
        description="pLDDT confidence score (0-100)"
    )
    is_low_confidence: bool = Field(
        ..., 
        description="True if pLDDT < 70"
    )


class Molecule(BaseModel):
    """Bioactive molecule from ChEMBL.
    
    Represents a small chemical compound that may bind to protein targets.
    """
    chembl_id: str = Field(..., description="ChEMBL identifier")
    name: str = Field(..., description="Molecule name")
    smiles: str = Field(..., description="SMILES notation")
    canonical_smiles: str = Field(..., description="Canonical SMILES representation")
    pchembl_value: float = Field(
        ..., 
        ge=0.0,
        description="Standardized activity measure (-log10 of IC50 in Molar)"
    )
    activity_type: str = Field(
        ..., 
        description="Measurement type (Ki, Kd, IC50, EC50, etc.)"
    )
    target_ids: List[str] = Field(
        default_factory=list,
        description="List of target UniProt IDs this molecule is active against"
    )
    
    @field_validator('smiles', 'canonical_smiles')
    @classmethod
    def validate_smiles_not_empty(cls, v: str) -> str:
        """Ensure SMILES strings are not empty."""
        if not v or not v.strip():
            raise ValueError("SMILES string cannot be empty")
        return v


class MolecularProperties(BaseModel):
    """Calculated molecular properties for drug-likeness assessment.
    
    Contains physicochemical properties calculated from molecular structure.
    """
    molecular_weight: float = Field(
        ..., 
        gt=0.0,
        description="Molecular weight in Daltons"
    )
    logp: float = Field(..., description="Lipophilicity (partition coefficient)")
    hbd: int = Field(
        ..., 
        ge=0,
        description="Hydrogen bond donors (N-H and O-H groups)"
    )
    hba: int = Field(
        ..., 
        ge=0,
        description="Hydrogen bond acceptors (N and O atoms)"
    )
    tpsa: float = Field(
        ..., 
        ge=0.0,
        description="Topological polar surface area in Ų"
    )
    rotatable_bonds: int = Field(
        ..., 
        ge=0,
        description="Number of rotatable bonds"
    )
    aromatic_rings: int = Field(
        ..., 
        ge=0,
        description="Number of aromatic rings"
    )
    lipinski_violations: int = Field(
        ..., 
        ge=0, 
        le=4,
        description="Number of Lipinski Rule of Five violations (0-4)"
    )
    drug_likeness_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Drug-likeness score (0-1)"
    )


class ToxicityAssessment(BaseModel):
    """Toxicity screening results based on structural alerts.
    
    Contains toxicophore detection results and risk classification.
    """
    toxicity_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Toxicity score (0-1)"
    )
    risk_level: str = Field(
        ..., 
        description="Risk classification: low, medium, or high"
    )
    detected_toxicophores: List[str] = Field(
        default_factory=list,
        description="List of detected toxic substructures"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Toxicity warnings and recommendations"
    )
    
    @field_validator('risk_level')
    @classmethod
    def validate_risk_level(cls, v: str) -> str:
        """Ensure risk level is one of the allowed values."""
        allowed = {'low', 'medium', 'high'}
        if v not in allowed:
            raise ValueError(f"Risk level must be one of {allowed}, got '{v}'")
        return v


class DrugCandidate(BaseModel):
    """Ranked drug candidate with complete analysis.
    
    Represents a molecule with all calculated properties, scores, and analysis.
    """
    molecule: Molecule = Field(..., description="Molecule information")
    target: Target = Field(..., description="Primary target information")
    properties: MolecularProperties = Field(..., description="Molecular properties")
    toxicity: ToxicityAssessment = Field(..., description="Toxicity assessment")
    binding_affinity_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Normalized binding affinity score (0-1)"
    )
    binding_confidence: float = Field(
        ..., 
        ge=0.6, 
        le=0.9,
        description="Confidence in binding measurement (0.6-0.9)"
    )
    composite_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Final ranking score (0-1)"
    )
    rank: int = Field(
        ..., 
        ge=1,
        description="Rank position in results (1-based)"
    )
    ai_analysis: Optional[str] = Field(
        None,
        description="AI-generated analysis text"
    )
    structure_2d_svg: str = Field(
        ..., 
        description="2D molecular structure as SVG"
    )


class DiscoveryResult(BaseModel):
    """Complete pipeline result with metadata.
    
    Contains all ranked candidates and execution metadata.
    """
    query: str = Field(..., description="Original disease query")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Query execution timestamp"
    )
    processing_time_seconds: float = Field(
        ..., 
        gt=0.0,
        description="Total processing time in seconds"
    )
    candidates: List[DrugCandidate] = Field(
        default_factory=list,
        description="Ranked list of drug candidates"
    )
    targets_found: int = Field(
        ..., 
        ge=0,
        description="Number of targets identified"
    )
    molecules_analyzed: int = Field(
        ..., 
        ge=0,
        description="Number of molecules analyzed"
    )
    api_version: str = Field(
        default="0.1.0",
        description="API version"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings about partial failures or low confidence"
    )


# API Request/Response Schemas

class DiscoveryRequest(BaseModel):
    """Request schema for drug discovery endpoint."""
    disease_name: str = Field(
        ..., 
        min_length=2, 
        max_length=200,
        description="Disease name to search for drug candidates"
    )


class DiscoveryResponse(BaseModel):
    """Response schema for drug discovery endpoint."""
    query: str = Field(..., description="Original disease query")
    timestamp: str = Field(..., description="Query execution timestamp (ISO format)")
    processing_time_seconds: float = Field(
        ..., 
        description="Total processing time in seconds"
    )
    candidates: List[DrugCandidate] = Field(
        ..., 
        description="Ranked list of drug candidates"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (targets found, molecules analyzed, etc.)"
    )
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings about partial failures or low confidence"
    )


class ErrorResponse(BaseModel):
    """Standard error response format."""
    error_code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Error timestamp (ISO format)"
    )
