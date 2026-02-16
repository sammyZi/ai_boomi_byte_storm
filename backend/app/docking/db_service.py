"""Database service for docking jobs.

This module provides database operations for persisting docking jobs
and results, replacing the in-memory storage.
"""

import logging
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.docking.models import (
    DockingJob,
    DockingJobStatus,
    DockingResult,
    GridBoxParams,
    DockingParams
)
from app.docking.db_models import DockingJobDB, DockingResultDB

logger = logging.getLogger(__name__)


class DockingJobService:
    """Service for managing docking jobs in the database."""
    
    def __init__(self, db: AsyncSession):
        """Initialize the service with a database session.
        
        Args:
            db: SQLAlchemy async session
        """
        self.db = db
    
    async def create_job(
        self,
        job_id: str,
        candidate_id: str,
        target_uniprot_id: str,
        disease_name: str,
        grid_params: Optional[GridBoxParams] = None,
        docking_params: Optional[DockingParams] = None
    ) -> DockingJob:
        """Create a new docking job in the database.
        
        Args:
            job_id: Unique job identifier
            candidate_id: ChEMBL ID of the drug candidate
            target_uniprot_id: UniProt ID of the target protein
            disease_name: Name of the disease
            grid_params: Optional custom grid box parameters
            docking_params: Optional custom docking parameters
        
        Returns:
            Created DockingJob
        """
        db_job = DockingJobDB(
            id=job_id,
            candidate_id=candidate_id,
            target_uniprot_id=target_uniprot_id,
            disease_name=disease_name,
            status=DockingJobStatus.QUEUED.value,
            created_at=datetime.now(timezone.utc)
        )
        
        # Set parameters
        if grid_params:
            db_job.grid_params = grid_params
        if docking_params:
            db_job.docking_params = docking_params
        else:
            db_job.docking_params = DockingParams()
        
        self.db.add(db_job)
        await self.db.commit()
        await self.db.refresh(db_job)
        
        logger.info(f"Created docking job {job_id} in database")
        return self._db_to_model(db_job)
    
    async def get_job(self, job_id: str) -> Optional[DockingJob]:
        """Get a docking job by ID.
        
        Args:
            job_id: Job identifier
        
        Returns:
            DockingJob or None if not found
        """
        stmt = select(DockingJobDB).where(DockingJobDB.id == job_id).options(
            selectinload(DockingJobDB.results)
        )
        result = await self.db.execute(stmt)
        db_job = result.scalar_one_or_none()
        
        if not db_job:
            return None
        
        return self._db_to_model(db_job)
    
    async def update_job(self, job: DockingJob) -> None:
        """Update a docking job in the database.
        
        Args:
            job: DockingJob with updated data
        """
        stmt = select(DockingJobDB).where(DockingJobDB.id == job.id)
        result = await self.db.execute(stmt)
        db_job = result.scalar_one_or_none()
        
        if not db_job:
            raise ValueError(f"Job not found: {job.id}")
        
        # Update fields
        db_job.status = job.status.value if hasattr(job.status, 'value') else job.status
        db_job.started_at = job.started_at
        db_job.completed_at = job.completed_at
        db_job.error_message = job.error_message
        db_job.protein_pdbqt_path = job.protein_pdbqt_path
        db_job.ligand_pdbqt_path = job.ligand_pdbqt_path
        db_job.output_pdbqt_path = job.output_pdbqt_path
        db_job.protein_pdbqt_data = job.protein_pdbqt_data
        db_job.best_affinity = job.best_affinity
        db_job.progress_percent = job.progress_percent
        db_job.current_step = job.current_step
        db_job.console_output = job.console_output
        
        # Update parameters
        if job.grid_params:
            db_job.grid_params = job.grid_params
        if job.docking_params:
            db_job.docking_params = job.docking_params
        
        await self.db.commit()
        logger.debug(f"Updated job {job.id} in database")
    
    async def save_results(self, job_id: str, results: List[DockingResult]) -> None:
        """Save docking results to the database.
        
        Args:
            job_id: Job identifier
            results: List of docking results
        """
        # Delete existing results
        await self.db.execute(
            delete(DockingResultDB).where(DockingResultDB.job_id == job_id)
        )
        
        # Add new results
        for result in results:
            db_result = DockingResultDB(
                job_id=job_id,
                pose_number=result.pose_number,
                binding_affinity=result.binding_affinity,
                rmsd_lb=result.rmsd_lb,
                rmsd_ub=result.rmsd_ub,
                pdbqt_data=result.pdbqt_data,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(db_result)
        
        await self.db.commit()
        logger.info(f"Saved {len(results)} results for job {job_id}")
    
    async def get_all_jobs(self) -> List[DockingJob]:
        """Get all docking jobs from the database.
        
        Returns:
            List of all DockingJob objects
        """
        stmt = select(DockingJobDB).options(selectinload(DockingJobDB.results))
        result = await self.db.execute(stmt)
        db_jobs = result.scalars().all()
        
        return [self._db_to_model(db_job) for db_job in db_jobs]
    
    async def get_jobs_by_status(self, status: DockingJobStatus) -> List[DockingJob]:
        """Get all jobs with a specific status.
        
        Args:
            status: Job status to filter by
        
        Returns:
            List of DockingJob objects
        """
        stmt = select(DockingJobDB).where(
            DockingJobDB.status == status.value
        ).options(selectinload(DockingJobDB.results))
        result = await self.db.execute(stmt)
        db_jobs = result.scalars().all()
        
        return [self._db_to_model(db_job) for db_job in db_jobs]
    
    async def delete_job(self, job_id: str) -> bool:
        """Delete a docking job from the database.
        
        Args:
            job_id: Job identifier
        
        Returns:
            True if job was deleted, False if not found
        """
        stmt = delete(DockingJobDB).where(DockingJobDB.id == job_id)
        result = await self.db.execute(stmt)
        await self.db.commit()
        
        return result.rowcount > 0
    
    def _db_to_model(self, db_job: DockingJobDB) -> DockingJob:
        """Convert database model to Pydantic model.
        
        Args:
            db_job: Database job object
        
        Returns:
            Pydantic DockingJob model
        """
        # Convert results
        results = []
        if db_job.results:
            for db_result in db_job.results:
                results.append(DockingResult(
                    pose_number=db_result.pose_number,
                    binding_affinity=db_result.binding_affinity,
                    rmsd_lb=db_result.rmsd_lb,
                    rmsd_ub=db_result.rmsd_ub,
                    pdbqt_data=db_result.pdbqt_data
                ))
        
        # Create Pydantic model
        return DockingJob(
            id=db_job.id,
            candidate_id=db_job.candidate_id,
            target_uniprot_id=db_job.target_uniprot_id,
            disease_name=db_job.disease_name or "",
            status=DockingJobStatus(db_job.status),
            created_at=db_job.created_at,
            started_at=db_job.started_at,
            completed_at=db_job.completed_at,
            progress_percent=db_job.progress_percent,
            current_step=db_job.current_step,
            console_output=db_job.console_output or "",
            grid_params=db_job.grid_params,
            docking_params=db_job.docking_params or DockingParams(),
            results=results,
            best_affinity=db_job.best_affinity,
            error_message=db_job.error_message,
            protein_pdbqt_path=db_job.protein_pdbqt_path,
            ligand_pdbqt_path=db_job.ligand_pdbqt_path,
            output_pdbqt_path=db_job.output_pdbqt_path,
            protein_pdbqt_data=db_job.protein_pdbqt_data
        )


# Synchronous wrapper for use in non-async contexts
class SyncDockingJobService:
    """Synchronous wrapper for database operations.
    
    This uses a thread pool to run async operations from sync contexts,
    avoiding the "asyncio.run() cannot be called from a running event loop" error.
    """
    
    def __init__(self):
        """Initialize the sync service."""
        from app.database import async_session_maker
        self.session_maker = async_session_maker
    
    def _run_async(self, coro):
        """Run an async coroutine from sync context.
        
        Uses a thread pool to avoid event loop conflicts.
        """
        import asyncio
        import concurrent.futures
        
        # Try to get the current event loop
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, use run_in_executor
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        except RuntimeError:
            # No running loop, safe to use asyncio.run
            return asyncio.run(coro)
    
    def create_job(
        self,
        job_id: str,
        candidate_id: str,
        target_uniprot_id: str,
        disease_name: str,
        grid_params: Optional[GridBoxParams] = None,
        docking_params: Optional[DockingParams] = None
    ) -> DockingJob:
        """Create a new docking job (sync wrapper)."""
        async def _create():
            async with self.session_maker() as session:
                service = DockingJobService(session)
                return await service.create_job(
                    job_id, candidate_id, target_uniprot_id, disease_name,
                    grid_params, docking_params
                )
        
        return self._run_async(_create())
    
    def get_job(self, job_id: str) -> Optional[DockingJob]:
        """Get a docking job by ID (sync wrapper)."""
        async def _get():
            async with self.session_maker() as session:
                service = DockingJobService(session)
                return await service.get_job(job_id)
        
        return self._run_async(_get())
    
    def update_job(self, job: DockingJob) -> None:
        """Update a docking job (sync wrapper)."""
        async def _update():
            async with self.session_maker() as session:
                service = DockingJobService(session)
                await service.update_job(job)
        
        self._run_async(_update())
    
    def save_results(self, job_id: str, results: List[DockingResult]) -> None:
        """Save docking results (sync wrapper)."""
        async def _save():
            async with self.session_maker() as session:
                service = DockingJobService(session)
                await service.save_results(job_id, results)
        
        self._run_async(_save())
    
    def get_all_jobs(self) -> List[DockingJob]:
        """Get all docking jobs (sync wrapper)."""
        async def _get_all():
            async with self.session_maker() as session:
                service = DockingJobService(session)
                return await service.get_all_jobs()
        
        return self._run_async(_get_all())
