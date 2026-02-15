"""
Tests for Configuration Management

Week 5 Day 1: Task 3 (30 minutes)
Total: 5 tests

Purpose: Production-grade configuration with validation
"""

import pytest
import os
from unittest.mock import patch

from src.utils.config import Config, get_config


def test_config_loads_from_env():
    """Test configuration loads from environment variables"""
    with patch.dict(os.environ, {
        'LLM_PROVIDER': 'openai',
        'OPENAI_API_KEY': 'sk-test-123',
        'OPENAI_DEFAULT_MODEL': 'gpt-4o',
        'LOG_LEVEL': 'DEBUG'
    }):
        config = Config()

    assert config.llm_provider == 'openai'
    assert config.openai_api_key == 'sk-test-123'
    assert config.openai_default_model == 'gpt-4o'
    assert config.log_level == 'DEBUG'


def test_config_defaults():
    """Test default configuration values"""
    # Note: Config loads from .env by default, so to test pure defaults
    # we need to ensure no .env file is loaded
    with patch.dict(os.environ, {
        'LLM_PROVIDER': 'openai'  # Override .env for test
    }):
        config = Config(_env_file=None)  # Don't load .env

    # Defaults (from code, not .env)
    assert config.llm_provider == 'openai'
    assert config.openai_default_model == 'gpt-4-turbo'
    assert config.openai_embedding_model == 'text-embedding-3-small'
    assert config.feature_flag_confidence_routing is True
    assert config.feature_flag_dual_vector_db is True
    assert config.confidence_threshold_local == 90
    assert config.confidence_threshold_enriched == 60
    assert config.log_level == 'INFO'
    assert config.log_format == 'json'


def test_config_validation():
    """Test configuration validation"""
    with patch.dict(os.environ, {
        'CONFIDENCE_THRESHOLD_LOCAL': '95',
        'CONFIDENCE_THRESHOLD_ENRICHED': '65'
    }):
        config = Config()

    # Thresholds should be integers
    assert isinstance(config.confidence_threshold_local, int)
    assert isinstance(config.confidence_threshold_enriched, int)
    assert config.confidence_threshold_local == 95
    assert config.confidence_threshold_enriched == 65


def test_invalid_threshold_raises():
    """Test invalid confidence thresholds raise error"""
    with patch.dict(os.environ, {'CONFIDENCE_THRESHOLD_LOCAL': '150'}):
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            Config()


def test_config_singleton():
    """Test get_config returns same instance"""
    # Clear singleton
    from src.utils import config
    config._config = None

    # Get config twice
    config1 = get_config()
    config2 = get_config()

    # Should be same instance
    assert config1 is config2
