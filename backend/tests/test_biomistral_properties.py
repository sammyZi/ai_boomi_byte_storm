"""Property-based tests for BioMistral AI engine.

Tests universal properties of the AI analysis engine using
Hypothesis for property-based testing.

Feature: drug-discovery-platform
"""

import pytest
from hypothesis import given, strategies as st, settings
from app.biomistral_engine import BioMistralEngine
from app.models import DrugCandidate, Molecule, Target, MolecularProperties, ToxicityAssessment


# Helper strategies for generating test data
def drug_candidate_strategy():
    """Strategy for generating DrugCandidate objects."""
    return st.builds(
        DrugCandidate,
        molecule=st.builds(
            Molecule,
            chembl_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
            name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd', 'Zs'))),
            smiles=st.just("CCO"),  # Simple ethanol SMILES
            canonical_smiles=st.just("CCO"),
            pchembl_value=st.floats(min_value=4.0, max_value=10.0, allow_nan=False, allow_infinity=False),
            activity_type=st.sampled_from(['Ki', 'Kd', 'IC50', 'EC50']),
            target_ids=st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=3)
        ),
        target=st.builds(
            Target,
            uniprot_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Nd'))),
            gene_symbol=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu',))),
            protein_name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs'))),
            confidence_score=st.floats(min_value=0.5, max_value=1.0, allow_nan=False, allow_infinity=False),
            disease_association=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Zs')))
        ),
        properties=st.builds(
            MolecularProperties,
            molecular_weight=st.floats(min_value=100.0, max_value=600.0, allow_nan=False, allow_infinity=False),
            logp=st.floats(min_value=-2.0, max_value=6.0, allow_nan=False, allow_infinity=False),
            hbd=st.integers(min_value=0, max_value=10),
            hba=st.integers(min_value=0, max_value=15),
            tpsa=st.floats(min_value=0.0, max_value=200.0, allow_nan=False, allow_infinity=False),
            rotatable_bonds=st.integers(min_value=0, max_value=20),
            aromatic_rings=st.integers(min_value=0, max_value=5),
            lipinski_violations=st.integers(min_value=0, max_value=4),
            drug_likeness_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
        ),
        toxicity=st.builds(
            ToxicityAssessment,
            toxicity_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            risk_level=st.sampled_from(['low', 'medium', 'high']),
            detected_toxicophores=st.lists(st.text(min_size=1, max_size=20), max_size=5),
            warnings=st.lists(st.text(min_size=1, max_size=50), max_size=3)
        ),
        binding_affinity_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        binding_confidence=st.floats(min_value=0.6, max_value=0.9, allow_nan=False, allow_infinity=False),
        composite_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        rank=st.integers(min_value=1, max_value=1000),
        ai_analysis=st.none(),  # Start with no analysis
        structure_2d_svg=st.text(min_size=10, max_size=100)
    )


# Feature: drug-discovery-platform, Property 21: AI Analysis Limitation
@settings(deadline=None, max_examples=100)
@given(
    candidates=st.lists(
        drug_candidate_strategy(),
        min_size=1,
        max_size=100
    ),
    max_candidates=st.integers(min_value=1, max_value=50)
)
@pytest.mark.asyncio
async def test_ai_analysis_limitation(candidates, max_candidates):
    """Property 21: AI Analysis Limitation
    
    For any list of ranked candidates, the system should generate AI analysis
    for at most the top N candidates (where N is configurable, default 20).
    
    This test verifies the limitation without actually calling the AI model,
    by checking that only the first max_candidates have analysis attempted.
    
    Validates: Requirements 7.11
    """
    # Create engine (won't actually call Ollama in this test)
    engine = BioMistralEngine()
    
    # Mock the analyze_candidate method to track calls
    call_count = 0
    original_analyze = engine.analyze_candidate
    
    async def mock_analyze_candidate(molecule, target, properties, toxicity):
        nonlocal call_count
        call_count += 1
        return f"Mock analysis {call_count}"
    
    engine.analyze_candidate = mock_analyze_candidate
    
    # Analyze candidates with limitation
    result = await engine.analyze_candidates(candidates, max_candidates=max_candidates)
    
    # Should return same candidates
    assert len(result) == len(candidates), \
        f"Expected {len(candidates)} candidates, got {len(result)}"
    
    # Calculate expected number of analyses
    expected_analyses = min(len(candidates), max_candidates)
    
    # Should have called analyze_candidate exactly expected_analyses times
    assert call_count == expected_analyses, \
        f"Expected {expected_analyses} analysis calls, got {call_count}"
    
    # First N candidates should have analysis
    for i in range(expected_analyses):
        assert result[i].ai_analysis is not None, \
            f"Candidate {i} should have AI analysis"
        assert result[i].ai_analysis.startswith("Mock analysis"), \
            f"Candidate {i} should have mock analysis"
    
    # Remaining candidates should have no analysis
    for i in range(expected_analyses, len(result)):
        assert result[i].ai_analysis is None, \
            f"Candidate {i} should not have AI analysis (beyond limit)"
    
    await engine.close()


