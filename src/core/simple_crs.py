"""
CRS (Context Retrieval Score) - 5-Factor Scoring System

5-Factor Scoring:
- Semantic Similarity: 40% (how well content matches query)
- Recency: 20% (how recent the memory is)
- Importance/Tier: 20% (importance level: LONG/MID/SHORT)
- Feedback: 10% (user feedback - thumbs up/down)
- Frequency: 10% (how often memory is accessed)

Reference Architecture Alignment:
score = similarity * α + recency * β + importance * γ + feedback * δ + frequency * ε
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import math
import logging

logger = logging.getLogger(__name__)


class SimpleCRS:
    """
    5-factor CRS scoring system for memory ranking.

    Provides comprehensive scoring using all available signals:
    semantic similarity, recency, importance, feedback, and frequency.
    """

    # Default weights (sum to 1.0) - 5 factors
    DEFAULT_WEIGHTS = {
        'semantic': 0.4,   # Content matching (was 0.5)
        'recency': 0.2,    # Time decay (was 0.3)
        'tier': 0.2,       # Importance level (was 0.2)
        'feedback': 0.1,   # User feedback (NEW)
        'frequency': 0.1   # Access frequency (NEW)
    }

    # Tier importance multipliers
    TIER_WEIGHTS = {
        'LONG': 1.2,   # Permanent, high importance
        'MID': 1.0,    # Medium-term, standard
        'SHORT': 0.8   # Temporary, lower importance
    }

    # Recency decay constants
    RECENCY_HALF_LIFE_DAYS = 30  # 30-day half-life for exponential decay

    # Frequency scaling constants
    FREQUENCY_LOG_BASE = 10  # Log base for frequency normalization
    MAX_ACCESS_COUNT = 100   # Cap for normalization

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """
        Initialize SimpleCRS with optional custom weights.

        Args:
            weights: Optional dict with keys 'semantic', 'recency', 'tier', 'feedback', 'frequency'
                    If provided, will be normalized to sum to 1.0
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self._normalize_weights()

    def _normalize_weights(self):
        """Ensure weights sum to 1.0"""
        total = sum(self.weights.values())
        if total > 0:
            for key in self.weights:
                self.weights[key] /= total

    def calculate_score(
        self,
        semantic_similarity: float,
        created_at: datetime,
        tier: str,
        feedback_summary: Optional[Dict[str, Any]] = None,
        access_count: int = 0,
        now: Optional[datetime] = None
    ) -> float:
        """
        Calculate 5-factor CRS score for a memory.

        Args:
            semantic_similarity: Float 0-1, from vector similarity
            created_at: When memory was created
            tier: Memory tier (LONG/MID/SHORT)
            feedback_summary: Dict with {avg_rating, thumbs_up, thumbs_down} (NEW)
            access_count: How many times memory was accessed (NEW)
            now: Current time (defaults to datetime.now())

        Returns:
            Float 0-1 representing overall CRS score
        """
        if now is None:
            now = datetime.now()

        # Factor 1: Semantic similarity (0-1)
        semantic_score = self._semantic_score(semantic_similarity)

        # Factor 2: Recency score (0-1, exponential decay)
        recency_score = self._recency_score(created_at, now)

        # Factor 3: Tier importance (0-1, mapped from multipliers)
        tier_score = self._tier_score(tier)

        # Factor 4: Feedback score (0-1, from user ratings) - NEW
        feedback_score = self._feedback_score(feedback_summary)

        # Factor 5: Frequency score (0-1, from access count) - NEW
        frequency_score = self._frequency_score(access_count)

        # Weighted 5-factor combination
        crs_score = (
            semantic_score * self.weights.get('semantic', 0.4) +
            recency_score * self.weights.get('recency', 0.2) +
            tier_score * self.weights.get('tier', 0.2) +
            feedback_score * self.weights.get('feedback', 0.1) +
            frequency_score * self.weights.get('frequency', 0.1)
        )

        # Clamp to [0, 1]
        return max(0.0, min(1.0, crs_score))

    def _semantic_score(self, similarity: float) -> float:
        """
        Convert semantic similarity to score.

        For Phase 3, this is just a passthrough.
        Future versions might apply curves or thresholds.

        Args:
            similarity: Raw similarity from vector search (0-1)

        Returns:
            Semantic score (0-1)
        """
        return max(0.0, min(1.0, similarity))

    def _recency_score(self, created_at: datetime, now: datetime) -> float:
        """
        Calculate recency score using exponential decay.

        Uses half-life decay: score = exp(-days / half_life)
        - Recent memories: score near 1.0
        - Old memories: score decays toward 0.0
        - 30-day half-life: 50% score after 30 days

        Args:
            created_at: When memory was created
            now: Current time

        Returns:
            Recency score (0-1)
        """
        # Handle timezone-naive datetimes
        if created_at.tzinfo is not None and now.tzinfo is None:
            now = now.replace(tzinfo=created_at.tzinfo)
        elif created_at.tzinfo is None and now.tzinfo is not None:
            created_at = created_at.replace(tzinfo=now.tzinfo)

        # Calculate days since creation
        delta = now - created_at
        days_old = delta.total_seconds() / (60 * 60 * 24)

        # Exponential decay
        decay_constant = self.RECENCY_HALF_LIFE_DAYS / math.log(2)
        score = math.exp(-days_old / decay_constant)

        return max(0.0, min(1.0, score))

    def _tier_score(self, tier: str) -> float:
        """
        Convert tier to normalized score.

        Tier weights are multipliers (0.8-1.2), normalize to 0-1 range.

        Args:
            tier: Memory tier (LONG/MID/SHORT)

        Returns:
            Tier score (0-1)
        """
        tier_upper = tier.upper()
        multiplier = self.TIER_WEIGHTS.get(tier_upper, 1.0)

        # Normalize from [0.8, 1.2] to [0, 1] range
        min_tier = 0.8
        max_tier = 1.2
        normalized = (multiplier - min_tier) / (max_tier - min_tier)

        return max(0.0, min(1.0, normalized))

    def _feedback_score(self, feedback_summary: Optional[Dict[str, Any]]) -> float:
        """
        Convert user feedback to score (NEW - Factor 4).

        Uses feedback_summary JSON from memory_items table:
        - avg_rating: -1.0 to 1.0 scale
        - thumbs_up/thumbs_down counts

        Args:
            feedback_summary: Dict with {avg_rating, thumbs_up, thumbs_down, total_ratings}

        Returns:
            Feedback score (0-1), 0.5 = neutral/no feedback
        """
        if not feedback_summary:
            return 0.5  # Neutral score for no feedback

        # Option 1: Use avg_rating if available (-1 to 1 → 0 to 1)
        avg_rating = feedback_summary.get('avg_rating')
        if avg_rating is not None:
            # Convert from [-1, 1] to [0, 1]
            return (avg_rating + 1.0) / 2.0

        # Option 2: Calculate from thumbs up/down
        thumbs_up = feedback_summary.get('thumbs_up', 0)
        thumbs_down = feedback_summary.get('thumbs_down', 0)
        total = thumbs_up + thumbs_down

        if total == 0:
            return 0.5  # Neutral

        # Wilson score lower bound (more robust than simple ratio)
        # Simplified version: positive ratio with slight pessimism
        positive_ratio = thumbs_up / total
        # Add slight dampening for low sample sizes
        confidence = min(1.0, total / 10.0)  # Full confidence at 10+ ratings
        score = 0.5 + (positive_ratio - 0.5) * confidence

        return max(0.0, min(1.0, score))

    def _frequency_score(self, access_count: int) -> float:
        """
        Convert access frequency to score (NEW - Factor 5).

        Uses logarithmic scaling to prevent runaway scores:
        - 0 accesses = 0.0
        - 1 access = ~0.3
        - 10 accesses = ~0.5
        - 100 accesses = ~1.0

        Args:
            access_count: Number of times memory was accessed

        Returns:
            Frequency score (0-1)
        """
        if access_count <= 0:
            return 0.0

        # Logarithmic scaling with cap
        capped_count = min(access_count, self.MAX_ACCESS_COUNT)

        # log10(1) = 0, log10(10) = 1, log10(100) = 2
        # Normalize to [0, 1] using log10(MAX_ACCESS_COUNT)
        max_log = math.log10(self.MAX_ACCESS_COUNT)  # log10(100) = 2
        score = math.log10(capped_count + 1) / (max_log + 0.1)  # +0.1 to avoid div issues

        return max(0.0, min(1.0, score))

    def batch_calculate(
        self,
        memories: List[Dict],
        now: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Calculate 5-factor CRS scores for multiple memories.

        Args:
            memories: List of memory dicts with keys:
                     - distance: Weaviate distance (0-1, lower is better)
                     - created_at: datetime object
                     - tier: str (LONG/MID/SHORT)
                     - feedback_summary: Optional dict with ratings (NEW)
                     - access_count: Optional int (NEW)
            now: Current time (defaults to datetime.now())

        Returns:
            List of memory dicts with added 'crs_score' key
        """
        if now is None:
            now = datetime.now()

        scored_memories = []
        for memory in memories:
            # Convert Weaviate distance to similarity (1 - distance)
            distance = memory.get('distance', 0.2)
            similarity = 1.0 - distance

            # Get new factors (with defaults for backwards compatibility)
            feedback_summary = memory.get('feedback_summary') or memory.get('properties', {}).get('feedback_summary')
            access_count = memory.get('access_count', 0) or memory.get('properties', {}).get('access_count', 0)

            # Calculate 5-factor CRS
            crs_score = self.calculate_score(
                semantic_similarity=similarity,
                created_at=memory['created_at'],
                tier=memory['tier'],
                feedback_summary=feedback_summary,
                access_count=access_count,
                now=now
            )

            # Add score to memory
            memory_with_score = memory.copy()
            memory_with_score['crs_score'] = round(crs_score, 4)
            scored_memories.append(memory_with_score)

        return scored_memories

    def update_weights(self, new_weights: Dict[str, float]):
        """
        Update CRS weights (useful for settings panel).

        Args:
            new_weights: Dict with keys 'semantic', 'recency', 'tier'
                        Will be normalized to sum to 1.0
        """
        self.weights.update(new_weights)
        self._normalize_weights()

    def get_weights(self) -> Dict[str, float]:
        """Get current weights"""
        return self.weights.copy()

    def reset_weights(self):
        """Reset to default weights"""
        self.weights = self.DEFAULT_WEIGHTS.copy()


# Convenience function for quick scoring
def calculate_crs(
    semantic_similarity: float,
    created_at: datetime,
    tier: str,
    feedback_summary: Optional[Dict[str, Any]] = None,
    access_count: int = 0,
    weights: Optional[Dict[str, float]] = None
) -> float:
    """
    Quick 5-factor CRS calculation without creating CRS instance.

    Args:
        semantic_similarity: 0-1 from vector search
        created_at: Memory creation time
        tier: LONG/MID/SHORT
        feedback_summary: Optional feedback dict (NEW)
        access_count: Optional access count (NEW)
        weights: Optional custom weights

    Returns:
        CRS score (0-1)
    """
    crs = SimpleCRS(weights)
    return crs.calculate_score(
        semantic_similarity, created_at, tier,
        feedback_summary, access_count
    )
