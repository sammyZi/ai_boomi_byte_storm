"""Unit tests for RDKit analyzer.

This module contains unit tests for validating specific examples,
edge cases, and error handling in the RDKit molecular analysis functionality.
"""

import pytest
from rdkit import Chem
from app.rdkit_analyzer import RDKitAnalyzer


class TestRDKitAnalyzerSMILESParsing:
    """Unit tests for SMILES parsing functionality."""
    
    def test_parse_valid_smiles_aspirin(self):
        """Test parsing aspirin SMILES."""
        analyzer = RDKitAnalyzer()
        
        aspirin_smiles = "CC(=O)Oc1ccccc1C(=O)O"
        mol = analyzer.parse_smiles(aspirin_smiles)
        
        assert mol is not None
        # RDKit counts heavy atoms (non-hydrogen) by default
        assert mol.GetNumAtoms() == 13  # 13 heavy atoms in aspirin
    
    def test_parse_valid_smiles_caffeine(self):
        """Test parsing caffeine SMILES."""
        analyzer = RDKitAnalyzer()
        
        caffeine_smiles = "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"
        mol = analyzer.parse_smiles(caffeine_smiles)
        
        assert mol is not None
        # RDKit counts heavy atoms (non-hydrogen) by default
        assert mol.GetNumAtoms() == 14  # 14 heavy atoms in caffeine
    
    def test_parse_invalid_smiles_empty_string(self):
        """Test that empty SMILES string returns None."""
        analyzer = RDKitAnalyzer()
        
        mol = analyzer.parse_smiles("")
        assert mol is None
    
    def test_parse_invalid_smiles_whitespace(self):
        """Test that whitespace-only SMILES returns None."""
        analyzer = RDKitAnalyzer()
        
        mol = analyzer.parse_smiles("   ")
        assert mol is None
    
    def test_parse_invalid_smiles_syntax_error(self):
        """Test that syntactically invalid SMILES returns None."""
        analyzer = RDKitAnalyzer()
        
        invalid_smiles = [
            "C(",  # Unmatched parenthesis
            "C[",  # Unmatched bracket
            "X",   # Invalid atom
            "C==C",  # Invalid bond
        ]
        
        for smiles in invalid_smiles:
            mol = analyzer.parse_smiles(smiles)
            assert mol is None, f"Should reject invalid SMILES: {smiles}"
    
    def test_parse_smiles_too_large(self):
        """Test that molecules with >200 atoms are rejected."""
        analyzer = RDKitAnalyzer()
        
        # Create a large carbon chain (250 atoms)
        large_smiles = "C" * 250
        mol = analyzer.parse_smiles(large_smiles)
        
        assert mol is None, "Should reject molecules with >200 atoms"
    
    def test_get_canonical_smiles(self):
        """Test canonical SMILES generation."""
        analyzer = RDKitAnalyzer()
        
        # Different representations of the same molecule
        smiles_variants = [
            "CCO",  # Ethanol
            "OCC",  # Ethanol (different order)
        ]
        
        canonical_forms = []
        for smiles in smiles_variants:
            mol = analyzer.parse_smiles(smiles)
            assert mol is not None
            canonical = analyzer.get_canonical_smiles(mol)
            canonical_forms.append(canonical)
        
        # All should produce the same canonical form
        assert len(set(canonical_forms)) == 1, "Canonical forms should be identical"


class TestRDKitAnalyzerMolecularProperties:
    """Unit tests for molecular property calculations."""
    
    def test_calculate_properties_aspirin(self):
        """Test property calculation for aspirin."""
        analyzer = RDKitAnalyzer()
        
        aspirin = analyzer.parse_smiles("CC(=O)Oc1ccccc1C(=O)O")
        assert aspirin is not None
        
        props = analyzer.calculate_properties(aspirin)
        
        # Check known properties
        assert 175 < props.molecular_weight < 185
        assert 0.5 < props.logp < 2.0
        assert props.hbd == 1
        assert props.hba >= 3
        assert props.aromatic_rings == 1
        assert props.lipinski_violations == 0
        assert props.drug_likeness_score == 1.0
    
    def test_calculate_properties_caffeine(self):
        """Test property calculation for caffeine."""
        analyzer = RDKitAnalyzer()
        
        caffeine = analyzer.parse_smiles("CN1C=NC2=C1C(=O)N(C(=O)N2C)C")
        assert caffeine is not None
        
        props = analyzer.calculate_properties(caffeine)
        
        # Check known properties
        assert 190 < props.molecular_weight < 200
        assert props.hbd == 0  # No H-bond donors
        assert props.hba >= 3  # Multiple N and O atoms
        assert props.lipinski_violations == 0
        assert props.drug_likeness_score == 1.0
    
    def test_calculate_properties_simple_molecules(self):
        """Test property calculation for simple molecules."""
        analyzer = RDKitAnalyzer()
        
        # Methane
        methane = analyzer.parse_smiles("C")
        assert methane is not None
        props = analyzer.calculate_properties(methane)
        
        assert 15 < props.molecular_weight < 17
        assert props.hbd == 0
        assert props.hba == 0
        assert props.aromatic_rings == 0
        assert props.rotatable_bonds == 0
        
        # Ethanol
        ethanol = analyzer.parse_smiles("CCO")
        assert ethanol is not None
        props = analyzer.calculate_properties(ethanol)
        
        assert 45 < props.molecular_weight < 47
        assert props.hbd == 1
        assert props.hba == 1
        assert props.aromatic_rings == 0


