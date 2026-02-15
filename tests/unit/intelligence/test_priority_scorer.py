"""
Unit tests for Priority Scoring (Week 6 Task 2)

Tests the priority scoring formula for detected patterns.
"""

import pytest
from src.intelligence.priority_scorer import (
    PriorityScorer,
    calculate_priority_score
)


class TestPriorityScoring:
    """Test priority scoring formula"""

    def test_high_priority_blocker(self):
        """High frequency + negative feedback should score high"""
        pattern = {
            "category": "PRODUCTIVITY_BLOCKER",
            "mentions": 12,  # High frequency
            "negative_feedback_rate": 0.75,  # 75% thumbs down
            "trend_30day": 0.40,  # 40% increase
            "estimated_impact": 8.0  # $18K/month impact (scale 0-10)
        }

        scorer = PriorityScorer()
        score = scorer.calculate_score(pattern)

        # Formula: (12/20 * 10 * 0.4) + (0.75 * 10 * 0.3) + (0.4 * 10 * 0.2) + (8 * 0.1)
        # = 2.4 + 2.25 + 0.8 + 0.8 = 6.25
        # With 1.2x category boost = 7.5
        assert 7.0 <= score <= 9.0

    def test_low_priority_pattern(self):
        """Low frequency + no negative feedback should score low"""
        pattern = {
            "category": "POSITIVE_TREND",
            "mentions": 2,
            "negative_feedback_rate": 0.0,
            "trend_30day": 0.0,
            "estimated_impact": 1.0
        }

        scorer = PriorityScorer()
        score = scorer.calculate_score(pattern)

        # Should be low (< 2)
        assert score < 2.0

    def test_knowledge_gap_priority(self):
        """Knowledge gaps with high regenerate should score moderately"""
        pattern = {
            "category": "KNOWLEDGE_GAP",
            "mentions": 20,  # Very frequent
            "negative_feedback_rate": 0.2,  # Some regenerate
            "trend_30day": 0.1,  # Stable
            "estimated_impact": 3.0  # Moderate impact
        }

        scorer = PriorityScorer()
        score = scorer.calculate_score(pattern)

        # Knowledge gap has no category boost (1.0x), but high frequency
        # Should be moderate-high (5-7)
        assert 5.0 <= score <= 7.0


class TestFrequencyNormalization:
    """Test frequency normalization (0-10 scale)"""

    def test_normalize_low_frequency(self):
        """Frequencies 0-2 should map to low scores (0-2)"""
        scorer = PriorityScorer()

        assert scorer._normalize_frequency(0) == 0
        assert scorer._normalize_frequency(1) < 1.0
        assert scorer._normalize_frequency(2) < 2.0

    def test_normalize_high_frequency(self):
        """Frequencies 20+ should map to max (10)"""
        scorer = PriorityScorer()

        assert scorer._normalize_frequency(20) == 10.0
        assert scorer._normalize_frequency(50) == 10.0

    def test_normalize_mid_frequency(self):
        """Mid-range frequencies should scale linearly"""
        scorer = PriorityScorer()

        # 10 mentions = 5/10 scale
        score = scorer._normalize_frequency(10)
        assert 4.5 <= score <= 5.5


class TestTrendScoring:
    """Test trend normalization"""

    def test_increasing_trend(self):
        """Increasing trends should score high"""
        scorer = PriorityScorer()

        # 40% increase
        score = scorer._normalize_trend(0.40)
        assert 8.0 <= score <= 10.0

    def test_decreasing_trend(self):
        """Decreasing trends should score low"""
        scorer = PriorityScorer()

        # 20% decrease
        score = scorer._normalize_trend(-0.20)
        assert 0.0 <= score <= 3.0

    def test_stable_trend(self):
        """Stable trends should score mid-range"""
        scorer = PriorityScorer()

        score = scorer._normalize_trend(0.0)
        assert 4.0 <= score <= 6.0


class TestCalculatePriorityFunction:
    """Test convenience function"""

    def test_calculate_with_dict(self):
        """Should accept pattern dict"""
        pattern = {
            "mentions": 10,
            "negative_feedback_rate": 0.5,
            "trend_30day": 0.2,
            "estimated_impact": 5.0
        }

        score = calculate_priority_score(pattern)
        assert isinstance(score, float)
        assert 0.0 <= score <= 10.0

    def test_calculate_missing_fields(self):
        """Should handle missing fields with defaults"""
        pattern = {
            "mentions": 5
            # Missing other fields
        }

        score = calculate_priority_score(pattern)
        assert isinstance(score, float)
        assert score > 0  # Should still calculate something


class TestCategoryWeighting:
    """Test category-specific weightings"""

    def test_blocker_gets_boost(self):
        """Productivity blockers should get priority boost"""
        base_pattern = {
            "mentions": 10,
            "negative_feedback_rate": 0.5,
            "trend_30day": 0.1,
            "estimated_impact": 5.0
        }

        scorer = PriorityScorer()

        blocker_pattern = {**base_pattern, "category": "PRODUCTIVITY_BLOCKER"}
        quality_pattern = {**base_pattern, "category": "QUALITY_ISSUE"}

        blocker_score = scorer.calculate_score(blocker_pattern)
        quality_score = scorer.calculate_score(quality_pattern)

        # Blockers should score higher
        assert blocker_score > quality_score

    def test_positive_trend_scores_lower(self):
        """Positive trends should score lower than problems"""
        base_pattern = {
            "mentions": 10,
            "negative_feedback_rate": 0.5,
            "trend_30day": 0.1,
            "estimated_impact": 5.0
        }

        scorer = PriorityScorer()

        blocker_pattern = {**base_pattern, "category": "PRODUCTIVITY_BLOCKER"}
        positive_pattern = {**base_pattern, "category": "POSITIVE_TREND"}

        blocker_score = scorer.calculate_score(blocker_pattern)
        positive_score = scorer.calculate_score(positive_pattern)

        # Problems should score higher than positives
        assert blocker_score > positive_score
