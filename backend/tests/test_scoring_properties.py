"""Property-based tests for scoring engine.

Tests universal properties of the scoring and ranking engine using
Hypothesis for property-based testing.

Feature: drug-discovery-platform
"""

import pytest
from hypothesis import given, strategies as st
from app.scoring_engine import ScoringEngine
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
        ai_analysis=st.one_of(st.none(), st.text(min_size=10, max_size=200)),
        structure_2d_svg=st.text(min_size=10, max_size=100)
    )


# Feature: drug-discovery-platform, Property 9: Binding Affinity Normalization
@given(pchembl=st.floats(min_value=0.0, max_value=15.0, allow_nan=False, allow_infinity=False))
def test_binding_affinity_normalization(pchembl):
    """Property 9: Binding Affinity Normalization
    
    For any pChEMBL value, the system should normalize it to a 0-1 scale
    using the formula (pChEMBL - 4) / (10 - 4), clamping values below 4
    to 0.0 and values above 10 to 1.0.
    
    Validates: Requirements 4.1, 4.2
    """
    score = ScoringEngine.normalize_binding_affinity(pchembl)
    
    # Score should always be in [0, 1]
    assert 0.0 <= score <= 1.0, f"Score {score} not in [0, 1] for pChEMBL {pchembl}"
    
    # Values below 4 should map to 0
    if pchembl < 4.0:
        assert score == 0.0, f"pChEMBL {pchembl} < 4 should map to 0, got {score}"
    
    # Values above 10 should map to 1
    elif pchembl > 10.0:
        assert score == 1.0, f"pChEMBL {pchembl} > 10 should map to 1, got {score}"
    
    # Values in range [4, 10] should follow formula
    else:
        expected = (pchembl - 4.0) / (10.0 - 4.0)
        assert abs(score - expected) < 0.001, \
            f"pChEMBL {pchembl} should map to {expected}, got {score}"


# Feature: drug-discovery-platform, Property 10: Maximum Activity Selection
@given(
    activities=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=15.0, allow_nan=False, allow_infinity=False),
            st.sampled_from(['Ki', 'Kd', 'IC50', 'EC50', 'Other'])
        ),
        min_size=1,
        max_size=20
    )
)
def test_maximum_activity_selection(activities):
    """Property 10: Maximum Activity Selection
    
    For any molecule-target pair with multiple activity measurements,
    the system should use the highest pChEMBL value for binding affinity
    calculation.
    
    Validates: Requirements 4.5
    """
    max_pchembl, activity_type = ScoringEngine.select_maximum_activity(activities)
    
    # The selected pChEMBL should be the maximum in the list
    all_pchembl_values = [pchembl for pchembl, _ in activities]
    expected_max = max(all_pchembl_values)
    
    assert max_pchembl == expected_max, \
        f"Selected pChEMBL {max_pchembl} is not the maximum {expected_max}"
    
    # The activity type should correspond to the maximum pChEMBL
    matching_activities = [act_type for pchembl, act_type in activities if pchembl == max_pchembl]
    assert activity_type in matching_activities, \
        f"Activity type {activity_type} doesn't match any activity with max pChEMBL {max_pchembl}"


# Feature: drug-discovery-platform, Property 11: Measurement Type Confidence Mapping
@given(
    activity_type=st.sampled_from([
        'Ki', 'Kd', 'IC50', 'EC50',  # Known types
        'GI50', 'AC50', 'Potency', 'Activity'  # Other types
    ])
)
def test_measurement_type_confidence_mapping(activity_type):
    """Property 11: Measurement Type Confidence Mapping
    
    For any activity measurement, the system should assign confidence scores
    based on measurement type: Ki/Kd → 0.9, IC50/EC50 → 0.8, other → 0.6.
    
    Validates: Requirements 4.6
    """
    confidence = ScoringEngine.get_measurement_confidence(activity_type)
    
    # Confidence should be in valid range
    assert 0.6 <= confidence <= 0.9, \
        f"Confidence {confidence} not in valid range [0.6, 0.9]"
    
    # Check specific mappings
    if activity_type in ['Ki', 'Kd']:
        assert confidence == 0.9, \
            f"Ki/Kd should have confidence 0.9, got {confidence}"
    elif activity_type in ['IC50', 'EC50']:
        assert confidence == 0.8, \
            f"IC50/EC50 should have confidence 0.8, got {confidence}"
    else:
        assert confidence == 0.6, \
            f"Other types should have confidence 0.6, got {confidence}"


# Feature: drug-discovery-platform, Property 19: Composite Score Calculation
@given(
    binding_affinity=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    drug_likeness=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    toxicity_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
    novelty_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
)
def test_composite_score_calculation(binding_affinity, drug_likeness, toxicity_score, novelty_score):
    """Property 19: Composite Score Calculation
    
    For any drug candidate with binding affinity, drug-likeness, toxicity,
    and novelty scores, the system should calculate composite score as:
    0.40×binding + 0.30×drug_likeness + 0.20×(1-toxicity) + 0.10×novelty
    
    Validates: Requirements 7.8
    """
    composite = ScoringEngine.calculate_composite_score(
        binding_affinity,
        drug_likeness,
        toxicity_score,
        novelty_score
    )
    
    # Composite score should be in [0, 1]
    assert 0.0 <= composite <= 1.0, \
        f"Composite score {composite} not in [0, 1]"
    
    # Verify the formula
    expected = (
        0.40 * binding_affinity +
        0.30 * drug_likeness +
        0.20 * (1.0 - toxicity_score) +
        0.10 * novelty_score
    )
    
    assert abs(composite - expected) < 0.001, \
        f"Composite score {composite} doesn't match expected {expected}"
    
    # Verify weights sum to 1.0
    weights_sum = 0.40 + 0.30 + 0.20 + 0.10
    assert abs(weights_sum - 1.0) < 0.001, \
        f"Weights should sum to 1.0, got {weights_sum}"


# Feature: drug-discovery-platform, Property 20: Candidate Ranking
@given(
    candidates=st.lists(
        drug_candidate_strategy(),
        min_size=1,
        max_size=20
    )
)
def test_candidate_ranking(candidates):
    """Property 20: Candidate Ranking
    
    For any list of drug candidates with composite scores, the system
    should rank them in descending order by composite score.
    
    Validates: Requirements 7.9
    """
    # Rank the candidates
    ranked = ScoringEngine.rank_candidates(candidates)
    
    # Should return same number of candidates
    assert len(ranked) == len(candidates), \
        f"Expected {len(candidates)} candidates, got {len(ranked)}"
    
    # Ranks should be 1-based and sequential
    for i, candidate in enumerate(ranked, start=1):
        assert candidate.rank == i, \
            f"Candidate at position {i} should have rank {i}, got {candidate.rank}"
    
    # Composite scores should be in descending order
    for i in range(len(ranked) - 1):
        assert ranked[i].composite_score >= ranked[i + 1].composite_score, \
            f"Candidate {i} score {ranked[i].composite_score} < candidate {i+1} score {ranked[i+1].composite_score}"
    
    # All original candidates should be present
    original_ids = {c.molecule.chembl_id for c in candidates}
    ranked_ids = {c.molecule.chembl_id for c in ranked}
    assert original_ids == ranked_ids, \
        "Ranked candidates don't match original candidates"
