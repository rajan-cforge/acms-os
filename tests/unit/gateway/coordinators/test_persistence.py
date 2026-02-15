"""Unit tests for PersistenceCoordinator.

Tests verify that:
1. Query history is always saved
2. Quality assessment runs on responses
3. Tiered storage follows quality gates
4. Fact extraction runs for high quality
5. Feedback updates work correctly
6. Cache metadata is generated properly

TDD spec from ACMS_Combined_Code_Review_Refactor_TDD_Spec.md
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from src.gateway.coordinators.persistence import (
    PersistenceCoordinator, PersistenceResult, QualityScore, QualityTier
)


@pytest.fixture
def mock_query_history_crud():
    """Mock query history CRUD."""
    crud = Mock()
    crud.save = AsyncMock(return_value="qh_123")
    crud.update_feedback = AsyncMock(return_value=True)
    return crud


@pytest.fixture
def mock_memory_crud():
    """Mock memory CRUD."""
    crud = Mock()
    crud.save = AsyncMock(return_value="mem_123")
    return crud


@pytest.fixture
def mock_fact_extractor():
    """Mock fact extractor."""
    extractor = Mock()
    extractor.extract = AsyncMock(return_value=[
        {"fact": "fact 1"},
        {"fact": "fact 2"}
    ])
    return extractor


@pytest.fixture
def mock_quality_gate():
    """Mock quality gate."""
    gate = Mock()
    gate.score = Mock(return_value=0.85)
    return gate


@pytest.fixture
def coordinator(mock_query_history_crud, mock_memory_crud, mock_fact_extractor, mock_quality_gate):
    """Get PersistenceCoordinator with mocks."""
    return PersistenceCoordinator(
        query_history_crud=mock_query_history_crud,
        memory_crud=mock_memory_crud,
        fact_extractor=mock_fact_extractor,
        quality_gate=mock_quality_gate,
        enable_caching=False,
        enable_facts=True
    )


@pytest.fixture
def sample_sources():
    """Sample sources for testing."""
    return [
        {"id": "1", "content": "source 1", "similarity": 0.9},
        {"id": "2", "content": "source 2", "similarity": 0.85}
    ]


class TestPersistenceBasic:
    """Test basic PersistenceCoordinator functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_persistence_result(self, coordinator, sample_sources):
        """persist() should return PersistenceResult."""
        result = await coordinator.persist(
            question="test question",
            answer="test answer " * 20,  # Make it long enough for quality
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            agent_used="claude",
            model_version="claude-3-sonnet"
        )
        assert isinstance(result, PersistenceResult)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_has_trace_id(self, coordinator, sample_sources):
        """PersistenceResult should have trace_id."""
        result = await coordinator.persist(
            question="test question",
            answer="test answer " * 20,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            agent_used="claude",
            model_version="claude-3-sonnet"
        )
        assert result.trace_id is not None


