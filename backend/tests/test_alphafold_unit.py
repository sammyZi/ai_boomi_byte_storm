"""Unit tests for AlphaFold API client.

This module contains unit tests for specific scenarios and edge cases
in the AlphaFold client implementation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.alphafold_client import AlphaFoldClient
from app.models import ProteinStructure


class TestAlphaFoldClient:
    """Unit tests for AlphaFoldClient class."""
    
    @pytest.mark.asyncio
    async def test_get_protein_structure_success(self):
        """Test successful protein structure retrieval with sample PDB data.
        
        Validates: Requirements 2.1, 2.2
        """
        client = AlphaFoldClient()
        
        # Sample PDB data with pLDDT scores in B-factor column
        sample_pdb = """HEADER    PROTEIN                                 01-JAN-20   XXXX
ATOM      1  N   MET A   1      10.000  10.000  10.000  1.00 85.50           N
ATOM      2  CA  MET A   1      11.000  10.000  10.000  1.00 87.20           C
ATOM      3  C   MET A   1      12.000  10.000  10.000  1.00 88.10           C
ATOM      4  O   MET A   1      13.000  10.000  10.000  1.00 86.30           O
END
"""
        
        # Mock API responses
        prediction_response = [
            {
                "entryId": "AF-P12345-F1",
                "gene": "TEST",
                "uniprotAccession": "P12345",
                "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P12345-F1-model_v4.pdb"
            }
        ]
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            # First call returns prediction info, second returns PDB file
            mock_responses = [
                MagicMock(
                    status_code=200,
                    json=lambda: prediction_response,
                    raise_for_status=lambda: None
                ),
                MagicMock(
                    status_code=200,
                    text=sample_pdb,
                    raise_for_status=lambda: None
                )
            ]
            mock_client.get = AsyncMock(side_effect=mock_responses)
            mock_client_class.return_value = mock_client
            
            # Mock cache to avoid Redis dependency
            with patch('app.alphafold_client.cache') as mock_cache:
                mock_cache.get = AsyncMock(return_value=None)
                mock_cache.set = AsyncMock(return_value=True)
                
                # Execute
                result = await client.get_protein_structure("P12345")
                
                # Verify
                assert result is not None
                assert isinstance(result, ProteinStructure)
                assert result.uniprot_id == "P12345"
                assert result.pdb_data == sample_pdb
                # Average pLDDT: (85.50 + 87.20 + 88.10 + 86.30) / 4 = 86.775
                assert 86.0 < result.plddt_score < 87.5
                assert result.is_low_confidence is False  # pLDDT > 70
    
    @pytest.mark.asyncio
    async def test_get_protein_structure_low_confidence(self):
        """Test structure with low confidence (pLDDT < 70).
        
        Validates: Requirements 2.3
        """
        client = AlphaFoldClient()
        
        # PDB data with low pLDDT scores
        low_confidence_pdb = """HEADER    PROTEIN
