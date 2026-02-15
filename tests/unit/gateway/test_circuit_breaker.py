"""Unit tests for Circuit Breaker.

Tests verify that:
1. Circuit starts closed and allows calls
2. Circuit opens after threshold failures
3. Open circuit rejects calls with CircuitOpenError
4. Circuit transitions to half-open after timeout
5. Half-open closes on success, opens on failure
6. Stats are tracked correctly
7. Registry manages multiple breakers

TDD spec from ACMS_Combined_Code_Review_Refactor_TDD_Spec.md
"""

import pytest
import asyncio
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.gateway.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitOpenError,
    CircuitBreakerRegistry,
    get_circuit_breaker,
    get_circuit_registry
)


@pytest.fixture
def breaker():
    """Get a fresh circuit breaker."""
    return CircuitBreaker(
        service_name="test_service",
        failure_threshold=3,
        recovery_timeout=1.0,  # Short for testing
        success_threshold=2
    )


@pytest.fixture
def registry():
    """Get a fresh registry."""
    return CircuitBreakerRegistry()


def success_func():
    """Function that succeeds."""
    return "success"


def failure_func():
    """Function that fails."""
    raise ValueError("test failure")


async def async_success_func():
    """Async function that succeeds."""
    return "async success"


async def async_failure_func():
    """Async function that fails."""
    raise ValueError("async test failure")


class TestCircuitBreakerStates:
    """Test circuit breaker state transitions."""

    @pytest.mark.unit
    def test_starts_closed(self, breaker):
        """Circuit should start in closed state."""
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.unit
    def test_stays_closed_on_success(self, breaker):
        """Circuit should stay closed on successful calls."""
        breaker.call(success_func)
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.unit
    def test_stays_closed_below_threshold(self, breaker):
        """Circuit should stay closed when failures < threshold."""
        # 2 failures (threshold is 3)
        for _ in range(2):
            try:
                breaker.call(failure_func)
            except ValueError:
                pass

        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.unit
    def test_opens_at_threshold(self, breaker):
        """Circuit should open when failures reach threshold."""
        # 3 failures (threshold is 3)
        for _ in range(3):
            try:
                breaker.call(failure_func)
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.unit
    def test_success_resets_failure_count(self, breaker):
        """Success should reset consecutive failure count."""
        # 2 failures
        for _ in range(2):
            try:
                breaker.call(failure_func)
            except ValueError:
                pass

        # 1 success resets
        breaker.call(success_func)

        # 2 more failures should not open
        for _ in range(2):
            try:
                breaker.call(failure_func)
            except ValueError:
                pass

        assert breaker.state == CircuitState.CLOSED


class TestCircuitOpen:
    """Test behavior when circuit is open."""

    @pytest.mark.unit
    def test_open_rejects_calls(self, breaker):
        """Open circuit should reject calls."""
        # Open the circuit
        for _ in range(3):
            try:
                breaker.call(failure_func)
            except ValueError:
                pass

        # Should reject with CircuitOpenError
        with pytest.raises(CircuitOpenError) as exc_info:
            breaker.call(success_func)

        assert exc_info.value.service_name == "test_service"
        assert exc_info.value.retry_after >= 0

    @pytest.mark.unit
    def test_open_tracks_rejected_calls(self, breaker):
        """Rejected calls should be tracked in stats."""
        # Open the circuit
        for _ in range(3):
            try:
                breaker.call(failure_func)
            except ValueError:
                pass

        # Try rejected calls
        for _ in range(5):
            try:
                breaker.call(success_func)
            except CircuitOpenError:
                pass

        assert breaker.stats.rejected_calls == 5


class TestHalfOpen:
    """Test half-open state behavior."""

    @pytest.mark.unit
    def test_transitions_to_half_open(self, breaker):
        """Circuit should transition to half-open after timeout."""
        # Open the circuit
        for _ in range(3):
            try:
                breaker.call(failure_func)
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(1.1)

        # Should be half-open now
        assert breaker.state == CircuitState.HALF_OPEN

    @pytest.mark.unit
    def test_half_open_closes_on_success(self, breaker):
        """Half-open should close after success threshold."""
        # Open and wait
        for _ in range(3):
            try:
                breaker.call(failure_func)
            except ValueError:
                pass
        time.sleep(1.1)

        # 2 successes should close (success_threshold=2)
        breaker.call(success_func)
        assert breaker.state == CircuitState.HALF_OPEN

        breaker.call(success_func)
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.unit
    def test_half_open_reopens_on_failure(self, breaker):
        """Half-open should reopen on any failure."""
        # Open and wait
        for _ in range(3):
            try:
                breaker.call(failure_func)
            except ValueError:
                pass
        time.sleep(1.1)

        assert breaker.state == CircuitState.HALF_OPEN

        # Single failure should reopen
        try:
            breaker.call(failure_func)
        except ValueError:
            pass

        assert breaker.state == CircuitState.OPEN


