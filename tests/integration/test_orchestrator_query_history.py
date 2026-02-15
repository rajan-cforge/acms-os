"""Integration tests for Gateway Orchestrator query_history integration.

Tests that both cache HIT and cache MISS paths correctly save to query_history
with proper from_cache flags and query_id consistency.
"""

import asyncio
import pytest
from uuid import uuid4, UUID
from src.gateway.orchestrator import execute_gateway_request
from src.gateway.models import GatewayRequest, AgentType
from src.storage.database import get_session
from sqlalchemy import text


@pytest.fixture
async def test_user():
    """Create a test user ID for this test session."""
    return str(uuid4())


@pytest.mark.asyncio
async def test_cache_miss_creates_query_history(test_user):
    """Test that cache MISS creates query_history entry with from_cache=FALSE."""

    # Execute fresh query (cache miss)
    request = GatewayRequest(
        query=f"Unique query {uuid4()}",  # Ensure no cache hit
        user_id=test_user,
        bypass_cache=True,  # Force cache miss
        context_limit=5
    )

    response = None
    async for chunk in execute_gateway_request(request):
        if chunk.get("type") == "done":
            response = chunk.get("response")

    # Verify response has query_id
    assert response is not None, "No response received from gateway"
    assert hasattr(response, 'query_id'), "Response missing query_id field"
    assert response.query_id is not None, "query_id is None"
    assert isinstance(response.query_id, UUID), "query_id is not a UUID"

    # Verify from_cache is FALSE
    assert response.from_cache is False, "Cache miss should have from_cache=False"

    # Verify entry exists in database with correct fields
    await asyncio.sleep(0.2)  # Wait for async insert

    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM query_history WHERE query_id = :qid"),
            {"qid": str(response.query_id)}
        )
        row = result.fetchone()

        assert row is not None, (
            f"Query {response.query_id} not found in database! "
            f"Orchestrator did not save to query_history."
        )

        assert row.from_cache is False, "Database entry should have from_cache=FALSE"
        assert row.response_source == response.agent_used.value
        assert row.question == request.query
        assert row.est_cost_usd > 0, "Fresh query should have cost > 0"


@pytest.mark.asyncio
async def test_cache_hit_creates_query_history(test_user):
    """Test that cache HIT creates query_history entry with from_cache=TRUE."""

    unique_query = f"Test cache hit query {uuid4()}"

    # First query (cache miss) - prime the cache
    request1 = GatewayRequest(
        query=unique_query,
        user_id=test_user,
        bypass_cache=False,
        context_limit=5
    )

    response1 = None
    async for chunk in execute_gateway_request(request1):
        if chunk.get("type") == "done":
            response1 = chunk.get("response")

    assert response1 is not None
    assert response1.query_id is not None
    first_query_id = response1.query_id

    # Wait for cache to be populated
    await asyncio.sleep(1.0)

    # Second query (cache hit) - same query
    request2 = GatewayRequest(
        query=unique_query,
        user_id=test_user,
        bypass_cache=False,
        context_limit=5
    )

    response2 = None
    async for chunk in execute_gateway_request(request2):
        if chunk.get("type") == "done":
            response2 = chunk.get("response")

    # Verify cache hit response
    assert response2 is not None
    assert response2.from_cache is True, "Second identical query should be cache hit"
    assert response2.query_id is not None, "Cache hit should have query_id"
    assert response2.query_id != first_query_id, "Cache hit should have NEW query_id"

    # Verify cache hit entry in database
    await asyncio.sleep(0.2)

    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM query_history WHERE query_id = :qid"),
            {"qid": str(response2.query_id)}
        )
        row = result.fetchone()

        assert row is not None, (
            f"Cached query {response2.query_id} not found in database! "
            f"Cache hits are not being saved to query_history."
        )

        assert row.from_cache is True, "Database entry should have from_cache=TRUE"
        assert row.response_source == "semantic_cache"
        assert row.est_cost_usd == 0.0, "Cached response should have cost = 0"
        assert "cache_similarity" in row.metadata, "Cached entry should have similarity metadata"


