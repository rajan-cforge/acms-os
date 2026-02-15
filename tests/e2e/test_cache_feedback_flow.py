"""E2E tests for cached response feedback flow.

Tests the complete user journey:
1. User asks query (cache miss)
2. User asks same query (cache hit)
3. User submits feedback on cached response
4. Verify feedback is saved and analytics work
"""

import asyncio
import pytest
import httpx
from uuid import uuid4
from src.storage.database import get_session
from sqlalchemy import text


BASE_URL = "http://localhost:40080"


@pytest.fixture
async def test_user():
    """Create a test user ID for this test session."""
    return str(uuid4())


@pytest.fixture
async def http_client():
    """Create async HTTP client for API requests."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
        yield client


@pytest.mark.asyncio
async def test_feedback_on_cached_response_complete_flow(test_user, http_client):
    """E2E: Query → Cache Hit → Feedback → Analytics.

    This is the CRITICAL test that would have caught the UUID mismatch bug.
    """

    unique_query = f"E2E feedback test {uuid4()}"

    # Step 1: Prime cache (first query)
    print(f"\n1️⃣ Submitting first query (cache miss)...")
    response1 = await http_client.post(
        "/gateway/ask",
        json={
            "query": unique_query,
            "user_id": test_user,
            "bypass_cache": False,
            "context_limit": 5
        }
    )

    assert response1.status_code == 200
    lines = response1.text.strip().split('\n')
    done_event = None
    for line in lines:
        if line.startswith('data: '):
            import json
            event = json.loads(line[6:])
            if event.get("type") == "done":
                done_event = event
                break

    assert done_event is not None, "No 'done' event in response"
    first_response = done_event["response"]
    assert first_response["from_cache"] is False
    first_query_id = first_response["query_id"]
    print(f"   ✓ First query_id: {first_query_id}")

    # Wait for cache to be populated
    await asyncio.sleep(1.5)

    # Step 2: Same query (cache hit)
    print(f"\n2️⃣ Submitting second query (cache hit)...")
    response2 = await http_client.post(
        "/gateway/ask",
        json={
            "query": unique_query,
            "user_id": test_user,
            "bypass_cache": False,
            "context_limit": 5
        }
    )

    assert response2.status_code == 200
    lines = response2.text.strip().split('\n')
    done_event = None
    for line in lines:
        if line.startswith('data: '):
            import json
            event = json.loads(line[6:])
            if event.get("type") == "done":
                done_event = event
                break

    assert done_event is not None
    cached_response = done_event["response"]

    assert cached_response["from_cache"] is True, "Second query should be cache hit"
    cached_query_id = cached_response["query_id"]
    assert cached_query_id is not None, "Cache hit missing query_id"
    assert cached_query_id != first_query_id, "Cache hit should have new query_id"

    print(f"   ✓ Cached query_id: {cached_query_id}")
    print(f"   ✓ from_cache: {cached_response['from_cache']}")

    # Wait for async insert to complete
    await asyncio.sleep(0.3)

    # Step 3: Verify both entries exist in database BEFORE feedback
    print(f"\n3️⃣ Verifying query_history entries exist...")
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT query_id, from_cache, response_source
                FROM query_history
                WHERE query_id IN (:id1, :id2)
            """),
            {"id1": first_query_id, "id2": cached_query_id}
        )
        rows = {str(row.query_id): row for row in result.fetchall()}

    assert len(rows) == 2, (
        f"Expected 2 entries in query_history, found {len(rows)}. "
        f"Missing: {set([first_query_id, cached_query_id]) - set(rows.keys())}"
    )
    assert rows[cached_query_id].from_cache is True
    print(f"   ✓ Both entries exist in database")

    # Step 4: Submit feedback on cached response
    print(f"\n4️⃣ Submitting feedback on cached response...")
    feedback_response = await http_client.post(
        "/feedback",
        json={
            "query_id": cached_query_id,
            "rating": 5,
            "feedback_type": "thumbs_up",
            "comment": "Great cached response!"
        }
    )

    # THIS IS THE CRITICAL ASSERTION that catches UUID mismatch bugs
    assert feedback_response.status_code == 200, (
        f"Feedback submission failed with {feedback_response.status_code}: "
        f"{feedback_response.text}\n"
        f"This means the query_id returned to user ({cached_query_id}) "
        f"doesn't match the query_id in the database. UUID MISMATCH BUG!"
    )

    feedback_result = feedback_response.json()
    print(f"   ✓ Feedback submitted successfully: {feedback_result}")

    # Step 5: Verify feedback was saved
    print(f"\n5️⃣ Verifying feedback was saved...")
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT f.*, qh.from_cache
                FROM feedback f
                JOIN query_history qh ON f.query_id = qh.query_id
                WHERE f.query_id = :qid
            """),
            {"qid": cached_query_id}
        )
        feedback_row = result.fetchone()

    assert feedback_row is not None, "Feedback not found in database"
    assert feedback_row.rating == 5
    assert feedback_row.feedback_type == "thumbs_up"
    assert feedback_row.from_cache is True
    print(f"   ✓ Feedback saved with rating={feedback_row.rating}")

    print(f"\n✅ E2E test passed! Feedback on cached responses works!")


@pytest.mark.asyncio
async def test_feedback_on_fresh_response(test_user, http_client):
    """E2E: Test feedback on cache MISS response."""

    unique_query = f"Fresh response feedback {uuid4()}"

    # Submit fresh query
    response = await http_client.post(
        "/gateway/ask",
        json={
            "query": unique_query,
            "user_id": test_user,
            "bypass_cache": True,  # Force cache miss
            "context_limit": 5
        }
    )

    assert response.status_code == 200
    lines = response.text.strip().split('\n')
    done_event = None
    for line in lines:
        if line.startswith('data: '):
            import json
            event = json.loads(line[6:])
            if event.get("type") == "done":
                done_event = event
                break

    assert done_event is not None
    query_response = done_event["response"]
    assert query_response["from_cache"] is False
    query_id = query_response["query_id"]

    await asyncio.sleep(0.3)

    # Submit feedback
    feedback_response = await http_client.post(
        "/feedback",
        json={
            "query_id": query_id,
            "rating": 4,
            "feedback_type": "thumbs_up"
        }
    )

    assert feedback_response.status_code == 200

    # Verify feedback
    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM feedback WHERE query_id = :qid"),
            {"qid": query_id}
        )
        feedback_row = result.fetchone()

    assert feedback_row is not None
    assert feedback_row.rating == 4


@pytest.mark.asyncio
async def test_feedback_with_retry_on_async_race(test_user, http_client):
    """Test that feedback API handles async insert race conditions.

    If query_id hasn't been written to DB yet (async insert in progress),
    the feedback endpoint should retry a few times before failing.
    """

    unique_query = f"Race condition test {uuid4()}"

    # Submit query
    response = await http_client.post(
        "/gateway/ask",
        json={
            "query": unique_query,
            "user_id": test_user,
            "bypass_cache": False,
            "context_limit": 5
        }
    )

    assert response.status_code == 200
    lines = response.text.strip().split('\n')
    done_event = None
    for line in lines:
        if line.startswith('data: '):
            import json
            event = json.loads(line[6:])
            if event.get("type") == "done":
                done_event = event
                break

    query_id = done_event["response"]["query_id"]

    # Submit feedback IMMEDIATELY (async insert might not be done)
    # Feedback endpoint should retry and succeed
    feedback_response = await http_client.post(
        "/feedback",
        json={
            "query_id": query_id,
            "rating": 5,
            "feedback_type": "thumbs_up"
        }
    )

    # Should still succeed due to retry logic
    assert feedback_response.status_code == 200


@pytest.mark.asyncio
async def test_analytics_separates_cached_vs_fresh_feedback(test_user, http_client):
    """Test that analytics can differentiate feedback on cached vs fresh responses."""

    base_query = f"Analytics test {uuid4()}"

    # Fresh response with positive feedback
    response1 = await http_client.post(
        "/gateway/ask",
        json={"query": base_query, "user_id": test_user, "bypass_cache": True, "context_limit": 5}
    )
    lines = response1.text.strip().split('\n')
    for line in lines:
        if line.startswith('data: '):
            import json
            event = json.loads(line[6:])
            if event.get("type") == "done":
                fresh_query_id = event["response"]["query_id"]
                break

    await asyncio.sleep(0.3)

    await http_client.post(
        "/feedback",
        json={"query_id": fresh_query_id, "rating": 5, "feedback_type": "thumbs_up"}
    )

    # Wait for cache to populate
    await asyncio.sleep(1.5)

    # Cached response with positive feedback
    response2 = await http_client.post(
        "/gateway/ask",
        json={"query": base_query, "user_id": test_user, "bypass_cache": False, "context_limit": 5}
    )
    lines = response2.text.strip().split('\n')
    for line in lines:
        if line.startswith('data: '):
            import json
            event = json.loads(line[6:])
            if event.get("type") == "done":
                cached_query_id = event["response"]["query_id"]
                break

    await asyncio.sleep(0.3)

    await http_client.post(
        "/feedback",
        json={"query_id": cached_query_id, "rating": 5, "feedback_type": "thumbs_up"}
    )

    # Query analytics
    async with get_session() as session:
        # Fresh response feedback
        result = await session.execute(
            text("""
                SELECT COUNT(*) as count
                FROM feedback f
                JOIN query_history qh ON f.query_id = qh.query_id
                WHERE qh.from_cache = FALSE
                AND qh.user_id = :user_id
            """),
            {"user_id": test_user}
        )
        fresh_feedback_count = result.fetchone().count

        # Cached response feedback
        result = await session.execute(
            text("""
                SELECT COUNT(*) as count
                FROM feedback f
                JOIN query_history qh ON f.query_id = qh.query_id
                WHERE qh.from_cache = TRUE
                AND qh.user_id = :user_id
            """),
            {"user_id": test_user}
        )
        cached_feedback_count = result.fetchone().count

    assert fresh_feedback_count >= 1, "Should have at least 1 feedback on fresh response"
    assert cached_feedback_count >= 1, "Should have at least 1 feedback on cached response"

    print(f"\n📊 Analytics verification:")
    print(f"   Fresh response feedback: {fresh_feedback_count}")
    print(f"   Cached response feedback: {cached_feedback_count}")
