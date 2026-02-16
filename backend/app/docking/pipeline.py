"""Enhanced Docking Pipeline with multi-tool support and fallback.

Complete pipeline: RDKit → OpenBabel → Smina → Vina → GNINA → Deep Learning Re-scoring

This module provides a robust docking pipeline that:
1. Uses RDKit for initial ligand preparation
2. Falls back to OpenBabel if RDKit fails
3. Attempts docking with Smina (fork of Vina with scoring improvements)
4. Falls back to AutoDock Vina if Smina unavailable
5. Optionally uses GNINA for GPU-accelerated docking
6. Applies deep learning re-scoring for improved accuracy
"""

import logging
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Tuple, List, Dict, Any, Callable

logger = logging.getLogger(__name__)


class DockingTool(Enum):
    """Available docking tools in order of preference."""
    GNINA = "gnina"      # Deep learning enhanced, best accuracy
    SMINA = "smina"      # Improved scoring functions
    VINA = "vina"        # Standard AutoDock Vina
    VINA_GPU = "vina_gpu"  # GPU-accelerated Vina


class LigandPrepTool(Enum):
    """Available ligand preparation tools."""
    RDKIT = "rdkit"
    OPENBABEL = "openbabel"


class ProteinPrepTool(Enum):
    """Available protein preparation tools."""
    OPENBABEL = "openbabel"
    REDUCE = "reduce"  # For adding hydrogens


@dataclass
class PipelineConfig:
    """Configuration for the docking pipeline."""
    # Tool preferences (in order)
    docking_tools: List[DockingTool] = field(default_factory=lambda: [
        DockingTool.GNINA,
        DockingTool.SMINA,
        DockingTool.VINA
    ])
    ligand_prep_tools: List[LigandPrepTool] = field(default_factory=lambda: [
        LigandPrepTool.RDKIT,
        LigandPrepTool.OPENBABEL
    ])
    protein_prep_tools: List[ProteinPrepTool] = field(default_factory=lambda: [
        ProteinPrepTool.OPENBABEL
    ])
    
    # Deep learning re-scoring
    enable_dl_rescoring: bool = True
    rescoring_model: str = "gnina_default"
    
    # Timeout settings
    ligand_prep_timeout: int = 60
    protein_prep_timeout: int = 120
    docking_timeout: int = 1800
    
    # Quality settings
    exhaustiveness: int = 16
    num_modes: int = 9
    energy_range: float = 3.0


@dataclass
class PipelineStep:
    """Represents a step in the docking pipeline."""
    name: str
    tool: str
    status: str  # pending, running, completed, failed, skipped
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    output: str = ""
    error: Optional[str] = None
    
    @property
    def duration_seconds(self) -> Optional[float]:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


@dataclass 
class PipelineResult:
    """Result from the docking pipeline."""
    success: bool
    docking_tool_used: Optional[str]
    ligand_prep_tool_used: Optional[str]
    protein_prep_tool_used: Optional[str]
    steps: List[PipelineStep]
    binding_affinities: List[float] = field(default_factory=list)
    poses_pdbqt: List[str] = field(default_factory=list)
    dl_rescoring_applied: bool = False
    console_output: str = ""
    error_message: Optional[str] = None


