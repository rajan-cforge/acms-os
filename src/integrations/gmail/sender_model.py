# src/integrations/gmail/sender_model.py
"""
Sender Importance Model v1

Rule-based scoring system for email priority classification.
Score range: 0-100

Scoring Components:
- Reply frequency (30 pts max): How often user replies to this sender
- Recency (20 pts max): How recently user interacted with sender
- Domain trust (15 pts max): Same company domain bonus
- VIP status (25 pts max): Explicitly marked important
- Open rate (10 pts max): Historical email open behavior

Priority threshold: 60+ = priority email
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SenderScore:
    """Result of sender importance scoring."""
    sender_email: str
    score: int
    is_priority: bool
    factors: Dict[str, int]  # Breakdown of score components


class SenderImportanceModel:
    """
    Rule-based sender importance scoring model.

    Usage:
        model = SenderImportanceModel(db_pool)
        score = await model.score_sender("boss@company.com", "user@company.com")
        print(f"Priority: {score.is_priority}, Score: {score.score}")
    """

    # Score component maximums
    MAX_REPLY_SCORE = 30
    MAX_RECENCY_SCORE = 20
    MAX_DOMAIN_SCORE = 15
    MAX_VIP_SCORE = 25
    MAX_OPEN_SCORE = 10

    # Priority threshold
    priority_threshold = 60

    # Recency decay (days until interaction is considered "old")
    RECENCY_DECAY_DAYS = 30

    def __init__(self, db_pool=None):
        """
        Initialize the sender importance model.

        Args:
            db_pool: AsyncPG connection pool for database access
        """
        self.db_pool = db_pool

    # ==========================================
    # INDIVIDUAL SCORING FUNCTIONS
    # ==========================================

    def _calculate_reply_score(self, reply_rate: float) -> int:
        """
        Calculate score based on reply frequency.

        Args:
            reply_rate: Ratio of replies to total emails (0.0 to 1.0)

        Returns:
            Score from 0 to MAX_REPLY_SCORE
        """
        if reply_rate <= 0:
            return 0

        # Scale: 10% reply rate = 15 pts, 20%+ = 30 pts
        if reply_rate >= 0.20:
            return self.MAX_REPLY_SCORE
        elif reply_rate >= 0.10:
            return int(self.MAX_REPLY_SCORE * 0.75)
        elif reply_rate >= 0.05:
            return int(self.MAX_REPLY_SCORE * 0.5)
        else:
            return int(self.MAX_REPLY_SCORE * 0.25)

    def _calculate_recency_score(self, last_interaction: Optional[datetime]) -> int:
        """
        Calculate score based on recency of interaction.

        Args:
            last_interaction: Datetime of last interaction (or None)

        Returns:
            Score from 0 to MAX_RECENCY_SCORE
        """
        if last_interaction is None:
            return 5  # Neutral baseline for unknown senders

        now = datetime.now(timezone.utc)

        # Handle naive datetime
        if last_interaction.tzinfo is None:
            last_interaction = last_interaction.replace(tzinfo=timezone.utc)

        days_ago = (now - last_interaction).days

        if days_ago <= 1:
            return self.MAX_RECENCY_SCORE
        elif days_ago <= 7:
            return int(self.MAX_RECENCY_SCORE * 0.75)
        elif days_ago <= 14:
            return int(self.MAX_RECENCY_SCORE * 0.5)
        elif days_ago <= self.RECENCY_DECAY_DAYS:
            return int(self.MAX_RECENCY_SCORE * 0.25)
        else:
            return 0

    def _calculate_domain_score(
        self,
        sender_email: str,
        user_email: str
    ) -> int:
        """
        Calculate domain trust score.

        Args:
            sender_email: Sender's email address
            user_email: User's email address

        Returns:
            Score: MAX_DOMAIN_SCORE for same domain, 0 otherwise
        """
        try:
            sender_domain = sender_email.split("@")[1].lower()
            user_domain = user_email.split("@")[1].lower()

            if sender_domain == user_domain:
                return self.MAX_DOMAIN_SCORE
        except (IndexError, AttributeError):
            pass

        return 0

    def _calculate_vip_score(self, is_vip: bool) -> int:
        """
        Calculate VIP bonus score.

        Args:
            is_vip: Whether sender is marked as VIP

        Returns:
            MAX_VIP_SCORE if VIP, 0 otherwise
        """
        return self.MAX_VIP_SCORE if is_vip else 0

    def _calculate_open_score(self, open_rate: float) -> int:
        """
        Calculate score based on historical open rate.

        Args:
            open_rate: Ratio of opened emails to total (0.0 to 1.0)

        Returns:
            Score from 0 to MAX_OPEN_SCORE
        """
        if open_rate >= 0.90:
            return self.MAX_OPEN_SCORE
        elif open_rate >= 0.70:
            return int(self.MAX_OPEN_SCORE * 0.75)
        elif open_rate >= 0.50:
            return int(self.MAX_OPEN_SCORE * 0.5)
        elif open_rate >= 0.30:
            return int(self.MAX_OPEN_SCORE * 0.25)
        else:
            return 0

    # ==========================================
    # TOTAL SCORE CALCULATION
    # ==========================================

    def _calculate_total_score(
        self,
        reply_score: int,
        recency_score: int,
        domain_score: int,
        vip_score: int,
        open_score: int,
        is_muted: bool,
    ) -> int:
        """
        Calculate total importance score.

        Args:
            reply_score: Reply frequency score
            recency_score: Recency score
            domain_score: Domain trust score
            vip_score: VIP bonus score
            open_score: Open rate score
            is_muted: Whether sender is muted

        Returns:
            Total score (0-100), or 0 if muted
        """
        if is_muted:
            return 0

        total = reply_score + recency_score + domain_score + vip_score + open_score
        return min(max(total, 0), 100)

    def _is_priority(self, score: int) -> bool:
        """Check if score meets priority threshold."""
        return score >= self.priority_threshold

    # ==========================================
    # DATABASE OPERATIONS
    # ==========================================

    async def _get_sender_stats(
        self,
        sender_email: str,
        user_id: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """
        Get sender statistics from database.

        Args:
            sender_email: Sender's email address
            user_id: User ID (kept for API compatibility, not used in single-tenant schema)

        Returns:
            Dict with sender stats or None if not found
        """
        if not self.db_pool:
            return None

        # Match actual schema column names from 013_gmail_integration.sql
        query = """
            SELECT
                sender_email,
                total_emails_received as total_received,
                emails_replied_to as total_replied,
                emails_opened as total_opened,
                last_interaction_at as last_interaction,
                is_manually_prioritized as is_vip,
                is_manually_deprioritized as is_muted
            FROM sender_scores
            WHERE sender_email = $1
        """

        try:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(query, sender_email.lower())
                if row:
                    return dict(row)
        except Exception as e:
            logger.warning(f"Failed to get sender stats: {e}")

        return None

    async def _update_sender_score(
        self,
        sender_email: str,
        score: int,
        factors: Dict[str, int],
        user_id: str = "default"
    ) -> None:
        """
        Update sender score in database.

        Args:
            sender_email: Sender's email address
            score: Calculated importance score
            factors: Score component breakdown (not stored - schema doesn't have this column)
            user_id: User ID (kept for API compatibility, not used in single-tenant schema)
        """
        if not self.db_pool:
            return

        # Extract domain from email for required column
        sender_domain = sender_email.split("@")[1].lower() if "@" in sender_email else "unknown"

        # Match actual schema - no user_id, no score_breakdown
        query = """
            INSERT INTO sender_scores (
                sender_email, sender_domain, importance_score
            )
            VALUES ($1, $2, $3)
            ON CONFLICT (sender_email)
            DO UPDATE SET
                importance_score = $3,
                last_score_update_at = NOW()
        """

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    query,
                    sender_email.lower(),
                    sender_domain,
                    score,
                )
        except Exception as e:
            logger.warning(f"Failed to update sender score: {e}")

    async def _execute_query(
        self,
        query: str,
        *args
    ) -> None:
        """Execute a database query."""
        if not self.db_pool:
            return

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(query, *args)
        except Exception as e:
            logger.warning(f"Failed to execute query: {e}")

    # ==========================================
    # PUBLIC SCORING API
    # ==========================================

    async def score_sender(
        self,
        sender_email: str,
        user_email: str,
        user_id: str = "default"
    ) -> SenderScore:
        """
        Calculate importance score for a sender.

        Args:
            sender_email: Sender's email address
            user_email: User's email address (for domain comparison)
            user_id: User ID for multi-user support

        Returns:
            SenderScore with score and breakdown
        """
        sender_email = sender_email.lower()

        # Get sender stats from database
        stats = await self._get_sender_stats(sender_email, user_id)

        if stats:
            # Calculate component scores
            total_received = stats.get("total_received", 0) or 1
            reply_rate = (stats.get("total_replied", 0) or 0) / total_received
            open_rate = (stats.get("total_opened", 0) or 0) / total_received

            reply_score = self._calculate_reply_score(reply_rate)
            recency_score = self._calculate_recency_score(
                stats.get("last_interaction")
            )
            domain_score = self._calculate_domain_score(sender_email, user_email)
            vip_score = self._calculate_vip_score(stats.get("is_vip", False))
            open_score = self._calculate_open_score(open_rate)

            total = self._calculate_total_score(
                reply_score=reply_score,
                recency_score=recency_score,
                domain_score=domain_score,
                vip_score=vip_score,
                open_score=open_score,
                is_muted=stats.get("is_muted", False),
            )

            factors = {
                "reply": reply_score,
                "recency": recency_score,
                "domain": domain_score,
                "vip": vip_score,
                "open": open_score,
            }

        else:
            # New sender: baseline scoring
            domain_score = self._calculate_domain_score(sender_email, user_email)

            factors = {
                "reply": 0,
                "recency": 5,  # Neutral baseline
                "domain": domain_score,
                "vip": 0,
                "open": 0,
            }

            total = sum(factors.values())

        result = SenderScore(
            sender_email=sender_email,
            score=total,
            is_priority=self._is_priority(total),
            factors=factors,
        )

        # Update cache
        await self._update_sender_score(sender_email, total, factors, user_id)

        return result

    async def score_emails_batch(
        self,
        emails: List[Dict[str, Any]],
        user_email: str,
        user_id: str = "default"
    ) -> List[Dict[str, Any]]:
        """
        Score multiple emails efficiently.

        Args:
            emails: List of email dicts with sender_email and message_id
            user_email: User's email address
            user_id: User ID for multi-user support

        Returns:
            List of emails with added score info, sorted by score desc
        """
        results = []

        for email in emails:
            sender = email.get("sender_email", "")
            if not sender:
                continue

            score = await self.score_sender(sender, user_email, user_id)

            results.append({
                **email,
                "importance_score": score.score,
                "is_priority": score.is_priority,
                "score_factors": score.factors,
            })

        # Sort by score descending
        results.sort(key=lambda x: x.get("importance_score", 0), reverse=True)

        return results

    # ==========================================
    # VIP MANAGEMENT
    # ==========================================

    async def add_vip(
        self,
        sender_email: str,
        user_id: str = "default"
    ) -> None:
        """Mark sender as VIP (manually prioritized)."""
        sender_domain = sender_email.split("@")[1].lower() if "@" in sender_email else "unknown"
        query = """
            INSERT INTO sender_scores (sender_email, sender_domain, is_manually_prioritized)
            VALUES ($1, $2, TRUE)
            ON CONFLICT (sender_email)
            DO UPDATE SET is_manually_prioritized = TRUE
        """
        await self._execute_query(query, sender_email.lower(), sender_domain)

    async def remove_vip(
        self,
        sender_email: str,
        user_id: str = "default"
    ) -> None:
        """Remove VIP status from sender."""
        query = """
            UPDATE sender_scores
            SET is_manually_prioritized = FALSE
            WHERE sender_email = $1
        """
        await self._execute_query(query, sender_email.lower())

    async def mute_sender(
        self,
        sender_email: str,
        user_id: str = "default"
    ) -> None:
        """Mute a sender (sets score to 0)."""
        sender_domain = sender_email.split("@")[1].lower() if "@" in sender_email else "unknown"
        query = """
            INSERT INTO sender_scores (sender_email, sender_domain, is_manually_deprioritized, importance_score)
            VALUES ($1, $2, TRUE, 0)
            ON CONFLICT (sender_email)
            DO UPDATE SET is_manually_deprioritized = TRUE, importance_score = 0
        """
        await self._execute_query(query, sender_email.lower(), sender_domain)

    async def unmute_sender(
        self,
        sender_email: str,
        user_id: str = "default"
    ) -> None:
        """Unmute a sender."""
        query = """
            UPDATE sender_scores
            SET is_manually_deprioritized = FALSE
            WHERE sender_email = $1
        """
        await self._execute_query(query, sender_email.lower())


# Convenience function for standalone usage
def create_sender_model(db_pool=None) -> SenderImportanceModel:
    """Create a SenderImportanceModel instance."""
    return SenderImportanceModel(db_pool=db_pool)
