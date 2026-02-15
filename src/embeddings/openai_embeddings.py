"""OpenAI Embeddings Client for ACMS with Redis Caching (P5).

Uses text-embedding-3-small model with 1536-dimensional embeddings.
Higher dimensions = better semantic representation for search quality.

P5 Enhancement: Redis cache layer to avoid redundant API calls.
- Cache key: hash of input text + dimensions
- TTL: 24 hours (configurable)
- Reduces OpenAI API costs significantly for repeated queries

Cost: ~$0.02 per 1M tokens (~$0.0001 per search)
Performance: ~100ms per API call, <5ms for cache hit

Dimensions: 1536 (upgraded from 768 on Dec 16, 2025)
"""

import os
import json
import hashlib
import logging
from typing import List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

# Redis cache configuration
EMBEDDING_CACHE_TTL = int(os.getenv("EMBEDDING_CACHE_TTL", "86400"))  # 24 hours default
EMBEDDING_CACHE_PREFIX = "emb:"

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
            logger.info(f"[EmbeddingCache] Connected to Redis at {redis_url}")
        except Exception as e:
            logger.warning(f"[EmbeddingCache] Redis not available: {e}. Caching disabled.")
            _redis_client = False  # Mark as unavailable
    return _redis_client if _redis_client else None


class OpenAIEmbeddings:
    """OpenAI embeddings client using text-embedding-3-small (768d).

    Features:
    - 768 dimensions (2x better than all-minilm 384d)
    - Fast API responses (~100ms)
    - High quality semantic search
    - $0.02 per 1M tokens

    Example:
        client = OpenAIEmbeddings()
        embedding = client.generate_embedding("FastAPI is a Python web framework")
        # Returns list of 768 floats
    """

    def __init__(self, api_key: str = None, use_cache: bool = True):
        """Initialize OpenAI embeddings client with optional Redis caching.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            use_cache: Enable Redis caching (default: True)

        Raises:
            ValueError: If API key not found
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY not found in environment. "
                "Please set it in .env or pass as argument."
            )

        self.client = OpenAI(api_key=self.api_key)
        self.model = "text-embedding-3-small"
        self.dimensions = 1536  # Upgraded from 768 for better semantic quality
        self.use_cache = use_cache
        self._cache_hits = 0
        self._cache_misses = 0

        logger.info(f"[OpenAI Embeddings] Initialized with {self.model} ({self.dimensions}d), cache={'enabled' if use_cache else 'disabled'}")

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text content + dimensions."""
        # Use MD5 hash for consistent, short keys
        # Include dimensions in key to prevent mixing different-dimension embeddings
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"{EMBEDDING_CACHE_PREFIX}{self.dimensions}:{text_hash}"

    def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Try to get embedding from Redis cache."""
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
            logger.warning(f"[EmbeddingCache] Get failed: {e}")

        return None

    def _cache_embedding(self, text: str, embedding: List[float]):
        """Store embedding in Redis cache."""
        if not self.use_cache:
            return

        redis = get_redis_client()
        if not redis:
            return

        try:
            cache_key = self._get_cache_key(text)
            redis.setex(cache_key, EMBEDDING_CACHE_TTL, json.dumps(embedding))
        except Exception as e:
            logger.warning(f"[EmbeddingCache] Set failed: {e}")

    def get_cache_stats(self) -> dict:
        """Get cache hit/miss statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        return {
            "hits": self._cache_hits,
            "misses": self._cache_misses,
            "total": total,
            "hit_rate_percent": round(hit_rate, 1)
        }

    def generate_embedding(self, text: str, use_chunking: bool = True) -> List[float]:
        """Generate 1536-dimensional embedding for text (with Redis caching).

        Args:
            text: Input text to embed (any length if use_chunking=True)
            use_chunking: If True, chunk long texts and average embeddings (default: True)

        Returns:
            List of 1536 floats representing the embedding vector

        Raises:
            ValueError: If text is empty
            RuntimeError: If embedding generation fails

        Performance: ~100ms per API call, <5ms for cache hit
        Cost: ~$0.00002 per 1K tokens (~500 chars), $0 for cache hits
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        # P5: Check cache first
        cached_embedding = self._get_cached_embedding(text)
        if cached_embedding is not None:
            logger.debug(f"[EmbeddingCache] HIT for {len(text)} char text")
            return cached_embedding

        self._cache_misses += 1

        # Estimate tokens (rough: 1 token ≈ 4 chars for English)
        estimated_tokens = len(text) // 4
        max_tokens = 8000  # Leave margin below 8192 limit

        # If text is short enough, generate embedding directly
        if estimated_tokens <= max_tokens:
            # Still truncate to be safe (32K chars ≈ 8K tokens)
            if len(text) > 32000:
                text = text[:32000]
                print(f"[OpenAI] Truncated text to 32K chars")

            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text,
                    dimensions=self.dimensions
                )

                embedding = response.data[0].embedding

                # Verify dimensions
                if len(embedding) != self.dimensions:
                    raise RuntimeError(
                        f"Expected {self.dimensions} dimensions, got {len(embedding)}"
                    )

                # P5: Cache the embedding
                self._cache_embedding(text, embedding)

                return embedding

            except Exception as e:
                print(f"[OpenAI Embeddings] Error: {e}")
                raise RuntimeError(f"Embedding generation failed: {e}")

        # Text is too long - use chunking strategy
        if not use_chunking:
            # Just truncate if chunking disabled
            text = text[:32000]
            print(f"[OpenAI] Truncated long text to 32K chars (chunking disabled)")
            return self.generate_embedding(text, use_chunking=False)

        # Chunk the text and average embeddings
        print(f"[OpenAI] Text too long ({estimated_tokens} tokens), using chunking strategy")
        avg_embedding = self._generate_chunked_embedding(text, max_tokens)

        # P5: Cache the averaged embedding for the full text
        self._cache_embedding(text, avg_embedding)

        return avg_embedding

    def _generate_chunked_embedding(self, text: str, max_tokens: int) -> List[float]:
        """Generate embedding for long text by chunking and averaging.

        Args:
            text: Long input text
            max_tokens: Maximum tokens per chunk

        Returns:
            Averaged embedding vector
        """
        import numpy as np

        # Calculate chunk size in chars (4 chars ≈ 1 token)
        max_chars = max_tokens * 4

        # Split text into chunks
        chunks = []
        for i in range(0, len(text), max_chars):
            chunk = text[i:i + max_chars]
            if chunk.strip():  # Skip empty chunks
                chunks.append(chunk)

        if not chunks:
            raise ValueError("No valid chunks after splitting text")

        print(f"[OpenAI] Split into {len(chunks)} chunks")

        # Generate embeddings for each chunk
        chunk_embeddings = []
        for i, chunk in enumerate(chunks, 1):
            print(f"[OpenAI] Processing chunk {i}/{len(chunks)}")
            embedding = self.generate_embedding(chunk, use_chunking=False)  # Disable recursion
            chunk_embeddings.append(embedding)

        # Average all chunk embeddings
        avg_embedding = np.mean(chunk_embeddings, axis=0).tolist()

        print(f"[OpenAI] Averaged {len(chunks)} chunk embeddings")

        return avg_embedding

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts (batch processing).

        Args:
            texts: List of texts to embed (max 2048 per batch)

        Returns:
            List of embeddings, each with 768 floats

        Raises:
            ValueError: If batch size exceeds 2048
            RuntimeError: If batch embedding fails

        Performance: ~200ms for 10 texts
        Cost: Same per-token rate as single embeddings
        """
        if len(texts) > 2048:
            raise ValueError(f"Max 2048 texts per batch, got {len(texts)}")

        # Truncate each text to 30K chars
        truncated = [t[:30000] if len(t) > 30000 else t for t in texts]

        try:
            response = self.client.embeddings.create(
                model=self.model,
                input=truncated,
                dimensions=self.dimensions
            )

            embeddings = [data.embedding for data in response.data]

            # Verify all embeddings have correct dimensions
            for i, emb in enumerate(embeddings):
                if len(emb) != self.dimensions:
                    raise RuntimeError(
                        f"Embedding {i}: expected {self.dimensions}d, got {len(emb)}d"
                    )

            return embeddings

        except Exception as e:
            print(f"[OpenAI Embeddings Batch] Error: {e}")
            raise RuntimeError(f"Batch embedding generation failed: {e}")


if __name__ == "__main__":
    # Test OpenAI embeddings
    print("Testing OpenAI Embeddings...")

    try:
        client = OpenAIEmbeddings()

        # Test single embedding
        text = "FastAPI is a modern Python web framework for building APIs"
        print(f"\nGenerating embedding for: '{text}'")

        embedding = client.generate_embedding(text)

        print(f"✅ Embedding generated successfully")
        print(f"   Dimensions: {len(embedding)}")
        print(f"   First 5 values: {embedding[:5]}")
        print(f"   Sample magnitudes: min={min(embedding):.4f}, max={max(embedding):.4f}")

        # Test batch embeddings
        print(f"\nTesting batch embeddings...")
        texts = [
            "Python async programming",
            "FastAPI REST API",
            "PostgreSQL database"
        ]

        embeddings = client.generate_embeddings_batch(texts)
        print(f"✅ Batch embeddings generated")
        print(f"   Count: {len(embeddings)}")
        print(f"   All 768d: {all(len(e) == 768 for e in embeddings)}")

        print("\n🎉 All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
