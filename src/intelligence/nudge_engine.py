"""
Nudge Engine - Proactive "Tap on Shoulder" notifications.

Generates intelligent nudges when:
- New relevant facts are learned
- Knowledge becomes stale
- Low-confidence items need review
- Insights are available

Part of Active Second Brain implementation (Jan 2026).
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Dict, Any, List

from src.storage.weaviate_client import WeaviateClient
from src.storage.database import get_session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class NudgeType(Enum):
    """Types of nudges the system can generate."""
    NEW_LEARNING = "new_learning"               # New fact learned
    STALE_KNOWLEDGE = "stale_knowledge"         # Old info needs review
    LOW_CONFIDENCE = "low_confidence"           # Uncertain item needs verification
    CORRECTION_SUGGESTED = "correction_suggested"  # System suggests edit
    REVIEW_REMINDER = "review_reminder"         # Periodic review prompt
    INSIGHT_AVAILABLE = "insight_available"     # Cross-source insight ready


class NudgePriority(Enum):
    """Priority levels for nudges."""
    HIGH = "high"       # Immediate attention (errors, conflicts)
    MEDIUM = "medium"   # Normal notifications
    LOW = "low"         # Background reminders


@dataclass
class Nudge:
    """
    Represents a proactive notification to the user.

    Nudges can be dismissed, snoozed, or expire automatically.
    """
    id: str
    user_id: str
    nudge_type: NudgeType
    title: str
    message: str
    priority: NudgePriority
    related_id: Optional[str]  # ID of related knowledge/insight
    created_at: datetime
    expires_at: Optional[datetime]
    dismissed: bool
    snoozed_until: Optional[datetime]

    def is_active(self) -> bool:
        """Check if nudge should be shown to user."""
        if self.dismissed:
            return False

        now = datetime.now(timezone.utc)

        # Check if snoozed
        if self.snoozed_until and self.snoozed_until > now:
            return False

        # Check if expired
        if self.expires_at and self.expires_at < now:
            return False

        return True


class NudgeEngine:
    """
    Generates and manages proactive nudges.

    Features:
    - Create nudges for various events
    - Respect user preferences (max daily, quiet hours)
    - Priority-based sorting
    - Snooze and dismiss functionality
    - Automatic stale knowledge detection
    """

    KNOWLEDGE_COLLECTION = "ACMS_Knowledge_v2"
    DEFAULT_MAX_DAILY = 10

    def __init__(self):
        """Initialize NudgeEngine."""
        self.max_daily_nudges = self.DEFAULT_MAX_DAILY
        logger.info("NudgeEngine initialized")

    async def create_nudge(
        self,
        user_id: str,
        nudge_type: NudgeType,
        title: str,
        message: str,
        priority: NudgePriority = NudgePriority.MEDIUM,
        related_id: Optional[str] = None,
        expires_at: Optional[datetime] = None
    ) -> Optional[Nudge]:
        """
        Create a new nudge for the user.

        Args:
            user_id: User to nudge
            nudge_type: Type of nudge
            title: Short title
            message: Full message
            priority: Priority level
            related_id: Optional related knowledge/insight ID
            expires_at: Optional expiration time

        Returns:
            Created Nudge or None if limit exceeded
        """
        try:
            # Check daily limit
            if not await self.can_create_nudge(user_id):
                logger.info(f"Daily nudge limit reached for {user_id}")
                return None

            nudge_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            nudge = Nudge(
                id=nudge_id,
                user_id=user_id,
                nudge_type=nudge_type,
                title=title,
                message=message,
                priority=priority,
                related_id=related_id,
                created_at=now,
                expires_at=expires_at,
                dismissed=False,
                snoozed_until=None
            )

            # Persist to database
            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO nudges
                        (id, user_id, nudge_type, title, message, priority,
                         related_id, created_at, expires_at, dismissed, snoozed_until)
                        VALUES (:id, :user_id, :nudge_type, :title, :message, :priority,
                                :related_id, :created_at, :expires_at, :dismissed, :snoozed_until)
                    """),
                    {
                        "id": nudge_id,
                        "user_id": user_id,
                        "nudge_type": nudge_type.value,
                        "title": title,
                        "message": message,
                        "priority": priority.value,
                        "related_id": related_id,
                        "created_at": now,
                        "expires_at": expires_at,
                        "dismissed": False,
                        "snoozed_until": None
                    }
                )
                await session.commit()

            logger.info(f"Created nudge {nudge_id} for {user_id}: {nudge_type.value}")
            return nudge

        except Exception as e:
            logger.error(f"Failed to create nudge: {e}", exc_info=True)
            return None

    async def get_active_nudges(
        self,
        user_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get active nudges for a user, sorted by priority.

        Args:
            user_id: User ID
            limit: Maximum nudges to return

        Returns:
            List of nudge dictionaries
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT id, user_id, nudge_type, title, message, priority,
                               related_id, created_at, expires_at, dismissed, snoozed_until
                        FROM nudges
                        WHERE user_id = :user_id
                        AND dismissed = false
                        AND (snoozed_until IS NULL OR snoozed_until < NOW())
                        AND (expires_at IS NULL OR expires_at > NOW())
                        ORDER BY
                            CASE priority
                                WHEN 'high' THEN 1
                                WHEN 'medium' THEN 2
                                WHEN 'low' THEN 3
                            END,
                            created_at DESC
                        LIMIT :limit
                    """),
                    {"user_id": user_id, "limit": limit}
                )
                rows = result.fetchall()

                nudges = []
                for row in rows:
                    nudges.append({
                        "id": row.id,
                        "user_id": row.user_id,
                        "nudge_type": row.nudge_type,
                        "title": row.title,
                        "message": row.message,
                        "priority": row.priority,
                        "related_id": row.related_id,
                        "created_at": row.created_at,
                        "expires_at": row.expires_at,
                        "dismissed": row.dismissed,
                        "snoozed_until": row.snoozed_until
                    })

                return nudges

        except Exception as e:
            logger.error(f"Failed to get active nudges: {e}", exc_info=True)
            return []

    async def dismiss_nudge(
        self,
        nudge_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Dismiss a nudge permanently.

        Args:
            nudge_id: Nudge ID to dismiss
            user_id: User ID (for ownership verification)

        Returns:
            Dict with success status
        """
        result = {"success": False}

        try:
            async with get_session() as session:
                await session.execute(
                    text("""
                        UPDATE nudges
                        SET dismissed = true, dismissed_at = :dismissed_at
                        WHERE id = :id AND user_id = :user_id
                    """),
                    {
                        "id": nudge_id,
                        "user_id": user_id,
                        "dismissed_at": datetime.now(timezone.utc)
                    }
                )
                await session.commit()

            result["success"] = True
            logger.info(f"Dismissed nudge {nudge_id}")

        except Exception as e:
            logger.error(f"Failed to dismiss nudge: {e}", exc_info=True)
            result["error"] = str(e)

        return result

    async def snooze_nudge(
        self,
        nudge_id: str,
        user_id: str,
        duration: timedelta
    ) -> Dict[str, Any]:
        """
        Snooze a nudge for a specified duration.

        Args:
            nudge_id: Nudge ID to snooze
            user_id: User ID (for ownership verification)
            duration: How long to snooze

        Returns:
            Dict with success status and snoozed_until
        """
        result = {"success": False, "snoozed_until": None}

        try:
            snoozed_until = datetime.now(timezone.utc) + duration

            async with get_session() as session:
                await session.execute(
                    text("""
                        UPDATE nudges
                        SET snoozed_until = :snoozed_until
                        WHERE id = :id AND user_id = :user_id
                    """),
                    {
                        "id": nudge_id,
                        "user_id": user_id,
                        "snoozed_until": snoozed_until
                    }
                )
                await session.commit()

            result["success"] = True
            result["snoozed_until"] = snoozed_until
            logger.info(f"Snoozed nudge {nudge_id} until {snoozed_until}")

        except Exception as e:
            logger.error(f"Failed to snooze nudge: {e}", exc_info=True)
            result["error"] = str(e)

        return result

    async def generate_stale_knowledge_nudges(
        self,
        user_id: str,
        stale_days: int = 90
    ) -> int:
        """
        Generate nudges for knowledge items not updated recently.

        Args:
            user_id: User ID
            stale_days: Days without update to consider stale

        Returns:
            Number of nudges generated
        """
        count = 0

        try:
            weaviate = WeaviateClient()

            # Query for stale items
            cutoff = datetime.now(timezone.utc) - timedelta(days=stale_days)
            stale_items = weaviate.query_collection(
                self.KNOWLEDGE_COLLECTION,
                filters={
                    "user_id": user_id,
                    "last_updated_lt": cutoff.isoformat()
                },
                limit=10
            )

            for item in stale_items:
                nudge = await self.create_nudge(
                    user_id=user_id,
                    nudge_type=NudgeType.STALE_KNOWLEDGE,
                    title="Knowledge may be outdated",
                    message=f"'{item['content'][:50]}...' hasn't been verified in {stale_days}+ days",
                    priority=NudgePriority.LOW,
                    related_id=item["id"],
                    expires_at=datetime.now(timezone.utc) + timedelta(days=7)
                )
                if nudge:
                    count += 1

            logger.info(f"Generated {count} stale knowledge nudges for {user_id}")

        except Exception as e:
            logger.error(f"Failed to generate stale nudges: {e}", exc_info=True)

        return count

    async def get_nudge_counts(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Get count of active nudges by type.

        Args:
            user_id: User ID

        Returns:
            Dict with total and by_type counts
        """
        result = {"total": 0, "by_type": {}}

        try:
            async with get_session() as session:
                query_result = await session.execute(
                    text("""
                        SELECT nudge_type, COUNT(*) as count
                        FROM nudges
                        WHERE user_id = :user_id
                        AND dismissed = false
                        AND (snoozed_until IS NULL OR snoozed_until < NOW())
                        AND (expires_at IS NULL OR expires_at > NOW())
                        GROUP BY nudge_type
                    """),
                    {"user_id": user_id}
                )
                rows = query_result.fetchall()

                for row in rows:
                    result["by_type"][row.nudge_type] = row.count
                    result["total"] += row.count

        except Exception as e:
            logger.error(f"Failed to get nudge counts: {e}", exc_info=True)

        return result

    async def can_create_nudge(
        self,
        user_id: str
    ) -> bool:
        """
        Check if user can receive more nudges today.

        Args:
            user_id: User ID

        Returns:
            True if under daily limit
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT COUNT(*) as count
                        FROM nudges
                        WHERE user_id = :user_id
                        AND created_at > NOW() - INTERVAL '1 day'
                    """),
                    {"user_id": user_id}
                )
                count = result.scalar()

                return count < self.max_daily_nudges

        except Exception as e:
            logger.error(f"Failed to check nudge limit: {e}", exc_info=True)
            return False


# Global instance
_engine_instance: Optional[NudgeEngine] = None


def get_nudge_engine() -> NudgeEngine:
    """Get global NudgeEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = NudgeEngine()
    return _engine_instance
