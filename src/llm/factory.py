"""
LLM Client Factory

Factory pattern for easy LLM provider switching.

Usage:
    # Use default provider from config
    client = get_llm_client()

    # Explicitly specify provider
    client = get_llm_client(provider='openai')

    # Easy switching: just change one line
    client = get_llm_client(provider='anthropic')  # When available

Implementation Status: COMPLETE
Week 5 Day 1: Task 2 (3.5 hours)
"""

import logging
import os
from typing import Optional

from src.llm.openai_client import OpenAIClient
from src.utils.logging import get_correlation_id

logger = logging.getLogger(__name__)


def get_llm_client(provider: Optional[str] = None):
    """
    Factory function to get LLM client.

    Enables provider switching with one config line change.

    Args:
        provider: LLM provider ('openai', 'anthropic', 'ollama', etc.)
                 If None, uses LLM_PROVIDER env variable (default: 'openai')

    Returns:
        LLM client instance (OpenAIClient, AnthropicClient, etc.)

    Raises:
        ValueError: If provider is unknown
        ValueError: If required API keys are missing

    Examples:
        >>> # Use OpenAI
        >>> client = get_llm_client(provider='openai')
        >>> response = await client.complete("Hello", model="gpt-5.1")

        >>> # Easy switching to Anthropic (when available)
        >>> client = get_llm_client(provider='anthropic')
        >>> response = await client.complete("Hello", model="claude-sonnet-4")
    """
    # Get provider from parameter or environment
    if provider is None:
        provider = os.getenv('LLM_PROVIDER', 'openai')

    provider = provider.lower()

    correlation_id = get_correlation_id()

    logger.info(
        f"Creating LLM client",
        extra={
            'provider': provider,
            'correlation_id': correlation_id
        }
    )

    # OpenAI provider
    if provider == 'openai':
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable required for OpenAI provider"
            )

        client = OpenAIClient(api_key=api_key)

        logger.info(
            "OpenAI client created",
            extra={'correlation_id': correlation_id}
        )

        return client

    # Anthropic provider (future implementation)
    elif provider == 'anthropic':
        raise NotImplementedError(
            "Anthropic client coming soon in Week 6! "
            "For now, use provider='openai'"
        )

    # Ollama provider (local LLM)
    elif provider == 'ollama':
        from src.llm.ollama_client import OllamaClient

        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:40434')
        model = os.getenv('OLLAMA_MODEL', 'llama3.2:latest')

        client = OllamaClient(base_url=base_url, model=model)

        logger.info(
            "Ollama client created",
            extra={'correlation_id': correlation_id, 'model': model}
        )

        return client

    # Unknown provider
    else:
        raise ValueError(
            f"Unknown LLM provider: {provider}. "
            f"Supported providers: openai (more coming soon!)"
        )


# Convenience function for default provider
def get_default_llm_client():
    """
    Get LLM client using default provider from config.

    Equivalent to: get_llm_client()

    Returns:
        LLM client instance
    """
    return get_llm_client()
