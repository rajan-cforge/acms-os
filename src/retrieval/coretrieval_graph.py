"""Co-Retrieval Graph for ACMS Retrieval Pipeline.

Cognitive Principle: Hebbian Learning
"Neurons that fire together, wire together"

When multiple knowledge items are retrieved together in response to a query,
they form an association. Repeated co-retrieval strengthens this association,
allowing the system to preload related items for faster context assembly.

This module implements:
1. Recording co-retrieval events (items retrieved together)
2. Computing association strength using Hebbian formula
3. Retrieving associated items for context preloading

Strength Formula: log(count + 1) * exp(-decay_rate * days_since_last)

Expected Impact:
- Faster context assembly through association preloading
- Better related item discovery
- Natural "spreading activation" for exploratory queries

Usage:
    from src.retrieval.coretrieval_graph import CoRetrievalTracker

    tracker = CoRetrievalTracker()

    # Record co-retrieval after each query
    await tracker.record_co_retrieval(
        session_id="session-123",
        retrieved_ids=["item-1", "item-2", "item-3"],
        topic="kubernetes"
    )

    # Get associated items for preloading
    associated = await tracker.get_associated_items(
        item_id="item-1",
        min_strength=0.5,
        limit=5
    )
"""

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Set, Tuple, Any
from collections import defaultdict
import itertools

logger = logging.getLogger(__name__)


@dataclass
class CoRetrievalConfig:
    """Configuration for co-retrieval tracking.

    Attributes:
        decay_rate: Exponential decay rate for association strength (per day)
        min_strength_threshold: Minimum strength to maintain an edge
        max_associated_items: Maximum items to return from get_associated_items
        min_count_threshold: Minimum co-retrieval count to consider
        auto_flush_threshold: Number of pending edges before auto-flush
        max_edges_per_recording: Limit edges created per recording to avoid explosion
    """
    decay_rate: float = 0.05  # ~50% decay after 14 days
    min_strength_threshold: float = 0.01
    max_associated_items: int = 10
    min_count_threshold: int = 2
    auto_flush_threshold: int = 100
    max_edges_per_recording: int = 50  # Limit for large result sets


@dataclass
class PendingEdge:
    """A pending co-retrieval edge not yet flushed to DB."""
    item_a_id: str
    item_b_id: str
    co_retrieval_count: int = 1
    last_co_retrieval: datetime = None
    context_topics: Dict[str, int] = None

    def __post_init__(self):
        if self.last_co_retrieval is None:
            self.last_co_retrieval = datetime.now(timezone.utc)
        if self.context_topics is None:
            self.context_topics = {}


