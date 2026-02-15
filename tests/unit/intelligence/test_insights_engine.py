"""Unit tests for Insights Engine.

Tests the insights engine module including:
- Summary generation
- Topic analysis
- Trend detection
- Pattern detection
- Evidence grounding (no speculation allowed)

Run with: pytest tests/unit/intelligence/test_insights_engine.py -v
"""

import pytest
from datetime import date, timedelta
from src.intelligence.insights_engine import (
    InsightsEngine,
    InsightsSummary,
    TopicStat,
    TopicAnalysis,
    TrendsResponse,
    TrendPoint,
    TrendDirection,
    GeneratedInsight,
    InsightEvidence,
    InsightType,
    TrustLevel,
    Recommendation,
    INSIGHTS_CONFIG,
)


class TestTrustLevel:
    """Tests for TrustLevel enum."""

    def test_trust_level_values(self):
        """TrustLevel has correct values."""
        assert TrustLevel.HIGH.value == "high"
        assert TrustLevel.MEDIUM.value == "medium"
        assert TrustLevel.LOW.value == "low"


class TestInsightType:
    """Tests for InsightType enum."""

    def test_insight_type_values(self):
        """InsightType has correct values."""
        assert InsightType.EMERGING_THEME.value == "emerging_theme"
        assert InsightType.KNOWLEDGE_GAP.value == "knowledge_gap"
        assert InsightType.PRODUCTIVITY_TREND.value == "productivity_trend"
        assert InsightType.COST_TREND.value == "cost_trend"


class TestTrendDirection:
    """Tests for TrendDirection enum."""

    def test_trend_direction_values(self):
        """TrendDirection has correct values."""
        assert TrendDirection.UP.value == "up"
        assert TrendDirection.DOWN.value == "down"
        assert TrendDirection.STABLE.value == "stable"
        assert TrendDirection.NEW.value == "new"


class TestInsightEvidence:
    """Tests for InsightEvidence dataclass."""

    def test_create_evidence(self):
        """Can create evidence instance."""
        evidence = InsightEvidence(
            source_ids=["id1", "id2"],
            source_type="query_history",
            trust_level=TrustLevel.MEDIUM,
            snippet_preview="Sample query about kubernetes...",
            retrieval_score=0.95
        )
        assert evidence.source_ids == ["id1", "id2"]
        assert evidence.source_type == "query_history"
        assert evidence.trust_level == TrustLevel.MEDIUM
        assert evidence.retrieval_score == 0.95

    def test_evidence_to_dict(self):
        """Evidence converts to dict correctly."""
        evidence = InsightEvidence(
            source_ids=["id1"],
            source_type="query_history",
            trust_level=TrustLevel.HIGH,
            snippet_preview="Test snippet",
            retrieval_score=1.0
        )
        d = evidence.to_dict()

        assert d["source_ids"] == ["id1"]
        assert d["source_type"] == "query_history"
        assert d["trust_level"] == "high"
        assert d["snippet_preview"] == "Test snippet"


