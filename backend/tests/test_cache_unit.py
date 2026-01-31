"""Unit tests for cache layer.

Tests specific cache scenarios including hit/miss, TTL expiration,
and Redis connection failures.

Validates: Requirements 9.2, 9.3, 9.4, 9.5, 9.6
"""

import pytest
import asyncio
from app.cache import CacheLayer


@pytest.mark.asyncio
async def test_cache_hit_scenario():
    """Test cache hit returns stored value.
    
    Validates: Requirements 9.6
    """
    cache = CacheLayer()
    
    try:
        # Store a value
        key = "test:hit"
        value = {"name": "aspirin", "smiles": "CC(=O)Oc1ccccc1C(=O)O"}
        
        success = await cache.set(key, value, ttl=10)
        if not success:
            pytest.skip("Redis not available")
        
        # Retrieve the value
        result = await cache.get(key)
        
        # Should get the same value back
        assert result == value
        assert result["name"] == "aspirin"
        assert result["smiles"] == "CC(=O)Oc1ccccc1C(=O)O"
        
    finally:
        await cache.close()


@pytest.mark.asyncio
async def test_cache_miss_scenario():
    """Test cache miss returns None.
    
    Validates: Requirements 9.6
    """
    cache = CacheLayer()
    
    try:
        # Try to get a non-existent key
        result = await cache.get("test:nonexistent:key:12345")
        
        # Should return None
        assert result is None
        
    finally:
        await cache.close()


@pytest.mark.asyncio
async def test_cache_ttl_expiration():
    """Test that cached values expire after TTL.
    
    Validates: Requirements 9.3, 9.4
    """
    cache = CacheLayer()
    
    try:
        # Store a value with short TTL
        key = "test:ttl"
        value = "expires soon"
        
        success = await cache.set(key, value, ttl=1)
        if not success:
            pytest.skip("Redis not available")
        
        # Should be available immediately
        result = await cache.get(key)
        assert result == value
        
        # Wait for TTL to expire
        await asyncio.sleep(1.5)
        
        # Should be expired now
        result = await cache.get(key)
        assert result is None
        
    finally:
        await cache.close()


@pytest.mark.asyncio
async def test_cache_different_data_types():
    """Test caching different data types.
    
    Validates: Requirements 9.2, 9.5
    """
    cache = CacheLayer()
    
    try:
        test_cases = [
            ("test:int", 42),
            ("test:float", 3.14159),
            ("test:string", "hello world"),
            ("test:bool", True),
            ("test:list", [1, 2, 3, 4, 5]),
            ("test:dict", {"a": 1, "b": 2, "c": 3}),
            ("test:nested", {"data": [1, 2, {"x": "y"}], "count": 3}),
        ]
        
        # Store all values
        for key, value in test_cases:
            success = await cache.set(key, value, ttl=10)
            if not success:
                pytest.skip("Redis not available")
        
        # Retrieve and verify all values
        for key, expected_value in test_cases:
            result = await cache.get(key)
            assert result == expected_value, f"Failed for {key}: expected {expected_value}, got {result}"
        
    finally:
        await cache.close()


@pytest.mark.asyncio
async def test_cache_invalidate_single_pattern():
    """Test invalidating cache entries by pattern.
    
    Validates: Requirements 9.5
    """
    cache = CacheLayer()
    
    try:
        # Store multiple values with same prefix
        prefix = "test:invalidate"
        for i in range(5):
            success = await cache.set(f"{prefix}:{i}", i, ttl=10)
            if not success:
                pytest.skip("Redis not available")
        
        # Store a value with different prefix
        success = await cache.set("test:keep:1", "keep me", ttl=10)
        if not success:
            pytest.skip("Redis not available")
        
        # Invalidate the first prefix
        deleted = await cache.invalidate(f"{prefix}:*")
        assert deleted == 5
        
        # Verify invalidated keys are gone
        for i in range(5):
            result = await cache.get(f"{prefix}:{i}")
            assert result is None
        
        # Verify other key is still there
        result = await cache.get("test:keep:1")
        assert result == "keep me"
        
    finally:
        await cache.close()