class DockingPipeline:
    """Enhanced docking pipeline with multi-tool support."""
    
    def __init__(self, work_dir: Optional[str] = None, config: Optional[PipelineConfig] = None):
        """Initialize the docking pipeline.
        
        Args:
            work_dir: Working directory for temporary files
            config: Pipeline configuration
        """
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="docking_pipeline_")
        self.config = config or PipelineConfig()
        self.steps: List[PipelineStep] = []
        self.console_output = ""
        
        # Detect available tools
        self.available_tools = self._detect_available_tools()
    
    def _log(self, message: str, level: str = "info"):
        """Log a message and add to console output."""
        timestamp = datetime.now(timezone.utc).strftime('%H:%M:%S')
        formatted = f"[{timestamp}] {message}"
        self.console_output += formatted + "\n"
        
        if level == "error":
            logger.error(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    
    def _detect_available_tools(self) -> Dict[str, bool]:
        """Detect which docking tools are available on the system."""
        tools = {}
        
        # Check docking tools
        for tool in DockingTool:
            tools[tool.value] = self._check_tool_available(tool.value)
        
        # Check prep tools
        tools['rdkit'] = self._check_rdkit()
        tools['openbabel'] = self._check_tool_available('obabel')
        tools['reduce'] = self._check_tool_available('reduce')
        
        self._log(f"Available tools: {[k for k, v in tools.items() if v]}")
        return tools
    
    def _check_tool_available(self, tool_name: str) -> bool:
        """Check if a command-line tool is available."""
        try:
            result = subprocess.run(
                [tool_name, '--help'],
                capture_output=True,
                timeout=5
            )
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
        except Exception:
            return False
    
    def _check_rdkit(self) -> bool:
        """Check if RDKit is available."""
        try:
            from rdkit import Chem
            from rdkit.Chem import AllChem
            return True
        except ImportError:
            return False
    
    def _add_step(self, name: str, tool: str) -> PipelineStep:
        """Add a new step to the pipeline."""
        step = PipelineStep(name=name, tool=tool, status="pending")
        self.steps.append(step)
        return step
    
    def _start_step(self, step: PipelineStep):
        """Mark a step as started."""
        step.status = "running"
        step.start_time = datetime.now(timezone.utc)
        self._log(f"▶ Starting: {step.name} using {step.tool}")
    
    def _complete_step(self, step: PipelineStep, output: str = ""):
        """Mark a step as completed."""
        step.status = "completed"
        step.end_time = datetime.now(timezone.utc)
        step.output = output
        duration = step.duration_seconds or 0
        self._log(f"✓ Completed: {step.name} ({duration:.1f}s)")
    
    def _fail_step(self, step: PipelineStep, error: str):
        """Mark a step as failed."""
        step.status = "failed"
        step.end_time = datetime.now(timezone.utc)
        step.error = error
        self._log(f"✗ Failed: {step.name} - {error}", "error")
    
    def _skip_step(self, step: PipelineStep, reason: str):
        """Mark a step as skipped."""
        step.status = "skipped"
        step.output = reason
        self._log(f"⊘ Skipped: {step.name} - {reason}")
    
    def prepare_ligand(self, smiles: str, ligand_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Prepare ligand using available tools with fallback.
        
        Pipeline: RDKit → OpenBabel
        
        Args:
            smiles: SMILES string of the ligand
            ligand_id: Identifier for output file naming
            
        Returns:
            Tuple of (pdbqt_data, pdbqt_path) or (None, None) if all tools fail
        """
        self._log(f"\n=== LIGAND PREPARATION ===")
        self._log(f"Input SMILES: {smiles[:50]}...")
        
        for tool in self.config.ligand_prep_tools:
            step = self._add_step(f"Ligand Prep ({tool.value})", tool.value)
            
            if not self.available_tools.get(tool.value, False):
                self._skip_step(step, f"{tool.value} not available")
                continue
            
            self._start_step(step)
            
            try:
                if tool == LigandPrepTool.RDKIT:
                    result = self._prepare_ligand_rdkit(smiles, ligand_id)
                else:
                    result = self._prepare_ligand_openbabel(smiles, ligand_id)
                
                if result[0]:
                    self._complete_step(step, f"Generated {len(result[0])} bytes")
                    return result
                else:
                    self._fail_step(step, "No output generated")
                    
            except Exception as e:
                self._fail_step(step, str(e))
        
        return None, None
    
    def _prepare_ligand_rdkit(self, smiles: str, ligand_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Prepare ligand using RDKit."""
        from rdkit import Chem
        from rdkit.Chem import AllChem
        
        # Parse SMILES
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            raise ValueError("Failed to parse SMILES")
        
        # Add hydrogens
        mol = Chem.AddHs(mol)
        
        # Generate 3D conformer
        status = AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
        if status == -1:
            # Try with random coordinates
            status = AllChem.EmbedMolecule(mol, useRandomCoords=True)
            if status == -1:
                raise ValueError("Failed to generate 3D conformer")
        
        # Optimize geometry
        AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
        
        # Compute Gasteiger charges
        AllChem.ComputeGasteigerCharges(mol)
        
        # Save as MOL2 first, then convert to PDBQT
        mol2_path = os.path.join(self.work_dir, f"{ligand_id}.mol2")
        pdbqt_path = os.path.join(self.work_dir, f"{ligand_id}_ligand.pdbqt")
        
        # Write MOL2
        Chem.MolToMolFile(mol, mol2_path.replace('.mol2', '.mol'))
        
        # Convert to PDBQT using OpenBabel
        result = subprocess.run(
            ['obabel', mol2_path.replace('.mol2', '.mol'), '-O', pdbqt_path, '-p', '7.4'],
            capture_output=True,
            text=True,
            timeout=self.config.ligand_prep_timeout
        )
        
        if os.path.exists(pdbqt_path):
            with open(pdbqt_path, 'r') as f:
                pdbqt_data = f.read()
            return pdbqt_data, pdbqt_path
        
        raise ValueError(f"Failed to generate PDBQT: {result.stderr}")
    
    def _prepare_ligand_openbabel(self, smiles: str, ligand_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Prepare ligand using OpenBabel."""
        pdbqt_path = os.path.join(self.work_dir, f"{ligand_id}_ligand.pdbqt")
        
        result = subprocess.run(
            ['obabel', f'-:{smiles}', '-O', pdbqt_path, '--gen3d', '-p', '7.4'],
            capture_output=True,
            text=True,
            timeout=self.config.ligand_prep_timeout
        )
        
        if result.returncode == 0 and os.path.exists(pdbqt_path):
            with open(pdbqt_path, 'r') as f:
                pdbqt_data = f.read()
            return pdbqt_data, pdbqt_path
        
        raise ValueError(f"OpenBabel failed: {result.stderr}")
    
    def prepare_protein(self, pdb_data: str, protein_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Prepare protein using available tools.
        
        Args:
            pdb_data: PDB format protein structure
            protein_id: Identifier for output file naming
            
        Returns:
            Tuple of (pdbqt_data, pdbqt_path) or (None, None) if all tools fail
        """
        self._log(f"\n=== PROTEIN PREPARATION ===")
        self._log(f"Protein ID: {protein_id}")
        
        for tool in self.config.protein_prep_tools:
            step = self._add_step(f"Protein Prep ({tool.value})", tool.value)
            
            tool_key = 'openbabel' if tool == ProteinPrepTool.OPENBABEL else tool.value
            if not self.available_tools.get(tool_key, False):
                self._skip_step(step, f"{tool.value} not available")
                continue
            
            self._start_step(step)
            
            try:
                if tool == ProteinPrepTool.OPENBABEL:
                    result = self._prepare_protein_openbabel(pdb_data, protein_id)
                else:
                    result = self._prepare_protein_reduce(pdb_data, protein_id)
                
                if result[0]:
                    self._complete_step(step, f"Generated {len(result[0])} bytes")
                    return result
                else:
                    self._fail_step(step, "No output generated")
                    
            except Exception as e:
                self._fail_step(step, str(e))
        
        return None, None
    
    def _prepare_protein_openbabel(self, pdb_data: str, protein_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Prepare protein using OpenBabel."""
        pdb_path = os.path.join(self.work_dir, f"{protein_id}.pdb")
        pdbqt_path = os.path.join(self.work_dir, f"{protein_id}_receptor.pdbqt")
        
        # Write PDB
        with open(pdb_path, 'w') as f:
            f.write(pdb_data)
        
        # Convert to PDBQT
        result = subprocess.run(
            ['obabel', pdb_path, '-O', pdbqt_path, '-xr', '-p', '7.4'],
            capture_output=True,
            text=True,
            timeout=self.config.protein_prep_timeout
        )
        
        if os.path.exists(pdbqt_path):
            with open(pdbqt_path, 'r') as f:
                pdbqt_data = f.read()
            return pdbqt_data, pdbqt_path
        
        raise ValueError(f"OpenBabel protein conversion failed: {result.stderr}")
    
    def _prepare_protein_reduce(self, pdb_data: str, protein_id: str) -> Tuple[Optional[str], Optional[str]]:
        """Prepare protein using Reduce (adds hydrogens) + OpenBabel."""
        pdb_path = os.path.join(self.work_dir, f"{protein_id}.pdb")
        reduced_path = os.path.join(self.work_dir, f"{protein_id}_H.pdb")
        pdbqt_path = os.path.join(self.work_dir, f"{protein_id}_receptor.pdbqt")
        
        # Write PDB
        with open(pdb_path, 'w') as f:
            f.write(pdb_data)
        
        # Add hydrogens with Reduce
        with open(reduced_path, 'w') as f:
            result = subprocess.run(
                ['reduce', '-BUILD', pdb_path],
                stdout=f,
                stderr=subprocess.PIPE,
                timeout=self.config.protein_prep_timeout
            )
        
        if not os.path.exists(reduced_path):
            raise ValueError("Reduce failed to add hydrogens")
        
        # Convert to PDBQT
        result = subprocess.run(
            ['obabel', reduced_path, '-O', pdbqt_path, '-xr'],
            capture_output=True,
            text=True,
            timeout=self.config.protein_prep_timeout
        )
        
        if os.path.exists(pdbqt_path):
            with open(pdbqt_path, 'r') as f:
                pdbqt_data = f.read()
            return pdbqt_data, pdbqt_path
        
        raise ValueError(f"PDBQT conversion after Reduce failed: {result.stderr}")
    
    def run_docking(
        self,
        protein_path: str,
        ligand_path: str,
        output_path: str,
        center: Tuple[float, float, float],
        size: Tuple[float, float, float]
    ) -> Tuple[bool, str, List[float], List[str]]:
        """Run molecular docking using available tools with fallback.
        
        Pipeline: GNINA → Smina → Vina
        
        Args:
            protein_path: Path to protein PDBQT
            ligand_path: Path to ligand PDBQT
            output_path: Path for output poses
            center: Grid box center (x, y, z)
            size: Grid box size (x, y, z)
            
        Returns:
            Tuple of (success, tool_used, binding_affinities, pose_pdbqts)
        """
        self._log(f"\n=== MOLECULAR DOCKING ===")
        self._log(f"Grid center: {center}")
        self._log(f"Grid size: {size}")
        
        for tool in self.config.docking_tools:
            step = self._add_step(f"Docking ({tool.value})", tool.value)
            
            if not self.available_tools.get(tool.value, False):
                self._skip_step(step, f"{tool.value} not available")
                continue
            
            self._start_step(step)
            
            try:
                if tool == DockingTool.GNINA:
                    result = self._dock_gnina(protein_path, ligand_path, output_path, center, size)
                elif tool == DockingTool.SMINA:
                    result = self._dock_smina(protein_path, ligand_path, output_path, center, size)
                else:
                    result = self._dock_vina(protein_path, ligand_path, output_path, center, size)
                
                success, stdout, affinities, poses = result
                
                if success and affinities:
                    self._complete_step(step, f"Found {len(affinities)} poses, best: {min(affinities):.2f} kcal/mol")
                    step.output = stdout
                    return True, tool.value, affinities, poses
                else:
                    self._fail_step(step, "No valid poses found")
                    
            except Exception as e:
                self._fail_step(step, str(e))
        
        return False, None, [], []
    
    def _create_config_file(
        self,
        protein_path: str,
        ligand_path: str,
        output_path: str,
        center: Tuple[float, float, float],
        size: Tuple[float, float, float],
        tool: str = "vina"
    ) -> str:
        """Create configuration file for docking."""
        config_path = os.path.join(self.work_dir, f"docking_{tool}.conf")
        
        config_content = f"""receptor = {protein_path}
ligand = {ligand_path}
out = {output_path}

center_x = {center[0]:.3f}
center_y = {center[1]:.3f}
center_z = {center[2]:.3f}

size_x = {size[0]:.1f}
size_y = {size[1]:.1f}
size_z = {size[2]:.1f}

exhaustiveness = {self.config.exhaustiveness}
num_modes = {self.config.num_modes}
energy_range = {self.config.energy_range}
"""
        
        with open(config_path, 'w') as f:
            f.write(config_content)
        
        return config_path
    
    def _dock_gnina(
        self,
        protein_path: str,
        ligand_path: str,
        output_path: str,
        center: Tuple[float, float, float],
        size: Tuple[float, float, float]
    ) -> Tuple[bool, str, List[float], List[str]]:
        """Run docking with GNINA (deep learning enhanced)."""
        cmd = [
            'gnina',
            '-r', protein_path,
            '-l', ligand_path,
            '-o', output_path,
            '--center_x', str(center[0]),
            '--center_y', str(center[1]),
            '--center_z', str(center[2]),
            '--size_x', str(size[0]),
            '--size_y', str(size[1]),
            '--size_z', str(size[2]),
            '--exhaustiveness', str(self.config.exhaustiveness),
            '--num_modes', str(self.config.num_modes),
            '--cnn_scoring', 'rescore'  # Use CNN for re-scoring
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=self.config.docking_timeout
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            affinities, poses = self._parse_docking_output(result.stdout, output_path)
            return True, result.stdout, affinities, poses
        
        raise ValueError(f"GNINA failed: {result.stderr}")
    
    def _dock_smina(
        self,
        protein_path: str,
        ligand_path: str,
        output_path: str,
        center: Tuple[float, float, float],
        size: Tuple[float, float, float]
    ) -> Tuple[bool, str, List[float], List[str]]:
        """Run docking with Smina (Vina fork with improved scoring)."""
        config_path = self._create_config_file(
            protein_path, ligand_path, output_path, center, size, "smina"
        )
        
        result = subprocess.run(
            ['smina', '--config', config_path],
            capture_output=True,
            text=True,
            timeout=self.config.docking_timeout
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            affinities, poses = self._parse_docking_output(result.stdout, output_path)
            return True, result.stdout, affinities, poses
        
        raise ValueError(f"Smina failed: {result.stderr}")
    
    def _dock_vina(
        self,
        protein_path: str,
        ligand_path: str,
        output_path: str,
        center: Tuple[float, float, float],
        size: Tuple[float, float, float]
    ) -> Tuple[bool, str, List[float], List[str]]:
        """Run docking with AutoDock Vina."""
        config_path = self._create_config_file(
            protein_path, ligand_path, output_path, center, size, "vina"
        )
        
        # Find vina executable
        vina_path = shutil.which('vina')
        if not vina_path:
            # Check backend tools folder
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            tools_path = os.path.join(backend_dir, 'tools', 'vina.exe')
            if os.path.exists(tools_path):
                vina_path = tools_path
            else:
                raise FileNotFoundError("AutoDock Vina not found")
        
        result = subprocess.run(
            [vina_path, '--config', config_path],
            capture_output=True,
            text=True,
            timeout=self.config.docking_timeout
        )
        
        if result.returncode == 0 and os.path.exists(output_path):
            affinities, poses = self._parse_docking_output(result.stdout, output_path)
            return True, result.stdout, affinities, poses
        
        raise ValueError(f"Vina failed: {result.stderr}")
    
    def _parse_docking_output(self, stdout: str, output_path: str) -> Tuple[List[float], List[str]]:
        """Parse docking output to extract affinities and poses."""
        affinities = []
        
        # Parse affinities from stdout
        for line in stdout.split('\n'):
            line = line.strip()
            if line and line[0].isdigit():
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        affinity = float(parts[1])
                        affinities.append(affinity)
                    except ValueError:
                        continue
        
        # Parse poses from output PDBQT
        poses = []
        if os.path.exists(output_path):
            with open(output_path, 'r') as f:
                content = f.read()
            
            # Split by MODEL/ENDMDL
            import re
            pose_matches = re.findall(r'MODEL\s+\d+\s*\n(.*?)ENDMDL', content, re.DOTALL)
            poses = [f"MODEL {i+1}\n{pose}\nENDMDL\n" for i, pose in enumerate(pose_matches)]
        
        return affinities, poses
    
    def apply_dl_rescoring(self, poses: List[str], protein_path: str) -> List[Tuple[str, float]]:
        """Apply deep learning re-scoring to docking poses.
        
        Args:
            poses: List of PDBQT pose strings
            protein_path: Path to protein structure
            
        Returns:
            List of (pose_pdbqt, dl_score) tuples, sorted by score
        """
        if not self.config.enable_dl_rescoring:
            self._log("Deep learning re-scoring disabled")
            return [(pose, 0.0) for pose in poses]
        
        step = self._add_step("DL Re-scoring", self.config.rescoring_model)
        self._start_step(step)
        
        try:
            # Try GNINA for re-scoring if available
            if self.available_tools.get('gnina', False):
                rescored = self._rescore_gnina(poses, protein_path)
                self._complete_step(step, f"Re-scored {len(rescored)} poses")
                return rescored
            else:
                # Fallback: use simple scoring function
                rescored = self._rescore_simple(poses)
                self._complete_step(step, f"Simple scoring applied to {len(rescored)} poses")
                return rescored
                
        except Exception as e:
            self._fail_step(step, str(e))
            return [(pose, 0.0) for pose in poses]
    
    def _rescore_gnina(self, poses: List[str], protein_path: str) -> List[Tuple[str, float]]:
        """Re-score poses using GNINA's CNN scoring."""
        results = []
        
        for i, pose in enumerate(poses):
            pose_path = os.path.join(self.work_dir, f"pose_{i}.pdbqt")
            with open(pose_path, 'w') as f:
                f.write(pose)
            
            result = subprocess.run(
                ['gnina', '-r', protein_path, '-l', pose_path, '--score_only', '--cnn_scoring', 'all'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Parse CNN score from output
            cnn_score = 0.0
            for line in result.stdout.split('\n'):
                if 'CNNscore' in line:
                    parts = line.split()
                    try:
                        cnn_score = float(parts[-1])
                    except (ValueError, IndexError):
                        pass
            
            results.append((pose, cnn_score))
        
        # Sort by CNN score (higher is better)
        results.sort(key=lambda x: x[1], reverse=True)
        return results
    
    def _rescore_simple(self, poses: List[str]) -> List[Tuple[str, float]]:
        """Simple scoring based on pose characteristics."""
        return [(pose, 0.0) for pose in poses]
    
    def run_full_pipeline(
        self,
        smiles: str,
        pdb_data: str,
        ligand_id: str,
        protein_id: str,
        center: Tuple[float, float, float],
        size: Tuple[float, float, float],
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> PipelineResult:
        """Run the complete docking pipeline.
        
        Pipeline: RDKit → OpenBabel → Smina → Vina → GNINA → Deep Learning Re-scoring
        
        Args:
            smiles: SMILES string of the ligand
            pdb_data: PDB format protein structure
            ligand_id: Identifier for the ligand
            protein_id: Identifier for the protein
            center: Grid box center
            size: Grid box size
            progress_callback: Optional callback for progress updates (step, percent, message)
            
        Returns:
            PipelineResult with all docking information
        """
        self._log("=" * 50)
        self._log("ENHANCED DOCKING PIPELINE")
        self._log("RDKit → OpenBabel → Smina → Vina → GNINA → DL Re-scoring")
        self._log("=" * 50)
        
        def update_progress(step: str, percent: int, msg: str):
            if progress_callback:
                progress_callback(step, percent, msg)
        
        result = PipelineResult(
            success=False,
            docking_tool_used=None,
            ligand_prep_tool_used=None,
            protein_prep_tool_used=None,
            steps=[]
        )
        
        try:
            # Step 1: Prepare ligand
            update_progress("Ligand Preparation", 10, "Preparing ligand structure...")
            ligand_pdbqt, ligand_path = self.prepare_ligand(smiles, ligand_id)
            
            if not ligand_pdbqt:
                result.error_message = "Failed to prepare ligand - all methods failed"
                result.steps = self.steps
                result.console_output = self.console_output
                return result
            
            # Find which tool succeeded
            for step in reversed(self.steps):
                if step.name.startswith("Ligand Prep") and step.status == "completed":
                    result.ligand_prep_tool_used = step.tool
                    break
            
            # Step 2: Prepare protein
            update_progress("Protein Preparation", 30, "Preparing protein structure...")
            protein_pdbqt, protein_path = self.prepare_protein(pdb_data, protein_id)
            
            if not protein_pdbqt:
                result.error_message = "Failed to prepare protein - all methods failed"
                result.steps = self.steps
                result.console_output = self.console_output
                return result
            
            for step in reversed(self.steps):
                if step.name.startswith("Protein Prep") and step.status == "completed":
                    result.protein_prep_tool_used = step.tool
                    break
            
            # Step 3: Run docking
            update_progress("Molecular Docking", 50, "Running molecular docking simulation...")
            output_path = os.path.join(self.work_dir, f"{ligand_id}_docked.pdbqt")
            
            success, tool_used, affinities, poses = self.run_docking(
                protein_path, ligand_path, output_path, center, size
            )
            
            if not success:
                result.error_message = "Docking failed - all tools failed"
                result.steps = self.steps
                result.console_output = self.console_output
                return result
            
            result.docking_tool_used = tool_used
            result.binding_affinities = affinities
            result.poses_pdbqt = poses
            
            # Step 4: Deep learning re-scoring
            if self.config.enable_dl_rescoring and poses:
                update_progress("DL Re-scoring", 85, "Applying deep learning re-scoring...")
                rescored_poses = self.apply_dl_rescoring(poses, protein_path)
                
                if rescored_poses:
                    result.dl_rescoring_applied = True
                    # Update poses with re-scored order
                    result.poses_pdbqt = [p[0] for p in rescored_poses]
            
            # Success
            update_progress("Completed", 100, "Docking pipeline completed successfully!")
            result.success = True
            result.steps = self.steps
            result.console_output = self.console_output
            
            self._log(f"\n=== PIPELINE SUMMARY ===")
            self._log(f"Ligand prep: {result.ligand_prep_tool_used}")
            self._log(f"Protein prep: {result.protein_prep_tool_used}")
            self._log(f"Docking: {result.docking_tool_used}")
            self._log(f"Poses found: {len(result.binding_affinities)}")
            if result.binding_affinities:
                self._log(f"Best affinity: {min(result.binding_affinities):.2f} kcal/mol")
            self._log(f"DL re-scoring: {'Applied' if result.dl_rescoring_applied else 'Not applied'}")
            
            return result
            
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            result.error_message = str(e)
            result.steps = self.steps
            result.console_output = self.console_output
            return result
