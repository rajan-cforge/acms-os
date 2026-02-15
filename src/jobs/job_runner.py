"""
Job Runner with Idempotency Guarantees

Per Arch-review.md Section 6 & 14:
- Every background job must be replayable without corrupting state
- Use advisory locks to prevent overlapping runs
- Record all runs in job_runs table

Usage:
    from src.jobs.job_runner import run_job_with_tracking

    result = await run_job_with_tracking(
        job_name="decay_job",
        job_version="1.0",
        job_func=decay_job,
        window_start=datetime.now() - timedelta(days=1),
        window_end=datetime.now()
    )
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


def _generate_lock_id(tenant_id: str, job_name: str) -> int:
    """
    Generate a unique lock ID for Postgres advisory locks.

    Uses hash of (tenant_id, job_name) to create a consistent int64 lock key.
    """
    key = f"{tenant_id}:{job_name}"
    # Use first 8 bytes of MD5 hash as int64
    hash_bytes = hashlib.md5(key.encode()).digest()[:8]
    return int.from_bytes(hash_bytes, byteorder='big', signed=True)


async def acquire_advisory_lock(conn, tenant_id: str, job_name: str) -> bool:
    """
    Try to acquire a Postgres advisory lock for this job.

    Returns True if lock acquired, False if already held by another process.

    Per Arch-review.md Risk B: Single-flight locks per (tenant, job_name).
    """
    lock_id = _generate_lock_id(tenant_id, job_name)

    # pg_try_advisory_lock returns true if acquired, false if already held
    result = await conn.fetchval(
        "SELECT pg_try_advisory_lock($1)",
        lock_id
    )

    if result:
        logger.debug(f"[JobRunner] Acquired lock for {job_name} (lock_id={lock_id})")
    else:
        logger.info(f"[JobRunner] Lock already held for {job_name}, skipping run")

    return result


async def release_advisory_lock(conn, tenant_id: str, job_name: str) -> None:
    """Release the advisory lock for this job."""
    lock_id = _generate_lock_id(tenant_id, job_name)
    await conn.execute("SELECT pg_advisory_unlock($1)", lock_id)
    logger.debug(f"[JobRunner] Released lock for {job_name} (lock_id={lock_id})")


async def record_job_start(
    conn,
    job_run_id: str,
    tenant_id: str,
    job_name: str,
    job_version: str,
    window_start: Optional[datetime] = None,
    window_end: Optional[datetime] = None,
    trace_id: Optional[str] = None
) -> None:
    """Record job start in job_runs table."""
    await conn.execute("""
        INSERT INTO job_runs (
            job_run_id, tenant_id, job_name, job_version, status,
            started_at, window_start, window_end, trace_id
        ) VALUES ($1, $2, $3, $4, 'running', NOW(), $5, $6, $7)
    """, job_run_id, tenant_id, job_name, job_version, window_start, window_end, trace_id)


async def record_job_complete(
    conn,
    job_run_id: str,
    status: str,
    input_count: int = 0,
    output_count: int = 0,
    error_count: int = 0,
    error_summary: Optional[str] = None
) -> None:
    """Record job completion in job_runs table."""
    await conn.execute("""
        UPDATE job_runs
        SET status = $2,
            completed_at = NOW(),
            input_count = $3,
            output_count = $4,
            error_count = $5,
            error_summary = $6
        WHERE job_run_id = $1
    """, job_run_id, status, input_count, output_count, error_count, error_summary)


async def run_job_with_tracking(
    job_name: str,
    job_version: str,
    job_func: Callable,
    tenant_id: str = "default",
    window_start: Optional[datetime] = None,
    window_end: Optional[datetime] = None,
    trace_id: Optional[str] = None,
    **job_kwargs
) -> Dict[str, Any]:
    """
    Run a job with full tracking and single-flight guarantee.

    This wrapper:
    1. Acquires advisory lock (prevents concurrent runs)
    2. Records job start in job_runs
    3. Executes the job function
    4. Records job completion/failure
    5. Releases the lock

    Args:
        job_name: Name of the job (e.g., "decay_job")
        job_version: Version for artifact tracking
        job_func: Async function to execute
        tenant_id: Tenant ID for multi-tenancy
        window_start: Start of time window being processed
        window_end: End of time window being processed
        trace_id: Optional trace ID for debugging
        **job_kwargs: Arguments to pass to job_func

    Returns:
        Dict with job results including status, counts, and timing

    Per Arch-review.md: "job starts → acquire lock, job ends → release lock,
    if lock held → skip + emit structured log"
    """
    from src.storage.database import get_db_pool

    job_run_id = str(uuid4())
    trace_id = trace_id or str(uuid4())

    result = {
        "job_run_id": job_run_id,
        "job_name": job_name,
        "job_version": job_version,
        "status": "skipped",
        "input_count": 0,
        "output_count": 0,
        "error_count": 0,
        "error_summary": None,
        "skipped_reason": None,
        "execution_time_ms": 0
    }

    pool = await get_db_pool()
    start_time = datetime.now()

    async with pool.acquire() as conn:
        # Step 1: Try to acquire advisory lock
        lock_acquired = await acquire_advisory_lock(conn, tenant_id, job_name)

        if not lock_acquired:
            result["skipped_reason"] = "lock_held_by_another_process"
            logger.info(
                f"[JobRunner] Job {job_name} skipped: lock already held",
                extra={"trace_id": trace_id, "job_name": job_name}
            )
            return result

        try:
            # Step 2: Record job start
            await record_job_start(
                conn, job_run_id, tenant_id, job_name, job_version,
                window_start, window_end, trace_id
            )

            # Step 3: Execute the job
            logger.info(
                f"[JobRunner] Starting job {job_name} v{job_version}",
                extra={"trace_id": trace_id, "job_run_id": job_run_id}
            )

            job_result = await job_func(**job_kwargs)

            # Extract counts from job result if available
            if isinstance(job_result, dict):
                result["input_count"] = job_result.get("input_count", 0)
                result["output_count"] = job_result.get("affected_count", job_result.get("output_count", 0))
                result["job_result"] = job_result

            result["status"] = "success"

            # Step 4: Record success
            await record_job_complete(
                conn, job_run_id, "success",
                result["input_count"], result["output_count"], 0, None
            )

            logger.info(
                f"[JobRunner] Job {job_name} completed successfully",
                extra={
                    "trace_id": trace_id,
                    "job_run_id": job_run_id,
                    "output_count": result["output_count"]
                }
            )

        except Exception as e:
            # Step 4: Record failure
            error_msg = str(e)[:500]  # Truncate long errors
            result["status"] = "failed"
            result["error_count"] = 1
            result["error_summary"] = error_msg

            await record_job_complete(
                conn, job_run_id, "failed",
                result["input_count"], 0, 1, error_msg
            )

            logger.error(
                f"[JobRunner] Job {job_name} failed: {error_msg}",
                extra={"trace_id": trace_id, "job_run_id": job_run_id},
                exc_info=True
            )

        finally:
            # Step 5: Release the lock
            await release_advisory_lock(conn, tenant_id, job_name)

    result["execution_time_ms"] = (datetime.now() - start_time).total_seconds() * 1000
    return result


# Convenience wrappers for maintenance jobs
async def run_decay_job_tracked() -> Dict[str, Any]:
    """Run decay job with tracking."""
    from src.jobs.maintenance import decay_job
    return await run_job_with_tracking(
        job_name="decay_job",
        job_version="1.0",
        job_func=decay_job
    )


async def run_dedup_job_tracked() -> Dict[str, Any]:
    """Run dedup job with tracking."""
    from src.jobs.maintenance import dedup_job
    return await run_job_with_tracking(
        job_name="dedup_job",
        job_version="1.0",
        job_func=dedup_job
    )


async def run_cleanup_job_tracked() -> Dict[str, Any]:
    """Run cleanup job with tracking."""
    from src.jobs.maintenance import cleanup_job
    return await run_job_with_tracking(
        job_name="cleanup_job",
        job_version="1.0",
        job_func=cleanup_job
    )
