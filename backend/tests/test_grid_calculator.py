"""Tests for the grid box calculator module.

Tests cover:
- Grid box calculation from full PDB structure
- Grid box calculation from binding site residues
- Geometric center calculation (Property 14)
- Box size validation (10-50Å range)
- Coordinate extraction from PDB format
- Error handling for invalid inputs
"""

import pytest
from hypothesis import given, strategies as st, settings

from app.docking.grid_calculator import GridBoxCalculator
from app.docking.models import GridBoxParams


# Sample PDB data fixtures
MINIMAL_PDB = """ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00  0.00           C
ATOM      3  C   ALA A   1       2.009   1.420   0.000  1.00  0.00           C
ATOM      4  O   ALA A   1       1.246   2.390   0.000  1.00  0.00           O
END
"""

MULTI_RESIDUE_PDB = """ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00  0.00           C
ATOM      3  C   ALA A   1       2.009   1.420   0.000  1.00  0.00           C
ATOM      4  O   ALA A   1       1.246   2.390   0.000  1.00  0.00           O
ATOM      5  N   GLY A   2       3.300   1.600   0.000  1.00  0.00           N
ATOM      6  CA  GLY A   2       3.900   2.900   0.000  1.00  0.00           C
ATOM      7  C   GLY A   2       5.400   2.800   0.000  1.00  0.00           C
ATOM      8  O   GLY A   2       5.900   1.700   0.000  1.00  0.00           O
ATOM      9  N   SER A   3       6.100   3.900   0.000  1.00  0.00           N
ATOM     10  CA  SER A   3       7.500   4.000   0.000  1.00  0.00           C
ATOM     11  C   SER A   3       8.200   2.700   0.000  1.00  0.00           C
ATOM     12  O   SER A   3       7.600   1.600   0.000  1.00  0.00           O
END
"""

MULTICHAIN_PDB = """ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00  0.00           C
ATOM      3  N   ALA A   2       5.000   5.000   5.000  1.00  0.00           N
ATOM      4  CA  ALA A   2       6.458   5.000   5.000  1.00  0.00           C
ATOM      5  N   ALA B   1      10.000  10.000  10.000  1.00  0.00           N
ATOM      6  CA  ALA B   1      11.458  10.000  10.000  1.00  0.00           C
END
"""

HETATM_PDB = """ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       1.458   0.000   0.000  1.00  0.00           C
HETATM    3 ZN    ZN A 101      10.000  10.000  10.000  1.00  0.00          ZN
END
"""

BINDING_SITE_PDB = """ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       1.000   0.000   0.000  1.00  0.00           C
ATOM      3  N   GLY A   2       5.000   5.000   5.000  1.00  0.00           N
ATOM      4  CA  GLY A   2       6.000   5.000   5.000  1.00  0.00           C
ATOM      5  N   SER A   3      10.000  10.000  10.000  1.00  0.00           N
ATOM      6  CA  SER A   3      11.000  10.000  10.000  1.00  0.00           C
ATOM      7  N   VAL A   4      20.000  20.000  20.000  1.00  0.00           N
ATOM      8  CA  VAL A   4      21.000  20.000  20.000  1.00  0.00           C
END
"""


class TestGridCalculatorInit:
    """Tests for GridBoxCalculator initialization."""
    
    def test_init_creates_instance(self):
        """Test that calculator initializes successfully."""
        calc = GridBoxCalculator()
        assert calc is not None
        assert calc.DEFAULT_BOX_SIZE == 25.0
        assert calc.MIN_BOX_SIZE == 10.0
        assert calc.MAX_BOX_SIZE == 50.0
        assert calc.PADDING == 5.0


