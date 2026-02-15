"""Knowledge Review Queue CRUD Operations.

Cognitive Principle: Active Forgetting with Human Oversight.

When a memory is determined to be unreliable (negative feedback, correction),
related memories are flagged for review rather than automatically deleted.
This mirrors how the hippocampus triggers re-consolidation of related memories
while requiring conscious verification for significant changes.

This module provides CRUD operations for the knowledge_review_queue table.

Usage:
    from src.storage.knowledge_review_crud import (
        flag_related_knowledge_for_review,
        get_pending_reviews,
        mark_reviewed,
    )

    # Flag an entry for review
    review_id = await flag_related_knowledge_for_review(
        entry_id="abc123",
        entry_collection="ACMS_Knowledge_v2",
        reason="Related cache entry was deleted",
        source_deletion_id="def456",
    )

    # Get pending reviews
    reviews = await get_pending_reviews(user_id="user1", limit=20)

    # Mark as reviewed
    await mark_reviewed(review_id, user_id="user1", status="approved")
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from uuid import uuid4, UUID

from sqlalchemy import text

from src.storage.database import get_session

logger = logging.getLogger(__name__)


async def flag_related_knowledge_for_review(
    entry_id: str,
    entry_collection: str,
    reason: str,
    source_deletion_id: str,
    priority: str = "medium",
    user_id: Optional[str] = None,
    similarity_to_deleted: Optional[float] = None,
    deleted_query: Optional[str] = None,
) -> Optional[str]:
    """
    Flag a knowledge entry for human review.

    Cognitive basis: When a memory is invalidated, semantically related
    memories should be reviewed for potential inconsistencies.

    Args:
        entry_id: ID of the knowledge entry to flag (Weaviate UUID)
        entry_collection: Collection name (ACMS_Knowledge_v2, ACMS_Raw_v1, etc.)
        reason: Human-readable reason for flagging
        source_deletion_id: ID of the entry whose deletion triggered this
        priority: Review priority (high/medium/low)
        user_id: User who owns the entry (for filtering)
        similarity_to_deleted: How similar this entry is to the deleted one
        deleted_query: The query text that was deleted (for context)

    Returns:
        UUID of the review queue entry, or None if failed
    """
    review_id = str(uuid4())

    try:
        async with get_session() as session:
            # Check if already flagged (avoid duplicates)
            existing = await session.execute(
                text("""
                    SELECT id FROM knowledge_review_queue
                    WHERE entry_id = :entry_id
                      AND entry_collection = :entry_collection
                      AND status = 'pending'
                    LIMIT 1
                """),
                {
                    "entry_id": entry_id,
                    "entry_collection": entry_collection,
                }
            )

            if existing.fetchone():
                logger.debug(f"Entry {entry_id} already flagged for review")
                return None

            # Insert new review queue entry
            await session.execute(
                text("""
                    INSERT INTO knowledge_review_queue (
                        id,
                        entry_id,
                        entry_collection,
                        reason,
                        source_deletion_id,
                        review_priority,
                        status,
                        user_id,
                        metadata,
                        created_at
                    ) VALUES (
                        :id,
                        :entry_id,
                        :entry_collection,
                        :reason,
                        :source_deletion_id,
                        :review_priority,
                        'pending',
                        :user_id,
                        :metadata,
                        NOW()
                    )
                """),
                {
                    "id": review_id,
                    "entry_id": entry_id,
                    "entry_collection": entry_collection,
                    "reason": reason,
                    "source_deletion_id": source_deletion_id,
                    "review_priority": priority,
                    "user_id": user_id,
                    "metadata": f'{{"similarity": {similarity_to_deleted or 0}, "deleted_query": "{(deleted_query or "")[:500]}"}}',
                }
            )

            await session.commit()

            logger.info(
                f"[KnowledgeReview] Flagged {entry_id[:8]}... in {entry_collection} "
                f"(priority={priority})"
            )

            return review_id

    except Exception as e:
        logger.error(f"[KnowledgeReview] Failed to flag entry: {e}", exc_info=True)
        return None


async def get_pending_reviews(
    user_id: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """
    Get pending review queue entries.

    Args:
        user_id: Filter by user (optional)
        priority: Filter by priority (high/medium/low, optional)
        limit: Maximum entries to return
        offset: Pagination offset

    Returns:
        List of review queue entries
    """
    try:
        async with get_session() as session:
            # Build query with optional filters
            query = """
                SELECT
                    id,
                    entry_id,
                    entry_collection,
                    reason,
                    source_deletion_id,
                    review_priority,
                    status,
                    user_id,
                    metadata,
                    created_at
                FROM knowledge_review_queue
                WHERE status = 'pending'
            """
            params = {}

            if user_id:
                query += " AND user_id = :user_id"
                params["user_id"] = user_id

            if priority:
                query += " AND review_priority = :priority"
                params["priority"] = priority

            # Order by priority (high first), then creation date
            query += """
                ORDER BY
                    CASE review_priority
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                        ELSE 4
                    END,
                    created_at DESC
                LIMIT :limit OFFSET :offset
            """
            params["limit"] = limit
            params["offset"] = offset

            result = await session.execute(text(query), params)
            rows = result.fetchall()

            return [
                {
                    "id": str(row.id),
                    "entry_id": row.entry_id,
                    "entry_collection": row.entry_collection,
                    "reason": row.reason,
                    "source_deletion_id": row.source_deletion_id,
                    "review_priority": row.review_priority,
                    "status": row.status,
                    "user_id": row.user_id,
                    "metadata": row.metadata,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                }
                for row in rows
            ]

    except Exception as e:
        logger.error(f"[KnowledgeReview] Failed to get pending reviews: {e}")
        return []


async def get_review_by_id(review_id: str) -> Optional[Dict[str, Any]]:
    """
    Get a single review queue entry by ID.

    Args:
        review_id: UUID of the review entry

    Returns:
        Dict with review data or None
    """
    try:
        async with get_session() as session:
            result = await session.execute(
                text("""
                    SELECT
                        id,
                        entry_id,
                        entry_collection,
                        reason,
                        source_deletion_id,
                        review_priority,
                        status,
                        user_id,
                        metadata,
                        reviewed_at,
                        reviewed_by,
                        created_at
                    FROM knowledge_review_queue
                    WHERE id = :id
                """),
                {"id": review_id}
            )
            row = result.fetchone()

            if not row:
                return None

            return {
                "id": str(row.id),
                "entry_id": row.entry_id,
                "entry_collection": row.entry_collection,
                "reason": row.reason,
                "source_deletion_id": row.source_deletion_id,
                "review_priority": row.review_priority,
                "status": row.status,
                "user_id": row.user_id,
                "metadata": row.metadata,
                "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
                "reviewed_by": str(row.reviewed_by) if row.reviewed_by else None,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }

    except Exception as e:
        logger.error(f"[KnowledgeReview] Failed to get review: {e}")
        return None


async def mark_reviewed(
    review_id: str,
    user_id: str,
    status: str,
    notes: Optional[str] = None,
) -> bool:
    """
    Mark a review queue entry as reviewed.

    Args:
        review_id: UUID of the review entry
        user_id: ID of the user who reviewed
        status: New status (approved/rejected/corrected)
        notes: Optional reviewer notes

    Returns:
        bool: True if updated successfully
    """
    if status not in ("approved", "rejected", "corrected"):
        logger.warning(f"Invalid review status: {status}")
        return False

    try:
        async with get_session() as session:
            await session.execute(
                text("""
                    UPDATE knowledge_review_queue
                    SET status = :status,
                        reviewed_at = NOW(),
                        reviewed_by = :reviewed_by,
                        reviewer_notes = :notes
                    WHERE id = :id
                """),
                {
                    "id": review_id,
                    "status": status,
                    "reviewed_by": user_id,
                    "notes": notes,
                }
            )
            await session.commit()

            logger.info(f"[KnowledgeReview] Marked {review_id[:8]}... as {status}")
            return True

    except Exception as e:
        logger.error(f"[KnowledgeReview] Failed to mark reviewed: {e}")
        return False


async def delete_entry_after_review(
    entry_id: str,
    entry_collection: str,
) -> bool:
    """
    Delete a knowledge entry after review approval.

    This is called when a reviewer confirms the entry should be deleted.
    The actual deletion from Weaviate is handled here.

    Args:
        entry_id: Weaviate UUID of the entry
        entry_collection: Collection name

    Returns:
        bool: True if deleted successfully
    """
    try:
        from src.storage.weaviate_client import WeaviateClient

        weaviate = WeaviateClient()
        weaviate.delete_by_id(entry_collection, entry_id)

        logger.info(f"[KnowledgeReview] Deleted {entry_id[:8]}... from {entry_collection}")
        return True

    except Exception as e:
        logger.error(f"[KnowledgeReview] Failed to delete entry: {e}")
        return False


async def get_review_stats(user_id: Optional[str] = None) -> Dict[str, int]:
    """
    Get review queue statistics.

    Args:
        user_id: Optional user filter

    Returns:
        Dict with counts by status and priority
    """
    try:
        async with get_session() as session:
            query = """
                SELECT
                    status,
                    review_priority,
                    COUNT(*) as count
                FROM knowledge_review_queue
            """
            params = {}

            if user_id:
                query += " WHERE user_id = :user_id"
                params["user_id"] = user_id

            query += " GROUP BY status, review_priority"

            result = await session.execute(text(query), params)
            rows = result.fetchall()

            stats = {
                "total": 0,
                "pending": 0,
                "approved": 0,
                "rejected": 0,
                "corrected": 0,
                "high_priority": 0,
                "medium_priority": 0,
                "low_priority": 0,
            }

            for row in rows:
                stats["total"] += row.count
                status_key = row.status if row.status in stats else "pending"
                stats[status_key] += row.count

                if row.status == "pending":
                    priority_key = f"{row.review_priority}_priority"
                    if priority_key in stats:
                        stats[priority_key] += row.count

            return stats

    except Exception as e:
        logger.error(f"[KnowledgeReview] Failed to get stats: {e}")
        return {"total": 0, "pending": 0}


async def cleanup_old_reviews(days_old: int = 30) -> int:
    """
    Clean up old reviewed entries.

    Removes entries that have been reviewed more than N days ago.
    Keeps a history for audit purposes but cleans up eventually.

    Args:
        days_old: Delete entries older than this many days

    Returns:
        int: Number of entries deleted
    """
    try:
        async with get_session() as session:
            result = await session.execute(
                text("""
                    DELETE FROM knowledge_review_queue
                    WHERE status != 'pending'
                      AND reviewed_at < NOW() - INTERVAL ':days days'
                    RETURNING id
                """.replace(":days", str(days_old)))
            )
            deleted = len(result.fetchall())
            await session.commit()

            logger.info(f"[KnowledgeReview] Cleaned up {deleted} old reviews")
            return deleted

    except Exception as e:
        logger.error(f"[KnowledgeReview] Failed to cleanup: {e}")
        return 0
