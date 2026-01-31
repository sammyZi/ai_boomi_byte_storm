"""Property-based tests for configuration validation.

Feature: drug-discovery-platform
Property 25: Configuration Validation
Validates: Requirements 13.8
"""

import os
import pytest
from hypothesis import given, strategies as st, settings
from pydantic import ValidationError
from config.settings import Settings


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    log_level=st.sampled_from(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL", "debug", "info", "warning", "error", "critical"])
)
@settings(max_examples=100)
def test_valid_log_levels_are_accepted(log_level):
    """For any valid log level, the system should accept it and normalize to uppercase.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    # Create settings with valid log level
    settings = Settings(log_level=log_level)
    
    # Should be normalized to uppercase
    assert settings.log_level == log_level.upper()
    assert settings.log_level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    log_level=st.text(min_size=1, max_size=20).filter(
        lambda x: x.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    )
)
@settings(max_examples=100)
def test_invalid_log_levels_are_rejected(log_level):
    """For any invalid log level, the system should reject it with a clear error message.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    with pytest.raises(ValidationError) as exc_info:
        Settings(log_level=log_level)
    
    # Should have clear error message
    error_msg = str(exc_info.value)
    assert "log_level" in error_msg.lower()
    assert "invalid" in error_msg.lower() or "must be one of" in error_msg.lower()


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    port=st.integers(min_value=1, max_value=65535)
)
@settings(max_examples=100)
def test_valid_port_numbers_are_accepted(port):
    """For any valid port number (1-65535), the system should accept it.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    settings = Settings(api_port=port)
    assert settings.api_port == port
    assert 1 <= settings.api_port <= 65535


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    port=st.integers().filter(lambda x: x < 1 or x > 65535)
)
@settings(max_examples=100)
def test_invalid_port_numbers_are_rejected(port):
    """For any invalid port number (outside 1-65535), the system should reject it.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    with pytest.raises(ValidationError) as exc_info:
        Settings(api_port=port)
    
    # Should have error about port validation
    error_msg = str(exc_info.value)
    assert "api_port" in error_msg.lower()


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    timeout=st.integers(min_value=1, max_value=60)
)
@settings(max_examples=100)
def test_valid_timeout_values_are_accepted(timeout):
    """For any valid timeout value (1-60 seconds), the system should accept it.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    settings = Settings(ollama_timeout=timeout)
    assert settings.ollama_timeout == timeout
    assert 1 <= settings.ollama_timeout <= 60


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    timeout=st.integers().filter(lambda x: x < 1 or x > 60)
)
@settings(max_examples=100)
def test_invalid_timeout_values_are_rejected(timeout):
    """For any invalid timeout value (outside 1-60), the system should reject it.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    with pytest.raises(ValidationError) as exc_info:
        Settings(ollama_timeout=timeout)
    
    # Should have error about timeout validation
    error_msg = str(exc_info.value)
    assert "ollama_timeout" in error_msg.lower()


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    origins=st.lists(
        st.text(alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters=","), min_size=1, max_size=50),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=100)
def test_valid_cors_origins_are_accepted(origins):
    """For any non-empty CORS origins string, the system should accept it and parse correctly.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    # Filter out empty strings after stripping
    origins = [o for o in origins if o.strip()]
    if not origins:  # Skip if all origins are empty after filtering
        return
    
    cors_string = ",".join(origins)
    settings = Settings(cors_origins=cors_string)
    
    # Should parse into list correctly
    parsed = settings.cors_origins_list
    assert len(parsed) == len(origins)
    for i, origin in enumerate(origins):
        assert parsed[i] == origin.strip()


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    empty_string=st.sampled_from(["", "   ", "\t", "\n", "  \t\n  "])
)
@settings(max_examples=100)
def test_empty_cors_origins_are_rejected(empty_string):
    """For any empty or whitespace-only CORS origins string, the system should reject it.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    with pytest.raises(ValidationError) as exc_info:
        Settings(cors_origins=empty_string)
    
    # Should have error about CORS origins
    error_msg = str(exc_info.value)
    assert "cors_origins" in error_msg.lower()
    assert "empty" in error_msg.lower()


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    protocol=st.sampled_from(["http://", "https://"]),
    domain=st.text(alphabet=st.characters(whitelist_categories=("L", "N")), min_size=1, max_size=20),
    port=st.integers(min_value=1, max_value=65535)
)
@settings(max_examples=100)
def test_valid_urls_are_accepted(protocol, domain, port):
    """For any valid URL format, the system should accept it.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    if not domain:  # Skip if domain is empty after filtering
        return
    
    url = f"{protocol}{domain}:{port}"
    settings = Settings(ollama_base_url=url)
    assert settings.ollama_base_url == url


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    invalid_url=st.text(min_size=1, max_size=50).filter(
        lambda x: not x.startswith("http://") and not x.startswith("https://") and not x.startswith("redis://")
    )
)
@settings(max_examples=100)
def test_invalid_urls_are_rejected(invalid_url):
    """For any invalid URL format (not starting with http://, https://, or redis://), 
    the system should reject it.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    with pytest.raises(ValidationError) as exc_info:
        Settings(ollama_base_url=invalid_url)
    
    # Should have error about URL format
    error_msg = str(exc_info.value)
    assert "url" in error_msg.lower() or "invalid" in error_msg.lower()


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    cache_ttl=st.integers(min_value=60, max_value=604800)  # 1 minute to 1 week
)
@settings(max_examples=100)
def test_valid_cache_ttl_values_are_accepted(cache_ttl):
    """For any valid cache TTL value (>= 60 seconds), the system should accept it.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    settings = Settings(cache_ttl=cache_ttl)
    assert settings.cache_ttl == cache_ttl
    assert settings.cache_ttl >= 60


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    cache_ttl=st.integers(max_value=59)
)
@settings(max_examples=100)
def test_invalid_cache_ttl_values_are_rejected(cache_ttl):
    """For any cache TTL value less than 60 seconds, the system should reject it.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    with pytest.raises(ValidationError) as exc_info:
        Settings(cache_ttl=cache_ttl)
    
    # Should have error about cache_ttl validation
    error_msg = str(exc_info.value)
    assert "cache_ttl" in error_msg.lower()


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    rate_limit=st.integers(min_value=1, max_value=10000)
)
@settings(max_examples=100)
def test_valid_rate_limit_values_are_accepted(rate_limit):
    """For any positive rate limit value, the system should accept it.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    settings = Settings(rate_limit_per_minute=rate_limit)
    assert settings.rate_limit_per_minute == rate_limit
    assert settings.rate_limit_per_minute >= 1


# Feature: drug-discovery-platform, Property 25: Configuration Validation
@given(
    rate_limit=st.integers(max_value=0)
)
@settings(max_examples=100)
def test_invalid_rate_limit_values_are_rejected(rate_limit):
    """For any non-positive rate limit value, the system should reject it.
    
    Property 25: Configuration Validation
    Validates: Requirements 13.8
    """
    with pytest.raises(ValidationError) as exc_info:
        Settings(rate_limit_per_minute=rate_limit)
    
    # Should have error about rate_limit validation
    error_msg = str(exc_info.value)
    assert "rate_limit_per_minute" in error_msg.lower()