class TestCalculateFromPDB:
    """Tests for calculate_from_pdb method."""
    
    def test_calculate_minimal_pdb(self):
        """Test grid calculation with minimal PDB structure."""
        calc = GridBoxCalculator()
        result = calc.calculate_from_pdb(MINIMAL_PDB)
        
        assert isinstance(result, GridBoxParams)
        # Default box size should be 25Å
        assert result.size_x == 25.0
        assert result.size_y == 25.0
        assert result.size_z == 25.0
    
    def test_calculate_returns_gridbox_params(self):
        """Test that result is proper GridBoxParams instance."""
        calc = GridBoxCalculator()
        result = calc.calculate_from_pdb(MULTI_RESIDUE_PDB)
        
        assert isinstance(result, GridBoxParams)
        assert hasattr(result, 'center_x')
        assert hasattr(result, 'center_y')
        assert hasattr(result, 'center_z')
        assert hasattr(result, 'size_x')
        assert hasattr(result, 'size_y')
        assert hasattr(result, 'size_z')
    
    def test_geometric_center_calculation(self):
        """Test Property 14: Geometric center calculation.
        
        For a structure with atoms at known positions, the center
        should be the average of all coordinates.
        """
        # Create PDB with atoms at known positions
        pdb_data = """ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1      10.000   0.000   0.000  1.00  0.00           C
END
"""
        calc = GridBoxCalculator()
        result = calc.calculate_from_pdb(pdb_data)
        
        # Center should be (5.0, 0.0, 0.0)
        assert result.center_x == 5.0
        assert result.center_y == 0.0
        assert result.center_z == 0.0
    
    def test_center_with_all_axes(self):
        """Test center calculation across all three axes."""
        pdb_data = """ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1      10.000  20.000  30.000  1.00  0.00           C
END
"""
        calc = GridBoxCalculator()
        result = calc.calculate_from_pdb(pdb_data)
        
        assert result.center_x == 5.0
        assert result.center_y == 10.0
        assert result.center_z == 15.0
    
    def test_custom_box_size(self):
        """Test grid calculation with custom box dimensions."""
        calc = GridBoxCalculator()
        result = calc.calculate_from_pdb(MINIMAL_PDB, box_size=(30.0, 35.0, 40.0))
        
        assert result.size_x == 30.0
        assert result.size_y == 35.0
        assert result.size_z == 40.0
    
    def test_box_size_validation_min(self):
        """Test that box size is clamped to minimum (10Å)."""
        calc = GridBoxCalculator()
        result = calc.calculate_from_pdb(MINIMAL_PDB, box_size=(5.0, 5.0, 5.0))
        
        assert result.size_x == 10.0
        assert result.size_y == 10.0
        assert result.size_z == 10.0
    
    def test_box_size_validation_max(self):
        """Test that box size is clamped to maximum (50Å)."""
        calc = GridBoxCalculator()
        result = calc.calculate_from_pdb(MINIMAL_PDB, box_size=(100.0, 100.0, 100.0))
        
        assert result.size_x == 50.0
        assert result.size_y == 50.0
        assert result.size_z == 50.0
    
    def test_results_rounded_to_two_decimals(self):
        """Test that center coordinates are rounded to 2 decimal places."""
        pdb_data = """ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       1.111   2.222   3.333  1.00  0.00           C
ATOM      3  C   ALA A   1       2.222   4.444   6.666  1.00  0.00           C
END
"""
        calc = GridBoxCalculator()
        result = calc.calculate_from_pdb(pdb_data)
        
        # Check rounding (center should be average)
        assert result.center_x == 1.11  # (0+1.111+2.222)/3 = 1.111
        assert result.center_y == 2.22  # (0+2.222+4.444)/3 = 2.222
        assert result.center_z == 3.33  # (0+3.333+6.666)/3 = 3.333
    
    def test_hetatm_included_in_center(self):
        """Test that HETATM records are included in center calculation."""
        calc = GridBoxCalculator()
        result = calc.calculate_from_pdb(HETATM_PDB)
        
        # HETATM (zinc) at (10, 10, 10) should be included
        # 3 atoms: (0,0,0), (1.458,0,0), (10,10,10)
        # Center should shift toward the zinc
        assert result.center_x > 0.5  # Would be lower without HETATM


class TestCalculateFromBindingSite:
    """Tests for calculate_from_binding_site method."""
    
    def test_binding_site_center(self):
        """Test center calculation for specific binding site residues."""
        calc = GridBoxCalculator()
        # Select residues 1 and 2 only (at positions near origin and 5,5,5)
        result = calc.calculate_from_binding_site(BINDING_SITE_PDB, [1, 2], 'A')
        
        # Center should be between residues 1 and 2
        # Residue 1: (0,0,0) and (1,0,0)
        # Residue 2: (5,5,5) and (6,5,5)
        # Center should be approximately (3.0, 2.5, 2.5)
        assert result.center_x == 3.0
        assert result.center_y == 2.5
        assert result.center_z == 2.5
    
    def test_binding_site_box_size_auto(self):
        """Test that box size is calculated from binding site extent."""
        calc = GridBoxCalculator()
        result = calc.calculate_from_binding_site(BINDING_SITE_PDB, [1, 2, 3], 'A')
        
        # Box should encompass residues 1-3 with padding
        # Size should be larger than default if site is spread out
        assert isinstance(result.size_x, float)
        assert isinstance(result.size_y, float)
        assert isinstance(result.size_z, float)
    
    def test_binding_site_fallback_to_whole_protein(self):
        """Test fallback when no binding site residues found."""
        calc = GridBoxCalculator()
        # Request non-existent residues
        result = calc.calculate_from_binding_site(MINIMAL_PDB, [99, 100], 'A')
        
        # Should fall back to whole protein calculation
        assert isinstance(result, GridBoxParams)
    
    def test_binding_site_chain_selection(self):
        """Test that chain filter works correctly."""
        calc = GridBoxCalculator()
        # Chain A only
        result_a = calc.calculate_from_binding_site(MULTICHAIN_PDB, [1, 2], 'A')
        # Chain B only (residue 1)
        result_b = calc.calculate_from_binding_site(MULTICHAIN_PDB, [1], 'B')
        
        # Centers should be different due to different chain positions
        assert result_a.center_x != result_b.center_x
        assert result_a.center_y != result_b.center_y


