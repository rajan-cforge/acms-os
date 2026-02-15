"""Unit tests for user feedback system (Week 4 Task 2).

Tests cover:
1. Feedback submission (thumbs up/down/regenerate)
2. Feedback summary aggregation
3. User feedback statistics (for auto-tuning)
4. Query ID tracking in /ask endpoint
5. Denormalized feedback_summary in memories table

TDD Approach: These tests are written BEFORE implementation.
Expected: All tests fail initially, then pass after Phase 3-4 implementation.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import httpx

# Import will fail until we implement the endpoints
try:
    from src.api_server import app
except ImportError:
    app = None
    pytest.skip("API server not available", allow_module_level=True)


@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client for testing FastAPI app with async operations."""
    from httpx import ASGITransport
    async with httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


class TestFeedbackSubmission:
    """Test feedback submission (thumbs up/down/regenerate)."""

    @pytest.mark.asyncio
    async def test_submit_thumbs_up_success(self, async_client):
        """User can submit positive feedback."""
        # ARRANGE: Create a test memory to act as query
        # First, create a memory via /memories endpoint (use UUID for uniqueness)
        unique_id = str(uuid4())
        memory_response = await async_client.post("/memories", json={
            "content": f"Test query: What is ACMS? ({unique_id})",
            "tags": ["test", "query"],
            "tier": "LONG",
            "phase": "testing"
        })
        assert memory_response.status_code == 200
        query_id = memory_response.json()["memory_id"]

        # ACT: Submit thumbs up feedback
        feedback_response = await async_client.post("/feedback", json={
            "query_id": query_id,
            "rating": 5,
            "feedback_type": "thumbs_up",
            "response_source": "claude",
            "comment": "Great answer!"
        })

        # ASSERT: Feedback stored successfully
        assert feedback_response.status_code == 200
        data = feedback_response.json()
        assert data["status"] == "success"
        assert "feedback_id" in data
        assert data["updated_summary"]["thumbs_up"] == 1
        assert data["updated_summary"]["total_ratings"] == 1
        assert data["updated_summary"]["avg_rating"] == 5.0

    @pytest.mark.asyncio
    async def test_submit_thumbs_down_success(self, async_client):
        """User can submit negative feedback."""
        # ARRANGE: Create test memory
        unique_id = str(uuid4())
        memory_response = await async_client.post("/memories", json={
            "content": f"Test query: How does semantic cache work? ({unique_id})",
            "tags": ["test"],
            "tier": "LONG"
        })
        query_id = memory_response.json()["memory_id"]

        # ACT: Submit thumbs down
        feedback_response = await async_client.post("/feedback", json={
            "query_id": query_id,
            "rating": 1,
            "feedback_type": "thumbs_down",
            "response_source": "semantic_cache",
            "comment": "Answer was incorrect"
        })

        # ASSERT
        assert feedback_response.status_code == 200
        data = feedback_response.json()
        assert data["updated_summary"]["thumbs_down"] == 1
        assert data["updated_summary"]["avg_rating"] == 1.0

    @pytest.mark.asyncio
    async def test_submit_regenerate_success(self, async_client):
        """User can submit regenerate feedback."""
        # ARRANGE: Create test memory
        unique_id = str(uuid4())
        memory_response = await async_client.post("/memories", json={
            "content": f"Test query: Explain CRS scoring ({unique_id})",
            "tags": ["test"],
            "tier": "LONG"
        })
        query_id = memory_response.json()["memory_id"]

        # ACT: Submit regenerate
        feedback_response = await async_client.post("/feedback", json={
            "query_id": query_id,
            "rating": 2,
            "feedback_type": "regenerate",
            "response_source": "claude"
        })

        # ASSERT
        assert feedback_response.status_code == 200
        data = feedback_response.json()
        assert data["updated_summary"]["regenerates"] == 1

    @pytest.mark.asyncio
    async def test_feedback_requires_valid_query_id(self, async_client):
        """Feedback submission fails for non-existent query."""
        # ACT: Submit feedback for non-existent query
        fake_query_id = str(uuid4())
        feedback_response = await async_client.post("/feedback", json={
            "query_id": fake_query_id,
            "rating": 5,
            "feedback_type": "thumbs_up",
            "response_source": "claude"
        })

        # ASSERT: 404 error
        assert feedback_response.status_code == 404
        assert "not found" in feedback_response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_feedback_requires_rating_in_range(self, async_client):
        """Rating must be 1-5."""
        # ARRANGE: Create test memory
        unique_id = str(uuid4())
        memory_response = await async_client.post("/memories", json={
            "content": f"Test query ({unique_id})",
            "tags": ["test"],
            "tier": "LONG"
        })
        query_id = memory_response.json()["memory_id"]

        # ACT & ASSERT: Rating too low (0)
        response_low = await async_client.post("/feedback", json={
            "query_id": query_id,
            "rating": 0,
            "feedback_type": "thumbs_up",
            "response_source": "claude"
        })
        assert response_low.status_code == 422  # Pydantic validation error

        # ACT & ASSERT: Rating too high (6)
        response_high = await async_client.post("/feedback", json={
            "query_id": query_id,
            "rating": 6,
            "feedback_type": "thumbs_up",
            "response_source": "claude"
        })
        assert response_high.status_code == 422


