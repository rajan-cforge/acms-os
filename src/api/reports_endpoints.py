"""Reports & Insights API Endpoints.

Sprint 5: Reports & Insights for UX Improvements

REST API for generating and viewing reports, insights, and analytics.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.storage.database import get_db_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/reports", tags=["reports"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class TopTopic(BaseModel):
    """Top topic with query count."""
    topic: str
    count: int
    trend: str  # 'up', 'down', 'stable'
    trend_percent: float


class AgentUsage(BaseModel):
    """Agent usage statistics."""
    agent: str
    queries: int
    percentage: float
    avg_latency_ms: float
    cost: float


class KnowledgeMetrics(BaseModel):
    """Knowledge growth metrics."""
    new_memories: int
    facts_extracted: int
    cache_hits: int
    cache_hit_rate: float
    knowledge_verified: int


class InsightItem(BaseModel):
    """Individual insight."""
    insight_id: str
    insight_type: str  # 'pattern', 'recommendation', 'observation'
    title: str
    description: str
    confidence: float
    created_at: datetime
    source_count: int


class WeeklyReport(BaseModel):
    """Weekly report data."""
    report_id: Optional[str] = None
    week_start: str
    week_end: str
    total_queries: int
    unique_topics: int
    top_topics: List[TopTopic]
    agent_usage: List[AgentUsage]
    knowledge: KnowledgeMetrics
    insights: List[InsightItem]
    highlights: List[str]


class ReportListItem(BaseModel):
    """Report list item."""
    report_id: str
    report_type: str
    week_start: str
    week_end: str
    generated_at: datetime
    total_queries: int


class DashboardStats(BaseModel):
    """Dashboard statistics."""
    total_memories: int
    total_queries_today: int
    total_queries_week: int
    cache_hit_rate: float
    knowledge_items: int
    verified_items: int
    top_agent: str
    active_topics: int


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(user_id: str = Query("default")):
    """Get dashboard statistics overview."""
    pool = await get_db_pool()
    today = date.today()
    week_start = today - timedelta(days=7)

    async with pool.acquire() as conn:
        # Total memories
        total_memories = await conn.fetchval("""
            SELECT COUNT(*) FROM query_history
            WHERE created_at >= NOW() - INTERVAL '90 days'
        """) or 0

        # Queries today
        queries_today = await conn.fetchval("""
            SELECT COUNT(*) FROM query_history
            WHERE DATE(created_at) = $1
        """, today) or 0

        # Queries this week
        queries_week = await conn.fetchval("""
            SELECT COUNT(*) FROM query_history
            WHERE created_at >= $1
        """, week_start) or 0

        # Cache stats (from quality_cache_entries if exists)
        cache_hit_rate = 0.0
        try:
            cache_stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE hit_count > 0) as hits
                FROM quality_cache_entries
                WHERE created_at >= NOW() - INTERVAL '7 days'
            """)
            if cache_stats and cache_stats['total'] > 0:
                cache_hit_rate = (cache_stats['hits'] / cache_stats['total']) * 100
        except Exception:
            pass  # Table may not exist yet

        # Knowledge items (try consolidated_knowledge, fallback to 0)
        knowledge_items = 0
        verified_items = 0
        try:
            knowledge_items = await conn.fetchval("""
                SELECT COUNT(*) FROM consolidated_knowledge
                WHERE is_active = TRUE
            """) or 0
            verified_items = await conn.fetchval("""
                SELECT COUNT(*) FROM consolidated_knowledge
                WHERE is_active = TRUE AND is_verified = TRUE
            """) or 0
        except Exception:
            pass  # Table may not exist yet

        # Top agent (use response_source column)
        top_agent_row = await conn.fetchrow("""
            SELECT response_source, COUNT(*) as count
            FROM query_history
            WHERE created_at >= $1 AND response_source IS NOT NULL
            GROUP BY response_source
            ORDER BY count DESC
            LIMIT 1
        """, week_start)
        top_agent = top_agent_row['response_source'] if top_agent_row else 'Claude'

        # Active topics (handle missing table)
        active_topics = 0
        try:
            active_topics = await conn.fetchval("""
                SELECT COUNT(DISTINCT topic)
                FROM topic_extractions
                WHERE created_at >= NOW() - INTERVAL '7 days'
            """) or 0
        except Exception:
            pass  # Table may not exist

        return DashboardStats(
            total_memories=total_memories,
            total_queries_today=queries_today,
            total_queries_week=queries_week,
            cache_hit_rate=round(cache_hit_rate, 1),
            knowledge_items=knowledge_items,
            verified_items=verified_items,
            top_agent=top_agent,
            active_topics=active_topics
        )


