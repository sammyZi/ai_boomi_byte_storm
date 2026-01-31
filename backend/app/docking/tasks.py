"""Celery tasks for asynchronous docking job execution.

This module defines Celery tasks for running molecular docking jobs
in the background with proper error handling and retry logic.
"""

import logging
import os
import tempfile
import shutil
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from app.docking.models import (
    DockingJob,
    DockingJobStatus,
    DockingParams,
    GridBoxParams
)
from app.docking.converter import PDBQTConverter
from app.docking.grid_calculator import GridBoxCalculator
from app.docking.config_generator import ConfigFileGenerator
from app.docking.executor import VinaExecutor
from app.docking.results_parser import DockingResultsParser

logger = logging.getLogger(__name__)

# In-memory job storage (replace with Redis/database in production)
_jobs_store: Dict[str, DockingJob] = {}


def get_job(job_id: str) -> Optional[DockingJob]:
    """Get a docking job by ID.
    
    Args:
        job_id: Job identifier
    
    Returns:
        DockingJob or None if not found
    """
    return _jobs_store.get(job_id)


def save_job(job: DockingJob) -> None:
    """Save a docking job.
    
    Args:
        job: DockingJob to save
    """
    _jobs_store[job.id] = job


def create_docking_job(
    candidate_id: str,
    target_uniprot_id: str,
    disease_name: str,
    smiles: str,
    pdb_data: str,
    grid_params: Optional[GridBoxParams] = None,
    docking_params: Optional[DockingParams] = None
) -> DockingJob:
    """Create and queue a new docking job.
    
    Args:
        candidate_id: ChEMBL ID of the drug candidate
        target_uniprot_id: UniProt ID of the target protein
        disease_name: Name of the disease
        smiles: SMILES string of the ligand
        pdb_data: PDB data of the target protein
        grid_params: Optional custom grid box parameters
        docking_params: Optional custom docking parameters
    
    Returns:
        Created DockingJob
    """
    job_id = str(uuid.uuid4())
    
    job = DockingJob(
        id=job_id,
        candidate_id=candidate_id,
        target_uniprot_id=target_uniprot_id,
        disease_name=disease_name,
        status=DockingJobStatus.QUEUED,
        grid_params=grid_params,
        docking_params=docking_params or DockingParams()
    )
    
    save_job(job)
    
    # Store additional data needed for execution
    _job_data[job_id] = {
        'smiles': smiles,
        'pdb_data': pdb_data
    }
    
    logger.info(f"Created docking job {job_id} for {candidate_id}")
    return job


# Additional data storage for job execution
_job_data: Dict[str, Dict[str, Any]] = {}