class TestGeneratedInsight:
    """Tests for GeneratedInsight dataclass."""

    def test_create_insight_with_evidence(self):
        """Can create insight with evidence."""
        evidence = InsightEvidence(
            source_ids=["id1"],
            source_type="query_history",
            trust_level=TrustLevel.MEDIUM,
            snippet_preview="Test",
            retrieval_score=1.0
        )

        insight = GeneratedInsight(
            insight_id="i1",
            insight_type=InsightType.EMERGING_THEME,
            title="Test Insight",
            description="This is a test insight",
            confidence=0.85,
            evidence=[evidence],
            generated_by="statistical"
        )

        assert insight.title == "Test Insight"
        assert insight.confidence == 0.85
        assert len(insight.evidence) == 1

    def test_insight_requires_evidence(self):
        """Insight without evidence raises ValueError."""
        with pytest.raises(ValueError, match="evidence"):
            GeneratedInsight(
                insight_id="i1",
                insight_type=InsightType.EMERGING_THEME,
                title="Test",
                description="Test",
                confidence=0.8,
                evidence=[],  # Empty - should fail
                generated_by="test"
            )

    def test_insight_confidence_bounds(self):
        """Insight confidence must be 0.0-1.0."""
        evidence = InsightEvidence(
            source_ids=["id1"],
            source_type="query_history",
            trust_level=TrustLevel.LOW,
            snippet_preview="Test",
            retrieval_score=1.0
        )

        # Above 1.0 should fail
        with pytest.raises(ValueError, match="[Cc]onfidence"):
            GeneratedInsight(
                insight_id="i1",
                insight_type=InsightType.COST_TREND,
                title="Test",
                description="Test",
                confidence=1.5,  # Invalid
                evidence=[evidence],
                generated_by="test"
            )

        # Negative should fail
        with pytest.raises(ValueError, match="[Cc]onfidence"):
            GeneratedInsight(
                insight_id="i1",
                insight_type=InsightType.COST_TREND,
                title="Test",
                description="Test",
                confidence=-0.1,  # Invalid
                evidence=[evidence],
                generated_by="test"
            )

    def test_insight_to_dict(self):
        """Insight converts to dict correctly."""
        evidence = InsightEvidence(
            source_ids=["id1"],
            source_type="query_history",
            trust_level=TrustLevel.MEDIUM,
            snippet_preview="Test",
            retrieval_score=1.0
        )

        insight = GeneratedInsight(
            insight_id="i1",
            insight_type=InsightType.EMERGING_THEME,
            title="Test Insight",
            description="Description",
            confidence=0.9,
            evidence=[evidence],
            generated_by="pattern_detection",
            trace_id="trace-123"
        )

        d = insight.to_dict()

        assert d["insight_id"] == "i1"
        assert d["type"] == "emerging_theme"
        assert d["title"] == "Test Insight"
        assert d["confidence"] == 0.9
        assert d["generated_by"] == "pattern_detection"
        assert d["trace_id"] == "trace-123"
        assert len(d["evidence"]) == 1


class TestTopicStat:
    """Tests for TopicStat dataclass."""

    def test_create_topic_stat(self):
        """Can create topic stat."""
        stat = TopicStat(
            topic="kubernetes",
            count=23,
            trend=TrendDirection.UP,
            trend_percent=45.5,
            sample_queries=["How do I deploy?"],
            first_seen=date(2025, 12, 1),
            last_seen=date(2025, 12, 10)
        )

        assert stat.topic == "kubernetes"
        assert stat.count == 23
        assert stat.trend == TrendDirection.UP
        assert stat.trend_percent == 45.5

    def test_topic_stat_to_dict(self):
        """Topic stat converts to dict correctly."""
        stat = TopicStat(
            topic="python",
            count=15,
            trend=TrendDirection.STABLE,
            trend_percent=0.0,
            sample_queries=["What is Python?", "How to use async?"],
            first_seen=date(2025, 12, 1),
            last_seen=date(2025, 12, 12)
        )

        d = stat.to_dict()

        assert d["topic"] == "python"
        assert d["count"] == 15
        assert d["trend"] == "stable"
        assert d["trend_percent"] == 0.0
        assert len(d["sample_queries"]) == 2
        assert d["first_seen"] == "2025-12-01"
        assert d["last_seen"] == "2025-12-12"


class TestRecommendation:
    """Tests for Recommendation dataclass."""

    def test_create_recommendation(self):
        """Can create recommendation."""
        rec = Recommendation(
            priority="high",
            action="Create documentation",
            context="You've asked many questions about this topic"
        )

        assert rec.priority == "high"
        assert rec.action == "Create documentation"

    def test_recommendation_to_dict(self):
        """Recommendation converts to dict correctly."""
        rec = Recommendation(
            priority="medium",
            action="Review model selection",
            context="Cost could be reduced"
        )

        d = rec.to_dict()

        assert d["priority"] == "medium"
        assert d["action"] == "Review model selection"
        assert d["context"] == "Cost could be reduced"


class TestTrendPoint:
    """Tests for TrendPoint dataclass."""

    def test_create_trend_point(self):
        """Can create trend point."""
        point = TrendPoint(
            date=date(2025, 12, 10),
            value=42.0,
            label="kubernetes"
        )

        assert point.date == date(2025, 12, 10)
        assert point.value == 42.0
        assert point.label == "kubernetes"

    def test_trend_point_to_dict(self):
        """Trend point converts to dict correctly."""
        point = TrendPoint(
            date=date(2025, 12, 10),
            value=15.5
        )

        d = point.to_dict()

        assert d["date"] == "2025-12-10"
        assert d["value"] == 15.5
        assert d["label"] is None


