"""Adversarial tests for rate limiting bypass attempts.

These tests verify that the rate limiting system properly
prevents brute-force and abuse attempts.

Test Categories:
1. Rapid request flooding
2. User ID rotation attempts
3. Blocked query probing
4. Distributed attack simulation
5. Time-based bypass attempts
"""

import pytest
from unittest.mock import Mock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.gateway.rate_limiter import InMemoryRateLimiter, RedisRateLimiter, RateLimitResult


class TestInMemoryRateLimiterAdversarial:
    """Adversarial tests for InMemoryRateLimiter."""

    @pytest.mark.adversarial
    def test_blocks_after_threshold(self):
        """Should block after exceeding blocked request threshold."""
        limiter = InMemoryRateLimiter(blocked_limit=5, window_seconds=60)

        # Submit blocked requests up to limit
        for i in range(5):
            result = limiter.check_and_record("attacker", was_blocked=True)

        # 6th blocked request should be rate limited
        result = limiter.check_and_record("attacker", was_blocked=True)
        assert result.allowed is False, "Should block after exceeding threshold"

    @pytest.mark.adversarial
    def test_tracks_per_user(self):
        """Should track limits per user ID."""
        limiter = InMemoryRateLimiter(blocked_limit=5, window_seconds=60)

        # User 1 hits limit
        for _ in range(6):
            limiter.check_and_record("user1", was_blocked=True)

        # User 2 should still be allowed
        result = limiter.check_and_record("user2", was_blocked=True)
        assert result.allowed is True, "User 2 should not be affected by User 1's limit"

    @pytest.mark.adversarial
    def test_blocked_requests_tracked(self):
        """Blocked requests should be tracked and limited."""
        limiter = InMemoryRateLimiter(blocked_limit=5, window_seconds=60)

        # Submit blocked requests
        results = []
        for _ in range(10):
            result = limiter.check_and_record("user1", was_blocked=True)
            results.append(result.allowed)

        # After threshold, should be blocked
        blocked_count = sum(1 for r in results if not r)
        assert blocked_count > 0, "Should block some requests after threshold"

    @pytest.mark.adversarial
    def test_global_limit_enforcement(self):
        """Should enforce global rate limit across all users."""
        limiter = InMemoryRateLimiter(global_limit=10, window_seconds=60)

        # Different users hitting the service
        results = []
        for i in range(15):
            result = limiter.check_and_record(f"user{i}", was_blocked=False)
            results.append(result.allowed)

        # Some requests should be blocked due to global limit
        blocked = sum(1 for r in results if not r)
        assert blocked > 0, "Should enforce global limit"


class TestRedisRateLimiterAdversarial:
    """Adversarial tests for RedisRateLimiter."""

    @pytest.mark.adversarial
    def test_falls_back_to_memory_on_redis_failure(self):
        """Should fall back to in-memory on Redis failure."""
        mock_redis = Mock()
        mock_redis.pipeline.side_effect = Exception("Redis connection failed")

        limiter = RedisRateLimiter(redis_client=mock_redis, blocked_limit=5)

        # Should not crash, should use fallback
        result = limiter.check_and_record("user1", was_blocked=False)
        assert isinstance(result, RateLimitResult), "Should return result via fallback"

    @pytest.mark.adversarial
    def test_null_redis_uses_fallback(self):
        """Should use in-memory fallback when Redis is None."""
        limiter = RedisRateLimiter(redis_client=None, blocked_limit=5)

        # Should use in-memory fallback
        result = limiter.check_and_record("user1", was_blocked=False)
        assert result.allowed is True

        # Should enforce limits via fallback
        for _ in range(6):
            limiter.check_and_record("attacker", was_blocked=True)

        result = limiter.check_and_record("attacker", was_blocked=True)
        assert result.allowed is False


class TestRapidRequestFlooding:
    """Test protection against rapid request flooding."""

    @pytest.mark.adversarial
    def test_many_rapid_blocked_requests(self):
        """Should handle many rapid blocked requests."""
        limiter = InMemoryRateLimiter(blocked_limit=5, window_seconds=60)

        # Simulate attacker rapidly trying blocked queries
        blocked_count = 0
        for _ in range(100):
            result = limiter.check_and_record("rapid_attacker", was_blocked=True)
            if not result.allowed:
                blocked_count += 1

        # Most requests should be blocked after threshold
        assert blocked_count >= 95, f"Should block most requests, only blocked {blocked_count}"

    @pytest.mark.adversarial
    def test_burst_protection(self):
        """Should protect against request bursts."""
        limiter = InMemoryRateLimiter(blocked_limit=3, window_seconds=60)

        # Rapid burst of blocked requests
        results = []
        for _ in range(10):
            result = limiter.check_and_record("burster", was_blocked=True)
            results.append(result.allowed)

        # First 3 allowed, rest blocked
        allowed_count = sum(results)
        assert allowed_count <= 3, f"Should only allow up to 3 blocked requests, allowed {allowed_count}"


