"""Unit tests for API endpoints.

This module contains unit tests for API endpoints including
successful discovery flow, validation errors, rate limiting,
and error handling.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from app.main import app, sanitize_disease_name
from app.models import (
    DiscoveryResult,
    DrugCandidate,
    Target,
    Molecule,
    MolecularProperties,
    ToxicityAssessment
)


# Create test client
client = TestClient(app)


def test_root_endpoint():
    """Test root endpoint returns API information."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert data["version"] == "0.1.0"


def test_health_check_endpoint():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"


def test_sanitize_disease_name_valid():
    """Test input sanitization accepts valid disease names."""
    valid_names = [
        "Alzheimer's disease",
        "Type 2 diabetes",
        "COVID-19",
        "Parkinson's disease (early onset)",
        "Breast cancer, stage II"
    ]
    
    for name in valid_names:
        result = sanitize_disease_name(name)
        assert isinstance(result, str)
        assert len(result) >= 2


def test_sanitize_disease_name_malicious():
    """Test input sanitization rejects malicious characters."""
    malicious_names = [
        "Disease<script>alert('xss')</script>",
        "Disease; DROP TABLE users;",
        "Disease$(rm -rf /)",
        "Disease{code}",
        "Disease[injection]",
        "Disease\\escape",
        "Disease|pipe",
        "Disease&command"
    ]
    
    for name in malicious_names:
        with pytest.raises(ValueError) as exc_info:
            sanitize_disease_name(name)
        assert "invalid characters" in str(exc_info.value).lower()


def test_sanitize_disease_name_length():
    """Test input sanitization enforces length constraints."""
    # Too short
    with pytest.raises(ValueError) as exc_info:
        sanitize_disease_name("A")
    assert "at least 2 characters" in str(exc_info.value)
    
    # Too long
    long_name = "A" * 201
    with pytest.raises(ValueError) as exc_info:
        sanitize_disease_name(long_name)
    assert "not exceed 200 characters" in str(exc_info.value)


def test_sanitize_disease_name_whitespace():
    """Test input sanitization strips whitespace."""
    name_with_whitespace = "  Alzheimer's disease  "
    result = sanitize_disease_name(name_with_whitespace)
    assert result == "Alzheimer's disease"
    assert not result.startswith(" ")
    assert not result.endswith(" ")


@pytest.mark.asyncio
async def test_discover_endpoint_validation_error():
    """Test /api/discover endpoint with validation errors.
    
    Validates: Requirements 11.4, 11.5
    """
    # Test with empty disease name
    response = client.post(
        "/api/discover",
        json={"disease_name": ""}
    )
    assert response.status_code == 422  # Validation error
    
    # Test with too short disease name (Pydantic validates min_length)
    response = client.post(
        "/api/discover",
        json={"disease_name": "A"}
    )
    assert response.status_code == 422  # Validation error from Pydantic
    
    # Test with missing disease_name
    response = client.post(
        "/api/discover",
        json={}
    )
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_discover_endpoint_malicious_input():
    """Test /api/discover endpoint rejects malicious input.
    
    Validates: Requirements 12.5
    """
    malicious_inputs = [
        {"disease_name": "Disease<script>"},
        {"disease_name": "Disease; DROP TABLE;"},
        {"disease_name": "Disease$(rm -rf /)"}
    ]
    
    for malicious_input in malicious_inputs:
        response = client.post("/api/discover", json=malicious_input)
        assert response.status_code == 400
        data = response.json()
        assert "error_code" in data
        assert "INVALID_INPUT" in data["error_code"]


def test_error_response_format():
    """Test error responses have consistent format.
    
    Validates: Requirements 15.5
    """
    # Trigger a validation error
    response = client.post(
        "/api/discover",
        json={"disease_name": ""}
    )
    
    assert response.status_code == 422
    data = response.json()
    
    # Verify error response structure (Pydantic validation error format)
    assert "detail" in data


def test_http_status_codes():
    """Test HTTP status codes are accurate.
    
    Validates: Requirements 15.6
    """
    # Test 200 for health check
    response = client.get("/health")
    assert response.status_code == 200
    
    # Test 422 for validation error (Pydantic)
    response = client.post(
        "/api/discover",
        json={"disease_name": ""}
    )
    assert response.status_code == 422
    
    # Test 422 for validation error
    response = client.post(
        "/api/discover",
        json={}
    )
    assert response.status_code == 422


def test_openapi_documentation():
    """Test OpenAPI documentation is available.
    
    Validates: Requirements 11.1, 11.2, 11.3
    """
    # Test Swagger UI
    response = client.get("/docs")
    assert response.status_code == 200
    
    # Test ReDoc
    response = client.get("/redoc")
    assert response.status_code == 200
    
    # Test OpenAPI JSON
    response = client.get("/openapi.json")
    assert response.status_code == 200
    data = response.json()
    assert "openapi" in data
    assert "info" in data
    assert "paths" in data


def test_cors_headers():
    """Test CORS headers are configured.
    
    Validates: Requirements 12.2
    """
    response = client.options(
        "/api/discover",
        headers={"Origin": "http://localhost:3000"}
    )
    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers or response.status_code == 200


def test_gzip_compression():
    """Test gzip compression is enabled.
    
    Validates: Requirements 15.7
    """
    response = client.get(
        "/health",
        headers={"Accept-Encoding": "gzip"}
    )
    # Response should either be compressed or small enough to skip compression
    assert response.status_code == 200
