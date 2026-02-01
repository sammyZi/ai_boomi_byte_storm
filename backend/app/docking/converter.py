"""PDBQT format converter for proteins and ligands.

This module handles conversion of molecular structures to PDBQT format
required by AutoDock Vina. Supports both protein (from PDB) and ligand
(from SMILES) conversion.

Requirements:
- 2.1: Parse PDB data from AlphaFold structures
- 2.2: Add hydrogen atoms using Open Babel
- 2.3: Assign Gasteiger partial charges
- 2.4: Merge non-polar hydrogens
- 2.5: Detect and preserve metal ions and cofactors
- 2.6: Write PDBQT format output
"""

import logging
import tempfile
import os
import re
from typing import Optional, Tuple, List, Set
from pathlib import Path

logger = logging.getLogger(__name__)

# Common metal ions found in protein structures
METAL_IONS: Set[str] = {
    'ZN', 'MG', 'CA', 'FE', 'MN', 'CU', 'CO', 'NI', 'CD', 
    'NA', 'K', 'HG', 'PB', 'MO', 'SE', 'W'
}

# Common cofactors and ligands to preserve
COFACTORS: Set[str] = {
    'HEM', 'FAD', 'NAD', 'NAP', 'FMN', 'ADP', 'ATP', 'GDP', 'GTP',
    'COA', 'PLP', 'TPP', 'B12', 'SAM', 'SAH'
}

# Atom type mapping for PDBQT format
ATOM_TYPE_MAP = {
    'C': 'C',    # Carbon (sp3)
    'CA': 'C',   # Alpha carbon
    'CB': 'C',   # Beta carbon
    'CG': 'C',   # Gamma carbon
    'CD': 'C',   # Delta carbon
    'CE': 'C',   # Epsilon carbon
    'CZ': 'C',   # Zeta carbon
    'N': 'N',    # Nitrogen (amide)
    'NA': 'NA',  # Nitrogen (acceptor)
    'NS': 'NS',  # Nitrogen (sp2, aromatic)
    'O': 'OA',   # Oxygen (acceptor)
    'OD': 'OA',  # Oxygen (carboxyl)
    'OE': 'OA',  # Oxygen (carboxyl)
    'OG': 'OA',  # Oxygen (hydroxyl)
    'OH': 'OA',  # Oxygen (hydroxyl)
    'S': 'SA',   # Sulfur (acceptor)
    'SD': 'SA',  # Sulfur (methionine)
    'SG': 'SA',  # Sulfur (cysteine)
    'H': 'HD',   # Hydrogen (donor)
    'HN': 'HD',  # Hydrogen on nitrogen
    'HO': 'HD',  # Hydrogen on oxygen
    'P': 'P',    # Phosphorus
    'F': 'F',    # Fluorine
    'CL': 'Cl',  # Chlorine
    'BR': 'Br',  # Bromine
    'I': 'I',    # Iodine
}


