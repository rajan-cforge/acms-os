"""Intelligence Jobs for ACMS.

Per Arch-review.md §15:
- Topic Extraction (hourly): Extract topics from new Q&A pairs
- Insight Generation (daily 2AM): Generate user/org insights
- Weekly Report (Monday 6AM): Generate weekly intelligence reports

All jobs use the job_runner for:
- Advisory locks (prevent concurrent runs)
- job_runs tracking
- Idempotent windowed processing
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from uuid import uuid4

from sqlalchemy import text

from src.jobs.job_runner import run_job_with_tracking
from src.storage.database import get_db_pool

logger = logging.getLogger(__name__)

# ============================================================
# TOPIC EXTRACTION JOB (Hourly)
# ============================================================

async def topic_extraction_job(
    window_hours: int = 1,
    batch_size: int = 100,
    budget_usd: float = 0.10,
    tenant_id: str = "default"
) -> Dict[str, Any]:
    """Extract topics from recent Q&A pairs with consolidation triage.

    Cognitive Principle: Selective consolidation (hippocampal replay).
    Not all queries deserve full knowledge extraction.

    Per §8 (LLM Boundary Discipline):
    - Use keyword extraction first (free)
    - Only escalate to LLM if low confidence
    - Never exceed budget_usd

    Consolidation Triage (NEW):
    - FULL_EXTRACTION: Full LLM-assisted knowledge extraction
    - LIGHTWEIGHT_TAGGING: Keyword-only extraction (no LLM cost)
    - TRANSIENT: Skip entirely (mark with TTL for natural decay)

    Expected Impact: 40-60% reduction in LLM extraction costs.

    Args:
        window_hours: Hours of history to process (default: 1)
        batch_size: Items per batch
        budget_usd: Max LLM spend
        tenant_id: Tenant to process

    Returns:
        Dict with processing stats
    """
    from src.intelligence.topic_extractor import (
        TopicExtractor, ExtractableItem
    )
    from src.intelligence.consolidation_triager import (
        ConsolidationTriager, ConsolidationPriority,
        QueryRecord, create_query_record_from_row
    )

    pool = await get_db_pool()
    stats = {
        "input_count": 0,
        "affected_count": 0,
        "errors": 0,
        "cached_count": 0,
        "tokens_used": 0,
        "cost_usd": 0.0,
        # New triage stats
        "triage_full": 0,
        "triage_light": 0,
        "triage_transient": 0,
        "cost_savings_estimate_usd": 0.0,
    }

    window_end = datetime.utcnow()
    window_start = window_end - timedelta(hours=window_hours)

    logger.info(
        f"[TopicExtraction] Processing window: {window_start} to {window_end}"
    )

    async with pool.acquire() as conn:
        # Get Q&A pairs without topic extractions
        # Also fetch feedback_type and session_id for triage signals
        rows = await conn.fetch("""
            SELECT qh.query_id, qh.question, qh.answer, qh.user_id,
                   qh.created_at, qh.tenant_id, qh.session_id,
                   qh.response_source, qh.total_latency_ms,
                   fb.feedback_type
            FROM query_history qh
            LEFT JOIN topic_extractions te
                ON te.source_type = 'query_history'
                AND te.source_id = qh.query_id
                AND te.extractor_version = 'v1'
            LEFT JOIN query_feedback fb
                ON fb.query_id = qh.query_id
            WHERE qh.tenant_id = $1
              AND qh.created_at >= $2
              AND qh.created_at < $3
              AND te.id IS NULL
            ORDER BY qh.created_at
            LIMIT $4
        """, tenant_id, window_start, window_end, batch_size)

        stats["input_count"] = len(rows)

        if not rows:
            logger.info("[TopicExtraction] No new Q&A pairs to process")
            return stats

        # ============================================================
        # CONSOLIDATION TRIAGE (NEW)
        # ============================================================
        # Cognitive basis: Hippocampal selective replay during sleep
        # Not all experiences get consolidated to long-term memory

        # Create query records for triage
        query_records = []
        for row in rows:
            record = QueryRecord(
                query_id=str(row['query_id']),
                question=row['question'] or "",
                answer=row['answer'] or "",
                user_id=str(row['user_id']),
                created_at=row['created_at'],
                tenant_id=row['tenant_id'],
                session_id=row.get('session_id'),
                response_source=row.get('response_source'),
                total_latency_ms=row.get('total_latency_ms'),
                feedback_type=row.get('feedback_type'),
            )
            query_records.append(record)

        # Triage all records
        triager = ConsolidationTriager(
            db=None,  # Skip follow-up detection for performance (can enable with DB)
            enable_follow_up_detection=False,
            enable_topic_novelty_check=False,
        )

        triaged = await triager.batch_triage(query_records)

        full_extraction_records = triaged[ConsolidationPriority.FULL_EXTRACTION]
        lightweight_records = triaged[ConsolidationPriority.LIGHTWEIGHT_TAGGING]
        transient_records = triaged[ConsolidationPriority.TRANSIENT]

        stats["triage_full"] = len(full_extraction_records)
        stats["triage_light"] = len(lightweight_records)
        stats["triage_transient"] = len(transient_records)

        triage_stats = triager.get_stats()
        logger.info(
            f"[TopicExtraction] Triage results: "
            f"{triage_stats['full_pct']}% full, "
            f"{triage_stats['light_pct']}% light, "
            f"{triage_stats['transient_pct']}% transient"
        )

        # Estimate cost savings (transient + light items would have used LLM)
        # Assume ~$0.001 per full extraction on average
        items_skipped_llm = len(lightweight_records) + len(transient_records)
        stats["cost_savings_estimate_usd"] = items_skipped_llm * 0.001

        # ============================================================
        # PROCESS BY PRIORITY
        # ============================================================

        # Initialize extractor (keyword-first per §8)
        extractor = TopicExtractor(version="v1")

        # Build extractable items for FULL extraction only
        full_items = []
        for record in full_extraction_records:
            question = record.question[:2000] if record.question else ""
            answer = record.answer[:2000] if record.answer else ""
            text = f"Q: {question}\nA: {answer}" if answer else question

            full_items.append(ExtractableItem(
                source_type="query_history",
                source_id=record.query_id,
                text=text,
                user_id=record.user_id,
                tenant_id=record.tenant_id,
                source_created_at=record.created_at
            ))

        # Build lightweight items (keyword-only, no LLM)
        light_items = []
        for record in lightweight_records:
            question = record.question[:2000] if record.question else ""
            answer = record.answer[:2000] if record.answer else ""
            text = f"Q: {question}\nA: {answer}" if answer else question

            light_items.append(ExtractableItem(
                source_type="query_history",
                source_id=record.query_id,
                text=text,
                user_id=record.user_id,
                tenant_id=record.tenant_id,
                source_created_at=record.created_at
            ))

        # Process full extraction items (with LLM budget)
        try:
            from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
            from sqlalchemy.orm import sessionmaker

            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                raise ValueError("DATABASE_URL environment variable must be set")
            # Ensure async driver
            if db_url.startswith("postgresql://"):
                db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            engine = create_async_engine(db_url)
            async_session = sessionmaker(engine, class_=AsyncSession)

            async with async_session() as session:
                extractor.db = session

                # FULL EXTRACTION: Use LLM budget
                if full_items:
                    result = await extractor.batch_extract(
                        items=full_items,
                        budget_usd=budget_usd
                    )
                    stats["affected_count"] += result.items_processed
                    stats["tokens_used"] = result.total_tokens
                    stats["cost_usd"] = result.total_cost_usd
                    stats["errors"] = len(result.errors)

                # LIGHTWEIGHT: Keyword-only extraction (budget=0 forces keyword mode)
                if light_items:
                    light_result = await extractor.batch_extract(
                        items=light_items,
                        budget_usd=0.0  # No LLM spend for lightweight
                    )
                    stats["affected_count"] += light_result.items_processed

                # TRANSIENT: Mark as processed but skip extraction
                # Insert minimal topic_extraction records to prevent re-processing
                if transient_records:
                    for record in transient_records:
                        await session.execute(text("""
                            INSERT INTO topic_extractions (
                                id, source_type, source_id, user_id, tenant_id,
                                topics, primary_topic, extraction_method,
                                extractor_version, confidence, created_at
                            ) VALUES (
                                gen_random_uuid(), 'query_history', :source_id::uuid,
                                :user_id::uuid, :tenant_id, ARRAY['transient']::text[],
                                'transient', 'keyword', 'v1', 0.0, NOW()
                            )
                            ON CONFLICT (tenant_id, source_type, source_id, extractor_version)
                            DO NOTHING
                        """), {
                            "source_id": record.query_id,
                            "user_id": record.user_id,
                            "tenant_id": record.tenant_id,
                        })
                    stats["affected_count"] += len(transient_records)

                await session.commit()

        except Exception as e:
            logger.error(f"[TopicExtraction] Batch extraction failed: {e}")
            stats["errors"] = 1
            stats["error_summary"] = str(e)[:500]

    logger.info(
        f"[TopicExtraction] Complete: {stats['affected_count']}/{stats['input_count']} "
        f"processed, ${stats['cost_usd']:.4f} spent, "
        f"~${stats['cost_savings_estimate_usd']:.4f} saved via triage"
    )

    return stats


async def run_topic_extraction_tracked() -> Dict[str, Any]:
    """Run topic extraction with full job tracking."""
    window_hours = 2  # Process last 2 hours for safety
    budget = float(os.getenv("ACMS_TOPIC_EXTRACTION_BUDGET_USD", "0.10"))

    window_end = datetime.utcnow()
    window_start = window_end - timedelta(hours=window_hours)

    return await run_job_with_tracking(
        job_name="topic_extraction",
        job_version="v1.0",
        job_func=topic_extraction_job,
        window_start=window_start,
        window_end=window_end,
        window_hours=window_hours,
        budget_usd=budget
    )


# ============================================================
# INSIGHT GENERATION JOB (Daily at 2AM)
# ============================================================

async def insight_generation_job(
    period_days: int = 7,
    tenant_id: str = "default"
) -> Dict[str, Any]:
    """Generate user and org insights from topic extractions.

    Per §7 (Temporal Decay):
    - Revives org_knowledge when topics resurface
    - Applies decay to stale knowledge

    Args:
        period_days: Days of history to analyze
        tenant_id: Tenant to process

    Returns:
        Dict with processing stats
    """
    from src.intelligence.insights_engine import InsightsEngine

    stats = {
        "input_count": 0,
        "affected_count": 0,
        "users_processed": 0,
        "org_knowledge_updated": 0,
        "errors": 0
    }

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        # Get active users with topic extractions
        users = await conn.fetch("""
            SELECT DISTINCT user_id
            FROM topic_extractions
            WHERE tenant_id = $1
              AND created_at >= NOW() - INTERVAL '%s days'
        """ % period_days, tenant_id)

        stats["input_count"] = len(users)

        if not users:
            logger.info("[InsightGeneration] No users with recent activity")
            return stats

        # Process each user (generate personal insights)
        for user_row in users:
            user_id = str(user_row['user_id'])

            try:
                # Initialize engine (will use on-demand generation)
                engine = InsightsEngine()
                await engine.initialize()

                # Generate summary triggers insight storage
                await engine.generate_summary(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    period_days=period_days
                )

                stats["users_processed"] += 1
                stats["affected_count"] += 1

            except Exception as e:
                logger.error(f"[InsightGeneration] User {user_id} failed: {e}")
                stats["errors"] += 1

        # Apply org_knowledge decay (per §7)
        try:
            decay_result = await conn.fetchval(
                "SELECT decay_org_knowledge($1, $2)",
                0.1,  # 10% decay rate
                7     # 7 days minimum
            )
            stats["org_knowledge_updated"] = decay_result or 0
            logger.info(f"[InsightGeneration] Decayed {decay_result} org_knowledge entries")
        except Exception as e:
            logger.warning(f"[InsightGeneration] Decay failed: {e}")

    logger.info(
        f"[InsightGeneration] Complete: {stats['users_processed']} users, "
        f"{stats['org_knowledge_updated']} org entries decayed"
    )

    return stats


async def run_insight_generation_tracked() -> Dict[str, Any]:
    """Run insight generation with full job tracking."""
    period_days = int(os.getenv("ACMS_INSIGHT_PERIOD_DAYS", "7"))

    window_end = datetime.utcnow()
    window_start = window_end - timedelta(days=period_days)

    return await run_job_with_tracking(
        job_name="insight_generation",
        job_version="v1.0",
        job_func=insight_generation_job,
        window_start=window_start,
        window_end=window_end,
        period_days=period_days
    )


# ============================================================
# WEEKLY REPORT JOB (Monday 6AM)
# ============================================================

async def weekly_report_job(
    tenant_id: str = "default"
) -> Dict[str, Any]:
    """Generate weekly intelligence reports for all users.

    Per §15 (Intelligence Jobs):
    - Generates personal and org-wide reports
    - Stores in intelligence_reports table
    - Consumes only successful insight runs

    Returns:
        Dict with processing stats
    """
    from src.intelligence.report_generator import ReportGenerator, ReportType

    stats = {
        "input_count": 0,
        "affected_count": 0,
        "personal_reports": 0,
        "org_reports": 0,
        "errors": 0,
        "tokens_used": 0,
        "cost_usd": 0.0
    }

    pool = await get_db_pool()

    # Calculate period (last 7 days)
    period_end = datetime.utcnow().date()
    period_start = period_end - timedelta(days=7)

    async with pool.acquire() as conn:
        # Get active users
        users = await conn.fetch("""
            SELECT DISTINCT user_id
            FROM query_history
            WHERE tenant_id = $1
              AND created_at >= $2
              AND created_at < $3
        """, tenant_id, period_start, period_end)

        stats["input_count"] = len(users)

        if not users:
            logger.info("[WeeklyReport] No active users")
            return stats

        # Generate reports for each user
        generator = ReportGenerator()

        for user_row in users:
            user_id = str(user_row['user_id'])

            try:
                report = await generator.generate_report(
                    report_type=ReportType.WEEKLY_PERSONAL,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    period_start=period_start,
                    period_end=period_end
                )

                if report:
                    stats["personal_reports"] += 1
                    stats["affected_count"] += 1
                    stats["tokens_used"] += report.tokens_used or 0
                    stats["cost_usd"] += float(report.cost_usd or 0)

            except Exception as e:
                logger.error(f"[WeeklyReport] User {user_id} failed: {e}")
                stats["errors"] += 1

        # Generate org-wide report (admin only)
        try:
            org_report = await generator.generate_report(
                report_type=ReportType.WEEKLY_ORG,
                user_id=None,  # Org-wide
                tenant_id=tenant_id,
                period_start=period_start,
                period_end=period_end
            )

            if org_report:
                stats["org_reports"] += 1
                stats["affected_count"] += 1

        except Exception as e:
            logger.error(f"[WeeklyReport] Org report failed: {e}")
            stats["errors"] += 1

    logger.info(
        f"[WeeklyReport] Complete: {stats['personal_reports']} personal, "
        f"{stats['org_reports']} org reports, ${stats['cost_usd']:.4f} spent"
    )

    return stats


async def run_weekly_report_tracked() -> Dict[str, Any]:
    """Run weekly report with full job tracking."""
    window_end = datetime.utcnow()
    window_start = window_end - timedelta(days=7)

    return await run_job_with_tracking(
        job_name="weekly_report",
        job_version="v1.0",
        job_func=weekly_report_job,
        window_start=window_start,
        window_end=window_end
    )


# ============================================================
# CROSS-VALIDATION JOB (Weekly, Sunday 3AM)
# ============================================================

async def cross_validation_job(
    batch_size: int = 100,
    tenant_id: str = "default"
) -> Dict[str, Any]:
    """Cross-validate Raw and Knowledge entries for consistency.

    Cognitive Principle: Error-Correcting Codes

    The brain maintains consistency across memory stores. When the hippocampus
    (Raw/episodic memory) and neocortex (Knowledge/semantic memory) have
    conflicting information, error-correcting mechanisms resolve inconsistencies.

    This job:
    1. Finds pairs of Raw and Knowledge entries that should be related
    2. Computes consistency scores (content + embedding similarity)
    3. Flags inconsistent pairs for human review

    Expected Impact:
    - Improved knowledge base accuracy
    - Detection of outdated or conflicting information
    - Human-in-the-loop correction for complex conflicts

    Args:
        batch_size: Max pairs to validate per run
        tenant_id: Tenant to process

    Returns:
        Dict with validation stats
    """
    from src.intelligence.cross_validator import CrossValidator, CrossValidatorConfig
    from src.storage.database import get_db_pool

    stats = {
        "input_count": 0,
        "pairs_validated": 0,
        "consistent_count": 0,
        "inconsistent_count": 0,
        "flagged_for_review": 0,
        "errors": 0
    }

    pool = await get_db_pool()

    logger.info("[CrossValidation] Starting weekly cross-validation job")

    try:
        # Initialize validator with default config
        validator = CrossValidator(
            config=CrossValidatorConfig(
                consistency_threshold=0.70,
                embedding_weight=0.4,
                content_weight=0.4,
                date_weight=0.2
            )
        )

        async with pool.acquire() as conn:
            # Find Raw entries that have been used to generate Knowledge entries
            # These are candidates for cross-validation
            # We look at Knowledge entries that reference Raw entries as sources
            rows = await conn.fetch("""
                SELECT
                    k.id as knowledge_id,
                    k.content as knowledge_content,
                    k.user_id,
                    k.created_at as knowledge_created_at,
                    k.confidence,
                    r.id as raw_id,
                    r.question as raw_question,
                    r.answer as raw_answer,
                    r.created_at as raw_created_at
                FROM knowledge_entries k
                CROSS JOIN LATERAL (
                    SELECT qh.query_id as id, qh.question, qh.answer, qh.created_at
                    FROM query_history qh
                    WHERE qh.user_id = k.user_id
                      AND qh.created_at <= k.created_at
                      AND qh.created_at >= k.created_at - INTERVAL '7 days'
                    ORDER BY qh.created_at DESC
                    LIMIT 1
                ) r
                WHERE k.tenant_id = $1
                  AND k.created_at >= NOW() - INTERVAL '30 days'
                  AND NOT EXISTS (
                      SELECT 1 FROM cross_validation_inconsistencies cvi
                      WHERE cvi.knowledge_id = k.id::text
                        AND cvi.created_at >= NOW() - INTERVAL '7 days'
                  )
                LIMIT $2
            """, tenant_id, batch_size)

            stats["input_count"] = len(rows)

            if not rows:
                logger.info("[CrossValidation] No new pairs to validate")
                return stats

            # Validate each pair
            for row in rows:
                try:
                    # Create mock entry objects for validation
                    class RawEntry:
                        def __init__(self, r):
                            self.id = str(r['raw_id'])
                            self.content = f"Q: {r['raw_question']}\nA: {r['raw_answer']}"
                            self.user_id = str(r['user_id'])
                            self.created_at = r['raw_created_at']
                            self.embedding = None  # Will use content-only comparison

                    class KnowledgeEntry:
                        def __init__(self, r):
                            self.id = str(r['knowledge_id'])
                            self.content = r['knowledge_content']
                            self.user_id = str(r['user_id'])
                            self.created_at = r['knowledge_created_at']
                            self.confidence = float(r['confidence'] or 0.9)
                            self.embedding = None

                    raw = RawEntry(row)
                    knowledge = KnowledgeEntry(row)

                    # Validate the pair
                    result = await validator.validate(raw, knowledge)
                    stats["pairs_validated"] += 1

                    if result.is_consistent:
                        stats["consistent_count"] += 1
                    else:
                        stats["inconsistent_count"] += 1

                        # Flag for review if inconsistent
                        flagged = await validator.flag_if_inconsistent(result)
                        if flagged:
                            stats["flagged_for_review"] += 1

                except Exception as e:
                    logger.warning(
                        f"[CrossValidation] Failed to validate pair "
                        f"raw={row['raw_id']}, knowledge={row['knowledge_id']}: {e}"
                    )
                    stats["errors"] += 1

        # Get final validator stats
        validator_stats = validator.get_stats()

        logger.info(
            f"[CrossValidation] Complete: {stats['pairs_validated']}/{stats['input_count']} pairs, "
            f"{stats['consistent_count']} consistent, "
            f"{stats['inconsistent_count']} inconsistent, "
            f"{stats['flagged_for_review']} flagged for review, "
            f"consistency_rate={validator_stats['consistency_rate']:.1%}"
        )

    except Exception as e:
        logger.error(f"[CrossValidation] Job failed: {e}")
        stats["errors"] += 1
        stats["error_summary"] = str(e)[:500]

    return stats


async def run_cross_validation_tracked() -> Dict[str, Any]:
    """Run cross-validation with full job tracking."""
    window_end = datetime.utcnow()
    window_start = window_end - timedelta(days=7)

    return await run_job_with_tracking(
        job_name="cross_validation",
        job_version="v1.0",
        job_func=cross_validation_job,
        window_start=window_start,
        window_end=window_end
    )


# ============================================================
# KNOWLEDGE COMPACTION JOB (Weekly, Monday 4AM)
# ============================================================

async def knowledge_compaction_job(
    tenant_id: str = "default"
) -> Dict[str, Any]:
    """Compact knowledge from Level 2 → Level 3 → Level 4.

    Cognitive Principle: LSM-Tree Consolidation

    Like Log-Structured Merge-Trees in databases, knowledge consolidates
    from volatile to stable stores over time:
    - Level 2 (Knowledge): Individual extracted facts
    - Level 3 (Topics): Synthesized topic summaries
    - Level 4 (Domains): Cross-topic domain maps

    This job:
    1. Clusters Knowledge entries by topic
    2. Synthesizes topic summaries using LLM
    3. Creates domain maps from related topics
    4. Stores results in Weaviate collections

    Expected Impact:
    - Higher-order knowledge synthesis
    - Expertise-calibrated responses via schema context
    - Knowledge gap identification

    Args:
        tenant_id: Tenant to process

    Returns:
        Dict with compaction stats
    """
    from src.jobs.knowledge_compaction import KnowledgeCompactor
    from src.storage.database import get_db_pool

    stats = {
        "input_count": 0,
        "topics_created": 0,
        "domains_created": 0,
        "entries_processed": 0,
        "cost_usd": 0.0,
        "errors": 0
    }

    pool = await get_db_pool()

    logger.info("[KnowledgeCompaction] Starting weekly knowledge compaction job")

    try:
        # Initialize compactor
        compactor = KnowledgeCompactor()

        async with pool.acquire() as conn:
            # Get all active users with knowledge entries
            users = await conn.fetch("""
                SELECT DISTINCT user_id
                FROM knowledge_entries
                WHERE tenant_id = $1
                  AND created_at >= NOW() - INTERVAL '30 days'
            """, tenant_id)

            stats["input_count"] = len(users)

            if not users:
                logger.info("[KnowledgeCompaction] No users with recent knowledge entries")
                return stats

            # Compact for each user
            for user_row in users:
                user_id = str(user_row['user_id'])

                try:
                    # Level 2 → Level 3: Knowledge → Topics
                    topic_result = await compactor.compact_to_topic_summaries(
                        user_id=user_id,
                        tenant_id=tenant_id
                    )
                    stats["topics_created"] += topic_result.get("topics_created", 0)
                    stats["entries_processed"] += topic_result.get("entries_processed", 0)
                    stats["cost_usd"] += topic_result.get("cost_usd", 0.0)
                    stats["errors"] += topic_result.get("errors", 0)

                    # Level 3 → Level 4: Topics → Domains
                    domain_result = await compactor.compact_to_domain_maps(
                        user_id=user_id,
                        tenant_id=tenant_id
                    )
                    stats["domains_created"] += domain_result.get("domains_created", 0)
                    stats["cost_usd"] += domain_result.get("cost_usd", 0.0)
                    stats["errors"] += domain_result.get("errors", 0)

                except Exception as e:
                    logger.error(f"[KnowledgeCompaction] User {user_id} failed: {e}")
                    stats["errors"] += 1

        # Get final compactor stats
        compactor_stats = compactor.get_stats()

        logger.info(
            f"[KnowledgeCompaction] Complete: "
            f"{stats['topics_created']} topics, "
            f"{stats['domains_created']} domains, "
            f"${stats['cost_usd']:.4f} spent"
        )

    except Exception as e:
        logger.error(f"[KnowledgeCompaction] Job failed: {e}")
        stats["errors"] += 1
        stats["error_summary"] = str(e)[:500]

    return stats


async def run_knowledge_compaction_tracked() -> Dict[str, Any]:
    """Run knowledge compaction with full job tracking."""
    window_end = datetime.utcnow()
    window_start = window_end - timedelta(days=30)  # Process last 30 days

    return await run_job_with_tracking(
        job_name="knowledge_compaction",
        job_version="v1.0",
        job_func=knowledge_compaction_job,
        window_start=window_start,
        window_end=window_end
    )


# ============================================================
# CREATIVE RECOMBINATION JOB (Sunday 3AM)
# ============================================================

async def creative_recombination_job(
    max_discoveries: int = 5,
    tenant_id: str = "default"
) -> Dict[str, Any]:
    """Discover cross-domain connections through creative recombination.

    Cognitive Principle: REM Sleep Creative Discovery

    During REM sleep, the brain replays and recombines memories from different
    contexts, leading to novel insights and creative problem-solving. The
    prefrontal cortex is less active, allowing unusual associations to form.

    This job:
    1. Finds shared entities across distant topic clusters
    2. Detects structural analogies (A:B :: C:D patterns)
    3. Identifies bridging queries that connect domains
    4. Generates human-readable insight text

    Expected Impact:
    - Cross-domain insight discovery
    - Hidden pattern identification
    - "Aha!" moments from knowledge connections

    Args:
        max_discoveries: Maximum discoveries per user per run
        tenant_id: Tenant to process

    Returns:
        Dict with discovery stats
    """
    from src.jobs.creative_recombination import CreativeRecombinator, RecombinatorConfig
    from src.storage.database import get_db_pool

    stats = {
        "input_count": 0,
        "users_processed": 0,
        "total_discoveries": 0,
        "discoveries_by_type": {
            "cross_domain_entity": 0,
            "structural_analogy": 0,
            "bridging_query": 0,
        },
        "errors": 0
    }

    pool = await get_db_pool()

    logger.info("[CreativeRecombination] Starting weekly creative discovery job")

    try:
        # Initialize recombinator with config
        recombinator = CreativeRecombinator(
            config=RecombinatorConfig(
                min_domain_distance=0.5,
                min_novelty_score=0.4,
                max_discoveries_per_run=max_discoveries
            )
        )

        async with pool.acquire() as conn:
            # Get all users with topic summaries
            users = await conn.fetch("""
                SELECT DISTINCT user_id
                FROM topic_extractions
                WHERE tenant_id = $1
                  AND created_at >= NOW() - INTERVAL '30 days'
            """, tenant_id)

            stats["input_count"] = len(users)

            if not users:
                logger.info("[CreativeRecombination] No users with recent topic extractions")
                return stats

            # Discover for each user
            for user_row in users:
                user_id = str(user_row['user_id'])

                try:
                    result = await recombinator.discover_cross_domain_connections(
                        user_id=user_id,
                        tenant_id=tenant_id
                    )

                    if result.get("discoveries"):
                        stats["users_processed"] += 1
                        stats["total_discoveries"] += result.get("discovery_count", 0)

                        # Count by type
                        for discovery in result["discoveries"]:
                            dtype = discovery.get("discovery_type", discovery.get("type", ""))
                            if dtype in stats["discoveries_by_type"]:
                                stats["discoveries_by_type"][dtype] += 1

                except Exception as e:
                    logger.error(f"[CreativeRecombination] User {user_id} failed: {e}")
                    stats["errors"] += 1

        # Get final recombinator stats
        recombinator_stats = recombinator.get_stats()

        logger.info(
            f"[CreativeRecombination] Complete: "
            f"{stats['users_processed']}/{stats['input_count']} users, "
            f"{stats['total_discoveries']} discoveries found"
        )

    except Exception as e:
        logger.error(f"[CreativeRecombination] Job failed: {e}")
        stats["errors"] += 1
        stats["error_summary"] = str(e)[:500]

    return stats


async def run_creative_recombination_tracked() -> Dict[str, Any]:
    """Run creative recombination with full job tracking."""
    window_end = datetime.utcnow()
    window_start = window_end - timedelta(days=30)  # Analyze last 30 days

    return await run_job_with_tracking(
        job_name="creative_recombination",
        job_version="v1.0",
        job_func=creative_recombination_job,
        window_start=window_start,
        window_end=window_end
    )


# ============================================================
# EMAIL INSIGHT EXTRACTION JOB (Hourly at :45)
# ============================================================

async def email_insight_extraction_job(
    batch_size: int = 50,
    use_llm_fallback: bool = True,
    llm_budget_usd: float = 0.05,
    tenant_id: str = "default"
) -> Dict[str, Any]:
    """Extract insights from recent emails.

    Extracts:
    - Action items (review, send, approve requests)
    - Deadlines (dates, ASAP, urgent)
    - Topics from subjects
    - Sender relationship signals

    Uses rule-based extraction first (free), LLM fallback for complex cases.

    Args:
        batch_size: Max emails to process per run
        use_llm_fallback: Whether to use Gemini Flash for complex emails
        llm_budget_usd: Max LLM spend per hour
        tenant_id: Tenant to process

    Returns:
        Dict with processing stats
    """
    from src.intelligence.email_insight_extractor import EmailInsightExtractor
    from src.intelligence.insight_extractor import InsightStorage

    stats = {
        "input_count": 0,
        "affected_count": 0,
        "insights_created": 0,
        "insights_vectorized": 0,
        "errors": 0,
        "cost_usd": 0.0
    }

    try:
        # Initialize extractor
        extractor = EmailInsightExtractor(
            use_llm_fallback=use_llm_fallback,
            llm_budget_per_hour=llm_budget_usd
        )

        # Extract insights from unprocessed emails
        result = await extractor.extract_batch(limit=batch_size)

        stats["input_count"] = result.total_processed
        stats["insights_created"] = result.insights_created
        stats["errors"] = result.errors

        if result.insights:
            # Save to PostgreSQL
            storage = InsightStorage()
            saved = await storage.save_batch(result.insights)
            stats["affected_count"] = saved

            # Vectorize for semantic search (async, don't block)
            try:
                vectorized = await storage.vectorize_pending(limit=batch_size)
                stats["insights_vectorized"] = vectorized
            except Exception as e:
                logger.warning(f"[EmailInsights] Vectorization failed: {e}")

        logger.info(
            f"[EmailInsights] Complete: {stats['input_count']} emails processed, "
            f"{stats['insights_created']} insights created, "
            f"{stats['insights_vectorized']} vectorized"
        )

    except Exception as e:
        logger.error(f"[EmailInsights] Job failed: {e}")
        stats["errors"] += 1

    return stats


async def run_email_insight_extraction_tracked() -> Dict[str, Any]:
    """Run email insight extraction with full job tracking."""
    window_end = datetime.utcnow()
    window_start = window_end - timedelta(hours=1)

    return await run_job_with_tracking(
        job_name="email_insight_extraction",
        job_version="v1.0",
        job_func=email_insight_extraction_job,
        window_start=window_start,
        window_end=window_end
    )


# ============================================================
# PORTFOLIO SYNC JOB (Daily)
# ============================================================

async def portfolio_sync_job(
    tenant_id: str = "default"
) -> Dict[str, Any]:
    """Sync investment portfolio from connected Plaid accounts.

    Pulls holdings and transactions from all connected brokerage accounts.
    Runs daily to keep portfolio data fresh for Constitution rule evaluation.

    Args:
        tenant_id: Tenant to process

    Returns:
        Dict with sync stats
    """
    stats = {
        "input_count": 0,
        "affected_count": 0,
        "items_synced": 0,
        "securities": 0,
        "positions": 0,
        "transactions": 0,
        "errors": 0
    }

    try:
        from src.integrations.plaid import PlaidSyncService
        from src.storage.database import get_db_pool

        pool = await get_db_pool()

        async with pool.acquire() as conn:
            # Get all active Plaid items for this tenant
            items = await conn.fetch("""
                SELECT item_id, institution_name
                FROM plaid_tokens
                WHERE user_id = $1
                  AND is_active = true
                  AND error_code IS NULL
            """, tenant_id)

            stats["input_count"] = len(items)

            if not items:
                logger.info("[PortfolioSync] No active Plaid items")
                return stats

        # Initialize sync service
        sync_service = PlaidSyncService(db_pool=pool)

        # Sync each item
        for item in items:
            try:
                result = await sync_service.sync_item(item["item_id"])
                stats["items_synced"] += 1
                stats["securities"] += result.get("securities", 0)
                stats["positions"] += result.get("positions", 0)
                stats["transactions"] += result.get("transactions", 0)
                stats["affected_count"] += 1

                logger.info(
                    f"[PortfolioSync] Synced {item['institution_name']}: "
                    f"{result.get('positions', 0)} positions"
                )
            except Exception as e:
                logger.error(f"[PortfolioSync] Failed to sync {item['institution_name']}: {e}")
                stats["errors"] += 1

        logger.info(
            f"[PortfolioSync] Complete: {stats['items_synced']}/{stats['input_count']} items, "
            f"{stats['positions']} positions, {stats['transactions']} transactions"
        )

    except Exception as e:
        logger.error(f"[PortfolioSync] Job failed: {e}")
        stats["errors"] += 1

    return stats


async def run_portfolio_sync_tracked() -> Dict[str, Any]:
    """Run portfolio sync with full job tracking."""
    window_end = datetime.utcnow()
    window_start = window_end - timedelta(days=1)

    return await run_job_with_tracking(
        job_name="portfolio_sync",
        job_version="v1.0",
        job_func=portfolio_sync_job,
        window_start=window_start,
        window_end=window_end
    )


# ============================================================
# CLI ENTRY POINT
# ============================================================

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    parser = argparse.ArgumentParser(
        description="Run ACMS intelligence jobs manually"
    )
    parser.add_argument(
        "job",
        choices=["topic_extraction", "insight_generation", "weekly_report", "cross_validation", "knowledge_compaction", "creative_recombination", "email_insights", "portfolio_sync", "all"],
        help="Job to run"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )

    args = parser.parse_args()

    async def main():
        if args.dry_run:
            print(f"Would run: {args.job}")
            return

        if args.job == "topic_extraction":
            result = await run_topic_extraction_tracked()
        elif args.job == "insight_generation":
            result = await run_insight_generation_tracked()
        elif args.job == "weekly_report":
            result = await run_weekly_report_tracked()
        elif args.job == "cross_validation":
            result = await run_cross_validation_tracked()
        elif args.job == "knowledge_compaction":
            result = await run_knowledge_compaction_tracked()
        elif args.job == "creative_recombination":
            result = await run_creative_recombination_tracked()
        elif args.job == "email_insights":
            result = await run_email_insight_extraction_tracked()
        elif args.job == "portfolio_sync":
            result = await run_portfolio_sync_tracked()
        elif args.job == "all":
            print("Running all intelligence jobs...")
            result = {}
            result["topic_extraction"] = await run_topic_extraction_tracked()
            result["insight_generation"] = await run_insight_generation_tracked()
            result["weekly_report"] = await run_weekly_report_tracked()
            result["cross_validation"] = await run_cross_validation_tracked()
            result["knowledge_compaction"] = await run_knowledge_compaction_tracked()
            result["creative_recombination"] = await run_creative_recombination_tracked()
            result["email_insights"] = await run_email_insight_extraction_tracked()
            result["portfolio_sync"] = await run_portfolio_sync_tracked()

        print(f"\nJob result: {result}")

    asyncio.run(main())
