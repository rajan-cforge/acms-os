#!/usr/bin/env python3
"""
Batch Vectorization Job for Imported Q&A Data

Purpose: Vectorize imported ChatGPT/Claude Q&A pairs for semantic search.
Per Arch-review.md: Vector storage is derived/regenerable from query_history.

Usage:
    # Vectorize all unprocessed imports (default batch of 100)
    PYTHONPATH=. python3 scripts/batch_vectorize_imports.py

    # Vectorize with custom batch size
    PYTHONPATH=. python3 scripts/batch_vectorize_imports.py --batch-size 50

    # Dry run (count only, no vectorization)
    PYTHONPATH=. python3 scripts/batch_vectorize_imports.py --dry-run

Architecture Note:
    This is a regenerable derived artifact. If vectors need to be rebuilt,
    simply delete from Weaviate and re-run this script.
"""

import asyncio
import argparse
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def get_unvectorized_imports(
    pool,
    batch_size: int = 100,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Get Q&A pairs from imports that need vectorization.

    Uses a tracking table (vectorization_status) to track what's been vectorized.
    If table doesn't exist, returns all imports.
    """
    async with pool.acquire() as conn:
        # Check if tracking table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'vectorization_status'
            )
        """)

        if table_exists:
            # Get unvectorized imports
            rows = await conn.fetch("""
                SELECT qh.query_id, qh.question, qh.answer, qh.data_source,
                       qh.created_at, qh.user_id
                FROM query_history qh
                LEFT JOIN vectorization_status vs ON qh.query_id = vs.query_id
                WHERE qh.data_source IN ('chatgpt_import', 'claude_import')
                  AND vs.query_id IS NULL
                ORDER BY qh.created_at
                LIMIT $1 OFFSET $2
            """, batch_size, offset)
        else:
            # No tracking table - get all imports
            rows = await conn.fetch("""
                SELECT query_id, question, answer, data_source, created_at, user_id
                FROM query_history
                WHERE data_source IN ('chatgpt_import', 'claude_import')
                ORDER BY created_at
                LIMIT $1 OFFSET $2
            """, batch_size, offset)

        return [dict(row) for row in rows]


async def count_unvectorized_imports(pool) -> int:
    """Count Q&A pairs from imports that haven't been vectorized yet."""
    async with pool.acquire() as conn:
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'vectorization_status'
            )
        """)

        if table_exists:
            result = await conn.fetchrow("""
                SELECT COUNT(*) as count
                FROM query_history qh
                LEFT JOIN vectorization_status vs ON qh.query_id = vs.query_id
                WHERE qh.data_source IN ('chatgpt_import', 'claude_import')
                  AND vs.query_id IS NULL
            """)
        else:
            result = await conn.fetchrow("""
                SELECT COUNT(*) as count
                FROM query_history
                WHERE data_source IN ('chatgpt_import', 'claude_import')
            """)

        return result['count'] if result else 0


async def ensure_tracking_table(pool) -> None:
    """Create vectorization tracking table if it doesn't exist."""
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS vectorization_status (
                query_id UUID PRIMARY KEY REFERENCES query_history(query_id),
                vectorized_at TIMESTAMPTZ DEFAULT NOW(),
                weaviate_id TEXT,
                error TEXT
            )
        """)
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_vectorization_status_at
            ON vectorization_status(vectorized_at)
        """)
        logger.info("[Vectorize] Tracking table ensured")


