"""
Unit Tests for QualityCache - TDD First

Tests written BEFORE implementation per TDD methodology.
These tests define the expected behavior of QualityCache.

Test Coverage:
- AC1: Promote to cache after positive feedback
- AC2: Demote from cache after negative feedback
- AC3: Agent mismatch = cache MISS
- AC4: Stale web search = cache MISS
- AC5: Cache hit shows verification badge
- AC6: Cache hit latency < 200ms
- AC7: Only PUBLIC/INTERNAL cached
- AC8: Show similarity score and original query
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional


# ============================================================================
# TEST: CacheEntry Data Class
# ============================================================================

class TestCacheEntry:
    """Tests for CacheEntry data structure."""

    def test_cache_entry_creation(self):
        """CacheEntry should store all required fields."""
        from src.cache.quality_cache import CacheEntry, QueryType

        entry = CacheEntry(
            query_text="What is SOLID?",
            response="SOLID is a set of principles...",
            agent_used="claude",
            contains_web_search=False,
            query_type=QueryType.DEFINITION,
            confidence=0.95,
            user_verified=True,
            positive_feedback_count=1,
            negative_feedback_count=0,
            user_id="user123",
            created_at=datetime.now(timezone.utc),
            last_served=datetime.now(timezone.utc),
            serve_count=0,
            privacy_level="PUBLIC"
        )

        assert entry.query_text == "What is SOLID?"
        assert entry.agent_used == "claude"
        assert entry.user_verified is True

    def test_quality_score_calculation_verified(self):
        """Verified entries should have high quality score."""
        from src.cache.quality_cache import CacheEntry, QueryType

        entry = CacheEntry(
            query_text="test",
            response="test response",
            agent_used="claude",
            contains_web_search=False,
            query_type=QueryType.FACTUAL,
            confidence=0.9,
            user_verified=True,
            positive_feedback_count=2,
            negative_feedback_count=0,
            user_id="user123",
            created_at=datetime.now(timezone.utc),
            last_served=datetime.now(timezone.utc),
            serve_count=0,
            privacy_level="PUBLIC"
        )

        # Verified + high confidence + positive feedback = high score
        assert entry.quality_score >= 0.9

    def test_quality_score_drops_with_negative_feedback(self):
        """Quality score should drop with negative feedback."""
        from src.cache.quality_cache import CacheEntry, QueryType

        entry = CacheEntry(
            query_text="test",
            response="test response",
            agent_used="claude",
            contains_web_search=False,
            query_type=QueryType.FACTUAL,
            confidence=0.9,
            user_verified=False,
            positive_feedback_count=0,
            negative_feedback_count=3,  # Too many downvotes
            user_id="user123",
            created_at=datetime.now(timezone.utc),
            last_served=datetime.now(timezone.utc),
            serve_count=0,
            privacy_level="PUBLIC"
        )

        # Too many downvotes = zero quality
        assert entry.quality_score == 0.0

    def test_ttl_hours_definition_query(self):
        """Definition queries should have 7-day TTL."""
        from src.cache.quality_cache import CacheEntry, QueryType

        entry = CacheEntry(
            query_text="What is Python?",
            response="Python is...",
            agent_used="claude",
            contains_web_search=False,
            query_type=QueryType.DEFINITION,
            confidence=0.9,
            user_verified=True,
            positive_feedback_count=0,
            negative_feedback_count=0,
            user_id="user123",
            created_at=datetime.now(timezone.utc),
            last_served=datetime.now(timezone.utc),
            serve_count=0,
            privacy_level="PUBLIC"
        )

        assert entry.ttl_hours == 168  # 7 days

    def test_ttl_hours_web_search_query(self):
        """Web search queries should have 1-hour TTL."""
        from src.cache.quality_cache import CacheEntry, QueryType

        entry = CacheEntry(
            query_text="Latest news about AI",
            response="Recent developments...",
            agent_used="claude",
            contains_web_search=True,  # Web search involved
            query_type=QueryType.FACTUAL,
            confidence=0.9,
            user_verified=True,
            positive_feedback_count=0,
            negative_feedback_count=0,
            user_id="user123",
            created_at=datetime.now(timezone.utc),
            last_served=datetime.now(timezone.utc),
            serve_count=0,
            privacy_level="PUBLIC"
        )

        assert entry.ttl_hours == 1  # Only 1 hour for web search

    def test_ttl_hours_temporal_query_never_cached(self):
        """Temporal queries should never be cached (TTL=0)."""
        from src.cache.quality_cache import CacheEntry, QueryType

        entry = CacheEntry(
            query_text="What happened today?",
            response="Today's events...",
            agent_used="claude",
            contains_web_search=False,
            query_type=QueryType.TEMPORAL,
            confidence=0.9,
            user_verified=True,
            positive_feedback_count=0,
            negative_feedback_count=0,
            user_id="user123",
            created_at=datetime.now(timezone.utc),
            last_served=datetime.now(timezone.utc),
            serve_count=0,
            privacy_level="PUBLIC"
        )

        assert entry.ttl_hours == 0  # Never cache temporal

    def test_is_valid_for_request_agent_mismatch(self):
        """Cache entry should be invalid if agent doesn't match request."""
        from src.cache.quality_cache import CacheEntry, QueryType

        entry = CacheEntry(
            query_text="Explain recursion",
            response="Recursion is...",
            agent_used="claude",  # Cached from Claude
            contains_web_search=False,
            query_type=QueryType.FACTUAL,
            confidence=0.9,
            user_verified=True,
            positive_feedback_count=1,
            negative_feedback_count=0,
            user_id="user123",
            created_at=datetime.now(timezone.utc),
            last_served=datetime.now(timezone.utc),
            serve_count=0,
            privacy_level="PUBLIC"
        )

        # User requested Ollama, but cache has Claude response
        assert entry.is_valid_for_request(requested_agent="ollama") is False

        # User requested "auto" - any agent is fine
        assert entry.is_valid_for_request(requested_agent=None) is True
        assert entry.is_valid_for_request(requested_agent="auto") is True

    def test_is_valid_for_request_expired_entry(self):
        """Expired cache entries should be invalid."""
        from src.cache.quality_cache import CacheEntry, QueryType

        # Entry created 25 hours ago (factual TTL is 24 hours)
        entry = CacheEntry(
            query_text="How does async work?",
            response="Async allows...",
            agent_used="claude",
            contains_web_search=False,
            query_type=QueryType.FACTUAL,  # 24hr TTL
            confidence=0.9,
            user_verified=True,
            positive_feedback_count=1,
            negative_feedback_count=0,
            user_id="user123",
            created_at=datetime.now(timezone.utc) - timedelta(hours=25),
            last_served=datetime.now(timezone.utc),
            serve_count=0,
            privacy_level="PUBLIC"
        )

        assert entry.is_valid_for_request(requested_agent=None) is False


