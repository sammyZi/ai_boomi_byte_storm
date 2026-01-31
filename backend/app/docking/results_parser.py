"""Docking results parser for AutoDock Vina output.

This module parses AutoDock Vina output files to extract binding
affinity scores, RMSD values, and atomic coordinates for each pose.
"""

import logging
import re
from typing import List, Optional, Tuple
from app.docking.models import DockingResult

logger = logging.getLogger(__name__)


class DockingResultsParser:
    """Parser for AutoDock Vina docking results.
    
    Extracts binding poses, affinity scores, and RMSD values from
    Vina output files.
    """
    
    def parse_stdout(self, stdout: str) -> List[DockingResult]:
        """Parse binding affinity from Vina stdout output.
        
        Extracts the results table from Vina's console output.
        
        Args:
            stdout: Standard output from Vina execution
        
        Returns:
            List of DockingResult objects
        """
        results = []
        
        # Pattern to match Vina output table lines
        # Format: "   1         -8.5      0.000      0.000"
        pattern = r'^\s*(\d+)\s+([-\d.]+)\s+([\d.]+)\s+([\d.]+)\s*$'
        
        in_results_section = False
        past_separator = False
        
        for line in stdout.split('\n'):
            # Detect start of results table
            if 'mode' in line.lower() and 'affinity' in line.lower():
                in_results_section = True
                past_separator = False
                continue
            
            if in_results_section:
                # Check for separator line (marks end of header)
                if line.strip().startswith('-----'):
                    past_separator = True
                    continue
                
                # Skip header continuation lines (before separator)
                if not past_separator:
                    continue
                
                # Try to parse result line
                match = re.match(pattern, line)
                if match:
                    pose_num = int(match.group(1))
                    affinity = float(match.group(2))
                    rmsd_lb = float(match.group(3))
                    rmsd_ub = float(match.group(4))
                    
                    results.append(DockingResult(
                        pose_number=pose_num,
                        binding_affinity=affinity,
                        rmsd_lb=rmsd_lb,
                        rmsd_ub=rmsd_ub
                    ))
                elif line.strip() and not line.strip().startswith('Writing'):
                    # End of results section
                    break
        
        if results:
            logger.info(f"Parsed {len(results)} poses from stdout")
        else:
            logger.warning("No poses found in stdout output")
        
        return results
    
    def parse_output_pdbqt(self, pdbqt_path: str) -> List[DockingResult]:
        """Parse docking results from Vina output PDBQT file.
        
        Extracts all binding poses with coordinates and scores.
        
        Args:
            pdbqt_path: Path to output PDBQT file
        
        Returns:
            List of DockingResult objects with PDBQT data
        """
        results = []
        
        try:
            with open(pdbqt_path, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            logger.error(f"Output PDBQT not found: {pdbqt_path}")
            return results
        except Exception as e:
            logger.error(f"Failed to read output PDBQT: {str(e)}")
            return results
        
        # Split by MODEL records
        models = re.split(r'^MODEL\s+\d+\s*$', content, flags=re.MULTILINE)
        
        for i, model in enumerate(models[1:], start=1):  # Skip first empty split
            # Extract REMARK lines for affinity and RMSD
            affinity = None
            rmsd_lb = 0.0
            rmsd_ub = 0.0
            
            for line in model.split('\n'):
                if line.startswith('REMARK VINA RESULT:'):
                    # Format: REMARK VINA RESULT:    -8.5      0.000      0.000
                    parts = line.split(':')[1].strip().split()
                    if len(parts) >= 3:
                        affinity = float(parts[0])
                        rmsd_lb = float(parts[1])
                        rmsd_ub = float(parts[2])
                    break
            
            if affinity is not None:
                # Extract the PDBQT data for this model
                pdbqt_data = f"MODEL {i}\n{model}"
                if not pdbqt_data.strip().endswith('ENDMDL'):
                    pdbqt_data += "\nENDMDL"
                
                results.append(DockingResult(
                    pose_number=i,
                    binding_affinity=affinity,
                    rmsd_lb=rmsd_lb,
                    rmsd_ub=rmsd_ub,
                    pdbqt_data=pdbqt_data
                ))
        
        if results:
            logger.info(f"Parsed {len(results)} poses from PDBQT file")
        else:
            logger.warning("No poses found in output PDBQT")
        
        return results
    
    def get_best_pose(self, results: List[DockingResult]) -> Optional[DockingResult]:
        """Get the best binding pose (most negative affinity).
        
        Args:
            results: List of docking results
        
        Returns:
            DockingResult with best (most negative) affinity, or None
        """
        if not results:
            return None
        
        return min(results, key=lambda r: r.binding_affinity)
    
    def get_summary_statistics(
        self,
        results: List[DockingResult]
    ) -> dict:
        """Calculate summary statistics for docking results.
        
        Args:
            results: List of docking results
        
        Returns:
            Dictionary with summary statistics
        """
        if not results:
            return {
                'num_poses': 0,
                'best_affinity': None,
                'worst_affinity': None,
                'mean_affinity': None,
                'affinity_range': None
            }
        
        affinities = [r.binding_affinity for r in results]
        
        return {
            'num_poses': len(results),
            'best_affinity': min(affinities),
            'worst_affinity': max(affinities),
            'mean_affinity': sum(affinities) / len(affinities),
            'affinity_range': max(affinities) - min(affinities)
        }
    
    def parse_combined(
        self,
        stdout: str,
        pdbqt_path: Optional[str] = None
    ) -> List[DockingResult]:
        """Parse results from both stdout and PDBQT file.
        
        Combines affinity data from stdout with coordinate data from
        PDBQT file for complete results.
        
        Args:
            stdout: Vina stdout output
            pdbqt_path: Optional path to output PDBQT file
        
        Returns:
            List of DockingResult objects
        """
        # Parse stdout for basic results
        results = self.parse_stdout(stdout)
        
        # If PDBQT file available, add coordinate data
        if pdbqt_path:
            pdbqt_results = self.parse_output_pdbqt(pdbqt_path)
            
            # Merge PDBQT data into stdout results
            pdbqt_by_pose = {r.pose_number: r for r in pdbqt_results}
            
            for result in results:
                if result.pose_number in pdbqt_by_pose:
                    result.pdbqt_data = pdbqt_by_pose[result.pose_number].pdbqt_data
        
        return results
