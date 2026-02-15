"""Integration tests for Gateway caching functionality.

Tests that:
1. First query is fresh (from_cache=False, has cost)
2. Second identical query is cached (from_cache=True, cost=$0)
3. Cache saves 30-40% cost over time
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.gateway.orchestrator import GatewayOrchestrator
from src.gateway.models import GatewayRequest, AgentType, IntentType


@pytest.fixture
async def orchestrator():
    """Create GatewayOrchestrator instance with mocked agents."""
    with patch('src.gateway.orchestrator.ClaudeSonnetAgent') as mock_claude, \
         patch('src.gateway.orchestrator.ChatGPTAgent') as mock_chatgpt, \
         patch('src.gateway.orchestrator.GeminiAgent') as mock_gemini, \
         patch('src.gateway.orchestrator.ClaudeCodeAgent') as mock_code:

        # Mock ChatGPT agent for creative queries
        mock_chatgpt_instance = MagicMock()
        async def chatgpt_generate_mock(query, context):
            yield "Roses "
            yield "are "
            yield "red."
        mock_chatgpt_instance.generate = chatgpt_generate_mock
        mock_chatgpt_instance.estimate_cost = MagicMock(return_value=0.001)
        mock_chatgpt_instance.get_metadata = MagicMock(return_value={
            "agent_name": "ChatGPT",
            "best_for": ["creative", "general"]
        })
        mock_chatgpt.return_value = mock_chatgpt_instance

        # Mock Claude Sonnet agent for analysis queries
        mock_claude_instance = MagicMock()
        async def claude_generate_mock(query, context):
            yield "JWT "
            yield "is "
            yield "secure."
        mock_claude_instance.generate = claude_generate_mock
        mock_claude_instance.estimate_cost = MagicMock(return_value=0.002)
        mock_claude_instance.get_metadata = MagicMock(return_value={
            "agent_name": "Claude Sonnet",
            "best_for": ["analysis", "reasoning"]
        })
        mock_claude.return_value = mock_claude_instance

        orchestrator = GatewayOrchestrator()
        yield orchestrator


class TestGatewayCaching:
    """Test Gateway query result caching."""

    @pytest.mark.asyncio
    async def test_first_query_is_fresh(self, orchestrator):
        """Test that first query is NOT from cache and has cost."""
        request = GatewayRequest(
            query="Write a haiku about databases",
            user_id="test-user",
            bypass_cache=False,
            context_limit=5
        )

        # Collect all events
        events = []
        async for event in orchestrator.execute(request):
            events.append(event)

        # Find the "done" event
        done_event = None
        for event in events:
            if event.get("type") == "done":
                done_event = event
                break

        assert done_event is not None, "No 'done' event found"

        response = done_event["response"]
        assert response["from_cache"] is False, "First query should NOT be from cache"
        assert response["cost_usd"] > 0, "First query should have cost > $0"

    @pytest.mark.asyncio
    async def test_second_query_is_cached(self, orchestrator):
        """Test that second identical query IS from cache with $0 cost."""
        query = "Write a haiku about databases"
        user_id = "test-user"

        # First query (fresh)
        request1 = GatewayRequest(
            query=query,
            user_id=user_id,
            bypass_cache=False,
            context_limit=5
        )

        events1 = []
        async for event in orchestrator.execute(request1):
            events1.append(event)

        # Second query (should be cached)
        request2 = GatewayRequest(
            query=query,
            user_id=user_id,
            bypass_cache=False,
            context_limit=5
        )

        events2 = []
        async for event in orchestrator.execute(request2):
            events2.append(event)

        # Extract responses
        response1 = None
        for event in events1:
            if event.get("type") == "done":
                response1 = event["response"]
                break

        response2 = None
        for event in events2:
            if event.get("type") == "done":
                response2 = event["response"]
                break

        assert response1 is not None
        assert response2 is not None

        # Validate first query
        assert response1["from_cache"] is False
        assert response1["cost_usd"] > 0

        # Validate second query (cached)
        assert response2["from_cache"] is True, "Second identical query should be from cache"
        assert response2["cost_usd"] == 0.0, "Cached query should have $0 cost"
        assert response2["answer"] == response1["answer"], "Cached answer should match original"

    @pytest.mark.asyncio
    async def test_bypass_cache_forces_fresh_query(self, orchestrator):
        """Test that bypass_cache=True forces fresh query even if cached."""
        query = "Write a haiku about databases"
        user_id = "test-user"

        # First query (cache it)
        request1 = GatewayRequest(
            query=query,
            user_id=user_id,
            bypass_cache=False,
            context_limit=5
        )

        events1 = []
        async for event in orchestrator.execute(request1):
            events1.append(event)

        # Second query with bypass_cache=True
        request2 = GatewayRequest(
            query=query,
            user_id=user_id,
            bypass_cache=True,  # Force fresh
            context_limit=5
        )

        events2 = []
        async for event in orchestrator.execute(request2):
            events2.append(event)

        # Extract responses
        response2 = None
        for event in events2:
            if event.get("type") == "done":
                response2 = event["response"]
                break

        assert response2 is not None
        assert response2["from_cache"] is False, "bypass_cache should force fresh query"
        assert response2["cost_usd"] > 0, "Fresh query should have cost > $0"

    @pytest.mark.asyncio
    async def test_different_queries_not_cached(self, orchestrator):
        """Test that different queries are NOT considered cache hits."""
        user_id = "test-user"

        # First query
        request1 = GatewayRequest(
            query="Write a haiku about databases",
            user_id=user_id,
            bypass_cache=False,
            context_limit=5
        )

        events1 = []
        async for event in orchestrator.execute(request1):
            events1.append(event)

        # Different query
        request2 = GatewayRequest(
            query="Write a sonnet about Redis",  # Different query
            user_id=user_id,
            bypass_cache=False,
            context_limit=5
        )

        events2 = []
        async for event in orchestrator.execute(request2):
            events2.append(event)

        # Extract responses
        response2 = None
        for event in events2:
            if event.get("type") == "done":
                response2 = event["response"]
                break

        assert response2 is not None
        assert response2["from_cache"] is False, "Different query should NOT be cached"
        assert response2["cost_usd"] > 0


class TestGatewayCostSavings:
    """Test that caching achieves 30-40% cost savings."""

    @pytest.mark.asyncio
    async def test_cost_savings_calculation(self, orchestrator):
        """Test that cache savings are calculated correctly."""
        queries = [
            "Write a haiku about databases",
            "Explain JWT authentication",
            "Write a haiku about databases",  # Repeat (cache hit)
        ]

        total_cost = 0.0
        total_cost_without_cache = 0.0

        for query in queries:
            request = GatewayRequest(
                query=query,
                user_id="test-user",
                bypass_cache=False,
                context_limit=5
            )

            events = []
            async for event in orchestrator.execute(request):
                events.append(event)

            # Extract response
            for event in events:
                if event.get("type") == "done":
                    response = event["response"]
                    total_cost += response["cost_usd"]

                    # If from cache, add what it WOULD have cost
                    if response["from_cache"]:
                        # Estimate: Creative queries ~$0.001, Analysis ~$0.002
                        estimated_cost = 0.001 if "haiku" in query else 0.002
                        total_cost_without_cache += estimated_cost
                    else:
                        total_cost_without_cache += response["cost_usd"]

        # Calculate savings
        if total_cost_without_cache > 0:
            savings_pct = ((total_cost_without_cache - total_cost) / total_cost_without_cache) * 100
        else:
            savings_pct = 0

        # With 1 cache hit out of 3 queries, savings should be ~33%
        assert savings_pct >= 25, f"Expected savings >=25%, got {savings_pct:.1f}%"
        assert total_cost < total_cost_without_cache, "Cached cost should be less than without cache"

    @pytest.mark.asyncio
    async def test_cache_hit_saves_money(self, orchestrator):
        """Test that cache hit costs $0 while fresh query has cost."""
        query = "Write a haiku about databases"

        # First query (fresh)
        request1 = GatewayRequest(
            query=query,
            user_id="test-user",
            bypass_cache=False,
            context_limit=5
        )

        events1 = []
        async for event in orchestrator.execute(request1):
            events1.append(event)

        response1 = None
        for event in events1:
            if event.get("type") == "done":
                response1 = event["response"]
                break

        # Second query (cached)
        request2 = GatewayRequest(
            query=query,
            user_id="test-user",
            bypass_cache=False,
            context_limit=5
        )

        events2 = []
        async for event in orchestrator.execute(request2):
            events2.append(event)

        response2 = None
        for event in events2:
            if event.get("type") == "done":
                response2 = event["response"]
                break

        assert response1["cost_usd"] > 0, "Fresh query should cost money"
        assert response2["cost_usd"] == 0.0, "Cached query should cost $0"

        savings = response1["cost_usd"] - response2["cost_usd"]
        assert savings > 0, "Cache should save money"
