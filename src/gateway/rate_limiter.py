"""Rate Limiter - Prevents brute-force probing of security filters.

This module implements rate limiting specifically for security-related blocking:
- If a user triggers too many security blocks, they get temporarily banned
- Prevents attackers from probing to find bypass patterns
- Uses sliding window with Redis for distributed rate limiting

Part of Sprint 1 Security Foundation (Day 3).
"""

import time
import os
from dataclasses import dataclass
from typing import Optional, Dict
from collections import defaultdict
import threading

from src.gateway.tracing import get_trace_id


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    current_count: int
    limit: int
    window_seconds: int
    retry_after: Optional[int] = None  # Seconds until limit resets
    reason: Optional[str] = None
    trace_id: str = ""

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "current_count": self.current_count,
            "limit": self.limit,
            "window_seconds": self.window_seconds,
            "retry_after": self.retry_after,
            "reason": self.reason,
            "trace_id": self.trace_id
        }


class InMemoryRateLimiter:
    """In-memory rate limiter using sliding window algorithm.

    For production, this should be replaced with Redis-backed implementation
    to support distributed rate limiting across multiple instances.
    """

    def __init__(
        self,
        blocked_limit: int = 5,  # Max blocked requests per window
        window_seconds: int = 60,  # Sliding window size
        global_limit: int = 100,  # Max total requests per window
    ):
        """Initialize the rate limiter.

        Args:
            blocked_limit: Max security-blocked requests before rate limiting
            window_seconds: Size of sliding window in seconds
            global_limit: Max total requests per window (regardless of blocking)
        """
        self.blocked_limit = blocked_limit
        self.window_seconds = window_seconds
        self.global_limit = global_limit

        # Storage: user_id -> list of (timestamp, was_blocked)
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = threading.Lock()

    def check_and_record(
        self,
        user_id: str,
        was_blocked: bool = False
    ) -> RateLimitResult:
        """Check rate limit and record the request.

        Args:
            user_id: User identifier
            was_blocked: Whether this request was blocked by security

        Returns:
            RateLimitResult indicating if request is allowed
        """
        trace_id = get_trace_id()
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            # Clean old entries
            self._requests[user_id] = [
                (ts, blocked) for ts, blocked in self._requests[user_id]
                if ts > window_start
            ]

            # Count requests in current window
            total_count = len(self._requests[user_id])
            blocked_count = sum(1 for _, blocked in self._requests[user_id] if blocked)

            # Check global rate limit
            if total_count >= self.global_limit:
                oldest = min((ts for ts, _ in self._requests[user_id]), default=now)
                retry_after = int(oldest + self.window_seconds - now) + 1
                return RateLimitResult(
                    allowed=False,
                    current_count=total_count,
                    limit=self.global_limit,
                    window_seconds=self.window_seconds,
                    retry_after=retry_after,
                    reason="global_rate_limit",
                    trace_id=trace_id
                )

            # Check blocked request rate limit
            if blocked_count >= self.blocked_limit:
                oldest_blocked = min(
                    (ts for ts, blocked in self._requests[user_id] if blocked),
                    default=now
                )
                retry_after = int(oldest_blocked + self.window_seconds - now) + 1
                return RateLimitResult(
                    allowed=False,
                    current_count=blocked_count,
                    limit=self.blocked_limit,
                    window_seconds=self.window_seconds,
                    retry_after=retry_after,
                    reason="security_block_limit",
                    trace_id=trace_id
                )

            # Record this request
            self._requests[user_id].append((now, was_blocked))

            return RateLimitResult(
                allowed=True,
                current_count=blocked_count if was_blocked else total_count,
                limit=self.blocked_limit if was_blocked else self.global_limit,
                window_seconds=self.window_seconds,
                trace_id=trace_id
            )

    def check_only(self, user_id: str) -> RateLimitResult:
        """Check rate limit without recording a request.

        Useful for pre-checking before expensive operations.
        """
        trace_id = get_trace_id()
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            # Count valid entries
            valid_entries = [
                (ts, blocked) for ts, blocked in self._requests.get(user_id, [])
                if ts > window_start
            ]

            total_count = len(valid_entries)
            blocked_count = sum(1 for _, blocked in valid_entries if blocked)

            if total_count >= self.global_limit:
                return RateLimitResult(
                    allowed=False,
                    current_count=total_count,
                    limit=self.global_limit,
                    window_seconds=self.window_seconds,
                    reason="global_rate_limit",
                    trace_id=trace_id
                )

            if blocked_count >= self.blocked_limit:
                return RateLimitResult(
                    allowed=False,
                    current_count=blocked_count,
                    limit=self.blocked_limit,
                    window_seconds=self.window_seconds,
                    reason="security_block_limit",
                    trace_id=trace_id
                )

            return RateLimitResult(
                allowed=True,
                current_count=total_count,
                limit=self.global_limit,
                window_seconds=self.window_seconds,
                trace_id=trace_id
            )

    def reset_user(self, user_id: str) -> None:
        """Reset rate limit for a user. Admin use only."""
        with self._lock:
            self._requests.pop(user_id, None)

    def get_stats(self, user_id: str) -> dict:
        """Get rate limit stats for a user."""
        now = time.time()
        window_start = now - self.window_seconds

        with self._lock:
            valid_entries = [
                (ts, blocked) for ts, blocked in self._requests.get(user_id, [])
                if ts > window_start
            ]

            total_count = len(valid_entries)
            blocked_count = sum(1 for _, blocked in valid_entries if blocked)

            return {
                "user_id": user_id,
                "total_requests": total_count,
                "blocked_requests": blocked_count,
                "global_limit": self.global_limit,
                "blocked_limit": self.blocked_limit,
                "window_seconds": self.window_seconds,
                "global_remaining": self.global_limit - total_count,
                "blocked_remaining": self.blocked_limit - blocked_count
            }


