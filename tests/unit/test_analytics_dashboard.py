"""
Unit tests for GET /analytics/dashboard endpoint (Week 4 Task 3)

Tests the comprehensive analytics aggregation that powers the Individual Metrics Dashboard.
Following TDD approach - tests written first.
"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta


@pytest.mark.asyncio
async def test_analytics_dashboard_basic_structure():
    """Test that dashboard endpoint returns expected JSON structure"""
    from src.api_server import app
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/analytics/dashboard?user_id=test_user&days=30")

        assert response.status_code == 200
        data = response.json()

        # Verify top-level structure
        assert "cache_performance" in data
        assert "source_performance" in data
        assert "user_satisfaction" in data
        assert "recent_queries" in data
        assert "time_period_days" in data


@pytest.mark.asyncio
async def test_cache_performance_metrics():
    """Test cache performance section includes hit rate and cost savings"""
    from src.api_server import app
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/analytics/dashboard?user_id=test_user")

        assert response.status_code == 200
        data = response.json()
        cache = data["cache_performance"]

        # Verify cache metrics
        assert "total_queries" in cache
        assert "cache_hits" in cache
        assert "semantic_cache_hits" in cache
        assert "cache_hit_rate" in cache
        assert "estimated_cost_savings" in cache

        # Validate types
        assert isinstance(cache["total_queries"], int)
        assert isinstance(cache["cache_hits"], int)
        assert isinstance(cache["semantic_cache_hits"], int)
        assert isinstance(cache["cache_hit_rate"], float)
        assert isinstance(cache["estimated_cost_savings"], float)

        # Validate ranges
        assert 0 <= cache["cache_hit_rate"] <= 100
        assert cache["estimated_cost_savings"] >= 0


@pytest.mark.asyncio
async def test_source_performance_comparison():
    """Test AI source performance includes latency and user satisfaction"""
    from src.api_server import app
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/analytics/dashboard?user_id=test_user")

        assert response.status_code == 200
        data = response.json()
        sources = data["source_performance"]

        # Verify source comparison structure
        assert isinstance(sources, list)

        if len(sources) > 0:
            source = sources[0]
            assert "source_name" in source
            assert "avg_rating" in source
            assert "total_queries" in source
            assert "thumbs_up" in source
            assert "thumbs_down" in source
            assert "regenerate_rate" in source

            # Validate types and ranges
            assert isinstance(source["avg_rating"], float)
            assert 0 <= source["avg_rating"] <= 5
            assert isinstance(source["total_queries"], int)
            assert source["total_queries"] >= 0
            assert 0 <= source["regenerate_rate"] <= 100


@pytest.mark.asyncio
async def test_user_satisfaction_trends():
    """Test user satisfaction includes overall metrics"""
    from src.api_server import app
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/analytics/dashboard?user_id=test_user")

        assert response.status_code == 200
        data = response.json()
        satisfaction = data["user_satisfaction"]

        # Verify satisfaction metrics
        assert "total_feedback" in satisfaction
        assert "avg_rating" in satisfaction
        assert "thumbs_up_percentage" in satisfaction
        assert "thumbs_down_percentage" in satisfaction
        assert "regenerate_percentage" in satisfaction

        # Validate types
        assert isinstance(satisfaction["total_feedback"], int)
        assert isinstance(satisfaction["avg_rating"], float)
        assert isinstance(satisfaction["thumbs_up_percentage"], float)

        # Validate ranges
        assert 0 <= satisfaction["avg_rating"] <= 5
        assert 0 <= satisfaction["thumbs_up_percentage"] <= 100


@pytest.mark.asyncio
async def test_recent_queries_with_feedback():
    """Test recent queries section includes query details and feedback"""
    from src.api_server import app
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/analytics/dashboard?user_id=test_user&recent_limit=10")

        assert response.status_code == 200
        data = response.json()
        recent = data["recent_queries"]

        # Verify structure
        assert isinstance(recent, list)
        assert len(recent) <= 10  # respects limit

        if len(recent) > 0:
            query = recent[0]
            assert "query_id" in query
            assert "question" in query
            assert "response_source" in query
            assert "created_at" in query
            assert "feedback_type" in query or query.get("feedback_type") is None
            assert "rating" in query or query.get("rating") is None


@pytest.mark.asyncio
async def test_dashboard_time_period_filtering():
    """Test that dashboard respects days parameter for time filtering"""
    from src.api_server import app
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test with 7 days
        response_7d = await client.get("/analytics/dashboard?user_id=test_user&days=7")
        assert response_7d.status_code == 200
        data_7d = response_7d.json()
        assert data_7d["time_period_days"] == 7

        # Test with 30 days (default)
        response_30d = await client.get("/analytics/dashboard?user_id=test_user")
        assert response_30d.status_code == 200
        data_30d = response_30d.json()
        assert data_30d["time_period_days"] == 30


@pytest.mark.asyncio
async def test_dashboard_with_default_user():
    """Test that dashboard handles 'default' user_id resolution"""
    from src.api_server import app
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/analytics/dashboard?user_id=default")

        assert response.status_code == 200
        data = response.json()

        # Should return valid dashboard data for default user
        assert "cache_performance" in data
        assert "source_performance" in data


@pytest.mark.asyncio
async def test_dashboard_zero_data_scenario():
    """Test dashboard gracefully handles users with no data"""
    from src.api_server import app
    from httpx import AsyncClient
    import uuid

    # Use a random UUID that definitely doesn't exist
    nonexistent_user = str(uuid.uuid4())

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get(f"/analytics/dashboard?user_id={nonexistent_user}")

        assert response.status_code == 200
        data = response.json()

        # Should return zero/empty metrics, not errors
        assert data["cache_performance"]["total_queries"] == 0
        assert data["cache_performance"]["cache_hit_rate"] == 0.0
        assert data["user_satisfaction"]["total_feedback"] == 0
        assert data["user_satisfaction"]["avg_rating"] == 0.0
        assert data["source_performance"] == []
        assert data["recent_queries"] == []


@pytest.mark.asyncio
async def test_dashboard_calculates_cost_savings():
    """Test that cost savings calculation is reasonable"""
    from src.api_server import app
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/analytics/dashboard?user_id=test_user")

        assert response.status_code == 200
        data = response.json()

        cache = data["cache_performance"]

        # Cost savings should be proportional to cache hits
        # Assuming $0.015 per external API call (Claude Sonnet 4.5 cost)
        expected_min_savings = (cache["cache_hits"] + cache["semantic_cache_hits"]) * 0.01

        assert cache["estimated_cost_savings"] >= expected_min_savings or cache["estimated_cost_savings"] == 0


@pytest.mark.asyncio
async def test_dashboard_source_performance_sorted():
    """Test that source performance is sorted by avg_rating descending"""
    from src.api_server import app
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/analytics/dashboard?user_id=test_user")

        assert response.status_code == 200
        data = response.json()
        sources = data["source_performance"]

        if len(sources) > 1:
            # Check that sources are sorted by avg_rating (highest first)
            for i in range(len(sources) - 1):
                assert sources[i]["avg_rating"] >= sources[i+1]["avg_rating"]


@pytest.mark.asyncio
async def test_dashboard_parameter_validation():
    """Test that invalid parameters are rejected"""
    from src.api_server import app
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Test days out of range
        response_bad_days = await client.get("/analytics/dashboard?user_id=test_user&days=500")
        assert response_bad_days.status_code == 422  # Validation error

        # Test negative recent_limit
        response_bad_limit = await client.get("/analytics/dashboard?user_id=test_user&recent_limit=-5")
        assert response_bad_limit.status_code == 422

        # Test missing user_id
        response_no_user = await client.get("/analytics/dashboard")
        assert response_no_user.status_code == 422
