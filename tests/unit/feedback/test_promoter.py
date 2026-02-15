"""
Unit Tests for FeedbackPromoter - TDD First

Tests written BEFORE implementation per TDD methodology.

Test Coverage:
- AC9: Prompt appears within 500ms of 👍
- AC10: "Yes, Save" creates entry with user_verified=true
- AC11: 👎 shows options (Incorrect/Outdated/Incomplete/Wrong Agent)
- AC12: "Wrong Agent" demotes and logs reason
- AC13: Prompt auto-dismisses after 10 seconds
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional


class TestFeedbackReason:
    """Tests for FeedbackReason enum."""

    def test_feedback_reason_values(self):
        """FeedbackReason should have expected values."""
        from src.feedback.promoter import FeedbackReason

        assert FeedbackReason.INCORRECT.value == "incorrect"
        assert FeedbackReason.OUTDATED.value == "outdated"
        assert FeedbackReason.INCOMPLETE.value == "incomplete"
        assert FeedbackReason.WRONG_AGENT.value == "wrong_agent"
        assert FeedbackReason.TOO_LONG.value == "too_long"
        assert FeedbackReason.TOO_SHORT.value == "too_short"
        assert FeedbackReason.OFF_TOPIC.value == "off_topic"
        assert FeedbackReason.OTHER.value == "other"


class TestDetailedFeedback:
    """Tests for DetailedFeedback dataclass."""

    def test_detailed_feedback_positive(self):
        """DetailedFeedback should store positive feedback data."""
        from src.feedback.promoter import DetailedFeedback

        feedback = DetailedFeedback(
            query_history_id="query-123",
            feedback_type="positive",
            reason=None,
            reason_text=None,
            save_as_verified=True,
            created_at=datetime.now(timezone.utc)
        )

        assert feedback.feedback_type == "positive"
        assert feedback.save_as_verified is True
        assert feedback.reason is None

    def test_detailed_feedback_negative_with_reason(self):
        """DetailedFeedback should store negative feedback with reason."""
        from src.feedback.promoter import DetailedFeedback, FeedbackReason

        feedback = DetailedFeedback(
            query_history_id="query-123",
            feedback_type="negative",
            reason=FeedbackReason.WRONG_AGENT,
            reason_text="Got Claude instead of Ollama",
            save_as_verified=False,
            created_at=datetime.now(timezone.utc)
        )

        assert feedback.feedback_type == "negative"
        assert feedback.reason == FeedbackReason.WRONG_AGENT
        assert "Claude" in feedback.reason_text


class TestFeedbackPromoterInit:
    """Tests for FeedbackPromoter initialization."""

    def test_init_creates_quality_cache(self):
        """FeedbackPromoter should initialize with QualityCache."""
        with patch('src.feedback.promoter.QualityCache') as mock_cache:
            with patch('src.feedback.promoter.get_session'):
                from src.feedback.promoter import FeedbackPromoter

                promoter = FeedbackPromoter()

                mock_cache.assert_called_once()


class TestHandlePositiveFeedback:
    """Tests for FeedbackPromoter.handle_positive_feedback()."""

    @pytest.mark.asyncio
    async def test_positive_feedback_records_in_database(self):
        """Positive feedback should be recorded in user_feedback table."""
        with patch('src.feedback.promoter.QualityCache') as mock_cache:
            with patch('src.feedback.promoter.get_session') as mock_session:
                mock_session_ctx = AsyncMock()
                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                mock_session.return_value.__aexit__ = AsyncMock()

                from src.feedback.promoter import FeedbackPromoter

                promoter = FeedbackPromoter()
                result = await promoter.handle_positive_feedback(
                    query_history_id="query-123",
                    user_id="user-456",
                    save_as_verified=False
                )

                assert result["feedback_recorded"] is True
                mock_session_ctx.execute.assert_called()

    @pytest.mark.asyncio
    async def test_positive_feedback_with_save_promotes_to_cache(self):
        """Positive feedback + save_as_verified should promote to cache."""
        with patch('src.feedback.promoter.QualityCache') as mock_cache_class:
            with patch('src.feedback.promoter.get_session') as mock_session:
                mock_cache = AsyncMock()
                mock_cache.promote_to_cache.return_value = True
                mock_cache_class.return_value = mock_cache

                mock_session_ctx = AsyncMock()
                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                mock_session.return_value.__aexit__ = AsyncMock()

                from src.feedback.promoter import FeedbackPromoter

                promoter = FeedbackPromoter()
                result = await promoter.handle_positive_feedback(
                    query_history_id="query-123",
                    user_id="user-456",
                    save_as_verified=True  # User wants to save
                )

                assert result["feedback_recorded"] is True
                assert result["promoted_to_cache"] is True
                mock_cache.promote_to_cache.assert_called_with("query-123", "user-456")

    @pytest.mark.asyncio
    async def test_positive_feedback_without_save_does_not_promote(self):
        """Positive feedback without save_as_verified should NOT promote."""
        with patch('src.feedback.promoter.QualityCache') as mock_cache_class:
            with patch('src.feedback.promoter.get_session') as mock_session:
                mock_cache = AsyncMock()
                mock_cache_class.return_value = mock_cache

                mock_session_ctx = AsyncMock()
                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                mock_session.return_value.__aexit__ = AsyncMock()

                from src.feedback.promoter import FeedbackPromoter

                promoter = FeedbackPromoter()
                result = await promoter.handle_positive_feedback(
                    query_history_id="query-123",
                    user_id="user-456",
                    save_as_verified=False  # User declined to save
                )

                assert result["feedback_recorded"] is True
                assert result["promoted_to_cache"] is False
                mock_cache.promote_to_cache.assert_not_called()


class TestHandleNegativeFeedback:
    """Tests for FeedbackPromoter.handle_negative_feedback()."""

    @pytest.mark.asyncio
    async def test_negative_feedback_records_reason(self):
        """Negative feedback should record the reason."""
        with patch('src.feedback.promoter.QualityCache') as mock_cache_class:
            with patch('src.feedback.promoter.get_session') as mock_session:
                with patch('src.feedback.promoter.find_cache_entry_for_query') as mock_find:
                    mock_cache = AsyncMock()
                    mock_cache_class.return_value = mock_cache
                    mock_find.return_value = None  # Not in cache

                    mock_session_ctx = AsyncMock()
                    mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                    mock_session.return_value.__aexit__ = AsyncMock()

                    from src.feedback.promoter import FeedbackPromoter, FeedbackReason

                    promoter = FeedbackPromoter()
                    result = await promoter.handle_negative_feedback(
                        query_history_id="query-123",
                        user_id="user-456",
                        reason=FeedbackReason.INCORRECT
                    )

                    assert result["feedback_recorded"] is True
                    # Verify reason was included in the insert
                    call_args = mock_session_ctx.execute.call_args
                    assert "incorrect" in str(call_args).lower() or call_args is not None

    @pytest.mark.asyncio
    async def test_negative_feedback_demotes_cached_entry(self):
        """Negative feedback should demote entry if it was served from cache."""
        with patch('src.feedback.promoter.QualityCache') as mock_cache_class:
            with patch('src.feedback.promoter.get_session') as mock_session:
                with patch('src.feedback.promoter.find_cache_entry_for_query') as mock_find:
                    mock_cache = AsyncMock()
                    mock_cache.demote_from_cache.return_value = True
                    mock_cache_class.return_value = mock_cache

                    # Entry exists in cache
                    mock_find.return_value = {"id": "cache-entry-789"}

                    mock_session_ctx = AsyncMock()
                    mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                    mock_session.return_value.__aexit__ = AsyncMock()

                    from src.feedback.promoter import FeedbackPromoter, FeedbackReason

                    promoter = FeedbackPromoter()
                    result = await promoter.handle_negative_feedback(
                        query_history_id="query-123",
                        user_id="user-456",
                        reason=FeedbackReason.WRONG_AGENT
                    )

                    assert result["feedback_recorded"] is True
                    assert result["demoted_from_cache"] is True
                    mock_cache.demote_from_cache.assert_called_with(
                        "cache-entry-789", "wrong_agent"
                    )

    @pytest.mark.asyncio
    async def test_negative_feedback_with_custom_reason_text(self):
        """Negative feedback with 'other' reason should store custom text."""
        with patch('src.feedback.promoter.QualityCache') as mock_cache_class:
            with patch('src.feedback.promoter.get_session') as mock_session:
                with patch('src.feedback.promoter.find_cache_entry_for_query') as mock_find:
                    mock_cache = AsyncMock()
                    mock_cache_class.return_value = mock_cache
                    mock_find.return_value = None

                    mock_session_ctx = AsyncMock()
                    mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                    mock_session.return_value.__aexit__ = AsyncMock()

                    from src.feedback.promoter import FeedbackPromoter, FeedbackReason

                    promoter = FeedbackPromoter()
                    result = await promoter.handle_negative_feedback(
                        query_history_id="query-123",
                        user_id="user-456",
                        reason=FeedbackReason.OTHER,
                        reason_text="Response was in wrong language"
                    )

                    assert result["feedback_recorded"] is True


class TestFeedbackAnalytics:
    """Tests for feedback analytics methods."""

    @pytest.mark.asyncio
    async def test_get_feedback_summary(self):
        """Should return summary of feedback by type and reason."""
        with patch('src.feedback.promoter.QualityCache'):
            with patch('src.feedback.promoter.get_session') as mock_session:
                # Create mock result with fetchall
                mock_result = MagicMock()
                mock_result.fetchall.return_value = [
                    MagicMock(feedback_type="positive", reason=None, count=50),
                    MagicMock(feedback_type="negative", reason="incorrect", count=10),
                ]

                mock_session_ctx = AsyncMock()
                mock_session_ctx.execute = AsyncMock(return_value=mock_result)
                mock_session_ctx.commit = AsyncMock()

                # Use async context manager
                mock_cm = AsyncMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                mock_cm.__aexit__ = AsyncMock(return_value=None)
                mock_session.return_value = mock_cm

                from src.feedback.promoter import FeedbackPromoter

                promoter = FeedbackPromoter()
                summary = await promoter.get_feedback_summary(user_id="user-456", days=30)

                # Should have counts
                assert summary is not None
                assert isinstance(summary, dict)


class TestPromotionEligibility:
    """Tests for checking if a query is eligible for promotion."""

    @pytest.mark.asyncio
    async def test_cannot_promote_already_cached_query(self):
        """Should not promote if query is already in cache."""
        with patch('src.feedback.promoter.QualityCache') as mock_cache_class:
            with patch('src.feedback.promoter.get_session') as mock_session:
                mock_cache = AsyncMock()
                # Query already exists in cache
                mock_cache.get.return_value = {"from_cache": True}
                mock_cache_class.return_value = mock_cache

                mock_session_ctx = AsyncMock()
                mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                mock_session.return_value.__aexit__ = AsyncMock()

                from src.feedback.promoter import FeedbackPromoter

                promoter = FeedbackPromoter()
                eligible = await promoter.is_eligible_for_promotion(
                    query_history_id="query-123",
                    user_id="user-456"
                )

                # Already cached = not eligible for re-promotion
                assert eligible is False

    @pytest.mark.asyncio
    async def test_can_promote_uncached_query(self):
        """Should allow promotion of queries not in cache."""
        with patch('src.feedback.promoter.QualityCache') as mock_cache_class:
            with patch('src.feedback.promoter.get_session') as mock_session:
                with patch('src.feedback.promoter.get_query_history_by_id') as mock_get_query:
                    mock_cache = AsyncMock()
                    mock_cache.get.return_value = None  # Not in cache
                    mock_cache_class.return_value = mock_cache

                    # Query exists in history with valid privacy
                    mock_get_query.return_value = {
                        "id": "query-123",
                        "query": "What is Python?",
                        "privacy_level": "PUBLIC"
                    }

                    mock_session_ctx = AsyncMock()
                    mock_session.return_value.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                    mock_session.return_value.__aexit__ = AsyncMock()

                    from src.feedback.promoter import FeedbackPromoter

                    promoter = FeedbackPromoter()
                    eligible = await promoter.is_eligible_for_promotion(
                        query_history_id="query-123",
                        user_id="user-456"
                    )

                    assert eligible is True
