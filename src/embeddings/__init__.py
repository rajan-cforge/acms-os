"""Embeddings module for ACMS.

Provides a unified interface to get embeddings from either
OpenAI (if API key is set) or Ollama (default, free).
"""

import os
import logging

logger = logging.getLogger(__name__)

_embeddings_instance = None


def get_embeddings():
    """Get the appropriate embeddings provider.

    Returns OpenAI embeddings if OPENAI_API_KEY is set,
    otherwise returns Ollama embeddings (default for open-source).

    Returns:
        Embeddings client (OpenAIEmbeddings or OllamaEmbeddings)
    """
    global _embeddings_instance

    if _embeddings_instance is not None:
        return _embeddings_instance

    if os.getenv("OPENAI_API_KEY"):
        try:
            from src.embeddings.openai_embeddings import OpenAIEmbeddings
            _embeddings_instance = OpenAIEmbeddings()
            logger.info("[Embeddings] Using OpenAI embeddings (1536d)")
            return _embeddings_instance
        except Exception as e:
            logger.warning(f"[Embeddings] OpenAI failed: {e}, falling back to Ollama")

    # Default to Ollama (free, local)
    try:
        from src.embeddings.ollama_embeddings import OllamaEmbeddings
        _embeddings_instance = OllamaEmbeddings()
        logger.info("[Embeddings] Using Ollama embeddings (768d)")
        return _embeddings_instance
    except Exception as e:
        logger.error(f"[Embeddings] Ollama failed: {e}")
        raise ValueError(
            "No embedding provider available. "
            "Either set OPENAI_API_KEY or ensure Ollama is running."
        )
