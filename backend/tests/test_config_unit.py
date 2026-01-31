"""Unit tests for configuration module.

Tests specific examples of configuration validation and error handling.

Validates: Requirements 13.8
"""

import os
import sys
import pytest
from unittest.mock import patch
from pydantic import ValidationError
from config.settings import Settings, load_settings


class TestConfigurationValidation:
    """Test configuration validation with specific examples.
    
    Validates: Requirement 13.8
    """
    
    def test_default_configuration_is_valid(self):
        """Test that default configuration values are valid.
        
        Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5
        """
        settings = Settings()
        
        # API Configuration
        assert settings.api_port == 8000
        assert settings.api_host == "0.0.0.0"
        assert settings.cors_origins == "http://localhost:3000"
        
        # External APIs
        assert settings.open_targets_api_url == "https://api.platform.opentargets.org/api/v4"
        assert settings.chembl_api_url == "https://www.ebi.ac.uk/chembl/api/data"
        assert settings.alphafold_api_url == "https://alphafold.ebi.ac.uk/api"
        
        # Ollama Configuration
        assert settings.ollama_base_url == "http://localhost:11434"
        assert settings.ollama_model == "biomistral:7b"
        assert settings.ollama_timeout == 5
        
        # Cache Configuration
        assert settings.redis_url == "redis://localhost:6379"
        assert settings.cache_ttl == 86400
        
        # Rate Limiting
        assert settings.rate_limit_per_minute == 100
        
        # Logging
        assert settings.log_level == "INFO"
    
    def test_cors_origins_list_parsing(self):
        """Test CORS origins are correctly parsed from comma-separated string.
        
        Validates: Requirement 13.3
        """
        settings = Settings(cors_origins="http://localhost:3000,https://example.com,https://app.example.com")
        
        origins = settings.cors_origins_list
        assert len(origins) == 3
        assert origins[0] == "http://localhost:3000"
        assert origins[1] == "https://example.com"
        assert origins[2] == "https://app.example.com"
    
    def test_cors_origins_with_spaces_are_trimmed(self):
        """Test CORS origins with spaces are trimmed correctly.
        
        Validates: Requirement 13.3
        """
        settings = Settings(cors_origins="  http://localhost:3000  ,  https://example.com  ")
        
        origins = settings.cors_origins_list
        assert len(origins) == 2
        assert origins[0] == "http://localhost:3000"
        assert origins[1] == "https://example.com"
    
    def test_log_level_case_insensitive(self):
        """Test log level is case-insensitive and normalized to uppercase.
        
        Validates: Requirement 13.5
        """
        # Test lowercase
        settings = Settings(log_level="debug")
        assert settings.log_level == "DEBUG"
        
        # Test mixed case
        settings = Settings(log_level="WaRnInG")
        assert settings.log_level == "WARNING"
        
        # Test uppercase
        settings = Settings(log_level="ERROR")
        assert settings.log_level == "ERROR"