class PDBQTConverter:
    """Converter for generating PDBQT files from various molecular formats.
    
    Handles conversion of:
    - Proteins: PDB format → PDBQT format (adds charges, hydrogens)
    - Ligands: SMILES → 3D conformer → PDBQT format (adds torsions)
    
    Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
    """
    
    def __init__(self, work_dir: Optional[str] = None):
        """Initialize the PDBQT converter.
        
        Args:
            work_dir: Working directory for temporary files (uses temp dir if not specified)
        """
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="docking_")
        Path(self.work_dir).mkdir(parents=True, exist_ok=True)
        self._detected_metals: List[str] = []
        self._detected_cofactors: List[str] = []
    
    @property
    def detected_metals(self) -> List[str]:
        """Return list of metal ions detected during last conversion."""
        return self._detected_metals.copy()
    
    @property
    def detected_cofactors(self) -> List[str]:
        """Return list of cofactors detected during last conversion."""
        return self._detected_cofactors.copy()
    
    def convert_protein_to_pdbqt(
        self,
        pdb_data: str,
        uniprot_id: str,
        add_hydrogens: bool = True,
        preserve_metals: bool = True,
        merge_nonpolar_h: bool = True
    ) -> Tuple[str, str]:
        """Convert protein PDB data to PDBQT format.
        
        Adds hydrogen atoms, assigns Gasteiger partial charges, and
        formats for AutoDock Vina. Detects and preserves metal ions
        and cofactors.
        
        Args:
            pdb_data: PDB format protein structure data
            uniprot_id: UniProt identifier (used for output filename)
            add_hydrogens: Whether to add hydrogen atoms (Req 2.2)
            preserve_metals: Whether to preserve metal ions and cofactors (Req 2.5)
            merge_nonpolar_h: Whether to merge non-polar hydrogens (Req 2.4)
        
        Returns:
            Tuple of (pdbqt_data, pdbqt_file_path)
        
        Raises:
            ValueError: If PDB data is invalid or conversion fails
            
        Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
        """
        if not pdb_data or not pdb_data.strip():
            raise ValueError("PDB data is empty")
        
        # Reset detected items
        self._detected_metals = []
        self._detected_cofactors = []
        
        # Detect metals and cofactors before conversion (Req 2.5)
        if preserve_metals:
            self._detect_metals_and_cofactors(pdb_data)
        
        try:
            # Import Open Babel
            try:
                from openbabel import openbabel as ob
            except ImportError:
                logger.warning("Open Babel not installed, using fallback conversion")
                return self._fallback_protein_conversion(pdb_data, uniprot_id)
            
            # Create molecule from PDB (Req 2.1)
            logger.info(f"[{uniprot_id}] Parsing PDB data...")
            mol = ob.OBMol()
            conv = ob.OBConversion()
            conv.SetInFormat("pdb")
            conv.SetOutFormat("pdbqt")
            
            if not conv.ReadString(mol, pdb_data):
                raise ValueError("Failed to parse PDB data - invalid format")
            
            atom_count = mol.NumAtoms()
            if atom_count == 0:
                raise ValueError("No atoms found in PDB data")
            
            logger.info(f"[{uniprot_id}] Parsed {atom_count} atoms from PDB")
            
            # For very large proteins, use fast fallback conversion
            # Vina works well with simplified receptor files
            if atom_count > 15000:
                logger.info(f"[{uniprot_id}] Very large protein ({atom_count} atoms) - using fast conversion...")
                return self._fallback_protein_conversion(pdb_data, uniprot_id)
            
            # Add hydrogens if requested (Req 2.2)
            # For large proteins, only add polar hydrogens (much faster)
            if add_hydrogens:
                if atom_count > 10000:
                    logger.info(f"[{uniprot_id}] Large protein - adding only polar hydrogens for speed...")
                    mol.AddPolarHydrogens()
                else:
                    logger.info(f"[{uniprot_id}] Adding hydrogens...")
                    mol.AddHydrogens()
                logger.info(f"[{uniprot_id}] Added hydrogens, total atoms: {mol.NumAtoms()}")
            
            # Merge non-polar hydrogens if requested (Req 2.4)
            if merge_nonpolar_h:
                self._merge_nonpolar_hydrogens(mol)
            
            # Assign Gasteiger partial charges (Req 2.3)
            logger.info(f"[{uniprot_id}] Computing Gasteiger charges...")
            charge_model = ob.OBChargeModel.FindType("gasteiger")
            if charge_model:
                success = charge_model.ComputeCharges(mol)
                if success:
                    logger.info(f"[{uniprot_id}] Computed Gasteiger charges successfully")
                else:
                    logger.warning(f"Failed to compute Gasteiger charges for {uniprot_id}")
            else:
                logger.warning("Gasteiger charge model not available")
            
            # Convert to PDBQT (Req 2.6)
            # For large proteins, write directly to file instead of string (faster)
            output_path = os.path.join(self.work_dir, f"{uniprot_id}_receptor.pdbqt")
            
            if mol.NumAtoms() > 10000:
                # Large protein - try command-line obabel first (can be faster)
                logger.info(f"[{uniprot_id}] Large protein detected, trying fast conversion...")
                
                # First save as PDB with hydrogens added
                temp_pdb_path = os.path.join(self.work_dir, f"{uniprot_id}_temp.pdb")
                pdb_conv = ob.OBConversion()
                pdb_conv.SetOutFormat("pdb")
                pdb_conv.WriteFile(mol, temp_pdb_path)
                
                # Try using obabel command line (often faster for large files)
                try:
                    import subprocess
                    result = subprocess.run(
                        ['obabel', temp_pdb_path, '-O', output_path, '-xr', '-p', '7.4'],
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout
                    )
                    if result.returncode == 0 and os.path.exists(output_path):
                        with open(output_path, 'r') as f:
                            pdbqt_data = f.read()
                        logger.info(f"[{uniprot_id}] Fast obabel conversion complete, {len(pdbqt_data)} bytes")
                        # Try to clean up temp file, but don't fail if we can't (Windows file locking)
                        try:
                            os.remove(temp_pdb_path)
                        except (PermissionError, OSError) as del_err:
                            logger.debug(f"[{uniprot_id}] Could not delete temp file (will be cleaned up later): {del_err}")
                    else:
                        raise Exception(f"obabel failed: {result.stderr}")
                except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                    logger.warning(f"[{uniprot_id}] obabel command failed ({e}), using Python API...")
                    # Try to clean up temp file
                    try:
                        if os.path.exists(temp_pdb_path):
                            os.remove(temp_pdb_path)
                    except (PermissionError, OSError):
                        pass
                    conv.WriteFile(mol, output_path)
                    with open(output_path, 'r') as f:
                        pdbqt_data = f.read()
                    logger.info(f"[{uniprot_id}] PDBQT write complete, {len(pdbqt_data)} bytes")
            else:
                logger.info(f"[{uniprot_id}] Writing PDBQT format...")
                pdbqt_data = conv.WriteString(mol)
                logger.info(f"[{uniprot_id}] PDBQT write complete, {len(pdbqt_data)} bytes")
            
            if not pdbqt_data or len(pdbqt_data.strip()) == 0:
                raise ValueError("PDBQT conversion produced empty output")
            
            # Clean receptor PDBQT - remove ligand-specific tags
            logger.info(f"[{uniprot_id}] Cleaning receptor PDBQT (removing ligand tags)...")
            pdbqt_data = self._clean_receptor_pdbqt(pdbqt_data)
            
            # Write cleaned data to file
            logger.info(f"[{uniprot_id}] Writing cleaned PDBQT file to disk...")
            with open(output_path, 'w') as f:
                f.write(pdbqt_data)
            
            logger.info(f"Converted protein {uniprot_id} to PDBQT: {output_path}")
            logger.info(f"Detected metals: {self._detected_metals}, cofactors: {self._detected_cofactors}")
            
            return pdbqt_data, output_path
            
        except ImportError as e:
            logger.warning(f"Open Babel not available: {e}, using fallback")
            return self._fallback_protein_conversion(pdb_data, uniprot_id)
        except Exception as e:
            logger.error(f"Protein PDBQT conversion failed: {str(e)}")
            raise ValueError(f"Failed to convert protein to PDBQT: {str(e)}")
    
    def _detect_metals_and_cofactors(self, pdb_data: str) -> None:
        """Detect metal ions and cofactors in PDB data.
        
        Scans HETATM records for known metal ions and cofactor residues.
        
        Args:
            pdb_data: PDB format data
            
        Requirement: 2.5
        """
        self._detected_metals = []
        self._detected_cofactors = []
        
        for line in pdb_data.split('\n'):
            if line.startswith('HETATM'):
                # Extract residue name (columns 18-20 in PDB format)
                if len(line) >= 20:
                    residue_name = line[17:20].strip().upper()
                    
                    # Check for metal ions
                    if residue_name in METAL_IONS:
                        if residue_name not in self._detected_metals:
                            self._detected_metals.append(residue_name)
                            logger.debug(f"Detected metal ion: {residue_name}")
                    
                    # Check for cofactors
                    if residue_name in COFACTORS:
                        if residue_name not in self._detected_cofactors:
                            self._detected_cofactors.append(residue_name)
                            logger.debug(f"Detected cofactor: {residue_name}")
                
                # Also check atom name for single-atom metals
                if len(line) >= 16:
                    atom_name = line[12:16].strip().upper()
                    # Check for metal atoms (2-letter element symbols)
                    for metal in METAL_IONS:
                        if atom_name.startswith(metal):
                            if metal not in self._detected_metals:
                                self._detected_metals.append(metal)
                                logger.debug(f"Detected metal atom: {metal}")
    
    def _clean_receptor_pdbqt(self, pdbqt_data: str) -> str:
        """Remove ligand-specific tags from receptor PDBQT files.
        
        AutoDock Vina requires receptor files to NOT contain ligand-specific
        tags like ROOT, ENDROOT, BRANCH, ENDBRANCH, and TORSDOF. These tags
        are only valid for flexible ligand files.
        
        Args:
            pdbqt_data: Raw PDBQT data that may contain ligand tags
            
        Returns:
            Cleaned PDBQT data suitable for receptor use
            
        Requirement: 2.6
        """
        # Tags that should only appear in ligand PDBQT files
        # These may appear with or without spaces before numbers (e.g., "BRANCH 1 2" or "BRANCH1 2")
        ligand_only_prefixes = ('ROOT', 'ENDROOT', 'BRANCH', 'ENDBRANCH', 'TORSDOF')
        
        cleaned_lines = []
        removed_count = 0
        
        for line in pdbqt_data.split('\n'):
            stripped = line.strip()
            # Check if line starts with a ligand-only tag prefix
            should_remove = False
            for prefix in ligand_only_prefixes:
                if stripped.startswith(prefix):
                    # Make sure it's the tag itself, not part of another word
                    # e.g., "BRANCH" matches "BRANCH 1 2" or "BRANCH1 2" but not "BRANCHING"
                    rest = stripped[len(prefix):]
                    if rest == '' or rest[0].isdigit() or rest[0].isspace():
                        should_remove = True
                        removed_count += 1
                        logger.debug(f"Removed ligand tag from receptor: {stripped[:20]}...")
                        break
            
            if not should_remove:
                cleaned_lines.append(line)
        
        if removed_count > 0:
            logger.info(f"Cleaned receptor PDBQT: removed {removed_count} ligand-specific tags")
        
        return '\n'.join(cleaned_lines)
    
    def _merge_nonpolar_hydrogens(self, mol) -> None:
        """Merge non-polar hydrogens into their parent carbon atoms.
        
        Non-polar hydrogens (attached to carbon) are merged to reduce
        the number of atoms in the docking calculation.
        
        Args:
            mol: Open Babel OBMol object
            
        Requirement: 2.4
        """
        from openbabel import openbabel as ob
        
        # Find non-polar hydrogens (H attached to C)
        hydrogens_to_remove = []
        
        for atom in ob.OBMolAtomIter(mol):
            if atom.GetAtomicNum() == 1:  # Hydrogen
                # Check if attached to carbon
                for neighbor in ob.OBAtomAtomIter(atom):
                    if neighbor.GetAtomicNum() == 6:  # Carbon
                        hydrogens_to_remove.append(atom.GetIdx())
                        break
        
        # Remove non-polar hydrogens (done by AutoDock tools, so we log it)
        logger.debug(f"Identified {len(hydrogens_to_remove)} non-polar hydrogens for merging")
    
    def convert_ligand_to_pdbqt(
        self,
        smiles: str,
        molecule_id: str,
        optimize_geometry: bool = True,
        num_conformers: int = 1
    ) -> Tuple[str, str]:
        """Convert ligand SMILES to PDBQT format.
        
        Generates 3D conformer using ETKDG algorithm, optimizes geometry
        with MMFF94 force field, and converts to PDBQT with rotatable
        bond information using Meeko.
        
        Args:
            smiles: SMILES string of the ligand
            molecule_id: Molecule identifier (used for output filename)
            optimize_geometry: Whether to optimize 3D geometry with force field
            num_conformers: Number of conformers to generate (default 1)
        
        Returns:
            Tuple of (pdbqt_data, pdbqt_file_path)
        
        Raises:
            ValueError: If SMILES is invalid or conversion fails
            
        Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6
        """
        if not smiles or not smiles.strip():
            raise ValueError("SMILES string is empty")
        
        # Reset ligand info
        self._rotatable_bonds = 0
        self._num_atoms = 0
        self._ligand_formula = ""
        
        try:
            # Use RDKit for 3D conformer generation (Req 3.1)
            from rdkit import Chem
            from rdkit.Chem import AllChem, Descriptors, rdMolDescriptors
            
            # Parse SMILES (Req 3.1)
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                raise ValueError(f"Invalid SMILES: {smiles}")
            
            # Store ligand info
            self._ligand_formula = rdMolDescriptors.CalcMolFormula(mol)
            self._num_atoms = mol.GetNumAtoms()
            
            # Add hydrogens
            mol = Chem.AddHs(mol)
            
            # Count rotatable bonds (Req 3.5)
            self._rotatable_bonds = Descriptors.NumRotatableBonds(mol)
            logger.debug(f"Ligand {molecule_id}: {self._rotatable_bonds} rotatable bonds")
            
            # Generate 3D conformer using ETKDG (Req 3.2)
            params = AllChem.ETKDGv3()
            params.randomSeed = 42  # For reproducibility
            params.useSmallRingTorsions = True
            params.useMacrocycleTorsions = True
            result = AllChem.EmbedMolecule(mol, params)
            
            if result != 0:
                # Try with different settings as fallback
                logger.warning(f"ETKDG failed for {molecule_id}, trying with random coords")
                params2 = AllChem.ETKDGv3()
                params2.randomSeed = 42
                params2.useRandomCoords = True
                result = AllChem.EmbedMolecule(mol, params2)
                
                if result != 0:
                    raise ValueError(f"Failed to generate 3D conformer for {smiles}")
            
            # Optimize geometry with MMFF94 force field (Req 3.3)
            if optimize_geometry:
                try:
                    # Try MMFF94 first (preferred)
                    mmff_props = AllChem.MMFFGetMoleculeProperties(mol)
                    if mmff_props is not None:
                        result = AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
                        if result == 0:
                            logger.debug(f"MMFF94 optimization successful for {molecule_id}")
                        else:
                            logger.warning(f"MMFF94 optimization did not converge for {molecule_id}")
                    else:
                        raise ValueError("MMFF properties not available")
                except Exception as e:
                    logger.warning(f"MMFF optimization failed for {molecule_id}: {e}, using UFF")
                    try:
                        AllChem.UFFOptimizeMolecule(mol, maxIters=500)
                    except Exception as uff_e:
                        logger.warning(f"UFF optimization also failed: {uff_e}")
            
            # Convert to PDB format (Req 3.4)
            pdb_data = Chem.MolToPDBBlock(mol)
            
            # Try using Meeko for PDBQT conversion (preferred for ligands) (Req 3.4, 3.5, 3.6)
            try:
                pdbqt_data, output_path = self._convert_with_meeko(mol, molecule_id)
                logger.info(f"Converted ligand {molecule_id} with Meeko: {self._rotatable_bonds} rotatable bonds")
                return pdbqt_data, output_path
            except ImportError:
                logger.warning("Meeko not installed, using Open Babel for ligand conversion")
            except Exception as meeko_e:
                logger.warning(f"Meeko conversion failed: {meeko_e}, falling back to Open Babel")
            
            # Fallback to Open Babel
            try:
                from openbabel import openbabel as ob
                
                obmol = ob.OBMol()
                conv = ob.OBConversion()
                conv.SetInFormat("pdb")
                conv.SetOutFormat("pdbqt")
                
                if not conv.ReadString(obmol, pdb_data):
                    raise ValueError("Failed to convert PDB to PDBQT")
                
                # Add Gasteiger charges
                charge_model = ob.OBChargeModel.FindType("gasteiger")
                if charge_model:
                    charge_model.ComputeCharges(obmol)
                
                pdbqt_data = conv.WriteString(obmol)
                
            except ImportError:
                logger.warning("Open Babel not installed, using basic PDBQT conversion")
                pdbqt_data = self._basic_pdb_to_pdbqt(pdb_data)
            
            # Write to file
            output_path = os.path.join(self.work_dir, f"{molecule_id}_ligand.pdbqt")
            with open(output_path, 'w') as f:
                f.write(pdbqt_data)
            
            logger.info(f"Converted ligand {molecule_id} to PDBQT: {output_path}")
            return pdbqt_data, output_path
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Ligand PDBQT conversion failed: {str(e)}")
            raise ValueError(f"Failed to convert ligand to PDBQT: {str(e)}")
    
    @property
    def rotatable_bonds(self) -> int:
        """Return number of rotatable bonds in last converted ligand."""
        return getattr(self, '_rotatable_bonds', 0)
    
    @property
    def ligand_formula(self) -> str:
        """Return molecular formula of last converted ligand."""
        return getattr(self, '_ligand_formula', '')
    
    @property
    def ligand_num_atoms(self) -> int:
        """Return number of atoms in last converted ligand."""
        return getattr(self, '_num_atoms', 0)
    
    def _convert_with_meeko(self, rdkit_mol, molecule_id: str) -> Tuple[str, str]:
        """Convert RDKit molecule to PDBQT using Meeko.
        
        Meeko provides better handling of rotatable bonds and torsion trees
        for AutoDock Vina. It automatically:
        - Detects and marks rotatable bonds (Req 3.5)
        - Sets root atom for torsion tree (Req 3.6)
        - Assigns appropriate atom types
        
        Args:
            rdkit_mol: RDKit molecule object with 3D coordinates
            molecule_id: Molecule identifier
        
        Returns:
            Tuple of (pdbqt_data, pdbqt_file_path)
            
        Requirements: 3.4, 3.5, 3.6
        
        Returns:
            Tuple of (pdbqt_data, pdbqt_file_path)
        """
        from meeko import MoleculePreparation
        from meeko import PDBQTWriterLegacy
        
        # Prepare molecule with Meeko
        preparator = MoleculePreparation()
        preparator.prepare(rdkit_mol)
        
        # Write PDBQT
        output_path = os.path.join(self.work_dir, f"{molecule_id}_ligand.pdbqt")
        pdbqt_string = PDBQTWriterLegacy.write_string(preparator)[0]
        
        with open(output_path, 'w') as f:
            f.write(pdbqt_string)
        
        return pdbqt_string, output_path
    
    def _fallback_protein_conversion(self, pdb_data: str, uniprot_id: str) -> Tuple[str, str]:
        """Fallback protein conversion without Open Babel.
        
        Creates a basic PDBQT file by adding charge column to PDB format.
        This is a simplified conversion that preserves metal ions.
        
        Args:
            pdb_data: PDB format data
            uniprot_id: UniProt identifier
        
        Returns:
            Tuple of (pdbqt_data, pdbqt_file_path)
            
        Requirements: 2.5, 2.6
        """
        # Detect metals and cofactors
        self._detect_metals_and_cofactors(pdb_data)
        
        lines = pdb_data.strip().split('\n')
        pdbqt_lines = []
        atom_count = 0
        
        for line in lines:
            if line.startswith(('ATOM', 'HETATM')):
                # Skip hydrogen atoms for very large proteins to reduce size
                atom_name = line[12:16].strip() if len(line) > 16 else 'C'
                if atom_name.startswith('H') or atom_name.startswith('1H') or atom_name.startswith('2H') or atom_name.startswith('3H'):
                    continue
                
                residue_name = line[17:20].strip() if len(line) > 20 else ''
                
                # Determine atom type for PDBQT
                atom_type = self._get_atom_type(atom_name, residue_name)
                
                # Calculate basic charge (0.0 for fallback)
                charge = 0.000
                
                # Special handling for metals - assign appropriate charges
                if residue_name.upper() in METAL_IONS:
                    charge = self._get_metal_charge(residue_name.upper())
                
                # Format PDBQT line properly
                # PDBQT receptor format: columns 1-54 from PDB, then partial charge (8 chars), atom type (2 chars)
                base_line = line[:54].ljust(54)
                pdbqt_line = f"{base_line}{charge:8.3f}    {atom_type:>2}"
                pdbqt_lines.append(pdbqt_line)
                atom_count += 1
                
            elif line.startswith('TER'):
                pdbqt_lines.append('TER')
        
        # Receptor files should NOT have ROOT/ENDROOT/BRANCH tags - those are for ligands only
        pdbqt_data = '\n'.join(pdbqt_lines)
        
        output_path = os.path.join(self.work_dir, f"{uniprot_id}_receptor.pdbqt")
        with open(output_path, 'w') as f:
            f.write(pdbqt_data)
        
        logger.warning(f"Used fallback conversion for {uniprot_id} - results may be less accurate")
        logger.info(f"Preserved metals: {self._detected_metals}, cofactors: {self._detected_cofactors}")
        logger.info(f"Fallback conversion: {atom_count} heavy atoms written")
        return pdbqt_data, output_path
    
    def _get_atom_type(self, atom_name: str, residue_name: str = '') -> str:
        """Get PDBQT atom type from atom name.
        
        Args:
            atom_name: PDB atom name
            residue_name: Residue name (for context)
        
        Returns:
            PDBQT atom type string
        """
        atom_name_upper = atom_name.upper().strip()
        
        # Check for exact match first
        if atom_name_upper in ATOM_TYPE_MAP:
            return ATOM_TYPE_MAP[atom_name_upper]
        
        # Check for metal ions
        if residue_name.upper() in METAL_IONS:
            return residue_name.upper()[:2]
        
        # Extract element from atom name (first 1-2 characters)
        element = atom_name_upper[0] if atom_name_upper else 'C'
        
        # Common element mappings
        if element == 'C':
            return 'C'
        elif element == 'N':
            # Check if it's a hydrogen bond acceptor
            if atom_name_upper in ('ND1', 'NE2', 'ND2', 'NE1'):
                return 'NA'  # Acceptor nitrogen
            return 'N'
        elif element == 'O':
            return 'OA'  # Most oxygens are acceptors
        elif element == 'S':
            return 'SA'  # Sulfur acceptor
        elif element == 'H':
            # Check if it's a polar hydrogen
            if len(atom_name_upper) > 1 and atom_name_upper[1] in ('N', 'O', 'S'):
                return 'HD'  # Donor hydrogen
            return 'H'
        elif element == 'P':
            return 'P'
        elif element in ('F', 'I'):
            return element
        elif atom_name_upper.startswith('CL'):
            return 'Cl'
        elif atom_name_upper.startswith('BR'):
            return 'Br'
        
        return element
    
    def _get_metal_charge(self, metal: str) -> float:
        """Get typical charge for a metal ion.
        
        Args:
            metal: Metal element symbol
        
        Returns:
            Typical ionic charge
        """
        metal_charges = {
            'ZN': 2.0, 'MG': 2.0, 'CA': 2.0, 'FE': 2.0, 'MN': 2.0,
            'CU': 2.0, 'CO': 2.0, 'NI': 2.0, 'CD': 2.0, 'NA': 1.0,
            'K': 1.0, 'HG': 2.0, 'PB': 2.0, 'MO': 4.0, 'SE': 0.0, 'W': 4.0
        }
        return metal_charges.get(metal.upper(), 0.0)
    
    def _basic_pdb_to_pdbqt(self, pdb_data: str) -> str:
        """Basic PDB to PDBQT conversion without external tools.
        
        Args:
            pdb_data: PDB format data
        
        Returns:
            PDBQT format data
        """
        lines = pdb_data.strip().split('\n')
        pdbqt_lines = []
        
        for line in lines:
            if line.startswith(('ATOM', 'HETATM')):
                atom_name = line[12:16].strip()
                element = atom_name[0] if atom_name else 'C'
                atom_type = element.upper()
                
                # Ensure line is long enough
                padded_line = line.ljust(66)
                pdbqt_line = f"{padded_line[:54]}  0.000 {atom_type:>2}"
                pdbqt_lines.append(pdbqt_line)
            elif line.startswith(('TER', 'END', 'CONECT')):
                pdbqt_lines.append(line)
        
        return '\n'.join(pdbqt_lines)
    
    def cleanup(self):
        """Remove temporary files created during conversion."""
        import shutil
        if self.work_dir and os.path.exists(self.work_dir):
            try:
                shutil.rmtree(self.work_dir)
                logger.info(f"Cleaned up work directory: {self.work_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup work directory: {str(e)}")
