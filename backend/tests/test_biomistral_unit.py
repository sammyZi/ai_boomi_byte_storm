"""Unit tests for BioMistral AI engine.

Tests specific examples and edge cases for the AI analysis engine.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.biomistral_engine import BioMistralEngine
from app.models import (
    Molecule,
    Target,
    MolecularProperties,
    ToxicityAssessment,
    DrugCandidate
)


@pytest.fixture
def sample_molecule():
    """Create a sample molecule for testing."""
    return Molecule(
        chembl_id="CHEMBL123",
        name="Aspirin",
        smiles="CC(=O)Oc1ccccc1C(=O)O",
        canonical_smiles="CC(=O)Oc1ccccc1C(=O)O",
        pchembl_value=6.5,
        activity_type="IC50",
        target_ids=["P12345"]
    )


@pytest.fixture
def sample_target():
    """Create a sample target for testing."""
    return Target(
        uniprot_id="P12345",
        gene_symbol="COX2",
        protein_name="Cyclooxygenase-2",
        confidence_score=0.85,
        disease_association="Inflammation and pain"
    )


@pytest.fixture
def sample_properties():
    """Create sample molecular properties for testing."""
    return MolecularProperties(
        molecular_weight=180.16,
        logp=1.19,
        hbd=1,
        hba=4,
        tpsa=63.6,
        rotatable_bonds=3,
        aromatic_rings=1,
        lipinski_violations=0,
        drug_likeness_score=1.0
    )


@pytest.fixture
def sample_toxicity():
    """Create sample toxicity assessment for testing."""
    return ToxicityAssessment(
        toxicity_score=0.15,
        risk_level="low",
        detected_toxicophores=["acyl_chloride"],
        warnings=["Contains reactive acyl group"]
    )


@pytest.fixture
def sample_candidate(sample_molecule, sample_target, sample_properties, sample_toxicity):
    """Create a sample drug candidate for testing."""
    return DrugCandidate(
        molecule=sample_molecule,
        target=sample_target,
        properties=sample_properties,
        toxicity=sample_toxicity,
        binding_affinity_score=0.75,
        binding_confidence=0.8,
        composite_score=0.72,
        rank=1,
        ai_analysis=None,
        structure_2d_svg="<svg></svg>"
    )


class TestBioMistralEngine:
    """Test suite for BioMistralEngine class."""
    
    def test_initialization_default_settings(self):
        """Test engine initialization with default settings."""
        engine = BioMistralEngine()
        
        assert engine.base_url == "http://localhost:11434"
        assert engine.model == "biomistral:7b"
        assert engine.timeout == 5
        assert engine.client is not None
    
    def test_initialization_custom_settings(self):
        """Test engine initialization with custom settings."""
        engine = BioMistralEngine(
            base_url="http://custom:8080",
            model="custom-model",
            timeout=10
        )
        
        assert engine.base_url == "http://custom:8080"
        assert engine.model == "custom-model"
        assert engine.timeout == 10
    
    def test_generate_prompt(
        self,
        sample_molecule,
        sample_target,
        sample_properties,
        sample_toxicity
    ):
        """Test prompt generation with sample data.
        
        Validates: Requirements 7.1
        """
        engine = BioMistralEngine()
        
        prompt = engine._generate_prompt(
            sample_molecule,
            sample_target,
            sample_properties,
            sample_toxicity
        )
        
        # Verify prompt contains key information
        assert "Aspirin" in prompt
        assert "CHEMBL123" in prompt
        assert "Cyclooxygenase-2" in prompt
        assert "COX2" in prompt
        assert "6.5" in prompt  # pChEMBL value
        assert "180.16" in prompt  # Molecular weight
        assert "IC50" in prompt
        assert "low" in prompt  # Risk level
        assert "acyl_chloride" in prompt  # Toxicophore
        
        # Verify prompt structure
        assert "MOLECULE INFORMATION:" in prompt
        assert "TARGET INFORMATION:" in prompt
        assert "BINDING AFFINITY:" in prompt
        assert "MOLECULAR PROPERTIES:" in prompt
        assert "DRUG-LIKENESS:" in prompt
        assert "TOXICITY ASSESSMENT:" in prompt
        
        # Verify prompt asks for specific analysis sections
        assert "Molecular properties" in prompt
        assert "Binding affinity" in prompt
        assert "Drug-likeness" in prompt
        assert "Safety profile" in prompt
        assert "Mechanism of action" in prompt
    
    @pytest.mark.asyncio
    async def test_analyze_candidate_success(
        self,
        sample_molecule,
        sample_target,
        sample_properties,
        sample_toxicity
    ):
        """Test successful candidate analysis.
        
        Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7
        """
        engine = BioMistralEngine()
        
        # Mock the Ollama API call
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "response": "This is a detailed AI analysis of the drug candidate."
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await engine.analyze_candidate(
                sample_molecule,
                sample_target,
                sample_properties,
                sample_toxicity
            )
        
        # Verify result
        assert result is not None
        assert result == "This is a detailed AI analysis of the drug candidate."
        
        # Verify API was called correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Verify URL
        assert call_args[0][0] == "http://localhost:11434/api/generate"
        
        # Verify payload
        payload = call_args[1]['json']
        assert payload['model'] == "biomistral:7b"
        assert payload['stream'] is False
        assert payload['options']['temperature'] == 0.3
        assert payload['options']['num_predict'] == 500
        assert 'prompt' in payload
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_analyze_candidate_timeout(
        self,
        sample_molecule,
        sample_target,
        sample_properties,
        sample_toxicity
    ):
        """Test graceful handling of timeout.
        
        Validates: Requirements 7.10
        """
        engine = BioMistralEngine(timeout=1)
        
        # Mock a slow API call that times out
        async def slow_call(*args, **kwargs):
            await asyncio.sleep(2)  # Longer than timeout
            return MagicMock()
        
        with patch.object(engine.client, 'post', side_effect=slow_call):
            result = await engine.analyze_candidate(
                sample_molecule,
                sample_target,
                sample_properties,
                sample_toxicity
            )
        
        # Should return None on timeout (graceful degradation)
        assert result is None
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_analyze_candidate_api_error(
        self,
        sample_molecule,
        sample_target,
        sample_properties,
        sample_toxicity
    ):
        """Test graceful handling of API errors.
        
        Validates: Requirements 7.10
        """
        engine = BioMistralEngine()
        
        # Mock an API error
        with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("API connection failed")
            
            result = await engine.analyze_candidate(
                sample_molecule,
                sample_target,
                sample_properties,
                sample_toxicity
            )
        
        # Should return None on error (graceful degradation)
        assert result is None
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_analyze_candidate_invalid_response(
        self,
        sample_molecule,
        sample_target,
        sample_properties,
        sample_toxicity
    ):
        """Test graceful handling of invalid API response.
        
        Validates: Requirements 7.10
        """
        engine = BioMistralEngine()
        
        # Mock an invalid response
        mock_response = MagicMock()
        mock_response.json.return_value = {}  # Missing 'response' key
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(engine.client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await engine.analyze_candidate(
                sample_molecule,
                sample_target,
                sample_properties,
                sample_toxicity
            )
        
        # Should return empty string for missing response
        assert result == ""
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_analyze_candidates_with_limit(self, sample_candidate):
        """Test analyzing multiple candidates with limit.
        
        Validates: Requirements 7.11
        """
        engine = BioMistralEngine()
        
        # Create 30 candidates
        candidates = []
        for i in range(30):
            candidate = DrugCandidate(
                molecule=Molecule(
                    chembl_id=f"CHEMBL{i}",
                    name=f"Molecule {i}",
                    smiles="CCO",
                    canonical_smiles="CCO",
                    pchembl_value=6.0,
                    activity_type="IC50",
                    target_ids=["P12345"]
                ),
                target=sample_candidate.target,
                properties=sample_candidate.properties,
                toxicity=sample_candidate.toxicity,
                binding_affinity_score=0.7,
                binding_confidence=0.8,
                composite_score=0.75 - (i * 0.01),  # Descending scores
                rank=i+1,
                ai_analysis=None,
                structure_2d_svg="<svg></svg>"
            )
            candidates.append(candidate)
        
        # Mock the analyze_candidate method
        call_count = 0
        
        async def mock_analyze(molecule, target, properties, toxicity):
            nonlocal call_count
            call_count += 1
            return f"Analysis for {molecule.chembl_id}"
        
        engine.analyze_candidate = mock_analyze
        
        # Analyze with limit of 20
        result = await engine.analyze_candidates(candidates, max_candidates=20)
        
        # Should have analyzed exactly 20 candidates
        assert call_count == 20
        
        # First 20 should have analysis
        for i in range(20):
            assert result[i].ai_analysis is not None
            assert f"CHEMBL{i}" in result[i].ai_analysis
        
        # Last 10 should not have analysis
        for i in range(20, 30):
            assert result[i].ai_analysis is None
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_analyze_candidates_fewer_than_limit(self, sample_candidate):
        """Test analyzing fewer candidates than the limit.
        
        Validates: Requirements 7.11
        """
        engine = BioMistralEngine()
        
        # Create 5 candidates
        candidates = []
        for i in range(5):
            candidate = DrugCandidate(
                molecule=Molecule(
                    chembl_id=f"CHEMBL{i}",
                    name=f"Molecule {i}",
                    smiles="CCO",
                    canonical_smiles="CCO",
                    pchembl_value=6.0,
                    activity_type="IC50",
                    target_ids=["P12345"]
                ),
                target=sample_candidate.target,
                properties=sample_candidate.properties,
                toxicity=sample_candidate.toxicity,
                binding_affinity_score=0.7,
                binding_confidence=0.8,
                composite_score=0.75,
                rank=i+1,
                ai_analysis=None,
                structure_2d_svg="<svg></svg>"
            )
            candidates.append(candidate)
        
        # Mock the analyze_candidate method
        call_count = 0
        
        async def mock_analyze(molecule, target, properties, toxicity):
            nonlocal call_count
            call_count += 1
            return f"Analysis for {molecule.chembl_id}"
        
        engine.analyze_candidate = mock_analyze
        
        # Analyze with limit of 20 (more than available)
        result = await engine.analyze_candidates(candidates, max_candidates=20)
        
        # Should have analyzed all 5 candidates
        assert call_count == 5
        
        # All should have analysis
        for i in range(5):
            assert result[i].ai_analysis is not None
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_analyze_candidates_empty_list(self):
        """Test analyzing empty candidate list."""
        engine = BioMistralEngine()
        
        result = await engine.analyze_candidates([], max_candidates=20)
        
        assert len(result) == 0
        
        await engine.close()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager usage."""
        async with BioMistralEngine() as engine:
            assert engine is not None
            assert engine.client is not None
        
        # Client should be closed after context exit
        # (We can't easily test this without accessing internal state)
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test explicit close method."""
        engine = BioMistralEngine()
        
        # Should not raise any errors
        await engine.close()