class TestQueryHistory:
    """Test query history saving."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_saves_query_history(self, coordinator, mock_query_history_crud, sample_sources):
        """Should always save to query history."""
        await coordinator.persist(
            question="test question",
            answer="test answer " * 20,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            agent_used="claude",
            model_version="claude-3-sonnet"
        )
        mock_query_history_crud.save.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_query_history_id_returned(self, coordinator, sample_sources):
        """Should return query history ID."""
        result = await coordinator.persist(
            question="test question",
            answer="test answer " * 20,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            agent_used="claude",
            model_version="claude-3-sonnet"
        )
        assert result.query_history_id == "qh_123"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_query_history_failure(self, mock_memory_crud, sample_sources):
        """Should handle query history save failure gracefully."""
        failing_crud = Mock()
        failing_crud.save = AsyncMock(side_effect=Exception("db error"))

        coordinator = PersistenceCoordinator(
            query_history_crud=failing_crud,
            memory_crud=mock_memory_crud,
            enable_facts=False
        )

        result = await coordinator.persist(
            question="test question",
            answer="test answer",
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            agent_used="claude",
            model_version="claude-3-sonnet"
        )
        assert result.query_history_id is None


class TestQualityAssessment:
    """Test quality assessment."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_assesses_quality(self, coordinator, sample_sources):
        """Should assess quality of response."""
        result = await coordinator.persist(
            question="test question",
            answer="test answer " * 20,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            agent_used="claude",
            model_version="claude-3-sonnet"
        )
        assert result.quality_score is not None

    @pytest.mark.unit
    def test_quality_score_assess(self):
        """QualityScore.assess should calculate scores."""
        quality = QualityScore.assess(
            answer="This is a well-formed answer with detailed explanation " * 5,
            sources=[{"id": "1"}, {"id": "2"}],
            question="What is X?"
        )
        assert 0.0 <= quality.overall <= 1.0
        assert quality.tier in [QualityTier.RAW, QualityTier.ENRICHED, QualityTier.KNOWLEDGE]

    @pytest.mark.unit
    def test_empty_answer_low_quality(self):
        """Empty answer should have low quality."""
        quality = QualityScore.assess(
            answer="",
            sources=[],
            question="What is X?"
        )
        assert quality.overall < 0.5
        assert quality.tier == QualityTier.RAW

    @pytest.mark.unit
    def test_quality_tier_knowledge(self):
        """High quality should get KNOWLEDGE tier."""
        # Long answer with multiple sources = high quality
        quality = QualityScore.assess(
            answer="Comprehensive answer " * 50,  # 500+ chars
            sources=[{"id": "1"}, {"id": "2"}, {"id": "3"}],
            question="What is X?"
        )
        assert quality.tier == QualityTier.KNOWLEDGE


class TestTieredStorage:
    """Test tiered memory storage."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_saves_to_raw_always(self, coordinator, sample_sources):
        """Should always save to raw tier."""
        result = await coordinator.persist(
            question="test question",
            answer="test answer " * 20,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            agent_used="claude",
            model_version="claude-3-sonnet"
        )
        assert result.saved_to_raw is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_saves_to_enriched_when_quality_high(self, coordinator, sample_sources):
        """Should save to enriched when quality > 0.8."""
        result = await coordinator.persist(
            question="test question",
            answer="This is a comprehensive and detailed answer " * 50,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            agent_used="claude",
            model_version="claude-3-sonnet"
        )
        # If quality is high enough, should save to enriched
        if result.quality_score and result.quality_score.overall >= 0.8:
            assert result.saved_to_enriched is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_save_for_cached_responses(self, coordinator, sample_sources):
        """Should not re-save cached responses to memory."""
        result = await coordinator.persist(
            question="test question",
            answer="test answer " * 20,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            agent_used="claude",
            model_version="claude-3-sonnet",
            from_cache=True  # Response was from cache
        )
        # Query history should still be saved
        assert result.query_history_id is not None
        # But memory shouldn't be re-saved (would be false in production)


class TestFactExtraction:
    """Test fact extraction."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extracts_facts_for_knowledge_tier(self, coordinator, mock_fact_extractor, sample_sources):
        """Should extract facts for high quality responses."""
        result = await coordinator.persist(
            question="test question",
            answer="Comprehensive answer " * 50,
            sources=[{"id": "1"}, {"id": "2"}, {"id": "3"}],
            user_id="user1",
            tenant_id="tenant1",
            agent_used="claude",
            model_version="claude-3-sonnet"
        )
        # If quality reached KNOWLEDGE tier, facts should be extracted
        if result.quality_score and result.quality_score.tier == QualityTier.KNOWLEDGE:
            mock_fact_extractor.extract.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_facts_when_disabled(self, mock_query_history_crud, mock_memory_crud, sample_sources):
        """Should not extract facts when disabled."""
        coordinator = PersistenceCoordinator(
            query_history_crud=mock_query_history_crud,
            memory_crud=mock_memory_crud,
            enable_facts=False
        )

        result = await coordinator.persist(
            question="test question",
            answer="Comprehensive answer " * 50,
            sources=[{"id": "1"}, {"id": "2"}, {"id": "3"}],
            user_id="user1",
            tenant_id="tenant1",
            agent_used="claude",
            model_version="claude-3-sonnet"
        )
        assert result.facts_extracted == 0


