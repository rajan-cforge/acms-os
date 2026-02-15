"""Unit tests for Report Generator.

Tests the report generation module including:
- Report creation and formatting
- Weekly/monthly report generation
- Markdown and HTML export
- Data classes and serialization

Run with: pytest tests/unit/intelligence/test_report_generator.py -v
"""

import pytest
from datetime import date, datetime, timedelta
from src.intelligence.report_generator import (
    ReportGenerator,
    IntelligenceReport,
    ReportType,
    ReportStatus,
    ReportSummary,
    TopicEntry,
    ReportInsight,
    ReportRecommendation,
    KnowledgeGrowth,
    AgentStats,
    REPORT_CONFIG,
)


class TestReportType:
    """Tests for ReportType enum."""

    def test_report_type_values(self):
        """ReportType has correct values."""
        assert ReportType.WEEKLY_PERSONAL.value == "weekly_personal"
        assert ReportType.WEEKLY_ORG.value == "weekly_org"
        assert ReportType.MONTHLY_PERSONAL.value == "monthly_personal"
        assert ReportType.MONTHLY_ORG.value == "monthly_org"
        assert ReportType.ON_DEMAND.value == "on_demand"


class TestReportStatus:
    """Tests for ReportStatus enum."""

    def test_report_status_values(self):
        """ReportStatus has correct values."""
        assert ReportStatus.PENDING.value == "pending"
        assert ReportStatus.GENERATING.value == "generating"
        assert ReportStatus.COMPLETED.value == "completed"
        assert ReportStatus.FAILED.value == "failed"


class TestAgentStats:
    """Tests for AgentStats dataclass."""

    def test_create_agent_stats(self):
        """Can create agent stats."""
        stats = AgentStats(
            agent_name="claude",
            queries=100,
            cost_usd=2.50,
            avg_latency_ms=1500.5,
            percentage=45.0
        )
        assert stats.agent_name == "claude"
        assert stats.queries == 100
        assert stats.cost_usd == 2.50

    def test_agent_stats_to_dict(self):
        """Agent stats converts to dict correctly."""
        stats = AgentStats(
            agent_name="gpt",
            queries=50,
            cost_usd=1.25,
            avg_latency_ms=2000.123,
            percentage=30.5
        )
        d = stats.to_dict()

        assert d["agent"] == "gpt"
        assert d["queries"] == 50
        assert d["cost"] == 1.25
        assert d["avg_latency_ms"] == 2000.1  # Rounded
        assert d["percentage"] == 30.5


class TestKnowledgeGrowth:
    """Tests for KnowledgeGrowth dataclass."""

    def test_create_knowledge_growth(self):
        """Can create knowledge growth."""
        kg = KnowledgeGrowth(
            new_qa_pairs=156,
            facts_extracted=42,
            memories_promoted=8,
            topics_mastered=["kubernetes", "security"],
            topics_in_progress=["llm-routing", "memory-browser"]
        )
        assert kg.new_qa_pairs == 156
        assert len(kg.topics_mastered) == 2
        assert len(kg.topics_in_progress) == 2

    def test_knowledge_growth_to_dict(self):
        """Knowledge growth converts to dict correctly."""
        kg = KnowledgeGrowth(
            new_qa_pairs=100,
            facts_extracted=20,
            memories_promoted=5,
            topics_mastered=["python"],
            topics_in_progress=["rust"]
        )
        d = kg.to_dict()

        assert d["new_qa_pairs"] == 100
        assert d["facts_extracted"] == 20
        assert d["topics_mastered"] == ["python"]


class TestReportSummary:
    """Tests for ReportSummary dataclass."""

    def test_create_report_summary(self):
        """Can create report summary."""
        summary = ReportSummary(
            headline="Focus on security architecture this week",
            key_stats={
                "total_queries": 156,
                "unique_topics": 23,
                "total_cost_usd": 4.23
            }
        )
        assert "security" in summary.headline.lower()
        assert summary.key_stats["total_queries"] == 156

    def test_report_summary_to_dict(self):
        """Report summary converts to dict correctly."""
        summary = ReportSummary(
            headline="Test headline",
            key_stats={"foo": "bar"}
        )
        d = summary.to_dict()

        assert d["headline"] == "Test headline"
        assert d["key_stats"]["foo"] == "bar"