@pytest.mark.asyncio
async def test_cache_invalidate_no_matches():
    """Test invalidating with pattern that matches nothing.
    
    Validates: Requirements 9.5
    """
    cache = CacheLayer()
    
    try:
        # Try to invalidate non-existent pattern
        deleted = await cache.invalidate("test:nonexistent:pattern:*")
        
        # Should return 0 (no keys deleted)
        assert deleted == 0
        
    finally:
        await cache.close()


@pytest.mark.asyncio
async def test_cache_connection_failure_graceful():
    """Test that cache handles connection failures gracefully.
    
    Validates: Requirements 9.2
    """
    # Create cache with invalid Redis URL
    cache = CacheLayer(redis_url="redis://invalid-host:9999")
    
    try:
        # Get should return None (not raise exception)
        result = await cache.get("test:key")
        assert result is None
        
        # Set should return False (not raise exception)
        success = await cache.set("test:key", "value")
        assert success is False
        
        # Invalidate should return 0 (not raise exception)
        deleted = await cache.invalidate("test:*")
        assert deleted == 0
        
        # Cache should report as not connected
        assert cache.is_connected is False
        
    finally:
        await cache.close()


@pytest.mark.asyncio
async def test_cache_empty_key_handling():
    """Test cache behavior with edge case keys.
    
    Validates: Requirements 9.2
    """
    cache = CacheLayer()
    
    try:
        # Test with various edge case keys
        edge_cases = [
            "a",  # Single character
            "key:with:colons",  # Colons in key
            "key-with-dashes",  # Dashes in key
            "key_with_underscores",  # Underscores in key
            "key.with.dots",  # Dots in key
        ]
        
        for key in edge_cases:
            success = await cache.set(key, f"value_{key}", ttl=10)
            if not success:
                pytest.skip("Redis not available")
            
            result = await cache.get(key)
            assert result == f"value_{key}", f"Failed for key: {key}"
        
    finally:
        await cache.close()


@pytest.mark.asyncio
async def test_cache_overwrite_existing_key():
    """Test that setting an existing key overwrites the value.
    
    Validates: Requirements 9.2, 9.5
    """
    cache = CacheLayer()
    
    try:
        key = "test:overwrite"
        
        # Set initial value
        success = await cache.set(key, "initial", ttl=10)
        if not success:
            pytest.skip("Redis not available")
        
        result = await cache.get(key)
        assert result == "initial"
        
        # Overwrite with new value
        success = await cache.set(key, "updated", ttl=10)
        assert success is True
        
        result = await cache.get(key)
        assert result == "updated"
        
    finally:
        await cache.close()


@pytest.mark.asyncio
async def test_cache_custom_ttl():
    """Test cache with custom TTL values.
    
    Validates: Requirements 9.3, 9.4
    """
    cache = CacheLayer()
    
    try:
        # Set value with custom TTL
        key = "test:custom_ttl"
        value = "custom ttl value"
        custom_ttl = 5
        
        success = await cache.set(key, value, ttl=custom_ttl)
        if not success:
            pytest.skip("Redis not available")
        
        # Should be available immediately
        result = await cache.get(key)
        assert result == value
        
        # Should still be available after 2 seconds
        await asyncio.sleep(2)
        result = await cache.get(key)
        assert result == value
        
    finally:
        await cache.close()


@pytest.mark.asyncio
async def test_cache_default_ttl():
    """Test cache uses default TTL when not specified.
    
    Validates: Requirements 9.3, 9.4
    """
    cache = CacheLayer()
    
    try:
        # Set value without specifying TTL (should use default)
        key = "test:default_ttl"
        value = "default ttl value"
        
        success = await cache.set(key, value)
        if not success:
            pytest.skip("Redis not available")
        
        # Should be available
        result = await cache.get(key)
        assert result == value
        
    finally:
        await cache.close()
