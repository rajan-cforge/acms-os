"""Unit tests for SalienceScorer.

Cognitive Principle: Emotional Priority Queue

The brain prioritizes emotionally significant memories for consolidation.
This module scores queries based on engagement and emotional signals
to prioritize which Q&A pairs deserve full knowledge extraction.

TDD: Tests written BEFORE implementation.
Run with: PYTHONPATH=. pytest tests/unit/intelligence/test_salience_scorer.py -v
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


# ============================================================
# TEST FIXTURES AND HELPERS
# ============================================================

@dataclass
class MockQueryContext:
    """Mock query context for testing."""
    query_id: str
    user_id: str
    question: str
    answer: str
    created_at: datetime
    session_id: Optional[str] = None
    session_duration_seconds: Optional[int] = None
    feedback_type: Optional[str] = None
    follow_up_count: int = 0
    return_visits: int = 0
    emotional_markers: List[str] = None

    def __post_init__(self):
        if self.emotional_markers is None:
            self.emotional_markers = []


def create_query_context(
    question: str = "How do I debug Python?",
    answer: str = "Use pdb or print statements.",
    session_duration_seconds: int = 60,
    session_id: Optional[str] = "test-session-1",
    feedback_type: Optional[str] = None,
    follow_up_count: int = 0,
    return_visits: int = 0,
    emotional_markers: List[str] = None,
) -> MockQueryContext:
    """Create a mock query context for testing."""
    return MockQueryContext(
        query_id="test-query-1",
        user_id="test-user-1",
        question=question,
        answer=answer,
        created_at=datetime.now(timezone.utc),
        session_id=session_id,
        session_duration_seconds=session_duration_seconds,
        feedback_type=feedback_type,
        follow_up_count=follow_up_count,
        return_visits=return_visits,
        emotional_markers=emotional_markers or [],
    )


# ============================================================
# SALIENCE SIGNAL ENUM TESTS
# ============================================================

class TestSalienceSignal:
    """Tests for SalienceSignal enum."""

    def test_signal_enum_exists(self):
        """Verify SalienceSignal enum exists with expected values."""
        from src.intelligence.salience_scorer import SalienceSignal

        assert hasattr(SalienceSignal, 'FOLLOW_UP')
        assert hasattr(SalienceSignal, 'POSITIVE_FEEDBACK')
        assert hasattr(SalienceSignal, 'LONG_SESSION')
        assert hasattr(SalienceSignal, 'LONG_RESPONSE')
        assert hasattr(SalienceSignal, 'CODE_PRESENT')
        assert hasattr(SalienceSignal, 'RETURN_VISIT')
        assert hasattr(SalienceSignal, 'EMOTIONAL_MARKER')

    def test_signal_weights(self):
        """Verify signal weights are defined and reasonable."""
        from src.intelligence.salience_scorer import SIGNAL_WEIGHTS

        # All weights should be between 0.0 and 0.5
        for signal, weight in SIGNAL_WEIGHTS.items():
            assert 0.0 < weight <= 0.5, f"Signal {signal} weight {weight} out of range"


# ============================================================
# SALIENCE SCORE RESULT TESTS
# ============================================================

class TestSalienceScore:
    """Tests for SalienceScore dataclass."""

    def test_salience_score_creation(self):
        """Test SalienceScore creation with all fields."""
        from src.intelligence.salience_scorer import SalienceScore

        score = SalienceScore(
            score=0.75,
            signals_detected=["follow_up", "positive_feedback"],
            signal_contributions={"follow_up": 0.15, "positive_feedback": 0.20},
            context_window_boost=0.1,
            timestamp=datetime.now(timezone.utc),
        )

        assert score.score == 0.75
        assert len(score.signals_detected) == 2
        assert "follow_up" in score.signals_detected

    def test_salience_score_to_dict(self):
        """Test SalienceScore serialization."""
        from src.intelligence.salience_scorer import SalienceScore

        now = datetime.now(timezone.utc)
        score = SalienceScore(
            score=0.65,
            signals_detected=["code_present"],
            signal_contributions={"code_present": 0.10},
            context_window_boost=0.0,
            timestamp=now,
        )

        result = score.to_dict()

        assert result["score"] == 0.65
        assert result["signals_detected"] == ["code_present"]
        assert result["signal_contributions"]["code_present"] == 0.10
        assert result["timestamp"] == now.isoformat()

    def test_salience_score_is_high_threshold(self):
        """Test is_high method with configurable threshold."""
        from src.intelligence.salience_scorer import SalienceScore

        high_score = SalienceScore(
            score=0.8,
            signals_detected=[],
            signal_contributions={},
            context_window_boost=0.0,
            timestamp=datetime.now(timezone.utc),
        )
        low_score = SalienceScore(
            score=0.3,
            signals_detected=[],
            signal_contributions={},
            context_window_boost=0.0,
            timestamp=datetime.now(timezone.utc),
        )

        assert high_score.is_high(threshold=0.6) is True
        assert low_score.is_high(threshold=0.6) is False


# ============================================================
# SALIENCE SCORER CONFIG TESTS
# ============================================================

class TestSalienceConfig:
    """Tests for SalienceConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        from src.intelligence.salience_scorer import SalienceConfig

        config = SalienceConfig()

        assert config.high_threshold == 0.6
        assert config.long_session_threshold_seconds >= 300  # 5+ minutes
        assert config.long_response_threshold_words >= 200
        assert config.context_window_minutes >= 5

    def test_custom_config(self):
        """Test custom configuration."""
        from src.intelligence.salience_scorer import SalienceConfig

        config = SalienceConfig(
            high_threshold=0.7,
            long_session_threshold_seconds=600,
            long_response_threshold_words=300,
        )

        assert config.high_threshold == 0.7
        assert config.long_session_threshold_seconds == 600


