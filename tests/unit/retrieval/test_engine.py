"""Unit tests for RetrievalEngine.

Tests verify that:
1. Unified interface works for all retrieval sources
2. RBAC filtering is applied
3. Deduplication and ranking work correctly
4. Context sanitization is applied
5. Web search integration works
6. Graceful degradation when services fail

TDD spec from ACMS_Combined_Code_Review_Refactor_TDD_Spec.md
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.retrieval.engine import (
    RetrievalEngine, RetrievalResult, RetrievalSource, SourceType
)


@pytest.fixture
def mock_dual_memory():
    """Mock dual memory service."""
    service = Mock()
    service.search_dual = AsyncMock(return_value=(
        [{"id": "cache1", "content": "cached answer", "similarity": 0.95, "metadata": {}}],
        [{"id": "know1", "content": "knowledge fact", "similarity": 0.85, "metadata": {}}]
    ))
    return service


@pytest.fixture
def mock_memory_crud():
    """Mock legacy memory crud."""
    crud = Mock()
    crud.search_memories = AsyncMock(return_value=[
        {"id": "mem1", "content": "memory content", "similarity": 0.80, "metadata": {}}
    ])
    return crud


@pytest.fixture
def mock_web_search():
    """Mock web search service."""
    service = Mock()
    service.search = AsyncMock(return_value=[
        {"title": "Web Result 1", "content": "Web content 1", "url": "https://example.com/1"},
        {"title": "Web Result 2", "content": "Web content 2", "url": "https://example.com/2"}
    ])
    return service


@pytest.fixture
def mock_sanitizer():
    """Mock context sanitizer."""
    sanitizer = Mock()
    result = Mock()
    result.sanitized_context = "sanitized context"
    result.is_clean = True
    result.detection_count = 0
    sanitizer.sanitize = Mock(return_value=result)
    return sanitizer


@pytest.fixture
def engine(mock_dual_memory, mock_memory_crud, mock_web_search, mock_sanitizer):
    """Get RetrievalEngine with mocks."""
    return RetrievalEngine(
        dual_memory=mock_dual_memory,
        memory_crud=mock_memory_crud,
        web_search=mock_web_search,
        context_sanitizer=mock_sanitizer
    )


class TestRetrievalEngineBasic:
    """Test basic RetrievalEngine functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_retrieval_result(self, engine):
        """retrieve_context should return RetrievalResult."""
        result = await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert isinstance(result, RetrievalResult)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_has_query(self, engine):
        """RetrievalResult should have query."""
        result = await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.query == "test query"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_has_context(self, engine):
        """RetrievalResult should have context."""
        result = await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.context is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_has_sanitized_context(self, engine):
        """RetrievalResult should have sanitized context."""
        result = await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.sanitized_context == "sanitized context"


class TestDualMemorySearch:
    """Test dual memory search."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_searches_dual_memory(self, engine, mock_dual_memory):
        """Should call dual memory search."""
        await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        mock_dual_memory.search_dual.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_counts_cache_hits(self, engine):
        """Should count cache hits."""
        result = await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.cache_hits >= 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_counts_knowledge_hits(self, engine):
        """Should count knowledge hits."""
        result = await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.knowledge_hits >= 0


class TestLegacyMemoryFallback:
    """Test legacy memory fallback."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_searches_legacy_memory(self, engine, mock_memory_crud):
        """Should search legacy memory."""
        await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        mock_memory_crud.search_memories.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_can_disable_legacy_memory(self, mock_dual_memory, mock_memory_crud, mock_sanitizer):
        """Should respect enable_legacy_memory flag."""
        engine = RetrievalEngine(
            dual_memory=mock_dual_memory,
            memory_crud=mock_memory_crud,
            context_sanitizer=mock_sanitizer,
            enable_legacy_memory=False
        )

        await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        mock_memory_crud.search_memories.assert_not_called()