class TestInsightsSummary:
    """Tests for InsightsSummary dataclass."""

    def test_create_summary(self):
        """Can create insights summary."""
        evidence = InsightEvidence(
            source_ids=["id1"],
            source_type="query_history",
            trust_level=TrustLevel.MEDIUM,
            snippet_preview="Test",
            retrieval_score=1.0
        )

        summary = InsightsSummary(
            period_start=date(2025, 12, 5),
            period_end=date(2025, 12, 12),
            key_stats={
                "total_queries": 156,
                "unique_topics": 23,
                "total_cost_usd": 4.23
            },
            top_topics=[
                TopicStat(topic="kubernetes", count=23, trend=TrendDirection.UP)
            ],
            insights=[
                GeneratedInsight(
                    insight_id="i1",
                    insight_type=InsightType.EMERGING_THEME,
                    title="Test",
                    description="Test",
                    confidence=0.8,
                    evidence=[evidence],
                    generated_by="statistical"
                )
            ],
            recommendations=[
                Recommendation(priority="high", action="Test", context="Context")
            ]
        )

        assert summary.period_start == date(2025, 12, 5)
        assert summary.key_stats["total_queries"] == 156
        assert len(summary.top_topics) == 1
        assert len(summary.insights) == 1
        assert len(summary.recommendations) == 1

    def test_summary_to_dict(self):
        """Summary converts to dict correctly."""
        summary = InsightsSummary(
            period_start=date(2025, 12, 5),
            period_end=date(2025, 12, 12),
            key_stats={"total_queries": 100},
            top_topics=[],
            insights=[],
            recommendations=[]
        )

        d = summary.to_dict()

        assert d["period"]["start"] == "2025-12-05"
        assert d["period"]["end"] == "2025-12-12"
        assert d["key_stats"]["total_queries"] == 100


class TestTopicAnalysis:
    """Tests for TopicAnalysis dataclass."""

    def test_create_analysis(self):
        """Can create topic analysis."""
        analysis = TopicAnalysis(
            query="What have I learned about kubernetes?",
            topic="kubernetes",
            analysis_text="Based on 23 conversations...",
            key_learnings=["Helm charts", "Service mesh"],
            knowledge_gaps=["RBAC setup"],
            related_topics=["docker", "helm"],
            source_queries=[{"query_id": "q1", "question": "How to deploy?"}],
            confidence=0.85
        )

        assert analysis.topic == "kubernetes"
        assert len(analysis.key_learnings) == 2
        assert len(analysis.knowledge_gaps) == 1

    def test_analysis_to_dict(self):
        """Analysis converts to dict correctly."""
        analysis = TopicAnalysis(
            query="Test query",
            topic="python",
            analysis_text="Analysis text",
            key_learnings=["Learning 1"],
            knowledge_gaps=["Gap 1"],
            related_topics=["fastapi"],
            source_queries=[],
            confidence=0.7
        )

        d = analysis.to_dict()

        assert d["query"] == "Test query"
        assert d["topic"] == "python"
        assert d["analysis"] == "Analysis text"
        assert d["confidence"] == 0.7


class TestTrendsResponse:
    """Tests for TrendsResponse dataclass."""

    def test_create_trends_response(self):
        """Can create trends response."""
        trends = TrendsResponse(
            period_start=date(2025, 11, 12),
            period_end=date(2025, 12, 12),
            granularity="day",
            timeline=[
                {"date": "2025-12-10", "queries": 12, "cost": 0.45}
            ],
            topic_evolution={
                "kubernetes": [
                    TrendPoint(date=date(2025, 12, 10), value=5.0)
                ]
            },
            model_usage={"claude": 45.0, "gpt": 35.0, "gemini": 20.0}
        )

        assert trends.granularity == "day"
        assert len(trends.timeline) == 1
        assert "kubernetes" in trends.topic_evolution

    def test_trends_to_dict(self):
        """Trends converts to dict correctly."""
        trends = TrendsResponse(
            period_start=date(2025, 12, 1),
            period_end=date(2025, 12, 12),
            granularity="week",
            timeline=[],
            topic_evolution={},
            model_usage={"claude": 100.0}
        )

        d = trends.to_dict()

        assert d["period"]["start"] == "2025-12-01"
        assert d["granularity"] == "week"
        assert d["model_usage"]["claude"] == 100.0


