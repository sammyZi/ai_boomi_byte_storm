"""Molecular docking module for drug-protein binding analysis.

This module provides molecular docking capabilities using AutoDock Vina,
allowing users to validate binding predictions for drug candidates against
target proteins.

Components:
- converter: PDBQT format conversion for proteins and ligands
- grid_calculator: Binding site grid box calculation
- config_generator: AutoDock Vina configuration file generation
- executor: AutoDock Vina subprocess execution
- results_parser: Docking results parsing and analysis
- tasks: Celery tasks for async docking jobs
- models: Database models for jobs and results
"""

from app.docking.models import (
    DockingJob,
    DockingResult,
    DockingJobStatus,
    DockingJobRequest,
    DockingJobResponse,
    GridBoxParams,
    DockingParams
)
from app.docking.service import (
    DockingService,
    DockingServiceError,
    JobNotFoundError,
    JobLimitExceededError,
    InvalidJobStateError,
    get_docking_service,
)
from app.docking.router import router as docking_router

__all__ = [
    'DockingJob',
    'DockingResult', 
    'DockingJobStatus',
    'DockingJobRequest',
    'DockingJobResponse',
    'GridBoxParams',
    'DockingParams',
    'DockingService',
    'DockingServiceError',
    'JobNotFoundError',
    'JobLimitExceededError',
    'InvalidJobStateError',
    'get_docking_service',
    'docking_router',
]
