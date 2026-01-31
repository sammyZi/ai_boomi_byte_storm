"""PDBQT format converter for proteins and ligands.

This module handles conversion of molecular structures to PDBQT format
required by AutoDock Vina. Supports both protein (from PDB) and ligand
(from SMILES) conversion.
"""

import logging
import tempfile
import os
from typing import Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class PDBQTConverter:
    """Converter for generating PDBQT files from various molecular formats.
    
    Handles conversion of:
    - Proteins: PDB format → PDBQT format (adds charges, hydrogens)
    - Ligands: SMILES → 3D conformer → PDBQT format (adds torsions)
    """
    
    def __init__(self, work_dir: Optional[str] = None):
        """Initialize the PDBQT converter.
        
        Args:
            work_dir: Working directory for temporary files (uses temp dir if not specified)
        """
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="docking_")
        Path(self.work_dir).mkdir(parents=True, exist_ok=True)
    
    def convert_protein_to_pdbqt(
        self,
        pdb_data: str,
        uniprot_id: str,
        add_hydrogens: bool = True,
        preserve_metals: bool = True
    ) -> Tuple[str, str]:
        """Convert protein PDB data to PDBQT format.
        
        Adds hydrogen atoms, assigns Gasteiger partial charges, and
        formats for AutoDock Vina.
        
        Args:
            pdb_data: PDB format protein structure data
            uniprot_id: UniProt identifier (used for output filename)
            add_hydrogens: Whether to add hydrogen atoms
            preserve_metals: Whether to preserve metal ions and cofactors
        
        Returns:
            Tuple of (pdbqt_data, pdbqt_file_path)
        
        Raises:
            ValueError: If PDB data is invalid or conversion fails
        """
        try:
            # Import Open Babel
            try:
                from openbabel import openbabel as ob
            except ImportError:
                logger.warning("Open Babel not installed, using fallback conversion")
                return self._fallback_protein_conversion(pdb_data, uniprot_id)
            
            # Create molecule from PDB
            mol = ob.OBMol()
            conv = ob.OBConversion()
            conv.SetInFormat("pdb")
            conv.SetOutFormat("pdbqt")
            
            if not conv.ReadString(mol, pdb_data):
                raise ValueError("Failed to parse PDB data")
            
            # Add hydrogens if requested
            if add_hydrogens:
                mol.AddHydrogens()
            
            # Assign Gasteiger partial charges
            charge_model = ob.OBChargeModel.FindType("gasteiger")
            if charge_model:
                charge_model.ComputeCharges(mol)
            
            # Convert to PDBQT
            pdbqt_data = conv.WriteString(mol)
            
            # Write to file
            output_path = os.path.join(self.work_dir, f"{uniprot_id}_receptor.pdbqt")
            with open(output_path, 'w') as f:
                f.write(pdbqt_data)
            
            logger.info(f"Converted protein {uniprot_id} to PDBQT: {output_path}")
            return pdbqt_data, output_path
            
        except Exception as e:
            logger.error(f"Protein PDBQT conversion failed: {str(e)}")
            raise ValueError(f"Failed to convert protein to PDBQT: {str(e)}")
    
    def convert_ligand_to_pdbqt(
        self,
        smiles: str,
        molecule_id: str,
        optimize_geometry: bool = True
    ) -> Tuple[str, str]:
        """Convert ligand SMILES to PDBQT format.
        
        Generates 3D conformer, optimizes geometry, and converts to PDBQT
        with rotatable bond information.
        
        Args:
            smiles: SMILES string of the ligand
            molecule_id: Molecule identifier (used for output filename)
            optimize_geometry: Whether to optimize 3D geometry with force field
        
        Returns:
            Tuple of (pdbqt_data, pdbqt_file_path)
        
        Raises:
            ValueError: If SMILES is invalid or conversion fails
        """
        try:
            # Use RDKit for 3D conformer generation
            from rdkit import Chem
            from rdkit.Chem import AllChem
            
            # Parse SMILES
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                raise ValueError(f"Invalid SMILES: {smiles}")
            
            # Add hydrogens
            mol = Chem.AddHs(mol)
            
            # Generate 3D conformer using ETKDG
            params = AllChem.ETKDGv3()
            params.randomSeed = 42  # For reproducibility
            result = AllChem.EmbedMolecule(mol, params)
            
            if result != 0:
                # Try with random coordinates as fallback
                AllChem.EmbedMolecule(mol, randomSeed=42)
            
            # Optimize geometry with MMFF94 force field
            if optimize_geometry:
                try:
                    AllChem.MMFFOptimizeMolecule(mol, maxIters=500)
                except Exception:
                    logger.warning(f"MMFF optimization failed for {molecule_id}, using UFF")
                    AllChem.UFFOptimizeMolecule(mol, maxIters=500)
            
            # Convert to PDB format first
            pdb_data = Chem.MolToPDBBlock(mol)
            
            # Try using Meeko for PDBQT conversion (preferred for ligands)
            try:
                pdbqt_data, output_path = self._convert_with_meeko(mol, molecule_id)
                return pdbqt_data, output_path
            except ImportError:
                logger.warning("Meeko not installed, using Open Babel for ligand conversion")
            
            # Fallback to Open Babel
            try:
                from openbabel import openbabel as ob
                
                obmol = ob.OBMol()
                conv = ob.OBConversion()
                conv.SetInFormat("pdb")
                conv.SetOutFormat("pdbqt")
                
                if not conv.ReadString(obmol, pdb_data):
                    raise ValueError("Failed to convert PDB to PDBQT")
                
                # Add charges
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
            
        except Exception as e:
            logger.error(f"Ligand PDBQT conversion failed: {str(e)}")
            raise ValueError(f"Failed to convert ligand to PDBQT: {str(e)}")
    
    def _convert_with_meeko(self, rdkit_mol, molecule_id: str) -> Tuple[str, str]:
        """Convert RDKit molecule to PDBQT using Meeko.
        
        Meeko provides better handling of rotatable bonds for AutoDock Vina.
        
        Args:
            rdkit_mol: RDKit molecule object with 3D coordinates
            molecule_id: Molecule identifier
        
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
        This is a simplified conversion and may not work for all docking scenarios.
        
        Args:
            pdb_data: PDB format data
            uniprot_id: UniProt identifier
        
        Returns:
            Tuple of (pdbqt_data, pdbqt_file_path)
        """
        lines = pdb_data.strip().split('\n')
        pdbqt_lines = []
        
        for line in lines:
            if line.startswith(('ATOM', 'HETATM')):
                # Add partial charge (0.000) and atom type to PDBQT format
                atom_name = line[12:16].strip()
                element = atom_name[0] if atom_name else 'C'
                
                # Basic atom type mapping
                atom_type = element.upper()
                if atom_type == 'C':
                    atom_type = 'C'
                elif atom_type == 'N':
                    atom_type = 'N'
                elif atom_type == 'O':
                    atom_type = 'OA'
                elif atom_type == 'S':
                    atom_type = 'SA'
                elif atom_type == 'H':
                    atom_type = 'HD'
                
                # Format PDBQT line (charge = 0.000, atom_type at end)
                pdbqt_line = f"{line[:54]}  0.000 {atom_type:>2}"
                pdbqt_lines.append(pdbqt_line)
            elif line.startswith(('TER', 'END')):
                pdbqt_lines.append(line)
        
        pdbqt_data = '\n'.join(pdbqt_lines)
        
        output_path = os.path.join(self.work_dir, f"{uniprot_id}_receptor.pdbqt")
        with open(output_path, 'w') as f:
            f.write(pdbqt_data)
        
        logger.warning(f"Used fallback conversion for {uniprot_id} - results may be less accurate")
        return pdbqt_data, output_path
    
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