class TestFeedbackSummary:
    """Test feedback summary aggregation."""

    @pytest.mark.asyncio
    async def test_get_feedback_summary_after_submission(self, async_client):
        """Feedback summary shows updated counts."""
        # ARRANGE: Create test memory
        unique_id = str(uuid4())
        memory_response = await async_client.post("/memories", json={
            "content": f"Test query for summary ({unique_id})",
            "tags": ["test"],
            "tier": "LONG"
        })
        query_id = memory_response.json()["memory_id"]

        # Submit multiple feedback entries
        await async_client.post("/feedback", json={
            "query_id": query_id, "rating": 5, "feedback_type": "thumbs_up", "response_source": "claude"
        })
        await async_client.post("/feedback", json={
            "query_id": query_id, "rating": 5, "feedback_type": "thumbs_up", "response_source": "claude"
        })
        await async_client.post("/feedback", json={
            "query_id": query_id, "rating": 4, "feedback_type": "thumbs_up", "response_source": "claude"
        })
        await async_client.post("/feedback", json={
            "query_id": query_id, "rating": 1, "feedback_type": "thumbs_down", "response_source": "claude"
        })

        # ACT: Get feedback summary
        summary_response = await async_client.get(f"/feedback/summary/{query_id}")

        # ASSERT
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["total_ratings"] == 4
        assert summary["thumbs_up"] == 3
        assert summary["thumbs_down"] == 1
        assert summary["avg_rating"] == pytest.approx(3.75, rel=0.1)  # (5+5+4+1)/4 = 3.75

    @pytest.mark.asyncio
    async def test_feedback_summary_for_nonexistent_query(self, async_client):
        """Summary for non-existent query returns zeros."""
        # ACT: Get summary for random UUID
        fake_query_id = str(uuid4())
        summary_response = await async_client.get(f"/feedback/summary/{fake_query_id}")

        # ASSERT: Returns zeros, not 404
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert summary["total_ratings"] == 0
        assert summary["avg_rating"] == 0.0
        assert summary["thumbs_up"] == 0
        assert summary["thumbs_down"] == 0
        assert summary["regenerates"] == 0

    @pytest.mark.asyncio
    async def test_memory_feedback_summary_denormalized(self, async_client):
        """feedback_summary column in memories table updates."""
        # ARRANGE: Create test memory
        unique_id = str(uuid4())
        memory_response = await async_client.post("/memories", json={
            "content": f"Test denormalized feedback ({unique_id})",
            "tags": ["test"],
            "tier": "LONG"
        })
        query_id = memory_response.json()["memory_id"]

        # Submit feedback
        await async_client.post("/feedback", json={
            "query_id": query_id, "rating": 5, "feedback_type": "thumbs_up", "response_source": "claude"
        })

        # ACT: Get memory directly via /memories/{id}
        memory_get_response = await async_client.get(f"/memories/{query_id}")

        # ASSERT: Memory contains feedback_summary in metadata or dedicated field
        assert memory_get_response.status_code == 200
        memory = memory_get_response.json()

        # Check if feedback_summary exists (might be in metadata or top-level)
        has_feedback = (
            "feedback_summary" in memory or
            ("metadata" in memory and "feedback_summary" in memory["metadata"])
        )
        assert has_feedback, "Memory should have feedback_summary data"