# Feature: drug-discovery-platform, Property 21: AI Analysis Limitation (Edge Cases)
@pytest.mark.asyncio
async def test_ai_analysis_limitation_edge_cases():
    """Test edge cases for AI analysis limitation.
    
    Validates: Requirements 7.11
    """
    engine = BioMistralEngine()
    
    # Mock the analyze_candidate method
    call_count = 0
    
    async def mock_analyze_candidate(molecule, target, properties, toxicity):
        nonlocal call_count
        call_count += 1
        return f"Analysis {call_count}"
    
    engine.analyze_candidate = mock_analyze_candidate
    
    # Test 1: Empty list
    result = await engine.analyze_candidates([], max_candidates=20)
    assert len(result) == 0
    assert call_count == 0
    
    # Test 2: Fewer candidates than limit
    call_count = 0
    candidates = [
        DrugCandidate(
            molecule=Molecule(
                chembl_id=f"CHEMBL{i}",
                name=f"Molecule {i}",
                smiles="CCO",
                canonical_smiles="CCO",
                pchembl_value=6.0,
                activity_type="IC50",
                target_ids=["P12345"]
            ),
            target=Target(
                uniprot_id="P12345",
                gene_symbol="TEST",
                protein_name="Test Protein",
                confidence_score=0.8,
                disease_association="Test Disease"
            ),
            properties=MolecularProperties(
                molecular_weight=200.0,
                logp=2.0,
                hbd=1,
                hba=2,
                tpsa=50.0,
                rotatable_bonds=2,
                aromatic_rings=1,
                lipinski_violations=0,
                drug_likeness_score=1.0
            ),
            toxicity=ToxicityAssessment(
                toxicity_score=0.1,
                risk_level="low",
                detected_toxicophores=[],
                warnings=[]
            ),
            binding_affinity_score=0.7,
            binding_confidence=0.8,
            composite_score=0.75,
            rank=i+1,
            ai_analysis=None,
            structure_2d_svg="<svg></svg>"
        )
        for i in range(5)
    ]
    
    result = await engine.analyze_candidates(candidates, max_candidates=20)
    assert len(result) == 5
    assert call_count == 5  # All 5 should be analyzed
    
    # Test 3: More candidates than limit
    call_count = 0
    candidates = [
        DrugCandidate(
            molecule=Molecule(
                chembl_id=f"CHEMBL{i}",
                name=f"Molecule {i}",
                smiles="CCO",
                canonical_smiles="CCO",
                pchembl_value=6.0,
                activity_type="IC50",
                target_ids=["P12345"]
            ),
            target=Target(
                uniprot_id="P12345",
                gene_symbol="TEST",
                protein_name="Test Protein",
                confidence_score=0.8,
                disease_association="Test Disease"
            ),
            properties=MolecularProperties(
                molecular_weight=200.0,
                logp=2.0,
                hbd=1,
                hba=2,
                tpsa=50.0,
                rotatable_bonds=2,
                aromatic_rings=1,
                lipinski_violations=0,
                drug_likeness_score=1.0
            ),
            toxicity=ToxicityAssessment(
                toxicity_score=0.1,
                risk_level="low",
                detected_toxicophores=[],
                warnings=[]
            ),
            binding_affinity_score=0.7,
            binding_confidence=0.8,
            composite_score=0.75,
            rank=i+1,
            ai_analysis=None,
            structure_2d_svg="<svg></svg>"
        )
        for i in range(30)
    ]
    
    result = await engine.analyze_candidates(candidates, max_candidates=20)
    assert len(result) == 30
    assert call_count == 20  # Only first 20 should be analyzed
    
    # First 20 should have analysis
    for i in range(20):
        assert result[i].ai_analysis is not None
    
    # Last 10 should not have analysis
    for i in range(20, 30):
        assert result[i].ai_analysis is None
    
    await engine.close()