@pytest.mark.asyncio
async def test_both_cache_paths_create_unique_query_ids(test_user):
    """Test that cache HIT and MISS both create separate query_history entries."""

    unique_query = f"Query ID uniqueness test {uuid4()}"

    # First query (cache miss)
    request1 = GatewayRequest(
        query=unique_query,
        user_id=test_user,
        bypass_cache=False,
        context_limit=5
    )

    response1 = None
    async for chunk in execute_gateway_request(request1):
        if chunk.get("type") == "done":
            response1 = chunk.get("response")

    await asyncio.sleep(1.0)

    # Second query (cache hit)
    request2 = GatewayRequest(
        query=unique_query,
        user_id=test_user,
        bypass_cache=False,
        context_limit=5
    )

    response2 = None
    async for chunk in execute_gateway_request(request2):
        if chunk.get("type") == "done":
            response2 = chunk.get("response")

    # Both should have query_ids
    assert response1.query_id is not None
    assert response2.query_id is not None

    # Query IDs should be DIFFERENT
    assert response1.query_id != response2.query_id, (
        "Cache HIT and MISS should have different query_ids"
    )

    await asyncio.sleep(0.2)

    # Both entries should exist in database
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT query_id, from_cache, response_source
                FROM query_history
                WHERE query_id IN (:id1, :id2)
            """),
            {"id1": str(response1.query_id), "id2": str(response2.query_id)}
        )
        rows = {str(row.query_id): row for row in result.fetchall()}

    assert len(rows) == 2, f"Expected 2 entries, found {len(rows)}"

    # First entry (cache miss)
    assert str(response1.query_id) in rows
    assert rows[str(response1.query_id)].from_cache is False

    # Second entry (cache hit)
    assert str(response2.query_id) in rows
    assert rows[str(response2.query_id)].from_cache is True


@pytest.mark.asyncio
async def test_manual_agent_selection_creates_query_history(test_user):
    """Test that manual agent selection (bypassing intent detection) still saves query_history."""

    request = GatewayRequest(
        query=f"Manual agent test {uuid4()}",
        user_id=test_user,
        manual_agent=AgentType.CLAUDE_SONNET,  # Manual override
        bypass_cache=True,
        context_limit=5
    )

    response = None
    async for chunk in execute_gateway_request(request):
        if chunk.get("type") == "done":
            response = chunk.get("response")

    assert response is not None
    assert response.query_id is not None
    assert response.agent_used == AgentType.CLAUDE_SONNET

    await asyncio.sleep(0.2)

    # Verify in database
    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM query_history WHERE query_id = :qid"),
            {"qid": str(response.query_id)}
        )
        row = result.fetchone()

        assert row is not None
        assert row.response_source == "claude_sonnet"


@pytest.mark.asyncio
async def test_query_history_metadata_structure(test_user):
    """Test that metadata field contains expected structure for both cache paths."""

    unique_query = f"Metadata test {uuid4()}"

    # Cache MISS
    request1 = GatewayRequest(
        query=unique_query,
        user_id=test_user,
        bypass_cache=False,
        context_limit=5
    )

    response1 = None
    async for chunk in execute_gateway_request(request1):
        if chunk.get("type") == "done":
            response1 = chunk.get("response")

    await asyncio.sleep(1.0)

    # Cache HIT
    request2 = GatewayRequest(
        query=unique_query,
        user_id=test_user,
        bypass_cache=False,
        context_limit=5
    )

    response2 = None
    async for chunk in execute_gateway_request(request2):
        if chunk.get("type") == "done":
            response2 = chunk.get("response")

    await asyncio.sleep(0.2)

    async with get_session() as session:
        # Cache MISS metadata
        result = await session.execute(
            text("SELECT metadata FROM query_history WHERE query_id = :qid"),
            {"qid": str(response1.query_id)}
        )
        miss_metadata = result.fetchone().metadata

        assert "cache_status" in miss_metadata
        assert miss_metadata["cache_status"] == "miss"
        assert "intent" in miss_metadata
        assert "context_size" in miss_metadata

        # Cache HIT metadata
        result = await session.execute(
            text("SELECT metadata FROM query_history WHERE query_id = :qid"),
            {"qid": str(response2.query_id)}
        )
        hit_metadata = result.fetchone().metadata

        assert "cache_status" in hit_metadata
        assert hit_metadata["cache_status"] == "hit"
        assert "cache_similarity" in hit_metadata
        assert "cache_type" in hit_metadata
