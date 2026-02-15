"""Tests for typed memory system - TDD: Write tests FIRST.

Phase 1: Memory Engine
Goal: Typed memories with explicit classification

Run with: PYTHONPATH=. pytest tests/unit/memory/test_memory_models.py -v
"""
import pytest
from uuid import uuid4
from datetime import datetime

# These imports will fail until we implement the models
from src.memory.models import (
    MemoryType,
    MemoryTier,
    PrivacyLevel,
    MemoryItem,
    CandidateMemory
)


class TestMemoryTypeEnum:
    """Test memory type classification enum."""

    def test_memory_type_has_episodic(self):
        """EPISODIC type for conversation turns, queries, events."""
        assert MemoryType.EPISODIC.value == "EPISODIC"

    def test_memory_type_has_semantic(self):
        """SEMANTIC type for stable facts and preferences."""
        assert MemoryType.SEMANTIC.value == "SEMANTIC"

    def test_memory_type_has_document(self):
        """DOCUMENT type for external docs, long content."""
        assert MemoryType.DOCUMENT.value == "DOCUMENT"

    def test_memory_type_has_cache_entry(self):
        """CACHE_ENTRY type for semantic cached answers."""
        assert MemoryType.CACHE_ENTRY.value == "CACHE_ENTRY"

    def test_memory_type_from_string(self):
        """Can create MemoryType from string."""
        assert MemoryType("SEMANTIC") == MemoryType.SEMANTIC
        assert MemoryType("EPISODIC") == MemoryType.EPISODIC


class TestMemoryTierEnum:
    """Test memory retention tier enum."""

    def test_tier_has_short(self):
        """SHORT tier: 30 days retention."""
        assert MemoryTier.SHORT.value == "SHORT"

    def test_tier_has_mid(self):
        """MID tier: 90 days retention."""
        assert MemoryTier.MID.value == "MID"

    def test_tier_has_long(self):
        """LONG tier: permanent retention."""
        assert MemoryTier.LONG.value == "LONG"


class TestPrivacyLevelEnum:
    """Test privacy classification enum."""

    def test_privacy_has_all_levels(self):
        """All four privacy levels must exist."""
        assert PrivacyLevel.PUBLIC.value == "PUBLIC"
        assert PrivacyLevel.INTERNAL.value == "INTERNAL"
        assert PrivacyLevel.CONFIDENTIAL.value == "CONFIDENTIAL"
        assert PrivacyLevel.LOCAL_ONLY.value == "LOCAL_ONLY"


