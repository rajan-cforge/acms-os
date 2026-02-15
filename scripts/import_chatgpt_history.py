#!/usr/bin/env python3
"""
ChatGPT History Import Script

Usage:
    # Import ChatGPT conversations.json to query_history
    PYTHONPATH=. python scripts/import_chatgpt_history.py /path/to/conversations.json

    # Import with specific user ID
    PYTHONPATH=. python scripts/import_chatgpt_history.py /path/to/conversations.json --user-id "your-uuid"

    # Force re-import (don't skip duplicates)
    PYTHONPATH=. python scripts/import_chatgpt_history.py /path/to/conversations.json --no-skip-duplicates
"""

import asyncio
import argparse
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main(file_path: str, user_id: str, tenant_id: str, skip_duplicates: bool):
    """Run the ChatGPT import."""
    from dotenv import load_dotenv
    load_dotenv()

    from src.importers.chatgpt_importer import ChatGPTImporter

    # Validate file exists
    if not Path(file_path).exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("ACMS ChatGPT History Import")
    logger.info("=" * 60)
    logger.info(f"File: {file_path}")
    logger.info(f"User ID: {user_id}")
    logger.info(f"Tenant ID: {tenant_id}")
    logger.info(f"Skip Duplicates: {skip_duplicates}")
    logger.info("=" * 60)

    # Initialize importer (skip vectors - we only need PostgreSQL for query_history)
    importer = ChatGPTImporter()
    await importer.initialize(skip_vectors=True)

    # Run import
    logger.info("Starting import...")
    stats = await importer.import_to_query_history(
        file_path=file_path,
        user_id=user_id,
        tenant_id=tenant_id,
        skip_duplicates=skip_duplicates
    )

    # Print results
    logger.info("=" * 60)
    logger.info("IMPORT COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Conversations processed: {stats['conversations_processed']}")
    logger.info(f"Q&A pairs imported: {stats['qa_pairs_imported']}")
    logger.info(f"Duplicates skipped: {stats['duplicates_skipped']}")
    logger.info(f"Errors: {stats['errors']}")
    logger.info("=" * 60)

    # Verification query
    logger.info("\nVerification - Query History by data_source:")
    from src.storage.database import get_db_pool
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT data_source, COUNT(*) as count
            FROM query_history
            GROUP BY data_source
            ORDER BY count DESC
        """)
        for row in rows:
            logger.info(f"  {row['data_source']}: {row['count']} rows")

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import ChatGPT history to ACMS")
    parser.add_argument(
        "file_path",
        help="Path to ChatGPT conversations.json file"
    )
    parser.add_argument(
        "--user-id",
        default="00000000-0000-0000-0000-000000000001",
        help="User ID to associate with imported data (default: default user)"
    )
    parser.add_argument(
        "--tenant-id",
        default="default",
        help="Tenant ID for multi-tenancy (default: 'default')"
    )
    parser.add_argument(
        "--no-skip-duplicates",
        action="store_true",
        help="Don't skip duplicates (re-import everything)"
    )

    args = parser.parse_args()

    asyncio.run(main(
        file_path=args.file_path,
        user_id=args.user_id,
        tenant_id=args.tenant_id,
        skip_duplicates=not args.no_skip_duplicates
    ))
