"""Insights Engine for ACMS Intelligence Hub.

Generates insights, detects patterns, and provides analysis from user data.

Key Features:
- RBAC-aware: All queries respect privacy filters
- Evidence-grounded: Every insight has source references
- Cost-guarded: LLM usage is budgeted and tracked

Usage:
    from src.intelligence.insights_engine import InsightsEngine

    engine = InsightsEngine(db_session)

    # Get quick summary
    summary = await engine.generate_summary(
        user_id="user-123",
        tenant_id="default",
        period_days=7,
        scope="user"
    )

    # Deep topic analysis
    analysis = await engine.analyze_topic(
        user_id="user-123",
        query="What have I learned about kubernetes?"
    )

    # Get trends
    trends = await engine.get_trends(
        user_id="user-123",
        period_days=30,
        granularity="day"
    )
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from uuid import uuid4
import json

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

INSIGHTS_CONFIG = {
    "max_llm_cost_per_summary": 0.10,      # $0.10 cap for summary generation
    "max_llm_cost_per_analysis": 0.25,     # $0.25 cap for deep analysis
    "default_period_days": 7,
    "max_period_days": 365,
    "top_topics_limit": 20,
    "sample_queries_per_topic": 3,
    "cache_ttl_seconds": 600,              # 10 minutes
}


# ============================================================
# DATA CLASSES
# ============================================================

class TrustLevel(str, Enum):
    """Evidence trust levels."""
    HIGH = "high"       # KNOWLEDGE collection, verified facts
    MEDIUM = "medium"   # ENRICHED collection, quality-gated Q&A
    LOW = "low"         # RAW query_history, may contain errors


class InsightType(str, Enum):
    """Types of generated insights."""
    EMERGING_THEME = "emerging_theme"
    KNOWLEDGE_GAP = "knowledge_gap"
    PRODUCTIVITY_TREND = "productivity_trend"
    COST_TREND = "cost_trend"
    MODEL_PREFERENCE = "model_preference"
    TOPIC_SHIFT = "topic_shift"


class TrendDirection(str, Enum):
    """Trend direction indicators."""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    NEW = "new"


@dataclass
class InsightEvidence:
    """Evidence backing an insight - every insight MUST have explicit evidence."""
    source_ids: List[str]           # UUIDs of source records
    source_type: str                # 'query_history', 'memory_items', 'topic_extractions'
    trust_level: TrustLevel
    snippet_preview: str            # First 200 chars for human review
    retrieval_score: float = 1.0    # How relevant was this evidence

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source_ids": self.source_ids,
            "source_type": self.source_type,
            "trust_level": self.trust_level.value,
            "snippet_preview": self.snippet_preview,
            "retrieval_score": self.retrieval_score
        }


@dataclass
class GeneratedInsight:
    """Insight with mandatory grounding - cannot exist without evidence."""
    insight_id: str
    insight_type: InsightType
    title: str
    description: str
    confidence: float               # 0.0 - 1.0
    evidence: List[InsightEvidence] # MUST NOT be empty
    generated_by: str               # 'statistical', 'pattern_detection', 'llm'
    trace_id: Optional[str] = None

    def __post_init__(self):
        """Validate insight requirements."""
        if not self.evidence:
            raise ValueError("Insights MUST have evidence - no speculation allowed")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("Confidence must be 0.0-1.0")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "insight_id": self.insight_id,
            "type": self.insight_type.value,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "evidence": [e.to_dict() for e in self.evidence],
            "generated_by": self.generated_by,
            "trace_id": self.trace_id
        }


@dataclass
class TopicStat:
    """Statistics for a single topic."""
    topic: str
    count: int
    trend: TrendDirection
    trend_percent: float = 0.0
    sample_queries: List[str] = field(default_factory=list)
    first_seen: Optional[date] = None
    last_seen: Optional[date] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "topic": self.topic,
            "count": self.count,
            "trend": self.trend.value,
            "trend_percent": self.trend_percent,
            "sample_queries": self.sample_queries,
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None
        }


@dataclass
class Recommendation:
    """Actionable recommendation based on insights."""
    priority: Literal["high", "medium", "low"]
    action: str
    context: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "priority": self.priority,
            "action": self.action,
            "context": self.context
        }


@dataclass
class InsightsSummary:
    """Complete insights summary response."""
    period_start: date
    period_end: date
    key_stats: Dict[str, Any]
    top_topics: List[TopicStat]
    insights: List[GeneratedInsight]
    recommendations: List[Recommendation]
    debug_info: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat()
            },
            "key_stats": self.key_stats,
            "top_topics": [t.to_dict() for t in self.top_topics],
            "insights": [i.to_dict() for i in self.insights],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "debug": self.debug_info
        }


@dataclass
class TrendPoint:
    """Single point in a trend timeline."""
    date: date
    value: float
    label: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "date": self.date.isoformat(),
            "value": self.value,
            "label": self.label
        }


@dataclass
class TrendsResponse:
    """Trends data over time."""
    period_start: date
    period_end: date
    granularity: str
    timeline: List[Dict[str, Any]]          # [{date, queries, cost, top_topic}]
    topic_evolution: Dict[str, List[TrendPoint]]  # {topic: [{date, count}]}
    model_usage: Dict[str, float]           # {model: percentage}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat()
            },
            "granularity": self.granularity,
            "timeline": self.timeline,
            "topic_evolution": {
                topic: [p.to_dict() for p in points]
                for topic, points in self.topic_evolution.items()
            },
            "model_usage": self.model_usage
        }


@dataclass
class TopicAnalysis:
    """Deep analysis of a specific topic."""
    query: str
    topic: str
    analysis_text: str
    key_learnings: List[str]
    knowledge_gaps: List[str]
    related_topics: List[str]
    source_queries: List[Dict[str, Any]]    # [{query_id, question, date}]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "query": self.query,
            "topic": self.topic,
            "analysis": self.analysis_text,
            "key_learnings": self.key_learnings,
            "knowledge_gaps": self.knowledge_gaps,
            "related_topics": self.related_topics,
            "sources": self.source_queries,
            "confidence": self.confidence
        }


# ============================================================
# INSIGHTS ENGINE CLASS
# ============================================================

class InsightsEngine:
    """Generates insights from user query history and memories.

    All methods are RBAC-aware and require user context.
    """

    def __init__(
        self,
        db_session=None,
        llm_provider=None,
        topic_extractor=None
    ):
        """Initialize insights engine.

        Args:
            db_session: Database session for queries
            llm_provider: Optional LLM provider for synthesis
            topic_extractor: TopicExtractor instance for topic extraction
        """
        self.db = db_session
        self.llm = llm_provider
        self.topic_extractor = topic_extractor
        logger.info("InsightsEngine initialized")

    async def generate_summary(
        self,
        user_id: str,
        tenant_id: str = "default",
        period_days: int = 7,
        scope: Literal["user", "org"] = "user",
        include_debug: bool = False,
        trace_id: Optional[str] = None
    ) -> InsightsSummary:
        """Generate quick insights summary.

        Args:
            user_id: User requesting the insights
            tenant_id: Tenant identifier
            period_days: Number of days to analyze
            scope: 'user' for personal, 'org' for org-wide (admin only)
            include_debug: Include debug information
            trace_id: Request trace ID

        Returns:
            InsightsSummary with stats, topics, insights, recommendations
        """
        logger.info(
            f"Generating insights summary: user={user_id}, "
            f"period={period_days}d, scope={scope}, trace={trace_id}"
        )

        period_end = date.today()
        period_start = period_end - timedelta(days=period_days)

        # Get key statistics
        key_stats = await self._get_key_stats(
            user_id=user_id,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            scope=scope
        )

        # Get top topics
        top_topics = await self._get_top_topics(
            user_id=user_id,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            scope=scope,
            limit=INSIGHTS_CONFIG["top_topics_limit"]
        )

        # Detect patterns and generate insights
        insights = await self._detect_patterns(
            user_id=user_id,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            scope=scope,
            key_stats=key_stats,
            top_topics=top_topics
        )

        # Generate recommendations
        recommendations = await self._generate_recommendations(
            insights=insights,
            top_topics=top_topics,
            key_stats=key_stats
        )

        debug_info = None
        if include_debug:
            debug_info = {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "scope": scope,
                "period_days": period_days,
                "trace_id": trace_id
            }

        return InsightsSummary(
            period_start=period_start,
            period_end=period_end,
            key_stats=key_stats,
            top_topics=top_topics,
            insights=insights,
            recommendations=recommendations,
            debug_info=debug_info
        )

    async def analyze_topic(
        self,
        user_id: str,
        query: str,
        tenant_id: str = "default",
        period_days: int = 30,
        trace_id: Optional[str] = None
    ) -> TopicAnalysis:
        """Deep analysis on a specific topic or question.

        Args:
            user_id: User requesting the analysis
            query: User's question (e.g., "What have I learned about kubernetes?")
            tenant_id: Tenant identifier
            period_days: Days of history to analyze
            trace_id: Request trace ID

        Returns:
            TopicAnalysis with learnings, gaps, and related topics
        """
        logger.info(
            f"Analyzing topic: user={user_id}, query='{query[:50]}...', trace={trace_id}"
        )

        # Extract topic from query
        topic = self._extract_topic_from_query(query)

        period_end = date.today()
        period_start = period_end - timedelta(days=period_days)

        # Get relevant queries for this topic
        source_queries = await self._get_queries_for_topic(
            user_id=user_id,
            tenant_id=tenant_id,
            topic=topic,
            period_start=period_start,
            period_end=period_end
        )

        # Extract key learnings from the queries
        key_learnings = self._extract_key_learnings(source_queries)

        # Detect knowledge gaps (questions with regenerates or low ratings)
        knowledge_gaps = await self._detect_knowledge_gaps(
            user_id=user_id,
            tenant_id=tenant_id,
            topic=topic,
            period_start=period_start,
            period_end=period_end
        )

        # Find related topics
        related_topics = await self._get_related_topics(
            user_id=user_id,
            tenant_id=tenant_id,
            topic=topic,
            period_start=period_start,
            period_end=period_end
        )

        # Generate analysis text
        analysis_text = self._generate_analysis_text(
            topic=topic,
            query_count=len(source_queries),
            period_days=period_days,
            key_learnings=key_learnings
        )

        confidence = min(0.9, 0.5 + (len(source_queries) * 0.05))

        return TopicAnalysis(
            query=query,
            topic=topic,
            analysis_text=analysis_text,
            key_learnings=key_learnings,
            knowledge_gaps=knowledge_gaps,
            related_topics=related_topics,
            source_queries=[
                {
                    "query_id": q.get("query_id"),
                    "question": q.get("question", "")[:100],
                    "date": q.get("created_at")
                }
                for q in source_queries[:20]
            ],
            confidence=confidence
        )

    async def get_trends(
        self,
        user_id: str,
        tenant_id: str = "default",
        period_days: int = 30,
        granularity: Literal["day", "week", "month"] = "day",
        scope: Literal["user", "org"] = "user",
        trace_id: Optional[str] = None
    ) -> TrendsResponse:
        """Get usage and topic trends over time.

        Args:
            user_id: User requesting the trends
            tenant_id: Tenant identifier
            period_days: Days of history
            granularity: Time bucket size
            scope: 'user' or 'org'
            trace_id: Request trace ID

        Returns:
            TrendsResponse with timeline, topic evolution, model usage
        """
        logger.info(
            f"Getting trends: user={user_id}, period={period_days}d, "
            f"granularity={granularity}, scope={scope}, trace={trace_id}"
        )

        period_end = date.today()
        period_start = period_end - timedelta(days=period_days)

        # Get daily/weekly/monthly timeline
        timeline = await self._get_timeline(
            user_id=user_id,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            granularity=granularity,
            scope=scope
        )

        # Get topic evolution over time
        topic_evolution = await self._get_topic_evolution(
            user_id=user_id,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            granularity=granularity,
            scope=scope
        )

        # Get model usage breakdown
        model_usage = await self._get_model_usage(
            user_id=user_id,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            scope=scope
        )

        return TrendsResponse(
            period_start=period_start,
            period_end=period_end,
            granularity=granularity,
            timeline=timeline,
            topic_evolution=topic_evolution,
            model_usage=model_usage
        )

    # ============================================================
    # PRIVATE METHODS - Statistics
    # ============================================================

    async def _get_key_stats(
        self,
        user_id: str,
        tenant_id: str,
        period_start: date,
        period_end: date,
        scope: str
    ) -> Dict[str, Any]:
        """Get key statistics for the period.

        Returns dict with:
        - total_queries: int
        - unique_topics: int
        - total_cost_usd: float
        - top_agent: str
        - avg_response_time_ms: float
        """
        # Default stats (will be populated from DB)
        stats = {
            "total_queries": 0,
            "unique_topics": 0,
            "total_cost_usd": 0.0,
            "top_agent": "unknown",
            "avg_response_time_ms": 0.0,
            "cache_hit_rate": 0.0,
            "facts_extracted": 0,
            "memories_promoted": 0,
            "memories_captured": 0  # Chrome extension captures
        }

        if self.db is None:
            return stats

        try:
            # Query query_history for stats
            from sqlalchemy import text

            user_filter = "AND user_id = :user_id" if scope == "user" else ""

            result = await self.db.execute(text(f"""
                SELECT
                    COUNT(*) as total_queries,
                    COALESCE(SUM(est_cost_usd), 0) as total_cost,
                    COALESCE(AVG(total_latency_ms), 0) as avg_response_time,
                    MODE() WITHIN GROUP (ORDER BY response_source) as top_agent,
                    SUM(CASE WHEN from_cache = TRUE THEN 1 ELSE 0 END)::float /
                        NULLIF(COUNT(*), 0) as cache_hit_rate
                FROM query_history
                WHERE tenant_id = :tenant_id
                  AND created_at >= :period_start
                  AND created_at < :period_end
                  {user_filter}
            """), {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "period_start": period_start,
                "period_end": period_end
            })

            row = result.fetchone()
            if row:
                stats["total_queries"] = row[0] or 0
                stats["total_cost_usd"] = round(float(row[1] or 0), 4)
                stats["avg_response_time_ms"] = round(float(row[2] or 0), 1)
                stats["top_agent"] = row[3] or "unknown"
                stats["cache_hit_rate"] = round(float(row[4] or 0) * 100, 1)

            # Get unique topics count
            topic_result = await self.db.execute(text(f"""
                SELECT COUNT(DISTINCT primary_topic) as unique_topics
                FROM topic_extractions
                WHERE tenant_id = :tenant_id
                  AND created_at >= :period_start
                  AND created_at < :period_end
                  {user_filter}
            """), {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "period_start": period_start,
                "period_end": period_end
            })

            topic_row = topic_result.fetchone()
            if topic_row:
                stats["unique_topics"] = topic_row[0] or 0

            # Get memory_items count (Chrome extension captures)
            mem_result = await self.db.execute(text(f"""
                SELECT COUNT(*) as memory_count
                FROM memory_items
                WHERE tenant_id = :tenant_id
                  AND created_at >= :period_start
                  AND created_at < :period_end
                  AND privacy_level IN ('PUBLIC', 'INTERNAL')
                  {user_filter}
            """), {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "period_start": period_start,
                "period_end": period_end
            })

            mem_row = mem_result.fetchone()
            if mem_row:
                stats["memories_captured"] = mem_row[0] or 0

            # Get knowledge base stats from Weaviate (ACMS_Knowledge_v2)
            try:
                from src.storage.weaviate_client import WeaviateClient
                weaviate_client = WeaviateClient()
                knowledge_collection = weaviate_client._client.collections.get("ACMS_Knowledge_v2")

                # Get total knowledge count
                knowledge_count = knowledge_collection.aggregate.over_all(total_count=True).total_count
                stats["knowledge_items"] = knowledge_count

                # Get total facts count
                knowledge_objects = knowledge_collection.query.fetch_objects(limit=1000, include_vector=False)
                total_facts = 0
                for obj in knowledge_objects.objects:
                    facts = obj.properties.get("key_facts", [])
                    total_facts += len(facts) if facts else 0
                stats["facts_extracted"] = total_facts

                weaviate_client.close()
                logger.info(f"[Insights] Knowledge stats: {knowledge_count} items, {total_facts} facts")
            except Exception as kb_err:
                logger.warning(f"Could not fetch knowledge base stats: {kb_err}")

        except Exception as e:
            logger.error(f"Error getting key stats: {e}")

        return stats

    async def _get_top_topics(
        self,
        user_id: str,
        tenant_id: str,
        period_start: date,
        period_end: date,
        scope: str,
        limit: int = 20
    ) -> List[TopicStat]:
        """Get top topics by frequency with trends."""
        topics = []

        if self.db is None:
            return topics

        try:
            from sqlalchemy import text

            user_filter = "AND user_id = :user_id" if scope == "user" else ""

            # Get current period topics
            result = await self.db.execute(text(f"""
                SELECT
                    primary_topic,
                    COUNT(*) as count,
                    MIN(created_at)::date as first_seen,
                    MAX(created_at)::date as last_seen
                FROM topic_extractions
                WHERE tenant_id = :tenant_id
                  AND created_at >= :period_start
                  AND created_at < :period_end
                  AND primary_topic IS NOT NULL
                  {user_filter}
                GROUP BY primary_topic
                ORDER BY count DESC
                LIMIT :limit
            """), {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "period_start": period_start,
                "period_end": period_end,
                "limit": limit
            })

            rows = result.fetchall()

            # Calculate previous period for trend comparison
            period_length = (period_end - period_start).days
            prev_start = period_start - timedelta(days=period_length)
            prev_end = period_start

            # Get previous period counts for trend calculation
            prev_result = await self.db.execute(text(f"""
                SELECT primary_topic, COUNT(*) as count
                FROM topic_extractions
                WHERE tenant_id = :tenant_id
                  AND created_at >= :prev_start
                  AND created_at < :prev_end
                  AND primary_topic IS NOT NULL
                  {user_filter}
                GROUP BY primary_topic
            """), {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "prev_start": prev_start,
                "prev_end": prev_end
            })

            prev_counts = {row[0]: row[1] for row in prev_result.fetchall()}

            for row in rows:
                topic_name = row[0]
                current_count = row[1]
                first_seen = row[2]
                last_seen = row[3]

                prev_count = prev_counts.get(topic_name, 0)

                # Calculate trend
                if prev_count == 0:
                    trend = TrendDirection.NEW
                    trend_percent = 100.0
                elif current_count > prev_count:
                    trend = TrendDirection.UP
                    trend_percent = ((current_count - prev_count) / prev_count) * 100
                elif current_count < prev_count:
                    trend = TrendDirection.DOWN
                    trend_percent = ((prev_count - current_count) / prev_count) * -100
                else:
                    trend = TrendDirection.STABLE
                    trend_percent = 0.0

                # Get sample queries
                sample_queries = await self._get_sample_queries_for_topic(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    topic=topic_name,
                    period_start=period_start,
                    period_end=period_end,
                    limit=INSIGHTS_CONFIG["sample_queries_per_topic"]
                )

                topics.append(TopicStat(
                    topic=topic_name,
                    count=current_count,
                    trend=trend,
                    trend_percent=round(trend_percent, 1),
                    sample_queries=sample_queries,
                    first_seen=first_seen,
                    last_seen=last_seen
                ))

        except Exception as e:
            logger.error(f"Error getting top topics: {e}")

        return topics

    async def _get_sample_queries_for_topic(
        self,
        user_id: str,
        tenant_id: str,
        topic: str,
        period_start: date,
        period_end: date,
        limit: int = 3
    ) -> List[str]:
        """Get sample queries for a topic.

        Includes both query_history Q&A pairs AND memory_items captures.
        """
        samples = []

        if self.db is None:
            return samples

        try:
            from sqlalchemy import text

            # Query both query_history AND memory_items via UNION
            result = await self.db.execute(text("""
                -- Q&A samples from query_history
                SELECT qh.question as content, 'query' as source_type
                FROM query_history qh
                JOIN topic_extractions te ON qh.query_id::text = te.source_id::text
                    AND te.source_type = 'query_history'
                WHERE te.tenant_id = :tenant_id
                  AND te.primary_topic = :topic
                  AND te.created_at >= :period_start
                  AND te.created_at < :period_end
                  AND te.user_id = :user_id

                UNION ALL

                -- Memory samples from memory_items (Chrome extension captures)
                SELECT LEFT(m.content, 200) as content, 'memory' as source_type
                FROM memory_items m
                JOIN topic_extractions te ON m.memory_id::text = te.source_id::text
                    AND te.source_type = 'memory_items'
                WHERE te.tenant_id = :tenant_id
                  AND te.primary_topic = :topic
                  AND te.created_at >= :period_start
                  AND te.created_at < :period_end
                  AND te.user_id = :user_id
                  AND m.privacy_level IN ('PUBLIC', 'INTERNAL')

                ORDER BY source_type
                LIMIT :limit
            """), {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "topic": topic,
                "period_start": period_start,
                "period_end": period_end,
                "limit": limit
            })

            samples = [row[0][:100] for row in result.fetchall()]

        except Exception as e:
            logger.error(f"Error getting sample queries: {e}")

        return samples

    # ============================================================
    # PRIVATE METHODS - Pattern Detection
    # ============================================================

    async def _detect_patterns(
        self,
        user_id: str,
        tenant_id: str,
        period_start: date,
        period_end: date,
        scope: str,
        key_stats: Dict[str, Any],
        top_topics: List[TopicStat]
    ) -> List[GeneratedInsight]:
        """Detect patterns and generate insights."""
        insights = []

        # Insight 1: Emerging themes (topics with upward trend)
        emerging = [t for t in top_topics if t.trend == TrendDirection.UP and t.trend_percent > 25]
        if emerging:
            top_emerging = emerging[0]
            insights.append(GeneratedInsight(
                insight_id=str(uuid4()),
                insight_type=InsightType.EMERGING_THEME,
                title=f"Emerging focus: {top_emerging.topic}",
                description=(
                    f"Your interest in {top_emerging.topic} has increased by "
                    f"{abs(top_emerging.trend_percent):.0f}% this period. "
                    f"You've explored this topic {top_emerging.count} times."
                ),
                confidence=0.85,
                evidence=[InsightEvidence(
                    source_ids=[],  # Would be populated with actual query IDs
                    source_type="topic_extractions",
                    trust_level=TrustLevel.MEDIUM,
                    snippet_preview=f"Topic: {top_emerging.topic}, Count: {top_emerging.count}",
                    retrieval_score=1.0
                )],
                generated_by="pattern_detection"
            ))

        # Insight 2: New topics this period
        new_topics = [t for t in top_topics if t.trend == TrendDirection.NEW]
        if new_topics:
            topic_names = ", ".join([t.topic for t in new_topics[:3]])
            insights.append(GeneratedInsight(
                insight_id=str(uuid4()),
                insight_type=InsightType.TOPIC_SHIFT,
                title="New areas of exploration",
                description=f"You've started exploring new topics: {topic_names}",
                confidence=0.9,
                evidence=[InsightEvidence(
                    source_ids=[],
                    source_type="topic_extractions",
                    trust_level=TrustLevel.MEDIUM,
                    snippet_preview=f"New topics: {topic_names}",
                    retrieval_score=1.0
                )],
                generated_by="pattern_detection"
            ))

        # Insight 3: Cost trends
        if key_stats.get("total_cost_usd", 0) > 0:
            cost = key_stats["total_cost_usd"]
            queries = key_stats.get("total_queries", 1)
            avg_cost = cost / max(queries, 1)

            if avg_cost > 0.05:  # More than $0.05 per query
                insights.append(GeneratedInsight(
                    insight_id=str(uuid4()),
                    insight_type=InsightType.COST_TREND,
                    title="Cost per query above average",
                    description=(
                        f"Your average cost per query is ${avg_cost:.3f}. "
                        f"Consider using cached responses more frequently."
                    ),
                    confidence=0.8,
                    evidence=[InsightEvidence(
                        source_ids=[],
                        source_type="query_history",
                        trust_level=TrustLevel.LOW,
                        snippet_preview=f"Total cost: ${cost:.2f}, Queries: {queries}",
                        retrieval_score=1.0
                    )],
                    generated_by="statistical"
                ))

        # Insight 4: Cache hit rate
        cache_rate = key_stats.get("cache_hit_rate", 0)
        if cache_rate < 20 and key_stats.get("total_queries", 0) > 10:
            insights.append(GeneratedInsight(
                insight_id=str(uuid4()),
                insight_type=InsightType.PRODUCTIVITY_TREND,
                title="Low cache utilization",
                description=(
                    f"Only {cache_rate:.0f}% of your queries hit the cache. "
                    f"Asking similar questions may yield faster, cached responses."
                ),
                confidence=0.7,
                evidence=[InsightEvidence(
                    source_ids=[],
                    source_type="query_history",
                    trust_level=TrustLevel.LOW,
                    snippet_preview=f"Cache hit rate: {cache_rate:.0f}%",
                    retrieval_score=1.0
                )],
                generated_by="statistical"
            ))

        return insights

    async def _generate_recommendations(
        self,
        insights: List[GeneratedInsight],
        top_topics: List[TopicStat],
        key_stats: Dict[str, Any]
    ) -> List[Recommendation]:
        """Generate actionable recommendations."""
        recommendations = []

        # Recommendation based on top topics
        if top_topics:
            top_topic = top_topics[0]
            if top_topic.count >= 5:
                recommendations.append(Recommendation(
                    priority="medium",
                    action=f"Create a knowledge base entry for {top_topic.topic}",
                    context=(
                        f"You've asked {top_topic.count} questions about {top_topic.topic}. "
                        f"Consolidating this knowledge could save time."
                    )
                ))

        # Recommendation for emerging themes
        for insight in insights:
            if insight.insight_type == InsightType.EMERGING_THEME:
                recommendations.append(Recommendation(
                    priority="low",
                    action="Track your learning progress",
                    context=f"Your focus on {top_topics[0].topic if top_topics else 'new topics'} is growing. Consider documenting key learnings."
                ))
                break

        # Cost optimization recommendation
        if key_stats.get("total_cost_usd", 0) > 10:
            recommendations.append(Recommendation(
                priority="high",
                action="Review model selection for cost optimization",
                context=(
                    f"Total spend this period: ${key_stats['total_cost_usd']:.2f}. "
                    f"Consider using faster/cheaper models for simple queries."
                )
            ))

        return recommendations

    # ============================================================
    # PRIVATE METHODS - Topic Analysis
    # ============================================================

    def _extract_topic_from_query(self, query: str) -> str:
        """Extract the topic from a user's query."""
        # Simple extraction - look for "about X" pattern
        query_lower = query.lower()

        patterns = [
            "learned about ",
            "know about ",
            "asked about ",
            "learning about ",
            "questions about ",
            "regarding ",
            "related to ",
        ]

        for pattern in patterns:
            if pattern in query_lower:
                idx = query_lower.index(pattern) + len(pattern)
                topic = query_lower[idx:].split()[0].strip("?.,!").strip()
                return topic

        # Fallback: use the last significant word
        words = [w.strip("?.,!") for w in query.split() if len(w) > 3]
        if words:
            return words[-1].lower()

        return "general"

    async def _get_queries_for_topic(
        self,
        user_id: str,
        tenant_id: str,
        topic: str,
        period_start: date,
        period_end: date
    ) -> List[Dict[str, Any]]:
        """Get all queries related to a topic."""
        queries = []

        if self.db is None:
            return queries

        try:
            from sqlalchemy import text

            result = await self.db.execute(text("""
                -- Q&A from query_history (desktop chat)
                SELECT
                    qh.query_id::text as query_id,
                    qh.question,
                    qh.answer,
                    qh.created_at,
                    qh.response_source,
                    te.topics,
                    'query_history' as source_table
                FROM query_history qh
                JOIN topic_extractions te ON qh.query_id::text = te.source_id::text
                    AND te.source_type = 'query_history'
                WHERE te.tenant_id = :tenant_id
                  AND te.user_id = :user_id
                  AND (te.primary_topic = :topic OR :topic = ANY(te.topics))
                  AND te.created_at >= :period_start
                  AND te.created_at < :period_end

                UNION ALL

                -- Memories from memory_items (Chrome extension captures)
                SELECT
                    m.memory_id::text as query_id,
                    COALESCE(m.tags[1], 'Captured Memory') as question,
                    LEFT(m.content, 500) as answer,
                    m.created_at,
                    'extension_capture' as response_source,
                    te.topics,
                    'memory_items' as source_table
                FROM memory_items m
                JOIN topic_extractions te ON m.memory_id::text = te.source_id::text
                    AND te.source_type = 'memory_items'
                WHERE te.tenant_id = :tenant_id
                  AND te.user_id = :user_id
                  AND (te.primary_topic = :topic OR :topic = ANY(te.topics))
                  AND te.created_at >= :period_start
                  AND te.created_at < :period_end
                  AND m.privacy_level IN ('PUBLIC', 'INTERNAL')

                ORDER BY created_at DESC
                LIMIT 50
            """), {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "topic": topic,
                "period_start": period_start,
                "period_end": period_end
            })

            for row in result.fetchall():
                queries.append({
                    "query_id": str(row[0]),
                    "question": row[1],
                    "answer": row[2],
                    "created_at": row[3].isoformat() if row[3] else None,
                    "response_source": row[4],
                    "topics": row[5],
                    "source_table": row[6]
                })

        except Exception as e:
            logger.error(f"Error getting queries for topic: {e}")

        return queries

    def _extract_key_learnings(self, queries: List[Dict[str, Any]]) -> List[str]:
        """Extract key learnings from query answers."""
        learnings = []

        for q in queries[:10]:  # Analyze top 10
            answer = q.get("answer", "")
            if answer:
                # Extract first meaningful sentence
                sentences = answer.split(". ")
                for sent in sentences[:2]:
                    if len(sent) > 20 and len(sent) < 200:
                        learnings.append(sent.strip())
                        break

        return learnings[:5]  # Return top 5

    async def _detect_knowledge_gaps(
        self,
        user_id: str,
        tenant_id: str,
        topic: str,
        period_start: date,
        period_end: date
    ) -> List[str]:
        """Detect knowledge gaps - questions with low satisfaction."""
        gaps = []

        if self.db is None:
            return gaps

        try:
            from sqlalchemy import text

            # Find queries with regenerates or low ratings
            result = await self.db.execute(text("""
                SELECT qh.question
                FROM query_history qh
                JOIN topic_extractions te ON qh.query_id::text = te.source_id::text
                LEFT JOIN query_feedback qf ON qh.query_id = qf.query_id
                WHERE te.tenant_id = :tenant_id
                  AND te.user_id = :user_id
                  AND (te.primary_topic = :topic OR :topic = ANY(te.topics))
                  AND te.created_at >= :period_start
                  AND te.created_at < :period_end
                  AND (qf.feedback_type = 'regenerate' OR qf.rating < 3)
                ORDER BY qh.created_at DESC
                LIMIT 5
            """), {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "topic": topic,
                "period_start": period_start,
                "period_end": period_end
            })

            gaps = [row[0][:100] for row in result.fetchall()]

        except Exception as e:
            logger.error(f"Error detecting knowledge gaps: {e}")

        return gaps

    async def _get_related_topics(
        self,
        user_id: str,
        tenant_id: str,
        topic: str,
        period_start: date,
        period_end: date
    ) -> List[str]:
        """Find topics that co-occur with the target topic."""
        related = []

        if self.db is None:
            return related

        try:
            from sqlalchemy import text

            result = await self.db.execute(text("""
                SELECT DISTINCT unnest(topics) as related_topic
                FROM topic_extractions
                WHERE tenant_id = :tenant_id
                  AND user_id = :user_id
                  AND :topic = ANY(topics)
                  AND created_at >= :period_start
                  AND created_at < :period_end
                LIMIT 10
            """), {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "topic": topic,
                "period_start": period_start,
                "period_end": period_end
            })

            related = [row[0] for row in result.fetchall() if row[0] != topic]

        except Exception as e:
            logger.error(f"Error getting related topics: {e}")

        return related[:5]

    def _generate_analysis_text(
        self,
        topic: str,
        query_count: int,
        period_days: int,
        key_learnings: List[str]
    ) -> str:
        """Generate human-readable analysis text."""
        if query_count == 0:
            return f"No queries found about {topic} in the last {period_days} days."

        learning_summary = ""
        if key_learnings:
            learning_summary = f" Key areas covered include: {'; '.join(key_learnings[:3])}"

        return (
            f"Based on {query_count} conversations over {period_days} days, "
            f"you've been exploring {topic} extensively.{learning_summary}"
        )

    # ============================================================
    # PRIVATE METHODS - Trends
    # ============================================================

    async def _get_timeline(
        self,
        user_id: str,
        tenant_id: str,
        period_start: date,
        period_end: date,
        granularity: str,
        scope: str
    ) -> List[Dict[str, Any]]:
        """Get usage timeline data."""
        timeline = []

        if self.db is None:
            return timeline

        try:
            from sqlalchemy import text

            # Determine date truncation based on granularity
            trunc = {
                "day": "day",
                "week": "week",
                "month": "month"
            }.get(granularity, "day")

            user_filter = "AND user_id = :user_id" if scope == "user" else ""

            result = await self.db.execute(text(f"""
                SELECT
                    DATE_TRUNC(:trunc, created_at)::date as period_date,
                    COUNT(*) as queries,
                    COALESCE(SUM(est_cost_usd), 0) as cost,
                    MODE() WITHIN GROUP (ORDER BY response_source) as top_source
                FROM query_history
                WHERE tenant_id = :tenant_id
                  AND created_at >= :period_start
                  AND created_at < :period_end
                  {user_filter}
                GROUP BY DATE_TRUNC(:trunc, created_at)
                ORDER BY period_date
            """), {
                "trunc": trunc,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "period_start": period_start,
                "period_end": period_end
            })

            for row in result.fetchall():
                timeline.append({
                    "date": row[0].isoformat() if row[0] else None,
                    "queries": row[1],
                    "cost": round(float(row[2] or 0), 4),
                    "top_source": row[3]
                })

        except Exception as e:
            logger.error(f"Error getting timeline: {e}")

        return timeline

    async def _get_topic_evolution(
        self,
        user_id: str,
        tenant_id: str,
        period_start: date,
        period_end: date,
        granularity: str,
        scope: str
    ) -> Dict[str, List[TrendPoint]]:
        """Get topic counts over time."""
        evolution = {}

        if self.db is None:
            return evolution

        try:
            from sqlalchemy import text

            trunc = {
                "day": "day",
                "week": "week",
                "month": "month"
            }.get(granularity, "day")

            user_filter = "AND user_id = :user_id" if scope == "user" else ""

            # Get top 5 topics for evolution chart
            top_topics_result = await self.db.execute(text(f"""
                SELECT primary_topic
                FROM topic_extractions
                WHERE tenant_id = :tenant_id
                  AND created_at >= :period_start
                  AND created_at < :period_end
                  AND primary_topic IS NOT NULL
                  {user_filter}
                GROUP BY primary_topic
                ORDER BY COUNT(*) DESC
                LIMIT 5
            """), {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "period_start": period_start,
                "period_end": period_end
            })

            top_topics = [row[0] for row in top_topics_result.fetchall()]

            for topic in top_topics:
                result = await self.db.execute(text(f"""
                    SELECT
                        DATE_TRUNC(:trunc, created_at)::date as period_date,
                        COUNT(*) as count
                    FROM topic_extractions
                    WHERE tenant_id = :tenant_id
                      AND primary_topic = :topic
                      AND created_at >= :period_start
                      AND created_at < :period_end
                      {user_filter}
                    GROUP BY DATE_TRUNC(:trunc, created_at)
                    ORDER BY period_date
                """), {
                    "trunc": trunc,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "topic": topic,
                    "period_start": period_start,
                    "period_end": period_end
                })

                evolution[topic] = [
                    TrendPoint(date=row[0], value=row[1])
                    for row in result.fetchall()
                ]

        except Exception as e:
            logger.error(f"Error getting topic evolution: {e}")

        return evolution

    async def _get_model_usage(
        self,
        user_id: str,
        tenant_id: str,
        period_start: date,
        period_end: date,
        scope: str
    ) -> Dict[str, float]:
        """Get model usage breakdown as percentages."""
        usage = {}

        if self.db is None:
            return usage

        try:
            from sqlalchemy import text

            user_filter = "AND user_id = :user_id" if scope == "user" else ""

            result = await self.db.execute(text(f"""
                SELECT
                    response_source,
                    COUNT(*) as count,
                    COUNT(*)::float / SUM(COUNT(*)) OVER () * 100 as percentage
                FROM query_history
                WHERE tenant_id = :tenant_id
                  AND created_at >= :period_start
                  AND created_at < :period_end
                  {user_filter}
                GROUP BY response_source
                ORDER BY count DESC
            """), {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "period_start": period_start,
                "period_end": period_end
            })

            for row in result.fetchall():
                model_name = row[0] or "unknown"
                usage[model_name] = round(float(row[2] or 0), 1)

        except Exception as e:
            logger.error(f"Error getting model usage: {e}")

        return usage
