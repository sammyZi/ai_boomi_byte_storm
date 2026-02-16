"""Celery tasks for asynchronous docking job execution.

This module defines Celery tasks for running molecular docking jobs
in the background with proper error handling and retry logic.
"""

import logging
import os
import tempfile
import shutil
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

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

# Database service for persistent storage
from app.docking.db_service import DockingJobService
from app.database import async_session_maker


async def get_job(job_id: str) -> Optional[DockingJob]:
    """Get a docking job by ID from database.
    
    Args:
        job_id: Job identifier
    
    Returns:
        DockingJob or None if not found
    """
    async with async_session_maker() as session:
        service = DockingJobService(session)
        return await service.get_job(job_id)


async def save_job(job: DockingJob) -> None:
    """Save a docking job to database.
    
    Args:
        job: DockingJob to save
    """
    async with async_session_maker() as session:
        service = DockingJobService(session)
        await service.update_job(job)


async def get_all_jobs() -> List[DockingJob]:
    """Get all docking jobs from database.
    
    Returns:
        List of all DockingJob objects
    """
    async with async_session_maker() as session:
        service = DockingJobService(session)
        return await service.get_all_jobs()


async def create_docking_job(
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
    
    # Create job in database
    async with async_session_maker() as session:
        service = DockingJobService(session)
        job = await service.create_job(
            job_id=job_id,
            candidate_id=candidate_id,
            target_uniprot_id=target_uniprot_id,
            disease_name=disease_name,
            grid_params=grid_params,
            docking_params=docking_params
        )
    
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
    import asyncio
    
    # Get job from database
    async def _get_job():
        async with async_session_maker() as session:
            service = DockingJobService(session)
            return await service.get_job(job_id)
    
    job = asyncio.run(_get_job())
    
    if not job:
        raise ValueError(f"Job not found: {job_id}")
    
    job_data = _job_data.get(job_id, {})
    smiles = job_data.get('smiles')
    pdb_data = job_data.get('pdb_data')
    
    def log_step(step: str, progress: int, message: str = ""):
        """Helper to log and update job progress."""
        job.current_step = step
        job.progress_percent = progress
        if message:
            job.console_output += f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] {message}\n"
        
        # Save to database (runs in thread, so asyncio.run is safe)
        async def _save():
            async with async_session_maker() as session:
                service = DockingJobService(session)
                await service.update_job(job)
        
        try:
            asyncio.run(_save())
        except Exception as e:
            logger.error(f"[{job_id}] Failed to save job progress: {e}")
        
        logger.info(f"[{job_id}] {step}: {message}" if message else f"[{job_id}] {step}")
    
    if not smiles or not pdb_data:
        job.status = DockingJobStatus.FAILED
        job.error_message = "Missing ligand SMILES or protein PDB data"
        job.console_output = f"ERROR: Missing input data\n- SMILES: {'provided' if smiles else 'MISSING'}\n- PDB data: {'provided' if pdb_data else 'MISSING'}\n"
        
        async def _save_error():
            async with async_session_maker() as session:
                service = DockingJobService(session)
                await service.update_job(job)
        
        asyncio.run(_save_error())
        return job
    
    # Update status to running
    job.status = DockingJobStatus.RUNNING
    job.started_at = datetime.now(timezone.utc)
    job.console_output = f"=== Docking Job {job_id} ===\n"
    job.console_output += f"Started at: {job.started_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
    job.console_output += f"Candidate: {job.candidate_id}\n"
    job.console_output += f"Target: {job.target_uniprot_id}\n"
    job.console_output += f"Disease: {job.disease_name}\n\n"
    log_step("Initializing", 5, "Starting docking workflow...")
    
    # Create working directory
    work_dir = tempfile.mkdtemp(prefix=f"docking_{job_id}_")
    job.console_output += f"Working directory: {work_dir}\n\n"
    
    try:
        # Step 1: Convert protein to PDBQT
        log_step("Converting Protein", 10, f"Converting protein {job.target_uniprot_id} to PDBQT format...")
        converter = PDBQTConverter(work_dir)
        
        protein_pdbqt, protein_path = converter.convert_protein_to_pdbqt(
            pdb_data,
            job.target_uniprot_id
        )
        job.protein_pdbqt_path = protein_path
        
        # Read and store protein PDBQT data for visualization
        try:
            with open(protein_path, 'r') as f:
                job.protein_pdbqt_data = f.read()
            logger.info(f"[{job_id}] Protein PDBQT data loaded from file: {len(job.protein_pdbqt_data)} bytes")
        except Exception as e:
            logger.warning(f"[{job_id}] Could not read protein PDBQT file: {e}")
            job.protein_pdbqt_data = protein_pdbqt
        
        # Debug: Verify protein data is set
        logger.info(f"[{job_id}] Protein PDBQT data length: {len(protein_pdbqt) if protein_pdbqt else 0} bytes")
        logger.info(f"[{job_id}] Job protein_pdbqt_data length: {len(job.protein_pdbqt_data) if job.protein_pdbqt_data else 0} bytes")
        
        job.console_output += f"✓ Protein PDBQT created: {os.path.basename(protein_path)}\n"
        job.console_output += f"  Size: {len(protein_pdbqt)} bytes\n\n"
        log_step("Protein Converted", 20, "")
        
        # Step 2: Convert ligand to PDBQT
        log_step("Converting Ligand", 25, f"Converting ligand {job.candidate_id} to PDBQT format...")
        job.console_output += f"Input SMILES: {smiles}\n"
        
        ligand_pdbqt, ligand_path = converter.convert_ligand_to_pdbqt(
            smiles,
            job.candidate_id
        )
        job.ligand_pdbqt_path = ligand_path
        job.console_output += f"✓ Ligand PDBQT created: {os.path.basename(ligand_path)}\n"
        job.console_output += f"  Size: {len(ligand_pdbqt)} bytes\n\n"
        log_step("Ligand Converted", 30, "")
        
        # Step 3: Calculate grid box if not provided
        if not job.grid_params:
            log_step("Calculating Grid Box", 40, "Auto-calculating grid box from protein structure...")
            calculator = GridBoxCalculator()
            job.grid_params = calculator.calculate_from_pdb(pdb_data)
            job.console_output += f"✓ Grid box calculated:\n"
            job.console_output += f"  Center: ({job.grid_params.center_x:.2f}, {job.grid_params.center_y:.2f}, {job.grid_params.center_z:.2f})\n"
            job.console_output += f"  Size: ({job.grid_params.size_x:.1f}, {job.grid_params.size_y:.1f}, {job.grid_params.size_z:.1f}) Å\n\n"
        else:
            log_step("Using Custom Grid Box", 40, "Using user-provided grid box parameters...")
            job.console_output += f"Grid box (user-provided):\n"
            job.console_output += f"  Center: ({job.grid_params.center_x:.2f}, {job.grid_params.center_y:.2f}, {job.grid_params.center_z:.2f})\n"
            job.console_output += f"  Size: ({job.grid_params.size_x:.1f}, {job.grid_params.size_y:.1f}, {job.grid_params.size_z:.1f}) Å\n\n"
        log_step("Grid Box Ready", 45, "")
        
        # Step 4: Generate config file
        log_step("Generating Config", 50, "Creating AutoDock Vina configuration file...")
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
        
        job.console_output += f"✓ Config file created: {os.path.basename(config_path)}\n"
        job.console_output += f"  Exhaustiveness: {job.docking_params.exhaustiveness}\n"
        job.console_output += f"  Num modes: {job.docking_params.num_modes}\n"
        job.console_output += f"  Energy range: {job.docking_params.energy_range} kcal/mol\n\n"
        log_step("Config Generated", 55, "")
        
        # Step 5: Execute AutoDock Vina
        log_step("Running AutoDock Vina", 60, "Executing molecular docking simulation...")
        job.console_output += "--- AutoDock Vina Output ---\n"
        log_step("Vina Starting", 65, "")
        
        executor = VinaExecutor()
        log_path = os.path.join(work_dir, f"{job_id}_vina.log")
        
        success, stdout, error = executor.execute_sync(config_path, log_path)
        
        # Add Vina output to console
        if stdout:
            job.console_output += stdout + "\n"
        if error:
            job.console_output += f"STDERR: {error}\n"
        job.console_output += "--- End Vina Output ---\n\n"
        log_step("Vina Completed", 85, "")
        
        if not success:
            job.status = DockingJobStatus.FAILED
            # Include log file contents for better debugging
            error_details = error or "Vina execution failed"
            if os.path.exists(log_path):
                try:
                    with open(log_path, 'r') as f:
                        log_contents = f.read()
                    logger.error(f"[{job_id}] Vina log contents:\n{log_contents}")
                    job.console_output += f"Log file contents:\n{log_contents}\n"
                except Exception as e:
                    logger.error(f"[{job_id}] Could not read log file: {e}")
            job.error_message = error_details
            job.completed_at = datetime.now(timezone.utc)
            job.progress_percent = 100
            job.current_step = "Failed"
            
            async def _save_failed():
                async with async_session_maker() as session:
                    service = DockingJobService(session)
                    await service.update_job(job)
            
            asyncio.run(_save_failed())
            return job
        
        # Step 6: Parse results
        log_step("Parsing Results", 90, "Extracting binding poses from output...")
        parser = DockingResultsParser()
        results = parser.parse_combined(stdout, output_path)
        
        if not results:
            job.status = DockingJobStatus.FAILED
            job.error_message = "No docking poses found"
            job.console_output += "ERROR: No valid docking poses found in output.\n"
            job.completed_at = datetime.now(timezone.utc)
            job.progress_percent = 100
            job.current_step = "Failed"
            
            async def _save_no_poses():
                async with async_session_maker() as session:
                    service = DockingJobService(session)
                    await service.update_job(job)
            
            asyncio.run(_save_no_poses())
            return job
        
        # Update job with results
        job.results = results
        job.best_affinity = min(r.binding_affinity for r in results)
        job.status = DockingJobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        job.progress_percent = 100
        job.current_step = "Completed"
        
        # Save job and results to database
        async def _save_final():
            async with async_session_maker() as session:
                service = DockingJobService(session)
                await service.update_job(job)
                await service.save_results(job.id, results)
        
        asyncio.run(_save_final())
        
        # Add results summary
        elapsed = (job.completed_at - job.started_at).total_seconds()
        job.console_output += f"=== RESULTS SUMMARY ===\n"
        job.console_output += f"Status: COMPLETED\n"
        job.console_output += f"Execution time: {elapsed:.1f} seconds\n"
        job.console_output += f"Poses found: {len(results)}\n"
        job.console_output += f"Best affinity: {job.best_affinity:.2f} kcal/mol\n\n"
        job.console_output += "Binding Poses:\n"
        job.console_output += f"{'Pose':<6} {'Affinity':<12} {'RMSD LB':<10} {'RMSD UB':<10}\n"
        job.console_output += "-" * 40 + "\n"
        for r in results:
            job.console_output += f"{r.pose_number:<6} {r.binding_affinity:<12.2f} {r.rmsd_lb:<10.3f} {r.rmsd_ub:<10.3f}\n"
        job.console_output += "\n✓ Docking job completed successfully!\n"
        
        # Final save
        async def _save_complete():
            async with async_session_maker() as session:
                service = DockingJobService(session)
                await service.update_job(job)
        
        asyncio.run(_save_complete())
        
        logger.info(f"[{job_id}] Docking completed with {len(results)} poses, "
                   f"best affinity: {job.best_affinity:.2f} kcal/mol")
        
        return job
        
    except Exception as e:
        logger.error(f"[{job_id}] Docking failed: {str(e)}", exc_info=True)
        job.status = DockingJobStatus.FAILED
        job.error_message = str(e)
        job.console_output += f"\nERROR: {str(e)}\n"
        job.completed_at = datetime.now(timezone.utc)
        job.progress_percent = 100
        job.current_step = "Failed"
        
        async def _save_error():
            async with async_session_maker() as session:
                service = DockingJobService(session)
                await service.update_job(job)
        
        asyncio.run(_save_error())
        return job
    
    finally:
        # Clean up working directory (keep for debugging in development)
        # In production, uncomment cleanup:
        # shutil.rmtree(work_dir, ignore_errors=True)
        pass


async def cancel_docking_job(job_id: str) -> bool:
    """Cancel a queued docking job.
    
    Args:
        job_id: ID of the job to cancel
    
    Returns:
        True if job was cancelled, False otherwise
    """
    job = await get_job(job_id)
    if not job:
        return False
    
    if job.status == DockingJobStatus.QUEUED:
        job.status = DockingJobStatus.CANCELLED
        job.completed_at = datetime.now(timezone.utc)
        await save_job(job)
        return True
    
    return False


async def get_queue_position(job_id: str) -> Optional[int]:
    """Get queue position for a job.
    
    Args:
        job_id: Job identifier
    
    Returns:
        Queue position (1-based) or None if not queued
    """
    job = await get_job(job_id)
    if not job or job.status != DockingJobStatus.QUEUED:
        return None
    
    # Count queued jobs created before this one
    all_jobs = await get_all_jobs()
    position = 1
    for j in all_jobs:
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
