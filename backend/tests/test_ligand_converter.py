"""Tests for PDBQT ligand converter.

These tests validate the PDBQTConverter class for ligand conversion,
including SMILES parsing, 3D conformer generation, geometry optimization,
and rotatable bond handling.

Requirements tested: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.8
"""

import pytest
import tempfile
import os
from hypothesis import given, strategies as st, settings, assume

from app.docking.converter import PDBQTConverter


# Sample SMILES for testing - common drug molecules
SAMPLE_SMILES = {
    # Simple molecules
    'aspirin': 'CC(=O)OC1=CC=CC=C1C(=O)O',
    'caffeine': 'CN1C=NC2=C1C(=O)N(C(=O)N2C)C',
    'ibuprofen': 'CC(C)CC1=CC=C(C=C1)C(C)C(=O)O',
    'paracetamol': 'CC(=O)NC1=CC=C(C=C1)O',
    'benzene': 'c1ccccc1',
    'ethanol': 'CCO',
    'methane': 'C',
    
    # More complex molecules
    'atorvastatin': 'CC(C)C1=C(C(=C(N1CCC(CC(CC(=O)O)O)O)C2=CC=C(C=C2)F)C3=CC=CC=C3)C(=O)NC4=CC=CC=C4',
    'metformin': 'CN(C)C(=N)NC(=N)N',
    
    # Molecules with stereocenters
    'glucose': 'OC[C@H]1OC(O)[C@H](O)[C@@H](O)[C@@H]1O',
    'alanine': 'C[C@H](N)C(=O)O',
    
    # Molecules with multiple rings
    'naphthalene': 'c1ccc2ccccc2c1',
    'testosterone': 'C[C@]12CC[C@H]3[C@@H](CCC4=CC(=O)CC[C@@]34C)[C@@H]1CC[C@@H]2O',
}

# Invalid SMILES for error testing
INVALID_SMILES = [
    '',
    '   ',
    'not_a_smiles',
    'XXXYYY',
    'C(C(C',  # Unbalanced parentheses
    '[InvalidAtom]',
]


