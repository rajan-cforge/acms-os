"""Unit tests for CrossValidator.

Cognitive Principle: Error-Correcting Codes

The brain maintains consistency across memory stores. When the hippocampus
(Raw) and neocortex (Knowledge) have conflicting information, the brain
uses error-correcting mechanisms to resolve inconsistencies.

This module validates consistency between Raw and Knowledge entries
and flags potential inconsistencies for review.

TDD: Tests written BEFORE implementation.
Run with: PYTHONPATH=. pytest tests/unit/intelligence/test_cross_validator.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


# ============================================================
# TEST FIXTURES AND HELPERS
# ============================================================

@dataclass
class MockRawEntry:
    """Mock Raw entry for testing."""
    id: str
    content: str
    user_id: str
    created_at: datetime
    question: Optional[str] = None
    answer: Optional[str] = None
    embedding: Optional[List[float]] = None

    def __post_init__(self):
        if self.embedding is None:
            self.embedding = [0.5] * 1536


@dataclass
class MockKnowledgeEntry:
    """Mock Knowledge entry for testing."""
    id: str
    content: str
    user_id: str
    created_at: datetime
    source_ids: Optional[List[str]] = None
    confidence: float = 0.9
    embedding: Optional[List[float]] = None

    def __post_init__(self):
        if self.source_ids is None:
            self.source_ids = []
        if self.embedding is None:
            self.embedding = [0.5] * 1536


def create_raw_entry(
    id: str = "raw-1",
    content: str = "Python uses indentation for blocks.",
    created_at: datetime = None,
) -> MockRawEntry:
    """Create a mock raw entry."""
    return MockRawEntry(
        id=id,
        content=content,
        user_id="user-1",
        created_at=created_at or datetime.now(timezone.utc),
    )


def create_knowledge_entry(
    id: str = "knowledge-1",
    content: str = "Python uses indentation for blocks.",
    source_ids: List[str] = None,
    created_at: datetime = None,
) -> MockKnowledgeEntry:
    """Create a mock knowledge entry."""
    return MockKnowledgeEntry(
        id=id,
        content=content,
        user_id="user-1",
        source_ids=source_ids or [],
        created_at=created_at or datetime.now(timezone.utc),
    )


# ============================================================
# CROSS VALIDATOR CONFIG TESTS
# ============================================================

class TestCrossValidatorConfig:
    """Tests for CrossValidatorConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        from src.intelligence.cross_validator import CrossValidatorConfig

        config = CrossValidatorConfig()

        # Consistency threshold (below this = inconsistent)
        assert config.consistency_threshold == 0.70
        # Embedding similarity weight
        assert config.embedding_weight >= 0.4
        # Content similarity weight
        assert config.content_weight >= 0.3

    def test_custom_config(self):
        """Test custom configuration."""
        from src.intelligence.cross_validator import CrossValidatorConfig

        config = CrossValidatorConfig(
            consistency_threshold=0.80,
            embedding_weight=0.5,
        )

        assert config.consistency_threshold == 0.80


# ============================================================
# CONSISTENCY SCORE CALCULATION TESTS
# ============================================================

class TestConsistencyScoring:
    """Tests for consistency score calculation."""

    @pytest.fixture
    def validator(self):
        from src.intelligence.cross_validator import CrossValidator
        return CrossValidator()

    def test_identical_content_high_consistency(self, validator):
        """Test that identical content has high consistency."""
        raw = create_raw_entry(content="Python uses indentation for blocks.")
        knowledge = create_knowledge_entry(content="Python uses indentation for blocks.")

        score = validator._compute_content_similarity(
            raw.content, knowledge.content
        )

        assert score >= 0.95  # Nearly identical

    def test_similar_content_moderate_consistency(self, validator):
        """Test that similar content has moderate consistency."""
        raw = create_raw_entry(
            content="Python uses indentation instead of braces for code blocks."
        )
        knowledge = create_knowledge_entry(
            content="Python uses indentation for defining code blocks."
        )

        score = validator._compute_content_similarity(
            raw.content, knowledge.content
        )

        assert 0.4 < score < 0.95  # Similar but not identical

    def test_contradictory_content_low_consistency(self, validator):
        """Test that contradictory content has low consistency."""
        raw = create_raw_entry(
            content="Python uses braces for code blocks like C and Java."
        )
        knowledge = create_knowledge_entry(
            content="Python uses indentation instead of braces for code blocks."
        )

        score = validator._compute_content_similarity(
            raw.content, knowledge.content
        )

        # Should be relatively low due to contradiction
        assert score < 0.7

    def test_empty_content_zero_consistency(self, validator):
        """Test that empty content results in zero consistency."""
        raw = create_raw_entry(content="")
        knowledge = create_knowledge_entry(content="Some content here.")

        score = validator._compute_content_similarity(
            raw.content, knowledge.content
        )

        assert score == 0.0


