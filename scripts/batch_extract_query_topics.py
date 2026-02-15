#!/usr/bin/env python3
"""Batch extract topics from query_history for insights integration.

This script populates the topic_extractions table with topics from
query_history, enabling desktop chat queries to appear in
Insights and Reports.

Usage:
    # Extract topics for default user (keyword extraction, minimal cost)
    PYTHONPATH=. python3 scripts/batch_extract_query_topics.py

    # Extract for specific user
    PYTHONPATH=. python3 scripts/batch_extract_query_topics.py <user_id>

    # Check extraction stats
    PYTHONPATH=. python3 scripts/batch_extract_query_topics.py --stats
"""

import asyncio
import sys
import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def batch_extract_query_topics(
    user_id: str,
    batch_size: int = 100,
    max_batches: int = 1000,
    use_llm: bool = False
):
    """Extract topics from all query_history for a user.

    Args:
        user_id: User UUID to process queries for
        batch_size: Number of queries to process per batch
        max_batches: Maximum number of batches to process
        use_llm: Whether to use LLM extraction (higher cost, higher quality)
    """
    from src.storage.database import get_session
    from src.intelligence.topic_extractor import TopicExtractor, ExtractableItem

    start_time = datetime.now()
    total_processed = 0
    total_tokens = 0
    total_cost = 0.0

    logger.info(f"Starting batch topic extraction for query_history, user: {user_id}")
    logger.info(f"Settings: batch_size={batch_size}, max_batches={max_batches}, use_llm={use_llm}")

    async with get_session() as session:
        extractor = TopicExtractor(db_session=session)

        # Convert user_id string to UUID for proper type matching
        user_uuid = UUID(user_id)

        # Get queries to process
        result = await session.execute(text("""
            SELECT qh.query_id, qh.question, qh.answer, qh.user_id, qh.created_at
            FROM query_history qh
            WHERE qh.user_id = :user_id
            ORDER BY qh.created_at DESC
            LIMIT :limit
        """), {
            "user_id": user_uuid,
            "limit": batch_size * max_batches
        })

        queries = result.fetchall()
        logger.info(f"Found {len(queries)} queries to process")

        if not queries:
            logger.info("No queries to process. Exiting.")
            return

        # Process in batches
        batch_num = 0
        for i in range(0, len(queries), batch_size):
            batch_num += 1
            batch = queries[i:i+batch_size]

            items = [
                ExtractableItem(
                    source_type="query_history",
                    source_id=str(q.query_id),
                    # Combine question and answer for better topic extraction
                    text=f"Question: {q.question[:1000] if q.question else ''}\n\nAnswer: {q.answer[:1000] if q.answer else ''}",
                    user_id=str(q.user_id),
                    tenant_id="default",
                    source_created_at=q.created_at  # Preserve original timestamp
                )
                for q in batch
            ]

            # Set budget based on whether LLM is enabled
            budget = 0.50 if use_llm else 0.00  # $0 forces keyword extraction

            batch_result = await extractor.batch_extract(
                items=items,
                budget_usd=budget
            )

            total_processed += batch_result.items_processed
            total_tokens += batch_result.total_tokens
            total_cost += batch_result.total_cost_usd

            logger.info(
                f"Batch {batch_num}/{(len(queries) + batch_size - 1) // batch_size}: "
                f"Processed {batch_result.items_processed}, "
                f"Tokens: {batch_result.total_tokens}, "
                f"Cost: ${batch_result.total_cost_usd:.4f}, "
                f"Errors: {len(batch_result.errors)}"
            )

            if batch_result.errors:
                for error in batch_result.errors[:3]:
                    logger.warning(f"  Error: {error}")

            # Commit after each batch to preserve progress
            await session.commit()

    elapsed = (datetime.now() - start_time).total_seconds()

    logger.info("=" * 60)
    logger.info("BATCH EXTRACTION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total queries processed: {total_processed}")
    logger.info(f"Total tokens used: {total_tokens}")
    logger.info(f"Total cost: ${total_cost:.4f}")
    logger.info(f"Time elapsed: {elapsed:.1f} seconds")
    logger.info(f"Rate: {total_processed / elapsed:.1f} queries/second")


async def get_extraction_stats():
    """Print current topic extraction statistics."""
    from src.storage.database import get_session

    async with get_session() as session:
        result = await session.execute(text("""
            SELECT
                source_type,
                COUNT(*) as count,
                COUNT(DISTINCT user_id) as users,
                COUNT(DISTINCT primary_topic) as unique_topics
            FROM topic_extractions
            GROUP BY source_type
            ORDER BY count DESC
        """))

        rows = result.fetchall()

        print("\n" + "=" * 60)
        print("TOPIC EXTRACTION STATISTICS")
        print("=" * 60)
        print(f"{'Source Type':<20} {'Count':>10} {'Users':>8} {'Topics':>10}")
        print("-" * 60)
        for row in rows:
            print(f"{row.source_type:<20} {row.count:>10} {row.users:>8} {row.unique_topics:>10}")

        # Get top topics for query_history
        result = await session.execute(text("""
            SELECT primary_topic, COUNT(*) as count
            FROM topic_extractions
            WHERE source_type = 'query_history'
              AND primary_topic IS NOT NULL
            GROUP BY primary_topic
            ORDER BY count DESC
            LIMIT 15
        """))

        print("\n" + "-" * 60)
        print("TOP 15 QUERY TOPICS:")
        for row in result.fetchall():
            print(f"  {row.primary_topic}: {row.count}")


if __name__ == "__main__":
    # Parse arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--stats":
            asyncio.run(get_extraction_stats())
            sys.exit(0)
        user_id = sys.argv[1]
    else:
        # Default user
        user_id = "00000000-0000-0000-0000-000000000001"

    # Run extraction
    asyncio.run(batch_extract_query_topics(
        user_id=user_id,
        batch_size=100,
        max_batches=1000,
        use_llm=False  # Use keyword extraction for cost efficiency
    ))

    # Show stats after extraction
    asyncio.run(get_extraction_stats())
