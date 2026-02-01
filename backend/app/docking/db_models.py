"""SQLAlchemy database models for docking jobs and results.

This module defines the database tables for persisting docking jobs
and their results, with proper relationships and indexes for efficient queries.
"""

from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
import json
import uuid

from sqlalchemy import (
    Column, String, Integer, Float, Text, DateTime, Enum, ForeignKey,
    Index, JSON, event
)
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.database import Base
from app.docking.models import DockingJobStatus, GridBoxParams, DockingParams


def generate_uuid() -> str:
    """Generate a new UUID string."""
    return str(uuid.uuid4())


class DockingJobDB(Base):
    """Database model for docking jobs.
    
    Stores the complete state of a docking job including parameters,
    status, and timestamps for tracking.
    
    Attributes:
        id: Unique job identifier (UUID)
        candidate_id: ChEMBL ID of the drug candidate
        target_uniprot_id: UniProt ID of the target protein
        disease_name: Name of the disease being treated
        user_id: Optional user identifier for job ownership
        status: Current job status (queued, running, completed, failed, cancelled)
        created_at: Timestamp when job was created
        started_at: Timestamp when job started running
        completed_at: Timestamp when job completed or failed
        grid_params: JSON-serialized grid box parameters
        docking_params: JSON-serialized docking parameters
        error_message: Error message if job failed
        protein_pdbqt_path: Path to protein PDBQT file
        ligand_pdbqt_path: Path to ligand PDBQT file
        output_pdbqt_path: Path to output PDBQT file
        best_affinity: Best binding affinity from results
        results: Relationship to DockingResultDB
    """
    __tablename__ = "docking_jobs"
    
    # Primary key (UUID generated automatically)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    
    # Job identification
    candidate_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    target_uniprot_id: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    disease_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, default=None)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    
    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=DockingJobStatus.QUEUED.value,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    # Parameters (stored as JSON)
    grid_params_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    docking_params_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Error handling
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # File paths
    protein_pdbqt_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ligand_pdbqt_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    output_pdbqt_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    # Results summary
    best_affinity: Mapped[Optional[float]] = mapped_column(Float, nullable=True, index=True)
    
    # Relationships
    results: Mapped[List["DockingResultDB"]] = relationship(
        "DockingResultDB",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # Indexes for common queries
    __table_args__ = (
        Index('ix_docking_jobs_user_status', 'user_id', 'status'),
        Index('ix_docking_jobs_candidate_target', 'candidate_id', 'target_uniprot_id'),
        Index('ix_docking_jobs_status_created', 'status', 'created_at'),
    )
    
    @property
    def grid_params(self) -> Optional[GridBoxParams]:
        """Deserialize grid parameters from JSON."""
        if self.grid_params_json:
            return GridBoxParams(**json.loads(self.grid_params_json))
        return None
    
    @grid_params.setter
    def grid_params(self, value: Optional[GridBoxParams]) -> None:
        """Serialize grid parameters to JSON."""
        if value:
            self.grid_params_json = value.model_dump_json()
        else:
            self.grid_params_json = None
    
    @property
    def docking_params(self) -> Optional[DockingParams]:
        """Deserialize docking parameters from JSON."""
        if self.docking_params_json:
            return DockingParams(**json.loads(self.docking_params_json))
        return None
    
    @docking_params.setter
    def docking_params(self, value: Optional[DockingParams]) -> None:
        """Serialize docking parameters to JSON."""
        if value:
            self.docking_params_json = value.model_dump_json()
        else:
            self.docking_params_json = None
    
    def __repr__(self) -> str:
        return (
            f"<DockingJobDB(id={self.id!r}, candidate_id={self.candidate_id!r}, "
            f"status={self.status!r})>"
        )


class DockingResultDB(Base):
    """Database model for individual docking results (poses).
    
    Stores each binding pose from a docking job with its
    binding affinity and structural data.
    
    Attributes:
        id: Auto-incrementing primary key
        job_id: Foreign key to parent DockingJobDB
        pose_number: Pose number (1 = best)
        binding_affinity: Binding energy in kcal/mol (more negative = better)
        rmsd_lb: RMSD lower bound from best pose
        rmsd_ub: RMSD upper bound from best pose
        pdbqt_file_path: Path to PDBQT file for this pose
        pdbqt_data: Optional inline PDBQT data
        created_at: Timestamp when result was created
        job: Relationship to parent DockingJobDB
    """
    __tablename__ = "docking_results"
    
    # Primary key
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to job
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("docking_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Pose data
    pose_number: Mapped[int] = mapped_column(Integer, nullable=False)
    binding_affinity: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    rmsd_lb: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    rmsd_ub: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    
    # Structure data
    pdbqt_file_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pdbqt_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )
    
    # Relationship back to job
    job: Mapped["DockingJobDB"] = relationship(
        "DockingJobDB",
        back_populates="results"
    )
    
    # Indexes
    __table_args__ = (
        Index('ix_docking_results_job_pose', 'job_id', 'pose_number'),
        Index('ix_docking_results_affinity', 'binding_affinity'),
    )
    
    def __repr__(self) -> str:
        return (
            f"<DockingResultDB(id={self.id!r}, job_id={self.job_id!r}, "
            f"pose={self.pose_number!r}, affinity={self.binding_affinity!r})>"
        )