class TestMemoryItem:
    """Test MemoryItem model."""

    def test_create_semantic_memory(self):
        """Can create a SEMANTIC memory (user fact)."""
        memory = MemoryItem(
            user_id=uuid4(),
            content="User prefers Python 3.11+ for new projects",
            memory_type=MemoryType.SEMANTIC
        )
        assert memory.memory_type == MemoryType.SEMANTIC
        assert memory.content == "User prefers Python 3.11+ for new projects"
        assert memory.memory_id is not None  # Auto-generated

    def test_create_episodic_memory_requires_conversation(self):
        """EPISODIC memories must have conversation_id."""
        # This should work - has conversation_id
        memory = MemoryItem(
            user_id=uuid4(),
            content="User asked about Python",
            memory_type=MemoryType.EPISODIC,
            conversation_id=uuid4()
        )
        assert memory.conversation_id is not None

    def test_episodic_without_conversation_raises_error(self):
        """EPISODIC without conversation_id should raise ValueError."""
        with pytest.raises(ValueError, match="EPISODIC.*conversation_id"):
            MemoryItem(
                user_id=uuid4(),
                content="User asked about Python",
                memory_type=MemoryType.EPISODIC
                # Missing conversation_id!
            )

    def test_semantic_memory_no_conversation_required(self):
        """SEMANTIC memories don't need conversation_id."""
        memory = MemoryItem(
            user_id=uuid4(),
            content="User likes dark mode",
            memory_type=MemoryType.SEMANTIC
            # No conversation_id - that's OK for SEMANTIC
        )
        assert memory.conversation_id is None

    def test_default_tier_is_short(self):
        """Default tier should be SHORT (30 days)."""
        memory = MemoryItem(
            user_id=uuid4(),
            content="Test",
            memory_type=MemoryType.SEMANTIC
        )
        assert memory.tier == MemoryTier.SHORT

    def test_default_privacy_is_internal(self):
        """Default privacy should be INTERNAL."""
        memory = MemoryItem(
            user_id=uuid4(),
            content="Test",
            memory_type=MemoryType.SEMANTIC
        )
        assert memory.privacy_level == PrivacyLevel.INTERNAL

    def test_confidence_score_bounds(self):
        """Confidence score must be between 0 and 1."""
        # Valid confidence
        memory = MemoryItem(
            user_id=uuid4(),
            content="Test",
            memory_type=MemoryType.SEMANTIC,
            confidence_score=0.85
        )
        assert memory.confidence_score == 0.85

        # Invalid: > 1
        with pytest.raises(ValueError):
            MemoryItem(
                user_id=uuid4(),
                content="Test",
                memory_type=MemoryType.SEMANTIC,
                confidence_score=1.5
            )

        # Invalid: < 0
        with pytest.raises(ValueError):
            MemoryItem(
                user_id=uuid4(),
                content="Test",
                memory_type=MemoryType.SEMANTIC,
                confidence_score=-0.1
            )

    def test_tags_default_to_empty_list(self):
        """Tags should default to empty list."""
        memory = MemoryItem(
            user_id=uuid4(),
            content="Test",
            memory_type=MemoryType.SEMANTIC
        )
        assert memory.tags == []

    def test_metadata_default_to_empty_dict(self):
        """Metadata should default to empty dict."""
        memory = MemoryItem(
            user_id=uuid4(),
            content="Test",
            memory_type=MemoryType.SEMANTIC
        )
        assert memory.metadata == {}

    def test_timestamps_auto_generated(self):
        """created_at and updated_at should be auto-generated."""
        memory = MemoryItem(
            user_id=uuid4(),
            content="Test",
            memory_type=MemoryType.SEMANTIC
        )
        assert isinstance(memory.created_at, datetime)
        assert isinstance(memory.updated_at, datetime)

    def test_memory_to_dict(self):
        """Memory should be serializable to dict."""
        user_id = uuid4()
        memory = MemoryItem(
            user_id=user_id,
            content="Test content",
            memory_type=MemoryType.SEMANTIC,
            tags=["test", "example"]
        )

        data = memory.model_dump()
        assert data["content"] == "Test content"
        assert data["memory_type"] == "SEMANTIC"
        assert data["tags"] == ["test", "example"]


class TestCandidateMemory:
    """Test CandidateMemory model for quality validation."""

    def test_create_candidate(self):
        """Can create a candidate memory for validation."""
        candidate = CandidateMemory(
            text="User prefers TypeScript over JavaScript",
            memory_type=MemoryType.SEMANTIC,
            source="extracted"
        )
        assert candidate.text == "User prefers TypeScript over JavaScript"
        assert candidate.source == "extracted"

    def test_candidate_sources(self):
        """Candidate can have different sources."""
        # User-provided
        c1 = CandidateMemory(text="test", memory_type=MemoryType.SEMANTIC, source="user")
        assert c1.source == "user"

        # AI-extracted
        c2 = CandidateMemory(text="test", memory_type=MemoryType.SEMANTIC, source="ai")
        assert c2.source == "ai"

        # System-extracted
        c3 = CandidateMemory(text="test", memory_type=MemoryType.SEMANTIC, source="extracted")
        assert c3.source == "extracted"

    def test_candidate_with_context(self):
        """Candidate can include context for validation."""
        candidate = CandidateMemory(
            text="User likes Python",
            memory_type=MemoryType.SEMANTIC,
            source="extracted",
            context={
                "conversation_id": str(uuid4()),
                "extraction_confidence": 0.9
            }
        )
        assert "conversation_id" in candidate.context
        assert candidate.context["extraction_confidence"] == 0.9
