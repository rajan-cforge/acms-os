"""
Cognitive Architecture API Endpoints.

Feb 2026 - Exposes cognitive features to the UI:
- Expertise profiles
- Knowledge health metrics
- Cross-domain discoveries
- Co-retrieval associations
- Topic summaries
- Weekly digest
"""

import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.storage.database import get_db_pool

router = APIRouter(prefix="/api", tags=["Cognitive Architecture"])


# Domain classification for topics
DOMAIN_MAP = {
    "llm": "ai", "claude": "ai", "gemini": "ai", "openai": "ai", "chatgpt": "ai", "embedding": "ai",
    "python": "programming", "go": "programming", "golang": "programming", "fastapi": "programming",
    "javascript": "programming", "typescript": "programming", "code-review": "programming",
    "kubernetes": "infrastructure", "docker": "infrastructure", "aws": "infrastructure",
    "monitoring": "infrastructure", "helm": "infrastructure", "prometheus": "infrastructure",
    "security": "security", "rbac": "security", "oauth": "security",
    "weaviate": "data", "postgresql": "data", "database": "data", "redis": "data",
    "finance": "business", "business": "business", "project-mgmt": "business",
    "testing": "quality",
    "writing": "communication",
    "http": "networking", "api": "networking",
}


def determine_expertise_level(topic_depth: int, total: int) -> str:
    """Determine expertise level using percentile + logarithmic scaling."""
    if topic_depth == 0:
        return "first_encounter"
    if total == 0:
        return "beginner"

    relative_share = topic_depth / max(total, 1)
    log_depth = math.log2(topic_depth + 1)
    normalized_log = min(log_depth / 10.0, 1.0)
    normalized_relative = min(relative_share / 0.20, 1.0)
    combined_score = (normalized_log * 0.6) + (normalized_relative * 0.4)

    if combined_score >= 0.75:
        return "expert"
    elif combined_score >= 0.50:
        return "advanced"
    elif combined_score >= 0.25:
        return "intermediate"
    elif topic_depth >= 3:
        return "beginner"
    else:
        return "first_encounter"


# ─── Response Models ─────────────────────────────────────────────

class TopicExpertise(BaseModel):
    topic: str
    depth: int
    level: str
    relative_share: float
    domain: str


class ExpertiseProfileResponse(BaseModel):
    total_queries: int
    topic_count: int
    profile: list[TopicExpertise]


class KnowledgeHealthResponse(BaseModel):
    total_entries: int
    topics_covered: int
    consistency_score: float
    needs_review: int
    last_compaction: Optional[str]


class DiscoveryItem(BaseModel):
    bridge: str
    domain_a: str
    domain_b: str
    session_count: int
    topics_involved: list[str]
    insight: str
    creativity_score: float
    status: str


class DiscoveriesResponse(BaseModel):
    count: int
    discoveries: list[DiscoveryItem]


class AssociationItem(BaseModel):
    topic: str
    strength: float
    co_retrieval_count: int


class AssociationsResponse(BaseModel):
    topic: str
    associations: list[AssociationItem]


class TopicSummaryResponse(BaseModel):
    topic_slug: str
    knowledge_depth: int
    expertise_level: str
    key_concepts: list[str]
    sample_questions: list[str]
    first_interaction: Optional[str]
    last_interaction: Optional[str]
    knowledge_gaps: list[str]


class WeeklyDigestStats(BaseModel):
    interactions: int
    topics_active: int
    new_topics: list[str]


class WeeklyDigestResponse(BaseModel):
    period_start: str
    period_end: str
    stats: WeeklyDigestStats
    top_topics: list[TopicExpertise]
    discoveries: list[DiscoveryItem]
    health: KnowledgeHealthResponse


# ─── API Endpoints ───────────────────────────────────────────────

@router.get("/expertise", response_model=ExpertiseProfileResponse)
async def get_expertise_profile():
    """Returns the user's expertise profile across all topics."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT primary_topic, COUNT(*) as count
            FROM topic_extractions
            WHERE primary_topic IS NOT NULL
              AND primary_topic NOT IN ('transient', '', 'general')
            GROUP BY primary_topic
            ORDER BY count DESC
        """)

    if not rows:
        return ExpertiseProfileResponse(total_queries=0, topic_count=0, profile=[])

    topic_counts = {row['primary_topic']: row['count'] for row in rows}
    total = sum(topic_counts.values())

    profile = []
    for topic, depth in topic_counts.items():
        level = determine_expertise_level(depth, total)
        profile.append(TopicExpertise(
            topic=topic,
            depth=depth,
            level=level,
            relative_share=round(depth / total * 100, 1),
            domain=DOMAIN_MAP.get(topic.lower(), 'other'),
        ))

    return ExpertiseProfileResponse(
        total_queries=total,
        topic_count=len(profile),
        profile=profile,
    )