class CoRetrievalTracker:
    """Tracks co-retrieval patterns using Hebbian learning.

    Implements the cognitive principle that items retrieved together
    form associations that strengthen over time with repeated use.

    Usage:
        tracker = CoRetrievalTracker()
        await tracker.record_co_retrieval(session_id, retrieved_ids, topic)
        associated = await tracker.get_associated_items(item_id)
    """

    def __init__(self, config: Optional[CoRetrievalConfig] = None):
        """Initialize co-retrieval tracker.

        Args:
            config: Optional configuration overrides
        """
        self.config = config or CoRetrievalConfig()

        # In-memory pending edges (edge_key -> PendingEdge)
        self._pending_edges: Dict[Tuple[str, str], PendingEdge] = {}

        # Mock edges for testing (populated by test fixtures)
        self._mock_edges: Dict[Tuple[str, str], Any] = {}

        # Auto-flush threshold
        self._auto_flush_threshold = self.config.auto_flush_threshold

        # Statistics
        self._total_recorded = 0
        self._total_flushed = 0

    def _compute_strength(self, count: int, days_since_last: float) -> float:
        """Compute Hebbian association strength.

        Formula: log(count + 1) * exp(-decay_rate * days_since_last)

        Cognitive basis:
        - log(count+1): Diminishing returns with repetition
        - exp(-decay): Exponential decay without reinforcement

        Args:
            count: Number of co-retrieval events
            days_since_last: Days since last co-retrieval

        Returns:
            Association strength (0.0+)
        """
        if count <= 0:
            return 0.0

        # Handle negative days gracefully
        days = max(0.0, days_since_last)

        # Hebbian formula
        repetition_factor = math.log(count + 1)
        decay_factor = math.exp(-self.config.decay_rate * days)

        return repetition_factor * decay_factor

    def _normalize_edge(self, item_a: str, item_b: str) -> Tuple[str, str]:
        """Normalize edge to consistent ordering (a < b).

        This ensures (A,B) and (B,A) are treated as the same edge.

        Args:
            item_a: First item ID
            item_b: Second item ID

        Returns:
            Tuple with smaller ID first
        """
        if item_a <= item_b:
            return (item_a, item_b)
        return (item_b, item_a)

    async def record_co_retrieval(
        self,
        session_id: Optional[str],
        retrieved_ids: List[str],
        topic: str,
    ) -> int:
        """Record co-retrieval event for all item pairs.

        Cognitive basis: Items retrieved together form associations.

        Args:
            session_id: Session identifier (for tracking)
            retrieved_ids: List of retrieved item IDs
            topic: Topic context for the retrieval

        Returns:
            Number of edges created/updated
        """
        if not retrieved_ids:
            return 0

        # Deduplicate IDs
        unique_ids = list(set(retrieved_ids))

        if len(unique_ids) < 2:
            return 0

        # Limit to avoid explosion with large result sets
        if len(unique_ids) > 20:
            unique_ids = unique_ids[:20]  # Take first 20

        # Generate all pairs
        pairs = list(itertools.combinations(unique_ids, 2))

        # Limit pairs if still too many
        if len(pairs) > self.config.max_edges_per_recording:
            pairs = pairs[:self.config.max_edges_per_recording]

        edges_updated = 0
        now = datetime.now(timezone.utc)

        for item_a, item_b in pairs:
            edge_key = self._normalize_edge(item_a, item_b)

            if edge_key in self._pending_edges:
                # Update existing edge
                edge = self._pending_edges[edge_key]
                edge.co_retrieval_count += 1
                edge.last_co_retrieval = now
                if topic:
                    edge.context_topics[topic] = edge.context_topics.get(topic, 0) + 1
            else:
                # Create new edge
                context = {topic: 1} if topic else {}
                self._pending_edges[edge_key] = PendingEdge(
                    item_a_id=edge_key[0],
                    item_b_id=edge_key[1],
                    co_retrieval_count=1,
                    last_co_retrieval=now,
                    context_topics=context,
                )

            edges_updated += 1

        self._total_recorded += 1

        # Auto-flush if threshold exceeded
        if len(self._pending_edges) >= self._auto_flush_threshold:
            await self.flush()

        return edges_updated

    def _get_pending_edges(self) -> List[PendingEdge]:
        """Get list of pending edges (for testing)."""
        return list(self._pending_edges.values())

    async def get_associated_items(
        self,
        item_id: str,
        min_strength: float = 0.0,
        limit: int = 10,
    ) -> List[Tuple[str, float]]:
        """Get items associated with the given item.

        Returns items that have been co-retrieved with the target,
        ordered by association strength.

        Args:
            item_id: Target item ID
            min_strength: Minimum strength threshold
            limit: Maximum items to return

        Returns:
            List of (item_id, strength) tuples, ordered by strength desc
        """
        associations: List[Tuple[str, float]] = []
        now = datetime.now(timezone.utc)

        # Check mock edges (for testing)
        for edge_key, edge in self._mock_edges.items():
            if item_id not in edge_key:
                continue

            # Get the other item
            other_id = edge_key[0] if edge_key[1] == item_id else edge_key[1]

            # Compute current strength
            if hasattr(edge, 'strength'):
                strength = edge.strength
            else:
                days_since = (now - edge.last_co_retrieval).total_seconds() / 86400
                strength = self._compute_strength(edge.co_retrieval_count, days_since)

            if strength >= min_strength:
                associations.append((other_id, strength))

        # Check pending edges
        for edge_key, edge in self._pending_edges.items():
            if item_id not in edge_key:
                continue

            other_id = edge_key[0] if edge_key[1] == item_id else edge_key[1]
            days_since = (now - edge.last_co_retrieval).total_seconds() / 86400
            strength = self._compute_strength(edge.co_retrieval_count, days_since)

            if strength >= min_strength:
                associations.append((other_id, strength))

        # Sort by strength descending and limit
        associations.sort(key=lambda x: x[1], reverse=True)
        return associations[:limit]

    async def flush(self) -> int:
        """Flush pending edges to database.

        Upserts edges with updated counts and timestamps.

        Returns:
            Number of edges flushed
        """
        if not self._pending_edges:
            return 0

        edges_to_flush = list(self._pending_edges.values())
        count = len(edges_to_flush)

        try:
            await self._flush_to_db(edges_to_flush)
            self._pending_edges.clear()
            self._total_flushed += count
            logger.info(f"[CoRetrieval] Flushed {count} edges to database")
        except Exception as e:
            logger.error(f"[CoRetrieval] Flush failed: {e}")
            # Keep edges in pending for retry
            raise

        return count

    async def _flush_to_db(self, edges: List[PendingEdge]) -> None:
        """Flush edges to database (upsert).

        Args:
            edges: List of edges to flush
        """
        # In production, this would upsert to coretrieval_edges table
        # For now, this is a placeholder for the database integration
        try:
            from src.storage.database import get_session
            from sqlalchemy import text

            async with get_session() as session:
                for edge in edges:
                    # Compute strength for storage
                    now = datetime.now(timezone.utc)
                    days_since = (now - edge.last_co_retrieval).total_seconds() / 86400
                    strength = self._compute_strength(
                        edge.co_retrieval_count,
                        days_since
                    )

                    # Upsert edge
                    await session.execute(
                        text("""
                            INSERT INTO coretrieval_edges (
                                item_a_id, item_b_id, co_retrieval_count,
                                last_co_retrieval, strength, context_topics,
                                created_at, updated_at
                            ) VALUES (
                                :item_a, :item_b, :count,
                                :last_retrieval, :strength, :topics::jsonb,
                                NOW(), NOW()
                            )
                            ON CONFLICT (item_a_id, item_b_id) DO UPDATE SET
                                co_retrieval_count = coretrieval_edges.co_retrieval_count + :count,
                                last_co_retrieval = :last_retrieval,
                                strength = :strength,
                                context_topics = coretrieval_edges.context_topics || :topics::jsonb,
                                updated_at = NOW()
                        """),
                        {
                            "item_a": edge.item_a_id,
                            "item_b": edge.item_b_id,
                            "count": edge.co_retrieval_count,
                            "last_retrieval": edge.last_co_retrieval,
                            "strength": strength,
                            "topics": str(edge.context_topics).replace("'", '"'),
                        }
                    )

                await session.commit()

        except ImportError:
            # Database not available (testing)
            logger.debug("[CoRetrieval] Database not available, skipping flush")
        except Exception as e:
            logger.error(f"[CoRetrieval] Database flush failed: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get tracker statistics.

        Returns:
            Dict with pending_edges, total_recorded, etc.
        """
        return {
            "pending_edges": len(self._pending_edges),
            "total_recorded": self._total_recorded,
            "total_flushed": self._total_flushed,
            "auto_flush_threshold": self._auto_flush_threshold,
            "config": {
                "decay_rate": self.config.decay_rate,
                "min_strength_threshold": self.config.min_strength_threshold,
            },
        }

    def reset(self) -> None:
        """Reset tracker state (for testing)."""
        self._pending_edges.clear()
        self._mock_edges.clear()
        self._total_recorded = 0
        self._total_flushed = 0


# ============================================================
# HELPER FUNCTIONS
# ============================================================

# Global instance
_tracker_instance: Optional[CoRetrievalTracker] = None


def get_coretrieval_tracker() -> CoRetrievalTracker:
    """Get global co-retrieval tracker instance."""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = CoRetrievalTracker()
    return _tracker_instance
