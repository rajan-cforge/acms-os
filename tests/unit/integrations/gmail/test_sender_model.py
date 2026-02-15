# tests/unit/integrations/gmail/test_sender_model.py
"""
TDD Tests for SenderImportanceModel v1 (Day 3)

Scoring Rules (0-100):
- Reply frequency: Did user reply to this sender? How often?
- Recency: How recently has user interacted with this sender?
- Domain trust: Is sender from same domain as user?
- VIP list: Is sender explicitly marked as important?
- Historical opens: Does user typically open emails from this sender?
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# Import will be created
from src.integrations.gmail.sender_model import SenderImportanceModel, SenderScore


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def model():
    """SenderImportanceModel instance with mock database."""
    db_pool = AsyncMock()
    return SenderImportanceModel(db_pool=db_pool)


@pytest.fixture
def sample_sender_stats():
    """Sample sender statistics from database."""
    return {
        "sender_email": "boss@company.com",
        "total_received": 50,
        "total_replied": 10,
        "total_opened": 45,
        "last_interaction": datetime.now(timezone.utc) - timedelta(hours=2),
        "is_vip": True,
        "is_muted": False,
    }


# ==========================================
# SCORING RULE TESTS
# ==========================================

class TestScoringRules:
    """Tests for individual scoring components."""

    def test_reply_frequency_score(self, model):
        """Senders user replies to get higher scores."""
        # High reply rate (20%)
        score_high = model._calculate_reply_score(reply_rate=0.20)
        # Low reply rate (1%)
        score_low = model._calculate_reply_score(reply_rate=0.01)

        assert score_high > score_low
        assert 0 <= score_high <= 30  # Max 30 points for reply frequency

    def test_recency_score_recent(self, model):
        """Recent interactions score higher than old ones."""
        now = datetime.now(timezone.utc)

        # Interacted 1 hour ago
        score_recent = model._calculate_recency_score(now - timedelta(hours=1))
        # Interacted 30 days ago
        score_old = model._calculate_recency_score(now - timedelta(days=30))

        assert score_recent > score_old
        assert 0 <= score_recent <= 20  # Max 20 points for recency

    def test_recency_score_never_interacted(self, model):
        """No interaction returns baseline recency score."""
        score = model._calculate_recency_score(None)
        assert score == 5  # Neutral baseline

    def test_domain_trust_same_company(self, model):
        """Same domain gets domain trust bonus."""
        user_email = "user@company.com"

        # Same domain
        score_same = model._calculate_domain_score("colleague@company.com", user_email)
        # Different domain
        score_diff = model._calculate_domain_score("vendor@external.com", user_email)

        assert score_same > score_diff
        assert score_same == 15  # Internal emails are more important
        assert score_diff == 0

    def test_vip_bonus(self, model):
        """VIP senders get significant bonus."""
        score_vip = model._calculate_vip_score(is_vip=True)
        score_normal = model._calculate_vip_score(is_vip=False)

        assert score_vip == 25  # VIP bonus
        assert score_normal == 0

    def test_muted_sender_score_zero(self, model):
        """Muted senders always score 0."""
        # Even with perfect stats, muted = 0
        score = model._calculate_total_score(
            reply_score=30,
            recency_score=20,
            domain_score=15,
            vip_score=25,
            open_score=10,
            is_muted=True,
        )
        assert score == 0


class TestTotalScoreCalculation:
    """Tests for combined scoring."""

    def test_total_score_combines_all_factors(self, model):
        """Total score is sum of all factors."""
        score = model._calculate_total_score(
            reply_score=15,
            recency_score=10,
            domain_score=15,
            vip_score=25,
            open_score=5,
            is_muted=False,
        )
        assert score == 70

    def test_total_score_capped_at_100(self, model):
        """Score is capped at maximum 100."""
        score = model._calculate_total_score(
            reply_score=30,
            recency_score=20,
            domain_score=15,
            vip_score=25,
            open_score=10,
            is_muted=False,
        )
        assert score <= 100

    def test_total_score_minimum_zero(self, model):
        """Score cannot go below 0."""
        score = model._calculate_total_score(
            reply_score=0,
            recency_score=0,
            domain_score=0,
            vip_score=0,
            open_score=0,
            is_muted=False,
        )
        assert score >= 0


# ==========================================
# ASYNC SCORING TESTS
# ==========================================

class TestAsyncScoring:
    """Tests for async scoring methods."""

    @pytest.mark.asyncio
    async def test_score_sender_new_sender(self, model):
        """New sender with no history gets baseline score."""
        # Given: No sender history in database
        model._get_sender_stats = AsyncMock(return_value=None)
        model._update_sender_score = AsyncMock()

        # When: Score new sender
        score = await model.score_sender(
            sender_email="new@unknown.com",
            user_email="user@company.com"
        )

        # Then: Returns baseline score (5 for recency baseline only)
        assert isinstance(score, SenderScore)
        assert score.score >= 5  # Neutral baseline
        assert score.score <= 30  # New sender shouldn't be too high

    @pytest.mark.asyncio
    async def test_score_sender_vip(self, model, sample_sender_stats):
        """VIP sender gets high score."""
        # Given: VIP sender stats
        model._get_sender_stats = AsyncMock(return_value=sample_sender_stats)

        # When: Score VIP sender
        score = await model.score_sender(
            sender_email="boss@company.com",
            user_email="user@company.com"
        )

        # Then: High score due to VIP status
        assert score.score >= 60
        assert score.is_priority is True

    @pytest.mark.asyncio
    async def test_score_sender_updates_cache(self, model, sample_sender_stats):
        """Scoring updates the sender_scores table."""
        model._get_sender_stats = AsyncMock(return_value=sample_sender_stats)
        model._update_sender_score = AsyncMock()

        await model.score_sender(
            sender_email="boss@company.com",
            user_email="user@company.com"
        )

        # Verify cache update was called
        model._update_sender_score.assert_called_once()


# ==========================================
# BATCH SCORING TESTS
# ==========================================

class TestBatchScoring:
    """Tests for batch email scoring."""

    @pytest.mark.asyncio
    async def test_score_emails_batch(self, model):
        """Score multiple emails efficiently."""
        emails = [
            {"sender_email": "a@test.com", "message_id": "1"},
            {"sender_email": "b@test.com", "message_id": "2"},
            {"sender_email": "c@test.com", "message_id": "3"},
        ]

        model.score_sender = AsyncMock(return_value=SenderScore(
            sender_email="test@test.com",
            score=50,
            is_priority=False,
            factors={}
        ))

        scores = await model.score_emails_batch(emails, user_email="user@company.com")

        assert len(scores) == 3
        assert model.score_sender.call_count == 3

    @pytest.mark.asyncio
    async def test_score_emails_returns_sorted_by_priority(self, model):
        """Batch scoring returns emails sorted by score descending."""
        emails = [
            {"sender_email": "low@test.com", "message_id": "1"},
            {"sender_email": "high@test.com", "message_id": "2"},
            {"sender_email": "mid@test.com", "message_id": "3"},
        ]

        async def mock_score(sender_email, user_email, user_id="default"):
            scores = {"low@test.com": 20, "high@test.com": 80, "mid@test.com": 50}
            return SenderScore(
                sender_email=sender_email,
                score=scores[sender_email],
                is_priority=scores[sender_email] >= 60,
                factors={}
            )

        model.score_sender = mock_score

        scores = await model.score_emails_batch(emails, user_email="user@company.com")

        # Verify sorted by score descending
        assert scores[0]["message_id"] == "2"  # highest
        assert scores[1]["message_id"] == "3"  # mid
        assert scores[2]["message_id"] == "1"  # lowest


# ==========================================
# VIP MANAGEMENT TESTS
# ==========================================

class TestVIPManagement:
    """Tests for VIP sender management."""

    @pytest.mark.asyncio
    async def test_add_vip(self, model):
        """Add sender to VIP list."""
        model._execute_query = AsyncMock()

        await model.add_vip("important@company.com", user_id="default")

        model._execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_vip(self, model):
        """Remove sender from VIP list."""
        model._execute_query = AsyncMock()

        await model.remove_vip("notimportant@company.com", user_id="default")

        model._execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_mute_sender(self, model):
        """Mute a sender."""
        model._execute_query = AsyncMock()

        await model.mute_sender("spam@annoying.com", user_id="default")

        model._execute_query.assert_called_once()


# ==========================================
# PRIORITY THRESHOLD TESTS
# ==========================================

class TestPriorityThreshold:
    """Tests for priority email identification."""

    def test_priority_threshold_default(self, model):
        """Default priority threshold is 60."""
        assert model.priority_threshold == 60

    def test_is_priority_above_threshold(self, model):
        """Emails above threshold are marked as priority."""
        assert model._is_priority(score=75) is True
        assert model._is_priority(score=60) is True

    def test_is_priority_below_threshold(self, model):
        """Emails below threshold are not priority."""
        assert model._is_priority(score=59) is False
        assert model._is_priority(score=0) is False
