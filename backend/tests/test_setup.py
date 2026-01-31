"""Basic tests to verify project setup and configuration."""

import pytest
from config.settings import Settings


def test_settings_can_be_loaded():
    """Test that settings can be loaded with default values."""
    settings = Settings()
    
    # Verify default values are set
    assert settings.api_port == 8000
    assert settings.api_host == "0.0.0.0"
    assert settings.cache_ttl == 86400
    assert settings.rate_limit_per_minute == 100


def test_cors_origins_parsing():
    """Test that CORS origins are parsed correctly from comma-separated string."""
    settings = Settings(cors_origins="http://localhost:3000,https://example.com")
    
    origins = settings.cors_origins_list
    assert len(origins) == 2
    assert "http://localhost:3000" in origins
    assert "https://example.com" in origins


def test_settings_with_custom_values():
    """Test that custom environment values override defaults."""
    settings = Settings(
        api_port=9000,
        log_level="DEBUG",
        cache_ttl=3600
    )
    
    assert settings.api_port == 9000
    assert settings.log_level == "DEBUG"
    assert settings.cache_ttl == 3600
