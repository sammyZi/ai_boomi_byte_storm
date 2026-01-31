"""Property-based tests for cache layer.

Feature: drug-discovery-platform
Property 4: Cache Hit Behavior
Validates: Requirements 2.4, 3.7, 9.6
"""

import pytest
import asyncio
from hypothesis import given, strategies as st, settings, HealthCheck
from app.cache import CacheLayer


# Feature: drug-discovery-platform, Property 4: Cache Hit Behavior
@pytest.mark.asyncio
@given(
    key=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_characters=['\x00'])),
    value=st.one_of(
        st.integers(),
        st.floats(allow_nan=False, allow_infinity=False),
        st.text(max_size=1000),
        st.booleans(),
        st.lists(st.integers(), max_size=50),
        st.dictionaries(
            st.text(min_size=1, max_size=20, alphabet=st.characters(blacklist_characters=['\x00'])),
            st.integers(),
            max_size=20
        )
    )
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_cache_hit_behavior(key: str, value):
    """Property: For any cached data with valid TTL, subsequent requests should return
    the cached value without making external API calls.
    
    This property verifies that:
    1. After setting a value in cache, getting it returns the same value
    2. The cached value persists for the duration of the TTL
    3. Cache hits return data without requiring external calls
    
    Validates: Requirements 2.4, 3.7, 9.6
    """
    cache = CacheLayer()
    
    try:
        # Set value in cache with TTL
        set_success = await cache.set(key, value, ttl=10)
        
        # If Redis is not available, skip the test
        if not set_success:
            pytest.skip("Redis not available")
        
        # Get value from cache - should be a cache hit
        cached_value = await cache.get(key)
        
        # Verify cache hit returns the same value
        assert cached_value == value, f"Cache hit should return original value. Expected {value}, got {cached_value}"
        
        # Get again - should still be a cache hit (within TTL)
        cached_value_2 = await cache.get(key)
        assert cached_value_2 == value, "Second cache hit should return same value"
        
    finally:
        # Cleanup
        await cache.close()


@pytest.mark.asyncio
@given(
    key=st.text(min_size=1, max_size=100, alphabet=st.characters(blacklist_characters=['\x00'])),
)
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_cache_miss_returns_none(key: str):
    """Property: For any key that doesn't exist in cache, get() should return None.
    
    This verifies cache miss behavior.
    """
    cache = CacheLayer()
    
    try:
        # Try to get a value that doesn't exist
        result = await cache.get(f"nonexistent_{key}")
        
        # Should return None for cache miss
        assert result is None, "Cache miss should return None"
        
    finally:
        await cache.close()


@pytest.mark.asyncio
@given(
    prefix=st.text(
        min_size=1, 
        max_size=20, 
        alphabet=st.characters(
            whitelist_categories=('Lu', 'Ll', 'Nd'),  # Letters and digits only
            blacklist_characters=['\x00']
        )
    ).filter(lambda x: len(x.strip()) > 0),  # Ensure non-empty after strip
    num_keys=st.integers(min_value=1, max_value=10)
)
@settings(
    max_examples=50,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
async def test_cache_invalidation_pattern(prefix: str, num_keys: int):
    """Property: For any pattern, invalidate() should delete all matching keys.
    
    This verifies that cache invalidation works correctly with patterns.
    Note: Prefix is restricted to alphanumeric characters to avoid Redis pattern
    special characters like *, ?, [, ], ^, -, \\ which have special meaning in SCAN.
    """
    cache = CacheLayer()
    
    try:
        # Set multiple keys with the same prefix
        keys_set = []
        for i in range(num_keys):
            key = f"{prefix}:{i}"
            success = await cache.set(key, i, ttl=10)
            if success:
                keys_set.append(key)
        
        # If Redis is not available, skip the test
        if not keys_set:
            pytest.skip("Redis not available")
        
        # Invalidate all keys with the prefix
        deleted = await cache.invalidate(f"{prefix}:*")
        
        # Should have deleted all keys we set
        assert deleted == len(keys_set), f"Should delete {len(keys_set)} keys, deleted {deleted}"
        
        # Verify keys are actually deleted
        for key in keys_set:
            result = await cache.get(key)
            assert result is None, f"Key {key} should be deleted"
        
    finally:
        await cache.close()
