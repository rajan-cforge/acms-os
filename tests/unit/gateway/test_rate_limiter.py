"""Unit tests for Rate Limiter.

Tests verify that:
1. Normal requests are allowed
2. Too many blocked requests trigger rate limiting
3. Global rate limit is enforced
4. Sliding window cleans old entries
5. Stats are reported correctly
6. Rate limit can be reset

TDD spec from ACMS_Combined_Code_Review_Refactor_TDD_Spec.md
"""

import pytest
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.gateway.rate_limiter import InMemoryRateLimiter, get_rate_limiter


@pytest.fixture
def limiter():
    """Get a fresh rate limiter instance."""
    return InMemoryRateLimiter(
        blocked_limit=3,
        window_seconds=60,
        global_limit=10
    )


class TestNormalRequests:
    """Test that normal requests are allowed."""

    @pytest.mark.unit
    def test_allows_first_request(self, limiter):
        """First request should always be allowed."""
        result = limiter.check_and_record("user1", was_blocked=False)
        assert result.allowed is True
        # Count is reported BEFORE recording (shows 0 for first request)
        # Use stats to verify actual count after recording
        stats = limiter.get_stats("user1")
        assert stats["total_requests"] == 1

    @pytest.mark.unit
    def test_allows_multiple_normal_requests(self, limiter):
        """Multiple normal requests should be allowed up to limit."""
        for i in range(5):
            result = limiter.check_and_record("user1", was_blocked=False)
            assert result.allowed is True

    @pytest.mark.unit
    def test_tracks_count_correctly(self, limiter):
        """Should track request count correctly."""
        for i in range(3):
            limiter.check_and_record("user1", was_blocked=False)

        stats = limiter.get_stats("user1")
        assert stats["total_requests"] == 3
        assert stats["blocked_requests"] == 0


class TestBlockedRequestLimit:
    """Test blocked request rate limiting."""

    @pytest.mark.unit
    def test_allows_initial_blocked_requests(self, limiter):
        """Initial blocked requests should be allowed."""
        result = limiter.check_and_record("user1", was_blocked=True)
        assert result.allowed is True

    @pytest.mark.unit
    def test_rate_limits_after_threshold(self, limiter):
        """Should rate limit after too many blocked requests."""
        # Use up all 3 blocked requests
        for i in range(3):
            result = limiter.check_and_record("user1", was_blocked=True)
            assert result.allowed is True

        # 4th blocked request should be rate limited
        result = limiter.check_and_record("user1", was_blocked=True)
        assert result.allowed is False
        assert result.reason == "security_block_limit"

    @pytest.mark.unit
    def test_provides_retry_after(self, limiter):
        """Should provide retry_after when rate limited."""
        for i in range(3):
            limiter.check_and_record("user1", was_blocked=True)

        result = limiter.check_and_record("user1", was_blocked=True)
        assert result.allowed is False
        assert result.retry_after is not None
        assert result.retry_after > 0

    @pytest.mark.unit
    def test_blocked_count_correct(self, limiter):
        """Should track blocked count separately."""
        # 2 normal requests
        limiter.check_and_record("user1", was_blocked=False)
        limiter.check_and_record("user1", was_blocked=False)

        # 1 blocked request
        limiter.check_and_record("user1", was_blocked=True)

        stats = limiter.get_stats("user1")
        assert stats["total_requests"] == 3
        assert stats["blocked_requests"] == 1


class TestGlobalRateLimit:
    """Test global rate limit enforcement."""

    @pytest.mark.unit
    def test_enforces_global_limit(self, limiter):
        """Should enforce global rate limit."""
        # Use up all 10 global requests
        for i in range(10):
            result = limiter.check_and_record("user1", was_blocked=False)
            assert result.allowed is True

        # 11th request should be rate limited
        result = limiter.check_and_record("user1", was_blocked=False)
        assert result.allowed is False
        assert result.reason == "global_rate_limit"

    @pytest.mark.unit
    def test_global_limit_has_retry_after(self, limiter):
        """Should provide retry_after for global limit."""
        for i in range(10):
            limiter.check_and_record("user1", was_blocked=False)

        result = limiter.check_and_record("user1", was_blocked=False)
        assert result.allowed is False
        assert result.retry_after is not None