# ============================================================
# EMBEDDING SIMILARITY TESTS
# ============================================================

class TestEmbeddingSimilarity:
    """Tests for embedding-based similarity."""

    @pytest.fixture
    def validator(self):
        from src.intelligence.cross_validator import CrossValidator
        return CrossValidator()

    def test_identical_embeddings_high_similarity(self, validator):
        """Test that identical embeddings have similarity 1.0."""
        embedding = [0.5] * 1536

        similarity = validator._compute_embedding_similarity(
            embedding, embedding
        )

        assert similarity >= 0.99

    def test_orthogonal_embeddings_low_similarity(self, validator):
        """Test that orthogonal embeddings have low similarity."""
        import numpy as np

        # Create orthogonal vectors
        emb1 = [1.0] + [0.0] * 1535
        emb2 = [0.0] + [1.0] + [0.0] * 1534

        similarity = validator._compute_embedding_similarity(emb1, emb2)

        assert similarity < 0.1  # Nearly orthogonal

    def test_empty_embeddings_zero_similarity(self, validator):
        """Test that empty embeddings return zero."""
        similarity = validator._compute_embedding_similarity([], [0.5] * 1536)

        assert similarity == 0.0


# ============================================================
# VALIDATION RESULT TESTS
# ============================================================

class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_validation_result_creation(self):
        """Test creating a validation result."""
        from src.intelligence.cross_validator import ValidationResult

        result = ValidationResult(
            raw_id="raw-1",
            knowledge_id="knowledge-1",
            consistency_score=0.85,
            content_similarity=0.80,
            embedding_similarity=0.90,
            is_consistent=True,
            resolution_hint=None,
        )

        assert result.consistency_score == 0.85
        assert result.is_consistent is True

    def test_validation_result_to_dict(self):
        """Test serialization of validation result."""
        from src.intelligence.cross_validator import ValidationResult

        result = ValidationResult(
            raw_id="raw-1",
            knowledge_id="knowledge-1",
            consistency_score=0.60,
            content_similarity=0.55,
            embedding_similarity=0.65,
            is_consistent=False,
            resolution_hint="prefer_newer",
        )

        d = result.to_dict()

        assert d["raw_id"] == "raw-1"
        assert d["is_consistent"] is False
        assert d["resolution_hint"] == "prefer_newer"


# ============================================================
# CROSS VALIDATION TESTS
# ============================================================

class TestCrossValidation:
    """Tests for cross-validation between Raw and Knowledge entries."""

    @pytest.fixture
    def validator(self):
        from src.intelligence.cross_validator import CrossValidator
        return CrossValidator()

    @pytest.mark.asyncio
    async def test_validate_consistent_entries(self, validator):
        """Test validation of consistent entries."""
        raw = create_raw_entry(content="Python uses indentation for blocks.")
        knowledge = create_knowledge_entry(
            content="Python uses indentation for blocks.",
            source_ids=["raw-1"],
        )

        result = await validator.validate(raw, knowledge)

        assert result.is_consistent is True
        assert result.consistency_score >= 0.7

    @pytest.mark.asyncio
    async def test_validate_inconsistent_entries(self, validator):
        """Test validation of inconsistent entries."""
        raw = create_raw_entry(
            content="Docker containers share the host kernel."
        )
        knowledge = create_knowledge_entry(
            content="Virtual machines have their own kernel."
        )

        result = await validator.validate(raw, knowledge)

        assert result.is_consistent is False
        assert result.consistency_score < 0.7

    @pytest.mark.asyncio
    async def test_validate_with_embeddings(self, validator):
        """Test that embeddings are considered in validation."""
        raw = create_raw_entry(content="Machine learning is a subset of AI.")
        raw.embedding = [0.9, 0.1, 0.0] * 512

        knowledge = create_knowledge_entry(
            content="Machine learning is a subset of artificial intelligence."
        )
        knowledge.embedding = [0.85, 0.15, 0.0] * 512

        result = await validator.validate(raw, knowledge)

        # Embeddings should contribute to consistency
        assert result.embedding_similarity > 0.9


