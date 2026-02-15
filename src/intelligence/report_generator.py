"""Report Generator for ACMS Intelligence Hub.

Generates executive reports from insights and query history.

Key Features:
- Weekly/monthly personal reports
- Org-wide reports (admin only)
- Multiple export formats (JSON, Markdown, HTML)
- Cost tracking for generation

Usage:
    from src.intelligence.report_generator import ReportGenerator

    generator = ReportGenerator(db_session, insights_engine)

    # Generate weekly report
    report = await generator.generate_report(
        user_id="user-123",
        report_type="weekly",
        scope="user"
    )

    # Export to markdown
    markdown = generator.format_as_markdown(report)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from uuid import uuid4
import json

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

REPORT_CONFIG = {
    "max_llm_cost_per_report": 0.50,      # $0.50 cap for report generation
    "default_top_topics": 20,
    "max_insights_per_report": 10,
    "max_recommendations_per_report": 5,
    "cache_ttl_seconds": 3600,            # 1 hour
}


# ============================================================
# DATA CLASSES
# ============================================================

class ReportType(str, Enum):
    """Types of reports."""
    WEEKLY_PERSONAL = "weekly_personal"
    WEEKLY_ORG = "weekly_org"
    MONTHLY_PERSONAL = "monthly_personal"
    MONTHLY_ORG = "monthly_org"
    ON_DEMAND = "on_demand"


class ReportStatus(str, Enum):
    """Report generation status."""
    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentStats:
    """Statistics for a single agent/model."""
    agent_name: str
    queries: int
    cost_usd: float
    avg_latency_ms: float
    percentage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent": self.agent_name,
            "queries": self.queries,
            "cost": round(self.cost_usd, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 1),
            "percentage": round(self.percentage, 1)
        }


@dataclass
class KnowledgeGrowth:
    """Knowledge growth metrics."""
    new_qa_pairs: int
    facts_extracted: int
    memories_promoted: int
    memories_captured: int  # Chrome extension captures
    topics_mastered: List[str]
    topics_in_progress: List[str]
    extension_sources: Dict[str, int] = None  # Breakdown by source

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "new_qa_pairs": self.new_qa_pairs,
            "facts_extracted": self.facts_extracted,
            "memories_promoted": self.memories_promoted,
            "memories_captured": self.memories_captured,
            "topics_mastered": self.topics_mastered,
            "topics_in_progress": self.topics_in_progress,
            "extension_sources": self.extension_sources or {}
        }


@dataclass
class ReportSummary:
    """Executive summary section of report."""
    headline: str
    key_stats: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "headline": self.headline,
            "key_stats": self.key_stats
        }


@dataclass
class TopicEntry:
    """Topic entry in report."""
    rank: int
    topic: str
    count: int
    trend: str
    trend_percent: float
    sample_queries: List[str]
    first_seen: Optional[str] = None
    last_seen: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rank": self.rank,
            "topic": self.topic,
            "count": self.count,
            "trend": self.trend,
            "trend_percent": round(self.trend_percent, 1),
            "sample_queries": self.sample_queries,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen
        }


@dataclass
class ReportInsight:
    """Insight entry in report."""
    insight_type: str
    title: str
    description: str
    confidence: float
    evidence: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.insight_type,
            "title": self.title,
            "description": self.description,
            "confidence": round(self.confidence, 2),
            "evidence": self.evidence
        }


@dataclass
class ReportRecommendation:
    """Recommendation entry in report."""
    priority: str
    action: str
    context: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "priority": self.priority,
            "action": self.action,
            "context": self.context
        }


@dataclass
class IntelligenceReport:
    """Complete intelligence report."""
    report_id: str
    report_type: ReportType
    scope: str
    tenant_id: str
    user_id: Optional[str]

    period_start: date
    period_end: date
    generated_at: datetime

    summary: ReportSummary
    top_topics: List[TopicEntry]
    insights: List[ReportInsight]
    recommendations: List[ReportRecommendation]
    knowledge_growth: KnowledgeGrowth
    agent_breakdown: List[AgentStats]

    # Generation metadata
    generated_by: str
    generation_time_ms: int
    tokens_used: int
    cost_usd: float
    trace_id: Optional[str] = None
    status: ReportStatus = ReportStatus.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.report_id,
            "type": self.report_type.value,
            "scope": self.scope,
            "period": {
                "start": self.period_start.isoformat(),
                "end": self.period_end.isoformat()
            },
            "generated_at": self.generated_at.isoformat(),

            "summary": self.summary.to_dict(),
            "top_topics": [t.to_dict() for t in self.top_topics],
            "insights": [i.to_dict() for i in self.insights],
            "recommendations": [r.to_dict() for r in self.recommendations],
            "knowledge_growth": self.knowledge_growth.to_dict(),
            "agent_breakdown": {a.agent_name: a.to_dict() for a in self.agent_breakdown},

            "meta": {
                "generated_by": self.generated_by,
                "generation_time_ms": self.generation_time_ms,
                "tokens_used": self.tokens_used,
                "cost_usd": round(self.cost_usd, 4),
                "trace_id": self.trace_id,
                "status": self.status.value
            }
        }


# ============================================================
# REPORT GENERATOR CLASS
# ============================================================

class ReportGenerator:
    """Generates intelligence reports from user data.

    All methods are RBAC-aware and require user context.
    """

    def __init__(
        self,
        db_session=None,
        insights_engine=None,
        llm_provider=None
    ):
        """Initialize report generator.

        Args:
            db_session: Database session for queries
            insights_engine: InsightsEngine for generating insights
            llm_provider: Optional LLM for synthesis
        """
        self.db = db_session
        self.insights = insights_engine
        self.llm = llm_provider
        logger.info("ReportGenerator initialized")

    async def generate_report(
        self,
        user_id: str,
        report_type: Literal["weekly", "monthly", "custom"] = "weekly",
        scope: Literal["user", "org"] = "user",
        tenant_id: str = "default",
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        include_recommendations: bool = True,
        trace_id: Optional[str] = None
    ) -> IntelligenceReport:
        """Generate an intelligence report.

        Args:
            user_id: User requesting the report
            report_type: Type of report (weekly, monthly, custom)
            scope: 'user' for personal, 'org' for org-wide
            tenant_id: Tenant identifier
            period_start: Custom start date (for custom reports)
            period_end: Custom end date (for custom reports)
            include_recommendations: Include AI recommendations
            trace_id: Request trace ID

        Returns:
            IntelligenceReport with full data
        """
        import time
        start_time = time.time()

        report_id = str(uuid4())
        logger.info(
            f"Generating report: id={report_id}, type={report_type}, "
            f"scope={scope}, user={user_id}, trace={trace_id}"
        )

        # Determine period
        if period_end is None:
            period_end = date.today()

        if period_start is None:
            if report_type == "weekly":
                period_start = period_end - timedelta(days=7)
            elif report_type == "monthly":
                period_start = period_end - timedelta(days=30)
            else:
                period_start = period_end - timedelta(days=7)  # Default to week

        period_days = (period_end - period_start).days

        # Determine report type enum
        if scope == "org":
            rtype = ReportType.WEEKLY_ORG if report_type == "weekly" else ReportType.MONTHLY_ORG
        else:
            rtype = ReportType.WEEKLY_PERSONAL if report_type == "weekly" else ReportType.MONTHLY_PERSONAL

        # Generate insights summary (reuse InsightsEngine if available)
        summary_data = await self._get_summary_data(
            user_id=user_id,
            tenant_id=tenant_id,
            period_start=period_start,
            period_end=period_end,
            scope=scope
        )

        # Build report sections
        summary = self._build_summary(summary_data, period_days)
        top_topics = self._build_top_topics(summary_data.get("top_topics", []))
        insights = self._build_insights(summary_data.get("insights", []))
        knowledge_growth = self._build_knowledge_growth(summary_data)
        agent_breakdown = self._build_agent_breakdown(summary_data.get("agent_stats", {}))

        # Generate recommendations if requested
        if include_recommendations:
            recommendations = self._build_recommendations(
                summary_data.get("recommendations", [])
            )
        else:
            recommendations = []

        generation_time_ms = int((time.time() - start_time) * 1000)

        report = IntelligenceReport(
            report_id=report_id,
            report_type=rtype,
            scope=scope,
            tenant_id=tenant_id,
            user_id=user_id if scope == "user" else None,

            period_start=period_start,
            period_end=period_end,
            generated_at=datetime.utcnow(),

            summary=summary,
            top_topics=top_topics,
            insights=insights,
            recommendations=recommendations,
            knowledge_growth=knowledge_growth,
            agent_breakdown=agent_breakdown,

            generated_by="report_generator_v1",
            generation_time_ms=generation_time_ms,
            tokens_used=0,  # No LLM used yet
            cost_usd=0.0,
            trace_id=trace_id,
            status=ReportStatus.COMPLETED
        )

        # Save report to database
        await self._save_report(report)

        logger.info(
            f"Report generated: id={report_id}, topics={len(top_topics)}, "
            f"insights={len(insights)}, time={generation_time_ms}ms"
        )

        return report

    async def list_reports(
        self,
        user_id: str,
        tenant_id: str = "default",
        report_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """List previous reports for user.

        Args:
            user_id: User to list reports for
            tenant_id: Tenant identifier
            report_type: Filter by type (optional)
            limit: Max reports to return

        Returns:
            List of report summaries
        """
        reports = []

        if self.db is None:
            return reports

        try:
            from sqlalchemy import text

            type_filter = "AND report_type = :report_type" if report_type else ""

            result = await self.db.execute(text(f"""
                SELECT
                    id,
                    report_type,
                    scope,
                    period_start,
                    period_end,
                    title,
                    summary,
                    created_at
                FROM intelligence_reports
                WHERE tenant_id = :tenant_id
                  AND (user_id = :user_id OR user_id IS NULL)
                  {type_filter}
                ORDER BY created_at DESC
                LIMIT :limit
            """), {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "report_type": report_type,
                "limit": limit
            })

            for row in result.fetchall():
                reports.append({
                    "report_id": str(row[0]),
                    "report_type": row[1],
                    "scope": row[2],
                    "period_start": row[3].isoformat() if row[3] else None,
                    "period_end": row[4].isoformat() if row[4] else None,
                    "title": row[5],
                    "summary": row[6][:200] if row[6] else None,
                    "created_at": row[7].isoformat() if row[7] else None
                })

        except Exception as e:
            logger.error(f"Error listing reports: {e}")

        return reports

    async def get_report(
        self,
        report_id: str,
        user_id: str,
        tenant_id: str = "default"
    ) -> Optional[Dict[str, Any]]:
        """Get a specific report by ID.

        Args:
            report_id: Report UUID
            user_id: User requesting the report
            tenant_id: Tenant identifier

        Returns:
            Report data or None if not found
        """
        if self.db is None:
            return None

        try:
            from sqlalchemy import text

            result = await self.db.execute(text("""
                SELECT
                    id,
                    tenant_id,
                    user_id,
                    report_type,
                    scope,
                    period_start,
                    period_end,
                    title,
                    summary,
                    top_topics,
                    insights,
                    recommendations,
                    metrics,
                    generated_by,
                    generation_time_ms,
                    tokens_used,
                    cost_usd,
                    trace_id,
                    created_at
                FROM intelligence_reports
                WHERE id = :report_id
                  AND tenant_id = :tenant_id
                  AND (user_id = :user_id OR user_id IS NULL)
            """), {
                "report_id": report_id,
                "tenant_id": tenant_id,
                "user_id": user_id
            })

            row = result.fetchone()
            if not row:
                return None

            return {
                "id": str(row[0]),
                "type": row[3],
                "scope": row[4],
                "period": {
                    "start": row[5].isoformat() if row[5] else None,
                    "end": row[6].isoformat() if row[6] else None
                },
                "title": row[7],
                "summary": row[8],
                "top_topics": row[9] or [],
                "insights": row[10] or [],
                "recommendations": row[11] or [],
                "metrics": row[12] or {},
                "meta": {
                    "generated_by": row[13],
                    "generation_time_ms": row[14],
                    "tokens_used": row[15],
                    "cost_usd": float(row[16] or 0),
                    "trace_id": row[17]
                },
                "generated_at": row[18].isoformat() if row[18] else None
            }

        except Exception as e:
            logger.error(f"Error getting report {report_id}: {e}")
            return None

    # ============================================================
    # FORMAT METHODS
    # ============================================================

    def format_as_markdown(self, report: IntelligenceReport) -> str:
        """Format report as Markdown.

        Args:
            report: IntelligenceReport to format

        Returns:
            Markdown string
        """
        lines = [
            f"# Intelligence Report",
            f"",
            f"**Period**: {report.period_start} to {report.period_end}",
            f"**Generated**: {report.generated_at.strftime('%Y-%m-%d %H:%M')} UTC",
            f"**Scope**: {report.scope.capitalize()}",
            f"",
            f"---",
            f"",
            f"## Executive Summary",
            f"",
            f"**{report.summary.headline}**",
            f"",
        ]

        # Key stats
        stats = report.summary.key_stats
        lines.extend([
            f"- **Total Queries**: {stats.get('total_queries', 0)}",
            f"- **Memories Captured**: {stats.get('memories_captured', 0)}",
            f"- **Knowledge Items**: {stats.get('knowledge_items', 0)}",
            f"- **Facts Extracted**: {stats.get('facts_extracted', 0)}",
            f"- **Unique Topics**: {stats.get('unique_topics', 0)}",
            f"- **Total Cost**: ${stats.get('total_cost_usd', 0):.2f}",
            f"- **Top Agent**: {stats.get('top_agent', 'N/A')}",
            f"",
        ])

        # Top Topics
        if report.top_topics:
            lines.extend([
                f"## Top {len(report.top_topics)} Topics",
                f"",
                f"| Rank | Topic | Count | Trend |",
                f"|------|-------|-------|-------|",
            ])
            for topic in report.top_topics[:20]:
                trend_icon = {"up": "^", "down": "v", "stable": "-", "new": "*"}.get(topic.trend, "")
                lines.append(
                    f"| {topic.rank} | {topic.topic} | {topic.count} | {trend_icon} {abs(topic.trend_percent):.0f}% |"
                )
            lines.append("")

        # Insights
        if report.insights:
            lines.extend([
                f"## Key Insights",
                f"",
            ])
            for insight in report.insights:
                emoji = {
                    "emerging_theme": "fire",
                    "knowledge_gap": "warning",
                    "cost_trend": "dollar",
                    "productivity_trend": "chart",
                }.get(insight.insight_type, "bulb")
                lines.extend([
                    f"### {insight.title}",
                    f"",
                    f"{insight.description}",
                    f"",
                    f"*Confidence: {insight.confidence:.0%}*",
                    f"",
                ])

        # Recommendations
        if report.recommendations:
            lines.extend([
                f"## Recommendations",
                f"",
            ])
            for rec in report.recommendations:
                priority_emoji = {"high": "[!]", "medium": "[*]", "low": "[-]"}.get(rec.priority, "")
                lines.extend([
                    f"- {priority_emoji} **{rec.action}**",
                    f"  {rec.context}",
                    f"",
                ])

        # Knowledge Growth
        kg = report.knowledge_growth
        lines.extend([
            f"## Knowledge Growth",
            f"",
            f"- New Q&A pairs: {kg.new_qa_pairs}",
            f"- Memories captured: {kg.memories_captured}",
            f"- Facts extracted: {kg.facts_extracted}",
            f"- Memories promoted: {kg.memories_promoted}",
            f"",
        ])
        # Extension breakdown if available
        if kg.extension_sources:
            ext = kg.extension_sources
            active_sources = [(k, v) for k, v in ext.items() if v > 0]
            if active_sources:
                lines.append("**Extension Sources**:")
                for source, count in sorted(active_sources, key=lambda x: -x[1]):
                    lines.append(f"  - {source.title()}: {count}")
                lines.append("")
        if kg.topics_mastered:
            lines.append(f"**Topics Mastered**: {', '.join(kg.topics_mastered)}")
        if kg.topics_in_progress:
            lines.append(f"**In Progress**: {', '.join(kg.topics_in_progress)}")
        lines.append("")

        # Agent Breakdown
        if report.agent_breakdown:
            lines.extend([
                f"## Agent Usage",
                f"",
                f"| Agent | Queries | Cost | Avg Latency |",
                f"|-------|---------|------|-------------|",
            ])
            for agent in report.agent_breakdown:
                lines.append(
                    f"| {agent.agent_name} | {agent.queries} ({agent.percentage:.0f}%) | ${agent.cost_usd:.2f} | {agent.avg_latency_ms:.0f}ms |"
                )
            lines.append("")

        # Footer
        lines.extend([
            f"---",
            f"",
            f"*Generated by ACMS Intelligence Hub*",
            f"*Report ID: {report.report_id}*",
        ])

        return "\n".join(lines)

    def format_as_html(self, report: IntelligenceReport) -> str:
        """Format report as HTML.

        Args:
            report: IntelligenceReport to format

        Returns:
            HTML string
        """
        # Convert markdown to basic HTML
        md = self.format_as_markdown(report)

        # Simple markdown to HTML conversion
        html_lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='utf-8'>",
            "<title>Intelligence Report</title>",
            "<style>",
            "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }",
            "table { border-collapse: collapse; width: 100%; margin: 1em 0; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f5f5f5; }",
            "h1 { color: #333; }",
            "h2 { color: #666; border-bottom: 1px solid #eee; padding-bottom: 0.5em; }",
            ".stat { background: #f9f9f9; padding: 10px; border-radius: 4px; margin: 5px 0; }",
            "</style>",
            "</head>",
            "<body>",
        ]

        # Basic conversion (simplified)
        for line in md.split("\n"):
            if line.startswith("# "):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("### "):
                html_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("- "):
                html_lines.append(f"<li>{line[2:]}</li>")
            elif line.startswith("|"):
                # Table row
                cells = [c.strip() for c in line.split("|")[1:-1]]
                if all(c.startswith("-") for c in cells):
                    continue  # Skip separator
                tag = "th" if html_lines[-1].endswith("</table>") == False and "<table>" in html_lines[-5:] else "td"
                if tag == "th" and "<table>" not in "".join(html_lines[-3:]):
                    html_lines.append("<table>")
                html_lines.append("<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>")
            elif line == "---":
                html_lines.append("<hr>")
            elif line.startswith("**") and line.endswith("**"):
                html_lines.append(f"<p><strong>{line[2:-2]}</strong></p>")
            elif line.strip():
                html_lines.append(f"<p>{line}</p>")

        html_lines.extend([
            "</body>",
            "</html>",
        ])

        return "\n".join(html_lines)

    # ============================================================
    # PRIVATE METHODS
    # ============================================================

    async def _get_summary_data(
        self,
        user_id: str,
        tenant_id: str,
        period_start: date,
        period_end: date,
        scope: str
    ) -> Dict[str, Any]:
        """Get summary data from InsightsEngine or database."""
        data = {
            "key_stats": {
                "total_queries": 0,
                "unique_topics": 0,
                "total_cost_usd": 0.0,
                "top_agent": "unknown"
            },
            "top_topics": [],
            "insights": [],
            "recommendations": [],
            "agent_stats": {}
        }

        # Use InsightsEngine if available
        if self.insights is not None:
            try:
                summary = await self.insights.generate_summary(
                    user_id=user_id,
                    tenant_id=tenant_id,
                    period_days=(period_end - period_start).days,
                    scope=scope
                )
                data["key_stats"] = summary.key_stats
                data["top_topics"] = [t.to_dict() for t in summary.top_topics]
                data["insights"] = [i.to_dict() for i in summary.insights]
                data["recommendations"] = [r.to_dict() for r in summary.recommendations]
            except Exception as e:
                logger.error(f"Error getting insights summary: {e}")

        # Get agent stats from DB
        if self.db is not None:
            try:
                from sqlalchemy import text

                user_filter = "AND user_id = :user_id" if scope == "user" else ""

                result = await self.db.execute(text(f"""
                    SELECT
                        response_source,
                        COUNT(*) as count,
                        COALESCE(SUM(est_cost_usd), 0) as cost,
                        COALESCE(AVG(response_time_ms), 0) as avg_latency
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

                total_queries = 0
                for row in result.fetchall():
                    agent = row[0] or "unknown"
                    count = row[1]
                    cost = float(row[2] or 0)
                    latency = float(row[3] or 0)
                    total_queries += count
                    data["agent_stats"][agent] = {
                        "queries": count,
                        "cost": cost,
                        "latency": latency
                    }

                # Calculate percentages
                for agent in data["agent_stats"]:
                    data["agent_stats"][agent]["percentage"] = (
                        data["agent_stats"][agent]["queries"] / max(total_queries, 1) * 100
                    )

            except Exception as e:
                logger.error(f"Error getting agent stats: {e}")

            # Get memory stats (Chrome extension captures)
            try:
                mem_result = await self.db.execute(text(f"""
                    SELECT
                        COUNT(*) as total_memories,
                        COUNT(CASE WHEN metadata_json->>'source' = 'chatgpt' THEN 1 END) as chatgpt_captures,
                        COUNT(CASE WHEN metadata_json->>'source' = 'claude' THEN 1 END) as claude_captures,
                        COUNT(CASE WHEN metadata_json->>'source' = 'gemini' THEN 1 END) as gemini_captures,
                        COUNT(CASE WHEN metadata_json->>'source' = 'perplexity' THEN 1 END) as perplexity_captures
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
                    data["key_stats"]["memories_captured"] = mem_row[0] or 0
                    data["extension_breakdown"] = {
                        "chatgpt": mem_row[1] or 0,
                        "claude": mem_row[2] or 0,
                        "gemini": mem_row[3] or 0,
                        "perplexity": mem_row[4] or 0
                    }

            except Exception as e:
                logger.error(f"Error getting memory stats: {e}")

        return data

    def _build_summary(
        self,
        data: Dict[str, Any],
        period_days: int
    ) -> ReportSummary:
        """Build executive summary section."""
        stats = data.get("key_stats", {})

        # Generate headline based on top topics and stats
        topics = data.get("top_topics", [])
        top_topic = topics[0]["topic"] if topics else "various topics"

        headline = f"Focus on {top_topic} over {period_days} days"

        return ReportSummary(
            headline=headline,
            key_stats=stats
        )

    def _build_top_topics(
        self,
        topics_data: List[Dict[str, Any]]
    ) -> List[TopicEntry]:
        """Build top topics list."""
        entries = []

        for i, t in enumerate(topics_data[:REPORT_CONFIG["default_top_topics"]]):
            entries.append(TopicEntry(
                rank=i + 1,
                topic=t.get("topic", "unknown"),
                count=t.get("count", 0),
                trend=t.get("trend", "stable"),
                trend_percent=t.get("trend_percent", 0.0),
                sample_queries=t.get("sample_queries", []),
                first_seen=t.get("first_seen"),
                last_seen=t.get("last_seen")
            ))

        return entries

    def _build_insights(
        self,
        insights_data: List[Dict[str, Any]]
    ) -> List[ReportInsight]:
        """Build insights list."""
        entries = []

        for i in insights_data[:REPORT_CONFIG["max_insights_per_report"]]:
            entries.append(ReportInsight(
                insight_type=i.get("type", "general"),
                title=i.get("title", ""),
                description=i.get("description", ""),
                confidence=i.get("confidence", 0.0),
                evidence=i.get("evidence", {})
            ))

        return entries

    def _build_recommendations(
        self,
        recommendations_data: List[Dict[str, Any]]
    ) -> List[ReportRecommendation]:
        """Build recommendations list."""
        entries = []

        for r in recommendations_data[:REPORT_CONFIG["max_recommendations_per_report"]]:
            entries.append(ReportRecommendation(
                priority=r.get("priority", "medium"),
                action=r.get("action", ""),
                context=r.get("context", "")
            ))

        return entries

    def _build_knowledge_growth(
        self,
        data: Dict[str, Any]
    ) -> KnowledgeGrowth:
        """Build knowledge growth metrics."""
        stats = data.get("key_stats", {})
        topics = data.get("top_topics", [])

        # Find mastered topics (high count, stable or down trend)
        mastered = [
            t["topic"] for t in topics
            if t.get("count", 0) >= 10 and t.get("trend") in ["stable", "down"]
        ][:3]

        # Find in-progress topics (new or up trend)
        in_progress = [
            t["topic"] for t in topics
            if t.get("trend") in ["new", "up"]
        ][:3]

        return KnowledgeGrowth(
            new_qa_pairs=stats.get("total_queries", 0),
            facts_extracted=stats.get("facts_extracted", 0),
            memories_promoted=stats.get("memories_promoted", 0),
            memories_captured=stats.get("memories_captured", 0),
            topics_mastered=mastered,
            topics_in_progress=in_progress,
            extension_sources=data.get("extension_breakdown", {})
        )

    def _build_agent_breakdown(
        self,
        agent_stats: Dict[str, Dict[str, Any]]
    ) -> List[AgentStats]:
        """Build agent breakdown list."""
        entries = []

        for agent, stats in agent_stats.items():
            entries.append(AgentStats(
                agent_name=agent,
                queries=stats.get("queries", 0),
                cost_usd=stats.get("cost", 0.0),
                avg_latency_ms=stats.get("latency", 0.0),
                percentage=stats.get("percentage", 0.0)
            ))

        # Sort by queries descending
        entries.sort(key=lambda x: x.queries, reverse=True)
        return entries

    async def _save_report(self, report: IntelligenceReport) -> None:
        """Save report to database."""
        if self.db is None:
            return

        try:
            from sqlalchemy import text

            await self.db.execute(text("""
                INSERT INTO intelligence_reports (
                    id, tenant_id, user_id, report_type, scope,
                    period_start, period_end, title, summary,
                    top_topics, insights, recommendations, metrics,
                    generated_by, generation_time_ms, tokens_used, cost_usd,
                    trace_id, created_at
                ) VALUES (
                    :id, :tenant_id, :user_id, :report_type, :scope,
                    :period_start, :period_end, :title, :summary,
                    :top_topics, :insights, :recommendations, :metrics,
                    :generated_by, :generation_time_ms, :tokens_used, :cost_usd,
                    :trace_id, :created_at
                )
            """), {
                "id": report.report_id,
                "tenant_id": report.tenant_id,
                "user_id": report.user_id,
                "report_type": report.report_type.value,
                "scope": report.scope,
                "period_start": report.period_start,
                "period_end": report.period_end,
                "title": report.summary.headline,
                "summary": report.summary.headline,
                "top_topics": json.dumps([t.to_dict() for t in report.top_topics]),
                "insights": json.dumps([i.to_dict() for i in report.insights]),
                "recommendations": json.dumps([r.to_dict() for r in report.recommendations]),
                "metrics": json.dumps(report.summary.key_stats),
                "generated_by": report.generated_by,
                "generation_time_ms": report.generation_time_ms,
                "tokens_used": report.tokens_used,
                "cost_usd": report.cost_usd,
                "trace_id": report.trace_id,
                "created_at": report.generated_at
            })

            await self.db.commit()
            logger.info(f"Report saved: {report.report_id}")

        except Exception as e:
            logger.error(f"Error saving report: {e}")
