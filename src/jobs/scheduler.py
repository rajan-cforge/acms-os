"""Job scheduler for ACMS maintenance tasks.

Uses APScheduler for in-process scheduling.
Can be run standalone or integrated into the API server.

Usage:
    # Standalone
    python -m src.jobs.scheduler

    # Integrated into API
    from src.jobs.scheduler import start_scheduler, shutdown_scheduler
    start_scheduler()  # Call in FastAPI startup
    shutdown_scheduler()  # Call in FastAPI shutdown

Per-job enable flags (set to 'false' to disable):
    ACMS_JOB_DECAY_ENABLED
    ACMS_JOB_DEDUP_ENABLED
    ACMS_JOB_CLEANUP_ENABLED
    ACMS_JOB_TOPIC_EXTRACTION_ENABLED
    ACMS_JOB_INSIGHT_GENERATION_ENABLED
    ACMS_JOB_WEEKLY_REPORT_ENABLED
    ACMS_JOB_PORTFOLIO_SYNC_ENABLED
"""

import asyncio
import logging
import os
from datetime import datetime
from typing import Optional

try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    AsyncIOScheduler = None
    CronTrigger = None

from src.jobs.maintenance import decay_job, dedup_job, cleanup_job
from src.jobs.job_runner import (
    run_decay_job_tracked,
    run_dedup_job_tracked,
    run_cleanup_job_tracked
)
from src.jobs.intelligence_jobs import (
    run_topic_extraction_tracked,
    run_insight_generation_tracked,
    run_weekly_report_tracked,
    run_email_insight_extraction_tracked,
    run_portfolio_sync_tracked
)

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Get the global scheduler instance."""
    return _scheduler


def start_scheduler():
    """
    Start the background job scheduler.

    Schedule (Maintenance):
    - decay_job: Daily at 3 AM
    - dedup_job: Weekly on Sunday at 4 AM
    - cleanup_job: Weekly on Sunday at 5 AM

    Schedule (Intelligence - per Arch-review.md §15):
    - topic_extraction: Hourly at :15
    - insight_generation: Daily at 2 AM
    - weekly_report: Monday at 6 AM

    Per §16: Each job has an enable flag (ACMS_JOB_<NAME>_ENABLED)
    """
    global _scheduler

    if not APSCHEDULER_AVAILABLE:
        logger.warning(
            "[Scheduler] APScheduler not installed. "
            "Install with: pip install apscheduler"
        )
        return None

    if _scheduler is not None:
        logger.warning("[Scheduler] Already running")
        return _scheduler

    _scheduler = AsyncIOScheduler()
    jobs_added = []

    # Helper to check if job is enabled
    def is_job_enabled(job_name: str, default: bool = True) -> bool:
        env_key = f"ACMS_JOB_{job_name.upper()}_ENABLED"
        return os.getenv(env_key, str(default)).lower() == "true"

    # ============================================================
    # MAINTENANCE JOBS
    # ============================================================

    # Decay job - daily at 3 AM
    if is_job_enabled("decay"):
        _scheduler.add_job(
            run_decay_job_tracked,
            CronTrigger(hour=3, minute=0),
            id="decay_job",
            name="Daily importance decay",
            replace_existing=True
        )
        jobs_added.append("decay (daily 3AM)")

    # Dedup job - weekly on Sunday at 4 AM
    if is_job_enabled("dedup"):
        _scheduler.add_job(
            run_dedup_job_tracked,
            CronTrigger(day_of_week='sun', hour=4, minute=0),
            id="dedup_job",
            name="Weekly deduplication",
            replace_existing=True
        )
        jobs_added.append("dedup (Sun 4AM)")

    # Cleanup job - weekly on Sunday at 5 AM
    if is_job_enabled("cleanup"):
        _scheduler.add_job(
            run_cleanup_job_tracked,
            CronTrigger(day_of_week='sun', hour=5, minute=0),
            id="cleanup_job",
            name="Weekly cleanup of old SHORT tier",
            replace_existing=True
        )
        jobs_added.append("cleanup (Sun 5AM)")

    # ============================================================
    # INTELLIGENCE JOBS (per Arch-review.md §15)
    # ============================================================

    # Topic extraction - hourly at :15 (gives time for queries to accumulate)
    if is_job_enabled("topic_extraction"):
        _scheduler.add_job(
            run_topic_extraction_tracked,
            CronTrigger(minute=15),
            id="topic_extraction_job",
            name="Hourly topic extraction",
            replace_existing=True
        )
        jobs_added.append("topic_extraction (hourly :15)")

    # Insight generation - daily at 2 AM
    if is_job_enabled("insight_generation"):
        _scheduler.add_job(
            run_insight_generation_tracked,
            CronTrigger(hour=2, minute=0),
            id="insight_generation_job",
            name="Daily insight generation",
            replace_existing=True
        )
        jobs_added.append("insight_generation (daily 2AM)")

    # Weekly report - Monday at 6 AM
    if is_job_enabled("weekly_report"):
        _scheduler.add_job(
            run_weekly_report_tracked,
            CronTrigger(day_of_week='mon', hour=6, minute=0),
            id="weekly_report_job",
            name="Weekly intelligence report",
            replace_existing=True
        )
        jobs_added.append("weekly_report (Mon 6AM)")

    # Email insight extraction - hourly at :45 (after topic extraction at :15)
    if is_job_enabled("email_insight_extraction"):
        _scheduler.add_job(
            run_email_insight_extraction_tracked,
            CronTrigger(minute=45),
            id="email_insight_extraction_job",
            name="Hourly email insight extraction",
            replace_existing=True
        )
        jobs_added.append("email_insight_extraction (hourly :45)")

    # ============================================================
    # FINANCIAL JOBS
    # ============================================================

    # Portfolio sync - daily at 7 AM (market opens at 9:30 AM ET)
    if is_job_enabled("portfolio_sync"):
        _scheduler.add_job(
            run_portfolio_sync_tracked,
            CronTrigger(hour=7, minute=0),
            id="portfolio_sync_job",
            name="Daily portfolio sync from Plaid",
            replace_existing=True
        )
        jobs_added.append("portfolio_sync (daily 7AM)")

    _scheduler.start()

    logger.info(
        f"[Scheduler] Started with {len(jobs_added)} jobs: {', '.join(jobs_added)}"
    )

    return _scheduler


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    global _scheduler

    if _scheduler is not None:
        _scheduler.shutdown(wait=True)
        _scheduler = None
        logger.info("[Scheduler] Shutdown complete")


def get_job_status() -> dict:
    """Get status of all scheduled jobs."""
    if _scheduler is None:
        return {"status": "not_running", "jobs": []}

    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger)
        })

    return {
        "status": "running",
        "jobs": jobs
    }


# Standalone entry point
if __name__ == "__main__":
    import signal
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if not APSCHEDULER_AVAILABLE:
        print("APScheduler not installed. Install with: pip install apscheduler")
        sys.exit(1)

    print("Starting ACMS Job Scheduler...")
    print("Press Ctrl+C to stop")

    scheduler = start_scheduler()

    if scheduler:
        print("\nScheduled jobs:")
        status = get_job_status()
        for job in status["jobs"]:
            print(f"  - {job['name']}: next run at {job['next_run']}")

        # Keep running until interrupted
        try:
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            print("\nShutting down...")
            shutdown_scheduler()