# ============================================================================
# TEST: QualityCache Class
# ============================================================================

class TestQualityCacheInit:
    """Tests for QualityCache initialization."""

    @pytest.mark.asyncio
    async def test_init_creates_collection_if_not_exists(self):
        """QualityCache should create Weaviate collection on init."""
        with patch('src.cache.quality_cache.WeaviateClient') as mock_weaviate:
            with patch('src.cache.quality_cache.OpenAIEmbeddings') as mock_embeddings:
                mock_client = MagicMock()
                mock_client.collection_exists.return_value = False
                mock_weaviate.return_value = mock_client

                mock_emb = MagicMock()
                mock_embeddings.return_value = mock_emb

                from src.cache.quality_cache import QualityCache
                cache = QualityCache()

                mock_client.collection_exists.assert_called_with("ACMS_QualityCache_v1")

    def test_similarity_threshold_is_strict(self):
        """Similarity threshold should be 0.95 (stricter than old 0.90)."""
        with patch('src.cache.quality_cache.WeaviateClient'):
            with patch('src.cache.quality_cache.OpenAIEmbeddings'):
                from src.cache.quality_cache import QualityCache
                cache = QualityCache()
                assert cache.SIMILARITY_THRESHOLD == 0.95


class TestQualityCacheGet:
    """Tests for QualityCache.get() method - cache lookup."""

    @pytest.mark.asyncio
    async def test_get_returns_none_for_no_match(self):
        """Cache should return None when no similar query exists."""
        with patch('src.cache.quality_cache.WeaviateClient') as mock_weaviate:
            with patch('src.cache.quality_cache.OpenAIEmbeddings') as mock_embeddings:
                mock_client = MagicMock()
                mock_client.semantic_search.return_value = []
                mock_weaviate.return_value = mock_client

                mock_emb = MagicMock()
                mock_emb.generate_embedding.return_value = [0.1] * 1536
                mock_embeddings.return_value = mock_emb

                from src.cache.quality_cache import QualityCache
                cache = QualityCache()

                result = await cache.get("Unique query never asked", "user123")
                assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_none_for_low_similarity(self):
        """Cache should return None if similarity < 0.95."""
        with patch('src.cache.quality_cache.WeaviateClient') as mock_weaviate:
            with patch('src.cache.quality_cache.OpenAIEmbeddings') as mock_embeddings:
                mock_client = MagicMock()
                # Distance 0.10 = similarity 0.90 (below 0.95 threshold)
                mock_client.semantic_search.return_value = [{
                    "distance": 0.10,
                    "properties": {
                        "query_text": "What is Python?",
                        "response": "Python is...",
                        "agent_used": "claude",
                        "user_id": "user123",
                        "user_verified": True,
                        "confidence": 0.9,
                        "negative_feedback_count": 0,
                        "query_type": "definition",
                        "contains_web_search": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "privacy_level": "PUBLIC"
                    }
                }]
                mock_weaviate.return_value = mock_client

                mock_emb = MagicMock()
                mock_emb.generate_embedding.return_value = [0.1] * 1536
                mock_embeddings.return_value = mock_emb

                from src.cache.quality_cache import QualityCache
                cache = QualityCache()

                result = await cache.get("What is Python programming?", "user123")
                assert result is None  # Similarity 0.90 < 0.95 threshold

    @pytest.mark.asyncio
    async def test_get_returns_none_for_different_user(self):
        """Cache should return None for different user (privacy isolation)."""
        with patch('src.cache.quality_cache.WeaviateClient') as mock_weaviate:
            with patch('src.cache.quality_cache.OpenAIEmbeddings') as mock_embeddings:
                mock_client = MagicMock()
                mock_client.semantic_search.return_value = [{
                    "distance": 0.02,  # High similarity
                    "properties": {
                        "query_text": "What is Python?",
                        "response": "Python is...",
                        "agent_used": "claude",
                        "user_id": "other_user",  # Different user!
                        "user_verified": True,
                        "confidence": 0.9,
                        "negative_feedback_count": 0,
                        "query_type": "definition",
                        "contains_web_search": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "privacy_level": "PUBLIC"
                    }
                }]
                mock_weaviate.return_value = mock_client

                mock_emb = MagicMock()
                mock_emb.generate_embedding.return_value = [0.1] * 1536
                mock_embeddings.return_value = mock_emb

                from src.cache.quality_cache import QualityCache
                cache = QualityCache()

                result = await cache.get("What is Python?", "user123")
                assert result is None  # Different user = no access

    @pytest.mark.asyncio
    async def test_get_returns_none_for_agent_mismatch(self):
        """Cache should return None if requested agent doesn't match cached."""
        with patch('src.cache.quality_cache.WeaviateClient') as mock_weaviate:
            with patch('src.cache.quality_cache.OpenAIEmbeddings') as mock_embeddings:
                mock_client = MagicMock()
                mock_client.semantic_search.return_value = [{
                    "distance": 0.02,  # High similarity
                    "properties": {
                        "query_text": "What is Python?",
                        "response": "Python is...",
                        "agent_used": "claude",  # Cached from Claude
                        "user_id": "user123",
                        "user_verified": True,
                        "confidence": 0.9,
                        "negative_feedback_count": 0,
                        "query_type": "definition",
                        "contains_web_search": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "privacy_level": "PUBLIC"
                    }
                }]
                mock_weaviate.return_value = mock_client

                mock_emb = MagicMock()
                mock_emb.generate_embedding.return_value = [0.1] * 1536
                mock_embeddings.return_value = mock_emb

                from src.cache.quality_cache import QualityCache
                cache = QualityCache()

                # User requested Ollama
                result = await cache.get("What is Python?", "user123", requested_agent="ollama")
                assert result is None  # Agent mismatch

    @pytest.mark.asyncio
    async def test_get_returns_hit_for_valid_entry(self):
        """Cache should return hit for valid, high-similarity entry."""
        with patch('src.cache.quality_cache.WeaviateClient') as mock_weaviate:
            with patch('src.cache.quality_cache.OpenAIEmbeddings') as mock_embeddings:
                mock_client = MagicMock()
                mock_client.semantic_search.return_value = [{
                    "distance": 0.02,  # Similarity 0.98
                    "properties": {
                        "query_text": "What is Python?",
                        "response": "Python is a programming language...",
                        "agent_used": "claude",
                        "user_id": "user123",
                        "user_verified": True,
                        "confidence": 0.95,
                        "positive_feedback_count": 2,
                        "negative_feedback_count": 0,
                        "query_type": "definition",
                        "contains_web_search": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "privacy_level": "PUBLIC"
                    }
                }]
                mock_weaviate.return_value = mock_client

                mock_emb = MagicMock()
                mock_emb.generate_embedding.return_value = [0.1] * 1536
                mock_embeddings.return_value = mock_emb

                from src.cache.quality_cache import QualityCache
                cache = QualityCache()

                result = await cache.get("Tell me about Python", "user123")

                assert result is not None
                assert result["from_cache"] is True
                assert result["response"] == "Python is a programming language..."
                assert result["cache_similarity"] == pytest.approx(0.98, abs=0.01)
                assert result["original_query"] == "What is Python?"
                assert result["user_verified"] is True


