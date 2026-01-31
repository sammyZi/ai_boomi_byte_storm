"""Configuration settings for the drug discovery platform.

This module reads and validates all configuration from environment variables.
It fails fast with clear error messages if required variables are missing.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables.
    
    All settings are validated on startup. Missing required variables
    will cause the application to fail with clear error messages.
    """
    
    # API Configuration
    api_port: int = 8000
    api_host: str = "0.0.0.0"
    cors_origins: str = "http://localhost:3000"
    
    # External APIs
    open_targets_api_url: str = "https://api.platform.opentargets.org/api/v4"
    chembl_api_url: str = "https://www.ebi.ac.uk/chembl/api/data"
    alphafold_api_url: str = "https://alphafold.ebi.ac.uk/api"
    
    # Ollama Configuration
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "biomistral:7b"
    ollama_timeout: int = 5
    
    # Cache Configuration
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 86400  # 24 hours in seconds
    
    # Rate Limiting
    rate_limit_per_minute: int = 100
    
    # Logging
    log_level: str = "INFO"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