class TestCoordinateExtraction:
    """Tests for coordinate extraction from PDB format."""
    
    def test_extract_atom_coordinates(self):
        """Test extraction of ATOM record coordinates."""
        calc = GridBoxCalculator()
        coords = calc._extract_coordinates(MINIMAL_PDB)
        
        assert len(coords) == 4
        assert coords[0] == (0.0, 0.0, 0.0)  # First atom
    
    def test_extract_hetatm_coordinates(self):
        """Test extraction of HETATM record coordinates."""
        calc = GridBoxCalculator()
        coords = calc._extract_coordinates(HETATM_PDB)
        
        # Should include both ATOM and HETATM
        assert len(coords) == 3
        assert (10.0, 10.0, 10.0) in coords  # Zinc position
    
    def test_extract_handles_malformed_lines(self):
        """Test that malformed lines are skipped gracefully."""
        pdb_with_malformed = """ATOM      1  N   ALA A   1       0.000   0.000   0.000  1.00  0.00           N
ATOM      2  CA  ALA A   1       BAD_DATA_HERE
ATOM      3  C   ALA A   1       2.000   2.000   2.000  1.00  0.00           C
END
"""
        calc = GridBoxCalculator()
        coords = calc._extract_coordinates(pdb_with_malformed)
        
        # Should only get 2 valid atoms
        assert len(coords) == 2


class TestErrorHandling:
    """Tests for error handling."""
    
    def test_empty_pdb_raises_error(self):
        """Test that empty PDB data raises ValueError."""
        calc = GridBoxCalculator()
        
        with pytest.raises(ValueError, match="No atom coordinates found"):
            calc.calculate_from_pdb("")
    
    def test_whitespace_only_raises_error(self):
        """Test that whitespace-only PDB raises ValueError."""
        calc = GridBoxCalculator()
        
        with pytest.raises(ValueError, match="No atom coordinates found"):
            calc.calculate_from_pdb("   \n\n   ")
    
    def test_no_atoms_raises_error(self):
        """Test that PDB with no ATOM/HETATM records raises error."""
        pdb_no_atoms = """HEADER    PROTEIN
REMARK   This has no atoms
END
"""
        calc = GridBoxCalculator()
        
        with pytest.raises(ValueError, match="No atom coordinates found"):
            calc.calculate_from_pdb(pdb_no_atoms)


class TestPrivateMethods:
    """Tests for private helper methods."""
    
    def test_calculate_center_empty_list(self):
        """Test center calculation with empty coordinate list."""
        calc = GridBoxCalculator()
        center = calc._calculate_center([])
        
        assert center == (0.0, 0.0, 0.0)
    
    def test_calculate_center_single_point(self):
        """Test center calculation with single coordinate."""
        calc = GridBoxCalculator()
        center = calc._calculate_center([(5.0, 10.0, 15.0)])
        
        assert center == (5.0, 10.0, 15.0)
    
    def test_calculate_box_size_empty_list(self):
        """Test box size calculation with empty list returns defaults."""
        calc = GridBoxCalculator()
        size = calc._calculate_box_size([])
        
        assert size == (25.0, 25.0, 25.0)
    
    def test_calculate_box_size_with_padding(self):
        """Test that box size includes padding."""
        calc = GridBoxCalculator()
        # Atoms at (0,0,0) and (10,10,10) - extent is 10Å each axis
        coords = [(0.0, 0.0, 0.0), (10.0, 10.0, 10.0)]
        size = calc._calculate_box_size(coords)
        
        # Size should be extent (10) + 2*padding (10) = 20Å
        assert size == (20.0, 20.0, 20.0)
    
    def test_box_size_clamped_to_min(self):
        """Test box size is clamped to minimum."""
        calc = GridBoxCalculator()
        # Very small extent (1Å) + padding (5*2 = 10Å) = 11Å
        # But if extent is 0 (same point), size would be 0 + 10 padding = 10
        coords = [(0.0, 0.0, 0.0), (0.0, 0.0, 0.0)]  # Same point
        size = calc._calculate_box_size(coords)
        
        # Extent (0) + 2*padding (10) = 10, which equals MIN_BOX_SIZE
        assert size == (10.0, 10.0, 10.0)
    
    def test_box_size_clamped_to_max(self):
        """Test box size is clamped to maximum."""
        calc = GridBoxCalculator()
        # Very large extent
        coords = [(0.0, 0.0, 0.0), (100.0, 100.0, 100.0)]
        size = calc._calculate_box_size(coords)
        
        # Should be clamped to MAX_BOX_SIZE (50)
        assert size == (50.0, 50.0, 50.0)