# ============================================================
# RESOLUTION HINT TESTS
# ============================================================

class TestResolutionHints:
    """Tests for resolution hint suggestions."""

    @pytest.fixture
    def validator(self):
        from src.intelligence.cross_validator import CrossValidator
        return CrossValidator()

    @pytest.mark.asyncio
    async def test_prefer_newer_hint(self, validator):
        """Test that newer entries are preferred in hints."""
        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        new_date = datetime.now(timezone.utc)

        raw = create_raw_entry(
            content="Old information",
            created_at=old_date,
        )
        knowledge = create_knowledge_entry(
            content="New information",
            created_at=new_date,
        )

        result = await validator.validate(raw, knowledge)

        if not result.is_consistent:
            assert "newer" in result.resolution_hint.lower()

    @pytest.mark.asyncio
    async def test_prefer_verified_hint(self, validator):
        """Test that verified knowledge is preferred."""
        raw = create_raw_entry(content="User claim without verification.")
        knowledge = create_knowledge_entry(
            content="Verified factual information.",
        )
        knowledge.confidence = 0.95

        result = await validator.validate(raw, knowledge)

        # High confidence knowledge should be preferred
        if not result.is_consistent and knowledge.confidence > 0.9:
            assert "verified" in result.resolution_hint.lower() or \
                   "confidence" in result.resolution_hint.lower()


# ============================================================
# BATCH VALIDATION TESTS
# ============================================================

class TestBatchValidation:
    """Tests for batch validation of entries."""

    @pytest.fixture
    def validator(self):
        from src.intelligence.cross_validator import CrossValidator
        return CrossValidator()

    @pytest.mark.asyncio
    async def test_batch_validate(self, validator):
        """Test batch validation of multiple entry pairs."""
        pairs = [
            (
                create_raw_entry(id="raw-1", content="Python is interpreted."),
                create_knowledge_entry(id="k-1", content="Python is interpreted."),
            ),
            (
                create_raw_entry(id="raw-2", content="Java is compiled."),
                create_knowledge_entry(id="k-2", content="Java runs on JVM."),
            ),
        ]

        results = await validator.batch_validate(pairs)

        assert len(results) == 2
        assert results[0].is_consistent is True
        # Second pair has different info - may or may not be consistent

    @pytest.mark.asyncio
    async def test_batch_validate_empty_list(self, validator):
        """Test batch validation with empty list."""
        results = await validator.batch_validate([])

        assert len(results) == 0


# ============================================================
# INCONSISTENCY FLAGGING TESTS
# ============================================================

class TestInconsistencyFlagging:
    """Tests for flagging inconsistencies."""

    @pytest.fixture
    def validator(self):
        from src.intelligence.cross_validator import CrossValidator
        return CrossValidator()

    @pytest.mark.asyncio
    async def test_flag_inconsistency(self, validator):
        """Test that inconsistencies are flagged."""
        raw = create_raw_entry(content="Kubernetes uses Docker by default.")
        knowledge = create_knowledge_entry(
            content="Kubernetes supports multiple container runtimes."
        )

        result = await validator.validate(raw, knowledge)

        if not result.is_consistent:
            # Should create a flag for review
            with patch.object(validator, '_flag_for_review', new_callable=AsyncMock) as mock_flag:
                await validator.flag_if_inconsistent(result)
                mock_flag.assert_called_once()


