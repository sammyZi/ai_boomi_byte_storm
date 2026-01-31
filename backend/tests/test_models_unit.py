"""Unit tests for data models.

This module contains unit tests for validating specific examples,
edge cases, and field constraints in the data models.
"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from app.models import (
    Target,
    ProteinStructure,
    Molecule,
    MolecularProperties,
    ToxicityAssessment,
    DrugCandidate,
    DiscoveryResult,
    DiscoveryRequest,
    DiscoveryResponse,
    ErrorResponse,
)


class TestTarget:
    """Unit tests for Target model."""
    
    def test_valid_target(self):
        """Test creating a valid Target instance."""
        target = Target(
            uniprot_id="P12345",
            gene_symbol="APOE",
            protein_name="Apolipoprotein E",
            confidence_score=0.85,
            disease_association="Alzheimer's disease risk factor"
        )
        
        assert target.uniprot_id == "P12345"
        assert target.gene_symbol == "APOE"
        assert target.confidence_score == 0.85
    
    def test_confidence_score_minimum_boundary(self):
        """Test confidence score at minimum boundary (0.5)."""
        target = Target(
            uniprot_id="P12345",
            gene_symbol="APOE",
            protein_name="Apolipoprotein E",
            confidence_score=0.5,
            disease_association="Test"
        )
        assert target.confidence_score == 0.5
    
    def test_confidence_score_maximum_boundary(self):
        """Test confidence score at maximum boundary (1.0)."""
        target = Target(
            uniprot_id="P12345",
            gene_symbol="APOE",
            protein_name="Apolipoprotein E",
            confidence_score=1.0,
            disease_association="Test"
        )
        assert target.confidence_score == 1.0
    
    def test_confidence_score_below_minimum(self):
        """Test that confidence score below 0.5 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Target(
                uniprot_id="P12345",
                gene_symbol="APOE",
                protein_name="Apolipoprotein E",
                confidence_score=0.4,
                disease_association="Test"
            )
        assert "greater than or equal to 0.5" in str(exc_info.value)
    
    def test_confidence_score_above_maximum(self):
        """Test that confidence score above 1.0 is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Target(
                uniprot_id="P12345",
                gene_symbol="APOE",
                protein_name="Apolipoprotein E",
                confidence_score=1.1,
                disease_association="Test"
            )
        assert "less than or equal to 1" in str(exc_info.value)


class TestProteinStructure:
    """Unit tests for ProteinStructure model."""
    
    def test_valid_protein_structure(self):
        """Test creating a valid ProteinStructure instance."""
        structure = ProteinStructure(
            uniprot_id="P12345",
            pdb_data="ATOM      1  N   MET A   1...",
            plddt_score=85.5,
            is_low_confidence=False
        )
        
        assert structure.uniprot_id == "P12345"
        assert structure.plddt_score == 85.5
        assert structure.is_low_confidence is False
    
    def test_low_confidence_structure(self):
        """Test structure with low confidence (pLDDT < 70)."""
        structure = ProteinStructure(
            uniprot_id="P12345",
            pdb_data="ATOM      1  N   MET A   1...",
            plddt_score=65.0,
            is_low_confidence=True
        )
        
        assert structure.plddt_score == 65.0
        assert structure.is_low_confidence is True
    
    def test_plddt_score_boundaries(self):
        """Test pLDDT score at boundaries (0 and 100)."""
        # Minimum
        structure_min = ProteinStructure(
            uniprot_id="P12345",
            pdb_data="ATOM      1  N   MET A   1...",
            plddt_score=0.0,
            is_low_confidence=True
        )
        assert structure_min.plddt_score == 0.0
        
        # Maximum
        structure_max = ProteinStructure(
            uniprot_id="P12345",
            pdb_data="ATOM      1  N   MET A   1...",
            plddt_score=100.0,
            is_low_confidence=False
        )
        assert structure_max.plddt_score == 100.0
    
    def test_plddt_score_out_of_range(self):
        """Test that pLDDT score outside 0-100 is rejected."""
        with pytest.raises(ValidationError):
            ProteinStructure(
                uniprot_id="P12345",
                pdb_data="ATOM      1  N   MET A   1...",
                plddt_score=101.0,
                is_low_confidence=False
            )


class TestMolecule:
    """Unit tests for Molecule model."""
    
    def test_valid_molecule(self):
        """Test creating a valid Molecule instance."""
        molecule = Molecule(
            chembl_id="CHEMBL25",
            name="Aspirin",
            smiles="CC(=O)Oc1ccccc1C(=O)O",
            canonical_smiles="CC(=O)Oc1ccccc1C(=O)O",
            pchembl_value=6.5,
            activity_type="IC50",
            target_ids=["P12345", "P67890"]
        )
        
        assert molecule.chembl_id == "CHEMBL25"
        assert molecule.name == "Aspirin"
        assert len(molecule.target_ids) == 2
    
    def test_empty_smiles_rejected(self):
        """Test that empty SMILES strings are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Molecule(
                chembl_id="CHEMBL25",
                name="Test",
                smiles="",
                canonical_smiles="CC",
                pchembl_value=6.5,
                activity_type="IC50"
            )
        assert "SMILES string cannot be empty" in str(exc_info.value)
    
    def test_whitespace_smiles_rejected(self):
        """Test that whitespace-only SMILES strings are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Molecule(
                chembl_id="CHEMBL25",
                name="Test",
                smiles="   ",
                canonical_smiles="CC",
                pchembl_value=6.5,
                activity_type="IC50"
            )
        assert "SMILES string cannot be empty" in str(exc_info.value)
    
    def test_molecule_with_no_targets(self):
        """Test molecule with empty target list."""
        molecule = Molecule(
            chembl_id="CHEMBL25",
            name="Test",
            smiles="CC",
            canonical_smiles="CC",
            pchembl_value=6.5,
            activity_type="IC50",
            target_ids=[]
        )
        assert molecule.target_ids == []
    
    def test_pchembl_value_boundaries(self):
        """Test pChEMBL value at boundary (0.0)."""
        molecule = Molecule(
            chembl_id="CHEMBL25",
            name="Test",
            smiles="CC",
            canonical_smiles="CC",
            pchembl_value=0.0,
            activity_type="IC50"
        )
        assert molecule.pchembl_value == 0.0


class TestMolecularProperties:
    """Unit tests for MolecularProperties model."""
    
    def test_valid_molecular_properties(self):
        """Test creating valid MolecularProperties instance."""
        props = MolecularProperties(
            molecular_weight=180.16,
            logp=1.19,
            hbd=1,
            hba=3,
            tpsa=63.6,
            rotatable_bonds=3,
            aromatic_rings=1,
            lipinski_violations=0,
            drug_likeness_score=1.0
        )
        
        assert props.molecular_weight == 180.16
        assert props.lipinski_violations == 0
        assert props.drug_likeness_score == 1.0
    
    def test_lipinski_violations_boundaries(self):
        """Test Lipinski violations at boundaries (0-4)."""
        # Zero violations
        props_zero = MolecularProperties(
            molecular_weight=180.16,
            logp=1.19,
            hbd=1,
            hba=3,
            tpsa=63.6,
            rotatable_bonds=3,
            aromatic_rings=1,
            lipinski_violations=0,
            drug_likeness_score=1.0
        )
        assert props_zero.lipinski_violations == 0
        
        # Four violations
        props_four = MolecularProperties(
            molecular_weight=600.0,
            logp=6.0,
            hbd=6,
            hba=12,
            tpsa=150.0,
            rotatable_bonds=10,
            aromatic_rings=3,
            lipinski_violations=4,
            drug_likeness_score=0.0
        )
        assert props_four.lipinski_violations == 4
    
    def test_drug_likeness_score_boundaries(self):
        """Test drug-likeness score at boundaries (0.0-1.0)."""
        props = MolecularProperties(
            molecular_weight=180.16,
            logp=1.19,
            hbd=1,
            hba=3,
            tpsa=63.6,
            rotatable_bonds=3,
            aromatic_rings=1,
            lipinski_violations=2,
            drug_likeness_score=0.5
        )
        assert 0.0 <= props.drug_likeness_score <= 1.0
    
    def test_negative_values_rejected(self):
        """Test that negative values are rejected for non-negative fields."""
        with pytest.raises(ValidationError):
            MolecularProperties(
                molecular_weight=-10.0,  # Invalid
                logp=1.19,
                hbd=1,
                hba=3,
                tpsa=63.6,
                rotatable_bonds=3,
                aromatic_rings=1,
                lipinski_violations=0,
                drug_likeness_score=1.0
            )


class TestToxicityAssessment:
    """Unit tests for ToxicityAssessment model."""
    
    def test_valid_toxicity_assessment_low_risk(self):
        """Test creating valid ToxicityAssessment with low risk."""
        toxicity = ToxicityAssessment(
            toxicity_score=0.15,
            risk_level="low",
            detected_toxicophores=["nitro_group"],
            warnings=["Contains nitro group"]
        )
        
        assert toxicity.toxicity_score == 0.15
        assert toxicity.risk_level == "low"
        assert len(toxicity.detected_toxicophores) == 1
    
    def test_valid_toxicity_assessment_medium_risk(self):
        """Test creating valid ToxicityAssessment with medium risk."""
        toxicity = ToxicityAssessment(
            toxicity_score=0.45,
            risk_level="medium",
            detected_toxicophores=["nitro_group", "azide", "epoxide"],
            warnings=["Multiple toxicophores detected"]
        )
        
        assert toxicity.risk_level == "medium"
        assert len(toxicity.detected_toxicophores) == 3
    
    def test_valid_toxicity_assessment_high_risk(self):
        """Test creating valid ToxicityAssessment with high risk."""
        toxicity = ToxicityAssessment(
            toxicity_score=0.75,
            risk_level="high",
            detected_toxicophores=["nitro_group", "azide", "epoxide", "peroxide", "hydrazine"],
            warnings=["High toxicity risk - multiple alerts"]
        )
        
        assert toxicity.risk_level == "high"
        assert toxicity.toxicity_score > 0.6
    
    def test_invalid_risk_level_rejected(self):
        """Test that invalid risk levels are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ToxicityAssessment(
                toxicity_score=0.15,
                risk_level="very_low",  # Invalid
                detected_toxicophores=[],
                warnings=[]
            )
        assert "Risk level must be one of" in str(exc_info.value)
    
    def test_toxicity_score_boundaries(self):
        """Test toxicity score at boundaries (0.0-1.0)."""
        # Minimum
        toxicity_min = ToxicityAssessment(
            toxicity_score=0.0,
            risk_level="low",
            detected_toxicophores=[],
            warnings=[]
        )
        assert toxicity_min.toxicity_score == 0.0
        
        # Maximum
        toxicity_max = ToxicityAssessment(
            toxicity_score=1.0,
            risk_level="high",
            detected_toxicophores=["multiple"],
            warnings=["Maximum toxicity"]
        )
        assert toxicity_max.toxicity_score == 1.0


