"""Property-based tests for Open Targets API client.

This module contains property-based tests using Hypothesis to verify
correctness properties of the Open Targets client.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from hypothesis import given, strategies as st, settings
import httpx

from app.open_targets_client import OpenTargetsClient
from app.models import Target


# Feature: drug-discovery-platform, Property 2: Retry with Exponential Backoff
@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    num_failures=st.integers(min_value=1, max_value=3),
    endpoint=st.sampled_from(["/graphql", "/api/targets", "/api/diseases"])
)
async def test_retry_with_exponential_backoff(num_failures, endpoint):
    """Property: For any failed API request, the system should retry up to 3 times
    with exponentially increasing delays (1s, 2s, 4s) before giving up.
    
    Validates: Requirements 1.6
    
    This test verifies that:
    1. The client retries exactly the expected number of times
    2. Delays between retries follow exponential backoff pattern (1s, 2s, 4s)
    3. The last exception is raised after all retries are exhausted
    """
    client = OpenTargetsClient()
    
    # Track sleep calls to verify exponential backoff
    sleep_calls = []
    
    async def mock_sleep(delay):
        sleep_calls.append(delay)
    
    # Create a mock that fails num_failures times
    call_count = 0
    
    async def mock_request(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count <= num_failures:
            raise httpx.TimeoutException("Timeout")
        return MagicMock(json=lambda: {"data": {}}, raise_for_status=lambda: None)
    
    with patch('asyncio.sleep', side_effect=mock_sleep):
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post = mock_request
            mock_client.get = mock_request
            mock_client_class.return_value = mock_client
            
            if num_failures < 3:
                # Should succeed after num_failures attempts
                result = await client._make_request_with_retry(
                    method="POST",
                    endpoint=endpoint,
                    json_data={"query": "test"}
                )
                
                # Verify we made num_failures + 1 attempts (failures + success)
                assert call_count == num_failures + 1
                
                # Verify exponential backoff delays
                expected_delays = [1.0, 2.0, 4.0][:num_failures]
                assert sleep_calls == expected_delays
            else:
                # Should fail after 3 attempts
                with pytest.raises(httpx.TimeoutException):
                    await client._make_request_with_retry(
                        method="POST",
                        endpoint=endpoint,
                        json_data={"query": "test"}
                    )
                
                # Verify we made exactly 3 attempts
                assert call_count == 3
                
                # Verify exponential backoff delays (only 2 delays for 3 attempts)
                expected_delays = [1.0, 2.0]
                assert sleep_calls == expected_delays


# Feature: drug-discovery-platform, Property 1: Target Filtering and Ranking
@pytest.mark.asyncio
@settings(max_examples=100, deadline=None)
@given(
    targets_data=st.lists(
        st.tuples(
            st.text(min_size=1, max_size=20),  # gene_symbol
            st.text(min_size=1, max_size=50),  # protein_name
            st.floats(min_value=0.0, max_value=1.0)  # confidence_score
        ),
        min_size=0,
        max_size=50
    ),
    min_confidence=st.floats(min_value=0.0, max_value=1.0)
)
async def test_target_filtering_and_ranking(targets_data, min_confidence):
    """Property: For any list of protein targets with confidence scores, the system
    should filter out targets with confidence < min_confidence, sort the remaining
    targets by confidence in descending order, and limit the result to at most 10 targets.
    
    Validates: Requirements 1.3, 1.4, 1.5
    
    This test verifies that:
    1. All returned targets have confidence >= min_confidence (and >= 0.5 per model constraint)
    2. Targets are sorted by confidence in descending order
    3. At most 10 targets are returned
    """
    client = OpenTargetsClient()
    
    # Convert test data to API format
    api_targets = []
    for i, (gene_symbol, protein_name, score) in enumerate(targets_data):
        api_targets.append({
            "target": {
                "id": f"ENSP{i:011d}",
                "approvedSymbol": gene_symbol,
                "approvedName": protein_name
            },
            "score": score
        })
    
    # Apply filtering and ranking
    result = client._filter_and_rank_targets(
        api_targets,
        min_confidence=min_confidence,
        max_targets=10
    )
    
    # The effective minimum confidence is max(min_confidence, 0.5) due to Target model validation
    effective_min_confidence = max(min_confidence, 0.5)
    
    # Property 1: All returned targets have confidence >= effective_min_confidence
    for target in result:
        assert target.confidence_score >= effective_min_confidence, \
            f"Target {target.gene_symbol} has confidence {target.confidence_score} < {effective_min_confidence}"
    
    # Property 2: Targets are sorted by confidence in descending order
    for i in range(len(result) - 1):
        assert result[i].confidence_score >= result[i + 1].confidence_score, \
            f"Targets not sorted: {result[i].confidence_score} < {result[i + 1].confidence_score}"
    
    # Property 3: At most 10 targets are returned
    assert len(result) <= 10, f"Returned {len(result)} targets, expected at most 10"
    
    # Property 4: Result count matches expected filtered count (up to 10)
    expected_count = sum(1 for _, _, score in targets_data if score >= effective_min_confidence)
    expected_count = min(expected_count, 10)
    assert len(result) == expected_count, \
        f"Expected {expected_count} targets, got {len(result)}"