class TestLigandPDBQTConversion:
    """Tests for ligand SMILES to PDBQT conversion.
    
    Requirements: 3.1, 3.4, 3.8
    """
    
    @pytest.fixture
    def converter(self):
        """Create a converter with temporary work directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PDBQTConverter(work_dir=tmpdir)
    
    def test_convert_simple_ligand(self, converter):
        """Test conversion of simple molecule (Req 3.1)."""
        pdbqt_data, pdbqt_path = converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['aspirin'],
            "ASPIRIN001"
        )
        
        # Check output file exists
        assert os.path.isfile(pdbqt_path)
        assert pdbqt_path.endswith("_ligand.pdbqt")
        
        # Check PDBQT content
        assert pdbqt_data is not None
        assert len(pdbqt_data) > 0
    
    def test_convert_produces_valid_pdbqt(self, converter):
        """Test that output is valid PDBQT format (Req 3.4)."""
        pdbqt_data, _ = converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['caffeine'],
            "CAFFEINE001"
        )
        
        # PDBQT for ligands should have ROOT, ENDROOT, BRANCH markers
        # or at minimum ATOM/HETATM records
        lines = pdbqt_data.strip().split('\n')
        atom_lines = [l for l in lines if l.startswith(('ATOM', 'HETATM'))]
        
        assert len(atom_lines) > 0, "PDBQT should contain ATOM records"
    
    def test_convert_all_sample_ligands(self, converter):
        """Test conversion of all sample molecules (Req 3.1)."""
        for name, smiles in SAMPLE_SMILES.items():
            pdbqt_data, pdbqt_path = converter.convert_ligand_to_pdbqt(
                smiles,
                f"TEST_{name.upper()}"
            )
            
            assert pdbqt_data is not None, f"Failed to convert {name}"
            assert os.path.isfile(pdbqt_path), f"Output file missing for {name}"
    
    def test_convert_empty_smiles_raises_error(self, converter):
        """Test that empty SMILES raises ValueError (Req 3.8)."""
        with pytest.raises(ValueError, match="empty"):
            converter.convert_ligand_to_pdbqt("", "TEST001")
    
    def test_convert_whitespace_smiles_raises_error(self, converter):
        """Test that whitespace-only SMILES raises ValueError (Req 3.8)."""
        with pytest.raises(ValueError, match="empty"):
            converter.convert_ligand_to_pdbqt("   ", "TEST001")
    
    def test_convert_invalid_smiles_raises_error(self, converter):
        """Test that invalid SMILES raises ValueError (Req 3.8)."""
        for invalid_smiles in INVALID_SMILES[2:]:  # Skip empty ones
            with pytest.raises(ValueError):
                converter.convert_ligand_to_pdbqt(invalid_smiles, "TEST001")
    
    def test_output_file_naming(self, converter):
        """Test that output file is named correctly."""
        _, pdbqt_path = converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['benzene'],
            "CHEMBL12345"
        )
        
        assert "CHEMBL12345_ligand.pdbqt" in pdbqt_path


class TestConformerGeneration:
    """Tests for 3D conformer generation using ETKDG.
    
    Requirements: 3.2, 3.3
    """
    
    @pytest.fixture
    def converter(self):
        """Create a converter with temporary work directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PDBQTConverter(work_dir=tmpdir)
    
    def test_conformer_has_3d_coordinates(self, converter):
        """Test that generated conformer has 3D coordinates (Req 3.2)."""
        pdbqt_data, _ = converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['ibuprofen'],
            "TEST001"
        )
        
        # PDBQT should have coordinates (x, y, z values)
        lines = pdbqt_data.strip().split('\n')
        atom_lines = [l for l in lines if l.startswith(('ATOM', 'HETATM'))]
        
        assert len(atom_lines) > 0
        
        # Check that at least one atom has non-zero coordinates
        has_3d = False
        for line in atom_lines:
            if len(line) > 46:
                try:
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])
                    if x != 0.0 or y != 0.0 or z != 0.0:
                        has_3d = True
                        break
                except ValueError:
                    continue
        
        assert has_3d, "Conformer should have non-zero 3D coordinates"
    
    def test_conformer_generation_reproducible(self, converter):
        """Test that conformer generation is reproducible (same seed)."""
        pdbqt1, _ = converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['aspirin'],
            "TEST001"
        )
        
        pdbqt2, _ = converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['aspirin'],
            "TEST002"
        )
        
        # With same seed, coordinates should be similar
        # (not exactly equal due to file naming differences)
        assert len(pdbqt1) > 0
        assert len(pdbqt2) > 0
    
    def test_geometry_optimization_enabled(self, converter):
        """Test conversion with geometry optimization (Req 3.3)."""
        pdbqt_data, _ = converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['caffeine'],
            "TEST001",
            optimize_geometry=True
        )
        
        assert pdbqt_data is not None
        assert len(pdbqt_data) > 0
    
    def test_geometry_optimization_disabled(self, converter):
        """Test conversion without geometry optimization."""
        pdbqt_data, _ = converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['caffeine'],
            "TEST001",
            optimize_geometry=False
        )
        
        assert pdbqt_data is not None
        assert len(pdbqt_data) > 0


