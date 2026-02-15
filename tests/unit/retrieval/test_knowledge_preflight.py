"""Unit tests for KnowledgePreflight.

Tests the cognitive science-inspired preflight check that determines
whether relevant knowledge likely exists before performing full retrieval.

Cognitive Principle: Feeling of Knowing (FOK)
The brain quickly estimates whether it knows something before engaging
in full memory search. This saves cognitive resources.

Run with: PYTHONPATH=. pytest tests/unit/retrieval/test_knowledge_preflight.py -v
"""

import pytest
import numpy as np
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from src.retrieval.knowledge_preflight import (
    KnowledgePreflight,
    KnowledgeSignal,
    PreflightResult,
    PreflightConfig,
)


# ============================================================
# KNOWLEDGE SIGNAL ENUM TESTS
# ============================================================

class TestKnowledgeSignal:
    """Tests for KnowledgeSignal enum."""

    def test_enum_values(self):
        """Verify enum has correct values."""
        assert KnowledgeSignal.LIKELY.value == "likely"
        assert KnowledgeSignal.UNLIKELY.value == "unlikely"
        assert KnowledgeSignal.UNCERTAIN.value == "uncertain"

    def test_enum_members_count(self):
        """Verify enum has exactly 3 members."""
        assert len(KnowledgeSignal) == 3


# ============================================================
# PREFLIGHT CONFIG TESTS
# ============================================================

