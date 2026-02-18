"""CRUD operations for query_history table.

Supports feedback on both cached and fresh responses by logging all queries.
"""

import asyncio
import json
import logging
from uuid import UUID, uuid4
from typing import Optional, Dict, Any
from sqlalchemy import text
from src.storage.database import get_session

logger = logging.getLogger(__name__)


async def save_query_to_history(
    user_id: str,
    question: str,
    answer: str,
    response_source: str,
    from_cache: bool,
    query_id: Optional[UUID] = None,  # NEW: Accept pre-generated ID
    confidence: float = 0.9,
    cost_usd: float = 0.0,
    context_limit: int = 10,
    latency_ms: int = 0,
    metadata: Optional[Dict[str, Any]] = None
) -> UUID:
    """
    Save query to history for both cached and fresh responses.

    Pre-generates UUID so caller gets immediate query_id.
    Actual DB insert can be made async for performance.

    Args:
        user_id: User identifier
        question: Original user query
        answer: Response text
        response_source: Agent name (e.g., 'claude_sonnet', 'semantic_cache')
        from_cache: Whether response came from cache
        query_id: Pre-generated UUID (if None, generates new one)
        confidence: Response confidence score
        cost_usd: Estimated cost (0.0 for cached responses)
        context_limit: Number of memories used
        latency_ms: Total latency in milliseconds
        metadata: Additional JSONB metadata

    Returns:
        UUID: query_id for this entry (can be used immediately for feedback)
    """
    if query_id is None:
        query_id = uuid4()

    try:
        # Build metadata with extra fields that aren't in the schema
        full_metadata = metadata or {}
        full_metadata["context_limit"] = context_limit
        full_metadata["est_cost_usd"] = cost_usd

        async with get_session() as session:
            await session.execute(
                text("""
                    INSERT INTO query_history (
                        query_id, user_id, query_text, response_text,
                        response_source, from_cache, confidence_score,
                        latency_ms, metadata, created_at
                    )
                    VALUES (
                        :query_id, :user_id, :query_text, :response_text,
                        :response_source, :from_cache, :confidence_score,
                        :latency_ms, :metadata, NOW()
                    )
                """),
                {
                    "query_id": str(query_id),
                    "user_id": user_id,
                    "query_text": question,
                    "response_text": answer,
                    "response_source": response_source,
                    "from_cache": from_cache,
                    "confidence_score": confidence,
                    "latency_ms": float(latency_ms),
                    "metadata": json.dumps(full_metadata)
                }
            )
            await session.commit()

        logger.info(
            f"[QUERY_HISTORY] Saved | "
            f"query_id={query_id} | "
            f"from_cache={from_cache} | "
            f"source={response_source} | "
            f"cost=${cost_usd:.4f} | "
            f"latency={latency_ms}ms"
        )

    except Exception as e:
        logger.error(f"[QUERY_HISTORY] Save error: {e}", exc_info=True)
        # Non-critical error - don't fail the request
        # query_id is still valid for feedback (will be in DB shortly)

    return query_id


async def save_query_to_history_async(
    user_id: str,
    question: str,
    answer: str,
    response_source: str,
    from_cache: bool,
    **kwargs
) -> UUID:
    """
    Async fire-and-forget wrapper for query_history saves.

    Returns query_id immediately without waiting for DB insert.
    Reduces latency impact on cached responses from 5-10ms to <1ms.

    Use for cache hits where latency is critical.
    For cache misses, use save_query_to_history() directly (latency less critical).

    Args:
        Same as save_query_to_history()

    Returns:
        UUID: query_id (usable immediately, DB insert happens in background)
    """
    query_id = uuid4()

    # Fire and forget - insert happens in background
    # IMPORTANT: Pass query_id so the same UUID is used in DB
    asyncio.create_task(
        save_query_to_history(
            user_id=user_id,
            question=question,
            answer=answer,
            response_source=response_source,
            from_cache=from_cache,
            query_id=query_id,  # Pass the pre-generated ID
            **kwargs
        )
    )

    logger.debug(f"[QUERY_HISTORY] Async save initiated: {query_id}")

    return query_id
