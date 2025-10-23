"""
Configuration management for Fontis AI Voice Agent.

This module handles all application settings loaded from environment variables,
providing type-safe configuration with validation and defaults.

Design decisions:
- Pydantic Settings for automatic env var loading and validation
- Separate sections for different concerns (API, app, security)
- Field validators ensure data integrity at startup
- Properties for computed values (is_production, is_development)
"""

from typing import Union

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application configuration loaded from environment variables.
    
    All settings can be overridden via environment variables.
    Example: FONTIS_API_KEY=xxx python run.py
    
    Configuration sections:
    1. Fontis API - External API connection settings
    2. Vapi AI - Voice platform integration settings
    3. JotForm - Contract generation and form integration
    4. Application - Runtime behavior configuration
    5. Server - HTTP server configuration
    6. Security - CORS and rate limiting settings
    """
    
    # ===== Fontis API Configuration =====
    fontis_api_key: str = Field(
        ...,  # Required field
        min_length=10,
        description="API key for Fontis Water RestAPI authentication"
    )
    fontis_base_url: str = Field(
        default="https://fontisweb.creatordraft.com/api/v1",
        description="Base URL for Fontis API endpoints"
    )
    fontis_timeout: int = Field(
        default=30,
        ge=5, le=120,
        description="HTTP timeout in seconds for Fontis API calls"
    )
    fontis_max_retries: int = Field(
        default=3,
        ge=0, le=10,
        description="Maximum retries for failed API calls"
    )
    
    # ===== Vapi AI Configuration =====
    vapi_api_key: str | None = Field(
        default=None,
        description="API key for Vapi AI platform (optional for dev)"
    )
    vapi_public_key: str | None = Field(
        default=None,
        description="Vapi public key for Web SDK (browser-side)"
    )
    vapi_assistant_id: str | None = Field(
        default=None,
        description="Vapi assistant ID for testing"
    )
    vapi_phone_number: str | None = Field(
        default=None,
        description="Vapi phone number for outbound calls"
    )
    vapi_phone_number_id: str | None = Field(
        default=None,
        description="Vapi phone number ID"
    )
    vapi_base_url: str = Field(
        default="https://api.vapi.ai",
        description="Base URL for Vapi API"
    )
    vapi_webhook_secret: str | None = Field(
        default=None,
        description="Secret for verifying Vapi webhook signatures"
    )
    
    # ===== JotForm Configuration =====
    jotform_api_key: str | None = Field(
        default=None,
        description="API key for JotForm integration (contract generation)"
    )
    jotform_base_url: str = Field(
        default="https://api.jotform.com",
        description="Base URL for JotForm API"
    )
    jotform_form_id: str | None = Field(
        default=None,
        description="JotForm form ID for customer onboarding contracts"
    )
    
    # ===== Security Settings =====
    internal_api_key: str = Field(
        default="dev_key_change_in_production",
        min_length=32,
        description="Shared secret for internal API authentication (tools endpoints)"
    )
    
    # ===== Application Settings =====
    app_env: str = Field(
        default="development",
        pattern="^(development|staging|production)$",
        description="Application environment"
    )
    log_level: str = Field(
        default="info",
        pattern="^(debug|info|warning|error|critical)$",
        description="Logging level"
    )
    log_format: str = Field(
        default="json",
        pattern="^(json|console)$",
        description="Log output format (json for prod, console for dev)"
    )
    
    # ===== Server Configuration =====
    server_host: str = Field(
        default="0.0.0.0",
        description="Server bind host"
    )
    server_port: int = Field(
        default=8000,
        ge=1024, le=65535,
        description="Server port"
    )
    
    # ===== Security Configuration =====
    cors_origins: Union[str, list[str]] = Field(
        default="",
        description="Allowed CORS origins - comma-separated string or list"
    )
    api_rate_limit: int = Field(
        default=100,
        ge=1,
        description="API rate limit per minute per IP"
    )
    
    @field_validator("fontis_api_key")
    @classmethod
    def validate_fontis_api_key(cls, v: str) -> str:
        """Validate Fontis API key is not empty."""
        if not v or v.strip() == "":
            raise ValueError("fontis_api_key cannot be empty")
        if not v.startswith("fk_"):
            raise ValueError("fontis_api_key must start with 'fk_' prefix")
        return v
    
    @model_validator(mode="after")
    def validate_and_parse_settings(self):
        """Parse cors_origins from string to list and validate."""
        # Parse CORS origins
        cors_value = self.cors_origins
        if isinstance(cors_value, str):
            if not cors_value or cors_value.strip() == "":
                self.cors_origins = []
            else:
                self.cors_origins = [origin.strip() for origin in cors_value.split(",") if origin.strip()]
        
        # Validate CORS in production
        if self.app_env == "production":
            if not self.cors_origins or len(self.cors_origins) == 0:
                raise ValueError("CORS origins must be configured in production")
            if "*" in self.cors_origins:
                raise ValueError("CORS wildcard not allowed in production")
        
        # Set default if empty
        if not self.cors_origins:
            self.cors_origins = ["http://localhost:8000"]
        
        return self
    
    @field_validator("internal_api_key")
    @classmethod
    def validate_internal_api_key(cls, v: str, info) -> str:
        """Ensure strong API key in production."""
        app_env = info.data.get("app_env", "development")
        if app_env == "production" and (v == "dev_key_change_in_production" or len(v) < 32):
            raise ValueError("Internal API key must be at least 32 characters in production")
        return v
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging mode."""
        return self.app_env == "staging"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore unknown env vars
    )


# Singleton instance - loaded once at module import
settings = Settings()
