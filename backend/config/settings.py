"""Configuration settings for the drug discovery platform.

This module reads and validates all configuration from environment variables.
It fails fast with clear error messages if required variables are missing.
"""

import sys
from pydantic import Field, field_validator, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    All settings are validated on startup. Missing required variables
    will cause the application to fail with clear error messages.
    
    Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.8
    """
    
    # API Configuration (Requirements 13.1, 13.4)
    api_port: int = Field(default=8000, ge=1, le=65535, description="API server port number")
    api_host: str = Field(default="0.0.0.0", description="API server host address")
    cors_origins: str = Field(default="http://localhost:3000", description="Comma-separated list of allowed CORS origins")
    
    # External APIs (Requirement 13.1)
    open_targets_api_url: str = Field(
        default="https://api.platform.opentargets.org/api/v4",
        description="Open Targets Platform API base URL"
    )
    chembl_api_url: str = Field(
        default="https://www.ebi.ac.uk/chembl/api/data",
        description="ChEMBL Database API base URL"
    )
    alphafold_api_url: str = Field(
        default="https://alphafold.ebi.ac.uk/api",
        description="AlphaFold Database API base URL"
    )
    
    # Ollama Configuration (Requirement 13.2)
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama service base URL"
    )
    ollama_model: str = Field(
        default="biomistral:7b",
        description="Ollama model name"
    )
    ollama_timeout: int = Field(
        default=5,
        ge=1,
        le=60,
        description="Ollama request timeout in seconds"
    )
    
    # Cache Configuration (Requirement 13.1)
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    cache_ttl: int = Field(
        default=86400,
        ge=60,
        description="Cache TTL in seconds (24 hours default)"
    )
    
    # Rate Limiting (Requirement 13.1)
    rate_limit_per_minute: int = Field(
        default=100,
        ge=1,
        description="Maximum requests per minute per IP"
    )
    
    # Logging (Requirement 13.5)
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    
    # Security Configuration (Requirement 12.1)
    enforce_https: bool = Field(
        default=False,
        description="Enforce HTTPS for all requests in production"
    )
    environment: str = Field(
        default="development",
        description="Environment (development, staging, production)"
    )
    
    # Molecular Docking Configuration
    vina_path: str = Field(
        default="d:/ai_boomi/backend/tools/vina.exe",
        description="Path to AutoDock Vina executable (auto-detected if empty)"
    )
    docking_timeout: int = Field(
        default=1800,
        ge=60,
        le=7200,
        description="Docking job timeout in seconds (default: 30 minutes)"
    )
    docking_max_concurrent: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum concurrent docking jobs"
    )
    docking_work_dir: str = Field(
        default="d:/ai_boomi/backend/docking_workdir",
        description="Working directory for docking files (uses temp if empty)"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is one of the allowed values.
        
        Requirement 13.5: Support configuration of log level
        """
        allowed_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in allowed_levels:
            raise ValueError(
                f"Invalid log level '{v}'. Must be one of: {', '.join(allowed_levels)}"
            )
        return v_upper
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment is one of the allowed values.
        
        Requirement 12.1: HTTPS enforcement configuration
        """
        allowed_envs = {"development", "staging", "production"}
        v_lower = v.lower()
        if v_lower not in allowed_envs:
            raise ValueError(
                f"Invalid environment '{v}'. Must be one of: {', '.join(allowed_envs)}"
            )
        return v_lower
    
    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: str) -> str:
        """Validate CORS origins are not empty.
        
        Requirement 13.3: Support configuration of CORS origins
        """
        if not v or not v.strip():
            raise ValueError("CORS origins cannot be empty")
        return v
    
    @field_validator("ollama_base_url", "open_targets_api_url", "chembl_api_url", "alphafold_api_url", "redis_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URLs are not empty and have proper format.
        
        Requirements 13.1, 13.2: Configuration from environment variables
        """
        if not v or not v.strip():
            raise ValueError("URL cannot be empty")
        if not (v.startswith("http://") or v.startswith("https://") or v.startswith("redis://")):
            raise ValueError(f"Invalid URL format: {v}")
        return v
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string.
        
        Requirement 13.3: Support configuration of CORS origins
        """
        return [origin.strip() for origin in self.cors_origins.split(",")]


def load_settings() -> Settings:
    """Load and validate settings from environment variables.
    
    This function fails fast with clear error messages if validation fails.
    
    Requirement 13.8: Validate required environment variables on startup
    and fail fast with clear error messages
    
    Returns:
        Settings: Validated settings instance
        
    Raises:
        SystemExit: If validation fails, exits with code 1
    """
    try:
        return Settings()
    except ValidationError as e:
        print("=" * 80, file=sys.stderr)
        print("CONFIGURATION ERROR: Failed to load settings", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        print(file=sys.stderr)
        print("The following configuration errors were found:", file=sys.stderr)
        print(file=sys.stderr)
        
        for error in e.errors():
            field = " -> ".join(str(loc) for loc in error["loc"])
            msg = error["msg"]
            print(f"  ❌ {field}: {msg}", file=sys.stderr)
        
        print(file=sys.stderr)
        print("Please check your environment variables or .env file.", file=sys.stderr)
        print("See .env.example for required configuration.", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        sys.exit(1)


# Global settings instance
# This will fail fast on import if configuration is invalid
settings = load_settings()
