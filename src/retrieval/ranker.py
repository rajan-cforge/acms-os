"""Ranker - Stage 2 of retrieval pipeline (CRS scoring).

Context Relevance Score (CRS) Algorithm:
    score = w1*similarity + w2*recency + w3*importance + w4*feedback

Default weights (Blueprint Section 4.1):
    similarity: 0.5 (most important - semantic match)
    recency: 0.2 (newer is better, exponential decay)
    importance: 0.2 (from metadata or default)
    feedback: 0.1 (user feedback signals)

Does NOT:
- Fetch data (that's Retriever's job)
- Build context (that's ContextBuilder's job)
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Optional
from math import exp

from src.retrieval.retriever import RawResult

logger = logging.getLogger(__name__)


@dataclass
class ScoredResult:
    """Result with CRS score and breakdown.

    Attributes:
        item: Original RawResult
        score: Combined CRS score (0.0-1.0)
        breakdown: Individual component scores for debugging
    """
    item: RawResult
    score: float
    breakdown: Dict[str, float]


class Ranker:
    """Stage 2: CRS (Context Relevance Score) ranking.

    Scores and re-ranks retrieval results using weighted factors:
    - Similarity: Semantic match quality (from vector distance)
    - Recency: How recent the content is (exponential decay)
    - Importance: Content importance level (from metadata)
    - Feedback: User feedback signals (from metadata)

    Example:
        ranker = Ranker()
        scored = ranker.score(raw_results, now=datetime.now(timezone.utc))
        # scored is sorted by score (highest first)
    """

    # Default CRS weights
    DEFAULT_WEIGHTS = {
        "similarity": 0.5,
        "recency": 0.2,
        "importance": 0.2,
        "feedback": 0.1
    }

    # Recency decay: half-life in days
    RECENCY_HALF_LIFE = 30

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        """Initialize ranker.

        Args:
            weights: Optional custom weights (must sum to 1.0)
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()

        logger.info(
            f"[Ranker] Initialized with weights: "
            f"sim={self.weights['similarity']}, "
            f"rec={self.weights['recency']}, "
            f"imp={self.weights['importance']}, "
            f"fb={self.weights['feedback']}"
        )

    def score(
        self,
        raw_results: List[RawResult],
        now: Optional[datetime] = None
    ) -> List[ScoredResult]:
        """Score and rank results using CRS algorithm.

        Args:
            raw_results: Raw results from Retriever
            now: Current time for recency calculation (default: now)

        Returns:
            Sorted list of ScoredResult (highest score first)
        """
        if now is None:
            now = datetime.now(timezone.utc)

        scored = []

        for r in raw_results:
            # Calculate individual components
            similarity = self._calculate_similarity(r)
            recency = self._calculate_recency(r.properties, now)
            importance = self._calculate_importance(r.properties)
            feedback = self._calculate_feedback(r.properties)

            # Combined CRS score
            total_score = (
                self.weights["similarity"] * similarity +
                self.weights["recency"] * recency +
                self.weights["importance"] * importance +
                self.weights["feedback"] * feedback
            )

            scored.append(ScoredResult(
                item=r,
                score=round(total_score, 4),
                breakdown={
                    "similarity": round(similarity, 4),
                    "recency": round(recency, 4),
                    "importance": round(importance, 4),
                    "feedback": round(feedback, 4)
                }
            ))

        # Sort by score (descending)
        scored.sort(key=lambda x: x.score, reverse=True)

        logger.debug(
            f"[Ranker] Scored {len(scored)} results, "
            f"top score: {scored[0].score if scored else 'N/A'}"
        )

        return scored

    def _calculate_similarity(self, result: RawResult) -> float:
        """Calculate similarity score from distance.

        Args:
            result: RawResult with distance

        Returns:
            Similarity score (0.0-1.0)
        """
        return result.similarity

    def _calculate_recency(
        self,
        properties: Dict,
        now: datetime
    ) -> float:
        """Calculate recency score with exponential decay.

        Half-life: 30 days (score halves every 30 days)

        Args:
            properties: Result properties with created_at
            now: Current time

        Returns:
            Recency score (0.0-1.0)
        """
        created_at_raw = properties.get("created_at")
        if not created_at_raw:
            return 0.5  # Default for unknown

        try:
            # Handle both datetime objects (from Weaviate) and strings
            if isinstance(created_at_raw, datetime):
                created_at = created_at_raw
            else:
                # Parse ISO format string
                created_at_str = str(created_at_raw)
                if created_at_str.endswith("Z"):
                    created_at_str = created_at_str[:-1] + "+00:00"
                created_at = datetime.fromisoformat(created_at_str)

            # Make timezone-aware if needed
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            # Calculate age in days
            age_delta = now - created_at
            age_days = max(0, age_delta.total_seconds() / 86400)

            # Exponential decay: score = e^(-age * ln(2) / half_life)
            decay = exp(-age_days * 0.693 / self.RECENCY_HALF_LIFE)

            return min(1.0, decay)

        except Exception as e:
            logger.warning(f"[Ranker] Could not parse created_at: {e}")
            return 0.5

    def _calculate_importance(self, properties: Dict) -> float:
        """Get importance score from properties.

        Args:
            properties: Result properties

        Returns:
            Importance score (0.0-1.0)
        """
        # Try different property names
        importance = properties.get("importance")
        if importance is not None:
            return min(1.0, max(0.0, float(importance)))

        # Try crs_score (legacy)
        crs = properties.get("crs_score")
        if crs is not None:
            return min(1.0, max(0.0, float(crs)))

        # Try confidence_score
        confidence = properties.get("confidence_score")
        if confidence is not None:
            return min(1.0, max(0.0, float(confidence)))

        return 0.5  # Default

    def _calculate_feedback(self, properties: Dict) -> float:
        """Get feedback score from properties.

        Args:
            properties: Result properties

        Returns:
            Feedback score (0.0-1.0)
        """
        # Try feedback_score
        feedback = properties.get("feedback_score")
        if feedback is not None:
            return min(1.0, max(0.0, float(feedback)))

        # Try usage_count (more usage = higher score)
        usage = properties.get("usage_count")
        if usage is not None:
            # Normalize: 0 usage = 0.5, 10+ usage = 1.0
            return min(1.0, 0.5 + float(usage) * 0.05)

        # Try validated (boolean)
        validated = properties.get("validated")
        if validated is True:
            return 0.8

        return 0.5  # Default