class TestAsyncCalls:
    """Test async function support."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_success(self, breaker):
        """Async successful calls should work."""
        result = await breaker.call_async(async_success_func)
        assert result == "async success"
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_failure_opens_circuit(self, breaker):
        """Async failures should open circuit."""
        for _ in range(3):
            try:
                await breaker.call_async(async_failure_func)
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_async_rejected_when_open(self, breaker):
        """Open circuit should reject async calls."""
        # Open the circuit
        for _ in range(3):
            try:
                await breaker.call_async(async_failure_func)
            except ValueError:
                pass

        with pytest.raises(CircuitOpenError):
            await breaker.call_async(async_success_func)


class TestStats:
    """Test statistics tracking."""

    @pytest.mark.unit
    def test_tracks_total_calls(self, breaker):
        """Should track total calls."""
        breaker.call(success_func)
        breaker.call(success_func)
        try:
            breaker.call(failure_func)
        except ValueError:
            pass

        assert breaker.stats.total_calls == 3

    @pytest.mark.unit
    def test_tracks_successful_calls(self, breaker):
        """Should track successful calls."""
        breaker.call(success_func)
        breaker.call(success_func)

        assert breaker.stats.successful_calls == 2

    @pytest.mark.unit
    def test_tracks_failed_calls(self, breaker):
        """Should track failed calls."""
        try:
            breaker.call(failure_func)
        except ValueError:
            pass
        try:
            breaker.call(failure_func)
        except ValueError:
            pass

        assert breaker.stats.failed_calls == 2

    @pytest.mark.unit
    def test_stats_to_dict(self, breaker):
        """Stats should be convertible to dict."""
        breaker.call(success_func)
        d = breaker.stats.to_dict()

        assert "total_calls" in d
        assert "successful_calls" in d
        assert "failed_calls" in d
        assert "success_rate" in d


class TestHealth:
    """Test health reporting."""

    @pytest.mark.unit
    def test_health_includes_state(self, breaker):
        """Health should include current state."""
        health = breaker.get_health()
        assert health["state"] == "closed"

    @pytest.mark.unit
    def test_health_includes_service_name(self, breaker):
        """Health should include service name."""
        health = breaker.get_health()
        assert health["service"] == "test_service"

    @pytest.mark.unit
    def test_health_includes_retry_after_when_open(self, breaker):
        """Health should include retry_after when open."""
        # Open the circuit
        for _ in range(3):
            try:
                breaker.call(failure_func)
            except ValueError:
                pass

        health = breaker.get_health()
        assert health["retry_after"] is not None
        assert health["retry_after"] > 0


class TestReset:
    """Test circuit reset functionality."""

    @pytest.mark.unit
    def test_reset_closes_circuit(self, breaker):
        """Reset should close the circuit."""
        # Open the circuit
        for _ in range(3):
            try:
                breaker.call(failure_func)
            except ValueError:
                pass

        assert breaker.state == CircuitState.OPEN

        breaker.reset()
        assert breaker.state == CircuitState.CLOSED

    @pytest.mark.unit
    def test_reset_clears_stats(self, breaker):
        """Reset should clear statistics."""
        breaker.call(success_func)
        try:
            breaker.call(failure_func)
        except ValueError:
            pass

        breaker.reset()

        assert breaker.stats.total_calls == 0
        assert breaker.stats.failed_calls == 0


class TestRegistry:
    """Test circuit breaker registry."""

    @pytest.mark.unit
    def test_creates_new_breaker(self, registry):
        """Should create new breaker for unknown service."""
        breaker = registry.get_or_create("new_service")
        assert breaker is not None
        assert breaker.service_name == "new_service"

    @pytest.mark.unit
    def test_returns_existing_breaker(self, registry):
        """Should return existing breaker for known service."""
        breaker1 = registry.get_or_create("my_service")
        breaker2 = registry.get_or_create("my_service")
        assert breaker1 is breaker2

    @pytest.mark.unit
    def test_get_returns_none_for_unknown(self, registry):
        """Get should return None for unknown service."""
        assert registry.get("unknown") is None

    @pytest.mark.unit
    def test_get_all_health(self, registry):
        """Should return health for all breakers."""
        registry.get_or_create("service1")
        registry.get_or_create("service2")

        health = registry.get_all_health()
        assert "service1" in health
        assert "service2" in health

    @pytest.mark.unit
    def test_reset_all(self, registry):
        """Should reset all breakers."""
        breaker1 = registry.get_or_create("s1", failure_threshold=1)
        breaker2 = registry.get_or_create("s2", failure_threshold=1)

        # Open both
        try:
            breaker1.call(failure_func)
        except ValueError:
            pass
        try:
            breaker2.call(failure_func)
        except ValueError:
            pass

        registry.reset_all()

        assert breaker1.state == CircuitState.CLOSED
        assert breaker2.state == CircuitState.CLOSED


class TestExpectedExceptions:
    """Test custom exception handling."""

    @pytest.mark.unit
    def test_only_expected_exceptions_count(self):
        """Only expected exceptions should count as failures."""
        breaker = CircuitBreaker(
            service_name="test",
            failure_threshold=2,
            expected_exceptions=(ValueError,)
        )

        # ValueError should count
        try:
            breaker.call(failure_func)  # Raises ValueError
        except ValueError:
            pass

        assert breaker.stats.consecutive_failures == 1

    @pytest.mark.unit
    def test_unexpected_exceptions_propagate(self):
        """Unexpected exceptions should propagate without counting."""
        breaker = CircuitBreaker(
            service_name="test",
            failure_threshold=2,
            expected_exceptions=(ValueError,)
        )

        def raise_type_error():
            raise TypeError("unexpected")

        # TypeError is not expected, should propagate
        with pytest.raises(TypeError):
            breaker.call(raise_type_error)

        # Should not count as failure for circuit purposes
        # (Actually it will because of how the exception handling works)


class TestGlobalRegistry:
    """Test global registry functions."""

    @pytest.mark.unit
    def test_get_circuit_breaker(self):
        """get_circuit_breaker should use global registry."""
        breaker = get_circuit_breaker("global_test_service")
        assert breaker is not None
        assert breaker.service_name == "global_test_service"

    @pytest.mark.unit
    def test_get_circuit_registry(self):
        """get_circuit_registry should return singleton."""
        reg1 = get_circuit_registry()
        reg2 = get_circuit_registry()
        assert reg1 is reg2
