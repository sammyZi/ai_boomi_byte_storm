"""Docking service layer for managing docking jobs.

This module provides a high-level service interface for submitting,
tracking, and managing molecular docking jobs.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.docking.models import (
    DockingJobStatus,
    DockingParams,
    GridBoxParams,
    DockingJob,
    DockingResult,
    DockingJobResponse,
    DockingStatusResponse,
    DockingResultsSummary,
)
from app.docking.db_models import DockingJobDB, DockingResultDB


logger = logging.getLogger(__name__)


# Constants
MAX_QUEUED_JOBS_PER_USER = 100
ESTIMATED_TIME_PER_JOB_SECONDS = 300  # 5 minutes average


@dataclass
class JobSubmissionResult:
    """Result of job submission."""
    job_id: str
    status: DockingJobStatus
    queue_position: int
    estimated_time_seconds: int


@dataclass
class JobStatusInfo:
    """Information about job status."""
    job_id: str
    status: DockingJobStatus
    progress_percent: int
    queue_position: Optional[int]
    estimated_time_remaining: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]


@dataclass
class JobResults:
    """Complete job results."""
    job_id: str
    status: DockingJobStatus
    candidate_id: str
    target_uniprot_id: str
    best_affinity: Optional[float]
    poses: List[DockingResult]
    completed_at: Optional[datetime]
    error_message: Optional[str]


class DockingServiceError(Exception):
    """Base exception for docking service errors."""
    pass


class JobNotFoundError(DockingServiceError):
    """Raised when a job is not found."""
    pass


class JobLimitExceededError(DockingServiceError):
    """Raised when user has too many queued jobs."""
    pass


class InvalidJobStateError(DockingServiceError):
    """Raised when job is in an invalid state for the operation."""
    pass


class DockingService:
    """Service for managing molecular docking jobs.
    
    Provides methods for submitting jobs, checking status, retrieving
    results, and managing job lifecycle.
    
    Attributes:
        db: Async database session
    """
    
    def __init__(self, db: AsyncSession):
        """Initialize the docking service.
        
        Args:
            db: Async database session for persistence
        """
        self.db = db
    
    async def submit_docking_job(
        self,
        candidate_id: str,
        target_uniprot_id: str,
        disease_name: Optional[str] = None,
        user_id: Optional[str] = None,
        grid_params: Optional[GridBoxParams] = None,
        docking_params: Optional[DockingParams] = None,
    ) -> JobSubmissionResult:
        """Submit a new docking job.
        
        Creates a new docking job in the database and returns its ID.
        The job will be picked up by a Celery worker for execution.
        
        Args:
            candidate_id: ChEMBL ID of the drug candidate
            target_uniprot_id: UniProt ID of the target protein
            disease_name: Optional disease name
            user_id: Optional user ID for job ownership
            grid_params: Optional custom grid box parameters
            docking_params: Optional custom docking parameters
        
        Returns:
            JobSubmissionResult with job ID, status, and queue info
        
        Raises:
            JobLimitExceededError: If user has too many queued jobs
        """
        # Check user job limits
        if user_id:
            queued_count = await self._count_user_queued_jobs(user_id)
            if queued_count >= MAX_QUEUED_JOBS_PER_USER:
                raise JobLimitExceededError(
                    f"User has {queued_count} queued jobs. "
                    f"Maximum is {MAX_QUEUED_JOBS_PER_USER}."
                )
        
        # Create new job record
        job = DockingJobDB(
            candidate_id=candidate_id,
            target_uniprot_id=target_uniprot_id,
            disease_name=disease_name,
            user_id=user_id,
            status=DockingJobStatus.QUEUED.value,
        )
        
        # Set parameters if provided
        if grid_params:
            job.grid_params = grid_params
        if docking_params:
            job.docking_params = docking_params
        
        self.db.add(job)
        await self.db.flush()  # Get the generated ID
        
        # Get queue position
        queue_position = await self._get_queue_position(job.id)
        
        # Estimate completion time
        estimated_time = queue_position * ESTIMATED_TIME_PER_JOB_SECONDS
        
        logger.info(
            f"Submitted docking job {job.id} for candidate {candidate_id}, "
            f"queue position {queue_position}"
        )
        
        return JobSubmissionResult(
            job_id=job.id,
            status=DockingJobStatus.QUEUED,
            queue_position=queue_position,
            estimated_time_seconds=estimated_time,
        )
    
    async def submit_batch_jobs(
        self,
        candidate_ids: List[str],
        target_uniprot_id: str,
        disease_name: Optional[str] = None,
        user_id: Optional[str] = None,
        grid_params: Optional[GridBoxParams] = None,
        docking_params: Optional[DockingParams] = None,
    ) -> List[JobSubmissionResult]:
        """Submit multiple docking jobs at once.
        
        Args:
            candidate_ids: List of ChEMBL IDs
            target_uniprot_id: UniProt ID of the target protein
            disease_name: Optional disease name
            user_id: Optional user ID for job ownership
            grid_params: Optional custom grid box parameters
            docking_params: Optional custom docking parameters
        
        Returns:
            List of JobSubmissionResult objects
        
        Raises:
            JobLimitExceededError: If total would exceed user limit
        """
        # Check user job limits for batch
        if user_id:
            queued_count = await self._count_user_queued_jobs(user_id)
            total_after = queued_count + len(candidate_ids)
            if total_after > MAX_QUEUED_JOBS_PER_USER:
                raise JobLimitExceededError(
                    f"Cannot submit {len(candidate_ids)} jobs. "
                    f"User has {queued_count} queued jobs. "
                    f"Maximum is {MAX_QUEUED_JOBS_PER_USER}."
                )
        
        results = []
        for candidate_id in candidate_ids:
            result = await self.submit_docking_job(
                candidate_id=candidate_id,
                target_uniprot_id=target_uniprot_id,
                disease_name=disease_name,
                user_id=user_id,
                grid_params=grid_params,
                docking_params=docking_params,
            )
            results.append(result)
        
        return results
    
    async def get_job_status(self, job_id: str) -> JobStatusInfo:
        """Get the current status of a docking job.
        
        Args:
            job_id: The job identifier
        
        Returns:
            JobStatusInfo with current status and progress
        
        Raises:
            JobNotFoundError: If job doesn't exist
        """
        job = await self._get_job(job_id)
        
        # Calculate progress based on status
        progress = self._calculate_progress(job)
        
        # Get queue position if queued
        queue_position = None
        estimated_time = None
        if job.status == DockingJobStatus.QUEUED.value:
            queue_position = await self._get_queue_position(job_id)
            estimated_time = queue_position * ESTIMATED_TIME_PER_JOB_SECONDS
        elif job.status == DockingJobStatus.RUNNING.value:
            # Estimate remaining time for running job
            if job.started_at:
                elapsed = (datetime.utcnow() - job.started_at).total_seconds()
                estimated_time = max(0, ESTIMATED_TIME_PER_JOB_SECONDS - int(elapsed))
        
        return JobStatusInfo(
            job_id=job.id,
            status=DockingJobStatus(job.status),
            progress_percent=progress,
            queue_position=queue_position,
            estimated_time_remaining=estimated_time,
            error_message=job.error_message,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
        )
    
    async def get_job_results(self, job_id: str) -> JobResults:
        """Get the results of a completed docking job.
        
        Args:
            job_id: The job identifier
        
        Returns:
            JobResults with all poses and binding affinities
        
        Raises:
            JobNotFoundError: If job doesn't exist
            InvalidJobStateError: If job is not completed
        """
        job = await self._get_job(job_id)
        
        if job.status not in (DockingJobStatus.COMPLETED.value, DockingJobStatus.FAILED.value):
            raise InvalidJobStateError(
                f"Job {job_id} is not finished. Current status: {job.status}"
            )
        
        # Convert DB results to Pydantic models
        poses = [
            DockingResult(
                pose_number=r.pose_number,
                binding_affinity=r.binding_affinity,
                rmsd_lb=r.rmsd_lb,
                rmsd_ub=r.rmsd_ub,
                pdbqt_data=r.pdbqt_data,
            )
            for r in sorted(job.results, key=lambda x: x.pose_number)
        ]
        
        return JobResults(
            job_id=job.id,
            status=DockingJobStatus(job.status),
            candidate_id=job.candidate_id,
            target_uniprot_id=job.target_uniprot_id,
            best_affinity=job.best_affinity,
            poses=poses,
            completed_at=job.completed_at,
            error_message=job.error_message,
        )
    
    async def cancel_job(self, job_id: str, user_id: Optional[str] = None) -> bool:
        """Cancel a queued or running job.
        
        Args:
            job_id: The job identifier
            user_id: Optional user ID for authorization check
        
        Returns:
            True if job was cancelled successfully
        
        Raises:
            JobNotFoundError: If job doesn't exist
            InvalidJobStateError: If job cannot be cancelled
        """
        job = await self._get_job(job_id)
        
        # Check ownership if user_id provided
        if user_id and job.user_id and job.user_id != user_id:
            raise JobNotFoundError(f"Job {job_id} not found")
        
        # Check if job can be cancelled
        if job.status not in (DockingJobStatus.QUEUED.value, DockingJobStatus.RUNNING.value):
            raise InvalidJobStateError(
                f"Cannot cancel job in {job.status} state"
            )
        
        # Update status
        job.status = DockingJobStatus.CANCELLED.value
        job.completed_at = datetime.utcnow()
        job.error_message = "Job cancelled by user"
        
        await self.db.flush()
        
        logger.info(f"Cancelled docking job {job_id}")
        
        return True
    
    async def get_user_job_history(
        self,
        user_id: Optional[str] = None,
        status: Optional[DockingJobStatus] = None,
        target_uniprot_id: Optional[str] = None,
        since: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[DockingJobDB], int]:
        """Get a user's job history with optional filtering.
        
        Args:
            user_id: The user identifier (None returns all jobs - for development)
            status: Optional filter by job status
            target_uniprot_id: Optional filter by target protein
            since: Optional filter for jobs created after this date
            limit: Maximum number of jobs to return
            offset: Number of jobs to skip (for pagination)
        
        Returns:
            Tuple of (list of jobs, total count)
        """
        # Build query conditions
        conditions = []
        
        # Only filter by user_id if provided
        if user_id:
            conditions.append(DockingJobDB.user_id == user_id)
        
        if status:
            conditions.append(DockingJobDB.status == status.value)
        if target_uniprot_id:
            conditions.append(DockingJobDB.target_uniprot_id == target_uniprot_id)
        if since:
            conditions.append(DockingJobDB.created_at >= since)
        
        # Get total count
        if conditions:
            count_query = select(func.count(DockingJobDB.id)).where(and_(*conditions))
        else:
            count_query = select(func.count(DockingJobDB.id))
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar() or 0
        
        # Get jobs with pagination
        if conditions:
            query = (
                select(DockingJobDB)
                .where(and_(*conditions))
                .order_by(desc(DockingJobDB.created_at))
                .limit(limit)
                .offset(offset)
            )
        else:
            query = (
                select(DockingJobDB)
                .order_by(desc(DockingJobDB.created_at))
                .limit(limit)
                .offset(offset)
            )
        result = await self.db.execute(query)
        jobs = list(result.scalars().all())
        
        return jobs, total_count
    
    async def get_job_by_id(self, job_id: str) -> Optional[DockingJobDB]:
        """Get a job by its ID.
        
        Args:
            job_id: The job identifier
        
        Returns:
            The job or None if not found
        """
        query = select(DockingJobDB).where(DockingJobDB.id == job_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_job_status(
        self,
        job_id: str,
        status: DockingJobStatus,
        error_message: Optional[str] = None,
        best_affinity: Optional[float] = None,
    ) -> DockingJobDB:
        """Update a job's status.
        
        Args:
            job_id: The job identifier
            status: New status
            error_message: Optional error message
            best_affinity: Optional best binding affinity
        
        Returns:
            Updated job
        
        Raises:
            JobNotFoundError: If job doesn't exist
        """
        job = await self._get_job(job_id)
        
        job.status = status.value
        
        if status == DockingJobStatus.RUNNING and not job.started_at:
            job.started_at = datetime.utcnow()
        elif status in (DockingJobStatus.COMPLETED, DockingJobStatus.FAILED, DockingJobStatus.CANCELLED):
            job.completed_at = datetime.utcnow()
        
        if error_message:
            job.error_message = error_message
        if best_affinity is not None:
            job.best_affinity = best_affinity
        
        await self.db.flush()
        
        return job
    
    async def add_job_result(
        self,
        job_id: str,
        pose_number: int,
        binding_affinity: float,
        rmsd_lb: float = 0.0,
        rmsd_ub: float = 0.0,
        pdbqt_data: Optional[str] = None,
        pdbqt_file_path: Optional[str] = None,
    ) -> DockingResultDB:
        """Add a docking result to a job.
        
        Args:
            job_id: The job identifier
            pose_number: Pose number (1 = best)
            binding_affinity: Binding affinity in kcal/mol
            rmsd_lb: RMSD lower bound
            rmsd_ub: RMSD upper bound
            pdbqt_data: Optional PDBQT data
            pdbqt_file_path: Optional path to PDBQT file
        
        Returns:
            Created result
        """
        result = DockingResultDB(
            job_id=job_id,
            pose_number=pose_number,
            binding_affinity=binding_affinity,
            rmsd_lb=rmsd_lb,
            rmsd_ub=rmsd_ub,
            pdbqt_data=pdbqt_data,
            pdbqt_file_path=pdbqt_file_path,
        )
        
        self.db.add(result)
        await self.db.flush()
        
        return result
    
    async def _get_job(self, job_id: str) -> DockingJobDB:
        """Get a job by ID or raise error.
        
        Args:
            job_id: The job identifier
        
        Returns:
            The job
        
        Raises:
            JobNotFoundError: If job doesn't exist
        """
        job = await self.get_job_by_id(job_id)
        if not job:
            raise JobNotFoundError(f"Job {job_id} not found")
        return job
    
    async def _count_user_queued_jobs(self, user_id: str) -> int:
        """Count the number of queued jobs for a user.
        
        Args:
            user_id: The user identifier
        
        Returns:
            Number of queued jobs
        """
        query = select(func.count(DockingJobDB.id)).where(
            and_(
                DockingJobDB.user_id == user_id,
                DockingJobDB.status.in_([
                    DockingJobStatus.QUEUED.value,
                    DockingJobStatus.RUNNING.value,
                ])
            )
        )
        result = await self.db.execute(query)
        return result.scalar() or 0
    
    async def _get_queue_position(self, job_id: str) -> int:
        """Get the queue position of a job.
        
        Args:
            job_id: The job identifier
        
        Returns:
            Queue position (1 = next to run)
        """
        # Count jobs that are queued and created before this job
        job = await self._get_job(job_id)
        
        query = select(func.count(DockingJobDB.id)).where(
            and_(
                DockingJobDB.status == DockingJobStatus.QUEUED.value,
                DockingJobDB.created_at <= job.created_at,
            )
        )
        result = await self.db.execute(query)
        return result.scalar() or 1
    
    def _calculate_progress(self, job: DockingJobDB) -> int:
        """Calculate job progress percentage.
        
        Args:
            job: The job to check
        
        Returns:
            Progress as percentage (0-100)
        """
        status = job.status
        
        if status == DockingJobStatus.QUEUED.value:
            return 0
        elif status == DockingJobStatus.RUNNING.value:
            # Estimate progress based on elapsed time
            if job.started_at:
                elapsed = (datetime.utcnow() - job.started_at).total_seconds()
                progress = min(95, int(elapsed / ESTIMATED_TIME_PER_JOB_SECONDS * 100))
                return progress
            return 10  # Just started
        elif status == DockingJobStatus.COMPLETED.value:
            return 100
        elif status == DockingJobStatus.FAILED.value:
            return 100
        elif status == DockingJobStatus.CANCELLED.value:
            return 100
        
        return 0


async def get_docking_service(db: AsyncSession) -> DockingService:
    """Factory function to create a DockingService instance.
    
    Args:
        db: Async database session
    
    Returns:
        DockingService instance
    """
    return DockingService(db)