# ============================================================================
# WEEKLY REPORT ENDPOINTS
# ============================================================================

@router.get("/weekly/current", response_model=WeeklyReport)
async def get_current_week_report(user_id: str = Query("default")):
    """Get report for current week."""
    today = date.today()
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)  # Sunday

    return await _generate_weekly_report(week_start, week_end, user_id)


@router.get("/weekly/{week_start_date}", response_model=WeeklyReport)
async def get_week_report(
    week_start_date: str,
    user_id: str = Query("default")
):
    """Get report for a specific week."""
    try:
        week_start = date.fromisoformat(week_start_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    week_end = week_start + timedelta(days=6)
    return await _generate_weekly_report(week_start, week_end, user_id)


async def _generate_weekly_report(
    week_start: date,
    week_end: date,
    user_id: str
) -> WeeklyReport:
    """Generate weekly report data."""
    pool = await get_db_pool()
    prev_week_start = week_start - timedelta(days=7)
    prev_week_end = week_start - timedelta(days=1)

    async with pool.acquire() as conn:
        # Total queries
        total_queries = await conn.fetchval("""
            SELECT COUNT(*) FROM query_history
            WHERE DATE(created_at) BETWEEN $1 AND $2
        """, week_start, week_end) or 0

        # Unique topics (use primary_topic column)
        unique_topics = await conn.fetchval("""
            SELECT COUNT(DISTINCT primary_topic)
            FROM topic_extractions
            WHERE DATE(created_at) BETWEEN $1 AND $2 AND primary_topic IS NOT NULL
        """, week_start, week_end) or 0

        # Top topics with trend (use primary_topic)
        current_topics = await conn.fetch("""
            SELECT primary_topic as topic, COUNT(*) as count
            FROM topic_extractions
            WHERE DATE(created_at) BETWEEN $1 AND $2 AND primary_topic IS NOT NULL
            GROUP BY primary_topic
            ORDER BY count DESC
            LIMIT 10
        """, week_start, week_end)

        prev_topics = await conn.fetch("""
            SELECT primary_topic as topic, COUNT(*) as count
            FROM topic_extractions
            WHERE DATE(created_at) BETWEEN $1 AND $2 AND primary_topic IS NOT NULL
            GROUP BY primary_topic
        """, prev_week_start, prev_week_end)

        prev_topics_map = {t['topic']: t['count'] for t in prev_topics}

        top_topics = []
        for t in current_topics:
            prev_count = prev_topics_map.get(t['topic'], 0)
            if prev_count == 0:
                trend = 'up'
                trend_percent = 100.0
            elif t['count'] > prev_count:
                trend = 'up'
                trend_percent = ((t['count'] - prev_count) / prev_count) * 100
            elif t['count'] < prev_count:
                trend = 'down'
                trend_percent = ((prev_count - t['count']) / prev_count) * 100
            else:
                trend = 'stable'
                trend_percent = 0.0

            top_topics.append(TopTopic(
                topic=t['topic'],
                count=t['count'],
                trend=trend,
                trend_percent=round(trend_percent, 1)
            ))

        # Agent usage (use response_source column)
        agent_stats = await conn.fetch("""
            SELECT
                response_source as agent_type,
                COUNT(*) as queries,
                AVG(total_latency_ms) as avg_latency
            FROM query_history
            WHERE DATE(created_at) BETWEEN $1 AND $2
              AND response_source IS NOT NULL
            GROUP BY response_source
            ORDER BY queries DESC
        """, week_start, week_end)

        total_agent_queries = sum(a['queries'] for a in agent_stats)
        agent_usage = [
            AgentUsage(
                agent=a['agent_type'],
                queries=a['queries'],
                percentage=round((a['queries'] / total_agent_queries) * 100, 1) if total_agent_queries > 0 else 0,
                avg_latency_ms=round(a['avg_latency'] or 0, 0),
                cost=0  # Cost calculation would need additional data
            )
            for a in agent_stats
        ]

        # Knowledge metrics
        new_memories = await conn.fetchval("""
            SELECT COUNT(*) FROM query_history
            WHERE DATE(created_at) BETWEEN $1 AND $2
        """, week_start, week_end) or 0

        facts_extracted = await conn.fetchval("""
            SELECT COUNT(*) FROM topic_extractions
            WHERE DATE(created_at) BETWEEN $1 AND $2
        """, week_start, week_end) or 0

        # Cache stats (handle missing table)
        cache_hits = 0
        cache_total = 1
        try:
            cache_hits = await conn.fetchval("""
                SELECT COALESCE(SUM(hit_count), 0)
                FROM quality_cache_entries
                WHERE DATE(created_at) BETWEEN $1 AND $2
            """, week_start, week_end) or 0
            cache_total = await conn.fetchval("""
                SELECT COUNT(*) FROM quality_cache_entries
                WHERE DATE(created_at) BETWEEN $1 AND $2
            """, week_start, week_end) or 1
        except Exception:
            pass  # Table may not exist

        cache_hit_rate = (cache_hits / cache_total) * 100 if cache_total > 0 else 0

        # Knowledge verified (handle missing table)
        knowledge_verified = 0
        try:
            knowledge_verified = await conn.fetchval("""
                SELECT COUNT(*) FROM consolidated_knowledge
                WHERE is_verified = TRUE
                  AND DATE(verified_at) BETWEEN $1 AND $2
            """, week_start, week_end) or 0
        except Exception:
            pass  # Table may not exist

        knowledge = KnowledgeMetrics(
            new_memories=new_memories,
            facts_extracted=facts_extracted,
            cache_hits=cache_hits,
            cache_hit_rate=round(cache_hit_rate, 1),
            knowledge_verified=knowledge_verified
        )

        # Insights (from patterns/insights if they exist)
        insights = []
        try:
            insight_rows = await conn.fetch("""
                SELECT
                    id::text as insight_id,
                    insight_type,
                    title,
                    description,
                    confidence,
                    created_at,
                    1 as source_count
                FROM insights
                WHERE DATE(created_at) BETWEEN $1 AND $2
                ORDER BY confidence DESC
                LIMIT 5
            """, week_start, week_end)

            insights = [
                InsightItem(
                    insight_id=r['insight_id'],
                    insight_type=r['insight_type'] or 'observation',
                    title=r['title'] or 'Insight',
                    description=r['description'] or '',
                    confidence=r['confidence'] or 0.5,
                    created_at=r['created_at'],
                    source_count=r['source_count']
                )
                for r in insight_rows
            ]
        except Exception:
            # Insights table might not exist
            pass

        # Generate highlights
        highlights = []
        if total_queries > 0:
            highlights.append(f"You asked {total_queries} questions this week")
        if len(top_topics) > 0:
            highlights.append(f"Top topic: {top_topics[0].topic} ({top_topics[0].count} mentions)")
        if knowledge.cache_hit_rate > 50:
            highlights.append(f"Cache hit rate: {knowledge.cache_hit_rate}% - great for speed!")
        if knowledge.knowledge_verified > 0:
            highlights.append(f"You verified {knowledge.knowledge_verified} knowledge items")

        return WeeklyReport(
            week_start=week_start.isoformat(),
            week_end=week_end.isoformat(),
            total_queries=total_queries,
            unique_topics=unique_topics,
            top_topics=top_topics,
            agent_usage=agent_usage,
            knowledge=knowledge,
            insights=insights,
            highlights=highlights
        )


# ============================================================================
# INSIGHTS ENDPOINTS
# ============================================================================

@router.get("/insights", response_model=List[InsightItem])
async def get_recent_insights(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(20, ge=1, le=100),
    user_id: str = Query("default")
):
    """Get recent insights."""
    pool = await get_db_pool()
    start_date = date.today() - timedelta(days=days)

    async with pool.acquire() as conn:
        try:
            rows = await conn.fetch("""
                SELECT
                    id::text as insight_id,
                    insight_type,
                    title,
                    description,
                    confidence,
                    created_at,
                    1 as source_count
                FROM insights
                WHERE DATE(created_at) >= $1
                ORDER BY created_at DESC
                LIMIT $2
            """, start_date, limit)

            return [
                InsightItem(
                    insight_id=r['insight_id'],
                    insight_type=r['insight_type'] or 'observation',
                    title=r['title'] or 'Insight',
                    description=r['description'] or '',
                    confidence=r['confidence'] or 0.5,
                    created_at=r['created_at'],
                    source_count=r['source_count']
                )
                for r in rows
            ]
        except Exception:
            # Fallback if insights table doesn't exist
            return []


# ============================================================================
# TOPIC ANALYTICS
# ============================================================================

@router.get("/topics/trends")
async def get_topic_trends(
    days: int = Query(30, ge=7, le=90),
    user_id: str = Query("default")
):
    """Get topic trends over time."""
    pool = await get_db_pool()
    start_date = date.today() - timedelta(days=days)

    async with pool.acquire() as conn:
        # Daily topic counts
        rows = await conn.fetch("""
            SELECT
                DATE(created_at) as day,
                topic,
                COUNT(*) as count
            FROM topic_extractions
            WHERE created_at >= $1
            GROUP BY DATE(created_at), topic
            ORDER BY day, count DESC
        """, start_date)

        # Aggregate by day
        trends = {}
        for row in rows:
            day = row['day'].isoformat()
            if day not in trends:
                trends[day] = {'date': day, 'topics': {}, 'total': 0}
            trends[day]['topics'][row['topic']] = row['count']
            trends[day]['total'] += row['count']

        # Top topics overall
        top_topics = await conn.fetch("""
            SELECT topic, COUNT(*) as count
            FROM topic_extractions
            WHERE created_at >= $1
            GROUP BY topic
            ORDER BY count DESC
            LIMIT 10
        """, start_date)

        return {
            "daily": list(trends.values()),
            "top_topics": [{"topic": t['topic'], "count": t['count']} for t in top_topics]
        }


# ============================================================================
# REPORT HISTORY
# ============================================================================

@router.get("/history", response_model=List[ReportListItem])
async def get_report_history(
    limit: int = Query(10, ge=1, le=50),
    user_id: str = Query("default")
):
    """Get historical reports."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        try:
            rows = await conn.fetch("""
                SELECT
                    report_id::text,
                    report_type,
                    week_start,
                    week_end,
                    generated_at,
                    total_queries
                FROM weekly_reports
                WHERE user_id = $1
                ORDER BY generated_at DESC
                LIMIT $2
            """, user_id, limit)

            return [
                ReportListItem(
                    report_id=r['report_id'],
                    report_type=r['report_type'],
                    week_start=r['week_start'].isoformat(),
                    week_end=r['week_end'].isoformat(),
                    generated_at=r['generated_at'],
                    total_queries=r['total_queries']
                )
                for r in rows
            ]
        except Exception:
            return []
