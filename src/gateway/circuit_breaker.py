"""Circuit Breaker - Fail fast when external services are down.

Implements the Circuit Breaker pattern for external API calls:
- Tavily (web search)
- OpenAI (embeddings, chat)
- Anthropic (Claude)
- Google (Gemini)

States:
- CLOSED: Normal operation, requests flow through
- OPEN: Service failing, reject requests immediately
- HALF_OPEN: Testing if service recovered

Part of Sprint 2 Architecture & Resilience (Days 6-7).
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, Dict, TypeVar, Generic
from enum import Enum
from datetime import datetime, timedelta
import threading

from src.gateway.tracing import get_trace_id

logger = logging.getLogger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject calls
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitStats:
    """Statistics for a circuit breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0

    def to_dict(self) -> dict:
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "rejected_calls": self.rejected_calls,
            "success_rate": self.successful_calls / self.total_calls if self.total_calls > 0 else 0,
            "consecutive_failures": self.consecutive_failures,
            "consecutive_successes": self.consecutive_successes
        }


class CircuitOpenError(Exception):
    """Raised when circuit is open and call is rejected."""
    def __init__(self, service_name: str, retry_after: float):
        self.service_name = service_name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit open for {service_name}. Retry after {retry_after:.1f}s"
        )


class CircuitBreaker:
    """Circuit breaker for external service calls.

    Monitors failures and opens circuit when threshold exceeded.
    After recovery timeout, allows test requests through (half-open).
    If test succeeds, closes circuit. If fails, reopens.

    Usage:
        breaker = CircuitBreaker("tavily", failure_threshold=5, recovery_timeout=30)

        # Sync usage
        try:
            result = breaker.call(sync_function, arg1, arg2)
        except CircuitOpenError as e:
            # Handle circuit open - use fallback

        # Async usage
        try:
            result = await breaker.call_async(async_function, arg1, arg2)
        except CircuitOpenError as e:
            # Handle circuit open
    """

    def __init__(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2,
        expected_exceptions: tuple = (Exception,)
    ):
        """Initialize circuit breaker.

        Args:
            service_name: Name of the service (for logging)
            failure_threshold: Consecutive failures to open circuit
            recovery_timeout: Seconds before attempting recovery
            success_threshold: Successes in half-open to close circuit
            expected_exceptions: Exception types that count as failures
        """
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.expected_exceptions = expected_exceptions

        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._last_state_change = time.time()
        self._lock = threading.RLock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        with self._lock:
            self._check_state_transition()
            return self._state

    @property
    def stats(self) -> CircuitStats:
        """Get circuit statistics."""
        return self._stats

    def _check_state_transition(self) -> None:
        """Check if state should transition based on time."""
        if self._state == CircuitState.OPEN:
            time_in_open = time.time() - self._last_state_change
            if time_in_open >= self.recovery_timeout:
                self._transition_to(CircuitState.HALF_OPEN)

    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to new state."""
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()

        if new_state == CircuitState.HALF_OPEN:
            self._stats.consecutive_successes = 0

        logger.info(
            f"[{get_trace_id()}] Circuit {self.service_name}: "
            f"{old_state.value} -> {new_state.value}"
        )

    def _on_success(self) -> None:
        """Handle successful call."""
        with self._lock:
            self._stats.total_calls += 1
            self._stats.successful_calls += 1
            self._stats.consecutive_failures = 0
            self._stats.consecutive_successes += 1
            self._stats.last_success_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                if self._stats.consecutive_successes >= self.success_threshold:
                    self._transition_to(CircuitState.CLOSED)

    def _on_failure(self, error: Exception) -> None:
        """Handle failed call."""
        with self._lock:
            self._stats.total_calls += 1
            self._stats.failed_calls += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_time = time.time()

            logger.warning(
                f"[{get_trace_id()}] Circuit {self.service_name} failure "
                f"({self._stats.consecutive_failures}/{self.failure_threshold}): {error}"
            )

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in half-open reopens circuit
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._stats.consecutive_failures >= self.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    def _on_rejected(self) -> None:
        """Handle rejected call (circuit open)."""
        with self._lock:
            self._stats.rejected_calls += 1

    def _get_retry_after(self) -> float:
        """Get seconds until circuit might close."""
        time_in_open = time.time() - self._last_state_change
        return max(0, self.recovery_timeout - time_in_open)

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute synchronous function through circuit breaker.

        Args:
            func: Function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Original exception if call fails
        """
        with self._lock:
            self._check_state_transition()

            if self._state == CircuitState.OPEN:
                self._on_rejected()
                raise CircuitOpenError(self.service_name, self._get_retry_after())

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as e:
            self._on_failure(e)
            raise

    async def call_async(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute async function through circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Original exception if call fails
        """
        with self._lock:
            self._check_state_transition()

            if self._state == CircuitState.OPEN:
                self._on_rejected()
                raise CircuitOpenError(self.service_name, self._get_retry_after())

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as e:
            self._on_failure(e)
            raise

    def reset(self) -> None:
        """Reset circuit to closed state. Admin use only."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._stats = CircuitStats()
            self._last_state_change = time.time()
            logger.info(f"Circuit {self.service_name} manually reset")

    def get_health(self) -> dict:
        """Get health status for monitoring."""
        with self._lock:
            return {
                "service": self.service_name,
                "state": self._state.value,
                "stats": self._stats.to_dict(),
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
                "retry_after": self._get_retry_after() if self._state == CircuitState.OPEN else None
            }


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers.

    Provides central access to all circuit breakers and health monitoring.
    """

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()

    def get_or_create(
        self,
        service_name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        **kwargs
    ) -> CircuitBreaker:
        """Get existing breaker or create new one.

        Args:
            service_name: Service identifier
            failure_threshold: Failures before opening
            recovery_timeout: Recovery wait time
            **kwargs: Additional CircuitBreaker arguments

        Returns:
            CircuitBreaker instance
        """
        with self._lock:
            if service_name not in self._breakers:
                self._breakers[service_name] = CircuitBreaker(
                    service_name=service_name,
                    failure_threshold=failure_threshold,
                    recovery_timeout=recovery_timeout,
                    **kwargs
                )
            return self._breakers[service_name]

    def get(self, service_name: str) -> Optional[CircuitBreaker]:
        """Get breaker by name."""
        return self._breakers.get(service_name)

    def get_all_health(self) -> Dict[str, dict]:
        """Get health status of all breakers."""
        return {
            name: breaker.get_health()
            for name, breaker in self._breakers.items()
        }

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.reset()


# Global registry
_circuit_registry: Optional[CircuitBreakerRegistry] = None


def get_circuit_registry() -> CircuitBreakerRegistry:
    """Get the global circuit breaker registry."""
    global _circuit_registry
    if _circuit_registry is None:
        _circuit_registry = CircuitBreakerRegistry()
    return _circuit_registry


def get_circuit_breaker(service_name: str, **kwargs) -> CircuitBreaker:
    """Get or create a circuit breaker for a service.

    Convenience function for getting breakers from global registry.

    Args:
        service_name: Service identifier (e.g., "tavily", "openai", "anthropic")
        **kwargs: CircuitBreaker configuration

    Returns:
        CircuitBreaker instance
    """
    return get_circuit_registry().get_or_create(service_name, **kwargs)