class TestRDKitAnalyzerToxicityAssessment:
    """Unit tests for toxicity assessment functionality."""
    
    def test_assess_toxicity_clean_molecule(self):
        """Test toxicity assessment for clean molecules."""
        analyzer = RDKitAnalyzer()
        
        # Aspirin should have no toxicophores
        aspirin = analyzer.parse_smiles("CC(=O)Oc1ccccc1C(=O)O")
        assert aspirin is not None
        
        toxicity = analyzer.assess_toxicity(aspirin)
        
        assert len(toxicity.detected_toxicophores) == 0
        assert toxicity.toxicity_score == 0.0
        assert toxicity.risk_level == "low"
        assert len(toxicity.warnings) == 0
    
    def test_assess_toxicity_acyl_chloride(self):
        """Test toxicity assessment for acyl chloride."""
        analyzer = RDKitAnalyzer()
        
        # Acyl chloride: CC(=O)Cl
        acyl_chloride = analyzer.parse_smiles("CC(=O)Cl")
        assert acyl_chloride is not None
        
        toxicity = analyzer.assess_toxicity(acyl_chloride)
        
        assert "acyl_chloride" in toxicity.detected_toxicophores
        assert toxicity.toxicity_score == 0.15
        assert toxicity.risk_level == "low"
        assert len(toxicity.warnings) > 0
    
    def test_assess_toxicity_epoxide(self):
        """Test toxicity assessment for epoxide."""
        analyzer = RDKitAnalyzer()
        
        # Epoxide: C1OC1
        epoxide = analyzer.parse_smiles("C1OC1")
        assert epoxide is not None
        
        toxicity = analyzer.assess_toxicity(epoxide)
        
        assert "epoxide" in toxicity.detected_toxicophores
        assert toxicity.toxicity_score == 0.15
        assert toxicity.risk_level == "low"
    
    def test_assess_toxicity_hydrazine(self):
        """Test toxicity assessment for hydrazine."""
        analyzer = RDKitAnalyzer()
        
        # Hydrazine: NN
        hydrazine = analyzer.parse_smiles("NN")
        assert hydrazine is not None
        
        toxicity = analyzer.assess_toxicity(hydrazine)
        
        assert "hydrazine" in toxicity.detected_toxicophores
        assert toxicity.toxicity_score == 0.15
        assert toxicity.risk_level == "low"
    
    def test_assess_toxicity_peroxide(self):
        """Test toxicity assessment for peroxide."""
        analyzer = RDKitAnalyzer()
        
        # Peroxide: OO
        peroxide = analyzer.parse_smiles("OO")
        assert peroxide is not None
        
        toxicity = analyzer.assess_toxicity(peroxide)
        
        assert "peroxide" in toxicity.detected_toxicophores
        assert toxicity.toxicity_score == 0.15
        assert toxicity.risk_level == "low"


class TestRDKitAnalyzer2DStructureGeneration:
    """Unit tests for 2D structure generation."""
    
    def test_generate_2d_structure_aspirin(self):
        """Test 2D structure generation for aspirin."""
        analyzer = RDKitAnalyzer()
        
        aspirin = analyzer.parse_smiles("CC(=O)Oc1ccccc1C(=O)O")
        assert aspirin is not None
        
        svg = analyzer.generate_2d_structure(aspirin)
        
        # Should return SVG string
        assert isinstance(svg, str)
        assert len(svg) > 0
        assert "<svg" in svg.lower()
    
    def test_generate_2d_structure_simple_molecule(self):
        """Test 2D structure generation for simple molecule."""
        analyzer = RDKitAnalyzer()
        
        ethanol = analyzer.parse_smiles("CCO")
        assert ethanol is not None
        
        svg = analyzer.generate_2d_structure(ethanol)
        
        # Should return SVG string
        assert isinstance(svg, str)
        assert len(svg) > 0
        assert "<svg" in svg.lower()
    
    def test_generate_2d_structure_custom_size(self):
        """Test 2D structure generation with custom size."""
        analyzer = RDKitAnalyzer()
        
        benzene = analyzer.parse_smiles("c1ccccc1")
        assert benzene is not None
        
        # Generate with custom size
        svg = analyzer.generate_2d_structure(benzene, width=400, height=400)
        
        # Should return SVG string
        assert isinstance(svg, str)
        assert len(svg) > 0
        assert "<svg" in svg.lower()


class TestRDKitAnalyzerIntegration:
    """Integration tests for complete analysis workflow."""
    
    def test_complete_analysis_workflow_aspirin(self):
        """Test complete analysis workflow for aspirin."""
        analyzer = RDKitAnalyzer()
        
        smiles = "CC(=O)Oc1ccccc1C(=O)O"
        
        # Parse
        mol = analyzer.parse_smiles(smiles)
        assert mol is not None
        
        # Get canonical SMILES
        canonical = analyzer.get_canonical_smiles(mol)
        assert canonical is not None
        
        # Calculate properties
        props = analyzer.calculate_properties(mol)
        assert props.drug_likeness_score == 1.0
        
        # Assess toxicity
        toxicity = analyzer.assess_toxicity(mol)
        assert toxicity.risk_level == "low"
        
        # Generate 2D structure
        svg = analyzer.generate_2d_structure(mol)
        assert "<svg" in svg.lower()
    
    def test_complete_analysis_workflow_toxic_molecule(self):
        """Test complete analysis workflow for molecule with toxicophore."""
        analyzer = RDKitAnalyzer()
        
        smiles = "CC(=O)Cl"  # Acyl chloride
        
        # Parse
        mol = analyzer.parse_smiles(smiles)
        assert mol is not None
        
        # Calculate properties
        props = analyzer.calculate_properties(mol)
        assert props.molecular_weight > 0
        
        # Assess toxicity
        toxicity = analyzer.assess_toxicity(mol)
        assert len(toxicity.detected_toxicophores) > 0
        assert toxicity.toxicity_score > 0
        
        # Generate 2D structure
        svg = analyzer.generate_2d_structure(mol)
        assert "<svg" in svg.lower()