@router.get("/knowledge-health", response_model=KnowledgeHealthResponse)
async def get_knowledge_health():
    """Returns knowledge base health metrics."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        # Count total entries
        total = await conn.fetchval("""
            SELECT COUNT(*) FROM topic_extractions
            WHERE primary_topic IS NOT NULL
        """)

        # Count topics
        topic_count = await conn.fetchval("""
            SELECT COUNT(DISTINCT primary_topic)
            FROM topic_extractions
            WHERE primary_topic IS NOT NULL
              AND primary_topic NOT IN ('transient', '', 'general')
        """)

        # Count items needing review
        try:
            needs_review = await conn.fetchval("""
                SELECT COUNT(*)
                FROM knowledge_review_queue
                WHERE status = 'pending'
            """) or 0
        except Exception:
            needs_review = 0

        # Check for last compaction (from job runs)
        try:
            last_compaction = await conn.fetchval("""
                SELECT MAX(completed_at)
                FROM scheduled_job_runs
                WHERE job_name LIKE '%compaction%'
                  AND status = 'success'
            """)
        except Exception:
            last_compaction = None

    return KnowledgeHealthResponse(
        total_entries=total or 0,
        topics_covered=topic_count or 0,
        consistency_score=98.0,  # Could be calculated from cross_validation table
        needs_review=needs_review,
        last_compaction=last_compaction.isoformat() if last_compaction else None,
    )


@router.get("/discoveries", response_model=DiscoveriesResponse)
async def get_discoveries(
    limit: int = Query(default=20, le=100),
    status: Optional[str] = Query(default=None),
):
    """Returns cross-domain insights."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        query = """
            SELECT bridge, domain_a, domain_b, session_count,
                   topics_involved, insight, creativity_score, status
            FROM cross_domain_discoveries
        """
        if status:
            query += f" WHERE status = '{status}'"
        query += " ORDER BY session_count DESC LIMIT $1"

        rows = await conn.fetch(query, limit)

    discoveries = [
        DiscoveryItem(
            bridge=row['bridge'],
            domain_a=row['domain_a'],
            domain_b=row['domain_b'],
            session_count=row['session_count'],
            topics_involved=row['topics_involved'] or [],
            insight=row['insight'],
            creativity_score=row['creativity_score'],
            status=row['status'],
        )
        for row in rows
    ]

    return DiscoveriesResponse(count=len(discoveries), discoveries=discoveries)


@router.get("/associations/{topic}", response_model=AssociationsResponse)
async def get_associations(
    topic: str,
    limit: int = Query(default=10, le=50),
    min_strength: float = Query(default=0.0),
):
    """Returns topics associated with the given topic via co-retrieval."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        # Search both directions since edges are stored with alphabetical ordering
        rows = await conn.fetch("""
            SELECT
                CASE WHEN item_a_id = $1 THEN item_b_id ELSE item_a_id END as related_topic,
                strength,
                co_retrieval_count
            FROM coretrieval_edges
            WHERE (item_a_id = $1 OR item_b_id = $1)
              AND strength >= $2
            ORDER BY strength DESC
            LIMIT $3
        """, topic, min_strength, limit)

    associations = [
        AssociationItem(
            topic=row['related_topic'],
            strength=round(row['strength'], 2),
            co_retrieval_count=row['co_retrieval_count'],
        )
        for row in rows
    ]

    return AssociationsResponse(topic=topic, associations=associations)


@router.get("/topic/{topic_slug}", response_model=TopicSummaryResponse)
async def get_topic_detail(topic_slug: str):
    """Returns detailed topic summary including sample questions."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT topic_slug, knowledge_depth, expertise_level,
                   key_concepts, sample_questions,
                   first_interaction, last_interaction, knowledge_gaps
            FROM topic_summaries
            WHERE topic_slug = $1
        """, topic_slug)

    if not row:
        raise HTTPException(status_code=404, detail=f"No data for topic: {topic_slug}")

    return TopicSummaryResponse(
        topic_slug=row['topic_slug'],
        knowledge_depth=row['knowledge_depth'],
        expertise_level=row['expertise_level'],
        key_concepts=row['key_concepts'] or [],
        sample_questions=row['sample_questions'] or [],
        first_interaction=row['first_interaction'].isoformat() if row['first_interaction'] else None,
        last_interaction=row['last_interaction'].isoformat() if row['last_interaction'] else None,
        knowledge_gaps=row['knowledge_gaps'] or [],
    )


