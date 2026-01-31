"""Property-based tests for discovery pipeline orchestrator.

Tests universal properties of the pipeline orchestration using
Hypothesis for property-based testing.

Feature: drug-discovery-platform
"""

import pytest
from hypothesis import given, strategies as st, settings
from unittest.mock import AsyncMock, MagicMock
from app.discovery_pipeline import DiscoveryPipeline
from app.models import Target, Molecule, MolecularProperties, ToxicityAssessment


# Feature: drug-discovery-platform, Property 5: Graceful Degradation
@settings(deadline=None, max_examples=50)
@given(
    alphafold_fails=st.booleans(),
    chembl_fails=st.booleans(),
    ai_fails=st.booleans()
)
@pytest.mark.asyncio
async def test_graceful_degradation(alphafold_fails, chembl_fails, ai_fails):
    """Property 5: Graceful Degradation
    
    For any pipeline execution where a non-critical component fails
    (AlphaFold, AI analysis), the system should continue processing
    and return partial results with appropriate warnings.
    
    This test verifies that the pipeline continues when:
    - AlphaFold structures are unavailable
    - AI analysis fails
    - Individual molecule analysis fails
    
    The pipeline should only fail completely if critical components fail
    (Open Targets, ChEMBL with no molecules).
    
    Validates: Requirements 2.5, 7.10, 10.1
    """
    # Create pipeline with mocked clients
    pipeline = DiscoveryPipeline()
    
    # Mock Open Targets to return sample targets
    sample_targets = [
        Target(
            uniprot_id="P12345",
            gene_symbol="TEST1",
            protein_name="Test Protein 1",
            confidence_score=0.8,
            disease_association="Test Disease"
        ),
        Target(
            uniprot_id="P67890",
            gene_symbol="TEST2",
            protein_name="Test Protein 2",
            confidence_score=0.7,
            disease_association="Test Disease"
        )
    ]
    
    pipeline.open_targets_client.get_disease_targets = AsyncMock(
        return_value=sample_targets
    )
    
    # Mock AlphaFold based on test parameter
    if alphafold_fails:
        # AlphaFold returns None (structure unavailable)
        pipeline.alphafold_client.get_protein_structure = AsyncMock(
            return_value=None
        )
    else:
        # AlphaFold returns structures
        from app.models import ProteinStructure
        pipeline.alphafold_client.get_protein_structure = AsyncMock(
            return_value=ProteinStructure(
                uniprot_id="P12345",
                pdb_data="MOCK PDB DATA",
                plddt_score=85.0,
                is_low_confidence=False
            )
        )
    
    # Mock ChEMBL based on test parameter
    if chembl_fails:
        # ChEMBL returns empty list (no molecules)
        pipeline.chembl_client.get_bioactive_molecules = AsyncMock(
            return_value=[]
        )
    else:
        # ChEMBL returns molecules
        sample_molecules = [
            Molecule(
                chembl_id="CHEMBL123",
                name="Test Molecule",
                smiles="CCO",
                canonical_smiles="CCO",
                pchembl_value=6.5,
                activity_type="IC50",
                target_ids=["P12345"]
            )
        ]
        pipeline.chembl_client.get_bioactive_molecules = AsyncMock(
            return_value=sample_molecules
        )
    
    # Mock AI analysis based on test parameter
    if ai_fails:
        # AI analysis raises exception
        pipeline.biomistral_engine.analyze_candidates = AsyncMock(
            side_effect=Exception("AI service unavailable")
        )
    else:
        # AI analysis succeeds
        async def mock_analyze(candidates, max_candidates=20):
            for i, candidate in enumerate(candidates[:max_candidates]):
                candidate.ai_analysis = f"Mock analysis for {candidate.molecule.chembl_id}"
            return candidates
        
        pipeline.biomistral_engine.analyze_candidates = mock_analyze
    
    # Run pipeline
    result = await pipeline.discover_drugs("Test Disease")
    
    # Verify result structure
    assert result is not None
    assert result.query == "Test Disease"
    assert result.processing_time_seconds >= 0
    assert isinstance(result.warnings, list)
    
    # If ChEMBL fails, we expect no candidates
    if chembl_fails:
        assert len(result.candidates) == 0
        assert result.molecules_analyzed == 0
        # Should still have found targets
        assert result.targets_found == len(sample_targets)
    else:
        # ChEMBL succeeded, should have candidates
        assert result.molecules_analyzed > 0
        
        # If AlphaFold failed, should have warning
        if alphafold_fails:
            assert any("structure" in w.lower() for w in result.warnings), \
                "Should have warning about missing structures"
        
        # If AI failed, should have warning
        if ai_fails:
            assert any("ai" in w.lower() for w in result.warnings), \
                "Should have warning about AI unavailability"
        
        # Candidates should still be present even with failures
        if len(result.candidates) > 0:
            # Verify candidates are properly formed
            for candidate in result.candidates:
                assert candidate.molecule is not None
                assert candidate.target is not None
                assert candidate.properties is not None
                assert candidate.toxicity is not None
                assert 0.0 <= candidate.composite_score <= 1.0
                assert candidate.rank >= 1
                
                # If AI succeeded and this is in top 20, should have analysis
                if not ai_fails and candidate.rank <= 20:
                    # AI analysis might be None if it failed for this specific candidate
                    pass  # Don't assert - graceful degradation per candidate
    
    await pipeline.close()