class TestPropertyBasedCalculations:
    """Property-based tests using Hypothesis."""
    
    @given(
        x1=st.floats(min_value=0, max_value=50, allow_nan=False, allow_infinity=False),
        y1=st.floats(min_value=0, max_value=50, allow_nan=False, allow_infinity=False),
        z1=st.floats(min_value=0, max_value=50, allow_nan=False, allow_infinity=False),
        x2=st.floats(min_value=0, max_value=50, allow_nan=False, allow_infinity=False),
        y2=st.floats(min_value=0, max_value=50, allow_nan=False, allow_infinity=False),
        z2=st.floats(min_value=0, max_value=50, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_center_always_between_atoms(self, x1, y1, z1, x2, y2, z2):
        """Property: Center is always between min and max coordinates.
        
        Uses positive coordinates only to avoid PDB format parsing issues
        with negative signs in fixed-width columns.
        """
        # Round to 2 decimal places and ensure different values for meaningful test
        x1, y1, z1 = round(x1, 2), round(y1, 2), round(z1, 2)
        x2, y2, z2 = round(x2, 2), round(y2, 2), round(z2, 2)
        
        # PDB format has fixed-width columns, format coordinates properly
        pdb_data = f"""ATOM      1  N   ALA A   1    {x1:8.3f}{y1:8.3f}{z1:8.3f}  1.00  0.00           N
ATOM      2  CA  ALA A   1    {x2:8.3f}{y2:8.3f}{z2:8.3f}  1.00  0.00           C
END
"""
        calc = GridBoxCalculator()
        result = calc.calculate_from_pdb(pdb_data)
        
        # Center should be within bounds (with small tolerance for rounding)
        min_x, max_x = min(x1, x2), max(x1, x2)
        min_y, max_y = min(y1, y2), max(y1, y2)
        min_z, max_z = min(z1, z2), max(z1, z2)
        
        assert min_x - 0.1 <= result.center_x <= max_x + 0.1
        assert min_y - 0.1 <= result.center_y <= max_y + 0.1
        assert min_z - 0.1 <= result.center_z <= max_z + 0.1
    
    @given(
        size_x=st.floats(min_value=1, max_value=100, allow_nan=False, allow_infinity=False),
        size_y=st.floats(min_value=1, max_value=100, allow_nan=False, allow_infinity=False),
        size_z=st.floats(min_value=1, max_value=100, allow_nan=False, allow_infinity=False),
    )
    @settings(max_examples=50)
    def test_box_size_always_within_valid_range(self, size_x, size_y, size_z):
        """Property: Box size is always within 10-50Å range."""
        calc = GridBoxCalculator()
        result = calc.calculate_from_pdb(MINIMAL_PDB, box_size=(size_x, size_y, size_z))
        
        assert 10.0 <= result.size_x <= 50.0
        assert 10.0 <= result.size_y <= 50.0
        assert 10.0 <= result.size_z <= 50.0


class TestRealWorldScenarios:
    """Tests with realistic PDB structures."""
    
    def test_large_protein_structure(self):
        """Test with larger protein structure."""
        # Generate a 100-atom protein-like structure
        lines = ["HEADER    TEST PROTEIN"]
        for i in range(100):
            x = (i % 10) * 3.8  # Pseudo-helical arrangement
            y = (i // 10) * 3.5
            z = i * 0.15
            lines.append(f"ATOM  {i+1:5d}  CA  ALA A{i+1:4d}    {x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00           C")
        lines.append("END")
        pdb_data = "\n".join(lines)
        
        calc = GridBoxCalculator()
        result = calc.calculate_from_pdb(pdb_data)
        
        assert isinstance(result, GridBoxParams)
        assert result.size_x == 25.0  # Default box size
    
    def test_negative_coordinates(self):
        """Test PDB with negative coordinates (common in real structures)."""
        pdb_data = """ATOM      1  N   ALA A   1     -10.000 -20.000 -30.000  1.00  0.00           N
ATOM      2  CA  ALA A   1      10.000  20.000  30.000  1.00  0.00           C
END
"""
        calc = GridBoxCalculator()
        result = calc.calculate_from_pdb(pdb_data)
        
        # Center should be at origin
        assert result.center_x == 0.0
        assert result.center_y == 0.0
        assert result.center_z == 0.0
