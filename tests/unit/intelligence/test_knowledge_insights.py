"""Unit tests for Knowledge-Powered Insights.

TDD approach: Tests written first, then implementation.

Tests cover:
- KnowledgeInsightsService class
- Expertise center calculation
- Learning pattern analysis
- Cross-domain connections
- Attention signals generation
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, date, timedelta
from collections import Counter


class TestKnowledgeInsightsService:
    """Tests for the KnowledgeInsightsService class."""

    @pytest.fixture
    def mock_weaviate_client(self):
        """Create a mock Weaviate client with sample knowledge data."""
        mock_client = Mock()
        mock_collection = Mock()

        # Sample knowledge objects
        mock_objects = []
        for i, (domain, topic, intent, facts) in enumerate([
            ("system-architecture", "acms-architecture", "building",
             ["Fact 1 about architecture", "Fact 2 about design patterns"]),
            ("system-architecture", "microservices", "building",
             ["Microservices communicate via APIs", "Service mesh handles routing"]),
            ("python-programming", "async-patterns", "learning",
             ["Use asyncio for concurrent IO", "await suspends coroutine execution"]),
            ("python-programming", "error-handling", "debugging",
             ["Catch specific exceptions", "Use context managers for cleanup"]),
            ("investment-analysis", "value-investing", "learning",
             ["Buy when price < intrinsic value", "Margin of safety is key"]),
        ]):
            obj = Mock()
            obj.uuid = f"uuid-{i}"
            obj.properties = {
                "problem_domain": domain,
                "topic_cluster": topic,
                "primary_intent": intent,
                "key_facts": facts,
                "related_topics": ["python", "architecture"] if i < 2 else ["finance"],
                "canonical_query": f"Sample query {i}",
                "created_at": datetime.utcnow().isoformat()
            }
            mock_objects.append(obj)

        mock_result = Mock()
        mock_result.objects = mock_objects
        mock_collection.query.fetch_objects.return_value = mock_result

        # Aggregate mock
        mock_aggregate = Mock()
        mock_aggregate.total_count = len(mock_objects)
        mock_collection.aggregate.over_all.return_value = mock_aggregate

        mock_client._client.collections.get.return_value = mock_collection
        mock_client.close = Mock()
        mock_client.is_ready = Mock(return_value=True)

        return mock_client

    @pytest.fixture
    def service(self, mock_weaviate_client):
        """Create KnowledgeInsightsService with mocked dependencies."""
        with patch('src.storage.weaviate_client.WeaviateClient', return_value=mock_weaviate_client):
            from src.intelligence.knowledge_insights import KnowledgeInsightsService
            svc = KnowledgeInsightsService()
            # Manually inject the mock data
            svc._client = mock_weaviate_client
            svc._knowledge_data = [obj.properties for obj in mock_weaviate_client._client.collections.get().query.fetch_objects().objects]
            svc._loaded = True
            return svc

    def test_get_expertise_centers(self, service):
        """Test expertise center calculation groups by domain with fact counts."""
        centers = service.get_expertise_centers()

        assert isinstance(centers, list)
        assert len(centers) > 0

        # Check structure of expertise center
        center = centers[0]
        assert "domain" in center
        assert "item_count" in center
        assert "fact_count" in center
        assert "depth_level" in center
        assert "topics" in center
        assert "sample_insight" in center

        # system-architecture should be top (2 items, 4 facts)
        arch_center = next((c for c in centers if c["domain"] == "system-architecture"), None)
        assert arch_center is not None
        assert arch_center["item_count"] == 2
        assert arch_center["fact_count"] == 4

    def test_get_learning_patterns(self, service):
        """Test learning pattern analysis categorizes by intent."""
        patterns = service.get_learning_patterns()

        assert isinstance(patterns, dict)
        assert "building" in patterns
        assert "learning" in patterns
        assert "debugging" in patterns

        # Check percentages sum to ~100
        total_pct = sum(p["percentage"] for p in patterns.values())
        assert 95 <= total_pct <= 105  # Allow small rounding variance

        # Building should be highest (2 items)
        assert patterns["building"]["count"] == 2

    def test_get_cross_domain_connections(self, service):
        """Test cross-domain connection discovery."""
        connections = service.get_cross_domain_connections()

        assert isinstance(connections, list)
        # Each connection should have topic and domains it connects
        if connections:
            conn = connections[0]
            assert "topic" in conn
            assert "domains" in conn
            assert "connection_count" in conn

    def test_get_attention_signals(self, service):
        """Test attention signals identify areas needing focus."""
        signals = service.get_attention_signals()

        assert isinstance(signals, dict)
        assert "deep_expertise" in signals
        assert "needs_attention" in signals
        assert "growing_areas" in signals

        # Each signal should have domain and reason
        for signal_type in signals.values():
            for signal in signal_type:
                assert "domain" in signal or "topic" in signal
                assert "reason" in signal

    def test_get_key_facts_summary(self, service):
        """Test key facts extraction per domain."""
        facts = service.get_key_facts_summary(max_per_domain=2)

        assert isinstance(facts, dict)
        # Should have facts grouped by domain
        assert len(facts) > 0

        for domain, domain_facts in facts.items():
            assert isinstance(domain_facts, list)
            assert len(domain_facts) <= 2  # Respects max

    def test_get_knowledge_velocity(self, service):
        """Test knowledge velocity metrics."""
        velocity = service.get_knowledge_velocity(period_days=7)

        assert isinstance(velocity, dict)
        assert "total_items" in velocity
        assert "total_facts" in velocity
        assert "domains_covered" in velocity
        assert "facts_per_item_avg" in velocity

    def test_generate_full_report(self, service):
        """Test full knowledge insights report generation."""
        report = service.generate_report(period_days=30)

        assert isinstance(report, dict)
        assert "generated_at" in report
        assert "period_days" in report
        assert "executive_summary" in report
        assert "expertise_centers" in report
        assert "learning_patterns" in report
        assert "cross_domain_connections" in report
        assert "attention_signals" in report
        assert "key_facts" in report
        assert "recommendations" in report

    def test_generate_recommendations(self, service):
        """Test actionable recommendations generation."""
        recommendations = service.generate_recommendations()

        assert isinstance(recommendations, list)
        for rec in recommendations:
            assert "priority" in rec
            assert "action" in rec
            assert "context" in rec
            assert rec["priority"] in ["high", "medium", "low"]


@pytest.mark.skip(reason="Integration tests - requires running services")
class TestKnowledgeInsightsAPI:
    """Integration tests for the API endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from src.api_server import app
        return TestClient(app)

    def test_knowledge_insights_endpoint_returns_200(self, client):
        """Test /api/v2/insights/knowledge returns 200."""
        pass

    def test_knowledge_insights_endpoint_structure(self, client):
        """Test response structure matches expected format."""
        pass


class TestDepthLevelCalculation:
    """Tests for expertise depth level calculation."""

    def test_depth_deep_threshold(self):
        """Test deep expertise threshold (>20 facts)."""
        from src.intelligence.knowledge_insights import calculate_depth_level

        assert calculate_depth_level(25) == "deep"
        assert calculate_depth_level(100) == "deep"

    def test_depth_growing_threshold(self):
        """Test growing expertise threshold (5-20 facts)."""
        from src.intelligence.knowledge_insights import calculate_depth_level

        assert calculate_depth_level(10) == "growing"
        assert calculate_depth_level(5) == "growing"
        assert calculate_depth_level(20) == "growing"

    def test_depth_shallow_threshold(self):
        """Test shallow expertise threshold (<5 facts)."""
        from src.intelligence.knowledge_insights import calculate_depth_level

        assert calculate_depth_level(4) == "shallow"
        assert calculate_depth_level(1) == "shallow"
        assert calculate_depth_level(0) == "shallow"