# ============================================================
# COGNITIVE PRINCIPLE TESTS
# ============================================================

class TestCognitivePrinciples:
    """Tests that verify cognitive science principles."""

    @pytest.fixture
    def validator(self):
        from src.intelligence.cross_validator import CrossValidator
        return CrossValidator()

    @pytest.mark.asyncio
    async def test_error_correcting_codes_principle(self, validator):
        """
        Cognitive Principle: Error-Correcting Codes

        The brain maintains consistency across memory stores.
        When hippocampus (Raw) and neocortex (Knowledge) conflict,
        the system should flag the inconsistency for resolution.
        """
        # Simulate hippocampus (Raw) vs neocortex (Knowledge) conflict
        raw = create_raw_entry(
            content="The meeting is on Tuesday at 3pm."
        )
        # Use different embedding to reflect semantic difference
        raw.embedding = [0.9, 0.1, 0.0] * 512

        knowledge = create_knowledge_entry(
            content="The meeting is on Wednesday at 2pm."
        )
        # Different embedding to reflect the conflicting information
        knowledge.embedding = [0.1, 0.9, 0.0] * 512

        result = await validator.validate(raw, knowledge)

        # Should detect the inconsistency
        assert result.is_consistent is False
        assert result.resolution_hint is not None

    @pytest.mark.asyncio
    async def test_memory_reconsolidation_principle(self, validator):
        """
        Cognitive Principle: Memory Reconsolidation

        When memories are retrieved, they become labile and can be updated.
        Newer information may override older, less reliable memories.
        """
        old = datetime.now(timezone.utc) - timedelta(days=60)
        new = datetime.now(timezone.utc) - timedelta(days=1)

        raw = create_raw_entry(
            content="API endpoint is /v1/users",
            created_at=old,
        )
        knowledge = create_knowledge_entry(
            content="API endpoint is /v2/users",
            created_at=new,
        )

        result = await validator.validate(raw, knowledge)

        # Newer knowledge should be preferred
        if not result.is_consistent:
            assert "newer" in result.resolution_hint.lower()


# ============================================================
# STATISTICS TESTS
# ============================================================

class TestCrossValidatorStats:
    """Tests for statistics and monitoring."""

    @pytest.fixture
    def validator(self):
        from src.intelligence.cross_validator import CrossValidator
        return CrossValidator()

    @pytest.mark.asyncio
    async def test_get_stats(self, validator):
        """Test statistics retrieval."""
        # Validate some entries
        raw = create_raw_entry()
        knowledge = create_knowledge_entry()

        await validator.validate(raw, knowledge)

        stats = validator.get_stats()

        assert "total_validated" in stats
        assert "consistent_count" in stats
        assert "inconsistent_count" in stats
        assert "consistency_threshold" in stats


# ============================================================
# EDGE CASES TESTS
# ============================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def validator(self):
        from src.intelligence.cross_validator import CrossValidator
        return CrossValidator()

    @pytest.mark.asyncio
    async def test_validate_with_missing_embeddings(self, validator):
        """Test validation when embeddings are missing."""
        raw = create_raw_entry()
        raw.embedding = None

        knowledge = create_knowledge_entry()
        knowledge.embedding = None

        result = await validator.validate(raw, knowledge)

        # Should still work with content-only comparison
        assert result is not None
        assert result.embedding_similarity == 0.0

    @pytest.mark.asyncio
    async def test_validate_with_very_long_content(self, validator):
        """Test validation with very long content."""
        raw = create_raw_entry(content="Python " * 10000)
        knowledge = create_knowledge_entry(content="Python " * 10000)

        result = await validator.validate(raw, knowledge)

        assert result is not None
        assert result.is_consistent is True

    @pytest.mark.asyncio
    async def test_validate_with_unicode_content(self, validator):
        """Test validation with unicode content."""
        raw = create_raw_entry(content="Python 是一种编程语言 🐍")
        knowledge = create_knowledge_entry(content="Python 是一种编程语言 🐍")

        result = await validator.validate(raw, knowledge)

        assert result.is_consistent is True
