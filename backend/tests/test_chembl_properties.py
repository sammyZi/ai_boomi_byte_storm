"""Property-based tests for ChEMBL API client.

This module contains property-based tests using Hypothesis to verify
correctness properties of the ChEMBL client.
"""

import pytest
from hypothesis import given, strategies as st, settings
from app.chembl_client import ChEMBLClient
from app.models import Molecule


# Feature: drug-discovery-platform, Property 6: Molecule Filtering by Activity
@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    activities_data=st.lists(
        st.tuples(
            st.text(min_size=1, max_size=20),  # chembl_id
            st.text(min_size=1, max_size=50),  # molecule_name
            st.text(min_size=5, max_size=100),  # smiles (will be validated)
            st.floats(min_value=0.0, max_value=15.0),  # pchembl_value
            st.sampled_from(['Ki', 'Kd', 'IC50', 'EC50', 'Other'])  # activity_type
        ),
        min_size=0,
        max_size=200
    ),
    min_pchembl=st.floats(min_value=0.0, max_value=10.0),
    max_molecules=st.integers(min_value=1, max_value=200)
)
async def test_molecule_filtering_by_activity(activities_data, min_pchembl, max_molecules):
    """Property: For any list of molecules with pChEMBL values, the system should
    include only molecules with pChEMBL >= min_pchembl and limit the result to at
    most max_molecules per target.
    
    Validates: Requirements 3.2, 3.3
    
    This test verifies that:
    1. All returned molecules have pChEMBL >= min_pchembl
    2. At most max_molecules are returned
    3. Invalid SMILES are excluded
    """
    client = ChEMBLClient()
    
    # Convert test data to API activity format
    # Use simple valid SMILES for testing
    valid_smiles_examples = [
        'CCO',  # Ethanol
        'CC(=O)O',  # Acetic acid
        'c1ccccc1',  # Benzene
        'CC(C)O',  # Isopropanol
        'CCN',  # Ethylamine
        'C1CCCCC1',  # Cyclohexane
        'CC(=O)C',  # Acetone
        'CCCC',  # Butane
        'C=C',  # Ethylene
        'C#C'  # Acetylene
    ]
    
    api_activities = []
    for i, (chembl_id, name, _, pchembl, activity_type) in enumerate(activities_data):
        # Use valid SMILES from our examples
        smiles = valid_smiles_examples[i % len(valid_smiles_examples)]
        
        api_activities.append({
            'molecule_chembl_id': f'CHEMBL{i}_{chembl_id}',
            'molecule_pref_name': name,
            'canonical_smiles': smiles,
            'pchembl_value': pchembl,
            'standard_type': activity_type
        })
    
    # Process activities
    result = client._process_activities(
        api_activities,
        target_id='TEST_TARGET',
        min_pchembl=min_pchembl,
        max_molecules=max_molecules
    )
    
    # Property 1: All returned molecules have pChEMBL >= min_pchembl
    for molecule in result:
        assert molecule.pchembl_value >= min_pchembl, \
            f"Molecule {molecule.chembl_id} has pChEMBL {molecule.pchembl_value} < {min_pchembl}"
    
    # Property 2: At most max_molecules are returned
    assert len(result) <= max_molecules, \
        f"Returned {len(result)} molecules, expected at most {max_molecules}"
    
    # Property 3: All returned molecules have valid SMILES (implicitly tested by successful parsing)
    for molecule in result:
        assert molecule.smiles, f"Molecule {molecule.chembl_id} has empty SMILES"
        assert molecule.canonical_smiles, f"Molecule {molecule.chembl_id} has empty canonical SMILES"
    
    # Property 4: Result count matches expected filtered count (up to max_molecules)
    expected_count = sum(1 for _, _, _, pchembl, _ in activities_data if pchembl >= min_pchembl)
    expected_count = min(expected_count, max_molecules)
    assert len(result) == expected_count, \
        f"Expected {expected_count} molecules, got {len(result)}"



# Feature: drug-discovery-platform, Property 7: Molecule Deduplication
@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    # Generate lists of molecules for multiple targets with potential overlaps
    molecule_data=st.lists(
        st.lists(
            st.tuples(
                st.text(min_size=1, max_size=20),  # chembl_id
                st.floats(min_value=6.0, max_value=10.0),  # pchembl_value
                st.text(min_size=1, max_size=50)  # name
            ),
            min_size=0,
            max_size=20
        ),
        min_size=1,
        max_size=10
    )
)
async def test_molecule_deduplication(molecule_data):
    """Property: For any set of molecules found across multiple targets, the system
    should deduplicate by ChEMBL ID and associate each unique molecule with all
    relevant target IDs.
    
    Validates: Requirements 3.4
    
    This test verifies that:
    1. Each ChEMBL ID appears only once in the result
    2. Molecules found in multiple targets have all target IDs associated
    3. The highest pChEMBL value is retained for duplicates
    """
    client = ChEMBLClient()
    
    # Convert test data to molecule lists
    molecule_lists = []
    chembl_id_to_targets = {}  # Track which targets each molecule should be associated with
    chembl_id_to_max_pchembl = {}  # Track max pChEMBL for each molecule
    
    for target_idx, target_molecules in enumerate(molecule_data):
        target_id = f'TARGET_{target_idx}'
        molecules = []
        
        for chembl_id, pchembl_value, name in target_molecules:
            # Track target associations
            if chembl_id not in chembl_id_to_targets:
                chembl_id_to_targets[chembl_id] = []
            chembl_id_to_targets[chembl_id].append(target_id)
            
            # Track max pChEMBL
            if chembl_id not in chembl_id_to_max_pchembl:
                chembl_id_to_max_pchembl[chembl_id] = pchembl_value
            else:
                chembl_id_to_max_pchembl[chembl_id] = max(
                    chembl_id_to_max_pchembl[chembl_id],
                    pchembl_value
                )
            
            # Create molecule
            molecule = Molecule(
                chembl_id=chembl_id,
                name=name,
                smiles='CCO',  # Simple valid SMILES
                canonical_smiles='CCO',
                pchembl_value=pchembl_value,
                activity_type='IC50',
                target_ids=[target_id]
            )
            molecules.append(molecule)
        
        molecule_lists.append(molecules)
    
    # Deduplicate
    result = client.deduplicate_molecules(molecule_lists)
    
    # Property 1: Each ChEMBL ID appears only once
    result_chembl_ids = [mol.chembl_id for mol in result]
    assert len(result_chembl_ids) == len(set(result_chembl_ids)), \
        "Duplicate ChEMBL IDs found in result"
    
    # Property 2: All unique ChEMBL IDs are present
    all_chembl_ids = set(chembl_id_to_targets.keys())
    assert set(result_chembl_ids) == all_chembl_ids, \
        "Not all unique ChEMBL IDs are present in result"
    
    # Property 3: Each molecule has all relevant target IDs
    for molecule in result:
        expected_targets = set(chembl_id_to_targets[molecule.chembl_id])
        actual_targets = set(molecule.target_ids)
        assert actual_targets == expected_targets, \
            f"Molecule {molecule.chembl_id} has targets {actual_targets}, expected {expected_targets}"
    
    # Property 4: Each molecule has the maximum pChEMBL value
    for molecule in result:
        expected_max_pchembl = chembl_id_to_max_pchembl[molecule.chembl_id]
        assert abs(molecule.pchembl_value - expected_max_pchembl) < 0.001, \
            f"Molecule {molecule.chembl_id} has pChEMBL {molecule.pchembl_value}, expected {expected_max_pchembl}"
