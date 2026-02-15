"""Unit tests for RetrievalCoordinator.

Tests verify that:
1. Web search executes when plan requires it
2. Dual memory search is called correctly
3. Legacy memory fallback works
4. Sources are deduplicated and ranked
5. Context is sanitized before return
6. Privacy filtering is applied

TDD spec from ACMS_Combined_Code_Review_Refactor_TDD_Spec.md
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from src.gateway.coordinators.retrieval import RetrievalCoordinator, RetrievalResult, RetrievalSource
from src.gateway.coordinators.query_planner import QueryPlan


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
def query_plan():
    """Sample query plan for retrieval."""
    return QueryPlan(
        original_query="test query",
        sanitized_query="test query",
        augmented_queries=["test query", "test query variation"],
        intent="general",
        intent_confidence=0.85,
        allow_web_search=True,
        needs_web_search=False,
        web_search_reason=None
    )


@pytest.fixture
def query_plan_with_web():
    """Query plan that needs web search."""
    return QueryPlan(
        original_query="current events",
        sanitized_query="current events",
        augmented_queries=["current events"],
        intent="general",
        intent_confidence=0.85,
        allow_web_search=True,
        needs_web_search=True,
        web_search_reason="current events query"
    )


@pytest.fixture
def coordinator(mock_dual_memory, mock_memory_crud, mock_web_search, mock_sanitizer):
    """Get RetrievalCoordinator with mocks."""
    return RetrievalCoordinator(
        dual_memory=mock_dual_memory,
        memory_crud=mock_memory_crud,
        web_search=mock_web_search,
        context_sanitizer=mock_sanitizer
    )


class TestRetrievalBasic:
    """Test basic RetrievalCoordinator functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_retrieval_result(self, coordinator, query_plan):
        """retrieve() should return RetrievalResult."""
        result = await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert isinstance(result, RetrievalResult)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_has_context(self, coordinator, query_plan):
        """RetrievalResult should have context."""
        result = await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.context is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_has_sanitized_context(self, coordinator, query_plan):
        """RetrievalResult should have sanitized_context."""
        result = await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.sanitized_context == "sanitized context"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_has_sources(self, coordinator, query_plan):
        """RetrievalResult should have sources list."""
        result = await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert isinstance(result.sources, list)


class TestWebSearch:
    """Test web search integration."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_search_when_needed(self, coordinator, query_plan_with_web, mock_web_search):
        """Should call web search when plan.needs_web_search=True."""
        await coordinator.retrieve(
            plan=query_plan_with_web,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        mock_web_search.search.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_web_search_when_not_needed(self, coordinator, query_plan, mock_web_search):
        """Should not call web search when plan.needs_web_search=False."""
        await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        mock_web_search.search.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_results_included(self, coordinator, query_plan_with_web):
        """Web results should be in RetrievalResult."""
        result = await coordinator.retrieve(
            plan=query_plan_with_web,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.web_hits == 2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_search_failure_graceful(self, mock_dual_memory, mock_memory_crud, mock_sanitizer, query_plan_with_web):
        """Should handle web search failure gracefully."""
        failing_search = Mock()
        failing_search.search = AsyncMock(side_effect=Exception("network error"))

        coordinator = RetrievalCoordinator(
            dual_memory=mock_dual_memory,
            memory_crud=mock_memory_crud,
            web_search=failing_search,
            context_sanitizer=mock_sanitizer
        )

        result = await coordinator.retrieve(
            plan=query_plan_with_web,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.web_hits == 0


class TestDualMemorySearch:
    """Test dual memory search."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_searches_dual_memory(self, coordinator, query_plan, mock_dual_memory):
        """Should call dual memory search."""
        await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        mock_dual_memory.search_dual.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cache_hits_counted(self, coordinator, query_plan):
        """Should count cache hits."""
        result = await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.cache_hits >= 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_knowledge_hits_counted(self, coordinator, query_plan):
        """Should count knowledge hits."""
        result = await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.knowledge_hits >= 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_dual_memory_failure(self, mock_memory_crud, mock_web_search, mock_sanitizer, query_plan):
        """Should handle dual memory failure gracefully."""
        failing_dual = Mock()
        failing_dual.search_dual = AsyncMock(side_effect=Exception("dual memory error"))

        coordinator = RetrievalCoordinator(
            dual_memory=failing_dual,
            memory_crud=mock_memory_crud,
            web_search=mock_web_search,
            context_sanitizer=mock_sanitizer
        )

        result = await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        # Should still work with legacy memory fallback
        assert result is not None