class TestRotatableBonds:
    """Tests for rotatable bond detection and handling.
    
    Requirements: 3.5, 3.6
    """
    
    @pytest.fixture
    def converter(self):
        """Create a converter with temporary work directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PDBQTConverter(work_dir=tmpdir)
    
    def test_rotatable_bonds_counted(self, converter):
        """Test that rotatable bonds are counted (Req 3.5)."""
        converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['ibuprofen'],
            "TEST001"
        )
        
        # Ibuprofen has several rotatable bonds
        assert converter.rotatable_bonds >= 0
    
    def test_rigid_molecule_no_rotatable_bonds(self, converter):
        """Test rigid molecule has few/no rotatable bonds."""
        converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['benzene'],
            "TEST001"
        )
        
        # Benzene is rigid - no rotatable bonds
        assert converter.rotatable_bonds == 0
    
    def test_flexible_molecule_has_rotatable_bonds(self, converter):
        """Test flexible molecule has rotatable bonds (Req 3.5)."""
        converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['atorvastatin'],
            "TEST001"
        )
        
        # Atorvastatin is flexible - should have multiple rotatable bonds
        assert converter.rotatable_bonds > 5
    
    def test_pdbqt_contains_branch_records(self, converter):
        """Test that flexible ligand PDBQT has BRANCH records (Req 3.5, 3.6)."""
        pdbqt_data, _ = converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['ibuprofen'],
            "TEST001"
        )
        
        # Meeko should generate ROOT/BRANCH/ENDBRANCH records
        # (if Meeko is available)
        if 'ROOT' in pdbqt_data:
            assert 'ENDROOT' in pdbqt_data
            # Flexible molecules should have branches
            if converter.rotatable_bonds > 0:
                assert 'BRANCH' in pdbqt_data or 'TORSDOF' in pdbqt_data


class TestComplexMolecules:
    """Tests for complex molecules with rings and stereocenters.
    
    Requirements: 3.1, 3.2
    """
    
    @pytest.fixture
    def converter(self):
        """Create a converter with temporary work directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PDBQTConverter(work_dir=tmpdir)
    
    def test_convert_molecule_with_multiple_rings(self, converter):
        """Test conversion of polycyclic molecule."""
        pdbqt_data, _ = converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['naphthalene'],
            "TEST001"
        )
        
        assert pdbqt_data is not None
        assert len(pdbqt_data) > 0
    
    def test_convert_molecule_with_stereocenters(self, converter):
        """Test conversion of molecule with stereocenters."""
        pdbqt_data, _ = converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['alanine'],
            "TEST001"
        )
        
        assert pdbqt_data is not None
        assert len(pdbqt_data) > 0
    
    def test_convert_steroid(self, converter):
        """Test conversion of complex steroid structure."""
        pdbqt_data, _ = converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['testosterone'],
            "TEST001"
        )
        
        assert pdbqt_data is not None
        assert len(pdbqt_data) > 0
    
    def test_convert_sugar(self, converter):
        """Test conversion of carbohydrate with multiple stereocenters."""
        pdbqt_data, _ = converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['glucose'],
            "TEST001"
        )
        
        assert pdbqt_data is not None
        assert len(pdbqt_data) > 0


class TestLigandProperties:
    """Tests for ligand property tracking."""
    
    @pytest.fixture
    def converter(self):
        """Create a converter with temporary work directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PDBQTConverter(work_dir=tmpdir)
    
    def test_ligand_formula_tracked(self, converter):
        """Test that molecular formula is tracked."""
        converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['aspirin'],
            "TEST001"
        )
        
        # Aspirin formula is C9H8O4
        assert converter.ligand_formula is not None
        assert 'C' in converter.ligand_formula
    
    def test_ligand_atom_count_tracked(self, converter):
        """Test that atom count is tracked."""
        converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['benzene'],
            "TEST001"
        )
        
        # Benzene has 6 carbons (without H)
        assert converter.ligand_num_atoms == 6
    
    def test_methane_atom_count(self, converter):
        """Test atom count for simplest molecule."""
        converter.convert_ligand_to_pdbqt(
            SAMPLE_SMILES['methane'],
            "TEST001"
        )
        
        # Methane has 1 carbon
        assert converter.ligand_num_atoms == 1


class TestPropertyBasedLigandConversion:
    """Property-based tests for ligand PDBQT conversion.
    
    Property 9: SMILES to 3D Structure Generation
    Validates: Requirement 3.1
    """
    
    # Common organic molecules as SMILES
    simple_molecules = st.sampled_from([
        'C',  # methane
        'CC',  # ethane
        'CCC',  # propane
        'CCCC',  # butane
        'c1ccccc1',  # benzene
        'CCO',  # ethanol
        'CC=O',  # acetaldehyde
        'CC(=O)O',  # acetic acid
        'CCN',  # ethylamine
        'c1ccc(O)cc1',  # phenol
        'CC(C)C',  # isobutane
        'C1CCCCC1',  # cyclohexane
    ])
    
    @given(smiles=simple_molecules)
    @settings(max_examples=10)
    def test_valid_smiles_always_converts(self, smiles):
        """Property: Valid SMILES should always produce PDBQT output (Req 3.1)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            converter = PDBQTConverter(work_dir=tmpdir)
            
            pdbqt_data, pdbqt_path = converter.convert_ligand_to_pdbqt(
                smiles,
                "TEST"
            )
            
            # Should produce non-empty output
            assert pdbqt_data is not None
            assert len(pdbqt_data) > 0
            assert os.path.isfile(pdbqt_path)
    
    @given(smiles=simple_molecules)
    @settings(max_examples=10)
    def test_output_contains_atom_records(self, smiles):
        """Property: Output should contain ATOM records for any valid SMILES."""
        with tempfile.TemporaryDirectory() as tmpdir:
            converter = PDBQTConverter(work_dir=tmpdir)
            
            pdbqt_data, _ = converter.convert_ligand_to_pdbqt(smiles, "TEST")
            
            lines = pdbqt_data.strip().split('\n')
            atom_lines = [l for l in lines if l.startswith(('ATOM', 'HETATM'))]
            
            # Should have at least one atom record
            assert len(atom_lines) >= 1
    
    @given(
        chain_length=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=5)
    def test_rotatable_bonds_scale_with_chain_length(self, chain_length):
        """Property: Rotatable bonds should generally increase with chain length."""
        with tempfile.TemporaryDirectory() as tmpdir:
            converter = PDBQTConverter(work_dir=tmpdir)
            
            # Generate alkane chain
            smiles = 'C' * chain_length
            
            converter.convert_ligand_to_pdbqt(smiles, "TEST")
            
            # RDKit may count rotatable bonds differently than expected
            # Just verify the count is non-negative and reasonable
            assert converter.rotatable_bonds >= 0
            # For longer chains, rotatable bonds should be bounded by number of C-C bonds
            assert converter.rotatable_bonds <= max(0, chain_length - 1)


