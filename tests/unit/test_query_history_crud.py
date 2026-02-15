"""Unit tests for query_history CRUD operations.

Tests the core functionality of query history tracking including
UUID consistency, async inserts, and database operations.
"""

import asyncio
import pytest
from uuid import uuid4, UUID
from src.storage.query_history_crud import (
    save_query_to_history,
    save_query_to_history_async
)
from src.storage.database import get_session
from sqlalchemy import text


@pytest.mark.asyncio
async def test_save_query_to_history_basic():
    """Test basic query_history insert with required fields."""
    user_id = str(uuid4())

    query_id = await save_query_to_history(
        user_id=user_id,
        question="Test question?",
        answer="Test answer",
        response_source="claude_sonnet",
        from_cache=False
    )

    assert query_id is not None
    assert isinstance(query_id, UUID)

    # Verify entry exists in database
    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM query_history WHERE query_id = :qid"),
            {"qid": str(query_id)}
        )
        row = result.fetchone()

        assert row is not None
        assert row.user_id == user_id
        assert row.question == "Test question?"
        assert row.from_cache is False
        assert row.response_source == "claude_sonnet"


@pytest.mark.asyncio
async def test_save_query_to_history_with_cache_metadata():
    """Test query_history insert for cached response with metadata."""
    user_id = str(uuid4())

    query_id = await save_query_to_history(
        user_id=user_id,
        question="Cached question?",
        answer="Cached answer",
        response_source="semantic_cache",
        from_cache=True,
        confidence=0.95,
        cost_usd=0.0,
        latency_ms=15,
        metadata={
            "cache_similarity": 0.95,
            "cache_status": "hit",
            "cache_type": "semantic"
        }
    )

    assert query_id is not None

    # Verify all fields saved correctly
    async with get_session() as session:
        result = await session.execute(
            text("SELECT * FROM query_history WHERE query_id = :qid"),
            {"qid": str(query_id)}
        )
        row = result.fetchone()

        assert row.from_cache is True
        assert row.response_source == "semantic_cache"
        assert row.confidence == 0.95
        assert row.est_cost_usd == 0.0
        assert row.total_latency_ms == 15
        assert "cache_similarity" in row.metadata


@pytest.mark.asyncio
async def test_uuid_consistency_sync():
    """CRITICAL: Test that pre-generated UUID is used in database.

    This test catches the bug where save_query_to_history() generates
    a new UUID instead of using the provided one.
    """
    user_id = str(uuid4())
    pre_generated_uuid = uuid4()

    # Pass pre-generated UUID
    returned_uuid = await save_query_to_history(
        user_id=user_id,
        question="UUID consistency test",
        answer="Answer",
        response_source="claude_sonnet",
        from_cache=False,
        query_id=pre_generated_uuid  # Pass explicit UUID
    )

    # Returned UUID should match pre-generated UUID
    assert returned_uuid == pre_generated_uuid

    # Database should have the SAME UUID
    async with get_session() as session:
        result = await session.execute(
            text("SELECT query_id FROM query_history WHERE query_id = :qid"),
            {"qid": str(pre_generated_uuid)}
        )
        row = result.fetchone()

        assert row is not None
        assert str(row.query_id) == str(pre_generated_uuid)


@pytest.mark.asyncio
async def test_uuid_consistency_async():
    """CRITICAL: Test async wrapper UUID matches database entry.

    This is the bug that caused 404 errors on feedback submission.
    The async wrapper MUST return the same UUID that gets saved to DB.
    """
    user_id = str(uuid4())

    # Get UUID from async wrapper (returns immediately)
    returned_uuid = await save_query_to_history_async(
        user_id=user_id,
        question="Async UUID test",
        answer="Answer",
        response_source="semantic_cache",
        from_cache=True
    )

    assert returned_uuid is not None
    assert isinstance(returned_uuid, UUID)

    # Wait for background task to complete
    await asyncio.sleep(0.2)

    # Database entry MUST have the SAME UUID
    async with get_session() as session:
        result = await session.execute(
            text("SELECT query_id FROM query_history WHERE query_id = :qid"),
            {"qid": str(returned_uuid)}
        )
        row = result.fetchone()

        assert row is not None, (
            f"Query {returned_uuid} not found in database! "
            f"This is the UUID mismatch bug."
        )
        assert str(row.query_id) == str(returned_uuid)


@pytest.mark.asyncio
async def test_async_wrapper_is_fast():
    """Test that async wrapper returns quickly without blocking on DB insert."""
    import time

    user_id = str(uuid4())

    start = time.time()
    query_id = await save_query_to_history_async(
        user_id=user_id,
        question="Performance test",
        answer="Answer",
        response_source="claude_sonnet",
        from_cache=False
    )
    elapsed_ms = (time.time() - start) * 1000

    # Should return in < 5ms (fire-and-forget)
    assert elapsed_ms < 5, f"Async wrapper took {elapsed_ms:.1f}ms (should be <5ms)"

    # Wait for actual insert to complete
    await asyncio.sleep(0.2)

    # Verify entry was created
    async with get_session() as session:
        result = await session.execute(
            text("SELECT query_id FROM query_history WHERE query_id = :qid"),
            {"qid": str(query_id)}
        )
        row = result.fetchone()
        assert row is not None


@pytest.mark.asyncio
async def test_from_cache_field_accuracy():
    """Test that from_cache field is set correctly for both cache hits and misses."""
    user_id = str(uuid4())

    # Cache MISS
    miss_id = await save_query_to_history(
        user_id=user_id,
        question="Cache miss query",
        answer="Fresh answer",
        response_source="claude_sonnet",
        from_cache=False,
        cost_usd=0.001
    )

    # Cache HIT
    hit_id = await save_query_to_history_async(
        user_id=user_id,
        question="Cache hit query",
        answer="Cached answer",
        response_source="semantic_cache",
        from_cache=True,
        cost_usd=0.0
    )

    await asyncio.sleep(0.2)

    # Verify both entries have correct from_cache values
    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT query_id, from_cache, response_source, est_cost_usd
                FROM query_history
                WHERE query_id IN (:miss_id, :hit_id)
            """),
            {"miss_id": str(miss_id), "hit_id": str(hit_id)}
        )
        rows = {str(row.query_id): row for row in result.fetchall()}

    # Cache MISS entry
    assert str(miss_id) in rows
    assert rows[str(miss_id)].from_cache is False
    assert rows[str(miss_id)].est_cost_usd > 0

    # Cache HIT entry
    assert str(hit_id) in rows
    assert rows[str(hit_id)].from_cache is True
    assert rows[str(hit_id)].est_cost_usd == 0.0
