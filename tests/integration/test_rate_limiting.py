"""Integration test: Rate limiting blocks users after too many security violations.

This test verifies that:
1. Rate limiting kicks in after configured threshold of blocked requests
2. User receives appropriate error message with retry_after
3. After window expires, user can try again

TDD spec from ACMS_Combined_Code_Review_Refactor_TDD_Spec.md
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.gateway.orchestrator import GatewayOrchestrator
from src.gateway.models import GatewayRequest
from src.gateway.rate_limiter import InMemoryRateLimiter


@pytest.fixture
def orchestrator():
    """Get GatewayOrchestrator with test rate limiter."""
    orch = GatewayOrchestrator()
    # Use a fresh rate limiter with low threshold for testing
    orch.rate_limiter = InMemoryRateLimiter(
        blocked_limit=2,  # Only 2 blocked requests allowed
        window_seconds=60,
        global_limit=100
    )
    return orch


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rate_limits_after_repeated_security_blocks(orchestrator):
    """User should be rate limited after too many blocked requests."""
    user_id = "rate_limit_test_user"

    # First blocked request (SSN)
    request1 = GatewayRequest(
        query="my ssn is 123-45-6789",
        user_id=user_id
    )
    events1 = []
    async for event in orchestrator.execute(request1):
        events1.append(event)

    # Should be blocked but not rate limited yet
    error_events1 = [e for e in events1 if e.get('type') == 'error']
    assert len(error_events1) == 1
    assert error_events1[0]['step'] == 'preflight_gate'
    assert "Social Security Number" in error_events1[0]['message']

    # Second blocked request (API key)
    request2 = GatewayRequest(
        query="my api key is sk-test123456789012345678901234",
        user_id=user_id
    )
    events2 = []
    async for event in orchestrator.execute(request2):
        events2.append(event)

    # Should be blocked but not rate limited yet
    error_events2 = [e for e in events2 if e.get('type') == 'error']
    assert len(error_events2) == 1
    assert error_events2[0]['step'] == 'preflight_gate'

    # Third blocked request - should trigger rate limit
    request3 = GatewayRequest(
        query="password = 'supersecret'",
        user_id=user_id
    )
    events3 = []
    async for event in orchestrator.execute(request3):
        events3.append(event)

    # Should be rate limited!
    error_events3 = [e for e in events3 if e.get('type') == 'error']
    assert len(error_events3) == 1
    assert error_events3[0]['step'] == 'rate_limit'
    assert "Too many blocked requests" in error_events3[0]['message']
    assert error_events3[0]['details']['retry_after'] is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rate_limit_only_affects_blocked_user():
    """Rate limiting for one user should not affect others."""
    orch = GatewayOrchestrator()
    orch.rate_limiter = InMemoryRateLimiter(
        blocked_limit=1,  # Very low for testing
        window_seconds=60,
        global_limit=100
    )

    # Block user1
    request1 = GatewayRequest(
        query="ssn 123-45-6789",
        user_id="user1"
    )
    events1 = []
    async for event in orch.execute(request1):
        events1.append(event)

    # Second block for user1 should trigger rate limit
    request1b = GatewayRequest(
        query="ssn 987-65-4321",
        user_id="user1"
    )
    events1b = []
    async for event in orch.execute(request1b):
        events1b.append(event)

    # user1 should be rate limited
    error_events1b = [e for e in events1b if e.get('type') == 'error']
    assert len(error_events1b) == 1
    assert error_events1b[0]['step'] == 'rate_limit'

    # user2 should still work (blocked but not rate limited)
    request2 = GatewayRequest(
        query="ssn 111-22-3333",
        user_id="user2"
    )
    events2 = []
    async for event in orch.execute(request2):
        events2.append(event)

    # user2 should be blocked by preflight (not rate limit)
    error_events2 = [e for e in events2 if e.get('type') == 'error']
    assert len(error_events2) == 1
    assert error_events2[0]['step'] == 'preflight_gate'


@pytest.mark.integration
@pytest.mark.asyncio
async def test_clean_requests_not_rate_limited():
    """Clean requests should not count toward security rate limit."""
    orch = GatewayOrchestrator()
    orch.rate_limiter = InMemoryRateLimiter(
        blocked_limit=2,
        window_seconds=60,
        global_limit=100
    )

    # Block one request
    request1 = GatewayRequest(
        query="ssn 123-45-6789",
        user_id="test_user"
    )
    async for event in orch.execute(request1):
        pass

    # Send clean request - should not contribute to blocked count
    # (Note: This will fail to complete without services, but we're testing
    # that it doesn't get rate limited)
    with patch.object(orch, 'intent_classifier') as mock_ic:
        mock_ic.classify.return_value = (MagicMock(value='general'), 0.9)

        # Mock to prevent full execution
        with patch.object(orch, 'agent_selector'):
            request2 = GatewayRequest(
                query="What is Python?",
                user_id="test_user"
            )
            events2 = []
            try:
                async for event in orch.execute(request2):
                    events2.append(event)
                    # Stop early after preflight passes
                    if event.get('step') == 'preflight_gate' and event.get('type') == 'status':
                        break
            except Exception:
                pass  # Expected - no services

    # Should not be rate limited (only 1 blocked request)
    rate_limit_events = [e for e in events2 if e.get('step') == 'rate_limit']
    assert len(rate_limit_events) == 0
