"""Ollama Embeddings Client - Local vector generation.

Generate 768-dimensional embeddings using Ollama-hosted models.
Uses nomic-embed-text by default for high-quality semantic search.

Features:
- 768-dimensional embeddings
- Redis caching for performance
- Batch embedding support
- Zero cost (local inference)

Note: Dimension difference from OpenAI (1536d)
- Ollama nomic-embed-text: 768d
- OpenAI text-embedding-3-small: 1536d
- Consider dimension when mixing embeddings
"""

import os
import json
import hashlib
import logging
import asyncio
from typing import List, Optional

import aiohttp

logger = logging.getLogger(__name__)

# Redis cache configuration
EMBEDDING_CACHE_TTL = int(os.getenv("EMBEDDING_CACHE_TTL", "86400"))  # 24 hours
EMBEDDING_CACHE_PREFIX = "emb:ollama:"

# Global Redis client (lazy initialized)
_redis_client = None


def get_redis_client():
    """Get or create Redis client for embedding cache."""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:40379")
            _redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            _redis_client.ping()
            logger.info(f"[OllamaEmbeddingCache] Connected to Redis at {redis_url}")
        except Exception as e:
            logger.warning(f"[OllamaEmbeddingCache] Redis not available: {e}. Caching disabled.")
            _redis_client = False  # Mark as unavailable
    return _redis_client if _redis_client else None


class OllamaEmbeddings:
    """Local embeddings using Ollama models.

    Generates 768-dimensional vectors for semantic search.
    Uses Redis caching to avoid redundant computations.

    Example:
        client = OllamaEmbeddings()
        embedding = client.generate_embedding("Hello world")
        # Returns list of 768 floats
    """

    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        use_cache: bool = True
    ):
        """Initialize Ollama embeddings client.

        Args:
            base_url: Ollama API URL (default: from env or localhost:40434)
            model: Embedding model (default: nomic-embed-text)
            use_cache: Enable Redis caching (default: True)
        """
        default_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:40434")
        self.base_url = (base_url or default_url).rstrip('/')

        self.model = model or os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
        self.dimensions = 768  # nomic-embed-text default
        self.use_cache = use_cache
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info(
            f"[OllamaEmbeddings] Initialized with {self.model} ({self.dimensions}d), "
            f"cache={'enabled' if use_cache else 'disabled'}"
        )

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text content + dimensions.

        Args:
            text: Input text

        Returns:
            str: Redis cache key
        """
        # Use MD5 hash for consistent, short keys
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"{EMBEDDING_CACHE_PREFIX}{self.dimensions}:{text_hash}"

    def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Try to get embedding from Redis cache.

        Args:
            text: Input text

        Returns:
            List[float] or None: Cached embedding or None if not found
        """
        if not self.use_cache:
            return None

        redis = get_redis_client()
        if not redis:
            return None

        try:
            cache_key = self._get_cache_key(text)
            cached = redis.get(cache_key)
            if cached:
                self._cache_hits += 1
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"[OllamaEmbeddingCache] Get failed: {e}")

        return None

    def _cache_embedding(self, text: str, embedding: List[float]):
        """Store embedding in Redis cache.

        Args:
            text: Input text
            embedding: Generated embedding vector
        """
        if not self.use_cache:
            return

        redis = get_redis_client()
        if not redis:
            return

        try:
            cache_key = self._get_cache_key(text)
            redis.setex(cache_key, EMBEDDING_CACHE_TTL, json.dumps(embedding))
        except Exception as e:
            logger.warning(f"[OllamaEmbeddingCache] Set failed: {e}")

    def get_cache_stats(self) -> dict:
        """Get cache hit/miss statistics.

        Returns:
            dict: Cache statistics
        """
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total": total,
            "hit_rate_percent": round(hit_rate, 1)
        }

    def generate_embedding(self, text: str) -> List[float]:
        """Generate 768-dimensional embedding (synchronous wrapper).

        Args:
            text: Input text to embed

        Returns:
            List[float]: 768-dimensional embedding vector

        Raises:
            ValueError: If text is empty
            RuntimeError: If embedding generation fails
        """
        # Run async method in event loop
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If called from async context, create a new task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        asyncio.run,
                        self._generate_embedding_async(text)
                    )
                    return future.result()
            else:
                return loop.run_until_complete(self._generate_embedding_async(text))
        except RuntimeError:
            # No event loop - create new one
            return asyncio.run(self._generate_embedding_async(text))

    async def _generate_embedding_async(self, text: str) -> List[float]:
        """Async embedding generation with caching.

        Args:
            text: Input text to embed

        Returns:
            List[float]: 768-dimensional embedding vector

        Raises:
            ValueError: If text is empty
            RuntimeError: If embedding generation fails
        """
        # Validation
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # Check cache first
        cached = self._get_cached_embedding(text)
        if cached is not None:
            logger.debug(f"[OllamaEmbeddingCache] HIT for {len(text)} char text")
            return cached

        self._cache_misses += 1

        # Truncate long text to prevent token limit issues
        MAX_CHARS = 8000  # ~2000 tokens
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS]
            logger.debug(f"[OllamaEmbeddings] Truncated text to {MAX_CHARS} chars")

        # Generate via Ollama API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/api/embeddings",
                    json={
                        "model": self.model,
                        "prompt": text
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise RuntimeError(
                            f"Ollama embedding failed: {resp.status} - {error_text}"
                        )

                    data = await resp.json()
                    embedding = data.get("embedding", [])

                    if not embedding:
                        raise RuntimeError("Ollama returned empty embedding")

                    if len(embedding) != self.dimensions:
                        logger.warning(
                            f"[OllamaEmbeddings] Unexpected dimensions: "
                            f"expected {self.dimensions}, got {len(embedding)}"
                        )

        except aiohttp.ClientError as e:
            raise RuntimeError(f"Ollama connection error: {e}")

        # Cache and return
        self._cache_embedding(text, embedding)

        logger.debug(
            f"[OllamaEmbeddings] Generated {len(embedding)}d embedding for "
            f"{len(text)} char text"
        )

        return embedding

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed (max 2048)

        Returns:
            List[List[float]]: List of embedding vectors

        Raises:
            ValueError: If batch size exceeds limit
        """
        MAX_BATCH = 2048

        if len(texts) > MAX_BATCH:
            raise ValueError(
                f"Max {MAX_BATCH} texts per batch, got {len(texts)}"
            )

        # Generate embeddings one at a time (Ollama doesn't support batch)
        embeddings = []
        for text in texts:
            embedding = self.generate_embedding(text)
            embeddings.append(embedding)

        return embeddings


if __name__ == "__main__":
    # Test Ollama embeddings
    print("Testing Ollama Embeddings...")

    try:
        client = OllamaEmbeddings()

        # Test single embedding
        text = "FastAPI is a modern Python web framework for building APIs"
        print(f"\nGenerating embedding for: '{text}'")

        embedding = client.generate_embedding(text)

        print(f"Embedding generated successfully")
        print(f"   Dimensions: {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}")
        print(f"   Sample magnitudes: min={min(embedding):.4f}, max={max(embedding):.4f}")

        # Test caching
        print(f"\nTesting cache...")
        embedding2 = client.generate_embedding(text)
        print(f"Cache stats: {client.get_cache_stats()}")

        print("\nAll tests passed!")

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