class TestInsightsEngine:
    """Tests for InsightsEngine class."""

    @pytest.fixture
    def engine(self):
        """Create engine without DB or LLM."""
        return InsightsEngine(db_session=None, llm_provider=None)

    def test_extract_topic_from_query_about(self, engine):
        """Extracts topic from 'about X' pattern."""
        topic = engine._extract_topic_from_query(
            "What have I learned about kubernetes?"
        )
        assert topic == "kubernetes"

    def test_extract_topic_from_query_regarding(self, engine):
        """Extracts topic from 'regarding X' pattern."""
        topic = engine._extract_topic_from_query(
            "Show me insights regarding python"
        )
        assert topic == "python"

    def test_extract_topic_fallback(self, engine):
        """Falls back to last significant word."""
        topic = engine._extract_topic_from_query(
            "How does deployment work?"
        )
        # Falls back to last significant word (>3 chars)
        assert topic == "work"

    def test_extract_topic_specific_word(self, engine):
        """Extracts specific word when it's the last significant one."""
        topic = engine._extract_topic_from_query(
            "Tell me about kubernetes"
        )
        # "about X" pattern should work
        assert topic == "kubernetes"

    def test_extract_topic_general_fallback(self, engine):
        """Falls back to 'general' for short queries."""
        topic = engine._extract_topic_from_query("Hi")
        assert topic == "general"

    def test_generate_analysis_text_empty(self, engine):
        """Generates text for zero queries."""
        text = engine._generate_analysis_text(
            topic="kubernetes",
            query_count=0,
            period_days=30,
            key_learnings=[]
        )
        assert "No queries found" in text
        assert "kubernetes" in text

    def test_generate_analysis_text_with_learnings(self, engine):
        """Generates text with key learnings."""
        text = engine._generate_analysis_text(
            topic="docker",
            query_count=15,
            period_days=7,
            key_learnings=["Container basics", "Docker compose"]
        )
        assert "15 conversations" in text
        assert "7 days" in text
        assert "Container basics" in text

    def test_extract_key_learnings_empty(self, engine):
        """Handles empty query list."""
        learnings = engine._extract_key_learnings([])
        assert learnings == []

    def test_extract_key_learnings_from_answers(self, engine):
        """Extracts learnings from query answers."""
        queries = [
            {"answer": "Kubernetes uses pods to group containers together for deployment."},
            {"answer": "Docker compose allows you to define multi-container applications."},
        ]
        learnings = engine._extract_key_learnings(queries)

        # Should extract sentences
        assert len(learnings) > 0
        assert all(isinstance(l, str) for l in learnings)

    @pytest.mark.asyncio
    async def test_generate_summary_without_db(self, engine):
        """Summary generation returns defaults without DB."""
        summary = await engine.generate_summary(
            user_id="user-123",
            tenant_id="default",
            period_days=7,
            scope="user"
        )

        assert isinstance(summary, InsightsSummary)
        assert summary.key_stats["total_queries"] == 0
        assert summary.top_topics == []
        # No insights without data
        assert summary.insights == []

    @pytest.mark.asyncio
    async def test_analyze_topic_without_db(self, engine):
        """Topic analysis returns defaults without DB."""
        analysis = await engine.analyze_topic(
            user_id="user-123",
            query="What have I learned about kubernetes?",
            tenant_id="default",
            period_days=30
        )

        assert isinstance(analysis, TopicAnalysis)
        assert analysis.topic == "kubernetes"
        assert "No queries found" in analysis.analysis_text

    @pytest.mark.asyncio
    async def test_get_trends_without_db(self, engine):
        """Trends returns defaults without DB."""
        trends = await engine.get_trends(
            user_id="user-123",
            tenant_id="default",
            period_days=30,
            granularity="day",
            scope="user"
        )

        assert isinstance(trends, TrendsResponse)
        assert trends.granularity == "day"
        assert trends.timeline == []
        assert trends.topic_evolution == {}
        assert trends.model_usage == {}


class TestInsightsConfig:
    """Tests for insights configuration."""

    def test_config_defaults(self):
        """Config has expected defaults."""
        assert "max_llm_cost_per_summary" in INSIGHTS_CONFIG
        assert "max_llm_cost_per_analysis" in INSIGHTS_CONFIG
        assert "default_period_days" in INSIGHTS_CONFIG
        assert "max_period_days" in INSIGHTS_CONFIG
        assert "top_topics_limit" in INSIGHTS_CONFIG

    def test_config_reasonable_values(self):
        """Config values are reasonable."""
        assert INSIGHTS_CONFIG["max_llm_cost_per_summary"] <= 1.0  # Max $1 per summary
        assert INSIGHTS_CONFIG["max_llm_cost_per_analysis"] <= 1.0  # Max $1 per analysis
        assert INSIGHTS_CONFIG["default_period_days"] <= 30
        assert INSIGHTS_CONFIG["max_period_days"] <= 365
        assert INSIGHTS_CONFIG["top_topics_limit"] <= 100


