# src/integrations/gmail/sync_service.py
"""
Gmail History Sync Service

Builds sender importance data from email history:
- Analyzes Sent folder for reply patterns
- Tracks read/unread patterns per sender
- Updates sender_scores table for accurate priority scoring

Usage:
    sync = GmailSyncService(db_pool, oauth_client)
    stats = await sync.sync_full_history(max_emails=500)
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from collections import defaultdict

logger = logging.getLogger(__name__)


class GmailSyncService:
    """
    Service for syncing Gmail data to build sender importance scores.
    """

    def __init__(self, db_pool, oauth_client):
        """
        Initialize sync service.

        Args:
            db_pool: AsyncPG database pool
            oauth_client: GoogleOAuthClient instance
        """
        self.db_pool = db_pool
        self.oauth = oauth_client

    async def sync_full_history(
        self,
        user_id: str = "default",
        max_sent: int = 500,
        max_inbox: int = 500,
    ) -> Dict[str, Any]:
        """
        Perform full historical sync to build sender importance data.

        Analyzes:
        1. Sent emails → who user replies to (reply frequency)
        2. Inbox emails → read/unread patterns (open rate)

        Args:
            user_id: User ID for multi-user support
            max_sent: Maximum sent emails to analyze
            max_inbox: Maximum inbox emails to analyze

        Returns:
            Dict with sync statistics
        """
        from .client import GmailClient

        logger.info(f"[GmailSync] Starting full history sync for user {user_id}")

        stats = {
            "sent_analyzed": 0,
            "inbox_analyzed": 0,
            "senders_updated": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "user_email": None,
        }

        try:
            # Get user email
            tokens = await self.oauth._load_tokens(user_id)
            if not tokens:
                return {"error": "Not authenticated", **stats}

            stats["user_email"] = tokens.email

            async with GmailClient(self.oauth, user_id) as gmail:
                # Step 1: Analyze sent emails for reply patterns
                sender_stats = defaultdict(lambda: {
                    "total_received": 0,
                    "total_replied": 0,
                    "total_opened": 0,
                    "last_interaction": None,
                })

                # Get sent emails (these are replies)
                logger.info(f"[GmailSync] Fetching sent emails...")
                sent_result = await gmail.list_messages(
                    max_results=max_sent,
                    label_ids=["SENT"],
                )

                sent_messages = sent_result.get("messages", [])
                stats["sent_analyzed"] = len(sent_messages)

                # Extract recipients from sent emails
                for msg in sent_messages:
                    try:
                        detail = await gmail.get_message(
                            msg["id"],
                            format="metadata",
                            metadata_headers=["To", "Date"],
                        )
                        headers = {
                            h["name"].lower(): h["value"]
                            for h in detail.get("payload", {}).get("headers", [])
                        }

                        # Parse recipients
                        to_header = headers.get("to", "")
                        recipients = self._parse_recipients(to_header)

                        for recipient in recipients:
                            sender_stats[recipient]["total_replied"] += 1
                            # Update last interaction
                            msg_date = self._parse_date(headers.get("date"))
                            if msg_date:
                                current = sender_stats[recipient]["last_interaction"]
                                if not current or msg_date > current:
                                    sender_stats[recipient]["last_interaction"] = msg_date

                    except Exception as e:
                        logger.warning(f"[GmailSync] Error processing sent msg {msg['id']}: {e}")
                        continue

                # Step 2: Analyze inbox emails for received/read patterns
                logger.info(f"[GmailSync] Fetching inbox emails...")
                inbox_result = await gmail.list_messages(
                    max_results=max_inbox,
                    label_ids=["INBOX"],
                )

                inbox_messages = inbox_result.get("messages", [])
                stats["inbox_analyzed"] = len(inbox_messages)

                for msg in inbox_messages:
                    try:
                        detail = await gmail.get_message(
                            msg["id"],
                            format="metadata",
                            metadata_headers=["From", "Date"],
                        )
                        headers = {
                            h["name"].lower(): h["value"]
                            for h in detail.get("payload", {}).get("headers", [])
                        }
                        labels = detail.get("labelIds", [])

                        # Parse sender
                        from_header = headers.get("from", "")
                        sender_email = GmailClient._parse_email_address(from_header)

                        if sender_email:
                            sender_stats[sender_email]["total_received"] += 1

                            # Track if read
                            if "UNREAD" not in labels:
                                sender_stats[sender_email]["total_opened"] += 1

                            # Update last interaction
                            msg_date = self._parse_date(headers.get("date"))
                            if msg_date:
                                current = sender_stats[sender_email]["last_interaction"]
                                if not current or msg_date > current:
                                    sender_stats[sender_email]["last_interaction"] = msg_date

                    except Exception as e:
                        logger.warning(f"[GmailSync] Error processing inbox msg {msg['id']}: {e}")
                        continue

                # Step 3: Update sender_scores table
                logger.info(f"[GmailSync] Updating {len(sender_stats)} sender scores...")
                updated = await self._update_sender_scores(sender_stats, user_id)
                stats["senders_updated"] = updated

            stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            stats["success"] = True
            logger.info(f"[GmailSync] Full sync complete: {stats}")
            return stats

        except Exception as e:
            logger.error(f"[GmailSync] Full sync failed: {e}")
            stats["error"] = str(e)
            stats["success"] = False
            return stats

    async def sync_incremental(
        self,
        user_id: str = "default",
        max_emails: int = 50,
    ) -> Dict[str, Any]:
        """
        Incremental sync - check recent emails for updates.

        Args:
            user_id: User ID
            max_emails: Max recent emails to check

        Returns:
            Dict with sync stats
        """
        from .client import GmailClient

        logger.info(f"[GmailSync] Starting incremental sync")

        stats = {
            "emails_checked": 0,
            "senders_updated": 0,
        }

        try:
            async with GmailClient(self.oauth, user_id) as gmail:
                # Just check recent inbox
                result = await gmail.list_messages(
                    max_results=max_emails,
                    label_ids=["INBOX"],
                )

                messages = result.get("messages", [])
                stats["emails_checked"] = len(messages)

                sender_stats = defaultdict(lambda: {
                    "total_received": 0,
                    "total_replied": 0,
                    "total_opened": 0,
                    "last_interaction": None,
                })

                for msg in messages:
                    try:
                        detail = await gmail.get_message(
                            msg["id"],
                            format="metadata",
                            metadata_headers=["From"],
                        )
                        headers = {
                            h["name"].lower(): h["value"]
                            for h in detail.get("payload", {}).get("headers", [])
                        }
                        labels = detail.get("labelIds", [])

                        sender_email = GmailClient._parse_email_address(
                            headers.get("from", "")
                        )

                        if sender_email:
                            sender_stats[sender_email]["total_received"] += 1
                            if "UNREAD" not in labels:
                                sender_stats[sender_email]["total_opened"] += 1

                    except Exception as e:
                        continue

                # Update scores (merge with existing)
                updated = await self._update_sender_scores(
                    sender_stats, user_id, merge=True
                )
                stats["senders_updated"] = updated

            return stats

        except Exception as e:
            logger.error(f"[GmailSync] Incremental sync failed: {e}")
            return {"error": str(e), **stats}

    async def sync_email_metadata(
        self,
        user_id: str = "default",
        max_emails: int = 100,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Sync email metadata to email_metadata table for insight extraction.

        Phase 1.5: Required for EmailInsightExtractor to have data.

        Args:
            user_id: User ID
            max_emails: Max emails to sync
            days: Number of days of history

        Returns:
            Dict with sync stats
        """
        from .client import GmailClient
        from datetime import timedelta

        logger.info(f"[GmailSync] Syncing email metadata (last {days} days, max {max_emails})")

        stats = {
            "emails_synced": 0,
            "emails_skipped": 0,
            "errors": 0,
        }

        try:
            # Calculate date filter
            after_date = datetime.now(timezone.utc) - timedelta(days=days)
            after_query = after_date.strftime("%Y/%m/%d")

            async with GmailClient(self.oauth, user_id) as gmail:
                # Fetch inbox emails
                result = await gmail.list_messages(
                    max_results=max_emails,
                    label_ids=["INBOX"],
                    query=f"after:{after_query}",
                )

                messages = result.get("messages", [])
                logger.info(f"[GmailSync] Found {len(messages)} emails to sync")

                for msg in messages:
                    try:
                        detail = await gmail.get_message(
                            msg["id"],
                            format="metadata",
                            metadata_headers=["From", "Subject", "Date"],
                        )

                        headers = {
                            h["name"].lower(): h["value"]
                            for h in detail.get("payload", {}).get("headers", [])
                        }
                        labels = detail.get("labelIds", [])

                        # Parse sender
                        from_header = headers.get("from", "")
                        sender_email = GmailClient._parse_email_address(from_header)
                        sender_name = GmailClient._parse_sender_name(from_header)

                        # Parse date
                        received_at = self._parse_date(headers.get("date")) or datetime.now(timezone.utc)

                        # Insert into email_metadata
                        async with self.db_pool.acquire() as conn:
                            await conn.execute("""
                                INSERT INTO email_metadata (
                                    gmail_message_id, gmail_thread_id,
                                    sender_email, sender_name,
                                    subject, snippet,
                                    received_at, is_read, is_starred,
                                    labels
                                )
                                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                                ON CONFLICT (gmail_message_id) DO NOTHING
                            """,
                                msg["id"],
                                detail.get("threadId"),
                                sender_email or "unknown@unknown.com",
                                sender_name,
                                headers.get("subject", "(No Subject)"),
                                detail.get("snippet", ""),
                                received_at,
                                "UNREAD" not in labels,
                                "STARRED" in labels,
                                labels,
                            )

                        stats["emails_synced"] += 1

                    except Exception as e:
                        logger.warning(f"[GmailSync] Error syncing email {msg['id']}: {e}")
                        stats["errors"] += 1
                        continue

            logger.info(f"[GmailSync] Email metadata sync complete: {stats}")
            return {"success": True, **stats}

        except Exception as e:
            logger.error(f"[GmailSync] Email metadata sync failed: {e}")
            return {"success": False, "error": str(e), **stats}

    async def _update_sender_scores(
        self,
        sender_stats: Dict[str, Dict],
        user_id: str,
        merge: bool = False,
    ) -> int:
        """
        Update sender_scores table with collected stats.

        Args:
            sender_stats: Dict mapping sender_email to stats
            user_id: User ID
            merge: If True, add to existing counts. If False, replace.

        Returns:
            Number of senders updated
        """
        if not self.db_pool:
            logger.warning("[GmailSync] No database pool, skipping update")
            return 0

        updated = 0

        for sender_email, stats in sender_stats.items():
            try:
                if merge:
                    # Incremental: add to existing counts
                    query = """
                        INSERT INTO sender_scores (
                            sender_email, user_id,
                            total_received, total_replied, total_opened,
                            last_interaction, updated_at
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, NOW())
                        ON CONFLICT (sender_email, user_id)
                        DO UPDATE SET
                            total_received = sender_scores.total_received + $3,
                            total_replied = sender_scores.total_replied + $4,
                            total_opened = sender_scores.total_opened + $5,
                            last_interaction = GREATEST(sender_scores.last_interaction, $6),
                            updated_at = NOW()
                    """
                else:
                    # Full sync: replace counts
                    query = """
                        INSERT INTO sender_scores (
                            sender_email, user_id,
                            total_received, total_replied, total_opened,
                            last_interaction, updated_at
                        )
                        VALUES ($1, $2, $3, $4, $5, $6, NOW())
                        ON CONFLICT (sender_email, user_id)
                        DO UPDATE SET
                            total_received = $3,
                            total_replied = $4,
                            total_opened = $5,
                            last_interaction = COALESCE($6, sender_scores.last_interaction),
                            updated_at = NOW()
                    """

                async with self.db_pool.acquire() as conn:
                    await conn.execute(
                        query,
                        sender_email.lower(),
                        user_id,
                        stats["total_received"],
                        stats["total_replied"],
                        stats["total_opened"],
                        stats["last_interaction"],
                    )
                    updated += 1

            except Exception as e:
                logger.warning(f"[GmailSync] Failed to update {sender_email}: {e}")
                continue

        return updated

    def _parse_recipients(self, to_header: str) -> List[str]:
        """Parse email addresses from To header."""
        import re
        emails = []
        # Match email addresses
        pattern = r'[\w\.-]+@[\w\.-]+'
        matches = re.findall(pattern, to_header.lower())
        return list(set(matches))

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse email date header."""
        if not date_str:
            return None

        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(date_str)
        except Exception:
            return None


# Factory function
def create_sync_service(db_pool, oauth_client) -> GmailSyncService:
    """Create a GmailSyncService instance."""
    return GmailSyncService(db_pool, oauth_client)
