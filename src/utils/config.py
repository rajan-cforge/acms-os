"""
Application Configuration Management

Production-grade configuration with validation and type safety.

Features:
- Environment variable loading (.env)
- Pydantic validation
- Type hints for IDE support
- Singleton pattern

Implementation Status: PLACEHOLDER
Week 5 Day 1: Task 3 (30 minutes)
"""

from pydantic import field_validator, ConfigDict
from pydantic_settings import BaseSettings
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Config(BaseSettings):
    """
    Application configuration with validation.

    Loads from environment variables or .env file.
    Validates all settings on initialization.

    Implementation Status: COMPLETE
    Week 5 Day 1: Task 3 (30 minutes)
    """

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra fields from .env
    )

    # LLM Configuration
    llm_provider: str = "openai"  # 'openai', 'anthropic', 'ollama', 'gemini'

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_default_model: str = "gpt-5.1"
    openai_embedding_model: str = "text-embedding-3-small"

    # Gemini (Google)
    gemini_api_key: Optional[str] = None
    gemini_default_model: str = "gemini-3-flash-preview"

    # Feature Flags
    feature_flag_confidence_routing: bool = True
    feature_flag_dual_vector_db: bool = True

    # Confidence Thresholds (0-100)
    confidence_threshold_local: int = 90
    confidence_threshold_enriched: int = 60

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    @field_validator('confidence_threshold_local', 'confidence_threshold_enriched')
    @classmethod
    def validate_threshold(cls, v: int) -> int:
        """Validate confidence thresholds are between 0 and 100"""
        if not 0 <= v <= 100:
            raise ValueError(f"Confidence threshold must be between 0 and 100, got {v}")
        return v

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is valid"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}, got {v}")
        return v_upper

    @field_validator('log_format')
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        """Validate log format"""
        valid_formats = ['json', 'text']
        v_lower = v.lower()
        if v_lower not in valid_formats:
            raise ValueError(f"Log format must be one of {valid_formats}, got {v}")
        return v_lower


_config: Optional[Config] = None


def get_config() -> Config:
    """
    Get singleton config instance.

    To be implemented in Week 5 Day 1.
    """
    global _config
    if _config is None:
        _config = Config()
    return _config