class TestUserIsolation:
    """Test that users are isolated from each other."""

    @pytest.mark.unit
    def test_users_are_isolated(self, limiter):
        """Different users should have separate limits."""
        # User1 uses all blocked requests
        for i in range(3):
            limiter.check_and_record("user1", was_blocked=True)

        # User2 should still be allowed
        result = limiter.check_and_record("user2", was_blocked=True)
        assert result.allowed is True

    @pytest.mark.unit
    def test_different_user_stats(self, limiter):
        """Stats should be per-user."""
        limiter.check_and_record("user1", was_blocked=True)
        limiter.check_and_record("user1", was_blocked=True)
        limiter.check_and_record("user2", was_blocked=False)

        stats1 = limiter.get_stats("user1")
        stats2 = limiter.get_stats("user2")

        assert stats1["blocked_requests"] == 2
        assert stats2["blocked_requests"] == 0


class TestCheckOnly:
    """Test check-only functionality."""

    @pytest.mark.unit
    def test_check_only_does_not_record(self, limiter):
        """check_only should not increment counter."""
        limiter.check_and_record("user1", was_blocked=True)

        # Check without recording
        result = limiter.check_only("user1")
        assert result.allowed is True

        stats = limiter.get_stats("user1")
        assert stats["blocked_requests"] == 1  # Still just 1

    @pytest.mark.unit
    def test_check_only_reports_limit_status(self, limiter):
        """check_only should report when at limit."""
        for i in range(3):
            limiter.check_and_record("user1", was_blocked=True)

        result = limiter.check_only("user1")
        assert result.allowed is False


class TestReset:
    """Test rate limit reset functionality."""

    @pytest.mark.unit
    def test_reset_clears_user(self, limiter):
        """reset_user should clear all records."""
        for i in range(3):
            limiter.check_and_record("user1", was_blocked=True)

        limiter.reset_user("user1")

        result = limiter.check_and_record("user1", was_blocked=True)
        assert result.allowed is True

        stats = limiter.get_stats("user1")
        assert stats["blocked_requests"] == 1

    @pytest.mark.unit
    def test_reset_only_affects_specified_user(self, limiter):
        """reset should only affect specified user."""
        limiter.check_and_record("user1", was_blocked=True)
        limiter.check_and_record("user2", was_blocked=True)

        limiter.reset_user("user1")

        stats2 = limiter.get_stats("user2")
        assert stats2["blocked_requests"] == 1


class TestStats:
    """Test stats reporting."""

    @pytest.mark.unit
    def test_stats_format(self, limiter):
        """Stats should have expected format."""
        limiter.check_and_record("user1", was_blocked=True)

        stats = limiter.get_stats("user1")

        assert "user_id" in stats
        assert "total_requests" in stats
        assert "blocked_requests" in stats
        assert "global_limit" in stats
        assert "blocked_limit" in stats
        assert "window_seconds" in stats
        assert "global_remaining" in stats
        assert "blocked_remaining" in stats

    @pytest.mark.unit
    def test_remaining_calculated_correctly(self, limiter):
        """Remaining should be calculated correctly."""
        limiter.check_and_record("user1", was_blocked=True)

        stats = limiter.get_stats("user1")
        assert stats["blocked_remaining"] == 2  # 3 - 1 = 2
        assert stats["global_remaining"] == 9  # 10 - 1 = 9


class TestResultFormat:
    """Test RateLimitResult format."""

    @pytest.mark.unit
    def test_result_to_dict(self, limiter):
        """to_dict should have expected format."""
        result = limiter.check_and_record("user1", was_blocked=True)
        d = result.to_dict()

        assert "allowed" in d
        assert "current_count" in d
        assert "limit" in d
        assert "window_seconds" in d
        assert "trace_id" in d

    @pytest.mark.unit
    def test_result_includes_trace_id(self, limiter):
        """Result should include trace_id."""
        result = limiter.check_and_record("user1", was_blocked=False)
        # trace_id may be empty if not set, but field should exist
        assert "trace_id" in result.to_dict()


class TestSingleton:
    """Test singleton behavior."""

    @pytest.mark.unit
    def test_get_rate_limiter_returns_same_instance(self):
        """get_rate_limiter should return same instance."""
        limiter1 = get_rate_limiter()
        limiter2 = get_rate_limiter()
        assert limiter1 is limiter2


class TestSlidingWindow:
    """Test sliding window behavior."""

    @pytest.mark.unit
    def test_window_size_respected(self):
        """Requests should expire after window."""
        # Use very short window for testing
        limiter = InMemoryRateLimiter(
            blocked_limit=2,
            window_seconds=1,  # 1 second window
            global_limit=10
        )

        # Use all blocked requests
        limiter.check_and_record("user1", was_blocked=True)
        limiter.check_and_record("user1", was_blocked=True)

        # Should be rate limited
        result = limiter.check_and_record("user1", was_blocked=True)
        assert result.allowed is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        result = limiter.check_and_record("user1", was_blocked=True)
        assert result.allowed is True
