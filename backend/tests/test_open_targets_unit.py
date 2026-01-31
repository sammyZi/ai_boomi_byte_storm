"""Unit tests for Open Targets API client.

This module contains unit tests for specific scenarios and edge cases
in the Open Targets client implementation.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.open_targets_client import OpenTargetsClient
from app.models import Target


class TestOpenTargetsClient:
    """Unit tests for OpenTargetsClient class."""
    
    @pytest.mark.asyncio
    async def test_get_disease_targets_success(self):
        """Test successful disease target retrieval with sample API response.
        
        Validates: Requirements 1.1, 1.2
        """
        client = OpenTargetsClient()
        
        # Mock disease search response
        disease_search_response = {
            "data": {
                "search": {
                    "hits": [
                        {
                            "id": "EFO_0000001",
                            "name": "Alzheimer's disease",
                            "entity": "disease"
                        }
                    ]
                }
            }
        }
        
        # Mock targets response
        targets_response = {
            "data": {
                "disease": {
                    "associatedTargets": {
                        "rows": [
                            {
                                "target": {
                                    "id": "ENSP00000000001",
                                    "approvedSymbol": "APOE",
                                    "approvedName": "Apolipoprotein E"
                                },
                                "score": 0.95
                            },
                            {
                                "target": {
                                    "id": "ENSP00000000002",
                                    "approvedSymbol": "APP",
                                    "approvedName": "Amyloid precursor protein"
                                },
                                "score": 0.87
                            },
                            {
                                "target": {
                                    "id": "ENSP00000000003",
                                    "approvedSymbol": "BACE1",
                                    "approvedName": "Beta-secretase 1"
                                },
                                "score": 0.72
                            }
                        ]
                    }
                }
            }
        }
        
        # Mock the HTTP client
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            # First call returns disease search, second returns targets
            mock_responses = [
                MagicMock(
                    json=lambda: disease_search_response,
                    raise_for_status=lambda: None
                ),
                MagicMock(
                    json=lambda: targets_response,
                    raise_for_status=lambda: None
                )
            ]
            mock_client.post = AsyncMock(side_effect=mock_responses)
            mock_client_class.return_value = mock_client
            
            # Execute
            result = await client.get_disease_targets("Alzheimer's disease")
            
            # Verify
            assert len(result) == 3
            assert result[0].gene_symbol == "APOE"
            assert result[0].confidence_score == 0.95
            assert result[1].gene_symbol == "APP"
            assert result[1].confidence_score == 0.87
            assert result[2].gene_symbol == "BACE1"
            assert result[2].confidence_score == 0.72
    
    @pytest.mark.asyncio
    async def test_get_disease_targets_not_found(self):
        """Test handling when disease is not found.
        
        Validates: Requirements 1.1, 1.2
        """
        client = OpenTargetsClient()
        
        # Mock empty disease search response
        disease_search_response = {
            "data": {
                "search": {
                    "hits": []
                }
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = AsyncMock(
                return_value=MagicMock(
                    json=lambda: disease_search_response,
                    raise_for_status=lambda: None
                )
            )
            mock_client_class.return_value = mock_client
            
            # Execute
            result = await client.get_disease_targets("NonexistentDisease123")
            
            # Verify - should return empty list
            assert result == []
    
    @pytest.mark.asyncio
    async def test_get_disease_targets_filters_low_confidence(self):
        """Test that targets with confidence < 0.5 are filtered out.
        
        Validates: Requirements 1.3, 1.4
        """
        client = OpenTargetsClient()
        
        disease_search_response = {
            "data": {
                "search": {
                    "hits": [{"id": "EFO_0000001", "name": "Test Disease"}]
                }
            }
        }
        
        targets_response = {
            "data": {
                "disease": {
                    "associatedTargets": {
                        "rows": [
                            {
                                "target": {
                                    "id": "ENSP00000000001",
                                    "approvedSymbol": "HIGH",
                                    "approvedName": "High confidence target"
                                },
                                "score": 0.85
                            },
                            {
                                "target": {
                                    "id": "ENSP00000000002",
                                    "approvedSymbol": "LOW",
                                    "approvedName": "Low confidence target"
                                },
                                "score": 0.35  # Below 0.5 threshold
                            },
                            {
                                "target": {
                                    "id": "ENSP00000000003",
                                    "approvedSymbol": "MEDIUM",
                                    "approvedName": "Medium confidence target"
                                },
                                "score": 0.55
                            }
                        ]
                    }
                }
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            mock_responses = [
                MagicMock(json=lambda: disease_search_response, raise_for_status=lambda: None),
                MagicMock(json=lambda: targets_response, raise_for_status=lambda: None)
            ]
            mock_client.post = AsyncMock(side_effect=mock_responses)
            mock_client_class.return_value = mock_client
            
            # Execute
            result = await client.get_disease_targets("Test Disease")
            
            # Verify - only targets with score >= 0.5 should be returned
            assert len(result) == 2
            assert result[0].gene_symbol == "HIGH"
            assert result[1].gene_symbol == "MEDIUM"
    
    @pytest.mark.asyncio
    async def test_get_disease_targets_limits_to_10(self):
        """Test that at most 10 targets are returned.
        
        Validates: Requirements 1.5
        """
        client = OpenTargetsClient()
        
        disease_search_response = {
            "data": {
                "search": {
                    "hits": [{"id": "EFO_0000001", "name": "Test Disease"}]
                }
            }
        }
        
        # Create 15 targets with varying confidence scores
        targets_rows = []
        for i in range(15):
            targets_rows.append({
                "target": {
                    "id": f"ENSP{i:011d}",
                    "approvedSymbol": f"GENE{i}",
                    "approvedName": f"Protein {i}"
                },
                "score": 0.95 - (i * 0.02)  # Descending scores
            })
        
        targets_response = {
            "data": {
                "disease": {
                    "associatedTargets": {
                        "rows": targets_rows
                    }
                }
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            mock_responses = [
                MagicMock(json=lambda: disease_search_response, raise_for_status=lambda: None),
                MagicMock(json=lambda: targets_response, raise_for_status=lambda: None)
            ]
            mock_client.post = AsyncMock(side_effect=mock_responses)
            mock_client_class.return_value = mock_client
            
            # Execute
            result = await client.get_disease_targets("Test Disease")
            
            # Verify - should return exactly 10 targets
            assert len(result) == 10
            # Verify they are the top 10 by confidence
            assert result[0].gene_symbol == "GENE0"
            assert result[9].gene_symbol == "GENE9"
    
    @pytest.mark.asyncio
    async def test_retry_logic_succeeds_after_failures(self):
        """Test that retry logic succeeds after initial failures.
        
        Validates: Requirements 1.6
        """
        client = OpenTargetsClient()
        
        call_count = 0
        success_response = {
            "data": {
                "search": {
                    "hits": [{"id": "EFO_0000001", "name": "Test"}]
                }
            }
        }
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("Timeout")
            return MagicMock(
                json=lambda: success_response,
                raise_for_status=lambda: None
            )
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post = mock_post
                mock_client_class.return_value = mock_client
                
                # Execute - should succeed on 3rd attempt
                result = await client._make_request_with_retry(
                    method="POST",
                    endpoint="/graphql",
                    json_data={"query": "test"}
                )
                
                # Verify
                assert result == success_response
                assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_retry_logic_fails_after_max_attempts(self):
        """Test that retry logic raises exception after all attempts fail.
        
        Validates: Requirements 1.7
        """
        client = OpenTargetsClient()
        
        call_count = 0
        
        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.TimeoutException("Timeout")
        
        with patch('asyncio.sleep', new_callable=AsyncMock):
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = None
                mock_client.post = mock_post
                mock_client_class.return_value = mock_client
                
                # Execute - should fail after 3 attempts
                with pytest.raises(httpx.TimeoutException):
                    await client._make_request_with_retry(
                        method="POST",
                        endpoint="/graphql",
                        json_data={"query": "test"}
                    )
                
                # Verify we made exactly 3 attempts
                assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_empty_disease_name_raises_error(self):
        """Test that empty disease name raises ValueError.
        
        Validates: Requirements 1.1
        """
        client = OpenTargetsClient()
        
        with pytest.raises(ValueError, match="Disease name cannot be empty"):
            await client.get_disease_targets("")
        
        with pytest.raises(ValueError, match="Disease name cannot be empty"):
            await client.get_disease_targets("   ")
    
    @pytest.mark.asyncio
    async def test_targets_sorted_by_confidence_descending(self):
        """Test that targets are sorted by confidence in descending order.
        
        Validates: Requirements 1.4
        """
        client = OpenTargetsClient()
        
        disease_search_response = {
            "data": {
                "search": {
                    "hits": [{"id": "EFO_0000001", "name": "Test"}]
                }
            }
        }
        
        # Targets in random order
        targets_response = {
            "data": {
                "disease": {
                    "associatedTargets": {
                        "rows": [
                            {
                                "target": {
                                    "id": "ENSP00000000001",
                                    "approvedSymbol": "MEDIUM",
                                    "approvedName": "Medium"
                                },
                                "score": 0.65
                            },
                            {
                                "target": {
                                    "id": "ENSP00000000002",
                                    "approvedSymbol": "HIGH",
                                    "approvedName": "High"
                                },
                                "score": 0.95
                            },
                            {
                                "target": {
                                    "id": "ENSP00000000003",
                                    "approvedSymbol": "LOW",
                                    "approvedName": "Low"
                                },
                                "score": 0.52
                            }
                        ]
                    }
                }
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            
            mock_responses = [
                MagicMock(json=lambda: disease_search_response, raise_for_status=lambda: None),
                MagicMock(json=lambda: targets_response, raise_for_status=lambda: None)
            ]
            mock_client.post = AsyncMock(side_effect=mock_responses)
            mock_client_class.return_value = mock_client
            
            # Execute
            result = await client.get_disease_targets("Test")
            
            # Verify sorted order
            assert len(result) == 3
            assert result[0].gene_symbol == "HIGH"
            assert result[0].confidence_score == 0.95
            assert result[1].gene_symbol == "MEDIUM"
            assert result[1].confidence_score == 0.65
            assert result[2].gene_symbol == "LOW"
            assert result[2].confidence_score == 0.52
