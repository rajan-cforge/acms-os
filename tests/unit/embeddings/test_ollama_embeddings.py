"""
Tests for Ollama Embeddings Client

TDD Implementation - Tests written before implementation
Total: 16 tests

Purpose: Local 768-dimensional embeddings with Redis caching
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Import will fail until implementation exists - expected for TDD
try:
    from src.embeddings.ollama_embeddings import OllamaEmbeddings
except ImportError:
    OllamaEmbeddings = None


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

def test_default_dimensions():
    """Test OllamaEmbeddings has 768 dimensions by default"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings()

    assert embeddings.dimensions == 768


def test_default_model():
    """Test OllamaEmbeddings uses nomic-embed-text by default"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings()

    assert embeddings.model == "nomic-embed-text"


def test_custom_model():
    """Test OllamaEmbeddings with custom embedding model"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings(model="all-minilm")

    assert embeddings.model == "all-minilm"


def test_custom_base_url():
    """Test OllamaEmbeddings with custom Ollama URL"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings(base_url="http://custom:11434")

    assert embeddings.base_url == "http://custom:11434"


def test_cache_enabled_by_default():
    """Test caching is enabled by default"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings()

    assert embeddings.use_cache is True


def test_cache_can_be_disabled():
    """Test caching can be disabled"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings(use_cache=False)

    assert embeddings.use_cache is False


# ============================================================================
# EMBEDDING GENERATION TESTS
# ============================================================================

def test_generate_embedding_returns_list():
    """Test generate_embedding() returns a list of floats"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings(use_cache=False)

    # Mock Ollama API response
    mock_embedding = [0.1] * 768

    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"embedding": mock_embedding})

        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_session.return_value.post = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock())
        )

        result = embeddings.generate_embedding("Test text")

    assert isinstance(result, list)
    assert all(isinstance(x, float) for x in result)


def test_embedding_dimensions_match():
    """Test embedding has exactly 768 dimensions"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings(use_cache=False)

    mock_embedding = [0.1] * 768

    with patch('aiohttp.ClientSession') as mock_session:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"embedding": mock_embedding})

        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_session.return_value.post = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock())
        )

        result = embeddings.generate_embedding("Test text")

    assert len(result) == 768


def test_empty_text_error():
    """Test empty text raises ValueError"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings()

    with pytest.raises(ValueError, match="Text cannot be empty"):
        embeddings.generate_embedding("")


def test_whitespace_text_error():
    """Test whitespace-only text raises ValueError"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings()

    with pytest.raises(ValueError, match="Text cannot be empty"):
        embeddings.generate_embedding("   \n\t   ")


def test_long_text_truncation():
    """Test long text is truncated to 8000 chars"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings(use_cache=False)

    # Very long text (10000 chars)
    long_text = "a" * 10000
    captured_prompt = None

    mock_embedding = [0.1] * 768

    async def capture_post(url, json=None, **kwargs):
        nonlocal captured_prompt
        captured_prompt = json.get("prompt", "") if json else ""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"embedding": mock_embedding})
        return AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock())

    with patch('aiohttp.ClientSession') as mock_session:
        mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
        mock_session.return_value.__aexit__ = AsyncMock()
        mock_session.return_value.post = capture_post

        embeddings.generate_embedding(long_text)

    assert len(captured_prompt) <= 8000


# ============================================================================
# CACHING TESTS
# ============================================================================

def test_cache_hit():
    """Test cache hit returns cached embedding without API call"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings(use_cache=True)

    cached_embedding = [0.5] * 768

    # Mock Redis with cached value
    with patch.object(embeddings, '_get_cached_embedding', return_value=cached_embedding) as mock_cache:
        result = embeddings.generate_embedding("Cached text")

    mock_cache.assert_called_once()
    assert result == cached_embedding
    assert embeddings._cache_hits == 1


def test_cache_miss():
    """Test cache miss calls API and caches result"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings(use_cache=True)

    mock_embedding = [0.1] * 768

    with patch.object(embeddings, '_get_cached_embedding', return_value=None):
        with patch.object(embeddings, '_cache_embedding') as mock_cache_set:
            with patch('aiohttp.ClientSession') as mock_session:
                mock_response = AsyncMock()
                mock_response.status = 200
                mock_response.json = AsyncMock(return_value={"embedding": mock_embedding})

                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session.return_value)
                mock_session.return_value.__aexit__ = AsyncMock()
                mock_session.return_value.post = AsyncMock(
                    return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock())
                )

                result = embeddings.generate_embedding("New text")

    mock_cache_set.assert_called_once()
    assert embeddings._cache_misses == 1


def test_cache_key_includes_dimensions():
    """Test cache key includes dimensions to prevent mixing"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings()

    key = embeddings._get_cache_key("Test text")

    assert "768" in key or "emb:ollama:" in key


def test_cache_stats():
    """Test get_cache_stats() returns statistics"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings()
    embeddings._cache_hits = 10
    embeddings._cache_misses = 5

    stats = embeddings.get_cache_stats()

    assert stats["hits"] == 10
    assert stats["misses"] == 5
    assert stats["total"] == 15
    assert stats["hit_rate_percent"] == pytest.approx(66.7, rel=0.1)


# ============================================================================
# BATCH EMBEDDING TESTS
# ============================================================================

def test_batch_embeddings():
    """Test batch embedding generation"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings(use_cache=False)

    texts = ["Text 1", "Text 2", "Text 3"]
    mock_embeddings = [[0.1] * 768, [0.2] * 768, [0.3] * 768]

    # Mock to return each embedding sequentially
    call_count = 0

    def mock_generate(text):
        nonlocal call_count
        result = mock_embeddings[call_count]
        call_count += 1
        return result

    with patch.object(embeddings, 'generate_embedding', side_effect=mock_generate):
        results = embeddings.generate_embeddings_batch(texts)

    assert len(results) == 3
    assert all(len(e) == 768 for e in results)


def test_batch_max_size():
    """Test batch respects maximum size"""
    if OllamaEmbeddings is None:
        pytest.skip("OllamaEmbeddings not implemented yet")

    embeddings = OllamaEmbeddings()

    # Try to embed too many texts at once
    too_many_texts = ["text"] * 3000

    with pytest.raises(ValueError, match="Max.*batch"):
        embeddings.generate_embeddings_batch(too_many_texts)
