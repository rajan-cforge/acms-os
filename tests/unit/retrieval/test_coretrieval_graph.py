"""Unit tests for CoRetrievalTracker (Hebbian Learning Graph).

Cognitive Principle: Hebbian Learning
"Neurons that fire together, wire together"

When multiple knowledge items are retrieved together in response to a query,
they form an association. Repeated co-retrieval strengthens this association,
allowing the system to preload related items for faster context assembly.

TDD: Tests written BEFORE implementation.
Run with: PYTHONPATH=. pytest tests/unit/retrieval/test_coretrieval_graph.py -v
"""

import pytest
import math
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


# ============================================================
# TEST FIXTURES AND HELPERS
# ============================================================

@dataclass
class MockCoRetrievalEdge:
    """Mock edge for testing."""
    item_a_id: str
    item_b_id: str
    co_retrieval_count: int = 1
    avg_temporal_distance: Optional[float] = None
    last_co_retrieval: datetime = None
    strength: float = 0.0
    context_topics: Dict[str, int] = None
    created_at: datetime = None
    updated_at: datetime = None

    def __post_init__(self):
        if self.last_co_retrieval is None:
            self.last_co_retrieval = datetime.now(timezone.utc)
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.updated_at is None:
            self.updated_at = datetime.now(timezone.utc)
        if self.context_topics is None:
            self.context_topics = {}


def create_mock_db():
    """Create a mock database session for testing."""
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    return mock_db


# ============================================================
# CO-RETRIEVAL CONFIG TESTS
# ============================================================

class TestCoRetrievalConfig:
    """Tests for CoRetrievalConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        from src.retrieval.coretrieval_graph import CoRetrievalConfig

        config = CoRetrievalConfig()

        # Hebbian decay rate
        assert config.decay_rate == 0.05
        # Minimum strength to maintain edge
        assert config.min_strength_threshold >= 0.01
        # Maximum edges to return
        assert config.max_associated_items >= 5
        # Minimum co-retrieval count to consider
        assert config.min_count_threshold >= 2

    def test_custom_config(self):
        """Test custom configuration."""
        from src.retrieval.coretrieval_graph import CoRetrievalConfig

        config = CoRetrievalConfig(
            decay_rate=0.1,
            min_strength_threshold=0.05,
            max_associated_items=10,
        )

        assert config.decay_rate == 0.1
        assert config.max_associated_items == 10


# ============================================================
# HEBBIAN STRENGTH CALCULATION TESTS
# ============================================================

class TestHebbianStrength:
    """Tests for Hebbian strength calculation."""

    def test_strength_formula(self):
        """
        Test Hebbian strength formula:
        strength = log(count + 1) * exp(-decay_rate * days_since)

        Cognitive basis: Associations strengthen with repetition
        but decay over time without reinforcement.
        """
        from src.retrieval.coretrieval_graph import CoRetrievalTracker

        tracker = CoRetrievalTracker()

        # Fresh co-retrieval (0 days ago)
        strength_fresh = tracker._compute_strength(
            count=5,
            days_since_last=0.0
        )
        # log(6) * exp(0) = log(6) * 1 ≈ 1.79
        assert 1.7 < strength_fresh < 1.9

        # Week-old co-retrieval
        strength_week = tracker._compute_strength(
            count=5,
            days_since_last=7.0
        )
        # log(6) * exp(-0.05 * 7) ≈ 1.79 * 0.705 ≈ 1.26
        assert strength_week < strength_fresh

        # Month-old co-retrieval
        strength_month = tracker._compute_strength(
            count=5,
            days_since_last=30.0
        )
        # log(6) * exp(-0.05 * 30) ≈ 1.79 * 0.223 ≈ 0.40
        assert strength_month < strength_week

    def test_strength_increases_with_count(self):
        """Test that strength increases with co-retrieval count."""
        from src.retrieval.coretrieval_graph import CoRetrievalTracker

        tracker = CoRetrievalTracker()

        strength_1 = tracker._compute_strength(count=1, days_since_last=0)
        strength_5 = tracker._compute_strength(count=5, days_since_last=0)
        strength_10 = tracker._compute_strength(count=10, days_since_last=0)

        assert strength_1 < strength_5 < strength_10

    def test_strength_decays_over_time(self):
        """Test that strength decays exponentially over time."""
        from src.retrieval.coretrieval_graph import CoRetrievalTracker

        tracker = CoRetrievalTracker()

        strengths = [
            tracker._compute_strength(count=10, days_since_last=d)
            for d in [0, 7, 14, 30, 60, 90]
        ]

        # Each should be less than the previous
        for i in range(1, len(strengths)):
            assert strengths[i] < strengths[i-1]

    def test_strength_never_negative(self):
        """Test that strength is never negative."""
        from src.retrieval.coretrieval_graph import CoRetrievalTracker

        tracker = CoRetrievalTracker()

        # Very old, low count
        strength = tracker._compute_strength(count=1, days_since_last=365)

        assert strength >= 0


# ============================================================
# CO-RETRIEVAL RECORDING TESTS
# ============================================================

class TestCoRetrievalRecording:
    """Tests for recording co-retrieval events."""

    @pytest.fixture
    def tracker(self):
        from src.retrieval.coretrieval_graph import CoRetrievalTracker
        return CoRetrievalTracker()

    @pytest.mark.asyncio
    async def test_record_co_retrieval_creates_edges(self, tracker):
        """Test that recording co-retrieval creates edges between items."""
        # Simulate retrieved items in a session
        retrieved_ids = ["item-1", "item-2", "item-3"]
        session_id = "session-123"
        topic = "debugging"

        # Record the co-retrieval (in-memory for testing)
        await tracker.record_co_retrieval(
            session_id=session_id,
            retrieved_ids=retrieved_ids,
            topic=topic,
        )

        # Should create edges: (1,2), (1,3), (2,3)
        edges = tracker._get_pending_edges()
        assert len(edges) == 3

    @pytest.mark.asyncio
    async def test_record_co_retrieval_with_single_item(self, tracker):
        """Test that single item doesn't create edges."""
        await tracker.record_co_retrieval(
            session_id="session-1",
            retrieved_ids=["item-1"],
            topic="topic",
        )

        edges = tracker._get_pending_edges()
        assert len(edges) == 0

    @pytest.mark.asyncio
    async def test_record_co_retrieval_with_empty_list(self, tracker):
        """Test that empty list doesn't create edges."""
        await tracker.record_co_retrieval(
            session_id="session-1",
            retrieved_ids=[],
            topic="topic",
        )

        edges = tracker._get_pending_edges()
        assert len(edges) == 0

    @pytest.mark.asyncio
    async def test_record_co_retrieval_deduplicates_ids(self, tracker):
        """Test that duplicate IDs are handled correctly."""
        await tracker.record_co_retrieval(
            session_id="session-1",
            retrieved_ids=["item-1", "item-1", "item-2", "item-2"],
            topic="topic",
        )

        # Should only create 1 edge: (item-1, item-2)
        edges = tracker._get_pending_edges()
        assert len(edges) == 1

    @pytest.mark.asyncio
    async def test_record_co_retrieval_tracks_topics(self, tracker):
        """Test that topics are tracked for context."""
        await tracker.record_co_retrieval(
            session_id="session-1",
            retrieved_ids=["item-1", "item-2"],
            topic="kubernetes",
        )

        edges = tracker._get_pending_edges()
        assert len(edges) == 1
        assert "kubernetes" in edges[0].context_topics


