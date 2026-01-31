"""Pytest configuration and fixtures for all tests.

This module provides common fixtures and configuration for the test suite.
"""

import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Set up test environment variables before any tests run.
    
    This fixture runs once per test session and ensures that all required
    environment variables have valid values for testing.
    """
    # Store original environment
    original_env = os.environ.copy()
    
    # Set default test environment variables
    test_env = {
        "LOG_LEVEL": "INFO",
        "ENFORCE_HTTPS": "false",
        "ENVIRONMENT": "development",
        "API_PORT": "8000",
        "API_HOST": "0.0.0.0",
        "CORS_ORIGINS": "http://localhost:3000",
        "OPEN_TARGETS_API_URL": "https://api.platform.opentargets.org/api/v4",
        "CHEMBL_API_URL": "https://www.ebi.ac.uk/chembl/api/data",
        "ALPHAFOLD_API_URL": "https://alphafold.ebi.ac.uk/api",
        "OLLAMA_BASE_URL": "http://localhost:11434",
        "OLLAMA_MODEL": "biomistral:7b",
        "OLLAMA_TIMEOUT": "5",
        "REDIS_URL": "redis://localhost:6379",
        "CACHE_TTL": "86400",
        "RATE_LIMIT_PER_MINUTE": "100",
    }
    
    # Update environment with test values (only if not already set)
    for key, value in test_env.items():
        if key not in os.environ:
            os.environ[key] = value
    
    yield
    
    # Restore original environment after all tests
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture(autouse=True)
def reset_environment_per_test():
    """Reset environment variables before each test.
    
    This ensures that tests that modify environment variables don't
    affect other tests.
    """
    # Store environment before test
    env_before = os.environ.copy()
    
    yield
    
    # Restore environment after test
    os.environ.clear()
    os.environ.update(env_before)
