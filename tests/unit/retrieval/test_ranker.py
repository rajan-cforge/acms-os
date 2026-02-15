"""Tests for Ranker - Stage 2 of retrieval pipeline (CRS scoring).

TDD: Write tests FIRST, then implement.

Run with: PYTHONPATH=. pytest tests/unit/retrieval/test_ranker.py -v
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from src.retrieval.retriever import RawResult
from src.retrieval.ranker import Ranker, ScoredResult


class TestScoredResult:
    """Test ScoredResult dataclass."""

    def test_scored_result_has_required_fields(self):
        """ScoredResult should have item, score, and breakdown."""
        raw = RawResult(
            uuid="test",
            content="test",
            distance=0.1,
            source="knowledge",
            properties={}
        )

        scored = ScoredResult(
            item=raw,
            score=0.85,
            breakdown={"similarity": 0.9, "recency": 0.8}
        )

        assert scored.item == raw
        assert scored.score == 0.85
        assert "similarity" in scored.breakdown


class TestRankerInit:
    """Test Ranker initialization."""

    def test_ranker_initializes_with_default_weights(self):
        """Ranker should initialize with default CRS weights."""
        ranker = Ranker()

        assert ranker.weights["similarity"] == 0.5
        assert ranker.weights["recency"] == 0.2
        assert ranker.weights["importance"] == 0.2
        assert ranker.weights["feedback"] == 0.1

    def test_ranker_accepts_custom_weights(self):
        """Ranker should accept custom weights."""
        custom_weights = {
            "similarity": 0.6,
            "recency": 0.2,
            "importance": 0.1,
            "feedback": 0.1
        }

        ranker = Ranker(weights=custom_weights)

        assert ranker.weights["similarity"] == 0.6


class TestRankerScoring:
    """Test CRS scoring algorithm."""

    @pytest.fixture
    def ranker(self):
        return Ranker()

    @pytest.fixture
    def now(self):
        return datetime.now(timezone.utc)

    def test_higher_similarity_ranks_higher(self, ranker, now):
        """More similar results should rank higher."""
        results = [
            RawResult(
                uuid="low-sim",
                content="Less similar",
                distance=0.5,  # 0.5 similarity
                source="knowledge",
                properties={"created_at": now.isoformat()}
            ),
            RawResult(
                uuid="high-sim",
                content="More similar",
                distance=0.1,  # 0.9 similarity
                source="knowledge",
                properties={"created_at": now.isoformat()}
            ),
        ]

        scored = ranker.score(results, now=now)

        # Higher similarity should be first
        assert scored[0].item.uuid == "high-sim"
        assert scored[0].score > scored[1].score

    def test_recent_content_boosted(self, ranker, now):
        """Recent content should score higher than old."""
        old_date = (now - timedelta(days=365)).isoformat()
        new_date = now.isoformat()

        results = [
            RawResult(
                uuid="old",
                content="Old content",
                distance=0.2,  # Same similarity
                source="knowledge",
                properties={"created_at": old_date}
            ),
            RawResult(
                uuid="new",
                content="New content",
                distance=0.2,  # Same similarity
                source="knowledge",
                properties={"created_at": new_date}
            ),
        ]

        scored = ranker.score(results, now=now)

        # New content should rank higher
        assert scored[0].item.uuid == "new"

    def test_importance_affects_score(self, ranker, now):
        """Higher importance should boost score."""
        results = [
            RawResult(
                uuid="low-importance",
                content="Low importance",
                distance=0.2,
                source="knowledge",
                properties={
                    "created_at": now.isoformat(),
                    "importance": 0.2
                }
            ),
            RawResult(
                uuid="high-importance",
                content="High importance",
                distance=0.2,  # Same similarity
                source="knowledge",
                properties={
                    "created_at": now.isoformat(),
                    "importance": 0.9
                }
            ),
        ]

        scored = ranker.score(results, now=now)

        # High importance should rank higher
        assert scored[0].item.uuid == "high-importance"

    def test_feedback_affects_score(self, ranker, now):
        """Positive feedback should boost score."""
        results = [
            RawResult(
                uuid="negative-feedback",
                content="Negative feedback",
                distance=0.2,
                source="knowledge",
                properties={
                    "created_at": now.isoformat(),
                    "feedback_score": 0.2
                }
            ),
            RawResult(
                uuid="positive-feedback",
                content="Positive feedback",
                distance=0.2,  # Same similarity
                source="knowledge",
                properties={
                    "created_at": now.isoformat(),
                    "feedback_score": 0.9
                }
            ),
        ]

        scored = ranker.score(results, now=now)

        # Positive feedback should rank higher
        assert scored[0].item.uuid == "positive-feedback"

    def test_score_calculation_correct(self, ranker, now):
        """Verify exact score calculation."""
        result = RawResult(
            uuid="test",
            content="test",
            distance=0.2,  # similarity = 0.8
            source="knowledge",
            properties={
                "created_at": now.isoformat(),
                "importance": 1.0,
                "feedback_score": 1.0
            }
        )

        scored = ranker.score([result], now=now)

        # Expected: 0.5*0.8 + 0.2*1.0 + 0.2*1.0 + 0.1*1.0 = 0.9
        # (recency ~1.0 for today)
        assert 0.85 <= scored[0].score <= 0.95

    def test_breakdown_included(self, ranker, now):
        """Score breakdown should be included."""
        result = RawResult(
            uuid="test",
            content="test",
            distance=0.2,
            source="knowledge",
            properties={"created_at": now.isoformat()}
        )

        scored = ranker.score([result], now=now)

        # Breakdown should have all components
        assert "similarity" in scored[0].breakdown
        assert "recency" in scored[0].breakdown
        assert "importance" in scored[0].breakdown
        assert "feedback" in scored[0].breakdown

    def test_results_sorted_by_score(self, ranker, now):
        """Results should be sorted by score (descending)."""
        results = [
            RawResult(uuid="low", content="a", distance=0.8, source="k", properties={"created_at": now.isoformat()}),
            RawResult(uuid="mid", content="b", distance=0.5, source="k", properties={"created_at": now.isoformat()}),
            RawResult(uuid="high", content="c", distance=0.1, source="k", properties={"created_at": now.isoformat()}),
        ]

        scored = ranker.score(results, now=now)

        # Should be sorted high to low
        assert scored[0].score >= scored[1].score >= scored[2].score

    def test_handles_missing_properties(self, ranker, now):
        """Should handle missing properties gracefully."""
        result = RawResult(
            uuid="test",
            content="test",
            distance=0.2,
            source="knowledge",
            properties={}  # Missing created_at, importance, feedback
        )

        scored = ranker.score([result], now=now)

        # Should not crash, should use defaults
        assert len(scored) == 1
        assert 0.0 <= scored[0].score <= 1.0