class TestQualityCachePromote:
    """Tests for QualityCache.promote_to_cache() method."""

    @pytest.mark.asyncio
    async def test_promote_creates_cache_entry(self):
        """Promoting should create entry in Weaviate with user_verified=True."""
        with patch('src.cache.quality_cache.WeaviateClient') as mock_weaviate:
            with patch('src.cache.quality_cache.OpenAIEmbeddings') as mock_embeddings:
                with patch('src.cache.quality_cache.get_query_history_by_id') as mock_get_query:
                    mock_client = MagicMock()
                    mock_client.insert_vector.return_value = "new-cache-id"
                    mock_weaviate.return_value = mock_client

                    mock_emb = MagicMock()
                    mock_emb.generate_embedding.return_value = [0.1] * 1536
                    mock_embeddings.return_value = mock_emb

                    # Mock query history record
                    mock_get_query.return_value = {
                        "id": "query-123",
                        "query": "What is SOLID?",
                        "response": "SOLID stands for...",
                        "response_source": "claude",
                        "contains_web_search": False,
                        "privacy_level": "PUBLIC"
                    }

                    from src.cache.quality_cache import QualityCache
                    cache = QualityCache()

                    result = await cache.promote_to_cache("query-123", "user123")

                    assert result is True
                    mock_client.insert_vector.assert_called_once()
                    # Verify user_verified is True in the call
                    call_args = mock_client.insert_vector.call_args
                    assert call_args[1]["data"]["user_verified"] is True

    @pytest.mark.asyncio
    async def test_promote_rejects_confidential_privacy(self):
        """Should not cache CONFIDENTIAL or LOCAL_ONLY responses."""
        with patch('src.cache.quality_cache.WeaviateClient') as mock_weaviate:
            with patch('src.cache.quality_cache.OpenAIEmbeddings') as mock_embeddings:
                with patch('src.cache.quality_cache.get_query_history_by_id') as mock_get_query:
                    mock_client = MagicMock()
                    mock_weaviate.return_value = mock_client

                    mock_emb = MagicMock()
                    mock_embeddings.return_value = mock_emb

                    # CONFIDENTIAL response
                    mock_get_query.return_value = {
                        "id": "query-123",
                        "query": "What is my password?",
                        "response": "Your password is...",
                        "response_source": "claude",
                        "privacy_level": "CONFIDENTIAL"  # Cannot cache!
                    }

                    from src.cache.quality_cache import QualityCache
                    cache = QualityCache()

                    result = await cache.promote_to_cache("query-123", "user123")

                    assert result is False
                    mock_client.insert_vector.assert_not_called()


