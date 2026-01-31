"""Docking API router for molecular docking endpoints.

This module provides RESTful API endpoints for submitting, tracking,
and managing molecular docking jobs.
"""

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.database import get_db
from app.docking.models import (
    DockingJobStatus,
    DockingParams,
    GridBoxParams,
    DockingJob,
    DockingResult,
    DockingJobResponse,
)
from app.docking.service import (
    DockingService,
    JobNotFoundError,
    JobLimitExceededError,
    InvalidJobStateError,
    ESTIMATED_TIME_PER_JOB_SECONDS,
)


logger = logging.getLogger(__name__)


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class DockingSubmitRequest(BaseModel):
    """Request schema for submitting docking jobs.
    
    Supports both single candidate (candidate_id) and batch (candidate_ids) formats.
    """
    candidate_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=50,
        description="Single ChEMBL ID to dock"
    )
    candidate_ids: Optional[List[str]] = Field(
        default=None,
        min_length=1,
        max_length=20,
        description="List of ChEMBL IDs to dock (1-20 candidates)"
    )
    smiles: Optional[str] = Field(
        default=None,
        description="SMILES string for the candidate molecule"
    )
    target_uniprot_id: str = Field(
        ...,
        min_length=3,
        max_length=20,
        description="UniProt ID of the target protein"
    )
    disease_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Disease being treated"
    )
    grid_params: Optional[GridBoxParams] = Field(
        default=None,
        description="Custom grid box parameters (auto-calculated if not provided)"
    )
    docking_params: Optional[DockingParams] = Field(
        default=None,
        description="Custom docking parameters (uses defaults if not provided)"
    )
    
    def get_candidate_ids(self) -> List[str]:
        """Get list of candidate IDs from either field."""
        if self.candidate_ids:
            return self.candidate_ids
        elif self.candidate_id:
            return [self.candidate_id]
        return []


class DockingSubmitResponse(BaseModel):
    """Response schema for docking job submission."""
    job_ids: List[str] = Field(..., description="List of job IDs for tracking")
    message: str = Field(..., description="Status message")
    total_jobs: int = Field(..., description="Number of jobs submitted")
    estimated_time_seconds: int = Field(..., description="Estimated total time for all jobs")


class JobStatusResponse(BaseModel):
    """Response schema for job status query."""
    job_id: str = Field(..., description="Job identifier")
    status: DockingJobStatus = Field(..., description="Current job status")
    progress_percent: int = Field(..., description="Progress percentage (0-100)")
    queue_position: Optional[int] = Field(default=None, description="Position in queue (if queued)")
    estimated_time_remaining: Optional[int] = Field(
        default=None,
        description="Estimated time remaining in seconds"
    )
    error_message: Optional[str] = Field(default=None, description="Error message (if failed)")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(default=None, description="Job start timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Job completion timestamp")


class PoseResult(BaseModel):
    """Single docking pose result."""
    pose_number: int = Field(..., description="Pose number (1 = best)")
    binding_affinity: float = Field(..., description="Binding affinity in kcal/mol")
    rmsd_lb: float = Field(..., description="RMSD lower bound from best pose")
    rmsd_ub: float = Field(..., description="RMSD upper bound from best pose")
    pdbqt_data: Optional[str] = Field(default=None, description="PDBQT structure data")


class JobResultsResponse(BaseModel):
    """Response schema for job results query."""
    job_id: str = Field(..., description="Job identifier")
    status: DockingJobStatus = Field(..., description="Job status")
    candidate_id: str = Field(..., description="ChEMBL ID of the candidate")
    target_uniprot_id: str = Field(..., description="UniProt ID of the target")
    best_affinity: Optional[float] = Field(
        default=None,
        description="Best (most negative) binding affinity in kcal/mol"
    )
    num_poses: int = Field(..., description="Number of binding poses found")
    poses: List[PoseResult] = Field(..., description="List of docking poses")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    error_message: Optional[str] = Field(default=None, description="Error message (if failed)")


class JobHistoryItem(BaseModel):
    """Single job in history list."""
    job_id: str = Field(..., description="Job identifier")
    candidate_id: str = Field(..., description="ChEMBL ID")
    target_uniprot_id: str = Field(..., description="UniProt ID")
    status: DockingJobStatus = Field(..., description="Job status")
    best_affinity: Optional[float] = Field(default=None, description="Best binding affinity")
    created_at: datetime = Field(..., description="Creation timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")


class JobHistoryResponse(BaseModel):
    """Response schema for job history query."""
    jobs: List[JobHistoryItem] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs matching filters")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of jobs per page")
    total_pages: int = Field(..., description="Total number of pages")


class CancelJobResponse(BaseModel):
    """Response schema for job cancellation."""
    job_id: str = Field(..., description="Job identifier")
    status: DockingJobStatus = Field(..., description="New job status")
    message: str = Field(..., description="Status message")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error_code: str = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/api/docking", tags=["docking"])


async def get_docking_service(db: AsyncSession = Depends(get_db)) -> DockingService:
    """Dependency to get DockingService instance."""
    return DockingService(db)


# ============================================================================
# ENDPOINTS
# ============================================================================

# NOTE: The /submit endpoint is defined in main.py to avoid conflicts.
# The main.py version uses the tasks module directly for job execution.