async def mark_vectorized(pool, query_id: str, weaviate_id: Optional[str] = None, error: Optional[str] = None) -> None:
    """Mark a Q&A pair as vectorized (or record error)."""
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO vectorization_status (query_id, weaviate_id, error)
            VALUES ($1, $2, $3)
            ON CONFLICT (query_id) DO UPDATE SET
                vectorized_at = NOW(),
                weaviate_id = EXCLUDED.weaviate_id,
                error = EXCLUDED.error
        """, query_id, weaviate_id, error)


async def batch_vectorize(
    batch_size: int = 100,
    dry_run: bool = False,
    max_batches: int = 100,
    cost_limit_usd: float = 1.0
) -> Dict[str, Any]:
    """
    Vectorize imported Q&A pairs in batches and store in Weaviate ACMS_Raw_v1.

    Args:
        batch_size: Number of Q&A pairs per batch
        dry_run: If True, only count without vectorizing
        max_batches: Maximum number of batches to process
        cost_limit_usd: Maximum cost in USD before stopping

    Returns:
        Dict with processing statistics
    """
    from dotenv import load_dotenv
    load_dotenv()

    from src.storage.database import get_db_pool
    from src.embeddings.openai_embeddings import OpenAIEmbeddings
    import hashlib

    pool = await get_db_pool()

    stats = {
        "total_unvectorized": 0,
        "batches_processed": 0,
        "items_vectorized": 0,
        "items_skipped": 0,
        "errors": 0,
        "total_tokens": 0,
        "estimated_cost_usd": 0.0,
        "dry_run": dry_run
    }

    # Ensure tracking table exists
    if not dry_run:
        await ensure_tracking_table(pool)

    # Count total unvectorized
    stats["total_unvectorized"] = await count_unvectorized_imports(pool)
    logger.info(f"[Vectorize] Found {stats['total_unvectorized']} unvectorized Q&A pairs")

    if dry_run:
        logger.info("[Vectorize] Dry run mode - no vectorization performed")
        return stats

    if stats["total_unvectorized"] == 0:
        logger.info("[Vectorize] No imports to vectorize")
        return stats

    # Initialize embeddings and Weaviate
    embeddings = OpenAIEmbeddings()

    # Initialize Weaviate client for storing vectors
    # For local access: HTTP port 40480, gRPC port 40481
    weaviate_client = None
    try:
        from src.storage.weaviate_client import WeaviateClient
        # Ensure gRPC port is set for local access (40481 maps to internal 50051)
        if not os.getenv("WEAVIATE_GRPC_PORT"):
            os.environ["WEAVIATE_GRPC_PORT"] = "40481"
        weaviate_client = WeaviateClient(
            host=os.getenv("WEAVIATE_HOST", "localhost"),
            port=int(os.getenv("WEAVIATE_PORT", "40480"))
        )
        logger.info("[Vectorize] Connected to Weaviate")
    except Exception as e:
        logger.warning(f"[Vectorize] Weaviate not available: {e}. Will track without storing vectors.")

    # Cost tracking (text-embedding-3-small: $0.02 per 1M tokens)
    COST_PER_1M_TOKENS = 0.02
    COLLECTION_NAME = "ACMS_Raw_v1"

    while stats["batches_processed"] < max_batches:
        # Check cost limit
        if stats["estimated_cost_usd"] >= cost_limit_usd:
            logger.warning(f"[Vectorize] Cost limit reached: ${stats['estimated_cost_usd']:.4f}")
            break

        # Get batch of unvectorized imports
        rows = await get_unvectorized_imports(pool, batch_size, 0)

        if not rows:
            logger.info("[Vectorize] No more imports to process")
            break

        logger.info(f"[Vectorize] Processing batch {stats['batches_processed'] + 1} ({len(rows)} items)")

        for row in rows:
            try:
                question = row['question'][:2000] if row['question'] else ""
                answer = row['answer'][:4000] if row['answer'] else ""

                # Generate embedding for the question (for semantic search)
                # OpenAIEmbeddings.generate_embedding() is synchronous
                embedding = embeddings.generate_embedding(question)

                # Track tokens
                tokens_used = (len(question) + len(answer)) // 4
                stats["total_tokens"] += tokens_used
                stats["estimated_cost_usd"] = (stats["total_tokens"] / 1_000_000) * COST_PER_1M_TOKENS

                weaviate_id = None

                # Store in Weaviate if available
                if weaviate_client:
                    try:
                        # Create query hash for deduplication
                        query_hash = hashlib.sha256(question.encode()).hexdigest()[:16]

                        # Prepare data for ACMS_Raw_v1 schema
                        data = {
                            "query_hash": query_hash,
                            "query_text": question,
                            "answer_text": answer,
                            "conversation_id": str(row.get('query_id', '')),
                            "agent_used": row.get('data_source', 'chatgpt_import'),
                            "created_at": row['created_at'].isoformat() if row.get('created_at') else datetime.now().isoformat()
                        }

                        weaviate_id = weaviate_client.insert_vector(
                            collection=COLLECTION_NAME,
                            vector=embedding,
                            data=data
                        )
                    except Exception as we:
                        logger.warning(f"[Vectorize] Weaviate insert failed for {row['query_id']}: {we}")
                        weaviate_id = f"failed_{uuid4()}"

                # Mark as vectorized
                await mark_vectorized(pool, str(row['query_id']), weaviate_id or str(uuid4()))
                stats["items_vectorized"] += 1

            except Exception as e:
                logger.error(f"[Vectorize] Error processing {row['query_id']}: {e}")
                await mark_vectorized(pool, str(row['query_id']), error=str(e)[:500])
                stats["errors"] += 1

        stats["batches_processed"] += 1
        logger.info(
            f"[Vectorize] Batch {stats['batches_processed']} complete: "
            f"{stats['items_vectorized']} vectorized, "
            f"${stats['estimated_cost_usd']:.4f} spent"
        )

    # Close Weaviate client
    if weaviate_client:
        try:
            weaviate_client._client.close()
        except:
            pass

    return stats


async def run_vectorization_job() -> Dict[str, Any]:
    """
    Run vectorization as a tracked job.

    This is the entry point for the scheduler.
    """
    from src.jobs.job_runner import run_job_with_tracking

    return await run_job_with_tracking(
        job_name="vectorize_imports",
        job_version="1.0",
        job_func=batch_vectorize,
        batch_size=100,
        max_batches=10,  # Process 1000 items max per run
        cost_limit_usd=0.10  # $0.10 per run max
    )


async def main(batch_size: int, dry_run: bool, cost_limit: float):
    """Run batch vectorization."""
    logger.info("=" * 60)
    logger.info("ACMS Batch Vectorization for Imports")
    logger.info("=" * 60)
    logger.info(f"Batch size: {batch_size}")
    logger.info(f"Cost limit: ${cost_limit}")
    logger.info(f"Dry run: {dry_run}")
    logger.info("=" * 60)

    stats = await batch_vectorize(
        batch_size=batch_size,
        dry_run=dry_run,
        cost_limit_usd=cost_limit
    )

    logger.info("=" * 60)
    logger.info("VECTORIZATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total unvectorized: {stats['total_unvectorized']}")
    logger.info(f"Batches processed: {stats['batches_processed']}")
    logger.info(f"Items vectorized: {stats['items_vectorized']}")
    logger.info(f"Errors: {stats['errors']}")
    logger.info(f"Total tokens: {stats['total_tokens']}")
    logger.info(f"Estimated cost: ${stats['estimated_cost_usd']:.4f}")
    logger.info("=" * 60)

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Batch vectorize imported ChatGPT/Claude Q&A data"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of Q&A pairs per batch (default: 100)"
    )
    parser.add_argument(
        "--cost-limit",
        type=float,
        default=1.0,
        help="Maximum cost in USD (default: $1.00)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Count imports without vectorizing"
    )

    args = parser.parse_args()

    asyncio.run(main(
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        cost_limit=args.cost_limit
    ))