class TestTopicEntry:
    """Tests for TopicEntry dataclass."""

    def test_create_topic_entry(self):
        """Can create topic entry."""
        entry = TopicEntry(
            rank=1,
            topic="kubernetes",
            count=23,
            trend="up",
            trend_percent=45.5,
            sample_queries=["How do I deploy?"],
            first_seen="2025-12-01",
            last_seen="2025-12-12"
        )
        assert entry.rank == 1
        assert entry.topic == "kubernetes"
        assert entry.trend == "up"

    def test_topic_entry_to_dict(self):
        """Topic entry converts to dict correctly."""
        entry = TopicEntry(
            rank=2,
            topic="python",
            count=15,
            trend="stable",
            trend_percent=0.0,
            sample_queries=["What is Python?"]
        )
        d = entry.to_dict()

        assert d["rank"] == 2
        assert d["topic"] == "python"
        assert d["trend"] == "stable"
        assert len(d["sample_queries"]) == 1


class TestReportInsight:
    """Tests for ReportInsight dataclass."""

    def test_create_report_insight(self):
        """Can create report insight."""
        insight = ReportInsight(
            insight_type="emerging_theme",
            title="Security focus increasing",
            description="You've been exploring security topics more.",
            confidence=0.85,
            evidence={"source_count": 5}
        )
        assert insight.insight_type == "emerging_theme"
        assert insight.confidence == 0.85

    def test_report_insight_to_dict(self):
        """Report insight converts to dict correctly."""
        insight = ReportInsight(
            insight_type="cost_trend",
            title="Costs rising",
            description="Description",
            confidence=0.7,
            evidence={}
        )
        d = insight.to_dict()

        assert d["type"] == "cost_trend"
        assert d["title"] == "Costs rising"
        assert d["confidence"] == 0.7


class TestReportRecommendation:
    """Tests for ReportRecommendation dataclass."""

    def test_create_recommendation(self):
        """Can create recommendation."""
        rec = ReportRecommendation(
            priority="high",
            action="Create documentation",
            context="You've asked many questions about this"
        )
        assert rec.priority == "high"
        assert rec.action == "Create documentation"

    def test_recommendation_to_dict(self):
        """Recommendation converts to dict correctly."""
        rec = ReportRecommendation(
            priority="medium",
            action="Review costs",
            context="Costs are above average"
        )
        d = rec.to_dict()

        assert d["priority"] == "medium"
        assert d["action"] == "Review costs"


class TestIntelligenceReport:
    """Tests for IntelligenceReport dataclass."""

    @pytest.fixture
    def sample_report(self):
        """Create a sample report for testing."""
        return IntelligenceReport(
            report_id="report-123",
            report_type=ReportType.WEEKLY_PERSONAL,
            scope="user",
            tenant_id="default",
            user_id="user-456",

            period_start=date(2025, 12, 5),
            period_end=date(2025, 12, 12),
            generated_at=datetime(2025, 12, 12, 14, 30, 0),

            summary=ReportSummary(
                headline="Focus on kubernetes",
                key_stats={"total_queries": 100}
            ),
            top_topics=[
                TopicEntry(rank=1, topic="kubernetes", count=23, trend="up", trend_percent=45.0, sample_queries=["How to deploy?"])
            ],
            insights=[
                ReportInsight(
                    insight_type="emerging_theme",
                    title="K8s focus",
                    description="Description",
                    confidence=0.8,
                    evidence={}
                )
            ],
            recommendations=[
                ReportRecommendation(priority="high", action="Document", context="Context")
            ],
            knowledge_growth=KnowledgeGrowth(
                new_qa_pairs=100,
                facts_extracted=20,
                memories_promoted=5,
                topics_mastered=["python"],
                topics_in_progress=["rust"]
            ),
            agent_breakdown=[
                AgentStats(agent_name="claude", queries=60, cost_usd=3.0, avg_latency_ms=2000, percentage=60)
            ],

            generated_by="test",
            generation_time_ms=500,
            tokens_used=0,
            cost_usd=0.0,
            trace_id="trace-789"
        )

    def test_create_report(self, sample_report):
        """Can create intelligence report."""
        assert sample_report.report_id == "report-123"
        assert sample_report.report_type == ReportType.WEEKLY_PERSONAL
        assert sample_report.scope == "user"
        assert len(sample_report.top_topics) == 1
        assert len(sample_report.insights) == 1

    def test_report_to_dict(self, sample_report):
        """Report converts to dict correctly."""
        d = sample_report.to_dict()

        assert d["id"] == "report-123"
        assert d["type"] == "weekly_personal"
        assert d["scope"] == "user"
        assert d["period"]["start"] == "2025-12-05"
        assert d["period"]["end"] == "2025-12-12"
        assert "generated_at" in d
        assert "summary" in d
        assert len(d["top_topics"]) == 1
        assert len(d["insights"]) == 1
        assert "meta" in d
        assert d["meta"]["trace_id"] == "trace-789"