def run_docking_job(job_id: str) -> DockingJob:
    """Execute a docking job synchronously.
    
    This function performs the complete docking workflow:
    1. Convert protein and ligand to PDBQT
    2. Calculate grid box
    3. Generate config file
    4. Execute AutoDock Vina
    5. Parse results
    6. Update job status
    
    Args:
        job_id: ID of the job to execute
    
    Returns:
        Updated DockingJob with results
    """
    job = get_job(job_id)
    if not job:
        raise ValueError(f"Job not found: {job_id}")
    
    job_data = _job_data.get(job_id, {})
    smiles = job_data.get('smiles')
    pdb_data = job_data.get('pdb_data')
    
    if not smiles or not pdb_data:
        job.status = DockingJobStatus.FAILED
        job.error_message = "Missing ligand SMILES or protein PDB data"
        save_job(job)
        return job
    
    # Update status to running
    job.status = DockingJobStatus.RUNNING
    job.started_at = datetime.utcnow()
    save_job(job)
    
    # Create working directory
    work_dir = tempfile.mkdtemp(prefix=f"docking_{job_id}_")
    
    try:
        # Step 1: Convert protein to PDBQT
        logger.info(f"[{job_id}] Converting protein to PDBQT")
        converter = PDBQTConverter(work_dir)
        
        protein_pdbqt, protein_path = converter.convert_protein_to_pdbqt(
            pdb_data,
            job.target_uniprot_id
        )
        job.protein_pdbqt_path = protein_path
        
        # Step 2: Convert ligand to PDBQT
        logger.info(f"[{job_id}] Converting ligand to PDBQT")
        ligand_pdbqt, ligand_path = converter.convert_ligand_to_pdbqt(
            smiles,
            job.candidate_id
        )
        job.ligand_pdbqt_path = ligand_path
        
        # Step 3: Calculate grid box if not provided
        if not job.grid_params:
            logger.info(f"[{job_id}] Calculating grid box")
            calculator = GridBoxCalculator()
            job.grid_params = calculator.calculate_from_pdb(pdb_data)
        
        # Step 4: Generate config file
        logger.info(f"[{job_id}] Generating config file")
        output_path = os.path.join(work_dir, f"{job_id}_output.pdbqt")
        job.output_pdbqt_path = output_path
        
        config_generator = ConfigFileGenerator(work_dir)
        config_path = config_generator.generate_config(
            receptor_path=protein_path,
            ligand_path=ligand_path,
            output_path=output_path,
            grid_params=job.grid_params,
            docking_params=job.docking_params,
            job_id=job_id
        )
        
        # Step 5: Execute AutoDock Vina
        logger.info(f"[{job_id}] Executing AutoDock Vina")
        executor = VinaExecutor()
        log_path = os.path.join(work_dir, f"{job_id}_vina.log")
        
        success, stdout, error = executor.execute_sync(config_path, log_path)
        
        if not success:
            job.status = DockingJobStatus.FAILED
            job.error_message = error or "Vina execution failed"
            job.completed_at = datetime.utcnow()
            save_job(job)
            return job
        
        # Step 6: Parse results
        logger.info(f"[{job_id}] Parsing results")
        parser = DockingResultsParser()
        results = parser.parse_combined(stdout, output_path)
        
        if not results:
            job.status = DockingJobStatus.FAILED
            job.error_message = "No docking poses found"
            job.completed_at = datetime.utcnow()
            save_job(job)
            return job
        
        # Update job with results
        job.results = results
        job.best_affinity = min(r.binding_affinity for r in results)
        job.status = DockingJobStatus.COMPLETED
        job.completed_at = datetime.utcnow()
        save_job(job)
        
        logger.info(f"[{job_id}] Docking completed with {len(results)} poses, "
                   f"best affinity: {job.best_affinity:.2f} kcal/mol")
        
        return job
        
    except Exception as e:
        logger.error(f"[{job_id}] Docking failed: {str(e)}", exc_info=True)
        job.status = DockingJobStatus.FAILED
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        save_job(job)
        return job
    
    finally:
        # Clean up working directory (keep for debugging in development)
        # In production, uncomment cleanup:
        # shutil.rmtree(work_dir, ignore_errors=True)
        pass


def cancel_docking_job(job_id: str) -> bool:
    """Cancel a queued docking job.
    
    Args:
        job_id: ID of the job to cancel
    
    Returns:
        True if job was cancelled, False otherwise
    """
    job = get_job(job_id)
    if not job:
        return False
    
    if job.status == DockingJobStatus.QUEUED:
        job.status = DockingJobStatus.CANCELLED
        job.completed_at = datetime.utcnow()
        save_job(job)
        return True
    
    return False


def get_queue_position(job_id: str) -> Optional[int]:
    """Get queue position for a job.
    
    Args:
        job_id: Job identifier
    
    Returns:
        Queue position (1-based) or None if not queued
    """
    job = get_job(job_id)
    if not job or job.status != DockingJobStatus.QUEUED:
        return None
    
    # Count queued jobs created before this one
    position = 1
    for j in _jobs_store.values():
        if (j.status == DockingJobStatus.QUEUED and 
            j.created_at < job.created_at):
            position += 1
    
    return position


def cleanup_job_files(job_id: str) -> bool:
    """Clean up temporary files for a docking job.
    
    Args:
        job_id: Job identifier
    
    Returns:
        True if cleanup was successful, False otherwise
    """
    job = get_job(job_id)
    if not job:
        return False
    
    try:
        # Clean up protein PDBQT file
        if job.protein_pdbqt_path and os.path.exists(job.protein_pdbqt_path):
            os.remove(job.protein_pdbqt_path)
        
        # Clean up ligand PDBQT file
        if job.ligand_pdbqt_path and os.path.exists(job.ligand_pdbqt_path):
            os.remove(job.ligand_pdbqt_path)
        
        # Clean up output PDBQT file
        if job.output_pdbqt_path and os.path.exists(job.output_pdbqt_path):
            os.remove(job.output_pdbqt_path)
        
        # Clean up working directory if empty
        for path in [job.protein_pdbqt_path, job.ligand_pdbqt_path, job.output_pdbqt_path]:
            if path:
                parent_dir = os.path.dirname(path)
                if parent_dir and os.path.isdir(parent_dir) and not os.listdir(parent_dir):
                    shutil.rmtree(parent_dir, ignore_errors=True)
        
        logger.info(f"Cleaned up files for job {job_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error cleaning up job {job_id} files: {str(e)}")
        return False