class TestQualityCacheDemote:
    """Tests for QualityCache.demote_from_cache() method."""

    @pytest.mark.asyncio
    async def test_demote_increments_negative_count(self):
        """Demoting should increment negative_feedback_count."""
        with patch('src.cache.quality_cache.WeaviateClient') as mock_weaviate:
            with patch('src.cache.quality_cache.OpenAIEmbeddings') as mock_embeddings:
                mock_client = MagicMock()
                # Mock getting existing entry
                mock_client.get_by_id.return_value = {
                    "negative_feedback_count": 1
                }
                mock_weaviate.return_value = mock_client

                mock_emb = MagicMock()
                mock_embeddings.return_value = mock_emb

                from src.cache.quality_cache import QualityCache
                cache = QualityCache()

                result = await cache.demote_from_cache("cache-entry-123", "incorrect")

                assert result is True
                mock_client.update_properties.assert_called()

    @pytest.mark.asyncio
    async def test_demote_invalidates_after_threshold(self):
        """Entry should be invalidated after 3+ negative feedbacks."""
        with patch('src.cache.quality_cache.WeaviateClient') as mock_weaviate:
            with patch('src.cache.quality_cache.OpenAIEmbeddings') as mock_embeddings:
                mock_client = MagicMock()
                # Entry already has 2 negative feedbacks
                mock_client.get_by_id.return_value = {
                    "negative_feedback_count": 2
                }
                mock_weaviate.return_value = mock_client

                mock_emb = MagicMock()
                mock_embeddings.return_value = mock_emb

                from src.cache.quality_cache import QualityCache
                cache = QualityCache()

                result = await cache.demote_from_cache("cache-entry-123", "incorrect")

                # Should be deleted after reaching threshold
                mock_client.delete_by_id.assert_called_with(
                    "ACMS_QualityCache_v1", "cache-entry-123"
                )