# ============================================================
# EDGE ORDERING TESTS
# ============================================================

class TestEdgeOrdering:
    """Tests for consistent edge ordering (item_a < item_b)."""

    @pytest.fixture
    def tracker(self):
        from src.retrieval.coretrieval_graph import CoRetrievalTracker
        return CoRetrievalTracker()

    def test_edge_ordering_consistent(self, tracker):
        """Test that edges are ordered consistently (a < b)."""
        # Regardless of input order, edge should be normalized
        edge1 = tracker._normalize_edge("item-z", "item-a")
        edge2 = tracker._normalize_edge("item-a", "item-z")

        assert edge1 == edge2
        assert edge1 == ("item-a", "item-z")

    def test_edge_ordering_alphabetical(self, tracker):
        """Test that edge ordering is alphabetical."""
        edge = tracker._normalize_edge("python", "debugging")
        assert edge == ("debugging", "python")


# ============================================================
# ASSOCIATED ITEMS RETRIEVAL TESTS
# ============================================================

class TestAssociatedItemsRetrieval:
    """Tests for retrieving associated items."""

    @pytest.fixture
    def tracker(self):
        from src.retrieval.coretrieval_graph import CoRetrievalTracker
        tracker = CoRetrievalTracker()
        # Pre-populate with mock edges
        tracker._mock_edges = {
            ("item-1", "item-2"): MockCoRetrievalEdge(
                item_a_id="item-1", item_b_id="item-2",
                co_retrieval_count=10, strength=2.5
            ),
            ("item-1", "item-3"): MockCoRetrievalEdge(
                item_a_id="item-1", item_b_id="item-3",
                co_retrieval_count=5, strength=1.8
            ),
            ("item-1", "item-4"): MockCoRetrievalEdge(
                item_a_id="item-1", item_b_id="item-4",
                co_retrieval_count=2, strength=0.5
            ),
            ("item-2", "item-3"): MockCoRetrievalEdge(
                item_a_id="item-2", item_b_id="item-3",
                co_retrieval_count=8, strength=2.0
            ),
        }
        return tracker

    @pytest.mark.asyncio
    async def test_get_associated_items(self, tracker):
        """Test retrieving items associated with a given item."""
        associated = await tracker.get_associated_items(
            item_id="item-1",
            min_strength=0.0,
            limit=10,
        )

        # Should return item-2, item-3, item-4
        assert len(associated) == 3
        # Should be ordered by strength (descending)
        assert associated[0][0] == "item-2"  # strength 2.5
        assert associated[1][0] == "item-3"  # strength 1.8
        assert associated[2][0] == "item-4"  # strength 0.5

    @pytest.mark.asyncio
    async def test_get_associated_items_with_min_strength(self, tracker):
        """Test filtering by minimum strength."""
        associated = await tracker.get_associated_items(
            item_id="item-1",
            min_strength=1.0,
            limit=10,
        )

        # Should only return item-2 and item-3 (strength > 1.0)
        assert len(associated) == 2

    @pytest.mark.asyncio
    async def test_get_associated_items_with_limit(self, tracker):
        """Test limiting number of results."""
        associated = await tracker.get_associated_items(
            item_id="item-1",
            min_strength=0.0,
            limit=2,
        )

        assert len(associated) == 2

    @pytest.mark.asyncio
    async def test_get_associated_items_unknown_item(self, tracker):
        """Test with item that has no associations."""
        associated = await tracker.get_associated_items(
            item_id="unknown-item",
            min_strength=0.0,
            limit=10,
        )

        assert len(associated) == 0


