"""Grid box calculator for molecular docking.

This module calculates the optimal grid box parameters for AutoDock Vina
based on protein structure coordinates.
"""

import logging
from typing import List, Tuple, Optional
from app.docking.models import GridBoxParams

logger = logging.getLogger(__name__)


class GridBoxCalculator:
    """Calculator for docking grid box parameters.
    
    Analyzes protein structure to determine optimal grid box center
    and dimensions for molecular docking.
    """
    
    DEFAULT_BOX_SIZE = 25.0  # Default box size in Angstroms
    MIN_BOX_SIZE = 10.0
    MAX_BOX_SIZE = 50.0
    PADDING = 5.0  # Padding around binding site
    
    def __init__(self):
        """Initialize the grid box calculator."""
        pass
    
    def calculate_from_pdb(
        self,
        pdb_data: str,
        box_size: Optional[Tuple[float, float, float]] = None
    ) -> GridBoxParams:
        """Calculate grid box parameters from PDB structure.
        
        Determines the geometric center of the protein and sets up
        a grid box of specified or default dimensions.
        
        Args:
            pdb_data: PDB format protein structure data
            box_size: Optional custom box dimensions (x, y, z) in Angstroms
        
        Returns:
            GridBoxParams with center coordinates and dimensions
        
        Raises:
            ValueError: If PDB data is invalid or contains no atoms
        """
        # Extract atom coordinates
        coords = self._extract_coordinates(pdb_data)
        
        if not coords:
            raise ValueError("No atom coordinates found in PDB data")
        
        # Calculate geometric center
        center_x, center_y, center_z = self._calculate_center(coords)
        
        # Use provided box size or defaults
        if box_size:
            size_x, size_y, size_z = box_size
        else:
            size_x = size_y = size_z = self.DEFAULT_BOX_SIZE
        
        # Validate dimensions
        size_x = max(self.MIN_BOX_SIZE, min(self.MAX_BOX_SIZE, size_x))
        size_y = max(self.MIN_BOX_SIZE, min(self.MAX_BOX_SIZE, size_y))
        size_z = max(self.MIN_BOX_SIZE, min(self.MAX_BOX_SIZE, size_z))
        
        logger.info(f"Grid box: center=({center_x:.2f}, {center_y:.2f}, {center_z:.2f}), "
                   f"size=({size_x:.2f}, {size_y:.2f}, {size_z:.2f})")
        
        return GridBoxParams(
            center_x=round(center_x, 2),
            center_y=round(center_y, 2),
            center_z=round(center_z, 2),
            size_x=round(size_x, 2),
            size_y=round(size_y, 2),
            size_z=round(size_z, 2)
        )
    
    def calculate_from_binding_site(
        self,
        pdb_data: str,
        residue_ids: List[int],
        chain_id: str = 'A'
    ) -> GridBoxParams:
        """Calculate grid box centered on specific binding site residues.
        
        Uses specified residues to define the binding site center and
        automatically sizes the box to encompass the site with padding.
        
        Args:
            pdb_data: PDB format protein structure data
            residue_ids: List of residue numbers defining the binding site
            chain_id: Chain identifier (default: 'A')
        
        Returns:
            GridBoxParams centered on the binding site
        """
        # Extract coordinates for specified residues only
        coords = self._extract_residue_coordinates(pdb_data, residue_ids, chain_id)
        
        if not coords:
            logger.warning("No binding site residues found, using whole protein")
            return self.calculate_from_pdb(pdb_data)
        
        # Calculate center
        center_x, center_y, center_z = self._calculate_center(coords)
        
        # Calculate box size based on binding site extent
        size_x, size_y, size_z = self._calculate_box_size(coords)
        
        return GridBoxParams(
            center_x=round(center_x, 2),
            center_y=round(center_y, 2),
            center_z=round(center_z, 2),
            size_x=round(size_x, 2),
            size_y=round(size_y, 2),
            size_z=round(size_z, 2)
        )
    
    def _extract_coordinates(self, pdb_data: str) -> List[Tuple[float, float, float]]:
        """Extract all atom coordinates from PDB data.
        
        Args:
            pdb_data: PDB format data
        
        Returns:
            List of (x, y, z) coordinate tuples
        """
        coords = []
        
        for line in pdb_data.strip().split('\n'):
            if line.startswith(('ATOM', 'HETATM')):
                try:
                    x = float(line[30:38].strip())
                    y = float(line[38:46].strip())
                    z = float(line[46:54].strip())
                    coords.append((x, y, z))
                except (ValueError, IndexError):
                    continue
        
        return coords
    
    def _extract_residue_coordinates(
        self,
        pdb_data: str,
        residue_ids: List[int],
        chain_id: str
    ) -> List[Tuple[float, float, float]]:
        """Extract coordinates for specific residues.
        
        Args:
            pdb_data: PDB format data
            residue_ids: List of residue numbers
            chain_id: Chain identifier
        
        Returns:
            List of (x, y, z) coordinate tuples for specified residues
        """
        coords = []
        residue_set = set(residue_ids)
        
        for line in pdb_data.strip().split('\n'):
            if line.startswith('ATOM'):
                try:
                    chain = line[21].strip()
                    res_num = int(line[22:26].strip())
                    
                    if chain == chain_id and res_num in residue_set:
                        x = float(line[30:38].strip())
                        y = float(line[38:46].strip())
                        z = float(line[46:54].strip())
                        coords.append((x, y, z))
                except (ValueError, IndexError):
                    continue
        
        return coords
    
    def _calculate_center(
        self,
        coords: List[Tuple[float, float, float]]
    ) -> Tuple[float, float, float]:
        """Calculate geometric center of coordinates.
        
        Args:
            coords: List of (x, y, z) coordinate tuples
        
        Returns:
            Tuple of (center_x, center_y, center_z)
        """
        if not coords:
            return (0.0, 0.0, 0.0)
        
        n = len(coords)
        center_x = sum(c[0] for c in coords) / n
        center_y = sum(c[1] for c in coords) / n
        center_z = sum(c[2] for c in coords) / n
        
        return (center_x, center_y, center_z)
    
    def _calculate_box_size(
        self,
        coords: List[Tuple[float, float, float]]
    ) -> Tuple[float, float, float]:
        """Calculate appropriate box size based on coordinate extent.
        
        Args:
            coords: List of (x, y, z) coordinate tuples
        
        Returns:
            Tuple of (size_x, size_y, size_z) with padding
        """
        if not coords:
            return (self.DEFAULT_BOX_SIZE, self.DEFAULT_BOX_SIZE, self.DEFAULT_BOX_SIZE)
        
        x_coords = [c[0] for c in coords]
        y_coords = [c[1] for c in coords]
        z_coords = [c[2] for c in coords]
        
        # Calculate extent plus padding
        size_x = (max(x_coords) - min(x_coords)) + 2 * self.PADDING
        size_y = (max(y_coords) - min(y_coords)) + 2 * self.PADDING
        size_z = (max(z_coords) - min(z_coords)) + 2 * self.PADDING
        
        # Ensure within valid range
        size_x = max(self.MIN_BOX_SIZE, min(self.MAX_BOX_SIZE, size_x))
        size_y = max(self.MIN_BOX_SIZE, min(self.MAX_BOX_SIZE, size_y))
        size_z = max(self.MIN_BOX_SIZE, min(self.MAX_BOX_SIZE, size_z))
        
        return (size_x, size_y, size_z)