ATOM      1  N   MET A   1      10.000  10.000  10.000  1.00 45.50           N
ATOM      2  CA  MET A   1      11.000  10.000  10.000  1.00 52.20           C
ATOM      3  C   MET A   1      12.000  10.000  10.000  1.00 48.10           C
END
"""
        
        prediction_response = [
            {
                "entryId": "AF-Q99999-F1",
                "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-Q99999-F1-model_v4.pdb"
            }
        ]
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            mock_responses = [
                MagicMock(status_code=200, json=lambda: prediction_response, raise_for_status=lambda: None),
                MagicMock(status_code=200, text=low_confidence_pdb, raise_for_status=lambda: None)
            ]
            mock_client.get = AsyncMock(side_effect=mock_responses)
            mock_client_class.return_value = mock_client
            
            with patch('app.alphafold_client.cache') as mock_cache:
                mock_cache.get = AsyncMock(return_value=None)
                mock_cache.set = AsyncMock(return_value=True)
                
                # Execute
                result = await client.get_protein_structure("Q99999")
                
                # Verify
                assert result is not None
                assert result.plddt_score < 70.0
                assert result.is_low_confidence is True
    
    @pytest.mark.asyncio
    async def test_get_protein_structure_not_found(self):
        """Test handling when structure is not available (404).
        
        Validates: Requirements 2.5
        """
        client = AlphaFoldClient()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            # Mock 404 response
            mock_response = MagicMock(status_code=404)
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found",
                request=MagicMock(),
                response=mock_response
            )
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            with patch('app.alphafold_client.cache') as mock_cache:
                mock_cache.get = AsyncMock(return_value=None)
                
                # Execute
                result = await client.get_protein_structure("NOTFOUND")
                
                # Verify - should return None gracefully
                assert result is None
    
    @pytest.mark.asyncio
    async def test_get_protein_structure_timeout(self):
        """Test handling of timeout (10 seconds).
        
        Validates: Requirements 2.6
        """
        client = AlphaFoldClient()
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            # Mock timeout exception
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
            mock_client_class.return_value = mock_client
            
            with patch('app.alphafold_client.cache') as mock_cache:
                mock_cache.get = AsyncMock(return_value=None)
                
                # Execute
                result = await client.get_protein_structure("P12345")
                
                # Verify - should return None gracefully
                assert result is None
    
    @pytest.mark.asyncio
    async def test_get_protein_structure_uses_cache(self):
        """Test that cached structures are returned without API calls.
        
        Validates: Requirements 2.4
        """
        client = AlphaFoldClient()
        
        # Cached structure data
        cached_structure = {
            "uniprot_id": "P12345",
            "pdb_data": "CACHED PDB DATA",
            "plddt_score": 85.5,
            "is_low_confidence": False
        }
        
        with patch('app.alphafold_client.cache') as mock_cache:
            mock_cache.get = AsyncMock(return_value=cached_structure)
            
            # Execute
            result = await client.get_protein_structure("P12345")
            
            # Verify
            assert result is not None
            assert result.uniprot_id == "P12345"
            assert result.pdb_data == "CACHED PDB DATA"
            assert result.plddt_score == 85.5
            
            # Verify cache was checked
            mock_cache.get.assert_called_once_with("af:structure:P12345")
    
    @pytest.mark.asyncio
    async def test_get_protein_structure_caches_result(self):
        """Test that fetched structures are cached with 24-hour TTL.
        
        Validates: Requirements 2.4
        """
        client = AlphaFoldClient()
        
        sample_pdb = "ATOM      1  CA  ALA A   1      10.000  10.000  10.000  1.00 85.00           C\n"
        
        prediction_response = [
            {
                "entryId": "AF-P12345-F1",
                "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P12345-F1-model_v4.pdb"
            }
        ]
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            mock_responses = [
                MagicMock(status_code=200, json=lambda: prediction_response, raise_for_status=lambda: None),
                MagicMock(status_code=200, text=sample_pdb, raise_for_status=lambda: None)
            ]
            mock_client.get = AsyncMock(side_effect=mock_responses)
            mock_client_class.return_value = mock_client
            
            with patch('app.alphafold_client.cache') as mock_cache:
                mock_cache.get = AsyncMock(return_value=None)
                mock_cache.set = AsyncMock(return_value=True)
                
                # Execute
                result = await client.get_protein_structure("P12345")
                
                # Verify cache.set was called with correct TTL
                assert mock_cache.set.called
                call_args = mock_cache.set.call_args
                assert call_args[0][0] == "af:structure:P12345"
                assert call_args[1]["ttl"] == 86400  # 24 hours
    
    @pytest.mark.asyncio
    async def test_empty_uniprot_id_returns_none(self):
        """Test that empty UniProt ID returns None.
        
        Validates: Requirements 2.1
        """
        client = AlphaFoldClient()
        
        # Test empty string
        result = await client.get_protein_structure("")
        assert result is None
        
        # Test whitespace
        result = await client.get_protein_structure("   ")
        assert result is None
    
    def test_parse_plddt_from_pdb(self):
        """Test PDB parsing extracts correct pLDDT scores.
        
        Validates: Requirements 2.2
        """
        client = AlphaFoldClient()
        
        # PDB with known pLDDT scores
        pdb_data = """HEADER    TEST
ATOM      1  N   ALA A   1      10.000  10.000  10.000  1.00 90.00           N
ATOM      2  CA  ALA A   1      11.000  10.000  10.000  1.00 85.00           C
ATOM      3  C   ALA A   1      12.000  10.000  10.000  1.00 80.00           C
ATOM      4  O   ALA A   1      13.000  10.000  10.000  1.00 75.00           O
END
"""
        
        # Parse
        plddt = client._parse_plddt_from_pdb(pdb_data)
        
        # Verify average: (90 + 85 + 80 + 75) / 4 = 82.5
        assert 82.0 < plddt < 83.0
    
    def test_parse_plddt_from_empty_pdb(self):
        """Test PDB parsing handles empty or invalid PDB data.
        
        Validates: Requirements 2.2
        """
        client = AlphaFoldClient()
        
        # Empty PDB
        plddt = client._parse_plddt_from_pdb("")
        assert plddt == 0.0
        
        # PDB with no ATOM records
        plddt = client._parse_plddt_from_pdb("HEADER    TEST\nEND\n")
        assert plddt == 0.0
    
    def test_parse_plddt_boundary_at_70(self):
        """Test confidence classification at the 70.0 boundary.
        
        Validates: Requirements 2.3
        """
        client = AlphaFoldClient()
        
        # Exactly 70.0
        pdb_70 = "ATOM      1  CA  ALA A   1      10.000  10.000  10.000  1.00 70.00           C\n"
        plddt_70 = client._parse_plddt_from_pdb(pdb_70)
        assert 69.5 < plddt_70 <= 70.5
        
        # Just below 70.0
        pdb_69 = "ATOM      1  CA  ALA A   1      10.000  10.000  10.000  1.00 69.99           C\n"
        plddt_69 = client._parse_plddt_from_pdb(pdb_69)
        assert plddt_69 < 70.0
        
        # Just above 70.0
        pdb_71 = "ATOM      1  CA  ALA A   1      10.000  10.000  10.000  1.00 70.01           C\n"
        plddt_71 = client._parse_plddt_from_pdb(pdb_71)
        assert plddt_71 > 70.0

