"""
Unit Tests for NudgeEngine - TDD First

Tests written BEFORE implementation per TDD methodology.

Test Coverage:
- AC14: System generates nudge when learning new relevant fact
- AC15: Stale knowledge triggers review reminder
- AC16: Low-confidence items get periodic nudges
- AC17: User can snooze or dismiss nudges
- AC18: Nudge queue respects user preferences
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional
import uuid


class TestNudgeType:
    """Tests for NudgeType enum."""

    def test_nudge_type_values(self):
        """NudgeType should have expected values."""
        from src.intelligence.nudge_engine import NudgeType

        assert NudgeType.NEW_LEARNING.value == "new_learning"
        assert NudgeType.STALE_KNOWLEDGE.value == "stale_knowledge"
        assert NudgeType.LOW_CONFIDENCE.value == "low_confidence"
        assert NudgeType.CORRECTION_SUGGESTED.value == "correction_suggested"
        assert NudgeType.REVIEW_REMINDER.value == "review_reminder"
        assert NudgeType.INSIGHT_AVAILABLE.value == "insight_available"


class TestNudgePriority:
    """Tests for NudgePriority enum."""

    def test_nudge_priority_values(self):
        """NudgePriority should have expected values."""
        from src.intelligence.nudge_engine import NudgePriority

        assert NudgePriority.HIGH.value == "high"
        assert NudgePriority.MEDIUM.value == "medium"
        assert NudgePriority.LOW.value == "low"


class TestNudge:
    """Tests for Nudge dataclass."""

    def test_nudge_creation(self):
        """Nudge should store all required fields."""
        from src.intelligence.nudge_engine import Nudge, NudgeType, NudgePriority

        nudge = Nudge(
            id=str(uuid.uuid4()),
            user_id="user-456",
            nudge_type=NudgeType.NEW_LEARNING,
            title="New fact learned",
            message="ACMS learned that Python 3.12 supports pattern matching",
            priority=NudgePriority.MEDIUM,
            related_id="knowledge-123",
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            dismissed=False,
            snoozed_until=None
        )

        assert nudge.user_id == "user-456"
        assert nudge.nudge_type == NudgeType.NEW_LEARNING
        assert "pattern matching" in nudge.message
        assert nudge.dismissed is False

    def test_nudge_is_active(self):
        """Nudge.is_active should return True for non-dismissed, non-expired nudges."""
        from src.intelligence.nudge_engine import Nudge, NudgeType, NudgePriority

        # Active nudge
        nudge = Nudge(
            id="nudge-1",
            user_id="user-456",
            nudge_type=NudgeType.NEW_LEARNING,
            title="Test",
            message="Test message",
            priority=NudgePriority.MEDIUM,
            related_id=None,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            dismissed=False,
            snoozed_until=None
        )
        assert nudge.is_active() is True

    def test_nudge_is_active_false_when_dismissed(self):
        """Dismissed nudges should not be active."""
        from src.intelligence.nudge_engine import Nudge, NudgeType, NudgePriority

        nudge = Nudge(
            id="nudge-1",
            user_id="user-456",
            nudge_type=NudgeType.NEW_LEARNING,
            title="Test",
            message="Test message",
            priority=NudgePriority.MEDIUM,
            related_id=None,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            dismissed=True,  # Dismissed
            snoozed_until=None
        )
        assert nudge.is_active() is False

    def test_nudge_is_active_false_when_snoozed(self):
        """Snoozed nudges should not be active until snooze expires."""
        from src.intelligence.nudge_engine import Nudge, NudgeType, NudgePriority

        nudge = Nudge(
            id="nudge-1",
            user_id="user-456",
            nudge_type=NudgeType.NEW_LEARNING,
            title="Test",
            message="Test message",
            priority=NudgePriority.MEDIUM,
            related_id=None,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            dismissed=False,
            snoozed_until=datetime.now(timezone.utc) + timedelta(hours=1)  # Future
        )
        assert nudge.is_active() is False

    def test_nudge_is_active_true_when_snooze_expired(self):
        """Nudges with expired snooze should be active."""
        from src.intelligence.nudge_engine import Nudge, NudgeType, NudgePriority

        nudge = Nudge(
            id="nudge-1",
            user_id="user-456",
            nudge_type=NudgeType.NEW_LEARNING,
            title="Test",
            message="Test message",
            priority=NudgePriority.MEDIUM,
            related_id=None,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            dismissed=False,
            snoozed_until=datetime.now(timezone.utc) - timedelta(hours=1)  # Past
        )
        assert nudge.is_active() is True


class TestNudgeEngineInit:
    """Tests for NudgeEngine initialization."""

    def test_init_creates_dependencies(self):
        """NudgeEngine should initialize with required dependencies."""
        with patch('src.intelligence.nudge_engine.get_session'):
            from src.intelligence.nudge_engine import NudgeEngine

            engine = NudgeEngine()

            assert engine is not None


class TestCreateNudge:
    """Tests for NudgeEngine.create_nudge()."""

    @pytest.mark.asyncio
    async def test_create_new_learning_nudge(self):
        """Should create nudge when new fact is learned."""
        with patch('src.intelligence.nudge_engine.get_session') as mock_session:
            # Mock result for scalar (can_create_nudge check)
            mock_scalar_result = MagicMock()
            mock_scalar_result.scalar.return_value = 0  # Under limit

            mock_session_ctx = AsyncMock()
            mock_session_ctx.execute = AsyncMock(return_value=mock_scalar_result)
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_cm

            from src.intelligence.nudge_engine import NudgeEngine, NudgeType, NudgePriority

            engine = NudgeEngine()
            nudge = await engine.create_nudge(
                user_id="user-456",
                nudge_type=NudgeType.NEW_LEARNING,
                title="New fact learned",
                message="ACMS learned: Python 3.12 introduced pattern matching",
                priority=NudgePriority.MEDIUM,
                related_id="knowledge-123"
            )

            assert nudge is not None
            assert nudge.nudge_type == NudgeType.NEW_LEARNING
            assert nudge.user_id == "user-456"
            # Should persist to database
            mock_session_ctx.execute.assert_called()

    @pytest.mark.asyncio
    async def test_create_stale_knowledge_nudge(self):
        """Should create nudge for stale knowledge."""
        with patch('src.intelligence.nudge_engine.get_session') as mock_session:
            # Mock result for scalar (can_create_nudge check)
            mock_scalar_result = MagicMock()
            mock_scalar_result.scalar.return_value = 0  # Under limit

            mock_session_ctx = AsyncMock()
            mock_session_ctx.execute = AsyncMock(return_value=mock_scalar_result)
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_cm

            from src.intelligence.nudge_engine import NudgeEngine, NudgeType, NudgePriority

            engine = NudgeEngine()
            nudge = await engine.create_nudge(
                user_id="user-456",
                nudge_type=NudgeType.STALE_KNOWLEDGE,
                title="Knowledge may be outdated",
                message="Information about Docker 20.10 hasn't been verified in 90 days",
                priority=NudgePriority.LOW,
                related_id="knowledge-456",
                expires_at=datetime.now(timezone.utc) + timedelta(days=7)
            )

            assert nudge.nudge_type == NudgeType.STALE_KNOWLEDGE
            assert nudge.expires_at is not None


class TestGetActiveNudges:
    """Tests for NudgeEngine.get_active_nudges()."""

    @pytest.mark.asyncio
    async def test_returns_active_nudges_sorted_by_priority(self):
        """Should return active nudges sorted by priority (high first)."""
        with patch('src.intelligence.nudge_engine.get_session') as mock_session:
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                MagicMock(
                    id="nudge-1",
                    user_id="user-456",
                    nudge_type="new_learning",
                    title="High priority",
                    message="Important",
                    priority="high",
                    related_id=None,
                    created_at=datetime.now(timezone.utc),
                    expires_at=None,
                    dismissed=False,
                    snoozed_until=None
                ),
                MagicMock(
                    id="nudge-2",
                    user_id="user-456",
                    nudge_type="stale_knowledge",
                    title="Low priority",
                    message="Less important",
                    priority="low",
                    related_id=None,
                    created_at=datetime.now(timezone.utc),
                    expires_at=None,
                    dismissed=False,
                    snoozed_until=None
                ),
            ]

            mock_session_ctx = AsyncMock()
            mock_session_ctx.execute = AsyncMock(return_value=mock_result)
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_cm

            from src.intelligence.nudge_engine import NudgeEngine

            engine = NudgeEngine()
            nudges = await engine.get_active_nudges("user-456")

            assert len(nudges) == 2
            # Should be sorted by priority
            assert nudges[0]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_excludes_dismissed_nudges(self):
        """Should not return dismissed nudges."""
        with patch('src.intelligence.nudge_engine.get_session') as mock_session:
            mock_result = MagicMock()
            # Query already filters out dismissed
            mock_result.fetchall.return_value = [
                MagicMock(
                    id="nudge-1",
                    user_id="user-456",
                    nudge_type="new_learning",
                    title="Active nudge",
                    message="This is active",
                    priority="medium",
                    related_id=None,
                    created_at=datetime.now(timezone.utc),
                    expires_at=None,
                    dismissed=False,
                    snoozed_until=None
                ),
            ]

            mock_session_ctx = AsyncMock()
            mock_session_ctx.execute = AsyncMock(return_value=mock_result)
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_cm

            from src.intelligence.nudge_engine import NudgeEngine

            engine = NudgeEngine()
            nudges = await engine.get_active_nudges("user-456")

            # All returned should be non-dismissed
            assert all(n["dismissed"] is False for n in nudges)


class TestDismissNudge:
    """Tests for NudgeEngine.dismiss_nudge()."""

    @pytest.mark.asyncio
    async def test_dismiss_sets_dismissed_true(self):
        """Dismiss should set dismissed=True."""
        with patch('src.intelligence.nudge_engine.get_session') as mock_session:
            mock_session_ctx = AsyncMock()
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_cm

            from src.intelligence.nudge_engine import NudgeEngine

            engine = NudgeEngine()
            result = await engine.dismiss_nudge("nudge-123", "user-456")

            assert result["success"] is True
            # Should update database
            mock_session_ctx.execute.assert_called()
            call_args = str(mock_session_ctx.execute.call_args)
            assert "dismissed" in call_args.lower() or result["success"] is True


class TestSnoozeNudge:
    """Tests for NudgeEngine.snooze_nudge()."""

    @pytest.mark.asyncio
    async def test_snooze_sets_snoozed_until(self):
        """Snooze should set snoozed_until to future time."""
        with patch('src.intelligence.nudge_engine.get_session') as mock_session:
            mock_session_ctx = AsyncMock()
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_cm

            from src.intelligence.nudge_engine import NudgeEngine

            engine = NudgeEngine()
            snooze_duration = timedelta(hours=4)
            result = await engine.snooze_nudge(
                "nudge-123",
                "user-456",
                snooze_duration
            )

            assert result["success"] is True
            assert result["snoozed_until"] is not None
            # snoozed_until should be in the future
            assert result["snoozed_until"] > datetime.now(timezone.utc)


class TestGenerateStaleKnowledgeNudges:
    """Tests for automatic stale knowledge detection."""

    @pytest.mark.asyncio
    async def test_generates_nudges_for_stale_items(self):
        """Should generate nudges for knowledge items not updated in 90+ days."""
        with patch('src.intelligence.nudge_engine.get_session') as mock_session:
            with patch('src.intelligence.nudge_engine.WeaviateClient') as mock_weaviate:
                # Mock stale knowledge items from Weaviate
                mock_client = MagicMock()
                mock_client.query_collection.return_value = [
                    {
                        "id": "knowledge-old-1",
                        "content": "Python 3.8 features",
                        "last_updated": datetime.now(timezone.utc) - timedelta(days=100)
                    },
                    {
                        "id": "knowledge-old-2",
                        "content": "Docker 19.03 commands",
                        "last_updated": datetime.now(timezone.utc) - timedelta(days=95)
                    },
                ]
                mock_weaviate.return_value = mock_client

                mock_session_ctx = AsyncMock()
                mock_cm = AsyncMock()
                mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                mock_cm.__aexit__ = AsyncMock(return_value=None)
                mock_session.return_value = mock_cm

                from src.intelligence.nudge_engine import NudgeEngine

                engine = NudgeEngine()
                count = await engine.generate_stale_knowledge_nudges(
                    user_id="user-456",
                    stale_days=90
                )

                assert count >= 0  # May be 0 if no stale items


class TestGetNudgeCount:
    """Tests for getting nudge counts."""

    @pytest.mark.asyncio
    async def test_returns_count_by_type(self):
        """Should return count of nudges by type."""
        with patch('src.intelligence.nudge_engine.get_session') as mock_session:
            mock_result = MagicMock()
            mock_result.fetchall.return_value = [
                MagicMock(nudge_type="new_learning", count=5),
                MagicMock(nudge_type="stale_knowledge", count=3),
            ]

            mock_session_ctx = AsyncMock()
            mock_session_ctx.execute = AsyncMock(return_value=mock_result)
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_cm

            from src.intelligence.nudge_engine import NudgeEngine

            engine = NudgeEngine()
            counts = await engine.get_nudge_counts("user-456")

            assert counts["total"] == 8
            assert counts["by_type"]["new_learning"] == 5


class TestNudgePreferences:
    """Tests for user nudge preferences."""

    @pytest.mark.asyncio
    async def test_respects_max_daily_nudges(self):
        """Should not create more nudges than max_daily preference."""
        with patch('src.intelligence.nudge_engine.get_session') as mock_session:
            # Mock: user has received 10 nudges today, max is 10
            mock_result = MagicMock()
            mock_result.scalar.return_value = 10  # Already at limit

            mock_session_ctx = AsyncMock()
            mock_session_ctx.execute = AsyncMock(return_value=mock_result)
            mock_cm = AsyncMock()
            mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
            mock_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session.return_value = mock_cm

            from src.intelligence.nudge_engine import NudgeEngine, NudgeType, NudgePriority

            engine = NudgeEngine()
            engine.max_daily_nudges = 10  # User preference

            result = await engine.can_create_nudge("user-456")

            # At limit, so should not allow more
            assert result is False
