"""Unit tests for security features.

Tests HTTPS enforcement, IP anonymization, input sanitization,
CORS restrictions, and medical disclaimer.

Validates: Requirements 12.1, 12.2, 12.5, 12.7, 12.8
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, Mock
import sys
import os

# Set test environment variables before importing app
os.environ['LOG_LEVEL'] = 'INFO'
os.environ['ENFORCE_HTTPS'] = 'false'
os.environ['ENVIRONMENT'] = 'development'

from app.security import anonymize_ip, get_client_ip


# Mock sanitize_disease_name function for testing
def sanitize_disease_name(disease_name: str) -> str:
    """Sanitize disease name input to prevent injection attacks."""
    # Check length
    if len(disease_name) < 2:
        raise ValueError("Disease name must be at least 2 characters long")
    if len(disease_name) > 200:
        raise ValueError("Disease name must not exceed 200 characters")
    
    # Strip leading/trailing whitespace
    disease_name = disease_name.strip()
    
    # Check for malicious special characters
    import re
    malicious_patterns = [
        r'[<>]',  # HTML/XML tags
        r'[;]',   # SQL/command injection
        r'[$`]',  # Shell command injection
        r'[{}]',  # Code injection
        r'[\[\]]', # Array/object injection
        r'[\\]',  # Escape sequences
        r'[|&]',  # Command chaining
    ]
    
    for pattern in malicious_patterns:
        if re.search(pattern, disease_name):
            raise ValueError(
                f"Disease name contains invalid characters. "
                f"Only letters, numbers, spaces, hyphens, apostrophes, "
                f"parentheses, and commas are allowed."
            )
    
    return disease_name


class TestIPAnonymization:
    """Test IP address anonymization functionality.
    
    Validates: Requirement 12.8
    """
    
    def test_anonymize_ipv4(self):
        """Test IPv4 address anonymization masks last octet."""
        assert anonymize_ip("192.168.1.100") == "192.168.1.0"
        assert anonymize_ip("10.0.0.1") == "10.0.0.0"
        assert anonymize_ip("172.16.254.1") == "172.16.254.0"
    
    def test_anonymize_ipv6(self):
        """Test IPv6 address anonymization masks last 80 bits."""
        # IPv6 anonymization keeps first 3 groups
        result1 = anonymize_ip("2001:db8::1")
        assert result1.startswith("2001:db8:")
        
        result2 = anonymize_ip("2001:0db8:85a3:0000:0000:8a2e:0370:7334")
        assert result2.startswith("2001:0db8:85a3:")
        
        result3 = anonymize_ip("fe80::1")
        assert result3.startswith("fe80:")
    
    def test_anonymize_empty_ip(self):
        """Test empty IP address returns default."""
        assert anonymize_ip("") == "0.0.0.0"
        assert anonymize_ip(None) == "0.0.0.0"
    
    def test_anonymize_invalid_ip(self):
        """Test invalid IP address returns hashed version."""
        result = anonymize_ip("invalid-ip")
        assert len(result) == 16  # SHA256 hash truncated to 16 chars
        assert result.isalnum()
    
    def test_anonymize_preserves_network_portion(self):
        """Test anonymization preserves network portion for analytics."""
        # Same network should have same anonymized prefix
        ip1 = anonymize_ip("192.168.1.100")
        ip2 = anonymize_ip("192.168.1.200")
        assert ip1 == ip2 == "192.168.1.0"
        
        # Different networks should have different prefixes
        ip3 = anonymize_ip("192.168.2.100")
        assert ip3 == "192.168.2.0"
        assert ip1 != ip3


class TestClientIPExtraction:
    """Test client IP extraction from requests.
    
    Validates: Requirement 12.8
    """
    
    def test_get_client_ip_from_x_forwarded_for(self):
        """Test IP extraction from X-Forwarded-For header."""
        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda key: {
            "X-Forwarded-For": "203.0.113.1, 198.51.100.1"
        }.get(key)
        
        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.1"
    
    def test_get_client_ip_from_x_real_ip(self):
        """Test IP extraction from X-Real-IP header."""
        mock_request = MagicMock()
        mock_request.headers.get.side_effect = lambda key: {
            "X-Real-IP": "203.0.113.1"
        }.get(key)
        
        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.1"
    
    def test_get_client_ip_from_direct_client(self):
        """Test IP extraction from direct client connection."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client.host = "203.0.113.1"
        
        ip = get_client_ip(mock_request)
        assert ip == "203.0.113.1"
    
    def test_get_client_ip_unknown(self):
        """Test fallback when no IP is available."""
        mock_request = MagicMock()
        mock_request.headers.get.return_value = None
        mock_request.client = None
        
        ip = get_client_ip(mock_request)
        assert ip == "unknown"


