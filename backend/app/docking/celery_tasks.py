"""Celery task definitions for docking jobs.

This module defines the actual Celery tasks that run asynchronously,
wrapping the synchronous functions in tasks.py.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from app.celery_app import celery_app
from app.docking.models import DockingJobStatus, DockingParams, GridBoxParams
from app.docking import tasks

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.docking.celery_tasks.run_docking_task",
    max_retries=2,
    default_retry_delay=60,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,  # Max 5 minutes between retries
)
def run_docking_task(
    self,
    candidate_id: str,
    target_uniprot_id: str,
    disease_name: str,
    smiles: str,
    pdb_data: str,
    grid_params: Optional[Dict[str, Any]] = None,
    docking_params: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Celery task to run a docking job asynchronously.
    
    This task creates and executes a docking job, with automatic retry
    on failure.
    
    Args:
        candidate_id: ChEMBL ID of the drug candidate
        target_uniprot_id: UniProt ID of the target protein
        disease_name: Name of the disease
        smiles: SMILES string of the ligand
        pdb_data: PDB data of the target protein
        grid_params: Optional custom grid box parameters dict
        docking_params: Optional custom docking parameters dict
    
    Returns:
        Dict containing job ID and status
    """
    logger.info(f"Starting docking task for {candidate_id} (attempt {self.request.retries + 1})")
    
    # Convert dicts to Pydantic models if provided
    grid = GridBoxParams(**grid_params) if grid_params else None
    params = DockingParams(**docking_params) if docking_params else None
    
    try:
        # Create and run the job
        job = tasks.create_docking_job(
            candidate_id=candidate_id,
            target_uniprot_id=target_uniprot_id,
            disease_name=disease_name,
            smiles=smiles,
            pdb_data=pdb_data,
            grid_params=grid,
            docking_params=params
        )
        
        # Execute the docking
        job = tasks.run_docking_job(job.id)
        
        # Return result summary
        return {
            "job_id": job.id,
            "status": job.status.value,
            "error": job.error_message,
            "results_count": len(job.results) if job.results else 0,
            "best_affinity": job.results[0].binding_affinity if job.results else None
        }
        
    except Exception as e:
        logger.error(f"Docking task failed for {candidate_id}: {str(e)}")
        raise


@celery_app.task(name="app.docking.celery_tasks.cleanup_old_jobs")
def cleanup_old_jobs(days_old: int = 7) -> Dict[str, Any]:
    """Celery task to clean up old docking jobs.
    
    Removes jobs and their files that are older than the specified
    number of days.
    
    Args:
        days_old: Number of days after which to clean up jobs
    
    Returns:
        Dict with cleanup statistics
    """
    logger.info(f"Starting cleanup of jobs older than {days_old} days")
    
    cutoff_date = datetime.utcnow() - timedelta(days=days_old)
    cleaned_count = 0
    error_count = 0
    
    # Get all jobs from store
    all_jobs = list(tasks._jobs_store.values())
    
    for job in all_jobs:
        try:
            # Check if job is old enough and completed/failed
            if job.created_at < cutoff_date and job.status in [
                DockingJobStatus.COMPLETED,
                DockingJobStatus.FAILED,
                DockingJobStatus.CANCELLED
            ]:
                # Clean up files
                tasks.cleanup_job_files(job.id)
                
                # Remove from store
                if job.id in tasks._jobs_store:
                    del tasks._jobs_store[job.id]
                if job.id in tasks._job_data:
                    del tasks._job_data[job.id]
                
                cleaned_count += 1
                logger.debug(f"Cleaned up job {job.id}")
                
        except Exception as e:
            logger.error(f"Error cleaning up job {job.id}: {str(e)}")
            error_count += 1
    
    result = {
        "cleaned_count": cleaned_count,
        "error_count": error_count,
        "cutoff_date": cutoff_date.isoformat()
    }
    
    logger.info(f"Cleanup complete: {cleaned_count} jobs removed, {error_count} errors")
    return result


@celery_app.task(name="app.docking.celery_tasks.get_queue_status")
def get_queue_status() -> Dict[str, Any]:
    """Get the current status of the docking job queue.
    
    Returns:
        Dict with queue statistics
    """
    all_jobs = list(tasks._jobs_store.values())
    
    status_counts = {
        "queued": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "cancelled": 0
    }
    
    for job in all_jobs:
        status_counts[job.status.value] = status_counts.get(job.status.value, 0) + 1
    
    return {
        "total_jobs": len(all_jobs),
        "status_counts": status_counts,
        "timestamp": datetime.utcnow().isoformat()
    }