class TestPatternDetection:
    """Tests for pattern detection logic."""

    @pytest.fixture
    def engine(self):
        """Create engine without DB."""
        return InsightsEngine(db_session=None)

    @pytest.mark.asyncio
    async def test_detect_emerging_themes(self, engine):
        """Detects emerging themes from trending topics."""
        key_stats = {"total_queries": 100}
        top_topics = [
            TopicStat(
                topic="kubernetes",
                count=23,
                trend=TrendDirection.UP,
                trend_percent=50.0  # High upward trend
            ),
            TopicStat(
                topic="python",
                count=15,
                trend=TrendDirection.STABLE,
                trend_percent=0.0
            )
        ]

        insights = await engine._detect_patterns(
            user_id="u1",
            tenant_id="default",
            period_start=date(2025, 12, 5),
            period_end=date(2025, 12, 12),
            scope="user",
            key_stats=key_stats,
            top_topics=top_topics
        )

        # Should detect emerging theme for kubernetes
        emerging = [i for i in insights if i.insight_type == InsightType.EMERGING_THEME]
        assert len(emerging) >= 1
        assert "kubernetes" in emerging[0].title.lower()

    @pytest.mark.asyncio
    async def test_detect_new_topics(self, engine):
        """Detects newly explored topics."""
        key_stats = {"total_queries": 50}
        top_topics = [
            TopicStat(
                topic="rust",
                count=5,
                trend=TrendDirection.NEW,  # New topic
                trend_percent=100.0
            )
        ]

        insights = await engine._detect_patterns(
            user_id="u1",
            tenant_id="default",
            period_start=date(2025, 12, 5),
            period_end=date(2025, 12, 12),
            scope="user",
            key_stats=key_stats,
            top_topics=top_topics
        )

        # Should detect topic shift
        shifts = [i for i in insights if i.insight_type == InsightType.TOPIC_SHIFT]
        assert len(shifts) >= 1

    @pytest.mark.asyncio
    async def test_all_insights_have_evidence(self, engine):
        """All generated insights must have evidence."""
        key_stats = {"total_queries": 100, "total_cost_usd": 15.0, "cache_hit_rate": 10}
        top_topics = [
            TopicStat(topic="k8s", count=10, trend=TrendDirection.UP, trend_percent=30)
        ]

        insights = await engine._detect_patterns(
            user_id="u1",
            tenant_id="default",
            period_start=date(2025, 12, 5),
            period_end=date(2025, 12, 12),
            scope="user",
            key_stats=key_stats,
            top_topics=top_topics
        )

        for insight in insights:
            # Every insight MUST have evidence
            assert len(insight.evidence) > 0, f"Insight '{insight.title}' has no evidence"


class TestRecommendationGeneration:
    """Tests for recommendation generation."""

    @pytest.fixture
    def engine(self):
        """Create engine without DB."""
        return InsightsEngine(db_session=None)

    @pytest.mark.asyncio
    async def test_generate_topic_recommendation(self, engine):
        """Generates recommendation for frequently asked topics."""
        insights = []
        top_topics = [
            TopicStat(topic="kubernetes", count=10, trend=TrendDirection.STABLE)
        ]
        key_stats = {"total_cost_usd": 2.0}

        recommendations = await engine._generate_recommendations(
            insights=insights,
            top_topics=top_topics,
            key_stats=key_stats
        )

        # Should recommend documentation for top topic
        assert len(recommendations) >= 1
        assert any("kubernetes" in r.action.lower() or "knowledge" in r.action.lower()
                   for r in recommendations)

    @pytest.mark.asyncio
    async def test_generate_cost_recommendation(self, engine):
        """Generates cost recommendation for high spenders."""
        insights = []
        top_topics = []
        key_stats = {"total_cost_usd": 15.0}  # High cost

        recommendations = await engine._generate_recommendations(
            insights=insights,
            top_topics=top_topics,
            key_stats=key_stats
        )

        # Should recommend cost review
        cost_recs = [r for r in recommendations if "cost" in r.action.lower() or "model" in r.action.lower()]
        assert len(cost_recs) >= 1
        assert cost_recs[0].priority == "high"