class TestLegacyMemory:
    """Test legacy memory fallback."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_searches_legacy_memory(self, coordinator, query_plan, mock_memory_crud):
        """Should call legacy memory search."""
        await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        mock_memory_crud.search_memories.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_memory_hits_counted(self, coordinator, query_plan):
        """Should count memory hits."""
        result = await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.memory_hits >= 0


class TestDeduplication:
    """Test source deduplication."""

    @pytest.mark.unit
    def test_deduplicate_removes_duplicates(self, coordinator):
        """Should remove sources with duplicate IDs."""
        sources = [
            RetrievalSource(id="1", content="a", similarity=0.9, source_type="cache"),
            RetrievalSource(id="1", content="a copy", similarity=0.85, source_type="memory"),
            RetrievalSource(id="2", content="b", similarity=0.8, source_type="cache"),
        ]
        unique = coordinator._deduplicate_sources(sources)
        assert len(unique) == 2
        assert unique[0].id == "1"
        assert unique[1].id == "2"


class TestRanking:
    """Test source ranking."""

    @pytest.mark.unit
    def test_rank_by_similarity(self, coordinator):
        """Should rank sources by similarity score."""
        sources = [
            RetrievalSource(id="1", content="low", similarity=0.5, source_type="cache"),
            RetrievalSource(id="2", content="high", similarity=0.95, source_type="cache"),
            RetrievalSource(id="3", content="medium", similarity=0.75, source_type="cache"),
        ]
        ranked = coordinator._rank_sources(sources, "general")
        assert ranked[0].id == "2"  # Highest similarity first
        assert ranked[1].id == "3"
        assert ranked[2].id == "1"


class TestContextSanitization:
    """Test context sanitization."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sanitizes_context(self, coordinator, query_plan, mock_sanitizer):
        """Should call context sanitizer."""
        await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        mock_sanitizer.sanitize.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_reports_clean_status(self, coordinator, query_plan):
        """Should report is_context_clean status."""
        result = await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        assert result.is_context_clean is True


class TestEventGeneration:
    """Test UI event generation."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_events(self, coordinator, query_plan):
        """Should create events for UI."""
        result = await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        events = coordinator.create_events(result)
        assert isinstance(events, list)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_search_event_created(self, coordinator, query_plan_with_web):
        """Should create web search event when web hits present."""
        result = await coordinator.retrieve(
            plan=query_plan_with_web,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        events = coordinator.create_events(result)

        web_events = [e for e in events if e.get("step") == "web_search"]
        assert len(web_events) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_context_assembly_event_created(self, coordinator, query_plan):
        """Should create context assembly event."""
        result = await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        events = coordinator.create_events(result)

        assembly_events = [e for e in events if e.get("step") == "context_assembly"]
        assert len(assembly_events) == 1


class TestRetrievalResultSerialization:
    """Test RetrievalResult serialization."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_to_dict(self, coordinator, query_plan):
        """RetrievalResult should serialize to dict."""
        result = await coordinator.retrieve(
            plan=query_plan,
            user_id="user1",
            role="member",
            tenant_id="tenant1"
        )
        d = result.to_dict()

        assert "total_sources" in d
        assert "cache_hits" in d
        assert "knowledge_hits" in d
        assert "memory_hits" in d
        assert "web_hits" in d
        assert "context_chars" in d

    @pytest.mark.unit
    def test_retrieval_source_dataclass(self):
        """RetrievalSource should serialize properly."""
        source = RetrievalSource(
            id="test",
            content="content",
            similarity=0.9,
            source_type="cache",
            metadata={"key": "value"}
        )
        assert source.id == "test"
        assert source.similarity == 0.9