class TestQualityCacheStats:
    """Tests for QualityCache statistics."""

    @pytest.mark.asyncio
    async def test_get_stats_returns_counts(self):
        """Stats should return entry counts and hit rates."""
        with patch('src.cache.quality_cache.WeaviateClient') as mock_weaviate:
            with patch('src.cache.quality_cache.OpenAIEmbeddings') as mock_embeddings:
                mock_client = MagicMock()
                mock_client.count_vectors.return_value = 150
                mock_weaviate.return_value = mock_client

                mock_emb = MagicMock()
                mock_embeddings.return_value = mock_emb

                from src.cache.quality_cache import QualityCache
                cache = QualityCache()
                cache._hits = 30
                cache._misses = 70

                stats = cache.get_stats()

                assert stats["total_entries"] == 150
                assert stats["hit_rate"] == 0.30
                assert stats["similarity_threshold"] == 0.95


# ============================================================================
# TEST: Cache Latency Requirements
# ============================================================================

class TestCacheLatency:
    """Tests for cache performance requirements (AC6)."""

    @pytest.mark.asyncio
    async def test_cache_hit_latency_under_200ms(self):
        """Cache hit should complete in under 200ms."""
        import time

        with patch('src.cache.quality_cache.WeaviateClient') as mock_weaviate:
            with patch('src.cache.quality_cache.OpenAIEmbeddings') as mock_embeddings:
                mock_client = MagicMock()
                mock_client.semantic_search.return_value = [{
                    "distance": 0.02,
                    "properties": {
                        "query_text": "What is Python?",
                        "response": "Python is...",
                        "agent_used": "claude",
                        "user_id": "user123",
                        "user_verified": True,
                        "confidence": 0.95,
                        "negative_feedback_count": 0,
                        "query_type": "definition",
                        "contains_web_search": False,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "privacy_level": "PUBLIC"
                    }
                }]
                mock_weaviate.return_value = mock_client

                mock_emb = MagicMock()
                mock_emb.generate_embedding.return_value = [0.1] * 1536
                mock_embeddings.return_value = mock_emb

                from src.cache.quality_cache import QualityCache
                cache = QualityCache()

                start = time.time()
                result = await cache.get("What is Python?", "user123")
                elapsed_ms = (time.time() - start) * 1000

                assert result is not None
                # Note: In unit tests with mocks, this will be fast
                # Real integration test should verify actual latency
                assert elapsed_ms < 200, f"Cache hit took {elapsed_ms}ms, expected < 200ms"


# ============================================================================
# TEST: Query Type Detection
# ============================================================================

class TestQueryTypeDetection:
    """Tests for detecting query type for TTL calculation."""

    def test_detect_definition_query(self):
        """'What is X?' should be detected as DEFINITION."""
        from src.cache.quality_cache import detect_query_type, QueryType

        assert detect_query_type("What is Python?") == QueryType.DEFINITION
        assert detect_query_type("Define recursion") == QueryType.DEFINITION
        assert detect_query_type("What does SOLID stand for?") == QueryType.DEFINITION

    def test_detect_temporal_query(self):
        """Queries about time/current events should be TEMPORAL."""
        from src.cache.quality_cache import detect_query_type, QueryType

        assert detect_query_type("What happened today?") == QueryType.TEMPORAL
        assert detect_query_type("What's the current price of Bitcoin?") == QueryType.TEMPORAL
        assert detect_query_type("Latest news about AI") == QueryType.TEMPORAL

    def test_detect_code_query(self):
        """Code generation requests should be CODE."""
        from src.cache.quality_cache import detect_query_type, QueryType

        assert detect_query_type("Write a Python function to sort a list") == QueryType.CODE
        assert detect_query_type("How do I implement binary search in JavaScript?") == QueryType.CODE

    def test_detect_creative_query(self):
        """Creative tasks should be CREATIVE (no cache)."""
        from src.cache.quality_cache import detect_query_type, QueryType

        assert detect_query_type("Write a poem about the ocean") == QueryType.CREATIVE
        assert detect_query_type("Create a story about a dragon") == QueryType.CREATIVE
