"""
Priority Scoring for Enterprise Intelligence (Week 6 Task 2)

Calculates priority scores for detected patterns using weighted formula:
Priority = (Frequency × 0.4) + (Negative_Feedback × 0.3) + (Trend × 0.2) + (Impact × 0.1)

Where:
- Frequency: Number of mentions (normalized 0-10)
- Negative_Feedback: % thumbs_down (0-10)
- Trend: 30-day change % (0-10)
- Impact: Estimated $ impact or user count (0-10)
"""

from typing import Dict, Any


class PriorityScorer:
    """
    Calculate priority scores for organizational intelligence patterns

    Uses weighted formula to rank patterns by importance for leadership attention.
    """

    # Weight distribution
    FREQUENCY_WEIGHT = 0.4  # How often is this mentioned?
    NEGATIVE_FEEDBACK_WEIGHT = 0.3  # How much negative feedback?
    TREND_WEIGHT = 0.2  # Is it getting worse?
    IMPACT_WEIGHT = 0.1  # What's the business impact?

    # Category boosts (some categories are inherently more important)
    CATEGORY_BOOST = {
        "PRODUCTIVITY_BLOCKER": 1.2,  # 20% boost
        "QUALITY_ISSUE": 1.15,  # 15% boost
        "KNOWLEDGE_GAP": 1.0,  # No boost
        "INNOVATION_IDEA": 0.9,  # Slight reduction (less urgent)
        "POSITIVE_TREND": 0.7,  # Significant reduction (celebrate, don't fix)
    }

    def __init__(self):
        """Initialize priority scorer"""
        pass

    def calculate_score(self, pattern: Dict[str, Any]) -> float:
        """
        Calculate priority score for a pattern

        Args:
            pattern: Dict with mentions, negative_feedback_rate, trend_30day, estimated_impact

        Returns:
            Priority score (0-10 scale, higher = more important)

        Example:
            >>> pattern = {
            ...     "mentions": 12,
            ...     "negative_feedback_rate": 0.75,
            ...     "trend_30day": 0.40,
            ...     "estimated_impact": 8.0,
            ...     "category": "PRODUCTIVITY_BLOCKER"
            ... }
            >>> scorer = PriorityScorer()
            >>> score = scorer.calculate_score(pattern)
            >>> 6.0 <= score <= 7.5  # High priority
            True
        """
        # Extract metrics (with defaults)
        mentions = pattern.get('mentions', 0)
        negative_feedback_rate = pattern.get('negative_feedback_rate', 0.0)
        trend_30day = pattern.get('trend_30day', 0.0)
        estimated_impact = pattern.get('estimated_impact', 0.0)
        category = pattern.get('category', 'KNOWLEDGE_GAP')

        # Normalize metrics to 0-10 scale
        frequency_score = self._normalize_frequency(mentions)
        feedback_score = negative_feedback_rate * 10  # Already 0-1, just scale
        trend_score = self._normalize_trend(trend_30day)
        impact_score = estimated_impact  # Already 0-10 scale

        # Calculate weighted score
        base_score = (
            (frequency_score * self.FREQUENCY_WEIGHT) +
            (feedback_score * self.NEGATIVE_FEEDBACK_WEIGHT) +
            (trend_score * self.TREND_WEIGHT) +
            (impact_score * self.IMPACT_WEIGHT)
        )

        # Apply category boost
        category_boost = self.CATEGORY_BOOST.get(category, 1.0)
        final_score = base_score * category_boost

        # Clamp to 0-10 range
        return min(10.0, max(0.0, final_score))

    def _normalize_frequency(self, mentions: int) -> float:
        """
        Normalize mention frequency to 0-10 scale

        Args:
            mentions: Raw count of mentions

        Returns:
            Normalized score (0-10)

        Scale:
            0 mentions = 0
            10 mentions = 5
            20+ mentions = 10
        """
        if mentions == 0:
            return 0.0

        # Linear scaling: 20 mentions = 10 score
        normalized = (mentions / 20.0) * 10.0
        return min(10.0, normalized)

    def _normalize_trend(self, trend_30day: float) -> float:
        """
        Normalize 30-day trend to 0-10 scale

        Args:
            trend_30day: Change rate (-1.0 to +1.0 or beyond)
                        0.0 = no change
                        +0.5 = 50% increase
                        -0.5 = 50% decrease

        Returns:
            Normalized score (0-10)

        Scale:
            -50% or worse = 0 (getting better, not urgent)
            0% = 5 (stable)
            +50% or more = 10 (getting much worse, very urgent)
        """
        # Center around 0, scale from -0.5 to +0.5
        # -0.5 → 0
        # 0.0 → 5
        # +0.5 → 10

        # Clamp input to reasonable range
        clamped_trend = max(-0.5, min(0.5, trend_30day))

        # Scale to 0-10
        normalized = ((clamped_trend + 0.5) / 1.0) * 10.0
        return normalized


def calculate_priority_score(pattern: Dict[str, Any]) -> float:
    """
    Convenience function to calculate priority score

    Args:
        pattern: Pattern dict with metrics

    Returns:
        Priority score (0-10)

    Example:
        >>> pattern = {"mentions": 10, "negative_feedback_rate": 0.5}
        >>> score = calculate_priority_score(pattern)
        >>> 0.0 <= score <= 10.0
        True
    """
    scorer = PriorityScorer()
    return scorer.calculate_score(pattern)