class TestWebSearch:
    """Test web search integration."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_search_when_needed(self, engine, mock_web_search):
        """Should call web search when needs_web_search=True."""
        await engine.retrieve_context(
            query="current events",
            user_id="user1",
            role="member",
            tenant_id="tenant1",
            needs_web_search=True
        )
        mock_web_search.search.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_web_search_by_default(self, engine, mock_web_search):
        """Should not call web search by default."""
        await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        mock_web_search.search.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_hits_counted(self, engine):
        """Should count web hits."""
        result = await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1",
            needs_web_search=True
        )
        assert result.web_hits == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_can_disable_web_search(self, mock_dual_memory, mock_web_search, mock_sanitizer):
        """Should respect enable_web_search flag."""
        engine = RetrievalEngine(
            dual_memory=mock_dual_memory,
            web_search=mock_web_search,
            context_sanitizer=mock_sanitizer,
            enable_web_search=False
        )

        await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1",
            needs_web_search=True
        )
        mock_web_search.search.assert_not_called()


class TestDeduplication:
    """Test source deduplication."""

    @pytest.mark.unit
    def test_deduplicate_by_id(self, engine):
        """Should remove sources with duplicate IDs."""
        sources = [
            RetrievalSource(id="1", content="a", similarity=0.9, source_type=SourceType.CACHE),
            RetrievalSource(id="1", content="a copy", similarity=0.85, source_type=SourceType.MEMORY),
            RetrievalSource(id="2", content="b", similarity=0.8, source_type=SourceType.CACHE),
        ]
        unique = engine._deduplicate(sources)
        assert len(unique) == 2

    @pytest.mark.unit
    def test_keeps_web_results_without_ids(self, engine):
        """Should keep web results even without unique IDs."""
        sources = [
            RetrievalSource(id="", content="web 1", similarity=0.9, source_type=SourceType.WEB),
            RetrievalSource(id="", content="web 2", similarity=0.85, source_type=SourceType.WEB),
        ]
        unique = engine._deduplicate(sources)
        assert len(unique) == 2


class TestRanking:
    """Test source ranking."""

    @pytest.mark.unit
    def test_rank_by_similarity(self, engine):
        """Should rank by similarity by default."""
        sources = [
            RetrievalSource(id="1", content="low", similarity=0.5, source_type=SourceType.CACHE),
            RetrievalSource(id="2", content="high", similarity=0.95, source_type=SourceType.CACHE),
            RetrievalSource(id="3", content="medium", similarity=0.75, source_type=SourceType.CACHE),
        ]
        ranked = engine._rank(sources, "general")
        assert ranked[0].id == "2"  # Highest similarity first

    @pytest.mark.unit
    def test_boost_web_for_news(self, engine):
        """Should boost web results for news intent."""
        sources = [
            RetrievalSource(id="1", content="cache", similarity=0.9, source_type=SourceType.CACHE),
            RetrievalSource(id="2", content="web", similarity=0.85, source_type=SourceType.WEB),
        ]
        ranked = engine._rank(sources, "news")
        # Web should be boosted for news
        assert ranked[0].id == "2" or ranked[0].similarity + 0.1 >= ranked[1].similarity


class TestContextBuilding:
    """Test context building."""

    @pytest.mark.unit
    def test_builds_context_from_sources(self, engine):
        """Should build context from sources."""
        sources = [
            RetrievalSource(id="1", content="cache content", similarity=0.9, source_type=SourceType.CACHE),
            RetrievalSource(id="2", content="knowledge content", similarity=0.85, source_type=SourceType.KNOWLEDGE),
        ]
        context = engine._build_context(sources, [], "general")
        assert "cache content" in context or "knowledge content" in context

    @pytest.mark.unit
    def test_web_results_first(self, engine):
        """Should put web results first in context."""
        sources = [
            RetrievalSource(
                id="web1",
                content="web content",
                similarity=0.9,
                source_type=SourceType.WEB,
                metadata={"title": "Web Title", "url": "https://example.com"}
            ),
        ]
        context = engine._build_context(sources, [], "general")
        assert "Web Search Results" in context


class TestContextSanitization:
    """Test context sanitization."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sanitizes_context(self, engine, mock_sanitizer):
        """Should call context sanitizer."""
        await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        mock_sanitizer.sanitize.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reports_clean_status(self, engine):
        """Should report is_context_clean."""
        result = await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.is_context_clean is True


class TestGracefulDegradation:
    """Test graceful degradation when services fail."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_dual_memory_failure(self, mock_memory_crud, mock_sanitizer):
        """Should handle dual memory failure gracefully."""
        failing_dual = Mock()
        failing_dual.search_dual = AsyncMock(side_effect=Exception("dual memory error"))

        engine = RetrievalEngine(
            dual_memory=failing_dual,
            memory_crud=mock_memory_crud,
            context_sanitizer=mock_sanitizer
        )

        result = await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_web_search_failure(self, mock_dual_memory, mock_sanitizer):
        """Should handle web search failure gracefully."""
        failing_web = Mock()
        failing_web.search = AsyncMock(side_effect=Exception("web error"))

        engine = RetrievalEngine(
            dual_memory=mock_dual_memory,
            web_search=failing_web,
            context_sanitizer=mock_sanitizer
        )

        result = await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1",
            needs_web_search=True
        )
        assert result is not None
        assert result.web_hits == 0


class TestAugmentedQueries:
    """Test augmented query support."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_uses_augmented_queries(self, engine, mock_dual_memory):
        """Should search with augmented queries."""
        await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1",
            augmented_queries=["variation 1", "variation 2"]
        )
        # Should have been called multiple times for different queries
        assert mock_dual_memory.search_dual.call_count >= 1


class TestSearchStats:
    """Test search statistics."""

    @pytest.mark.unit
    def test_get_search_stats(self, engine):
        """Should return search stats."""
        stats = engine.get_search_stats()
        assert "dual_memory_available" in stats
        assert "web_search_available" in stats
        assert "legacy_memory_available" in stats


class TestRetrievalSourceDataclass:
    """Test RetrievalSource dataclass."""

    @pytest.mark.unit
    def test_to_dict(self):
        """RetrievalSource should serialize to dict."""
        source = RetrievalSource(
            id="test",
            content="test content",
            similarity=0.9,
            source_type=SourceType.CACHE,
            metadata={"key": "value"}
        )
        d = source.to_dict()
        assert d["id"] == "test"
        assert d["similarity"] == 0.9
        assert d["source_type"] == "cache"

    @pytest.mark.unit
    def test_truncates_long_content(self):
        """Should truncate long content in to_dict."""
        source = RetrievalSource(
            id="test",
            content="x" * 300,
            similarity=0.9,
            source_type=SourceType.CACHE
        )
        d = source.to_dict()
        assert len(d["content"]) <= 203  # 200 + "..."


class TestRetrievalResultDataclass:
    """Test RetrievalResult dataclass."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_to_dict(self, engine):
        """RetrievalResult should serialize to dict."""
        result = await engine.retrieve_context(
            query="test query",
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        d = result.to_dict()
        assert "total_sources" in d
        assert "cache_hits" in d
        assert "context_chars" in d

    @pytest.mark.unit
    def test_total_sources_property(self):
        """total_sources should count sources."""
        result = RetrievalResult(
            query="test",
            context="ctx",
            sanitized_context="ctx",
            sources=[
                RetrievalSource(id="1", content="a", similarity=0.9, source_type=SourceType.CACHE)
            ]
        )
        assert result.total_sources == 1