class TestPreflightConfig:
    """Tests for PreflightConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PreflightConfig()

        # Bloom filter defaults
        assert config.bloom_capacity > 0
        assert 0 < config.bloom_error_rate < 1

        # Centroid defaults
        assert config.centroid_threshold > 0
        assert config.centroid_threshold < 1

        # Confidence thresholds
        assert config.likely_threshold > config.unlikely_threshold

    def test_custom_config(self):
        """Test custom configuration."""
        config = PreflightConfig(
            bloom_capacity=50000,
            bloom_error_rate=0.05,
            centroid_threshold=0.6,
            likely_threshold=0.8,
            unlikely_threshold=0.3,
        )

        assert config.bloom_capacity == 50000
        assert config.bloom_error_rate == 0.05
        assert config.centroid_threshold == 0.6


# ============================================================
# PREFLIGHT RESULT TESTS
# ============================================================

class TestPreflightResult:
    """Tests for PreflightResult dataclass."""

    def test_likely_result(self):
        """Test creating a LIKELY result."""
        result = PreflightResult(
            signal=KnowledgeSignal.LIKELY,
            confidence=0.85,
            bloom_match=True,
            centroid_similarity=0.78,
            matched_entities=["kubernetes", "docker"],
            closest_cluster="devops",
        )

        assert result.signal == KnowledgeSignal.LIKELY
        assert result.confidence == 0.85
        assert result.bloom_match is True
        assert len(result.matched_entities) == 2

    def test_unlikely_result(self):
        """Test creating an UNLIKELY result."""
        result = PreflightResult(
            signal=KnowledgeSignal.UNLIKELY,
            confidence=0.15,
            bloom_match=False,
            centroid_similarity=0.25,
            matched_entities=[],
            closest_cluster=None,
        )

        assert result.signal == KnowledgeSignal.UNLIKELY
        assert result.bloom_match is False
        assert result.matched_entities == []

    def test_to_dict(self):
        """Test result serialization."""
        result = PreflightResult(
            signal=KnowledgeSignal.UNCERTAIN,
            confidence=0.55,
            bloom_match=True,
            centroid_similarity=0.45,
            matched_entities=["python"],
            closest_cluster="programming",
        )

        d = result.to_dict()
        assert d["signal"] == "uncertain"
        assert d["confidence"] == 0.55
        assert d["bloom_match"] is True


# ============================================================
# HELPER TO CREATE INITIALIZED PREFLIGHT
# ============================================================

def create_preflight(
    entities: set = None,
    centroids: dict = None,
    initialized: bool = True
) -> KnowledgePreflight:
    """Create a KnowledgePreflight with mocked state for testing."""
    pf = KnowledgePreflight.__new__(KnowledgePreflight)
    pf.config = PreflightConfig()
    pf._weaviate = None
    pf._entities = entities or set()
    pf._cluster_centroids = centroids or {}
    pf._initialized = initialized
    return pf


# ============================================================
# KNOWLEDGE PREFLIGHT CLASS TESTS
# ============================================================

class TestKnowledgePreflight:
    """Tests for KnowledgePreflight class."""

    def test_initialization_state(self):
        """Test preflight starts uninitialized."""
        pf = create_preflight(initialized=False)
        assert pf._initialized is False

    @pytest.mark.asyncio
    async def test_check_requires_initialization(self):
        """Test that check raises error if not initialized."""
        pf = create_preflight(initialized=False)
        with pytest.raises(RuntimeError, match="not initialized"):
            await pf.check("test query", [0.1] * 1536)

    @pytest.mark.asyncio
    async def test_check_with_matching_entity(self):
        """Test preflight check when query contains known entity."""
        pf = create_preflight(
            entities={"kubernetes", "docker", "python"},
            centroids={"devops": np.array([0.5] * 1536)},
        )

        query = "How do I deploy a kubernetes cluster?"
        embedding = [0.5] * 1536

        result = await pf.check(query, embedding)

        assert result.signal in [KnowledgeSignal.LIKELY, KnowledgeSignal.UNCERTAIN]
        assert "kubernetes" in result.matched_entities

    @pytest.mark.asyncio
    async def test_check_with_no_matching_entity(self):
        """Test preflight check when query has no known entities."""
        pf = create_preflight(
            entities={"kubernetes", "docker"},
            centroids={"devops": np.array([0.1] * 1536)},
        )

        query = "What is the meaning of life?"
        embedding = [0.9] * 1536  # Different from centroids

        result = await pf.check(query, embedding)

        assert result.matched_entities == []

    @pytest.mark.asyncio
    async def test_check_with_multiple_entities(self):
        """Test preflight with multiple matching entities."""
        pf = create_preflight(
            entities={"python", "postgresql", "docker", "kubernetes"},
        )

        query = "How do I connect Python to PostgreSQL and Docker?"
        embedding = [0.5] * 1536

        result = await pf.check(query, embedding)

        # Should match multiple entities
        matched = set(result.matched_entities)
        assert "python" in matched
        assert "postgresql" in matched
        assert "docker" in matched


# ============================================================
# ENTITY EXTRACTION TESTS
# ============================================================

class TestEntityExtraction:
    """Tests for entity extraction from queries."""

    def test_extract_entities_from_query(self):
        """Test extracting known entities from query."""
        pf = create_preflight(entities={"python", "docker", "kubernetes", "react"})

        query = "How do I containerize my Python app with Docker?"
        entities = pf._extract_entities(query)

        assert "python" in entities
        assert "docker" in entities
        assert "kubernetes" not in entities

    def test_extract_entities_case_insensitive(self):
        """Test entity extraction is case insensitive."""
        pf = create_preflight(entities={"python", "docker", "kubernetes"})

        query = "PYTHON and Docker are great tools"
        entities = pf._extract_entities(query)

        assert "python" in entities
        assert "docker" in entities

    def test_extract_entities_empty_query(self):
        """Test entity extraction with empty query."""
        pf = create_preflight(entities={"python", "docker"})

        entities = pf._extract_entities("")
        assert entities == []

    def test_extract_entities_no_matches(self):
        """Test entity extraction with no matches."""
        pf = create_preflight(entities={"python", "docker"})

        query = "What is the weather today?"
        entities = pf._extract_entities(query)

        assert entities == []


# ============================================================
# CENTROID MATCHING TESTS
# ============================================================

class TestCentroidMatching:
    """Tests for cluster centroid matching."""

    def test_find_closest_cluster(self):
        """Test finding closest cluster centroid."""
        pf = create_preflight(centroids={
            "python": np.array([1.0, 0.0, 0.0, 0.0] * 384),
            "docker": np.array([0.0, 1.0, 0.0, 0.0] * 384),
            "general": np.array([0.5, 0.5, 0.5, 0.5] * 384),
        })

        # Embedding close to "python" centroid
        embedding = [0.9, 0.1, 0.1, 0.1] * 384

        cluster, similarity = pf._find_closest_cluster(embedding)

        assert cluster == "python"
        assert similarity > 0.5

    def test_find_closest_cluster_with_different_embedding(self):
        """Test closest cluster with docker-like embedding."""
        pf = create_preflight(centroids={
            "python": np.array([1.0, 0.0, 0.0, 0.0] * 384),
            "docker": np.array([0.0, 1.0, 0.0, 0.0] * 384),
        })

        # Embedding close to "docker" centroid
        embedding = [0.1, 0.9, 0.1, 0.1] * 384

        cluster, similarity = pf._find_closest_cluster(embedding)

        assert cluster == "docker"
        assert similarity > 0.5

    def test_find_closest_cluster_no_centroids(self):
        """Test closest cluster with empty centroids."""
        pf = create_preflight(centroids={})

        embedding = [0.5] * 1536
        cluster, similarity = pf._find_closest_cluster(embedding)

        assert cluster is None
        assert similarity == 0.0


# ============================================================
# SIGNAL DETERMINATION TESTS
# ============================================================

class TestSignalDetermination:
    """Tests for final signal determination logic."""

    def test_determine_signal_likely_high_confidence(self):
        """Test LIKELY signal with high confidence."""
        pf = create_preflight()
        pf.config = PreflightConfig(
            likely_threshold=0.7,
            unlikely_threshold=0.3,
            centroid_threshold=0.5,
        )

        signal, confidence = pf._determine_signal(
            bloom_match=True,
            centroid_similarity=0.85,
            entity_count=3,
        )

        assert signal == KnowledgeSignal.LIKELY
        assert confidence >= 0.7

    def test_determine_signal_unlikely_no_match(self):
        """Test UNLIKELY signal with no matches."""
        pf = create_preflight()
        pf.config = PreflightConfig(
            likely_threshold=0.7,
            unlikely_threshold=0.3,
            centroid_threshold=0.5,
        )

        signal, confidence = pf._determine_signal(
            bloom_match=False,
            centroid_similarity=0.2,
            entity_count=0,
        )

        assert signal == KnowledgeSignal.UNLIKELY
        assert confidence <= 0.3

    def test_determine_signal_uncertain_mixed(self):
        """Test UNCERTAIN signal with mixed signals."""
        pf = create_preflight()
        pf.config = PreflightConfig(
            likely_threshold=0.7,
            unlikely_threshold=0.3,
            centroid_threshold=0.5,
        )

        # With bloom_match=True and entity_count=4, we get 0.4 confidence (max from entities)
        # Centroid below threshold adds 0, so total = 0.4 which is in UNCERTAIN range
        signal, confidence = pf._determine_signal(
            bloom_match=True,
            centroid_similarity=0.45,  # Below centroid threshold
            entity_count=4,  # 4 entities = 0.4 confidence
        )

        assert signal == KnowledgeSignal.UNCERTAIN
        assert 0.3 < confidence < 0.7

    def test_determine_signal_likely_many_entities(self):
        """Test LIKELY signal when many entities match."""
        pf = create_preflight()
        pf.config = PreflightConfig(
            likely_threshold=0.7,
            unlikely_threshold=0.3,
            centroid_threshold=0.5,
        )

        signal, confidence = pf._determine_signal(
            bloom_match=True,
            centroid_similarity=0.6,
            entity_count=5,  # Many entities
        )

        assert signal == KnowledgeSignal.LIKELY
        assert confidence >= 0.7


# ============================================================
# BLOOM FILTER SIMULATION TESTS
# ============================================================

class TestBloomFilterSimulation:
    """Tests for bloom filter-like entity checking."""

    def test_bloom_check_positive(self):
        """Test bloom filter returns True for known entities."""
        pf = create_preflight(entities={
            "python", "javascript", "typescript", "rust", "go",
            "docker", "kubernetes", "terraform", "ansible",
            "postgresql", "mongodb", "redis", "elasticsearch",
        })

        assert pf._bloom_check("python") is True
        assert pf._bloom_check("kubernetes") is True
        assert pf._bloom_check("redis") is True

    def test_bloom_check_negative(self):
        """Test bloom filter returns False for unknown entities."""
        pf = create_preflight(entities={"python", "docker", "kubernetes"})

        assert pf._bloom_check("cobol") is False
        assert pf._bloom_check("fortran") is False
        assert pf._bloom_check("weather") is False

    def test_bloom_check_case_insensitive(self):
        """Test bloom filter is case insensitive."""
        pf = create_preflight(entities={"python", "docker", "postgresql"})

        assert pf._bloom_check("Python") is True
        assert pf._bloom_check("DOCKER") is True
        assert pf._bloom_check("PostgreSQL") is True


# ============================================================
# PERFORMANCE TESTS
# ============================================================

class TestPreflightPerformance:
    """Tests for preflight performance characteristics."""

    @pytest.mark.asyncio
    async def test_check_is_fast(self):
        """Test that preflight check is fast even with large data."""
        import time

        # Large entity set (10K entities)
        entities = {f"entity_{i}" for i in range(10000)}

        # Many cluster centroids
        centroids = {
            f"cluster_{i}": np.random.rand(1536)
            for i in range(100)
        }

        pf = create_preflight(entities=entities, centroids=centroids)

        query = "How do I use entity_500 with entity_1000?"
        embedding = np.random.rand(1536).tolist()

        start = time.time()
        result = await pf.check(query, embedding)
        elapsed = time.time() - start

        # Preflight should be fast (< 100ms)
        assert elapsed < 0.1, f"Preflight took {elapsed:.3f}s, should be < 0.1s"
        assert result is not None

    def test_entity_lookup_is_constant_time(self):
        """Test that entity lookup is O(1) using set."""
        import time

        pf = create_preflight(entities={f"entity_{i}" for i in range(10000)})

        # Lookup at start
        start = time.time()
        for i in range(100):
            pf._bloom_check("entity_1")
        early_time = time.time() - start

        # Lookup at end
        start = time.time()
        for i in range(100):
            pf._bloom_check("entity_9999")
        late_time = time.time() - start

        # Times should be similar (constant time)
        ratio = max(early_time, late_time) / (min(early_time, late_time) + 0.0001)
        assert ratio < 5.0, f"Lookup times differ too much: {early_time:.6f} vs {late_time:.6f}"


# ============================================================
# EDGE CASE TESTS
# ============================================================

class TestPreflightEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_check_with_empty_query(self):
        """Test check with empty query string."""
        # Use no centroids to avoid high similarity score
        pf = create_preflight(
            entities={"python", "docker"},
            centroids={},  # No centroids = 0 centroid similarity
        )

        result = await pf.check("", [0.5] * 1536)

        # Empty query with no centroids = UNLIKELY
        assert result.signal == KnowledgeSignal.UNLIKELY
        assert result.matched_entities == []

    @pytest.mark.asyncio
    async def test_check_with_unicode(self):
        """Test check with unicode characters."""
        pf = create_preflight(
            entities={"python", "docker"},
            centroids={"default": np.array([0.5] * 1536)},
        )

        query = "Python \u4e2d\u6587 \u65e5\u672c\u8a9e"
        result = await pf.check(query, [0.5] * 1536)

        assert result is not None
        assert "python" in result.matched_entities

    @pytest.mark.asyncio
    async def test_check_with_special_characters(self):
        """Test check with special characters."""
        pf = create_preflight(
            entities={"python", "docker"},
            centroids={"default": np.array([0.5] * 1536)},
        )

        query = "How do I use python3.11 with @decorator?"
        result = await pf.check(query, [0.5] * 1536)

        assert result is not None

    @pytest.mark.asyncio
    async def test_check_with_very_long_query(self):
        """Test check with very long query."""
        pf = create_preflight(
            entities={"python", "docker"},
            centroids={"default": np.array([0.5] * 1536)},
        )

        query = "python " * 10000
        result = await pf.check(query, [0.5] * 1536)

        assert result is not None
        assert "python" in result.matched_entities

    @pytest.mark.asyncio
    async def test_check_with_wrong_embedding_dimension(self):
        """Test check with wrong embedding dimension."""
        pf = create_preflight(entities={"python"})

        with pytest.raises(ValueError, match="dimension"):
            await pf.check("test", [0.1] * 100)  # Wrong dimension


# ============================================================
# COGNITIVE PRINCIPLE TESTS
# ============================================================

class TestCognitivePrinciples:
    """Tests that verify cognitive science principles are implemented."""

    @pytest.mark.asyncio
    async def test_feeling_of_knowing_likely(self):
        """
        Cognitive Principle: Feeling of Knowing (FOK)

        When the brain quickly estimates high likelihood of relevant knowledge,
        it should return LIKELY signal to trigger full retrieval.
        """
        pf = create_preflight(
            # Include entities that will match the query words
            entities={"train", "neural", "network", "tensorflow", "machine-learning"},
            centroids={"ml": np.array([0.8, 0.1, 0.1] * 512)},
        )

        query = "How do I train a neural network with TensorFlow?"
        # Embedding similar to ML cluster
        embedding = [0.7, 0.2, 0.1] * 512

        result = await pf.check(query, embedding)

        # Should feel confident about knowing this
        # With 4+ entity matches + high centroid similarity + synergy → LIKELY
        assert result.signal == KnowledgeSignal.LIKELY
        assert result.confidence >= 0.7

    @pytest.mark.asyncio
    async def test_feeling_of_knowing_unlikely(self):
        """
        Cognitive Principle: FOK for unknown topics

        When there's no indication of relevant knowledge,
        should return UNLIKELY to skip expensive retrieval.
        """
        pf = create_preflight(
            entities={"python", "docker"},
            centroids={"programming": np.array([0.1, 0.9, 0.1] * 512)},
        )

        query = "What is the weather in Paris?"
        # Random embedding not matching any cluster
        embedding = [0.3, 0.3, 0.3] * 512

        result = await pf.check(query, embedding)

        # Should not feel confident about this
        assert result.signal in [KnowledgeSignal.UNLIKELY, KnowledgeSignal.UNCERTAIN]
        assert result.confidence < 0.7