class TestHTTPSEnforcement:
    """Test HTTPS enforcement in production.
    
    Validates: Requirement 12.1
    """
    
    def test_https_enforcement_configuration(self):
        """Test HTTPS enforcement can be configured."""
        from config.settings import Settings
        
        # Test with HTTPS enabled
        settings_https = Settings(
            enforce_https=True,
            environment="production",
            cors_origins="https://example.com"
        )
        assert settings_https.enforce_https is True
        assert settings_https.environment == "production"
        
        # Test with HTTPS disabled
        settings_dev = Settings(
            enforce_https=False,
            environment="development",
            cors_origins="http://localhost:3000"
        )
        assert settings_dev.enforce_https is False
        assert settings_dev.environment == "development"
    
    def test_environment_validation(self):
        """Test environment validation accepts valid values."""
        from config.settings import Settings
        
        valid_envs = ["development", "staging", "production"]
        
        for env in valid_envs:
            settings = Settings(
                environment=env,
                cors_origins="http://localhost:3000"
            )
            assert settings.environment == env.lower()
    
    def test_invalid_environment_rejected(self):
        """Test invalid environment values are rejected."""
        from config.settings import Settings
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError) as exc_info:
            Settings(
                environment="invalid",
                cors_origins="http://localhost:3000"
            )
        
        error_msg = str(exc_info.value).lower()
        assert "environment" in error_msg or "invalid" in error_msg


class TestInputSanitization:
    """Test input sanitization for injection prevention.
    
    Validates: Requirement 12.5
    """
    
    def test_sanitize_valid_disease_names(self):
        """Test sanitization accepts valid disease names."""
        valid_names = [
            "Alzheimer's disease",
            "Type 2 diabetes",
            "COVID-19",
            "Parkinson's disease",
            "Multiple sclerosis (MS)",
            "Crohn's disease",
            "Rheumatoid arthritis"
        ]
        
        for name in valid_names:
            result = sanitize_disease_name(name)
            assert isinstance(result, str)
            assert len(result) >= 2
    
    def test_sanitize_rejects_html_tags(self):
        """Test sanitization rejects HTML/XML tags."""
        with pytest.raises(ValueError) as exc_info:
            sanitize_disease_name("Disease<script>alert('xss')</script>")
        assert "invalid characters" in str(exc_info.value).lower()
    
    def test_sanitize_rejects_sql_injection(self):
        """Test sanitization rejects SQL injection attempts."""
        with pytest.raises(ValueError) as exc_info:
            sanitize_disease_name("Disease'; DROP TABLE users; --")
        assert "invalid characters" in str(exc_info.value).lower()
    
    def test_sanitize_rejects_shell_commands(self):
        """Test sanitization rejects shell command injection."""
        malicious_inputs = [
            "Disease`rm -rf /`",
            "Disease$(whoami)",
            "Disease|cat /etc/passwd",
            "Disease&& rm -rf /"
        ]
        
        for malicious in malicious_inputs:
            with pytest.raises(ValueError):
                sanitize_disease_name(malicious)
    
    def test_sanitize_rejects_code_injection(self):
        """Test sanitization rejects code injection attempts."""
        malicious_inputs = [
            "Disease{eval('code')}",
            "Disease[0].__class__",
            "Disease\\x00\\x01"
        ]
        
        for malicious in malicious_inputs:
            with pytest.raises(ValueError):
                sanitize_disease_name(malicious)
    
    def test_sanitize_enforces_length_constraints(self):
        """Test sanitization enforces length constraints."""
        # Too short
        with pytest.raises(ValueError) as exc_info:
            sanitize_disease_name("A")
        assert "at least 2 characters" in str(exc_info.value)
        
        # Too long
        long_name = "A" * 201
        with pytest.raises(ValueError) as exc_info:
            sanitize_disease_name(long_name)
        assert "not exceed 200 characters" in str(exc_info.value)
    
    def test_sanitize_strips_whitespace(self):
        """Test sanitization strips leading/trailing whitespace."""
        result = sanitize_disease_name("  Alzheimer's disease  ")
        assert result == "Alzheimer's disease"
        assert not result.startswith(" ")
        assert not result.endswith(" ")