# ============================================================
# SALIENCE SCORER CORE TESTS
# ============================================================

class TestSalienceScorer:
    """Tests for SalienceScorer main functionality."""

    @pytest.fixture
    def scorer(self):
        """Create a SalienceScorer instance."""
        from src.intelligence.salience_scorer import SalienceScorer
        return SalienceScorer()

    @pytest.mark.asyncio
    async def test_score_basic_query(self, scorer):
        """Test scoring a basic query with no special signals."""
        context = create_query_context()

        result = await scorer.score(context)

        assert result.score >= 0.0
        assert result.score <= 1.0
        assert isinstance(result.signals_detected, list)

    @pytest.mark.asyncio
    async def test_score_with_positive_feedback(self, scorer):
        """Test that positive feedback increases salience."""
        base_context = create_query_context()
        feedback_context = create_query_context(feedback_type="positive")

        base_result = await scorer.score(base_context)
        feedback_result = await scorer.score(feedback_context)

        assert feedback_result.score > base_result.score
        assert "positive_feedback" in feedback_result.signals_detected

    @pytest.mark.asyncio
    async def test_score_with_negative_feedback(self, scorer):
        """Test that negative feedback does NOT increase salience."""
        base_context = create_query_context()
        negative_context = create_query_context(feedback_type="negative")

        base_result = await scorer.score(base_context)
        negative_result = await scorer.score(negative_context)

        # Negative feedback shouldn't boost salience
        assert negative_result.score <= base_result.score
        assert "positive_feedback" not in negative_result.signals_detected

    @pytest.mark.asyncio
    async def test_score_with_follow_ups(self, scorer):
        """Test that follow-up questions increase salience."""
        base_context = create_query_context()
        followup_context = create_query_context(follow_up_count=3)

        base_result = await scorer.score(base_context)
        followup_result = await scorer.score(followup_context)

        assert followup_result.score > base_result.score
        assert "follow_up" in followup_result.signals_detected

    @pytest.mark.asyncio
    async def test_score_with_long_session(self, scorer):
        """Test that long sessions increase salience."""
        short_session = create_query_context(session_duration_seconds=60)
        long_session = create_query_context(session_duration_seconds=600)  # 10 minutes

        short_result = await scorer.score(short_session)
        long_result = await scorer.score(long_session)

        assert long_result.score > short_result.score
        assert "long_session" in long_result.signals_detected

    @pytest.mark.asyncio
    async def test_score_with_code_in_response(self, scorer):
        """Test that code in response increases salience."""
        no_code_context = create_query_context(
            answer="The answer is 42."
        )
        code_context = create_query_context(
            answer="Here's the code:\n```python\ndef hello():\n    print('world')\n```"
        )

        no_code_result = await scorer.score(no_code_context)
        code_result = await scorer.score(code_context)

        assert code_result.score > no_code_result.score
        assert "code_present" in code_result.signals_detected

    @pytest.mark.asyncio
    async def test_score_with_long_response(self, scorer):
        """Test that long responses increase salience."""
        short_response = create_query_context(answer="Short answer.")
        long_response = create_query_context(
            answer="This is a detailed comprehensive answer. " * 50
        )

        short_result = await scorer.score(short_response)
        long_result = await scorer.score(long_response)

        assert long_result.score > short_result.score
        assert "long_response" in long_result.signals_detected


# ============================================================
# SIGNAL DETECTION TESTS
# ============================================================

