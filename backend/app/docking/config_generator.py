"""AutoDock Vina configuration file generator.

This module generates configuration files for AutoDock Vina execution
with all required parameters.
"""

import os
import logging
from typing import Optional
from app.docking.models import GridBoxParams, DockingParams

logger = logging.getLogger(__name__)


class ConfigFileGenerator:
    """Generator for AutoDock Vina configuration files.
    
    Creates properly formatted configuration files with all required
    parameters for docking execution.
    """
    
    def __init__(self, work_dir: str):
        """Initialize the configuration generator.
        
        Args:
            work_dir: Directory for output configuration files
        """
        self.work_dir = work_dir
        os.makedirs(work_dir, exist_ok=True)
    
    def generate_config(
        self,
        receptor_path: str,
        ligand_path: str,
        output_path: str,
        grid_params: GridBoxParams,
        docking_params: Optional[DockingParams] = None,
        job_id: str = "docking"
    ) -> str:
        """Generate AutoDock Vina configuration file.
        
        Creates a configuration file with all required fields:
        - Receptor and ligand file paths
        - Grid box center and size
        - Docking parameters (exhaustiveness, num_modes, etc.)
        - Output file path
        
        Args:
            receptor_path: Path to receptor PDBQT file
            ligand_path: Path to ligand PDBQT file
            output_path: Path for output PDBQT file
            grid_params: Grid box parameters
            docking_params: Docking algorithm parameters (uses defaults if None)
            job_id: Job identifier for config filename
        
        Returns:
            Path to the generated configuration file
        
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        # Validate inputs
        self._validate_paths(receptor_path, ligand_path)
        
        # Use default docking params if not provided
        if docking_params is None:
            docking_params = DockingParams()
        
        # Build configuration content
        config_lines = [
            f"# AutoDock Vina Configuration File",
            f"# Generated for job: {job_id}",
            f"",
            f"# Input files",
            f"receptor = {receptor_path}",
            f"ligand = {ligand_path}",
            f"",
            f"# Output file",
            f"out = {output_path}",
            f"",
            f"# Grid box center (Angstroms)",
            f"center_x = {grid_params.center_x:.2f}",
            f"center_y = {grid_params.center_y:.2f}",
            f"center_z = {grid_params.center_z:.2f}",
            f"",
            f"# Grid box size (Angstroms)",
            f"size_x = {grid_params.size_x:.2f}",
            f"size_y = {grid_params.size_y:.2f}",
            f"size_z = {grid_params.size_z:.2f}",
            f"",
            f"# Docking parameters",
            f"exhaustiveness = {docking_params.exhaustiveness}",
            f"num_modes = {docking_params.num_modes}",
            f"energy_range = {docking_params.energy_range:.1f}",
            f"cpu = {docking_params.cpu}",
        ]
        
        # Add optional seed if specified
        if docking_params.seed is not None:
            config_lines.append(f"seed = {docking_params.seed}")
        
        config_content = '\n'.join(config_lines)
        
        # Write configuration file
        config_path = os.path.join(self.work_dir, f"{job_id}_config.txt")
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        logger.info(f"Generated Vina config: {config_path}")
        return config_path
    
    def _validate_paths(self, receptor_path: str, ligand_path: str) -> None:
        """Validate that input file paths exist.
        
        Args:
            receptor_path: Path to receptor file
            ligand_path: Path to ligand file
        
        Raises:
            ValueError: If files don't exist
        """
        if not os.path.exists(receptor_path):
            raise ValueError(f"Receptor file not found: {receptor_path}")
        if not os.path.exists(ligand_path):
            raise ValueError(f"Ligand file not found: {ligand_path}")
    
    def validate_config(self, config_path: str) -> bool:
        """Validate that a configuration file is complete.
        
        Checks for all required fields in the configuration file.
        
        Args:
            config_path: Path to configuration file
        
        Returns:
            True if configuration is valid and complete
        """
        required_fields = [
            'receptor', 'ligand', 'out',
            'center_x', 'center_y', 'center_z',
            'size_x', 'size_y', 'size_z',
            'exhaustiveness', 'num_modes', 'energy_range'
        ]
        
        try:
            with open(config_path, 'r') as f:
                content = f.read()
            
            found_fields = set()
            for line in content.split('\n'):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    field = line.split('=')[0].strip()
                    found_fields.add(field)
            
            missing = set(required_fields) - found_fields
            if missing:
                logger.warning(f"Config missing fields: {missing}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Config validation failed: {str(e)}")
            return False