class TestUserFeedbackStats:
    """Test user-level feedback statistics (for auto-tuning)."""

    @pytest.mark.asyncio
    async def test_user_feedback_stats_by_source(self, async_client):
        """User stats broken down by response source."""
        # ARRANGE: Create multiple queries and submit feedback
        # Create query 1 (cache source)
        mem1_response = await async_client.post("/memories", json={"content": f"Query 1 ({str(uuid4())})", "tags": ["test"], "tier": "LONG"})
        mem1 = mem1_response.json()
        await async_client.post("/feedback", json={
            "query_id": mem1["memory_id"], "rating": 5, "feedback_type": "thumbs_up", "response_source": "semantic_cache"
        })
        await async_client.post("/feedback", json={
            "query_id": mem1["memory_id"], "rating": 4, "feedback_type": "thumbs_up", "response_source": "semantic_cache"
        })

        # Create query 2 (claude source)
        mem2_response = await async_client.post("/memories", json={"content": f"Query 2 ({str(uuid4())})", "tags": ["test"], "tier": "LONG"})
        mem2 = mem2_response.json()
        await async_client.post("/feedback", json={
            "query_id": mem2["memory_id"], "rating": 3, "feedback_type": "thumbs_down", "response_source": "claude"
        })

        # ACT: Get user feedback stats (using default user)
        # First get default user ID
        health_response = await async_client.get("/health")
        # We'll need to infer user_id or use "default" endpoint
        # For now, use a placeholder - implementation will determine actual endpoint
        stats_response = await async_client.get("/feedback/user/default?days=30")

        # ASSERT
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert "sources" in stats
        assert len(stats["sources"]) >= 2  # semantic_cache and claude

        # Find semantic_cache stats
        cache_stats = next((s for s in stats["sources"] if s["response_source"] == "semantic_cache"), None)
        assert cache_stats is not None
        assert cache_stats["count"] == 2
        assert cache_stats["avg_rating"] == pytest.approx(4.5, rel=0.1)  # (5+4)/2

        # Find claude stats
        claude_stats = next((s for s in stats["sources"] if s["response_source"] == "claude"), None)
        assert claude_stats is not None
        assert claude_stats["count"] == 1
        assert claude_stats["avg_rating"] == pytest.approx(3.0, rel=0.1)

    @pytest.mark.asyncio
    async def test_user_feedback_stats_time_filter(self, async_client):
        """Stats respect time period filter."""
        # NOTE: This test requires time manipulation which is complex in real DB
        # We'll mark it as a placeholder - in production, use database time functions
        # For now, test that the endpoint accepts days parameter

        stats_response = await async_client.get("/feedback/user/default?days=7")
        assert stats_response.status_code == 200
        stats = stats_response.json()
        assert "time_period_days" in stats
        assert stats["time_period_days"] == 7


class TestAskEndpointQueryIdTracking:
    """Test that /ask endpoint returns query_id and response_source."""

    @pytest.mark.asyncio
    async def test_ask_returns_query_id_and_source(self, async_client):
        """Ask endpoint returns query_id for feedback tracking."""
        # ARRANGE: Ask a question
        ask_response = await async_client.post("/ask", json={
            "question": "What is ACMS semantic cache?",
            "context_limit": 5
        })

        # ASSERT: Response includes query_id and response_source
        assert ask_response.status_code == 200
        data = ask_response.json()
        assert "query_id" in data, "Ask endpoint must return query_id for feedback tracking"
        assert "response_source" in data, "Ask endpoint must return response_source (cache/semantic_cache/claude)"
        assert data["query_id"] is not None
        assert data["response_source"] in ["cache", "semantic_cache", "claude", "chatgpt", "gemini"]


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
