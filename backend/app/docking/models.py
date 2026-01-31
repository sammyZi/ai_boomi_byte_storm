"""Data models for molecular docking jobs and results.

This module defines Pydantic models for docking job management,
including job status tracking, parameters, and results storage.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DockingJobStatus(str, Enum):
    """Status of a docking job."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GridBoxParams(BaseModel):
    """Parameters for the docking grid box.
    
    Defines the 3D search space for molecular docking.
    """
    center_x: float = Field(..., description="X coordinate of grid box center (Å)")
    center_y: float = Field(..., description="Y coordinate of grid box center (Å)")
    center_z: float = Field(..., description="Z coordinate of grid box center (Å)")
    size_x: float = Field(default=25.0, ge=10.0, le=50.0, description="Grid box size in X direction (Å)")
    size_y: float = Field(default=25.0, ge=10.0, le=50.0, description="Grid box size in Y direction (Å)")
    size_z: float = Field(default=25.0, ge=10.0, le=50.0, description="Grid box size in Z direction (Å)")


class DockingParams(BaseModel):
    """Parameters for AutoDock Vina execution.
    
    Controls the docking algorithm behavior.
    """
    exhaustiveness: int = Field(default=8, ge=1, le=32, description="Search exhaustiveness (higher = more thorough)")
    num_modes: int = Field(default=9, ge=1, le=20, description="Maximum number of binding poses to generate")
    energy_range: float = Field(default=3.0, ge=1.0, le=10.0, description="Energy range for pose selection (kcal/mol)")
    cpu: int = Field(default=4, ge=1, le=16, description="Number of CPU cores to use")
    seed: Optional[int] = Field(default=None, description="Random seed for reproducibility")


class DockingResult(BaseModel):
    """Single docking pose result.
    
    Represents one binding pose from AutoDock Vina output.
    """
    pose_number: int = Field(..., ge=1, description="Pose number (1 = best)")
    binding_affinity: float = Field(..., description="Binding affinity (kcal/mol, more negative = better)")
    rmsd_lb: float = Field(default=0.0, ge=0.0, description="RMSD lower bound from best pose")
    rmsd_ub: float = Field(default=0.0, ge=0.0, description="RMSD upper bound from best pose")
    pdbqt_data: Optional[str] = Field(default=None, description="PDBQT format atomic coordinates")


class DockingJob(BaseModel):
    """Docking job with status and results.
    
    Tracks the complete lifecycle of a docking job from submission
    to completion, including all parameters and results.
    """
    id: str = Field(..., description="Unique job identifier")
    candidate_id: str = Field(..., description="ChEMBL ID of the drug candidate")
    target_uniprot_id: str = Field(..., description="UniProt ID of the target protein")
    disease_name: str = Field(..., description="Disease being treated")
    
    # Status tracking
    status: DockingJobStatus = Field(default=DockingJobStatus.QUEUED, description="Current job status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Job creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Job completion timestamp")
    
    # Parameters
    grid_params: Optional[GridBoxParams] = Field(default=None, description="Grid box parameters")
    docking_params: DockingParams = Field(default_factory=DockingParams, description="Docking parameters")
    
    # Results
    results: List[DockingResult] = Field(default_factory=list, description="List of docking poses")
    best_affinity: Optional[float] = Field(default=None, description="Best (most negative) binding affinity")
    error_message: Optional[str] = Field(default=None, description="Error message if job failed")
    
    # File paths (internal use)
    protein_pdbqt_path: Optional[str] = Field(default=None, description="Path to protein PDBQT file")
    ligand_pdbqt_path: Optional[str] = Field(default=None, description="Path to ligand PDBQT file")
    output_pdbqt_path: Optional[str] = Field(default=None, description="Path to output PDBQT file")
    
    class Config:
        use_enum_values = True


class DockingJobRequest(BaseModel):
    """Request to submit a new docking job."""
    candidate_id: str = Field(..., description="ChEMBL ID of the drug candidate")
    target_uniprot_id: str = Field(..., description="UniProt ID of the target protein")
    disease_name: str = Field(..., description="Disease being treated")
    smiles: str = Field(..., description="SMILES string of the ligand molecule")
    grid_params: Optional[GridBoxParams] = Field(default=None, description="Custom grid box parameters (auto-calculated if not provided)")
    docking_params: Optional[DockingParams] = Field(default=None, description="Custom docking parameters")


class DockingJobResponse(BaseModel):
    """Response after submitting a docking job."""
    job_id: str = Field(..., description="Unique job identifier for tracking")
    status: DockingJobStatus = Field(..., description="Current job status")
    message: str = Field(..., description="Status message")
    estimated_time_seconds: Optional[int] = Field(default=None, description="Estimated completion time")


class DockingStatusResponse(BaseModel):
    """Response for docking job status query."""
    job: DockingJob = Field(..., description="Full docking job details")
    queue_position: Optional[int] = Field(default=None, description="Position in queue (if queued)")


class DockingResultsSummary(BaseModel):
    """Summary of docking results for display."""
    job_id: str = Field(..., description="Job identifier")
    candidate_id: str = Field(..., description="ChEMBL ID")
    candidate_name: str = Field(..., description="Molecule name")
    target_gene: str = Field(..., description="Target gene symbol")
    best_affinity: float = Field(..., description="Best binding affinity (kcal/mol)")
    num_poses: int = Field(..., description="Number of poses generated")
    status: DockingJobStatus = Field(..., description="Job status")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