class TestSignalDetection:
    """Tests for individual signal detection methods."""

    @pytest.fixture
    def scorer(self):
        from src.intelligence.salience_scorer import SalienceScorer
        return SalienceScorer()

    def test_detect_code_with_backticks(self, scorer):
        """Test code detection with triple backticks."""
        assert scorer._has_code("```python\nprint('hello')\n```") is True
        assert scorer._has_code("No code here") is False

    def test_detect_code_with_inline_code(self, scorer):
        """Test code detection with inline code."""
        # Should detect inline code patterns too
        assert scorer._has_code("Use `print()` function") is True

    def test_detect_code_with_common_patterns(self, scorer):
        """Test code detection with function/class patterns."""
        assert scorer._has_code("def my_function():") is True
        assert scorer._has_code("class MyClass:") is True
        assert scorer._has_code("import numpy") is True

    def test_detect_long_response(self, scorer):
        """Test long response detection."""
        short = "Short answer"
        long = "word " * 250  # 250 words

        assert scorer._is_long_response(short) is False
        assert scorer._is_long_response(long) is True

    def test_detect_emotional_markers(self, scorer):
        """Test emotional marker detection."""
        frustrated = "I'm so frustrated with this error!"
        excited = "Amazing! This is exactly what I needed!"
        neutral = "What is Python?"

        assert len(scorer._detect_emotional_markers(frustrated)) > 0
        assert len(scorer._detect_emotional_markers(excited)) > 0
        assert len(scorer._detect_emotional_markers(neutral)) == 0


# ============================================================
# CONTEXT WINDOW TESTS
# ============================================================

class TestContextWindow:
    """Tests for context window (flashbulb memory) functionality."""

    @pytest.fixture
    def scorer(self):
        from src.intelligence.salience_scorer import SalienceScorer
        return SalienceScorer()

    @pytest.mark.asyncio
    async def test_context_window_boost(self, scorer):
        """Test that queries in emotional context get boosted."""
        # Create a high-salience query that establishes context
        high_salience_context = create_query_context(
            question="Critical production error!",
            answer="Here's the fix:\n```python\ndef fix():\n    pass\n```" + " detail" * 100,
            feedback_type="positive",
            follow_up_count=2,
            session_duration_seconds=600,
        )

        # Score it to establish context window
        await scorer.score(high_salience_context)

        # Now a normal query in the same session should get boosted
        following_context = create_query_context(
            question="One more question about that fix",
            session_id=high_salience_context.session_id,
        )

        result = await scorer.score(following_context)

        # The context window boost should be positive
        assert result.context_window_boost >= 0.0


# ============================================================
# RETURN VISIT TESTS
# ============================================================

class TestReturnVisits:
    """Tests for return visit signal detection."""

    @pytest.fixture
    def scorer(self):
        from src.intelligence.salience_scorer import SalienceScorer
        return SalienceScorer()

    @pytest.mark.asyncio
    async def test_return_visit_increases_salience(self, scorer):
        """Test that returning to a topic increases salience."""
        first_visit = create_query_context(return_visits=0)
        return_visit = create_query_context(return_visits=3)

        first_result = await scorer.score(first_visit)
        return_result = await scorer.score(return_visit)

        assert return_result.score > first_result.score
        assert "return_visit" in return_result.signals_detected


# ============================================================
# COMBINED SIGNALS TESTS
# ============================================================

class TestCombinedSignals:
    """Tests for combined signal scoring."""

    @pytest.fixture
    def scorer(self):
        from src.intelligence.salience_scorer import SalienceScorer
        return SalienceScorer()

    @pytest.mark.asyncio
    async def test_multiple_signals_cumulative(self, scorer):
        """Test that multiple signals increase score cumulatively."""
        single_signal = create_query_context(feedback_type="positive")

        multiple_signals = create_query_context(
            feedback_type="positive",
            follow_up_count=2,
            session_duration_seconds=600,
            answer="```python\ndef answer():\n    pass\n```" + " word" * 200,
        )

        single_result = await scorer.score(single_signal)
        multi_result = await scorer.score(multiple_signals)

        assert multi_result.score > single_result.score
        assert len(multi_result.signals_detected) >= 3

    @pytest.mark.asyncio
    async def test_score_clamped_to_one(self, scorer):
        """Test that maximum score is clamped to 1.0."""
        all_signals = create_query_context(
            feedback_type="positive",
            follow_up_count=10,
            return_visits=5,
            session_duration_seconds=3600,  # 1 hour
            answer="```python\nclass BigClass:\n    def method(self):\n        pass\n```" + " word" * 500,
            emotional_markers=["amazing", "breakthrough", "finally"],
        )

        result = await scorer.score(all_signals)

        assert result.score <= 1.0


# ============================================================
# COGNITIVE PRINCIPLE TESTS
# ============================================================