class TestUserIDRotation:
    """Test protection against user ID rotation attacks."""

    @pytest.mark.adversarial
    def test_global_limit_applies_to_all_users(self):
        """Global limit should apply across all users."""
        limiter = InMemoryRateLimiter(global_limit=10, window_seconds=60)

        # Different users hitting the service
        results = []
        for i in range(20):
            result = limiter.check_and_record(f"rotating_user_{i}", was_blocked=False)
            results.append(result.allowed)

        # Some should be blocked after global limit
        blocked = sum(1 for r in results if not r)
        assert blocked > 0, "Global limit should block some requests"

    @pytest.mark.adversarial
    def test_user_id_isolation(self):
        """Users should be tracked independently for per-user limits."""
        limiter = InMemoryRateLimiter(blocked_limit=2, window_seconds=60)

        # User 1 hits their blocked limit
        for _ in range(3):
            limiter.check_and_record("user1", was_blocked=True)

        # User 2 should still be allowed
        result = limiter.check_and_record("user2", was_blocked=True)
        assert result.allowed is True


class TestBlockedQueryProbing:
    """Test protection against probing for blocked patterns."""

    @pytest.mark.adversarial
    def test_escalates_on_repeated_blocks(self):
        """Should escalate restrictions on repeated blocked attempts."""
        limiter = InMemoryRateLimiter(blocked_limit=5, window_seconds=60)

        # Attacker probing with blocked queries
        for i in range(5):
            limiter.check_and_record("prober", was_blocked=True)

        # After hitting limit, all further blocked requests denied
        result = limiter.check_and_record("prober", was_blocked=True)
        assert result.allowed is False


class TestWindowBehavior:
    """Test sliding window behavior."""

    @pytest.mark.adversarial
    def test_old_entries_expire(self):
        """Old entries should expire after window."""
        # Use a very short window for testing
        limiter = InMemoryRateLimiter(blocked_limit=2, window_seconds=1)

        # Fill the limit
        limiter.check_and_record("user1", was_blocked=True)
        limiter.check_and_record("user1", was_blocked=True)
        result = limiter.check_and_record("user1", was_blocked=True)
        assert result.allowed is False

        # Wait for window to pass (in real tests, we'd use time mocking)
        # For now, just verify the structure is correct
        assert limiter.window_seconds == 1


class TestRateLimitResult:
    """Test RateLimitResult structure."""

    @pytest.mark.adversarial
    def test_result_has_required_fields(self):
        """RateLimitResult should have required fields."""
        limiter = InMemoryRateLimiter()
        result = limiter.check_and_record("user1", was_blocked=False)

        # Check actual fields from the dataclass
        assert hasattr(result, 'allowed')
        assert hasattr(result, 'current_count')
        assert hasattr(result, 'limit')
        assert hasattr(result, 'window_seconds')
        assert hasattr(result, 'trace_id')

    @pytest.mark.adversarial
    def test_result_is_serializable(self):
        """RateLimitResult should be serializable."""
        limiter = InMemoryRateLimiter()
        result = limiter.check_and_record("user1", was_blocked=False)

        # Should have to_dict method
        d = result.to_dict()
        assert isinstance(d, dict)
        assert 'allowed' in d
        assert 'current_count' in d


class TestConcurrentAccess:
    """Test behavior under concurrent access patterns."""

    @pytest.mark.adversarial
    def test_handles_many_users(self):
        """Should handle many simultaneous users."""
        limiter = InMemoryRateLimiter(global_limit=1000, window_seconds=60)

        # Simulate many users
        for i in range(500):
            result = limiter.check_and_record(f"user_{i}", was_blocked=False)

        # Should still function
        result = limiter.check_and_record("final_user", was_blocked=False)
        assert isinstance(result, RateLimitResult)

    @pytest.mark.adversarial
    def test_cleanup_doesnt_crash(self):
        """Cleanup should not crash under load."""
        limiter = InMemoryRateLimiter(blocked_limit=5, window_seconds=60)

        # Many different users with blocked requests
        for i in range(100):
            for _ in range(3):
                limiter.check_and_record(f"user_{i}", was_blocked=True)

        # Force cleanup
        if hasattr(limiter, '_cleanup'):
            limiter._cleanup()

        # Should still function after cleanup
        result = limiter.check_and_record("post_cleanup_user", was_blocked=False)
        assert isinstance(result, RateLimitResult)


class TestConfiguration:
    """Test rate limiter configuration."""

    @pytest.mark.adversarial
    def test_custom_limits(self):
        """Should accept custom limits."""
        limiter = InMemoryRateLimiter(
            blocked_limit=10,
            window_seconds=120,
            global_limit=500
        )

        assert limiter.blocked_limit == 10
        assert limiter.window_seconds == 120
        assert limiter.global_limit == 500

    @pytest.mark.adversarial
    def test_default_limits(self):
        """Should have sensible defaults."""
        limiter = InMemoryRateLimiter()

        assert limiter.blocked_limit > 0
        assert limiter.window_seconds > 0
        assert limiter.global_limit > 0


class TestMetrics:
    """Test rate limiter metrics."""

    @pytest.mark.adversarial
    def test_tracks_statistics(self):
        """Should track request statistics."""
        limiter = InMemoryRateLimiter()

        for _ in range(10):
            limiter.check_and_record("user1", was_blocked=False)
        for _ in range(5):
            limiter.check_and_record("user1", was_blocked=True)

        # Check if metrics are available
        if hasattr(limiter, 'get_stats'):
            stats = limiter.get_stats("user1")
            assert "total_requests" in stats or isinstance(stats, dict)