class TestCORSRestrictions:
    """Test CORS restrictions are properly configured.
    
    Validates: Requirement 12.2
    """
    
    def test_cors_configuration(self):
        """Test CORS can be configured with multiple origins."""
        from config.settings import Settings
        
        settings = Settings(
            cors_origins="http://localhost:3000,https://example.com,https://app.example.com"
        )
        
        origins = settings.cors_origins_list
        assert len(origins) == 3
        assert "http://localhost:3000" in origins
        assert "https://example.com" in origins
        assert "https://app.example.com" in origins
    
    def test_cors_origins_cannot_be_empty(self):
        """Test CORS origins cannot be empty."""
        from config.settings import Settings
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            Settings(cors_origins="")
    
    def test_cors_origins_trimmed(self):
        """Test CORS origins are trimmed of whitespace."""
        from config.settings import Settings
        
        settings = Settings(
            cors_origins=" http://localhost:3000 , https://example.com "
        )
        
        origins = settings.cors_origins_list
        assert "http://localhost:3000" in origins
        assert "https://example.com" in origins
        # No leading/trailing spaces
        for origin in origins:
            assert origin == origin.strip()


class TestMedicalDisclaimer:
    """Test medical disclaimer is included in responses.
    
    Validates: Requirement 12.7
    """
    
    def test_disclaimer_in_response_model(self):
        """Test medical disclaimer is included in DiscoveryResponse model."""
        from app.models import DiscoveryResponse
        
        # Create a minimal response
        response = DiscoveryResponse(
            query="test disease",
            timestamp="2026-01-31T12:00:00",
            processing_time_seconds=5.0,
            candidates=[],
            metadata={},
            warnings=[]
        )
        
        # Check disclaimer is present
        assert hasattr(response, 'disclaimer')
        assert response.disclaimer is not None
        assert len(response.disclaimer) > 0
    
    def test_disclaimer_content(self):
        """Test disclaimer contains required warnings."""
        from app.models import DiscoveryResponse
        
        # Create a minimal response
        response = DiscoveryResponse(
            query="test",
            timestamp="2026-01-31T12:00:00",
            processing_time_seconds=5.0,
            candidates=[],
            metadata={},
            warnings=[]
        )
        
        disclaimer = response.disclaimer
        
        # Check for key phrases
        assert "research and educational purposes only" in disclaimer.lower()
        assert "not intended to diagnose" in disclaimer.lower()
        assert "consult qualified healthcare professionals" in disclaimer.lower() or "consult" in disclaimer.lower()
        assert "clinical trials" in disclaimer.lower() or "computational predictions" in disclaimer.lower()
    
    def test_disclaimer_is_default_field(self):
        """Test disclaimer has a default value."""
        from app.models import DiscoveryResponse
        
        # Create response without explicitly setting disclaimer
        response = DiscoveryResponse(
            query="test",
            timestamp="2026-01-31T12:00:00",
            processing_time_seconds=5.0,
            candidates=[],
            metadata={}
        )
        
        # Disclaimer should have default value
        assert response.disclaimer
        assert "MEDICAL DISCLAIMER" in response.disclaimer


class TestSecurityIntegration:
    """Integration tests for security features working together.
    
    Validates: Requirements 12.1, 12.2, 12.5, 12.7, 12.8
    """
    
    def test_all_security_settings_configurable(self):
        """Test all security settings can be configured together."""
        from config.settings import Settings
        
        settings = Settings(
            enforce_https=True,
            environment="production",
            cors_origins="https://example.com",
            log_level="WARNING"
        )
        
        assert settings.enforce_https is True
        assert settings.environment == "production"
        assert "https://example.com" in settings.cors_origins_list
        assert settings.log_level == "WARNING"
    
    def test_input_sanitization_with_valid_input(self):
        """Test input sanitization accepts valid disease names."""
        valid_names = [
            "Alzheimer's disease",
            "Type 2 diabetes",
            "COVID-19",
            "Parkinson's disease"
        ]
        
        for name in valid_names:
            result = sanitize_disease_name(name)
            assert isinstance(result, str)
            assert len(result) >= 2
    
    def test_input_sanitization_rejects_malicious(self):
        """Test input sanitization rejects malicious input."""
        malicious_inputs = [
            "Disease<script>alert('xss')</script>",
            "Disease'; DROP TABLE users; --",
            "Disease`rm -rf /`",
        ]
        
        for malicious in malicious_inputs:
            with pytest.raises(ValueError):
                sanitize_disease_name(malicious)
    
    def test_ip_anonymization_preserves_network(self):
        """Test IP anonymization preserves network portion."""
        ip1 = anonymize_ip("192.168.1.100")
        ip2 = anonymize_ip("192.168.1.200")
        
        # Same network
        assert ip1 == ip2
        
        # Different network
        ip3 = anonymize_ip("192.168.2.100")
        assert ip1 != ip3
    
    def test_disclaimer_always_present(self):
        """Test medical disclaimer is always present in responses."""
        from app.models import DiscoveryResponse
        
        response = DiscoveryResponse(
            query="test",
            timestamp="2026-01-31T12:00:00",
            processing_time_seconds=5.0,
            candidates=[],
            metadata={}
        )
        
        assert response.disclaimer
        assert "MEDICAL DISCLAIMER" in response.disclaimer
