#!/usr/bin/env python3
"""
Sync 5000 emails from Gmail to email_metadata table.

This script handles pagination since Gmail API limits to 500 per page.
Run from project root: python scripts/sync_5000_emails.py
"""

import asyncio
import logging
import sys
from datetime import datetime, timezone, timedelta

# Add project root to path (works in both local and Docker)
import os
project_root = os.environ.get("PROJECT_ROOT", "/app")
sys.path.insert(0, project_root)

from src.storage.database import get_db_pool
from src.integrations.gmail.oauth import GoogleOAuthClient
from src.integrations.gmail.client import GmailClient

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def sync_emails(max_emails: int = 5000, days: int = 365):
    """
    Sync emails with pagination support.

    Args:
        max_emails: Target number of emails to sync
        days: Days of history to fetch
    """
    logger.info(f"Starting sync: {max_emails} emails, last {days} days")

    db_pool = await get_db_pool()
    oauth = GoogleOAuthClient(db_pool=db_pool)

    stats = {
        "fetched": 0,
        "synced": 0,
        "skipped": 0,
        "errors": 0,
    }

    try:
        # Date filter
        after_date = datetime.now(timezone.utc) - timedelta(days=days)
        after_query = after_date.strftime("%Y/%m/%d")

        async with GmailClient(oauth, "default") as gmail:
            page_token = None
            page_num = 0

            while stats["fetched"] < max_emails:
                page_num += 1
                remaining = max_emails - stats["fetched"]
                page_size = min(500, remaining)

                logger.info(f"[Page {page_num}] Fetching {page_size} emails...")

                # Fetch page of message IDs
                result = await gmail.list_messages(
                    max_results=page_size,
                    label_ids=["INBOX"],
                    query=f"after:{after_query}",
                    page_token=page_token,
                )

                messages = result.get("messages", [])
                if not messages:
                    logger.info("No more messages to fetch")
                    break

                logger.info(f"[Page {page_num}] Got {len(messages)} message IDs")
                stats["fetched"] += len(messages)

                # Fetch and store each email's metadata
                for i, msg in enumerate(messages):
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
                        date_str = headers.get("date", "")
                        try:
                            from email.utils import parsedate_to_datetime
                            received_at = parsedate_to_datetime(date_str)
                        except:
                            received_at = datetime.now(timezone.utc)

                        # Insert into email_metadata
                        async with db_pool.acquire() as conn:
                            insert_result = await conn.execute("""
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

                            if "INSERT" in insert_result:
                                stats["synced"] += 1
                            else:
                                stats["skipped"] += 1

                        # Progress every 100 emails
                        if (i + 1) % 100 == 0:
                            logger.info(f"  Progress: {i+1}/{len(messages)} this page, {stats['synced']} total synced")

                    except Exception as e:
                        logger.warning(f"Error syncing {msg['id']}: {e}")
                        stats["errors"] += 1

                # Next page
                page_token = result.get("nextPageToken")
                if not page_token:
                    logger.info("No more pages")
                    break

                # Brief pause between pages to respect rate limits
                await asyncio.sleep(0.5)

        logger.info(f"\n{'='*50}")
        logger.info(f"SYNC COMPLETE")
        logger.info(f"  Fetched: {stats['fetched']}")
        logger.info(f"  Synced: {stats['synced']}")
        logger.info(f"  Skipped (duplicates): {stats['skipped']}")
        logger.info(f"  Errors: {stats['errors']}")
        logger.info(f"{'='*50}\n")

        return stats

    finally:
        await db_pool.close()


if __name__ == "__main__":
    asyncio.run(sync_emails(max_emails=5000, days=365))
