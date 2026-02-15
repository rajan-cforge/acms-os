"""
Feedback Promoter - Connects user feedback to cache quality.

When user gives 👍:
1. Record positive feedback (existing)
2. Offer to "Save as verified knowledge" (NEW)
3. If accepted, promote to QualityCache (NEW)

When user gives 👎:
1. Record negative feedback (existing)
2. Demote from QualityCache if cached (NEW)
3. Flag for review (NEW)

Part of Active Second Brain implementation (Jan 2026).
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, Literal

from src.cache.quality_cache import QualityCache, get_query_history_by_id
from src.storage.database import get_session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class FeedbackReason(Enum):
    """Reasons for negative feedback."""
    INCORRECT = "incorrect"        # Factually wrong
    OUTDATED = "outdated"          # Information is old
    INCOMPLETE = "incomplete"      # Missing key details
    WRONG_AGENT = "wrong_agent"    # Got different agent than requested
    TOO_LONG = "too_long"          # Response too verbose
    TOO_SHORT = "too_short"        # Response too brief
    OFF_TOPIC = "off_topic"        # Didn't answer the question
    OTHER = "other"                # Free text


@dataclass
class DetailedFeedback:
    """
    Detailed feedback data structure.

    Stores both the feedback type and optional reason/text.
    """
    query_history_id: str
    feedback_type: Literal["positive", "negative"]
    reason: Optional[FeedbackReason]
    reason_text: Optional[str]  # For "other" or additional context
    save_as_verified: bool
    created_at: datetime


class FeedbackPromoter:
    """
    Connects user feedback to cache quality.

    Handles:
    - Recording feedback in database
    - Promoting to QualityCache on positive + save
    - Demoting from QualityCache on negative
    - Analytics on feedback patterns
    """

    def __init__(self):
        """Initialize FeedbackPromoter."""
        self.quality_cache = QualityCache()
        logger.info("FeedbackPromoter initialized")

    async def handle_positive_feedback(
        self,
        query_history_id: str,
        user_id: str,
        save_as_verified: bool = False
    ) -> Dict[str, Any]:
        """
        Handle 👍 feedback with optional knowledge save.

        Args:
            query_history_id: ID of the query_history record
            user_id: User ID
            save_as_verified: Whether user wants to save as verified

        Returns:
            Dict with feedback_recorded, promoted_to_cache, knowledge_id
        """
        result = {
            "feedback_recorded": False,
            "promoted_to_cache": False,
            "knowledge_id": None
        }

        try:
            # Record feedback in database
            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO user_feedback
                        (query_history_id, user_id, feedback_type, created_at)
                        VALUES (:query_id, :user_id, 'positive', :created_at)
                        ON CONFLICT (query_history_id, user_id) DO UPDATE
                        SET feedback_type = 'positive', updated_at = :created_at
                    """),
                    {
                        "query_id": query_history_id,
                        "user_id": user_id,
                        "created_at": datetime.now(timezone.utc)
                    }
                )
                await session.commit()

            result["feedback_recorded"] = True
            logger.info(f"Recorded positive feedback for {query_history_id}")

            # Promote to cache if user wants to save
            if save_as_verified:
                promoted = await self.quality_cache.promote_to_cache(
                    query_history_id, user_id
                )
                result["promoted_to_cache"] = promoted

                if promoted:
                    logger.info(f"Promoted {query_history_id} to QualityCache")

        except Exception as e:
            logger.error(f"Failed to handle positive feedback: {e}", exc_info=True)

        return result

    async def handle_negative_feedback(
        self,
        query_history_id: str,
        user_id: str,
        reason: Optional[FeedbackReason] = None,
        reason_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle 👎 feedback with cache demotion.

        Args:
            query_history_id: ID of the query_history record
            user_id: User ID
            reason: Reason for negative feedback
            reason_text: Additional context (for "other")

        Returns:
            Dict with feedback_recorded, demoted_from_cache
        """
        result = {
            "feedback_recorded": False,
            "demoted_from_cache": False
        }

        try:
            reason_value = reason.value if reason else None

            # Record feedback in database
            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO user_feedback
                        (query_history_id, user_id, feedback_type, reason, reason_text, created_at)
                        VALUES (:query_id, :user_id, 'negative', :reason, :reason_text, :created_at)
                        ON CONFLICT (query_history_id, user_id) DO UPDATE
                        SET feedback_type = 'negative',
                            reason = :reason,
                            reason_text = :reason_text,
                            updated_at = :created_at
                    """),
                    {
                        "query_id": query_history_id,
                        "user_id": user_id,
                        "reason": reason_value,
                        "reason_text": reason_text,
                        "created_at": datetime.now(timezone.utc)
                    }
                )
                await session.commit()

            result["feedback_recorded"] = True
            logger.info(f"Recorded negative feedback for {query_history_id}: {reason_value}")

            # Check if this query was served from cache
            cache_entry = await find_cache_entry_for_query(query_history_id)
            if cache_entry:
                # Demote from cache
                demoted = await self.quality_cache.demote_from_cache(
                    cache_entry["id"],
                    reason_value or "negative_feedback"
                )
                result["demoted_from_cache"] = demoted

                if demoted:
                    logger.info(f"Demoted cache entry {cache_entry['id']}")

        except Exception as e:
            logger.error(f"Failed to handle negative feedback: {e}", exc_info=True)

        return result

    async def get_feedback_summary(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get summary of feedback for analytics.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            Dict with feedback counts by type and reason
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT
                            feedback_type,
                            reason,
                            COUNT(*) as count
                        FROM user_feedback
                        WHERE user_id = :user_id
                        AND created_at > NOW() - INTERVAL ':days days'
                        GROUP BY feedback_type, reason
                        ORDER BY count DESC
                    """),
                    {"user_id": user_id, "days": days}
                )
                rows = result.fetchall()

                summary = {
                    "positive_count": 0,
                    "negative_count": 0,
                    "reasons": {}
                }

                for row in rows:
                    if row.feedback_type == "positive":
                        summary["positive_count"] += row.count
                    else:
                        summary["negative_count"] += row.count
                        if row.reason:
                            summary["reasons"][row.reason] = row.count

                return summary

        except Exception as e:
            logger.error(f"Failed to get feedback summary: {e}", exc_info=True)
            return {}

    async def is_eligible_for_promotion(
        self,
        query_history_id: str,
        user_id: str
    ) -> bool:
        """
        Check if a query is eligible for cache promotion.

        Conditions:
        - Not already in cache
        - Privacy level is PUBLIC or INTERNAL
        - Query exists in history

        Args:
            query_history_id: ID of the query_history record
            user_id: User ID

        Returns:
            bool: True if eligible for promotion
        """
        try:
            # Get query details
            query_record = await get_query_history_by_id(query_history_id)
            if not query_record:
                return False

            # Check privacy
            privacy = query_record.get("privacy_level", "PUBLIC")
            if privacy in ("CONFIDENTIAL", "LOCAL_ONLY"):
                return False

            # Check if already in cache
            existing = await self.quality_cache.get(
                query_record["query"],
                user_id
            )
            if existing:
                return False  # Already cached

            return True

        except Exception as e:
            logger.error(f"Failed to check promotion eligibility: {e}", exc_info=True)
            return False


async def find_cache_entry_for_query(query_history_id: str) -> Optional[Dict[str, Any]]:
    """
    Find cache entry that originated from a query history record.

    Args:
        query_history_id: ID of the query_history record

    Returns:
        Dict with cache entry data or None
    """
    # TODO: Implement lookup by original_query_id in Weaviate
    # For now, return None (query not served from cache)
    return None


# Global instance
_feedback_promoter_instance: Optional[FeedbackPromoter] = None


def get_feedback_promoter() -> FeedbackPromoter:
    """Get global FeedbackPromoter instance."""
    global _feedback_promoter_instance
    if _feedback_promoter_instance is None:
        _feedback_promoter_instance = FeedbackPromoter()
    return _feedback_promoter_instance
