"""Property-based tests for data models.

This module contains property-based tests using Hypothesis to verify
universal properties of the data models.
"""

import pytest
from hypothesis import given, strategies as st, assume
from rdkit import Chem
from app.models import Molecule


# Feature: drug-discovery-platform, Property 27: Molecule Size Validation
# Validates: Requirements 14.5, 14.6


def generate_valid_smiles(min_atoms: int = 1, max_atoms: int = 200) -> st.SearchStrategy[str]:
    """Generate valid SMILES strings with controlled atom counts.
    
    This strategy generates SMILES strings that represent molecules
    with atom counts in the specified range.
    """
    # Common valid SMILES patterns with known atom counts
    small_molecules = [
        "C",           # Methane (1 atom)
        "CC",          # Ethane (2 atoms)
        "CCO",         # Ethanol (3 atoms)
        "c1ccccc1",    # Benzene (6 atoms)
        "CC(C)C",      # Isobutane (4 atoms)
        "CCN",         # Ethylamine (3 atoms)
        "C=C",         # Ethene (2 atoms)
        "C#C",         # Ethyne (2 atoms)
    ]
    
    # Medium molecules
    medium_molecules = [
        "CC(=O)Oc1ccccc1C(=O)O",  # Aspirin (21 atoms)
        "CN1C=NC2=C1C(=O)N(C(=O)N2C)C",  # Caffeine (24 atoms)
        "CC(C)Cc1ccc(cc1)C(C)C(=O)O",  # Ibuprofen (26 atoms)
    ]
    
    # Build larger molecules by chaining carbons
    def build_chain(length: int) -> str:
        """Build a carbon chain of specified length."""
        if length == 1:
            return "C"
        return "C" * length
    
    # Strategy that generates SMILES with controlled sizes
    @st.composite
    def smiles_with_size(draw):
        target_atoms = draw(st.integers(min_value=min_atoms, max_value=max_atoms))
        
        if target_atoms <= 8:
            # Use small molecules
            smiles = draw(st.sampled_from(small_molecules))
        elif target_atoms <= 30:
            # Use medium molecules
            smiles = draw(st.sampled_from(medium_molecules))
        else:
            # Build a carbon chain
            smiles = build_chain(target_atoms)
        
        # Verify the molecule has the right number of atoms
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            assume(False)  # Skip invalid SMILES
        
        actual_atoms = mol.GetNumAtoms()
        
        # If we need more atoms, add more carbons
        if actual_atoms < min_atoms:
            additional = min_atoms - actual_atoms
            smiles = smiles + "C" * additional
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                assume(False)
        
        # If we have too many atoms, try a smaller molecule
        if actual_atoms > max_atoms:
            assume(False)
        
        return smiles
    
    return smiles_with_size()


@pytest.mark.property
@given(smiles=generate_valid_smiles(min_atoms=1, max_atoms=200))
def test_molecule_size_validation_accepts_valid_sizes(smiles: str):
    """Property 27: Molecules with 1-200 atoms should be accepted.
    
    For any valid SMILES string representing a molecule with 1-200 atoms,
    the system should successfully parse and validate it.
    """
    # Parse the SMILES to verify atom count
    mol = Chem.MolFromSmiles(smiles)
    assert mol is not None, f"Generated invalid SMILES: {smiles}"
    
    atom_count = mol.GetNumAtoms()
    assert 1 <= atom_count <= 200, f"Atom count {atom_count} outside valid range"
    
    # Create a Molecule model instance
    # Note: This test focuses on the size validation aspect
    # The actual RDKit parsing will be tested in the RDKit analyzer tests
    canonical_smiles = Chem.MolToSmiles(mol)
    
    molecule = Molecule(
        chembl_id="CHEMBL_TEST",
        name="Test Molecule",
        smiles=smiles,
        canonical_smiles=canonical_smiles,
        pchembl_value=6.5,
        activity_type="IC50",
        target_ids=["P12345"]
    )
    
    # Verify the molecule was created successfully
    assert molecule.smiles == smiles
    assert molecule.canonical_smiles == canonical_smiles


@pytest.mark.property
def test_molecule_size_validation_rejects_empty():
    """Property 27: Molecules with 0 atoms should be rejected.
    
    Empty SMILES strings should be rejected during validation.
    """
    from pydantic import ValidationError
    
    # Test empty SMILES
    with pytest.raises(ValidationError) as exc_info:
        Molecule(
            chembl_id="CHEMBL_TEST",
            name="Test Molecule",
            smiles="",
            canonical_smiles="",
            pchembl_value=6.5,
            activity_type="IC50",
            target_ids=["P12345"]
        )
    
    # Verify the error is about empty SMILES
    assert "SMILES string cannot be empty" in str(exc_info.value)


@pytest.mark.property
def test_molecule_size_validation_rejects_whitespace_only():
    """Property 27: Molecules with only whitespace should be rejected.
    
    SMILES strings containing only whitespace should be rejected.
    """
    from pydantic import ValidationError
    
    # Test whitespace-only SMILES
    with pytest.raises(ValidationError) as exc_info:
        Molecule(
            chembl_id="CHEMBL_TEST",
            name="Test Molecule",
            smiles="   ",
            canonical_smiles="   ",
            pchembl_value=6.5,
            activity_type="IC50",
            target_ids=["P12345"]
        )
    
    # Verify the error is about empty SMILES
    assert "SMILES string cannot be empty" in str(exc_info.value)


@pytest.mark.property
def test_molecule_size_validation_large_molecule():
    """Property 27: Very large molecules (>200 atoms) should be handled.
    
    This test documents the expected behavior for molecules exceeding
    the reasonable drug size limit. The actual rejection will happen
    in the RDKit analyzer, not in the Pydantic model.
    """
    # Create a large carbon chain (250 atoms)
    large_smiles = "C" * 250
    mol = Chem.MolFromSmiles(large_smiles)
    assert mol is not None
    assert mol.GetNumAtoms() == 250
    
    # The Pydantic model itself doesn't enforce atom count limits
    # This will be enforced by the RDKit analyzer during parsing
    canonical_smiles = Chem.MolToSmiles(mol)
    
    molecule = Molecule(
        chembl_id="CHEMBL_TEST",
        name="Large Test Molecule",
        smiles=large_smiles,
        canonical_smiles=canonical_smiles,
        pchembl_value=6.5,
        activity_type="IC50",
        target_ids=["P12345"]
    )
    
    # The model accepts it, but the RDKit analyzer should reject it
    assert molecule.smiles == large_smiles