class RedisRateLimiter:
    """Redis-backed rate limiter for distributed deployments.

    Uses Redis sorted sets for efficient sliding window implementation.
    Falls back to in-memory if Redis is unavailable.
    """

    def __init__(
        self,
        redis_client=None,
        blocked_limit: int = 5,
        window_seconds: int = 60,
        global_limit: int = 100,
        key_prefix: str = "acms:ratelimit:"
    ):
        """Initialize Redis rate limiter.

        Args:
            redis_client: Redis client (sync or async)
            blocked_limit: Max blocked requests per window
            window_seconds: Sliding window size
            global_limit: Max total requests per window
            key_prefix: Prefix for Redis keys
        """
        self.redis = redis_client
        self.blocked_limit = blocked_limit
        self.window_seconds = window_seconds
        self.global_limit = global_limit
        self.key_prefix = key_prefix

        # Fallback to in-memory if Redis not available
        self._fallback = InMemoryRateLimiter(
            blocked_limit=blocked_limit,
            window_seconds=window_seconds,
            global_limit=global_limit
        )

    def _get_key(self, user_id: str, key_type: str) -> str:
        """Generate Redis key for user."""
        return f"{self.key_prefix}{key_type}:{user_id}"

    def check_and_record(
        self,
        user_id: str,
        was_blocked: bool = False
    ) -> RateLimitResult:
        """Check rate limit and record request using Redis."""
        if self.redis is None:
            return self._fallback.check_and_record(user_id, was_blocked)

        try:
            return self._redis_check_and_record(user_id, was_blocked)
        except Exception:
            # Fallback to in-memory on Redis errors
            return self._fallback.check_and_record(user_id, was_blocked)

    def _redis_check_and_record(
        self,
        user_id: str,
        was_blocked: bool
    ) -> RateLimitResult:
        """Redis implementation of check and record."""
        trace_id = get_trace_id()
        now = time.time()
        window_start = now - self.window_seconds

        # Keys
        total_key = self._get_key(user_id, "total")
        blocked_key = self._get_key(user_id, "blocked")

        # Use pipeline for atomic operations
        pipe = self.redis.pipeline()

        # Remove old entries
        pipe.zremrangebyscore(total_key, "-inf", window_start)
        pipe.zremrangebyscore(blocked_key, "-inf", window_start)

        # Count current entries
        pipe.zcard(total_key)
        pipe.zcard(blocked_key)

        results = pipe.execute()
        total_count = results[2]
        blocked_count = results[3]

        # Check limits
        if total_count >= self.global_limit:
            # Get oldest entry to calculate retry_after
            oldest = self.redis.zrange(total_key, 0, 0, withscores=True)
            retry_after = int(oldest[0][1] + self.window_seconds - now) + 1 if oldest else 60
            return RateLimitResult(
                allowed=False,
                current_count=total_count,
                limit=self.global_limit,
                window_seconds=self.window_seconds,
                retry_after=retry_after,
                reason="global_rate_limit",
                trace_id=trace_id
            )

        if blocked_count >= self.blocked_limit:
            oldest = self.redis.zrange(blocked_key, 0, 0, withscores=True)
            retry_after = int(oldest[0][1] + self.window_seconds - now) + 1 if oldest else 60
            return RateLimitResult(
                allowed=False,
                current_count=blocked_count,
                limit=self.blocked_limit,
                window_seconds=self.window_seconds,
                retry_after=retry_after,
                reason="security_block_limit",
                trace_id=trace_id
            )

        # Record request
        member = f"{now}:{trace_id}"
        pipe = self.redis.pipeline()
        pipe.zadd(total_key, {member: now})
        pipe.expire(total_key, self.window_seconds + 10)

        if was_blocked:
            pipe.zadd(blocked_key, {member: now})
            pipe.expire(blocked_key, self.window_seconds + 10)

        pipe.execute()

        return RateLimitResult(
            allowed=True,
            current_count=blocked_count if was_blocked else total_count,
            limit=self.blocked_limit if was_blocked else self.global_limit,
            window_seconds=self.window_seconds,
            trace_id=trace_id
        )

    def check_only(self, user_id: str) -> RateLimitResult:
        """Check rate limit without recording."""
        if self.redis is None:
            return self._fallback.check_only(user_id)
        return self._fallback.check_only(user_id)  # Simplified for now


# Singleton instance
_rate_limiter: Optional[InMemoryRateLimiter] = None


def get_rate_limiter() -> InMemoryRateLimiter:
    """Get the singleton rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = InMemoryRateLimiter(
            blocked_limit=int(os.getenv("ACMS_BLOCKED_RATE_LIMIT", "5")),
            window_seconds=int(os.getenv("ACMS_RATE_LIMIT_WINDOW", "60")),
            global_limit=int(os.getenv("ACMS_GLOBAL_RATE_LIMIT", "100"))
        )
    return _rate_limiter