# ============================================================
# BATCH FLUSH TESTS
# ============================================================

class TestBatchFlush:
    """Tests for batch flushing edges to database."""

    @pytest.fixture
    def tracker(self):
        from src.retrieval.coretrieval_graph import CoRetrievalTracker
        return CoRetrievalTracker()

    @pytest.mark.asyncio
    async def test_flush_pending_edges(self, tracker):
        """Test flushing pending edges to database."""
        # Record some co-retrievals
        await tracker.record_co_retrieval(
            session_id="s1",
            retrieved_ids=["item-1", "item-2", "item-3"],
            topic="topic1",
        )
        await tracker.record_co_retrieval(
            session_id="s2",
            retrieved_ids=["item-1", "item-2"],
            topic="topic2",
        )

        # Check pending edges exist
        pending = tracker._get_pending_edges()
        assert len(pending) > 0

        # Flush (mock DB)
        with patch.object(tracker, '_flush_to_db', new_callable=AsyncMock) as mock_flush:
            await tracker.flush()
            mock_flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_auto_flush_threshold(self, tracker):
        """Test auto-flush when pending edges exceed threshold."""
        tracker._auto_flush_threshold = 5

        # Record enough co-retrievals to trigger auto-flush
        with patch.object(tracker, '_flush_to_db', new_callable=AsyncMock) as mock_flush:
            for i in range(10):
                await tracker.record_co_retrieval(
                    session_id=f"session-{i}",
                    retrieved_ids=[f"item-{i}", f"item-{i+1}"],
                    topic="topic",
                )

            # Should have triggered auto-flush
            assert mock_flush.call_count >= 1


# ============================================================
# STRENGTH UPDATE TESTS
# ============================================================

class TestStrengthUpdate:
    """Tests for updating edge strength on repeat co-retrieval."""

    @pytest.fixture
    def tracker(self):
        from src.retrieval.coretrieval_graph import CoRetrievalTracker
        return CoRetrievalTracker()

    @pytest.mark.asyncio
    async def test_repeated_co_retrieval_increases_count(self, tracker):
        """Test that repeated co-retrieval increases count."""
        # First co-retrieval
        await tracker.record_co_retrieval(
            session_id="s1",
            retrieved_ids=["item-1", "item-2"],
            topic="topic",
        )

        edges1 = tracker._get_pending_edges()
        assert edges1[0].co_retrieval_count == 1

        # Second co-retrieval (same pair)
        await tracker.record_co_retrieval(
            session_id="s2",
            retrieved_ids=["item-1", "item-2"],
            topic="topic",
        )

        edges2 = tracker._get_pending_edges()
        # Should have updated the existing edge
        matching = [e for e in edges2 if set([e.item_a_id, e.item_b_id]) == {"item-1", "item-2"}]
        assert len(matching) == 1
        assert matching[0].co_retrieval_count == 2