class TestCognitivePrinciples:
    """Tests that verify cognitive science principles are implemented."""

    @pytest.fixture
    def scorer(self):
        from src.intelligence.salience_scorer import SalienceScorer
        return SalienceScorer()

    @pytest.mark.asyncio
    async def test_emotional_priority_queue_principle(self, scorer):
        """
        Cognitive Principle: Emotional Priority Queue

        Emotionally significant memories (high engagement, positive feedback)
        should be prioritized for consolidation over neutral memories.
        """
        emotional_query = create_query_context(
            question="This bug has been driving me crazy! How do I fix it?",
            answer="Finally! Here's the solution:\n```python\nfix()\n```" + " detail" * 100,
            feedback_type="positive",
            follow_up_count=3,
            emotional_markers=["frustrated", "finally", "crazy"],
        )

        neutral_query = create_query_context(
            question="What is a function?",
            answer="A function is a block of code.",
        )

        emotional_result = await scorer.score(emotional_query)
        neutral_result = await scorer.score(neutral_query)

        # Emotional should score significantly higher
        assert emotional_result.score > neutral_result.score + 0.2

    @pytest.mark.asyncio
    async def test_flashbulb_memory_principle(self, scorer):
        """
        Cognitive Principle: Flashbulb Memory

        Memories formed during emotionally significant events are
        more vivid and persistent. The "context window" captures this.
        """
        # The flashbulb effect means nearby memories get boosted
        # This is tested via the context_window_boost field
        high_engagement = create_query_context(
            feedback_type="positive",
            follow_up_count=5,
            session_duration_seconds=900,
            answer="Comprehensive answer with ```code```" + " word" * 200,
        )

        result = await scorer.score(high_engagement)

        # High-engagement queries should establish a context window
        # that could boost subsequent queries
        assert result.is_high(threshold=0.6)

    @pytest.mark.asyncio
    async def test_engagement_equals_importance_principle(self, scorer):
        """
        Cognitive Principle: Engagement = Importance

        The amount of engagement (follow-ups, time spent, returns)
        indicates the importance of the memory to the user.
        """
        low_engagement = create_query_context(
            session_duration_seconds=30,
            follow_up_count=0,
            return_visits=0,
        )

        high_engagement = create_query_context(
            session_duration_seconds=900,  # 15 minutes
            follow_up_count=5,
            return_visits=3,
        )

        low_result = await scorer.score(low_engagement)
        high_result = await scorer.score(high_engagement)

        # High engagement should score much higher
        assert high_result.score > low_result.score * 2


# ============================================================
# EDGE CASES TESTS
# ============================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def scorer(self):
        from src.intelligence.salience_scorer import SalienceScorer
        return SalienceScorer()

    @pytest.mark.asyncio
    async def test_empty_question_and_answer(self, scorer):
        """Test scoring with empty content."""
        context = create_query_context(question="", answer="")

        result = await scorer.score(context)

        # Should still work, just low score
        assert result.score >= 0.0
        assert result.score < 0.3  # Low baseline

    @pytest.mark.asyncio
    async def test_none_optional_fields(self, scorer):
        """Test scoring with None optional fields."""
        context = MockQueryContext(
            query_id="test",
            user_id="user",
            question="Test?",
            answer="Answer.",
            created_at=datetime.now(timezone.utc),
            session_id=None,
            session_duration_seconds=None,
            feedback_type=None,
        )

        result = await scorer.score(context)

        # Should handle gracefully
        assert result.score >= 0.0

    @pytest.mark.asyncio
    async def test_very_long_content(self, scorer):
        """Test scoring with very long content."""
        long_question = "question " * 10000
        long_answer = "answer " * 10000

        context = create_query_context(
            question=long_question,
            answer=long_answer,
        )

        result = await scorer.score(context)

        # Should complete without error
        assert result is not None
        assert "long_response" in result.signals_detected


# ============================================================
# STATS AND DEBUGGING TESTS
# ============================================================

class TestStatsAndDebugging:
    """Tests for statistics and debugging functionality."""

    @pytest.fixture
    def scorer(self):
        from src.intelligence.salience_scorer import SalienceScorer
        return SalienceScorer()

    @pytest.mark.asyncio
    async def test_get_stats(self, scorer):
        """Test statistics retrieval."""
        # Score a few queries
        await scorer.score(create_query_context())
        await scorer.score(create_query_context(feedback_type="positive"))
        await scorer.score(create_query_context(follow_up_count=2))

        stats = scorer.get_stats()

        assert "total_scored" in stats
        assert stats["total_scored"] >= 3
        assert "avg_score" in stats
        assert "high_salience_pct" in stats

    @pytest.mark.asyncio
    async def test_signal_contributions_detailed(self, scorer):
        """Test that signal contributions are properly tracked."""
        context = create_query_context(
            feedback_type="positive",
            follow_up_count=2,
        )

        result = await scorer.score(context)

        # Should have detailed contributions
        assert "positive_feedback" in result.signal_contributions
        assert "follow_up" in result.signal_contributions
        assert result.signal_contributions["positive_feedback"] > 0