class TestReportGenerator:
    """Tests for ReportGenerator class."""

    @pytest.fixture
    def generator(self):
        """Create generator without DB."""
        return ReportGenerator(db_session=None, insights_engine=None)

    def test_build_summary(self, generator):
        """Build summary generates headline."""
        data = {
            "key_stats": {"total_queries": 100},
            "top_topics": [{"topic": "kubernetes"}]
        }

        summary = generator._build_summary(data, period_days=7)

        assert "kubernetes" in summary.headline.lower()
        assert "7 days" in summary.headline

    def test_build_summary_no_topics(self, generator):
        """Build summary handles empty topics."""
        data = {
            "key_stats": {"total_queries": 0},
            "top_topics": []
        }

        summary = generator._build_summary(data, period_days=30)

        assert "various topics" in summary.headline.lower()

    def test_build_top_topics(self, generator):
        """Build top topics creates entries."""
        topics_data = [
            {"topic": "k8s", "count": 10, "trend": "up", "trend_percent": 20.5},
            {"topic": "python", "count": 5, "trend": "stable", "trend_percent": 0}
        ]

        entries = generator._build_top_topics(topics_data)

        assert len(entries) == 2
        assert entries[0].rank == 1
        assert entries[0].topic == "k8s"
        assert entries[1].rank == 2

    def test_build_top_topics_limits_to_max(self, generator):
        """Build top topics respects limit."""
        # Create more topics than the limit
        topics_data = [
            {"topic": f"topic-{i}", "count": 100-i, "trend": "stable", "trend_percent": 0}
            for i in range(50)
        ]

        entries = generator._build_top_topics(topics_data)

        assert len(entries) <= REPORT_CONFIG["default_top_topics"]

    def test_build_insights(self, generator):
        """Build insights creates entries."""
        insights_data = [
            {"type": "emerging_theme", "title": "Test", "description": "Desc", "confidence": 0.8, "evidence": {}}
        ]

        entries = generator._build_insights(insights_data)

        assert len(entries) == 1
        assert entries[0].insight_type == "emerging_theme"

    def test_build_recommendations(self, generator):
        """Build recommendations creates entries."""
        rec_data = [
            {"priority": "high", "action": "Act", "context": "Ctx"}
        ]

        entries = generator._build_recommendations(rec_data)

        assert len(entries) == 1
        assert entries[0].priority == "high"

    def test_build_knowledge_growth(self, generator):
        """Build knowledge growth creates object."""
        data = {
            "key_stats": {"total_queries": 50},
            "top_topics": [
                {"topic": "k8s", "count": 15, "trend": "stable"},
                {"topic": "rust", "count": 5, "trend": "new"}
            ]
        }

        kg = generator._build_knowledge_growth(data)

        assert kg.new_qa_pairs == 50
        assert "k8s" in kg.topics_mastered
        assert "rust" in kg.topics_in_progress

    def test_build_agent_breakdown(self, generator):
        """Build agent breakdown creates entries."""
        stats = {
            "claude": {"queries": 60, "cost": 3.0, "latency": 2000, "percentage": 60},
            "gpt": {"queries": 40, "cost": 1.5, "latency": 1500, "percentage": 40}
        }

        entries = generator._build_agent_breakdown(stats)

        assert len(entries) == 2
        # Should be sorted by queries descending
        assert entries[0].agent_name == "claude"
        assert entries[0].queries == 60

    @pytest.mark.asyncio
    async def test_generate_report_weekly(self, generator):
        """Generate weekly report returns valid report."""
        report = await generator.generate_report(
            user_id="user-123",
            report_type="weekly",
            scope="user",
            tenant_id="default"
        )

        assert isinstance(report, IntelligenceReport)
        assert report.report_type == ReportType.WEEKLY_PERSONAL
        assert report.scope == "user"
        # Period should be 7 days
        assert (report.period_end - report.period_start).days == 7

    @pytest.mark.asyncio
    async def test_generate_report_monthly(self, generator):
        """Generate monthly report returns valid report."""
        report = await generator.generate_report(
            user_id="user-123",
            report_type="monthly",
            scope="user"
        )

        assert report.report_type == ReportType.MONTHLY_PERSONAL
        # Period should be 30 days
        assert (report.period_end - report.period_start).days == 30

    @pytest.mark.asyncio
    async def test_generate_report_org_scope(self, generator):
        """Generate org scope report sets correct type."""
        report = await generator.generate_report(
            user_id="admin-123",
            report_type="weekly",
            scope="org"
        )

        assert report.report_type == ReportType.WEEKLY_ORG
        assert report.scope == "org"
        assert report.user_id is None  # Org reports don't have user_id

    @pytest.mark.asyncio
    async def test_generate_report_custom_dates(self, generator):
        """Generate report with custom dates."""
        start = date(2025, 12, 1)
        end = date(2025, 12, 10)

        report = await generator.generate_report(
            user_id="user-123",
            report_type="custom",
            period_start=start,
            period_end=end
        )

        assert report.period_start == start
        assert report.period_end == end


