"""Background maintenance jobs for memory management.

P4 Implementation - Three maintenance jobs:
1. decay_job: Reduce importance of old unused memories (run daily)
2. dedup_job: Merge near-duplicate memories (run weekly)
3. cleanup_job: Delete SHORT tier memories > 30 days (run weekly)

Usage:
    # Run individual jobs
    from src.jobs.maintenance import decay_job, dedup_job, cleanup_job
    await decay_job()

    # Run all maintenance
    from src.jobs.maintenance import run_all_maintenance
    await run_all_maintenance()

    # CLI: python -m src.jobs.maintenance --job decay
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Configuration
DECAY_RATE = 0.95  # 5% decay per day for unused memories
DECAY_MIN_AGE_DAYS = 7  # Only decay memories older than 7 days
DECAY_MIN_SCORE = 0.1  # Don't decay below this threshold

DEDUP_SIMILARITY_THRESHOLD = 0.95  # Content similarity threshold for dedup
DEDUP_BATCH_SIZE = 100  # Process in batches

CLEANUP_SHORT_TIER_DAYS = 30  # Delete SHORT tier memories older than this
CLEANUP_BATCH_SIZE = 500  # Delete in batches


async def decay_job(db_session: Optional[Session] = None) -> Dict[str, Any]:
    """
    Decay importance scores of old, unused memories.

    This prevents old memories from dominating retrieval results.
    Memories accessed recently are not decayed.

    Returns:
        Dict with job results {affected_count, execution_time_ms}
    """
    from src.storage.database import get_db_session

    start_time = datetime.now()
    logger.info("[DecayJob] Starting importance decay job...")

    if db_session is None:
        db_session = next(get_db_session())

    try:
        # Find memories to decay:
        # - Older than DECAY_MIN_AGE_DAYS
        # - Not accessed in the last DECAY_MIN_AGE_DAYS
        # - Current importance_score > DECAY_MIN_SCORE
        cutoff_date = datetime.now() - timedelta(days=DECAY_MIN_AGE_DAYS)

        # Update query - reduce outcome_score and frequency_score by DECAY_RATE
        result = db_session.execute(
            text("""
                UPDATE memory_items
                SET
                    outcome_score = GREATEST(:min_score, outcome_score * :decay_rate),
                    frequency_score = GREATEST(:min_score, frequency_score * :decay_rate),
                    updated_at = NOW()
                WHERE
                    created_at < :cutoff_date
                    AND (last_accessed_at IS NULL OR last_accessed_at < :cutoff_date)
                    AND (outcome_score > :min_score OR frequency_score > :min_score)
                RETURNING id
            """),
            {
                "decay_rate": DECAY_RATE,
                "min_score": DECAY_MIN_SCORE,
                "cutoff_date": cutoff_date
            }
        )

        affected_ids = result.fetchall()
        affected_count = len(affected_ids)

        db_session.commit()

        execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            f"[DecayJob] Completed: {affected_count} memories decayed "
            f"in {execution_time_ms:.0f}ms"
        )

        return {
            "job": "decay",
            "affected_count": affected_count,
            "execution_time_ms": round(execution_time_ms, 2),
            "decay_rate": DECAY_RATE,
            "cutoff_days": DECAY_MIN_AGE_DAYS
        }

    except Exception as e:
        logger.error(f"[DecayJob] Failed: {e}")
        db_session.rollback()
        raise


async def dedup_job(db_session: Optional[Session] = None) -> Dict[str, Any]:
    """
    Find and merge near-duplicate memories.

    Uses content hash comparison for exact duplicates,
    and can optionally use embedding similarity for near-duplicates.

    Returns:
        Dict with job results {merged_count, execution_time_ms}
    """
    from src.storage.database import get_db_session

    start_time = datetime.now()
    logger.info("[DedupJob] Starting deduplication job...")

    if db_session is None:
        db_session = next(get_db_session())

    try:
        # Find exact duplicates by content_hash
        # Keep the oldest (or highest scored) and remove others
        result = db_session.execute(
            text("""
                WITH duplicates AS (
                    SELECT
                        content_hash,
                        COUNT(*) as dup_count,
                        array_agg(id ORDER BY
                            COALESCE(outcome_score, 0) + COALESCE(frequency_score, 0) DESC,
                            created_at ASC
                        ) as ids
                    FROM memory_items
                    WHERE content_hash IS NOT NULL
                    GROUP BY content_hash
                    HAVING COUNT(*) > 1
                ),
                to_delete AS (
                    SELECT unnest(ids[2:]) as id
                    FROM duplicates
                )
                DELETE FROM memory_items
                WHERE id IN (SELECT id FROM to_delete)
                RETURNING id
            """)
        )

        deleted_ids = result.fetchall()
        merged_count = len(deleted_ids)

        db_session.commit()

        execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            f"[DedupJob] Completed: {merged_count} duplicate memories merged "
            f"in {execution_time_ms:.0f}ms"
        )

        return {
            "job": "dedup",
            "merged_count": merged_count,
            "execution_time_ms": round(execution_time_ms, 2)
        }

    except Exception as e:
        logger.error(f"[DedupJob] Failed: {e}")
        db_session.rollback()
        raise


async def cleanup_job(db_session: Optional[Session] = None) -> Dict[str, Any]:
    """
    Delete old SHORT tier memories that are no longer useful.

    SHORT tier memories are meant to be temporary.
    This job enforces the retention policy.

    Returns:
        Dict with job results {deleted_count, execution_time_ms}
    """
    from src.storage.database import get_db_session

    start_time = datetime.now()
    logger.info("[CleanupJob] Starting cleanup job...")

    if db_session is None:
        db_session = next(get_db_session())

    try:
        cutoff_date = datetime.now() - timedelta(days=CLEANUP_SHORT_TIER_DAYS)

        # Delete old SHORT tier memories with low scores
        result = db_session.execute(
            text("""
                DELETE FROM memory_items
                WHERE
                    tier = 'SHORT'
                    AND created_at < :cutoff_date
                    AND COALESCE(outcome_score, 0) < 0.5
                    AND COALESCE(frequency_score, 0) < 0.5
                RETURNING id
            """),
            {"cutoff_date": cutoff_date}
        )

        deleted_ids = result.fetchall()
        deleted_count = len(deleted_ids)

        db_session.commit()

        execution_time_ms = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            f"[CleanupJob] Completed: {deleted_count} old SHORT tier memories deleted "
            f"in {execution_time_ms:.0f}ms"
        )

        return {
            "job": "cleanup",
            "deleted_count": deleted_count,
            "execution_time_ms": round(execution_time_ms, 2),
            "retention_days": CLEANUP_SHORT_TIER_DAYS
        }

    except Exception as e:
        logger.error(f"[CleanupJob] Failed: {e}")
        db_session.rollback()
        raise


async def run_all_maintenance(db_session: Optional[Session] = None) -> Dict[str, Any]:
    """
    Run all maintenance jobs in sequence.

    Order: decay → dedup → cleanup

    Returns:
        Dict with all job results
    """
    logger.info("[Maintenance] Starting all maintenance jobs...")
    start_time = datetime.now()

    results = {}

    try:
        results["decay"] = await decay_job(db_session)
        results["dedup"] = await dedup_job(db_session)
        results["cleanup"] = await cleanup_job(db_session)

        total_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        results["total_execution_time_ms"] = round(total_time_ms, 2)

        logger.info(
            f"[Maintenance] All jobs completed in {total_time_ms:.0f}ms: "
            f"decay={results['decay']['affected_count']}, "
            f"dedup={results['dedup']['merged_count']}, "
            f"cleanup={results['cleanup']['deleted_count']}"
        )

        return results

    except Exception as e:
        logger.error(f"[Maintenance] Failed: {e}")
        results["error"] = str(e)
        return results


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run ACMS maintenance jobs")
    parser.add_argument(
        "--job",
        choices=["decay", "dedup", "cleanup", "all"],
        default="all",
        help="Which job to run (default: all)"
    )

    args = parser.parse_args()

    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    async def main():
        from dotenv import load_dotenv
        load_dotenv()

        if args.job == "decay":
            result = await decay_job()
        elif args.job == "dedup":
            result = await dedup_job()
        elif args.job == "cleanup":
            result = await cleanup_job()
        else:
            result = await run_all_maintenance()

        print(f"\nResults: {result}")

    asyncio.run(main())
