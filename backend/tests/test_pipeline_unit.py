"""Unit tests for discovery pipeline orchestrator.

Tests specific examples and edge cases for the pipeline orchestration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from app.discovery_pipeline import DiscoveryPipeline
from app.models import (
    Target,
    Molecule,
    MolecularProperties,
    ToxicityAssessment,
    ProteinStructure,
    DrugCandidate
)


@pytest.fixture
def sample_target():
    """Create a sample target for testing."""
    return Target(
        uniprot_id="P12345",
        gene_symbol="TEST",
        protein_name="Test Protein",
        confidence_score=0.8,
        disease_association="Test Disease"
    )


@pytest.fixture
def sample_molecule():
    """Create a sample molecule for testing."""
    return Molecule(
        chembl_id="CHEMBL123",
        name="Test Molecule",
        smiles="CCO",
        canonical_smiles="CCO",
        pchembl_value=6.5,
        activity_type="IC50",
        target_ids=["P12345"]
    )


@pytest.fixture
def sample_structure():
    """Create a sample protein structure for testing."""
    return ProteinStructure(
        uniprot_id="P12345",
        pdb_data="MOCK PDB DATA",
        plddt_score=85.0,
        is_low_confidence=False
    )


class TestDiscoveryPipeline:
    """Test suite for DiscoveryPipeline class."""
    
    def test_initialization_default(self):
        """Test pipeline initialization with default clients."""
        pipeline = DiscoveryPipeline()
        
        assert pipeline.open_targets_client is not None
        assert pipeline.alphafold_client is not None
        assert pipeline.chembl_client is not None
        assert pipeline.rdkit_analyzer is not None
        assert pipeline.scoring_engine is not None
        assert pipeline.biomistral_engine is not None
        assert pipeline.max_concurrent_requests == 5
        assert pipeline.warnings == []
    
    def test_initialization_custom(self):
        """Test pipeline initialization with custom clients."""
        mock_ot = MagicMock()
        mock_af = MagicMock()
        mock_chembl = MagicMock()
        
        pipeline = DiscoveryPipeline(
            open_targets_client=mock_ot,
            alphafold_client=mock_af,
            chembl_client=mock_chembl,
            max_concurrent_requests=10
        )
        
        assert pipeline.open_targets_client == mock_ot
        assert pipeline.alphafold_client == mock_af
        assert pipeline.chembl_client == mock_chembl
        assert pipeline.max_concurrent_requests == 10
    
    @pytest.mark.asyncio
    async def test_discover_drugs_no_targets(self):
        """Test pipeline with no targets found.
        
        Validates: Requirements 9.1, 10.1
        """
        pipeline = DiscoveryPipeline()
        
        # Mock Open Targets to return empty list
        pipeline.open_targets_client.get_disease_targets = AsyncMock(return_value=[])
        
        result = await pipeline.discover_drugs("Unknown Disease")
        
        assert result is not None
        assert result.query == "Unknown Disease"
        assert len(result.candidates) == 0
        assert result.targets_found == 0
        assert result.molecules_analyzed == 0
        assert result.processing_time_seconds >= 0
    
    @pytest.mark.asyncio
    async def test_discover_drugs_no_molecules(self, sample_target):
        """Test pipeline with targets but no molecules.
        
        Validates: Requirements 9.1, 10.1
        """
        pipeline = DiscoveryPipeline()
        
        # Mock Open Targets to return targets
        pipeline.open_targets_client.get_disease_targets = AsyncMock(
            return_value=[sample_target]
        )
        
        # Mock AlphaFold
        pipeline.alphafold_client.get_protein_structure = AsyncMock(return_value=None)
        
        # Mock ChEMBL to return empty list
        pipeline.chembl_client.get_bioactive_molecules = AsyncMock(return_value=[])
        
        result = await pipeline.discover_drugs("Test Disease")
        
        assert result is not None
        assert result.targets_found == 1
        assert len(result.candidates) == 0
        assert result.molecules_analyzed == 0
    
    @pytest.mark.asyncio
    async def test_discover_drugs_complete_workflow(
        self,
        sample_target,
        sample_molecule,
        sample_structure
    ):
        """Test complete pipeline workflow with mocked components.
        
        Validates: Requirements 9.1, 9.7, 9.8
        """
        pipeline = DiscoveryPipeline()
        
        # Mock Open Targets
        pipeline.open_targets_client.get_disease_targets = AsyncMock(
            return_value=[sample_target]
        )
        
        # Mock AlphaFold
        pipeline.alphafold_client.get_protein_structure = AsyncMock(
            return_value=sample_structure
        )
        
        # Mock ChEMBL
        pipeline.chembl_client.get_bioactive_molecules = AsyncMock(
            return_value=[sample_molecule]
        )
        
        # Mock AI analysis
        async def mock_analyze(candidates, max_candidates=20):
            for candidate in candidates[:max_candidates]:
                candidate.ai_analysis = "Mock AI analysis"
            return candidates
        
        pipeline.biomistral_engine.analyze_candidates = mock_analyze
        
        result = await pipeline.discover_drugs("Test Disease")
        
        assert result is not None
        assert result.query == "Test Disease"
        assert result.targets_found == 1
        assert result.molecules_analyzed == 1
        assert len(result.candidates) > 0
        
        # Verify candidate structure
        candidate = result.candidates[0]
        assert candidate.molecule.chembl_id == "CHEMBL123"
        assert candidate.target.uniprot_id == "P12345"
        assert candidate.rank == 1
        assert 0.0 <= candidate.composite_score <= 1.0
        assert candidate.ai_analysis == "Mock AI analysis"
    
    @pytest.mark.asyncio
    async def test_concurrent_structure_fetching(self, sample_target):
        """Test concurrent fetching of protein structures.
        
        Validates: Requirements 9.7, 9.8
        """
        pipeline = DiscoveryPipeline(max_concurrent_requests=2)
        
        # Create multiple targets
        targets = [
            Target(
                uniprot_id=f"P{i:05d}",
                gene_symbol=f"GENE{i}",
                protein_name=f"Protein {i}",
                confidence_score=0.8,
                disease_association="Test Disease"
            )
            for i in range(5)
        ]
        
        # Mock AlphaFold to return structures
        call_count = 0
        
        async def mock_get_structure(uniprot_id):
            nonlocal call_count
            call_count += 1
            return ProteinStructure(
                uniprot_id=uniprot_id,
                pdb_data="MOCK PDB",
                plddt_score=80.0,
                is_low_confidence=False
            )
        
        pipeline.alphafold_client.get_protein_structure = mock_get_structure
        
        structures = await pipeline._fetch_structures_concurrent(targets)
        
        # Should have called for all targets
        assert call_count == 5
        assert len(structures) == 5
        
        # Verify all structures are present
        for target in targets:
            assert target.uniprot_id in structures
    
    @pytest.mark.asyncio
    async def test_concurrent_molecule_fetching(self):
        """Test concurrent fetching of bioactive molecules.
        
        Validates: Requirements 9.7, 9.8, 3.4
        """
        pipeline = DiscoveryPipeline(max_concurrent_requests=2)
        
        # Create multiple targets
        targets = [
            Target(
                uniprot_id=f"P{i:05d}",
                gene_symbol=f"GENE{i}",
                protein_name=f"Protein {i}",
                confidence_score=0.8,
                disease_association="Test Disease"
            )
            for i in range(3)
        ]
        
        # Mock ChEMBL to return molecules
        async def mock_get_molecules(target_id):
            return [
                Molecule(
                    chembl_id=f"CHEMBL{target_id}",
                    name=f"Molecule for {target_id}",
                    smiles="CCO",
                    canonical_smiles="CCO",
                    pchembl_value=6.5,
                    activity_type="IC50",
                    target_ids=[]
                )
            ]
        
        pipeline.chembl_client.get_bioactive_molecules = mock_get_molecules
        
        molecules = await pipeline._fetch_molecules_concurrent(targets)
        
        # Should have fetched molecules for all targets
        assert len(molecules) == 3
        
        # Verify target IDs are associated
        for molecule in molecules:
            assert len(molecule.target_ids) == 1
    
    @pytest.mark.asyncio
    async def test_molecule_deduplication(self):
        """Test deduplication of molecules across targets.
        
        Validates: Requirements 3.4
        """
        pipeline = DiscoveryPipeline()
        
        # Create targets
        targets = [
            Target(
                uniprot_id="P12345",
                gene_symbol="GENE1",
                protein_name="Protein 1",
                confidence_score=0.8,
                disease_association="Test Disease"
            ),
            Target(
                uniprot_id="P67890",
                gene_symbol="GENE2",
                protein_name="Protein 2",
                confidence_score=0.7,
                disease_association="Test Disease"
            )
        ]
        
        # Mock ChEMBL to return same molecule for both targets
        async def mock_get_molecules(target_id):
            return [
                Molecule(
                    chembl_id="CHEMBL123",  # Same molecule
                    name="Shared Molecule",
                    smiles="CCO",
                    canonical_smiles="CCO",
                    pchembl_value=6.5,
                    activity_type="IC50",
                    target_ids=[]
                )
            ]
        
        pipeline.chembl_client.get_bioactive_molecules = mock_get_molecules
        
        molecules = await pipeline._fetch_molecules_concurrent(targets)
        
        # Should have only one molecule (deduplicated)
        assert len(molecules) == 1
        
        # Should be associated with both targets
        assert len(molecules[0].target_ids) == 2
        assert "P12345" in molecules[0].target_ids
        assert "P67890" in molecules[0].target_ids
    
    @pytest.mark.asyncio
    async def test_graceful_degradation_alphafold_failure(self, sample_target, sample_molecule):
        """Test graceful degradation when AlphaFold fails.
        
        Validates: Requirements 2.5, 10.1
        """
        pipeline = DiscoveryPipeline()
        
        pipeline.open_targets_client.get_disease_targets = AsyncMock(
            return_value=[sample_target]
        )
        
        # AlphaFold returns None (structure unavailable)
        pipeline.alphafold_client.get_protein_structure = AsyncMock(return_value=None)
        
        pipeline.chembl_client.get_bioactive_molecules = AsyncMock(
            return_value=[sample_molecule]
        )
        
        result = await pipeline.discover_drugs("Test Disease")
        
        # Should still complete successfully
        assert result is not None
        assert len(result.candidates) > 0
        
        # Should have warning about missing structures
        assert any("structure" in w.lower() for w in result.warnings)
    
    @pytest.mark.asyncio
    @pytest.mark.filterwarnings("ignore::ResourceWarning")
    @pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
    async def test_graceful_degradation_ai_failure(self, sample_target, sample_molecule):
        """Test graceful degradation when AI analysis fails.
        
        Validates: Requirements 7.10, 10.1
        
        Note: Resource warnings are suppressed for this test as they are artifacts
        of mocking the AI engine's analyze_candidates method, which bypasses normal
        cleanup flow. In production, the context manager ensures proper cleanup.
        """
        pipeline = DiscoveryPipeline()
        
        try:
            pipeline.open_targets_client.get_disease_targets = AsyncMock(
                return_value=[sample_target]
            )
            
            pipeline.alphafold_client.get_protein_structure = AsyncMock(return_value=None)
            
            pipeline.chembl_client.get_bioactive_molecules = AsyncMock(
                return_value=[sample_molecule]
            )
            
            # AI analysis raises exception
            pipeline.biomistral_engine.analyze_candidates = AsyncMock(
                side_effect=Exception("AI service unavailable")
            )
            
            result = await pipeline.discover_drugs("Test Disease")
            
            # Should still complete successfully
            assert result is not None
            assert len(result.candidates) > 0
            
            # Should have warning about AI unavailability
            assert any("ai" in w.lower() for w in result.warnings)
        finally:
            # Ensure proper cleanup
            await pipeline.close()
    
    @pytest.mark.asyncio
    async def test_error_logging(self, sample_target):
        """Test error logging throughout pipeline.
        
        Validates: Requirements 10.5
        """
        pipeline = DiscoveryPipeline()
        
        try:
            pipeline.open_targets_client.get_disease_targets = AsyncMock(
                return_value=[sample_target]
            )
            
            # Mock ChEMBL to raise exception
            pipeline.chembl_client.get_bioactive_molecules = AsyncMock(
                side_effect=Exception("ChEMBL API error")
            )
            
            result = await pipeline.discover_drugs("Test Disease")
            
            # Should handle error gracefully
            assert result is not None
            assert len(result.candidates) == 0
        finally:
            # Ensure proper cleanup
            await pipeline.close()
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager usage."""
        async with DiscoveryPipeline() as pipeline:
            assert pipeline is not None
        
        # Pipeline should be closed after context exit
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test explicit close method."""
        pipeline = DiscoveryPipeline()
        
        # Should not raise any errors
        await pipeline.close()