class TestDiscoveryRequest:
    """Unit tests for DiscoveryRequest model."""
    
    def test_valid_discovery_request(self):
        """Test creating a valid DiscoveryRequest."""
        request = DiscoveryRequest(disease_name="Alzheimer's disease")
        assert request.disease_name == "Alzheimer's disease"
    
    def test_disease_name_minimum_length(self):
        """Test disease name at minimum length (2 characters)."""
        request = DiscoveryRequest(disease_name="AD")
        assert len(request.disease_name) == 2
    
    def test_disease_name_too_short(self):
        """Test that disease name shorter than 2 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DiscoveryRequest(disease_name="A")
        assert "at least 2 characters" in str(exc_info.value)
    
    def test_disease_name_maximum_length(self):
        """Test disease name at maximum length (200 characters)."""
        long_name = "A" * 200
        request = DiscoveryRequest(disease_name=long_name)
        assert len(request.disease_name) == 200
    
    def test_disease_name_too_long(self):
        """Test that disease name longer than 200 characters is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            DiscoveryRequest(disease_name="A" * 201)
        assert "at most 200 characters" in str(exc_info.value)


class TestDiscoveryResult:
    """Unit tests for DiscoveryResult model."""
    
    def test_valid_discovery_result_empty(self):
        """Test creating a valid DiscoveryResult with no candidates."""
        result = DiscoveryResult(
            query="Test disease",
            processing_time_seconds=5.5,
            candidates=[],
            targets_found=0,
            molecules_analyzed=0
        )
        
        assert result.query == "Test disease"
        assert result.processing_time_seconds == 5.5
        assert len(result.candidates) == 0
        assert result.api_version == "0.1.0"
    
    def test_discovery_result_with_warnings(self):
        """Test DiscoveryResult with warnings."""
        result = DiscoveryResult(
            query="Test disease",
            processing_time_seconds=5.5,
            candidates=[],
            targets_found=5,
            molecules_analyzed=50,
            warnings=["AlphaFold API unavailable", "AI analysis failed"]
        )
        
        assert len(result.warnings) == 2
        assert "AlphaFold API unavailable" in result.warnings
    
    def test_discovery_result_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated if not provided."""
        result = DiscoveryResult(
            query="Test disease",
            processing_time_seconds=5.5,
            candidates=[],
            targets_found=0,
            molecules_analyzed=0
        )
        
        assert isinstance(result.timestamp, datetime)


class TestErrorResponse:
    """Unit tests for ErrorResponse model."""
    
    def test_valid_error_response(self):
        """Test creating a valid ErrorResponse."""
        error = ErrorResponse(
            error_code="INVALID_DISEASE_NAME",
            message="Disease name must be between 2 and 200 characters",
            details={"provided_length": 1, "min_length": 2}
        )
        
        assert error.error_code == "INVALID_DISEASE_NAME"
        assert error.message == "Disease name must be between 2 and 200 characters"
        assert error.details["provided_length"] == 1
    
    def test_error_response_without_details(self):
        """Test ErrorResponse without details field."""
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            message="An unexpected error occurred"
        )
        
        assert error.error_code == "INTERNAL_ERROR"
        assert error.details is None
    
    def test_error_response_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated."""
        error = ErrorResponse(
            error_code="TEST_ERROR",
            message="Test error message"
        )
        
        assert isinstance(error.timestamp, str)
        assert len(error.timestamp) > 0