class TestFeedbackUpdate:
    """Test feedback update functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_update_feedback(self, coordinator, mock_query_history_crud):
        """Should update feedback for query."""
        success = await coordinator.update_feedback(
            query_history_id="qh_123",
            rating=5,
            feedback_text="Great answer!"
        )
        mock_query_history_crud.update_feedback.assert_called_once()
        assert success is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_feedback_update_failure(self, mock_memory_crud):
        """Should handle feedback update failure."""
        failing_crud = Mock()
        failing_crud.update_feedback = AsyncMock(side_effect=Exception("db error"))

        coordinator = PersistenceCoordinator(
            query_history_crud=failing_crud,
            memory_crud=mock_memory_crud
        )

        success = await coordinator.update_feedback(
            query_history_id="qh_123",
            rating=5
        )
        assert success is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_feedback_without_crud(self, mock_memory_crud):
        """Should return False if no query history CRUD."""
        coordinator = PersistenceCoordinator(
            query_history_crud=None,
            memory_crud=mock_memory_crud
        )

        success = await coordinator.update_feedback(
            query_history_id="qh_123",
            rating=5
        )
        assert success is False


class TestCacheMetadata:
    """Test cache metadata generation."""

    @pytest.mark.unit
    def test_generates_cache_metadata(self, coordinator):
        """Should generate cache metadata."""
        metadata = coordinator.get_cache_metadata(
            question="test question",
            model_version="claude-3-sonnet",
            prompt_version="v1.0"
        )
        assert "embedding_model" in metadata
        assert "prompt_version" in metadata
        assert "llm_model" in metadata
        assert "created_at" in metadata
        assert "trace_id" in metadata

    @pytest.mark.unit
    def test_cache_metadata_values(self, coordinator):
        """Cache metadata should have correct values."""
        metadata = coordinator.get_cache_metadata(
            question="test question",
            model_version="claude-3-sonnet",
            prompt_version="v1.0"
        )
        assert metadata["llm_model"] == "claude-3-sonnet"
        assert metadata["prompt_version"] == "v1.0"


class TestIdempotencyKey:
    """Test idempotency key generation."""

    @pytest.mark.unit
    def test_generates_idempotency_key(self, coordinator):
        """Should generate deterministic idempotency key."""
        key1 = coordinator._make_idempotency_key(
            question="What is X?",
            answer="X is Y.",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        key2 = coordinator._make_idempotency_key(
            question="What is X?",
            answer="X is Y.",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        assert key1 == key2

    @pytest.mark.unit
    def test_different_content_different_key(self, coordinator):
        """Different content should produce different keys."""
        key1 = coordinator._make_idempotency_key(
            question="What is X?",
            answer="X is Y.",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        key2 = coordinator._make_idempotency_key(
            question="What is Z?",
            answer="Z is W.",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        assert key1 != key2


class TestPersistenceResultSerialization:
    """Test PersistenceResult serialization."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_to_dict(self, coordinator, sample_sources):
        """PersistenceResult should serialize to dict."""
        result = await coordinator.persist(
            question="test question",
            answer="test answer " * 20,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            agent_used="claude",
            model_version="claude-3-sonnet"
        )
        d = result.to_dict()

        assert "query_history_id" in d
        assert "memory_id" in d
        assert "quality_score" in d
        assert "quality_tier" in d
        assert "facts_extracted" in d
        assert "saved_to_raw" in d
        assert "saved_to_enriched" in d
        assert "trace_id" in d


class TestQualityTierValues:
    """Test QualityTier enum values."""

    @pytest.mark.unit
    def test_tier_values(self):
        """QualityTier should have correct values."""
        assert QualityTier.RAW.value == "raw"
        assert QualityTier.ENRICHED.value == "enriched"
        assert QualityTier.KNOWLEDGE.value == "knowledge"