class TestMarkdownFormat:
    """Tests for Markdown formatting."""

    @pytest.fixture
    def generator(self):
        """Create generator without DB."""
        return ReportGenerator(db_session=None)

    @pytest.fixture
    def sample_report(self):
        """Create a sample report for formatting tests."""
        return IntelligenceReport(
            report_id="report-md-test",
            report_type=ReportType.WEEKLY_PERSONAL,
            scope="user",
            tenant_id="default",
            user_id="user-456",

            period_start=date(2025, 12, 5),
            period_end=date(2025, 12, 12),
            generated_at=datetime(2025, 12, 12, 14, 30, 0),

            summary=ReportSummary(
                headline="Focus on kubernetes",
                key_stats={
                    "total_queries": 156,
                    "unique_topics": 23,
                    "total_cost_usd": 4.23,
                    "top_agent": "claude"
                }
            ),
            top_topics=[
                TopicEntry(rank=1, topic="kubernetes", count=23, trend="up", trend_percent=45.0, sample_queries=["How to deploy?"]),
                TopicEntry(rank=2, topic="python", count=15, trend="stable", trend_percent=0, sample_queries=[])
            ],
            insights=[
                ReportInsight(
                    insight_type="emerging_theme",
                    title="K8s adoption increasing",
                    description="Your interest in kubernetes has grown significantly.",
                    confidence=0.85,
                    evidence={}
                )
            ],
            recommendations=[
                ReportRecommendation(
                    priority="high",
                    action="Create K8s runbook",
                    context="You've built significant K8s knowledge"
                )
            ],
            knowledge_growth=KnowledgeGrowth(
                new_qa_pairs=156,
                facts_extracted=42,
                memories_promoted=8,
                topics_mastered=["docker"],
                topics_in_progress=["kubernetes"]
            ),
            agent_breakdown=[
                AgentStats(agent_name="claude", queries=100, cost_usd=3.5, avg_latency_ms=2000, percentage=65),
                AgentStats(agent_name="gpt", queries=56, cost_usd=0.73, avg_latency_ms=1500, percentage=35)
            ],

            generated_by="test",
            generation_time_ms=500,
            tokens_used=0,
            cost_usd=0.0,
            trace_id="trace-md"
        )

    def test_format_as_markdown_structure(self, generator, sample_report):
        """Markdown has expected sections."""
        md = generator.format_as_markdown(sample_report)

        # Check headers
        assert "# Intelligence Report" in md
        assert "## Executive Summary" in md
        assert "## Top" in md and "Topics" in md
        assert "## Key Insights" in md
        assert "## Recommendations" in md
        assert "## Knowledge Growth" in md
        assert "## Agent Usage" in md

    def test_format_as_markdown_summary(self, generator, sample_report):
        """Markdown includes summary stats."""
        md = generator.format_as_markdown(sample_report)

        assert "Focus on kubernetes" in md
        assert "156" in md  # total_queries
        assert "23" in md   # unique_topics
        assert "$4.23" in md  # cost

    def test_format_as_markdown_topics_table(self, generator, sample_report):
        """Markdown includes topics table."""
        md = generator.format_as_markdown(sample_report)

        assert "| Rank | Topic | Count | Trend |" in md
        assert "kubernetes" in md
        assert "python" in md

    def test_format_as_markdown_insights(self, generator, sample_report):
        """Markdown includes insights."""
        md = generator.format_as_markdown(sample_report)

        assert "K8s adoption increasing" in md
        assert "Confidence: 85%" in md

    def test_format_as_markdown_recommendations(self, generator, sample_report):
        """Markdown includes recommendations."""
        md = generator.format_as_markdown(sample_report)

        assert "Create K8s runbook" in md
        assert "[!]" in md  # High priority marker

    def test_format_as_markdown_agent_table(self, generator, sample_report):
        """Markdown includes agent table."""
        md = generator.format_as_markdown(sample_report)

        assert "| Agent | Queries | Cost | Avg Latency |" in md
        assert "claude" in md
        assert "gpt" in md