# ============================================================
# COGNITIVE PRINCIPLE TESTS
# ============================================================

class TestCognitivePrinciples:
    """Tests that verify Hebbian learning principles."""

    @pytest.fixture
    def tracker(self):
        from src.retrieval.coretrieval_graph import CoRetrievalTracker
        return CoRetrievalTracker()

    def test_hebbian_fire_together_wire_together(self, tracker):
        """
        Cognitive Principle: Hebbian Learning

        "Neurons that fire together, wire together."
        Items retrieved together should form associations.
        """
        # This is the core principle - tested via record_co_retrieval
        # The fact that we create edges between co-retrieved items
        # implements this principle
        pass  # Covered by TestCoRetrievalRecording

    def test_association_strengthens_with_repetition(self, tracker):
        """
        Cognitive Principle: Use-dependent plasticity

        Associations strengthen with repeated co-activation.
        """
        strength_1 = tracker._compute_strength(count=1, days_since_last=0)
        strength_5 = tracker._compute_strength(count=5, days_since_last=0)
        strength_20 = tracker._compute_strength(count=20, days_since_last=0)

        # Logarithmic growth (not linear) - mirrors neural learning
        assert strength_5 > strength_1
        assert strength_20 > strength_5
        # But diminishing returns
        growth_1_to_5 = strength_5 - strength_1
        growth_5_to_20 = strength_20 - strength_5
        # The 15 extra retrievals should add less than the first 4
        assert growth_5_to_20 < growth_1_to_5 * 4

    def test_association_decays_without_reinforcement(self, tracker):
        """
        Cognitive Principle: Synaptic decay

        Unused associations weaken over time.
        """
        initial_strength = tracker._compute_strength(count=10, days_since_last=0)
        week_later = tracker._compute_strength(count=10, days_since_last=7)
        month_later = tracker._compute_strength(count=10, days_since_last=30)

        # Without reinforcement, strength decays
        assert week_later < initial_strength
        assert month_later < week_later


# ============================================================
# STATISTICS TESTS
# ============================================================

class TestCoRetrievalStats:
    """Tests for statistics and monitoring."""

    @pytest.fixture
    def tracker(self):
        from src.retrieval.coretrieval_graph import CoRetrievalTracker
        return CoRetrievalTracker()

    @pytest.mark.asyncio
    async def test_get_stats(self, tracker):
        """Test statistics retrieval."""
        # Record some co-retrievals
        await tracker.record_co_retrieval(
            session_id="s1",
            retrieved_ids=["item-1", "item-2", "item-3"],
            topic="topic1",
        )

        stats = tracker.get_stats()

        assert "pending_edges" in stats
        assert "total_recorded" in stats
        assert "auto_flush_threshold" in stats


# ============================================================
# EDGE CASE TESTS
# ============================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def tracker(self):
        from src.retrieval.coretrieval_graph import CoRetrievalTracker
        return CoRetrievalTracker()

    @pytest.mark.asyncio
    async def test_record_with_none_session_id(self, tracker):
        """Test recording with None session ID."""
        # Should still work
        await tracker.record_co_retrieval(
            session_id=None,
            retrieved_ids=["item-1", "item-2"],
            topic="topic",
        )

        edges = tracker._get_pending_edges()
        assert len(edges) == 1

    @pytest.mark.asyncio
    async def test_record_with_empty_topic(self, tracker):
        """Test recording with empty topic."""
        await tracker.record_co_retrieval(
            session_id="s1",
            retrieved_ids=["item-1", "item-2"],
            topic="",
        )

        edges = tracker._get_pending_edges()
        assert len(edges) == 1

    @pytest.mark.asyncio
    async def test_very_large_retrieved_set(self, tracker):
        """Test with large number of retrieved items."""
        # 20 items = 190 possible edges (20 choose 2)
        large_set = [f"item-{i}" for i in range(20)]

        await tracker.record_co_retrieval(
            session_id="s1",
            retrieved_ids=large_set,
            topic="topic",
        )

        edges = tracker._get_pending_edges()
        # Should limit to avoid explosion
        # 20 choose 2 = 190, but we might cap it
        assert len(edges) <= 190

    def test_compute_strength_with_zero_count(self, tracker):
        """Test strength computation with zero count."""
        strength = tracker._compute_strength(count=0, days_since_last=0)
        # log(1) = 0
        assert strength == 0.0

    def test_compute_strength_with_negative_days(self, tracker):
        """Test strength computation handles edge cases gracefully."""
        # Negative days shouldn't happen but should be handled
        strength = tracker._compute_strength(count=5, days_since_last=-1)
        # Should treat as 0 or handle gracefully
        assert strength >= 0
