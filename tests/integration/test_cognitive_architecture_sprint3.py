"""Integration tests for Cognitive Architecture Sprint 3.

Sprint 3 Focus: Hebbian Learning & Cross-Validation
- 2.3 Co-Retrieval Graph (Hebbian Learning)
- 2.4 Cross-Validation (Error-Correcting Codes)

Cognitive Principles Tested:
1. Hebbian Learning: "Neurons that fire together, wire together"
   - Items retrieved together form associations
   - Associations strengthen with repeated co-retrieval
   - Associations decay without reinforcement

2. Error-Correcting Codes: Memory consistency maintenance
   - Cross-validation between Raw and Knowledge entries
   - Detection of inconsistencies
   - Flagging for human review

Run with: PYTHONPATH=. pytest tests/integration/test_cognitive_architecture_sprint3.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


# ============================================================
# TEST FIXTURES
# ============================================================

@dataclass
class MockRetrievalSource:
    """Mock retrieval source for testing."""
    id: str
    content: str
    similarity: float
    source_type: Any
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MockRawEntry:
    """Mock Raw entry for testing."""
    id: str
    content: str
    user_id: str
    created_at: datetime
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
    confidence: float = 0.9
    embedding: Optional[List[float]] = None

    def __post_init__(self):
        if self.embedding is None:
            self.embedding = [0.5] * 1536


@pytest.fixture
def coretrieval_tracker():
    """Create a fresh CoRetrievalTracker for each test."""
    from src.retrieval.coretrieval_graph import CoRetrievalTracker
    tracker = CoRetrievalTracker()
    return tracker


@pytest.fixture
def cross_validator():
    """Create a fresh CrossValidator for each test."""
    from src.intelligence.cross_validator import CrossValidator
    validator = CrossValidator()
    return validator


@pytest.fixture
def retrieval_engine(coretrieval_tracker):
    """Create a RetrievalEngine with co-retrieval tracking."""
    from src.retrieval.engine import RetrievalEngine, SourceType

    # Create engine with tracker
    engine = RetrievalEngine(
        dual_memory=None,
        memory_crud=None,
        web_search=None,
        coretrieval_tracker=coretrieval_tracker,
        enable_coretrieval_tracking=True,
        enable_web_search=False,
        enable_legacy_memory=False
    )

    return engine


# ============================================================
# HEBBIAN LEARNING INTEGRATION TESTS
# ============================================================

class TestHebbianLearningIntegration:
    """Integration tests for Hebbian learning in retrieval pipeline."""

    @pytest.mark.asyncio
    async def test_retrieval_records_co_retrieval(self, coretrieval_tracker):
        """Test that retrieval operations record co-retrieval events."""
        # Simulate retrieval of items together
        session_id = "session-1"
        retrieved_ids = ["item-1", "item-2", "item-3"]
        topic = "kubernetes"

        # Record co-retrieval
        edges_created = await coretrieval_tracker.record_co_retrieval(
            session_id=session_id,
            retrieved_ids=retrieved_ids,
            topic=topic
        )

        # Should create edges for all pairs: (1,2), (1,3), (2,3)
        assert edges_created == 3

        # Verify associations exist
        associations = await coretrieval_tracker.get_associated_items("item-1")
        assert len(associations) == 2  # item-2 and item-3

    @pytest.mark.asyncio
    async def test_associations_strengthen_with_repetition(self, coretrieval_tracker):
        """Test that repeated co-retrieval strengthens associations."""
        session_id = "session-1"
        items = ["item-a", "item-b"]
        topic = "python"

        # Record co-retrieval multiple times
        for _ in range(5):
            await coretrieval_tracker.record_co_retrieval(
                session_id=session_id,
                retrieved_ids=items,
                topic=topic
            )

        # Get association strength
        associations = await coretrieval_tracker.get_associated_items("item-a")
        assert len(associations) == 1

        item_id, strength = associations[0]
        assert item_id == "item-b"

        # Strength should be higher after 5 retrievals
        # log(5+1) * exp(-0) ≈ 1.79
        assert strength > 1.5

    @pytest.mark.asyncio
    async def test_engine_tracks_co_retrieval_in_stats(self, retrieval_engine, coretrieval_tracker):
        """Test that engine includes co-retrieval tracking in stats."""
        stats = retrieval_engine.get_search_stats()

        assert stats["coretrieval_tracking_enabled"] is True
        assert stats["coretrieval_tracker_available"] is True
        assert "coretrieval_stats" in stats

    @pytest.mark.asyncio
    async def test_spreading_activation_pattern(self, coretrieval_tracker):
        """Test spreading activation: when A activates, B also gets preloaded.

        Cognitive basis: Activating one concept spreads activation to
        associated concepts, enabling faster retrieval.
        """
        # Build a network: A <-> B <-> C
        await coretrieval_tracker.record_co_retrieval(
            session_id="s1",
            retrieved_ids=["concept-A", "concept-B"],
            topic="network"
        )
        await coretrieval_tracker.record_co_retrieval(
            session_id="s2",
            retrieved_ids=["concept-B", "concept-C"],
            topic="network"
        )

        # Activating A should preload B (direct association)
        a_associations = await coretrieval_tracker.get_associated_items("concept-A")
        assert len(a_associations) == 1
        assert a_associations[0][0] == "concept-B"

        # Activating B should preload both A and C
        b_associations = await coretrieval_tracker.get_associated_items("concept-B")
        assert len(b_associations) == 2
        associated_ids = {a[0] for a in b_associations}
        assert "concept-A" in associated_ids
        assert "concept-C" in associated_ids

    @pytest.mark.asyncio
    async def test_topic_context_preserved(self, coretrieval_tracker):
        """Test that topic context is preserved in co-retrieval edges."""
        items = ["docker-1", "kubernetes-1"]

        # Record with different topics
        await coretrieval_tracker.record_co_retrieval(
            session_id="s1",
            retrieved_ids=items,
            topic="containers"
        )
        await coretrieval_tracker.record_co_retrieval(
            session_id="s2",
            retrieved_ids=items,
            topic="deployment"
        )

        # Check pending edges have topic context
        pending = coretrieval_tracker._get_pending_edges()
        assert len(pending) == 1

        edge = pending[0]
        assert "containers" in edge.context_topics
        assert "deployment" in edge.context_topics
        assert edge.context_topics["containers"] == 1
        assert edge.context_topics["deployment"] == 1


# ============================================================
# CROSS-VALIDATION INTEGRATION TESTS
# ============================================================

class TestCrossValidationIntegration:
    """Integration tests for cross-validation between Raw and Knowledge."""

    @pytest.mark.asyncio
    async def test_consistent_entries_validate(self, cross_validator):
        """Test that consistent entries pass validation."""
        raw = MockRawEntry(
            id="raw-1",
            content="Python uses indentation for code blocks.",
            user_id="user-1",
            created_at=datetime.now(timezone.utc)
        )
        knowledge = MockKnowledgeEntry(
            id="knowledge-1",
            content="Python uses indentation for code blocks.",
            user_id="user-1",
            created_at=datetime.now(timezone.utc)
        )

        result = await cross_validator.validate(raw, knowledge)

        assert result.is_consistent is True
        assert result.consistency_score >= 0.7

    @pytest.mark.asyncio
    async def test_inconsistent_entries_detected(self, cross_validator):
        """Test that inconsistent entries are detected."""
        raw = MockRawEntry(
            id="raw-1",
            content="Kubernetes uses Docker as its only runtime.",
            user_id="user-1",
            created_at=datetime.now(timezone.utc)
        )
        raw.embedding = [0.9, 0.1, 0.0] * 512  # Different embedding

        knowledge = MockKnowledgeEntry(
            id="knowledge-1",
            content="Kubernetes supports containerd, CRI-O, and other runtimes.",
            user_id="user-1",
            created_at=datetime.now(timezone.utc)
        )
        knowledge.embedding = [0.1, 0.9, 0.0] * 512  # Different embedding

        result = await cross_validator.validate(raw, knowledge)

        assert result.is_consistent is False
        assert result.consistency_score < 0.7
        assert result.resolution_hint is not None

    @pytest.mark.asyncio
    async def test_batch_validation(self, cross_validator):
        """Test batch validation of multiple entry pairs."""
        pairs = [
            (
                MockRawEntry(
                    id="raw-1",
                    content="Python is interpreted.",
                    user_id="user-1",
                    created_at=datetime.now(timezone.utc)
                ),
                MockKnowledgeEntry(
                    id="k-1",
                    content="Python is interpreted.",
                    user_id="user-1",
                    created_at=datetime.now(timezone.utc)
                )
            ),
            (
                MockRawEntry(
                    id="raw-2",
                    content="JavaScript runs only in browsers.",
                    user_id="user-1",
                    created_at=datetime.now(timezone.utc),
                    embedding=[0.8, 0.2, 0.0] * 512
                ),
                MockKnowledgeEntry(
                    id="k-2",
                    content="JavaScript runs in Node.js, browsers, and other environments.",
                    user_id="user-1",
                    created_at=datetime.now(timezone.utc),
                    embedding=[0.2, 0.8, 0.0] * 512
                )
            )
        ]

        results = await cross_validator.batch_validate(pairs)

        assert len(results) == 2
        assert results[0].is_consistent is True
        assert results[1].is_consistent is False  # Conflicting information

    @pytest.mark.asyncio
    async def test_resolution_hints_prefer_newer(self, cross_validator):
        """Test that resolution hints prefer newer information."""
        old_date = datetime.now(timezone.utc) - timedelta(days=60)
        new_date = datetime.now(timezone.utc) - timedelta(days=1)

        raw = MockRawEntry(
            id="raw-1",
            content="API uses v1 endpoints.",
            user_id="user-1",
            created_at=old_date,
            embedding=[0.9, 0.1, 0.0] * 512
        )
        knowledge = MockKnowledgeEntry(
            id="k-1",
            content="API uses v2 endpoints.",
            user_id="user-1",
            created_at=new_date,
            embedding=[0.1, 0.9, 0.0] * 512
        )

        result = await cross_validator.validate(raw, knowledge)

        if not result.is_consistent:
            assert "newer" in result.resolution_hint.lower()

    @pytest.mark.asyncio
    async def test_resolution_hints_prefer_verified(self, cross_validator):
        """Test that resolution hints prefer high-confidence knowledge."""
        raw = MockRawEntry(
            id="raw-1",
            content="Unverified claim about system.",
            user_id="user-1",
            created_at=datetime.now(timezone.utc),
            embedding=[0.9, 0.1, 0.0] * 512
        )
        knowledge = MockKnowledgeEntry(
            id="k-1",
            content="Verified documentation about system.",
            user_id="user-1",
            created_at=datetime.now(timezone.utc),
            confidence=0.95,
            embedding=[0.1, 0.9, 0.0] * 512
        )

        result = await cross_validator.validate(raw, knowledge)

        if not result.is_consistent:
            assert "verified" in result.resolution_hint.lower()


# ============================================================
# END-TO-END PIPELINE TESTS
# ============================================================

class TestCognitiveArchitecturePipelineS3:
    """End-to-end tests for Sprint 3 cognitive architecture."""

    @pytest.mark.asyncio
    async def test_full_hebbian_cycle(self, coretrieval_tracker):
        """Test full cycle: retrieval → recording → preloading."""
        # Simulate multiple query sessions
        sessions = [
            {"id": "s1", "items": ["docker", "kubernetes", "helm"], "topic": "devops"},
            {"id": "s2", "items": ["docker", "kubernetes"], "topic": "containers"},
            {"id": "s3", "items": ["kubernetes", "helm"], "topic": "deployment"},
        ]

        # Record co-retrievals from multiple sessions
        for session in sessions:
            await coretrieval_tracker.record_co_retrieval(
                session_id=session["id"],
                retrieved_ids=session["items"],
                topic=session["topic"]
            )

        # Kubernetes should have strong associations with docker and helm
        associations = await coretrieval_tracker.get_associated_items(
            "kubernetes",
            min_strength=0.0
        )

        assert len(associations) >= 2
        associated_ids = {a[0] for a in associations}
        assert "docker" in associated_ids
        assert "helm" in associated_ids

        # docker-kubernetes pair should be strongest (2 co-retrievals)
        docker_assoc = next((a for a in associations if a[0] == "docker"), None)
        helm_assoc = next((a for a in associations if a[0] == "helm"), None)

        assert docker_assoc is not None
        assert helm_assoc is not None
        # docker has 2 co-retrievals, helm has 2 co-retrievals
        # Both should have similar strength
        assert docker_assoc[1] > 0
        assert helm_assoc[1] > 0

    @pytest.mark.asyncio
    async def test_full_validation_cycle(self, cross_validator):
        """Test full cycle: create entries → validate → get stats."""
        # Create some entry pairs
        pairs = []
        for i in range(5):
            consistent = i < 3  # First 3 consistent, last 2 inconsistent

            raw = MockRawEntry(
                id=f"raw-{i}",
                content=f"Fact number {i}" if consistent else f"Outdated info {i}",
                user_id="user-1",
                created_at=datetime.now(timezone.utc)
            )

            knowledge = MockKnowledgeEntry(
                id=f"k-{i}",
                content=f"Fact number {i}" if consistent else f"Updated info {i}",
                user_id="user-1",
                created_at=datetime.now(timezone.utc)
            )

            # Set different embeddings for inconsistent pairs
            if not consistent:
                raw.embedding = [0.9, 0.1, 0.0] * 512
                knowledge.embedding = [0.1, 0.9, 0.0] * 512

            pairs.append((raw, knowledge))

        # Validate all pairs
        results = await cross_validator.batch_validate(pairs)

        # Get stats
        stats = cross_validator.get_stats()

        assert stats["total_validated"] == 5
        assert stats["consistent_count"] == 3
        assert stats["inconsistent_count"] == 2
        assert 0.5 < stats["consistency_rate"] < 0.7

    @pytest.mark.asyncio
    async def test_cognitive_principles_combined(self, coretrieval_tracker, cross_validator):
        """Test that Hebbian learning and error-correction work together.

        Scenario: Items retrieved together form associations, but some
        pairs may have inconsistent information that needs flagging.
        """
        # Create items that would be retrieved together
        items = ["api-docs", "api-examples", "api-changelog"]

        # Record co-retrieval
        await coretrieval_tracker.record_co_retrieval(
            session_id="s1",
            retrieved_ids=items,
            topic="api"
        )

        # Now validate consistency between api-docs and api-changelog
        # (docs might be outdated compared to changelog)
        old_date = datetime.now(timezone.utc) - timedelta(days=30)
        new_date = datetime.now(timezone.utc)

        docs = MockRawEntry(
            id="api-docs",
            content="API requires authentication header.",
            user_id="user-1",
            created_at=old_date,
            embedding=[0.9, 0.1, 0.0] * 512
        )

        changelog = MockKnowledgeEntry(
            id="api-changelog",
            content="API now uses OAuth2 instead of header auth.",
            user_id="user-1",
            created_at=new_date,
            confidence=0.95,
            embedding=[0.1, 0.9, 0.0] * 512
        )

        # Validate
        result = await cross_validator.validate(docs, changelog)

        # Should be inconsistent (different auth methods)
        assert result.is_consistent is False
        # Should suggest preferring the newer/verified version
        assert "newer" in result.resolution_hint.lower() or "verified" in result.resolution_hint.lower()

        # But they're still associated via Hebbian learning
        associations = await coretrieval_tracker.get_associated_items("api-docs")
        associated_ids = {a[0] for a in associations}
        assert "api-changelog" in associated_ids


# ============================================================
# STATS AND MONITORING TESTS
# ============================================================

class TestSprintThreeMonitoring:
    """Tests for Sprint 3 monitoring and observability."""

    @pytest.mark.asyncio
    async def test_coretrieval_stats_tracked(self, coretrieval_tracker):
        """Test that co-retrieval stats are properly tracked."""
        # Record some co-retrievals
        await coretrieval_tracker.record_co_retrieval(
            session_id="s1",
            retrieved_ids=["a", "b", "c"],
            topic="test"
        )

        stats = coretrieval_tracker.get_stats()

        assert stats["total_recorded"] == 1
        assert stats["pending_edges"] == 3  # (a,b), (a,c), (b,c)
        assert "config" in stats
        assert stats["config"]["decay_rate"] == 0.05

    @pytest.mark.asyncio
    async def test_crossvalidator_stats_tracked(self, cross_validator):
        """Test that cross-validator stats are properly tracked."""
        # Validate some entries
        for i in range(3):
            raw = MockRawEntry(
                id=f"raw-{i}",
                content=f"Content {i}",
                user_id="user-1",
                created_at=datetime.now(timezone.utc)
            )
            knowledge = MockKnowledgeEntry(
                id=f"k-{i}",
                content=f"Content {i}",
                user_id="user-1",
                created_at=datetime.now(timezone.utc)
            )
            await cross_validator.validate(raw, knowledge)

        stats = cross_validator.get_stats()

        assert stats["total_validated"] == 3
        assert stats["consistent_count"] == 3
        assert stats["inconsistent_count"] == 0
        assert stats["consistency_rate"] == 1.0

    @pytest.mark.asyncio
    async def test_retrieval_result_includes_hebbian_info(self, retrieval_engine):
        """Test that retrieval results include Hebbian tracking info."""
        from src.retrieval.engine import RetrievalResult

        # Create a mock result
        result = RetrievalResult(
            query="test query",
            context="test context",
            sanitized_context="test context",
            sources=[],
            associated_items_preloaded=3,
            co_retrieval_recorded=True
        )

        result_dict = result.to_dict()

        assert "associated_items_preloaded" in result_dict
        assert result_dict["associated_items_preloaded"] == 3
        assert "co_retrieval_recorded" in result_dict
        assert result_dict["co_retrieval_recorded"] is True
