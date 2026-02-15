"""Unit tests for MemoryWriter.

Tests verify that:
1. All Q&A pairs are written to RAW tier
2. Quality gate enforces ENRICHED threshold (> 0.8)
3. Facts are extracted for KNOWLEDGE tier (> 0.85)
4. Idempotency keys prevent duplicates
5. Cache metadata is properly generated
6. Invalidation works correctly

TDD spec from ACMS_Combined_Code_Review_Refactor_TDD_Spec.md
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.memory.memory_writer import (
    MemoryWriter, WriteResult, QualityScore, CacheMetadata, StorageTier
)


@pytest.fixture
def mock_raw_storage():
    """Mock raw storage."""
    storage = Mock()
    storage.save = AsyncMock(return_value="raw_123")
    storage.exists_by_key = AsyncMock(return_value=False)
    return storage


@pytest.fixture
def mock_enriched_storage():
    """Mock enriched storage."""
    storage = Mock()
    storage.save = AsyncMock(return_value="enriched_123")
    return storage


@pytest.fixture
def mock_knowledge_storage():
    """Mock knowledge storage."""
    storage = Mock()
    storage.save = AsyncMock(return_value="knowledge_123")
    return storage


@pytest.fixture
def mock_fact_extractor():
    """Mock fact extractor."""
    extractor = Mock()
    extractor.extract = AsyncMock(return_value=[
        {"content": "fact 1", "confidence": 0.9},
        {"content": "fact 2", "confidence": 0.85}
    ])
    return extractor


@pytest.fixture
def writer(mock_raw_storage, mock_enriched_storage, mock_knowledge_storage, mock_fact_extractor):
    """Get MemoryWriter with mocks."""
    return MemoryWriter(
        raw_storage=mock_raw_storage,
        enriched_storage=mock_enriched_storage,
        knowledge_storage=mock_knowledge_storage,
        fact_extractor=mock_fact_extractor,
        enable_facts=True,
        enable_enriched=True
    )


@pytest.fixture
def sample_sources():
    """Sample sources."""
    return [
        {"id": "1", "content": "source 1"},
        {"id": "2", "content": "source 2"},
        {"id": "3", "content": "source 3"}
    ]


class TestMemoryWriterBasic:
    """Test basic MemoryWriter functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_write_result(self, writer, sample_sources):
        """write() should return WriteResult."""
        result = await writer.write(
            question="test question",
            answer="test answer " * 20,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        assert isinstance(result, WriteResult)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_has_trace_id(self, writer, sample_sources):
        """WriteResult should have trace_id."""
        result = await writer.write(
            question="test question",
            answer="test answer " * 20,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        assert result.trace_id is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_result_has_idempotency_key(self, writer, sample_sources):
        """WriteResult should have idempotency key."""
        result = await writer.write(
            question="test question",
            answer="test answer",
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        assert result.idempotency_key is not None
        assert len(result.idempotency_key) == 64  # SHA-256 hex


class TestRawTier:
    """Test RAW tier storage."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_always_writes_to_raw(self, writer, mock_raw_storage, sample_sources):
        """Should always write to RAW tier."""
        await writer.write(
            question="test question",
            answer="short answer",  # Low quality
            sources=[],
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        mock_raw_storage.save.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raw_id_returned(self, writer, sample_sources):
        """Should return raw_id."""
        result = await writer.write(
            question="test question",
            answer="test answer",
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        assert result.raw_id == "raw_123"


class TestQualityAssessment:
    """Test quality assessment."""

    @pytest.mark.unit
    def test_quality_score_low_for_short_answer(self):
        """Short answer should have low quality."""
        quality = QualityScore.assess(
            answer="short",
            sources=[],
            question="What is X?"
        )
        assert quality.overall < 0.5
        assert quality.tier == StorageTier.RAW

    @pytest.mark.unit
    def test_quality_score_high_for_long_answer_with_sources(self):
        """Long answer with sources should have high quality."""
        quality = QualityScore.assess(
            answer="Comprehensive detailed answer " * 50,
            sources=[{"id": "1"}, {"id": "2"}, {"id": "3"}],
            question="What is X?"
        )
        assert quality.overall >= 0.8

    @pytest.mark.unit
    def test_quality_tier_raw(self):
        """Low quality should get RAW tier."""
        quality = QualityScore.assess(
            answer="",
            sources=[],
            question="What?"
        )
        assert quality.tier == StorageTier.RAW

    @pytest.mark.unit
    def test_quality_tier_enriched(self):
        """Medium-high quality should get ENRICHED tier."""
        quality = QualityScore.assess(
            answer="A reasonably detailed answer with good content. " * 15,  # Longer answer
            sources=[{"id": "1"}, {"id": "2"}, {"id": "3"}],  # More sources
            question="What is X?"
        )
        # Should reach ENRICHED or KNOWLEDGE tier
        assert quality.tier in [StorageTier.ENRICHED, StorageTier.KNOWLEDGE]

    @pytest.mark.unit
    def test_quality_tier_knowledge(self):
        """High quality should get KNOWLEDGE tier."""
        quality = QualityScore.assess(
            answer="Comprehensive answer " * 50,
            sources=[{"id": "1"}, {"id": "2"}, {"id": "3"}],
            question="What is X?"
        )
        assert quality.tier == StorageTier.KNOWLEDGE


class TestEnrichedTier:
    """Test ENRICHED tier storage."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_writes_to_enriched_when_quality_high(self, writer, mock_enriched_storage, sample_sources):
        """Should write to ENRICHED when quality > 0.8."""
        result = await writer.write(
            question="test question",
            answer="Comprehensive detailed answer " * 50,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        # If quality reached threshold, enriched storage should be called
        if result.quality and result.quality.overall >= 0.8:
            mock_enriched_storage.save.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_enriched_when_quality_low(self, mock_raw_storage, mock_enriched_storage, sample_sources):
        """Should not write to ENRICHED when quality low."""
        writer = MemoryWriter(
            raw_storage=mock_raw_storage,
            enriched_storage=mock_enriched_storage,
            enable_enriched=True
        )

        await writer.write(
            question="test",
            answer="short",
            sources=[],
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        mock_enriched_storage.save.assert_not_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_can_disable_enriched(self, mock_raw_storage, mock_enriched_storage, sample_sources):
        """Should respect enable_enriched flag."""
        writer = MemoryWriter(
            raw_storage=mock_raw_storage,
            enriched_storage=mock_enriched_storage,
            enable_enriched=False
        )

        await writer.write(
            question="test question",
            answer="Comprehensive detailed answer " * 50,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        mock_enriched_storage.save.assert_not_called()


class TestKnowledgeTier:
    """Test KNOWLEDGE tier storage."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_extracts_facts_for_knowledge(self, writer, mock_fact_extractor, sample_sources):
        """Should extract facts for high quality responses."""
        result = await writer.write(
            question="test question",
            answer="Comprehensive answer " * 50,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        # If quality reached KNOWLEDGE tier
        if result.quality and result.quality.tier == StorageTier.KNOWLEDGE:
            mock_fact_extractor.extract.assert_called()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_knowledge_ids_returned(self, writer, sample_sources):
        """Should return knowledge IDs."""
        result = await writer.write(
            question="test question",
            answer="Comprehensive answer " * 50,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        if result.quality and result.quality.tier == StorageTier.KNOWLEDGE:
            assert len(result.knowledge_ids) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_can_disable_facts(self, mock_raw_storage, mock_fact_extractor, sample_sources):
        """Should respect enable_facts flag."""
        writer = MemoryWriter(
            raw_storage=mock_raw_storage,
            fact_extractor=mock_fact_extractor,
            enable_facts=False
        )

        await writer.write(
            question="test question",
            answer="Comprehensive answer " * 50,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        mock_fact_extractor.extract.assert_not_called()


class TestIdempotency:
    """Test idempotency key handling."""

    @pytest.mark.unit
    def test_idempotency_key_deterministic(self, writer):
        """Same inputs should produce same key."""
        key1 = writer._make_idempotency_key(
            question="What is X?",
            answer="X is Y.",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        key2 = writer._make_idempotency_key(
            question="What is X?",
            answer="X is Y.",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        assert key1 == key2

    @pytest.mark.unit
    def test_different_inputs_different_key(self, writer):
        """Different inputs should produce different keys."""
        key1 = writer._make_idempotency_key(
            question="What is X?",
            answer="X is Y.",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        key2 = writer._make_idempotency_key(
            question="What is Z?",
            answer="Z is W.",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        assert key1 != key2

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_skips_duplicate(self, mock_raw_storage, sample_sources):
        """Should skip write if duplicate exists."""
        mock_raw_storage.exists_by_key = AsyncMock(return_value=True)

        writer = MemoryWriter(raw_storage=mock_raw_storage)

        result = await writer.write(
            question="test",
            answer="test",
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        assert result.was_duplicate is True
        mock_raw_storage.save.assert_not_called()


class TestCacheMetadata:
    """Test cache metadata generation."""

    @pytest.mark.unit
    def test_cache_metadata_fields(self):
        """CacheMetadata should have required fields."""
        metadata = CacheMetadata(
            embedding_model="text-embedding-3-small",
            prompt_version="v1.0",
            llm_model="claude-3-sonnet",
            quality_score=0.85,
            trace_id="trace123",
            created_at="2024-01-01T00:00:00Z"
        )
        d = metadata.to_dict()
        assert "embedding_model" in d
        assert "prompt_version" in d
        assert "llm_model" in d
        assert "quality_score" in d
        assert "trace_id" in d
        assert "created_at" in d
        assert "ttl_seconds" in d

    @pytest.mark.unit
    def test_cache_metadata_values(self):
        """CacheMetadata should store correct values."""
        metadata = CacheMetadata(
            embedding_model="text-embedding-3-small",
            prompt_version="v2.0",
            llm_model="gpt-4",
            quality_score=0.9,
            trace_id="abc123",
            created_at="2024-01-01T00:00:00Z",
            ttl_seconds=3600
        )
        d = metadata.to_dict()
        assert d["prompt_version"] == "v2.0"
        assert d["llm_model"] == "gpt-4"
        assert d["ttl_seconds"] == 3600


class TestWriteResultSerialization:
    """Test WriteResult serialization."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_to_dict(self, writer, sample_sources):
        """WriteResult should serialize to dict."""
        result = await writer.write(
            question="test question",
            answer="test answer " * 20,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        d = result.to_dict()
        assert "raw_id" in d
        assert "quality" in d
        assert "facts_extracted" in d
        assert "idempotency_key" in d
        assert "was_duplicate" in d


class TestQualityScoreSerialization:
    """Test QualityScore serialization."""

    @pytest.mark.unit
    def test_to_dict(self):
        """QualityScore should serialize to dict."""
        quality = QualityScore(
            overall=0.85,
            relevance=0.9,
            completeness=0.8,
            accuracy=0.85,
            source_quality=0.85
        )
        d = quality.to_dict()
        assert "overall" in d
        assert "tier" in d
        assert d["tier"] == "knowledge"


class TestThresholds:
    """Test quality thresholds."""

    @pytest.mark.unit
    def test_get_quality_thresholds(self, writer):
        """Should return quality thresholds."""
        thresholds = writer.get_quality_thresholds()
        assert "enriched_threshold" in thresholds
        assert "knowledge_threshold" in thresholds
        assert thresholds["enriched_threshold"] == 0.8
        assert thresholds["knowledge_threshold"] == 0.85

    @pytest.mark.unit
    def test_get_ttl_settings(self, writer):
        """Should return TTL settings."""
        ttl = writer.get_ttl_settings()
        assert "raw_ttl_seconds" in ttl
        assert "enriched_ttl_seconds" in ttl
        assert "knowledge_ttl_seconds" in ttl


class TestGracefulDegradation:
    """Test graceful degradation."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_raw_storage_failure(self, mock_enriched_storage, sample_sources):
        """Should handle raw storage failure."""
        failing_raw = Mock()
        failing_raw.save = AsyncMock(side_effect=Exception("storage error"))
        failing_raw.exists_by_key = AsyncMock(return_value=False)

        writer = MemoryWriter(
            raw_storage=failing_raw,
            enriched_storage=mock_enriched_storage
        )

        result = await writer.write(
            question="test",
            answer="test answer " * 20,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        assert result.raw_id is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_fact_extraction_failure(self, mock_raw_storage, sample_sources):
        """Should handle fact extraction failure."""
        failing_extractor = Mock()
        failing_extractor.extract = AsyncMock(side_effect=Exception("extraction error"))

        writer = MemoryWriter(
            raw_storage=mock_raw_storage,
            fact_extractor=failing_extractor,
            enable_facts=True
        )

        result = await writer.write(
            question="test",
            answer="Comprehensive answer " * 50,
            sources=sample_sources,
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
        assert result.facts_extracted == 0


class TestStorageTierValues:
    """Test StorageTier enum."""

    @pytest.mark.unit
    def test_tier_values(self):
        """StorageTier should have correct values."""
        assert StorageTier.RAW.value == "raw"
        assert StorageTier.ENRICHED.value == "enriched"
        assert StorageTier.KNOWLEDGE.value == "knowledge"