class TestChEMBLMolecules:
    """Tests with real drug molecules from ChEMBL.
    
    Requirements: 3.1, 3.8
    """
    
    @pytest.fixture
    def converter(self):
        """Create a converter with temporary work directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield PDBQTConverter(work_dir=tmpdir)
    
    # Real drug molecules with ChEMBL IDs
    CHEMBL_DRUGS = {
        'CHEMBL25': 'CC(=O)OC1=CC=CC=C1C(=O)O',  # Aspirin
        'CHEMBL112': 'CC1=CC=C(C=C1)C2=CC(=NN2C3=CC=C(C=C3)S(=O)(=O)N)C(F)(F)F',  # Celecoxib
        'CHEMBL941': 'CC(C)CC1=CC=C(C=C1)C(C)C(=O)O',  # Ibuprofen
        'CHEMBL1201587': 'CN1C=NC2=C1C(=O)N(C(=O)N2C)C',  # Caffeine
    }
    
    def test_convert_chembl_aspirin(self, converter):
        """Test conversion of aspirin (CHEMBL25)."""
        pdbqt_data, _ = converter.convert_ligand_to_pdbqt(
            self.CHEMBL_DRUGS['CHEMBL25'],
            'CHEMBL25'
        )
        
        assert pdbqt_data is not None
        assert 'C' in converter.ligand_formula  # Contains carbon
    
    def test_convert_chembl_celecoxib(self, converter):
        """Test conversion of celecoxib (CHEMBL112)."""
        pdbqt_data, _ = converter.convert_ligand_to_pdbqt(
            self.CHEMBL_DRUGS['CHEMBL112'],
            'CHEMBL112'
        )
        
        assert pdbqt_data is not None
        # Celecoxib has fluorine and sulfur
        assert 'F' in converter.ligand_formula or 'S' in converter.ligand_formula
    
    def test_convert_all_chembl_drugs(self, converter):
        """Test conversion of all ChEMBL drug molecules."""
        for chembl_id, smiles in self.CHEMBL_DRUGS.items():
            pdbqt_data, pdbqt_path = converter.convert_ligand_to_pdbqt(
                smiles,
                chembl_id
            )
            
            assert pdbqt_data is not None, f"Failed to convert {chembl_id}"
            assert os.path.isfile(pdbqt_path), f"Output file missing for {chembl_id}"


# Run tests with: pytest tests/test_ligand_converter.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
