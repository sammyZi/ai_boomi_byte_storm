"""Unit tests for ChEMBL API client.

This module contains unit tests for specific scenarios and edge cases
in the ChEMBL client implementation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.chembl_client import ChEMBLClient
from app.models import Molecule


class TestChEMBLClient:
    """Unit tests for ChEMBLClient class."""
    
    @pytest.mark.asyncio
    async def test_molecule_filtering_by_pchembl(self):
        """Test that molecules are filtered by pChEMBL >= 6.0.
        
        Validates: Requirements 3.2
        """
        client = ChEMBLClient()
        
        # Sample activities with varying pChEMBL values
        activities = [
            {
                'molecule_chembl_id': 'CHEMBL1',
                'molecule_pref_name': 'High Activity',
                'canonical_smiles': 'CCO',
                'pchembl_value': 8.5,
                'standard_type': 'IC50'
            },
            {
                'molecule_chembl_id': 'CHEMBL2',
                'molecule_pref_name': 'Low Activity',
                'canonical_smiles': 'CC(=O)O',
                'pchembl_value': 5.0,  # Below threshold
                'standard_type': 'IC50'
            },
            {
                'molecule_chembl_id': 'CHEMBL3',
                'molecule_pref_name': 'Medium Activity',
                'canonical_smiles': 'c1ccccc1',
                'pchembl_value': 6.5,
                'standard_type': 'Ki'
            }
        ]
        
        # Process activities
        result = client._process_activities(
            activities,
            target_id='TEST_TARGET',
            min_pchembl=6.0,
            max_molecules=100
        )
        
        # Verify only molecules with pChEMBL >= 6.0 are returned
        assert len(result) == 2
        assert result[0].chembl_id == 'CHEMBL1'
        assert result[0].pchembl_value == 8.5
        assert result[1].chembl_id == 'CHEMBL3'
        assert result[1].pchembl_value == 6.5
    
    @pytest.mark.asyncio
    async def test_molecule_limit_enforced(self):
        """Test that at most max_molecules are returned.
        
        Validates: Requirements 3.3
        """
        client = ChEMBLClient()
        
        # Create 10 activities
        activities = []
        for i in range(10):
            activities.append({
                'molecule_chembl_id': f'CHEMBL{i}',
                'molecule_pref_name': f'Molecule {i}',
                'canonical_smiles': 'CCO',
                'pchembl_value': 7.0 + i * 0.1,
                'standard_type': 'IC50'
            })
        
        # Process with limit of 5
        result = client._process_activities(
            activities,
            target_id='TEST_TARGET',
            min_pchembl=6.0,
            max_molecules=5
        )
        
        # Verify exactly 5 molecules returned
        assert len(result) == 5
    
    @pytest.mark.asyncio
    async def test_invalid_smiles_excluded(self):
        """Test that molecules with invalid SMILES are excluded.
        
        Validates: Requirements 3.5, 3.6
        """
        client = ChEMBLClient()
        
        activities = [
            {
                'molecule_chembl_id': 'CHEMBL1',
                'molecule_pref_name': 'Valid Molecule',
                'canonical_smiles': 'CCO',
                'pchembl_value': 7.0,
                'standard_type': 'IC50'
            },
            {
                'molecule_chembl_id': 'CHEMBL2',
                'molecule_pref_name': 'Invalid Molecule',
                'canonical_smiles': 'INVALID_SMILES_XYZ',
                'pchembl_value': 8.0,
                'standard_type': 'IC50'
            },
            {
                'molecule_chembl_id': 'CHEMBL3',
                'molecule_pref_name': 'Another Valid',
                'canonical_smiles': 'c1ccccc1',
                'pchembl_value': 7.5,
                'standard_type': 'Ki'
            }
        ]
        
        # Process activities
        result = client._process_activities(
            activities,
            target_id='TEST_TARGET',
            min_pchembl=6.0,
            max_molecules=100
        )
        
        # Verify only valid SMILES are included
        assert len(result) == 2
        assert result[0].chembl_id == 'CHEMBL1'
        assert result[1].chembl_id == 'CHEMBL3'
    
    @pytest.mark.asyncio
    async def test_deduplication_merges_targets(self):
        """Test that deduplication merges target IDs for the same molecule.
        
        Validates: Requirements 3.4
        """
        client = ChEMBLClient()
        
        # Create molecule lists with overlapping molecules
        molecules_target1 = [
            Molecule(
                chembl_id='CHEMBL1',
                name='Shared Molecule',
                smiles='CCO',
                canonical_smiles='CCO',
                pchembl_value=7.0,
                activity_type='IC50',
                target_ids=['TARGET1']
            ),
            Molecule(
                chembl_id='CHEMBL2',
                name='Unique to Target1',
                smiles='CC(=O)O',
                canonical_smiles='CC(=O)O',
                pchembl_value=6.5,
                activity_type='Ki',
                target_ids=['TARGET1']
            )
        ]
        
        molecules_target2 = [
            Molecule(
                chembl_id='CHEMBL1',
                name='Shared Molecule',
                smiles='CCO',
                canonical_smiles='CCO',
                pchembl_value=7.5,  # Higher pChEMBL
                activity_type='IC50',
                target_ids=['TARGET2']
            ),
            Molecule(
                chembl_id='CHEMBL3',
                name='Unique to Target2',
                smiles='c1ccccc1',
                canonical_smiles='c1ccccc1',
                pchembl_value=8.0,
                activity_type='Kd',
                target_ids=['TARGET2']
            )
        ]
        
        # Deduplicate
        result = client.deduplicate_molecules([molecules_target1, molecules_target2])
        
        # Verify results
        assert len(result) == 3
        
        # Find CHEMBL1 in results
        chembl1 = next(m for m in result if m.chembl_id == 'CHEMBL1')
        assert set(chembl1.target_ids) == {'TARGET1', 'TARGET2'}
        assert chembl1.pchembl_value == 7.5  # Should keep higher value
        
        # Verify unique molecules
        chembl2 = next(m for m in result if m.chembl_id == 'CHEMBL2')
        assert chembl2.target_ids == ['TARGET1']
        
        chembl3 = next(m for m in result if m.chembl_id == 'CHEMBL3')
        assert chembl3.target_ids == ['TARGET2']
    
    @pytest.mark.asyncio
    async def test_deduplication_keeps_max_pchembl(self):
        """Test that deduplication keeps the maximum pChEMBL value.
        
        Validates: Requirements 3.4, 4.5
        """
        client = ChEMBLClient()
        
        # Create same molecule with different pChEMBL values
        molecules_list1 = [
            Molecule(
                chembl_id='CHEMBL1',
                name='Test Molecule',
                smiles='CCO',
                canonical_smiles='CCO',
                pchembl_value=6.5,
                activity_type='IC50',
                target_ids=['TARGET1']
            )
        ]
        
        molecules_list2 = [
            Molecule(
                chembl_id='CHEMBL1',
                name='Test Molecule',
                smiles='CCO',
                canonical_smiles='CCO',
                pchembl_value=8.2,  # Higher
                activity_type='Ki',
                target_ids=['TARGET2']
            )
        ]
        
        molecules_list3 = [
            Molecule(
                chembl_id='CHEMBL1',
                name='Test Molecule',
                smiles='CCO',
                canonical_smiles='CCO',
                pchembl_value=7.0,  # Middle
                activity_type='Kd',
                target_ids=['TARGET3']
            )
        ]
        
        # Deduplicate
        result = client.deduplicate_molecules([molecules_list1, molecules_list2, molecules_list3])
        
        # Verify
        assert len(result) == 1
        assert result[0].pchembl_value == 8.2  # Maximum value
        assert result[0].activity_type == 'Ki'  # From the max pChEMBL entry
        assert set(result[0].target_ids) == {'TARGET1', 'TARGET2', 'TARGET3'}
    
    @pytest.mark.asyncio
    async def test_empty_target_id_returns_empty_list(self):
        """Test that empty target ID returns empty list.
        
        Validates: Requirements 3.1
        """
        client = ChEMBLClient()
        
        result = await client.get_bioactive_molecules("")
        assert result == []
        
        result = await client.get_bioactive_molecules("   ")
        assert result == []
    
    @pytest.mark.asyncio
    async def test_missing_pchembl_value_skipped(self):
        """Test that activities without pChEMBL values are skipped.
        
        Validates: Requirements 3.2
        """
        client = ChEMBLClient()
        
        activities = [
            {
                'molecule_chembl_id': 'CHEMBL1',
                'molecule_pref_name': 'Valid',
                'canonical_smiles': 'CCO',
                'pchembl_value': 7.0,
                'standard_type': 'IC50'
            },
            {
                'molecule_chembl_id': 'CHEMBL2',
                'molecule_pref_name': 'No pChEMBL',
                'canonical_smiles': 'CC(=O)O',
                'pchembl_value': None,  # Missing
                'standard_type': 'IC50'
            },
            {
                'molecule_chembl_id': 'CHEMBL3',
                'molecule_pref_name': 'Another Valid',
                'canonical_smiles': 'c1ccccc1',
                'pchembl_value': 6.5,
                'standard_type': 'Ki'
            }
        ]
        
        result = client._process_activities(
            activities,
            target_id='TEST_TARGET',
            min_pchembl=6.0,
            max_molecules=100
        )
        
        # Only molecules with pChEMBL values should be included
        assert len(result) == 2
        assert result[0].chembl_id == 'CHEMBL1'
        assert result[1].chembl_id == 'CHEMBL3'
    
    @pytest.mark.asyncio
    async def test_missing_smiles_skipped(self):
        """Test that activities without SMILES are skipped.
        
        Validates: Requirements 3.5
        """
        client = ChEMBLClient()
        
        activities = [
            {
                'molecule_chembl_id': 'CHEMBL1',
                'molecule_pref_name': 'Valid',
                'canonical_smiles': 'CCO',
                'pchembl_value': 7.0,
                'standard_type': 'IC50'
            },
            {
                'molecule_chembl_id': 'CHEMBL2',
                'molecule_pref_name': 'No SMILES',
                'canonical_smiles': None,  # Missing
                'pchembl_value': 8.0,
                'standard_type': 'IC50'
            }
        ]
        
        result = client._process_activities(
            activities,
            target_id='TEST_TARGET',
            min_pchembl=6.0,
            max_molecules=100
        )
        
        # Only molecules with SMILES should be included
        assert len(result) == 1
        assert result[0].chembl_id == 'CHEMBL1'
    
    @pytest.mark.asyncio
    async def test_duplicate_chembl_ids_in_same_target_skipped(self):
        """Test that duplicate ChEMBL IDs within the same target are skipped.
        
        Validates: Requirements 3.4
        """
        client = ChEMBLClient()
        
        activities = [
            {
                'molecule_chembl_id': 'CHEMBL1',
                'molecule_pref_name': 'First occurrence',
                'canonical_smiles': 'CCO',
                'pchembl_value': 7.0,
                'standard_type': 'IC50'
            },
            {
                'molecule_chembl_id': 'CHEMBL1',  # Duplicate
                'molecule_pref_name': 'Second occurrence',
                'canonical_smiles': 'CCO',
                'pchembl_value': 8.0,
                'standard_type': 'Ki'
            },
            {
                'molecule_chembl_id': 'CHEMBL2',
                'molecule_pref_name': 'Different molecule',
                'canonical_smiles': 'c1ccccc1',
                'pchembl_value': 6.5,
                'standard_type': 'Kd'
            }
        ]
        
        result = client._process_activities(
            activities,
            target_id='TEST_TARGET',
            min_pchembl=6.0,
            max_molecules=100
        )
        
        # Only unique ChEMBL IDs should be included
        assert len(result) == 2
        assert result[0].chembl_id == 'CHEMBL1'
        assert result[1].chembl_id == 'CHEMBL2'
