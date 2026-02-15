"""
Unit tests for Pattern Detection (Week 6 Task 3)

Tests TF-IDF vectorization, DBSCAN clustering, and pattern analysis.
"""

import pytest
from src.intelligence.pattern_detector import PatternDetector
from src.intelligence.categorizer import MemoryCategory


class TestPatternDetection:
    """Test pattern detection logic"""

    def test_vectorize_texts(self):
        """Should vectorize texts using TF-IDF"""
        detector = PatternDetector(None)  # No DB needed for this test

        texts = [
            "CI deployment takes 3 hours",
            "Deployment is very slow",
            "How do I speed up deployment?"
        ]

        vectors, vectorizer = detector._vectorize_texts(texts)

        # Should return array of correct shape
        assert vectors.shape[0] == 3
        assert vectors.shape[1] > 0  # Has features

        # Vectors should have non-zero values
        assert vectors.sum() > 0

    def test_cluster_memories(self):
        """Should cluster similar texts together"""
        detector = PatternDetector(None)

        texts = [
            "CI deployment takes 3 hours",
            "Deployment is very slow",
            "Where are the API docs?",
            "How do I find documentation?",
            "Bug in user login",
            "Login feature is broken"
        ]

        vectors, _ = detector._vectorize_texts(texts)
        clusters = detector._cluster_memories(vectors, min_samples=2)

        # Should have multiple clusters
        unique_clusters = set(clusters)
        assert len(unique_clusters) > 1

        # Similar texts should be in same cluster
        # (deployment-related should cluster together)
        assert clusters[0] == clusters[1] or clusters[0] == -1 or clusters[1] == -1

    def test_calculate_negative_feedback(self):
        """Should calculate negative feedback rate"""
        detector = PatternDetector(None)

        memories = [
            {'feedback_summary': {'thumbs_down': 1}},
            {'feedback_summary': {'thumbs_down': 0}},
            {'feedback_summary': {'regenerate': 1}},
            {'feedback_summary': {}}
        ]

        rate = detector._calculate_negative_feedback(memories)

        # 2 out of 4 have negative feedback = 0.5
        assert rate == 0.5

    def test_calculate_negative_feedback_empty(self):
        """Should handle empty memories"""
        detector = PatternDetector(None)

        rate = detector._calculate_negative_feedback([])

        assert rate == 0.0

    def test_detect_category_blocker(self):
        """Should detect productivity blockers"""
        detector = PatternDetector(None)

        memories = [
            {'content': 'The CI process is very slow and takes too long'},
            {'content': 'Waiting for deployment to finish'}
        ]

        category = detector._detect_category(memories, negative_feedback_rate=0.8)

        assert category == MemoryCategory.PRODUCTIVITY_BLOCKER

    def test_detect_category_quality(self):
        """Should detect quality issues"""
        detector = PatternDetector(None)

        memories = [
            {'content': 'There is a bug in the login feature'},
            {'content': 'Error when trying to submit form'}
        ]

        category = detector._detect_category(memories, negative_feedback_rate=0.5)

        assert category == MemoryCategory.QUALITY_ISSUE

    def test_detect_category_knowledge_gap(self):
        """Should detect knowledge gaps"""
        detector = PatternDetector(None)

        memories = [
            {'content': 'Where can I find the API documentation?'},
            {'content': 'How do I configure the database?'}
        ]

        category = detector._detect_category(memories, negative_feedback_rate=0.2)

        assert category == MemoryCategory.KNOWLEDGE_GAP

    def test_calculate_trend_increasing(self):
        """Should detect increasing trend"""
        from datetime import datetime, timedelta
        detector = PatternDetector(None)

        # More recent memories (second half larger)
        base_time = datetime.now() - timedelta(days=30)

        memories = [
            {'created_at': base_time + timedelta(days=i)}
            for i in range(5)
        ] + [
            {'created_at': base_time + timedelta(days=15 + i)}
            for i in range(10)  # More in second half
        ]

        trend = detector._calculate_trend(memories, lookback_days=30)

        # Should be positive (increasing)
        assert trend > 0

    def test_estimate_impact(self):
        """Should estimate business impact"""
        detector = PatternDetector(None)

        impact = detector._estimate_impact(
            category=MemoryCategory.PRODUCTIVITY_BLOCKER,
            mentions=10,
            negative_feedback_rate=0.8
        )

        # Should be high impact (blocker + high frequency + negative feedback)
        assert impact > 5.0
        assert impact <= 10.0

    def test_estimate_impact_low(self):
        """Should estimate low impact for positive trends"""
        detector = PatternDetector(None)

        impact = detector._estimate_impact(
            category=MemoryCategory.POSITIVE_TREND,
            mentions=3,
            negative_feedback_rate=0.1
        )

        # Should be low impact
        assert impact < 3.0


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_texts(self):
        """Should handle empty text list"""
        detector = PatternDetector(None)

        with pytest.raises(ValueError):
            detector._vectorize_texts([])

    def test_single_text(self):
        """Should handle single text"""
        detector = PatternDetector(None)

        vectors, _ = detector._vectorize_texts(["single text"])

        assert vectors.shape[0] == 1