@router.get(
    "/jobs/{job_id}/status",
    response_model=JobStatusResponse,
    responses={
        200: {"description": "Job status retrieved"},
        404: {"description": "Job not found", "model": ErrorResponse},
    },
    summary="Get job status",
    description="""
    Get the current status of a docking job.
    
    Returns:
    - Current status (queued, running, completed, failed, cancelled)
    - Progress percentage
    - Queue position (for queued jobs)
    - Estimated time remaining
    - Error message (for failed jobs)
    """
)
async def get_job_status(
    job_id: str,
    service: DockingService = Depends(get_docking_service),
) -> JobStatusResponse:
    """Get the status of a docking job.
    
    Args:
        job_id: The job identifier
        service: Docking service instance
    
    Returns:
        Job status information
    """
    try:
        status = await service.get_job_status(job_id)
        
        return JobStatusResponse(
            job_id=status.job_id,
            status=status.status,
            progress_percent=status.progress_percent,
            queue_position=status.queue_position,
            estimated_time_remaining=status.estimated_time_remaining,
            error_message=status.error_message,
            created_at=status.created_at,
            started_at=status.started_at,
            completed_at=status.completed_at,
        )
        
    except JobNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": f"Docking job not found: {job_id}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


@router.get(
    "/jobs/{job_id}/results",
    response_model=JobResultsResponse,
    responses={
        200: {"description": "Job results retrieved"},
        400: {"description": "Job not completed", "model": ErrorResponse},
        404: {"description": "Job not found", "model": ErrorResponse},
    },
    summary="Get job results",
    description="""
    Get the results of a completed docking job.
    
    Returns:
    - Binding affinity scores for all poses
    - PDBQT structure data for each pose
    - Summary statistics
    
    Note: Job must be in completed or failed state.
    """
)
async def get_job_results(
    job_id: str,
    service: DockingService = Depends(get_docking_service),
) -> JobResultsResponse:
    """Get the results of a completed docking job.
    
    Args:
        job_id: The job identifier
        service: Docking service instance
    
    Returns:
        Docking results with all poses
    """
    try:
        results = await service.get_job_results(job_id)
        
        poses = [
            PoseResult(
                pose_number=p.pose_number,
                binding_affinity=p.binding_affinity,
                rmsd_lb=p.rmsd_lb,
                rmsd_ub=p.rmsd_ub,
                pdbqt_data=p.pdbqt_data,
            )
            for p in results.poses
        ]
        
        return JobResultsResponse(
            job_id=results.job_id,
            status=results.status,
            candidate_id=results.candidate_id,
            target_uniprot_id=results.target_uniprot_id,
            best_affinity=results.best_affinity,
            num_poses=len(poses),
            poses=poses,
            completed_at=results.completed_at,
            error_message=results.error_message,
        )
        
    except JobNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": f"Docking job not found: {job_id}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except InvalidJobStateError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "JOB_NOT_COMPLETED",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


@router.delete(
    "/jobs/{job_id}",
    response_model=CancelJobResponse,
    responses={
        200: {"description": "Job cancelled successfully"},
        400: {"description": "Job cannot be cancelled", "model": ErrorResponse},
        404: {"description": "Job not found", "model": ErrorResponse},
    },
    summary="Cancel a job",
    description="""
    Cancel a queued or running docking job.
    
    - Queued jobs are removed from the queue
    - Running jobs are terminated
    - Completed/failed jobs cannot be cancelled
    """
)
async def cancel_job(
    job_id: str,
    service: DockingService = Depends(get_docking_service),
    user_id: Optional[str] = None,  # TODO: Get from auth
) -> CancelJobResponse:
    """Cancel a docking job.
    
    Args:
        job_id: The job identifier
        service: Docking service instance
        user_id: User ID for authorization check
    
    Returns:
        Cancellation confirmation
    """
    try:
        await service.cancel_job(job_id, user_id=user_id)
        
        logger.info(f"Cancelled docking job {job_id}")
        
        return CancelJobResponse(
            job_id=job_id,
            status=DockingJobStatus.CANCELLED,
            message="Job cancelled successfully",
        )
        
    except JobNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "JOB_NOT_FOUND",
                "message": f"Docking job not found: {job_id}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
    except InvalidJobStateError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "CANNOT_CANCEL",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


@router.get(
    "/jobs",
    response_model=JobHistoryResponse,
    responses={
        200: {"description": "Job history retrieved"},
    },
    summary="Get job history",
    description="""
    Get the current user's docking job history.
    
    Supports filtering by:
    - Status (queued, running, completed, failed, cancelled)
    - Target protein (UniProt ID)
    - Date range
    
    Results are paginated (default 20 per page).
    """
)
async def get_job_history(
    service: DockingService = Depends(get_docking_service),
    user_id: Optional[str] = None,  # TODO: Get from auth
    status: Optional[DockingJobStatus] = Query(default=None, description="Filter by status"),
    target_uniprot_id: Optional[str] = Query(default=None, description="Filter by target protein"),
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Jobs per page"),
) -> JobHistoryResponse:
    """Get the user's docking job history.
    
    Args:
        service: Docking service instance
        user_id: User ID for filtering
        status: Optional status filter
        target_uniprot_id: Optional target filter
        page: Page number (1-indexed)
        page_size: Number of jobs per page
    
    Returns:
        Paginated job history
    """
    # For development: if no user_id, return all jobs
    # In production, this should require authentication
    offset = (page - 1) * page_size
    
    jobs, total = await service.get_user_job_history(
        user_id=user_id,  # Pass None to get all jobs
        status=status,
        target_uniprot_id=target_uniprot_id,
        limit=page_size,
        offset=offset,
    )
    
    job_items = [
        JobHistoryItem(
            job_id=job.id,
            candidate_id=job.candidate_id,
            target_uniprot_id=job.target_uniprot_id,
            status=DockingJobStatus(job.status),
            best_affinity=job.best_affinity,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
        for job in jobs
    ]
    
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    
    return JobHistoryResponse(
        jobs=job_items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
