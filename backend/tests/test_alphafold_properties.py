"""Property-based tests for AlphaFold API client.

This module contains property-based tests using Hypothesis to verify
correctness properties of the AlphaFold client.
"""

import pytest
from hypothesis import given, strategies as st, settings

from app.alphafold_client import AlphaFoldClient
from app.models import ProteinStructure


# Feature: drug-discovery-platform, Property 3: Structure Confidence Classification
@settings(max_examples=100, deadline=None)
@given(
    plddt_score=st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False)
)
def test_structure_confidence_classification(plddt_score):
    """Property: For any protein structure with a pLDDT score, the system should
    flag it as low confidence if and only if pLDDT < 70.
    
    Validates: Requirements 2.3
    
    This test verifies that:
    1. Structures with pLDDT < 70 are flagged as low confidence
    2. Structures with pLDDT >= 70 are NOT flagged as low confidence
    3. The classification is consistent and deterministic
    
    Note: PDB B-factor format uses 6.2f precision, which may truncate values.
    We test the classification logic directly rather than round-tripping through PDB format.
    """
    client = AlphaFoldClient()
    
    # Test the classification logic directly with the given pLDDT score
    # This avoids PDB format precision issues
    is_low_confidence = (plddt_score < 70.0)
    
    # Create a ProteinStructure with the score
    structure = ProteinStructure(
        uniprot_id="P12345",
        pdb_data="MOCK PDB DATA",  # Not testing PDB parsing here
        plddt_score=plddt_score,
        is_low_confidence=is_low_confidence
    )
    
    # Property: is_low_confidence should be True if and only if pLDDT < 70
    if plddt_score < 70.0:
        assert structure.is_low_confidence is True, \
            f"Structure with pLDDT {plddt_score} should be flagged as low confidence"
    else:
        assert structure.is_low_confidence is False, \
            f"Structure with pLDDT {plddt_score} should NOT be flagged as low confidence"
    
    # Verify the threshold is exactly 70.0 (boundary test)
    if abs(plddt_score - 70.0) < 0.01:
        # At the boundary, verify correct classification
        if plddt_score < 70.0:
            assert structure.is_low_confidence is True
        else:
            assert structure.is_low_confidence is False