class TestHTMLFormat:
    """Tests for HTML formatting."""

    @pytest.fixture
    def generator(self):
        """Create generator without DB."""
        return ReportGenerator(db_session=None)

    @pytest.fixture
    def simple_report(self):
        """Create a simple report for HTML tests."""
        return IntelligenceReport(
            report_id="report-html",
            report_type=ReportType.WEEKLY_PERSONAL,
            scope="user",
            tenant_id="default",
            user_id="user-123",

            period_start=date(2025, 12, 5),
            period_end=date(2025, 12, 12),
            generated_at=datetime(2025, 12, 12, 14, 30, 0),

            summary=ReportSummary(headline="Test", key_stats={}),
            top_topics=[],
            insights=[],
            recommendations=[],
            knowledge_growth=KnowledgeGrowth(
                new_qa_pairs=0, facts_extracted=0, memories_promoted=0,
                topics_mastered=[], topics_in_progress=[]
            ),
            agent_breakdown=[],

            generated_by="test",
            generation_time_ms=100,
            tokens_used=0,
            cost_usd=0.0
        )

    def test_format_as_html_valid(self, generator, simple_report):
        """HTML output is valid HTML structure."""
        html = generator.format_as_html(simple_report)

        assert "<!DOCTYPE html>" in html
        assert "<html>" in html
        assert "</html>" in html
        assert "<head>" in html
        assert "<body>" in html

    def test_format_as_html_has_title(self, generator, simple_report):
        """HTML has title."""
        html = generator.format_as_html(simple_report)

        assert "<title>" in html
        assert "Intelligence Report" in html

    def test_format_as_html_has_styles(self, generator, simple_report):
        """HTML has embedded styles."""
        html = generator.format_as_html(simple_report)

        assert "<style>" in html
        assert "font-family" in html


class TestReportConfig:
    """Tests for report configuration."""

    def test_config_has_required_keys(self):
        """Config has all required keys."""
        assert "max_llm_cost_per_report" in REPORT_CONFIG
        assert "default_top_topics" in REPORT_CONFIG
        assert "max_insights_per_report" in REPORT_CONFIG
        assert "max_recommendations_per_report" in REPORT_CONFIG

    def test_config_reasonable_values(self):
        """Config values are reasonable."""
        assert REPORT_CONFIG["max_llm_cost_per_report"] <= 1.0  # Max $1
        assert REPORT_CONFIG["default_top_topics"] <= 50
        assert REPORT_CONFIG["max_insights_per_report"] <= 20
        assert REPORT_CONFIG["max_recommendations_per_report"] <= 10


class TestListReports:
    """Tests for listing reports."""

    @pytest.fixture
    def generator(self):
        """Create generator without DB."""
        return ReportGenerator(db_session=None)

    @pytest.mark.asyncio
    async def test_list_reports_without_db(self, generator):
        """List reports returns empty without DB."""
        reports = await generator.list_reports(
            user_id="user-123",
            tenant_id="default"
        )

        assert reports == []

    @pytest.mark.asyncio
    async def test_get_report_without_db(self, generator):
        """Get report returns None without DB."""
        report = await generator.get_report(
            report_id="nonexistent",
            user_id="user-123",
            tenant_id="default"
        )

        assert report is None