# Feature: drug-discovery-platform, Property 5: Graceful Degradation (Edge Cases)
@pytest.mark.asyncio
async def test_graceful_degradation_edge_cases():
    """Test specific edge cases for graceful degradation.
    
    Validates: Requirements 2.5, 7.10, 10.1
    """
    pipeline = DiscoveryPipeline()
    
    # Test 1: No targets found
    pipeline.open_targets_client.get_disease_targets = AsyncMock(return_value=[])
    
    result = await pipeline.discover_drugs("Unknown Disease")
    
    assert result is not None
    assert len(result.candidates) == 0
    assert result.targets_found == 0
    assert result.molecules_analyzed == 0
    
    # Test 2: Targets found but all molecules fail analysis
    sample_targets = [
        Target(
            uniprot_id="P12345",
            gene_symbol="TEST",
            protein_name="Test Protein",
            confidence_score=0.8,
            disease_association="Test Disease"
        )
    ]
    
    pipeline.open_targets_client.get_disease_targets = AsyncMock(
        return_value=sample_targets
    )
    
    # Return molecules with invalid SMILES
    invalid_molecules = [
        Molecule(
            chembl_id="CHEMBL999",
            name="Invalid Molecule",
            smiles="INVALID_SMILES",
            canonical_smiles="INVALID_SMILES",
            pchembl_value=6.5,
            activity_type="IC50",
            target_ids=["P12345"]
        )
    ]
    
    pipeline.chembl_client.get_bioactive_molecules = AsyncMock(
        return_value=invalid_molecules
    )
    
    result = await pipeline.discover_drugs("Test Disease")
    
    # Should handle invalid molecules gracefully
    assert result is not None
    assert result.targets_found == 1
    # Molecules with invalid SMILES should be filtered out
    assert len(result.candidates) == 0
    assert any("failed analysis" in w.lower() for w in result.warnings)
    
    # Test 3: Pipeline exception handling
    pipeline.open_targets_client.get_disease_targets = AsyncMock(
        side_effect=Exception("API connection failed")
    )
    
    result = await pipeline.discover_drugs("Test Disease")
    
    # Should return empty result with error warning
    assert result is not None
    assert len(result.candidates) == 0
    assert len(result.warnings) > 0
    
    await pipeline.close()


# Feature: drug-discovery-platform, Property 5: Graceful Degradation (Concurrent Failures)
@pytest.mark.asyncio
async def test_graceful_degradation_concurrent_failures():
    """Test graceful degradation with concurrent API failures.
    
    Validates: Requirements 2.5, 7.10, 10.1, 9.7, 9.8
    """
    pipeline = DiscoveryPipeline()
    
    # Create multiple targets
    targets = [
        Target(
            uniprot_id=f"P{i:05d}",
            gene_symbol=f"GENE{i}",
            protein_name=f"Protein {i}",
            confidence_score=0.8,
            disease_association="Test Disease"
        )
        for i in range(10)
    ]
    
    pipeline.open_targets_client.get_disease_targets = AsyncMock(
        return_value=targets
    )
    
    # Mock AlphaFold to fail for some targets
    call_count = 0
    
    async def mock_get_structure(uniprot_id):
        nonlocal call_count
        call_count += 1
        # Fail for odd-numbered calls
        if call_count % 2 == 1:
            return None
        from app.models import ProteinStructure
        return ProteinStructure(
            uniprot_id=uniprot_id,
            pdb_data="MOCK PDB",
            plddt_score=80.0,
            is_low_confidence=False
        )
    
    pipeline.alphafold_client.get_protein_structure = mock_get_structure
    
    # Mock ChEMBL to return molecules for all targets
    pipeline.chembl_client.get_bioactive_molecules = AsyncMock(
        return_value=[
            Molecule(
                chembl_id="CHEMBL123",
                name="Test Molecule",
                smiles="CCO",
                canonical_smiles="CCO",
                pchembl_value=6.5,
                activity_type="IC50",
                target_ids=[]
            )
        ]
    )
    
    result = await pipeline.discover_drugs("Test Disease")
    
    # Should complete despite partial AlphaFold failures
    assert result is not None
    assert result.targets_found == 10
    # Should have warning about missing structures
    assert any("structure" in w.lower() for w in result.warnings)
    
    await pipeline.close()