class TestConfigurationValidationErrors:
    """Test configuration validation error handling.
    
    Validates: Requirement 13.8
    """
    
    def test_invalid_log_level_raises_error(self):
        """Test invalid log level raises ValidationError with clear message.
        
        Validates: Requirement 13.8
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(log_level="INVALID")
        
        error_msg = str(exc_info.value)
        assert "log_level" in error_msg.lower()
        assert "invalid" in error_msg.lower()
    
    def test_port_below_minimum_raises_error(self):
        """Test port number below 1 raises ValidationError.
        
        Validates: Requirement 13.8
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(api_port=0)
        
        error_msg = str(exc_info.value)
        assert "api_port" in error_msg.lower()
    
    def test_port_above_maximum_raises_error(self):
        """Test port number above 65535 raises ValidationError.
        
        Validates: Requirement 13.8
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(api_port=65536)
        
        error_msg = str(exc_info.value)
        assert "api_port" in error_msg.lower()
    
    def test_negative_timeout_raises_error(self):
        """Test negative timeout raises ValidationError.
        
        Validates: Requirement 13.8
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(ollama_timeout=-1)
        
        error_msg = str(exc_info.value)
        assert "ollama_timeout" in error_msg.lower()
    
    def test_timeout_above_maximum_raises_error(self):
        """Test timeout above 60 seconds raises ValidationError.
        
        Validates: Requirement 13.8
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(ollama_timeout=61)
        
        error_msg = str(exc_info.value)
        assert "ollama_timeout" in error_msg.lower()
    
    def test_empty_cors_origins_raises_error(self):
        """Test empty CORS origins raises ValidationError.
        
        Validates: Requirement 13.8
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(cors_origins="")
        
        error_msg = str(exc_info.value)
        assert "cors_origins" in error_msg.lower()
        assert "empty" in error_msg.lower()
    
    def test_whitespace_only_cors_origins_raises_error(self):
        """Test whitespace-only CORS origins raises ValidationError.
        
        Validates: Requirement 13.8
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(cors_origins="   ")
        
        error_msg = str(exc_info.value)
        assert "cors_origins" in error_msg.lower()
        assert "empty" in error_msg.lower()
    
    def test_invalid_url_format_raises_error(self):
        """Test invalid URL format raises ValidationError.
        
        Validates: Requirement 13.8
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(ollama_base_url="not-a-url")
        
        error_msg = str(exc_info.value)
        assert "url" in error_msg.lower() or "invalid" in error_msg.lower()
    
    def test_empty_url_raises_error(self):
        """Test empty URL raises ValidationError.
        
        Validates: Requirement 13.8
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(redis_url="")
        
        error_msg = str(exc_info.value)
        assert "redis_url" in error_msg.lower()
    
    def test_cache_ttl_below_minimum_raises_error(self):
        """Test cache TTL below 60 seconds raises ValidationError.
        
        Validates: Requirement 13.8
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(cache_ttl=59)
        
        error_msg = str(exc_info.value)
        assert "cache_ttl" in error_msg.lower()
    
    def test_zero_rate_limit_raises_error(self):
        """Test zero rate limit raises ValidationError.
        
        Validates: Requirement 13.8
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(rate_limit_per_minute=0)
        
        error_msg = str(exc_info.value)
        assert "rate_limit_per_minute" in error_msg.lower()
    
    def test_negative_rate_limit_raises_error(self):
        """Test negative rate limit raises ValidationError.
        
        Validates: Requirement 13.8
        """
        with pytest.raises(ValidationError) as exc_info:
            Settings(rate_limit_per_minute=-1)
        
        error_msg = str(exc_info.value)
        assert "rate_limit_per_minute" in error_msg.lower()


class TestLoadSettingsFunction:
    """Test the load_settings function for fail-fast behavior.
    
    Validates: Requirement 13.8
    """
    
    def test_load_settings_with_valid_config(self):
        """Test load_settings returns Settings instance with valid configuration.
        
        Validates: Requirement 13.8
        """
        settings = load_settings()
        assert isinstance(settings, Settings)
    
    def test_load_settings_with_invalid_config_exits(self):
        """Test load_settings exits with code 1 on invalid configuration.
        
        Validates: Requirement 13.8 - Fail fast with clear error messages
        """
        with patch.dict(os.environ, {"LOG_LEVEL": "INVALID_LEVEL"}):
            with pytest.raises(SystemExit) as exc_info:
                # Need to reload the module to trigger load_settings with new env
                from importlib import reload
                import config.settings
                reload(config.settings)
            
            # Should exit with code 1
            assert exc_info.value.code == 1


class TestSpecificConfigurationScenarios:
    """Test specific configuration scenarios from requirements.
    
    Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5
    """
    
    def test_production_configuration_example(self):
        """Test a typical production configuration.
        
        Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5
        """
        settings = Settings(
            api_port=8080,
            api_host="0.0.0.0",
            cors_origins="https://drugdiscovery.example.com",
            ollama_base_url="http://ollama-server:11434",
            ollama_model="biomistral:7b",
            ollama_timeout=10,
            redis_url="redis://redis-server:6379",
            cache_ttl=86400,
            rate_limit_per_minute=100,
            log_level="WARNING"
        )
        
        assert settings.api_port == 8080
        assert settings.cors_origins == "https://drugdiscovery.example.com"
        assert settings.ollama_timeout == 10
        assert settings.log_level == "WARNING"
    
    def test_development_configuration_example(self):
        """Test a typical development configuration.
        
        Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5
        """
        settings = Settings(
            api_port=8000,
            cors_origins="http://localhost:3000,http://localhost:3001",
            log_level="DEBUG"
        )
        
        assert settings.api_port == 8000
        assert len(settings.cors_origins_list) == 2
        assert settings.log_level == "DEBUG"
    
    def test_multiple_cors_origins(self):
        """Test configuration with multiple CORS origins.
        
        Validates: Requirement 13.3
        """
        settings = Settings(
            cors_origins="http://localhost:3000,https://staging.example.com,https://prod.example.com"
        )
        
        origins = settings.cors_origins_list
        assert len(origins) == 3
        assert "http://localhost:3000" in origins
        assert "https://staging.example.com" in origins
        assert "https://prod.example.com" in origins
    
    def test_custom_ollama_configuration(self):
        """Test custom Ollama configuration.
        
        Validates: Requirement 13.2
        """
        settings = Settings(
            ollama_base_url="https://remote-ollama.example.com",
            ollama_model="custom-model:latest",
            ollama_timeout=30
        )
        
        assert settings.ollama_base_url == "https://remote-ollama.example.com"
        assert settings.ollama_model == "custom-model:latest"
        assert settings.ollama_timeout == 30
    
    def test_redis_with_authentication(self):
        """Test Redis URL with authentication.
        
        Validates: Requirement 13.1
        """
        settings = Settings(
            redis_url="redis://username:password@redis-server:6379/0"
        )
        
        assert settings.redis_url == "redis://username:password@redis-server:6379/0"
    
    def test_custom_cache_ttl(self):
        """Test custom cache TTL configuration.
        
        Validates: Requirement 13.1
        """
        # 1 hour
        settings = Settings(cache_ttl=3600)
        assert settings.cache_ttl == 3600
        
        # 1 week
        settings = Settings(cache_ttl=604800)
        assert settings.cache_ttl == 604800
    
    def test_custom_rate_limit(self):
        """Test custom rate limit configuration.
        
        Validates: Requirement 13.1
        """
        # Low rate limit for testing
        settings = Settings(rate_limit_per_minute=10)
        assert settings.rate_limit_per_minute == 10
        
        # High rate limit for production
        settings = Settings(rate_limit_per_minute=1000)
        assert settings.rate_limit_per_minute == 1000
    
    def test_all_log_levels(self):
        """Test all valid log levels.
        
        Validates: Requirement 13.5
        """
        for level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            settings = Settings(log_level=level)
            assert settings.log_level == level