@router.get("/digest/weekly", response_model=WeeklyDigestResponse)
async def get_weekly_digest():
    """Returns the weekly cognitive digest data."""
    pool = await get_db_pool()
    now = datetime.now(timezone.utc)
    week_ago = now - timedelta(days=7)

    async with pool.acquire() as conn:
        # This week's activity
        interactions = await conn.fetchval("""
            SELECT COUNT(*)
            FROM query_history
            WHERE created_at >= $1
        """, week_ago)

        # Unique topics this week
        topics_active = await conn.fetchval("""
            SELECT COUNT(DISTINCT primary_topic)
            FROM topic_extractions te
            JOIN query_history qh ON qh.query_id = te.source_id
                AND te.source_type = 'query_history'
            WHERE qh.created_at >= $1
              AND te.primary_topic IS NOT NULL
        """, week_ago)

        # New topics (first seen this week)
        new_topics = await conn.fetch("""
            SELECT ts.topic_slug
            FROM topic_summaries ts
            WHERE ts.first_interaction >= $1
            ORDER BY ts.knowledge_depth DESC
            LIMIT 5
        """, week_ago)

        # Top topics this week
        top_topics = await conn.fetch("""
            SELECT te.primary_topic, COUNT(*) as count
            FROM topic_extractions te
            JOIN query_history qh ON qh.query_id = te.source_id
                AND te.source_type = 'query_history'
            WHERE qh.created_at >= $1
              AND te.primary_topic IS NOT NULL
              AND te.primary_topic NOT IN ('transient', '', 'general')
            GROUP BY te.primary_topic
            ORDER BY count DESC
            LIMIT 10
        """, week_ago)

        # Recent discoveries
        discoveries = await conn.fetch("""
            SELECT bridge, domain_a, domain_b, session_count,
                   topics_involved, insight, creativity_score, status
            FROM cross_domain_discoveries
            WHERE status = 'confirmed'
            ORDER BY session_count DESC
            LIMIT 5
        """)

    # Calculate total for relative share
    total = sum(t['count'] for t in top_topics)

    top_topics_list = [
        TopicExpertise(
            topic=t['primary_topic'],
            depth=t['count'],
            level=determine_expertise_level(t['count'], total),
            relative_share=round(t['count'] / total * 100, 1) if total > 0 else 0,
            domain=DOMAIN_MAP.get(t['primary_topic'].lower(), 'other'),
        )
        for t in top_topics
    ]

    discoveries_list = [
        DiscoveryItem(
            bridge=row['bridge'],
            domain_a=row['domain_a'],
            domain_b=row['domain_b'],
            session_count=row['session_count'],
            topics_involved=row['topics_involved'] or [],
            insight=row['insight'],
            creativity_score=row['creativity_score'],
            status=row['status'],
        )
        for row in discoveries
    ]

    health = await get_knowledge_health()

    return WeeklyDigestResponse(
        period_start=week_ago.isoformat(),
        period_end=now.isoformat(),
        stats=WeeklyDigestStats(
            interactions=interactions or 0,
            topics_active=topics_active or 0,
            new_topics=[t['topic_slug'] for t in new_topics],
        ),
        top_topics=top_topics_list,
        discoveries=discoveries_list,
        health=health,
    )


@router.post("/schema-context")
async def get_schema_context(topic: str = Query(...)):
    """Get schema context for a topic (for UI expertise badge)."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        # Get all topic counts
        rows = await conn.fetch("""
            SELECT primary_topic, COUNT(*) as count
            FROM topic_extractions
            WHERE primary_topic IS NOT NULL
              AND primary_topic NOT IN ('transient', '', 'general')
            GROUP BY primary_topic
        """)

    if not rows:
        return {"level": "beginner", "depth": 0, "topic": topic}

    topic_counts = {row['primary_topic']: row['count'] for row in rows}
    total = sum(topic_counts.values())

    # Find matching topic
    depth = topic_counts.get(topic, 0)

    # Also try case-insensitive match
    if depth == 0:
        for t, c in topic_counts.items():
            if t.lower() == topic.lower():
                depth = c
                topic = t
                break

    level = determine_expertise_level(depth, total)

    return {
        "topic": topic,
        "level": level,
        "depth": depth,
        "relative_share": round(depth / total * 100, 1) if total > 0 else 0,
    }
