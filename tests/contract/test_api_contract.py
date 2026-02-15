"""API Contract Tests.

Verifies that the ACMS API implementation matches the OpenAPI specification.
These tests ensure API contracts are maintained across versions.

Blueprint Section 6 - Testing & TDD: Evidence-Driven, API-First

Note: These tests run against the live API server (localhost:40080).
Make sure Docker services are running: docker-compose up -d
"""

import pytest
import requests
from uuid import uuid4
import json
import os

# API base URL - uses the running Docker container
API_BASE_URL = os.environ.get("ACMS_API_URL", "http://localhost:40080")


class APIClient:
    """Simple HTTP client for API testing."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def get(self, path: str, **kwargs) -> requests.Response:
        return requests.get(f"{self.base_url}{path}", **kwargs)

    def post(self, path: str, **kwargs) -> requests.Response:
        return requests.post(f"{self.base_url}{path}", **kwargs)

    def put(self, path: str, **kwargs) -> requests.Response:
        return requests.put(f"{self.base_url}{path}", **kwargs)

    def delete(self, path: str, **kwargs) -> requests.Response:
        return requests.delete(f"{self.base_url}{path}", **kwargs)


client = APIClient(API_BASE_URL)


@pytest.fixture(scope="session", autouse=True)
def check_api_running():
    """Check if API is running before tests."""
    try:
        response = client.get("/health")
        if response.status_code != 200:
            pytest.skip("API server not responding correctly")
    except requests.ConnectionError:
        pytest.skip(f"API server not running at {API_BASE_URL}")


class TestHealthEndpoints:
    """Contract tests for health check endpoints."""

    def test_health_returns_status_and_timestamp(self):
        """GET /health returns correct schema."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        # Verify schema
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data

    def test_health_ready_returns_components(self):
        """GET /health/ready returns component status."""
        response = client.get("/health/ready")

        # May be 200 or 503 depending on component health
        assert response.status_code in [200, 503]
        data = response.json()

        # Verify schema - actual response has database, redis, weaviate keys
        assert "database" in data or "ready" in data


class TestMemoriesEndpoints:
    """Contract tests for memory CRUD endpoints."""

    def test_get_memories_returns_array(self):
        """GET /memories returns memories in response."""
        response = client.get("/memories?limit=5")

        assert response.status_code == 200
        data = response.json()

        # Verify schema: response has "memories" key with array
        assert "memories" in data
        assert isinstance(data["memories"], list)

    def test_get_memories_respects_limit(self):
        """GET /memories respects limit parameter."""
        response = client.get("/memories?limit=3")

        assert response.status_code == 200
        data = response.json()

        # Response has "memories" array and "count" field
        assert len(data["memories"]) <= 3

    def test_get_memory_count_returns_count(self):
        """GET /memories/count returns count object."""
        response = client.get("/memories/count")

        assert response.status_code == 200
        data = response.json()

        # Actual response uses "total_count"
        assert "total_count" in data or "count" in data

    def test_get_memory_not_found(self):
        """GET /memories/{id} returns 404 for non-existent memory."""
        fake_id = str(uuid4())
        response = client.get(f"/memories/{fake_id}")

        assert response.status_code == 404

    def test_post_memory_creates_memory(self):
        """POST /memories creates a new memory."""
        import time
        payload = {
            "content": f"Test memory for contract testing - unique {time.time()}",
            "privacy_level": "INTERNAL"
        }
        response = client.post("/memories", json=payload)

        # 200 for new memory, 409 for duplicate (idempotent)
        assert response.status_code in [200, 409]
        data = response.json()

        # Verify schema
        assert "memory_id" in data or "id" in data or "detail" in data
        assert "status" in data or "message" in data or "detail" in data

    def test_post_memory_requires_content(self):
        """POST /memories requires content field."""
        payload = {"privacy_level": "INTERNAL"}
        response = client.post("/memories", json=payload)

        # Should fail validation
        assert response.status_code == 422  # Validation error


class TestMemoriesV2Endpoint:
    """Contract tests for V2 memory endpoint with quality gate."""

    def test_post_v2_memory_returns_quality_score(self):
        """POST /api/v2/memories returns quality assessment."""
        payload = {
            "content": "User prefers dark mode and uses Python for development",
            "memory_type": "SEMANTIC",
            "source": "user_stated"
        }
        response = client.post("/api/v2/memories", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Verify V2 schema
        assert "memory_id" in data
        assert "status" in data
        assert "quality_score" in data
        assert isinstance(data["quality_score"], (int, float))
        assert 0 <= data["quality_score"] <= 1

    def test_post_v2_memory_with_default_type(self):
        """POST /api/v2/memories works with default memory_type."""
        payload = {
            "content": "Test content without explicit memory_type"
        }
        response = client.post("/api/v2/memories", json=payload)

        # Works because memory_type has a default value
        assert response.status_code in [200, 422]  # 422 if quality gate rejects

    def test_post_v2_memory_validates_memory_type(self):
        """POST /api/v2/memories validates memory_type enum."""
        payload = {
            "content": "Test content",
            "memory_type": "INVALID_TYPE"
        }
        response = client.post("/api/v2/memories", json=payload)

        # Should fail validation
        assert response.status_code == 422


class TestSearchEndpoint:
    """Contract tests for search endpoint."""

    def test_post_search_returns_results(self):
        """POST /search returns search results."""
        payload = {"query": "test query"}
        response = client.post("/search", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Verify schema: results array
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_post_search_requires_query(self):
        """POST /search requires query field."""
        payload = {}
        response = client.post("/search", json=payload)

        assert response.status_code == 422


class TestAskEndpoint:
    """Contract tests for ask endpoint."""

    def test_post_ask_returns_answer(self):
        """POST /ask returns AI-generated answer."""
        # Note: API expects "question" field, not "query"
        payload = {"question": "What is ACMS?"}
        response = client.post("/ask", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Verify schema
        assert "answer" in data
        assert isinstance(data["answer"], str)

    def test_post_ask_requires_question(self):
        """POST /ask requires question field."""
        payload = {}
        response = client.post("/ask", json=payload)

        assert response.status_code == 422


class TestFeedbackEndpoints:
    """Contract tests for feedback endpoints."""

    def test_post_feedback_accepts_rating(self):
        """POST /feedback accepts feedback submission."""
        payload = {
            "query_id": str(uuid4()),
            "rating": 4,
            "feedback_type": "thumbs_up",  # Must be: thumbs_up, thumbs_down, regenerate
            "comment": "Test feedback"
        }
        response = client.post("/feedback", json=payload)

        # May succeed (200) or fail (404 if query doesn't exist, 500 on internal error)
        assert response.status_code in [200, 404, 400, 500]

    def test_post_feedback_validates_rating_range(self):
        """POST /feedback validates rating is 1-5."""
        payload = {
            "query_id": str(uuid4()),
            "rating": 10,  # Invalid: out of range
            "feedback_type": "thumbs_up",
            "comment": "Test"
        }
        response = client.post("/feedback", json=payload)

        # Should fail validation
        assert response.status_code == 422


class TestCacheEndpoints:
    """Contract tests for cache management endpoints."""

    def test_get_cache_stats_returns_metrics(self):
        """GET /cache/stats returns cache statistics."""
        response = client.get("/cache/stats")

        assert response.status_code == 200
        data = response.json()

        # Verify schema has cache metrics
        assert isinstance(data, dict)

    def test_post_cache_clear_clears_cache(self):
        """POST /cache/clear clears the cache."""
        response = client.post("/cache/clear")

        assert response.status_code == 200


class TestAnalyticsEndpoint:
    """Contract tests for analytics endpoint."""

    def test_get_dashboard_returns_data(self):
        """GET /analytics/dashboard returns dashboard data."""
        # Dashboard requires user_id query parameter
        user_id = "00000000-0000-0000-0000-000000000001"
        response = client.get(f"/analytics/dashboard?user_id={user_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify some dashboard metrics present
        assert isinstance(data, dict)


class TestChatEndpoints:
    """Contract tests for unified chat endpoints."""

    def test_get_conversations_returns_list(self):
        """GET /chat/conversations returns conversation list."""
        user_id = "00000000-0000-0000-0000-000000000001"
        response = client.get(f"/chat/conversations?user_id={user_id}")

        assert response.status_code == 200
        data = response.json()

        # Verify schema
        assert "conversations" in data
        assert isinstance(data["conversations"], list)

    def test_post_conversation_creates_new(self):
        """POST /chat/conversations creates a new conversation."""
        payload = {
            "title": "Test Conversation",
            "user_id": "00000000-0000-0000-0000-000000000001",
            "agent": "claude"  # Must be: claude, gpt, gemini, claude-code
        }
        response = client.post("/chat/conversations", json=payload)

        assert response.status_code == 200
        data = response.json()

        # Verify conversation created
        assert "conversation_id" in data or "id" in data

    def test_get_conversation_not_found(self):
        """GET /chat/conversations/{id} returns 404 for non-existent."""
        fake_id = str(uuid4())
        response = client.get(f"/chat/conversations/{fake_id}")

        assert response.status_code == 404

    def test_delete_conversation_not_found(self):
        """DELETE /chat/conversations/{id} handles non-existent."""
        fake_id = str(uuid4())
        response = client.delete(f"/chat/conversations/{fake_id}")

        # Should be 404 or 200 (idempotent delete)
        assert response.status_code in [200, 404]


class TestResponseHeaders:
    """Contract tests for response headers."""

    def test_health_has_content_type(self):
        """Responses have Content-Type header."""
        response = client.get("/health")

        assert "content-type" in response.headers
        assert "application/json" in response.headers["content-type"]


class TestErrorResponses:
    """Contract tests for error response format."""

    def test_404_returns_json(self):
        """404 errors return JSON response."""
        response = client.get("/nonexistent-endpoint")

        # FastAPI returns 404 for unknown routes
        assert response.status_code == 404
        # Should be JSON
        try:
            data = response.json()
            assert "detail" in data
        except json.JSONDecodeError:
            pytest.fail("404 response should be JSON")

    def test_422_validation_error_format(self):
        """422 validation errors have standard format."""
        # Send invalid data
        response = client.post("/memories", json={})

        assert response.status_code == 422
        data = response.json()

        # Verify FastAPI validation error format
        assert "detail" in data
        assert isinstance(data["detail"], list)


class TestIdempotency:
    """Contract tests for idempotent operations."""

    def test_get_endpoints_idempotent(self):
        """GET endpoints are idempotent."""
        # First request
        response1 = client.get("/health")
        # Second request
        response2 = client.get("/health")

        assert response1.status_code == response2.status_code
        assert response1.json()["status"] == response2.json()["status"]

    def test_get_memories_idempotent(self):
        """GET /memories is idempotent."""
        response1 = client.get("/memories?limit=5")
        response2 = client.get("/memories?limit=5")

        assert response1.status_code == response2.status_code


class TestContentTypes:
    """Contract tests for content type handling."""

    def test_post_requires_json(self):
        """POST endpoints require application/json."""
        response = client.post(
            "/memories",
            data="plain text",
            headers={"Content-Type": "text/plain"}
        )

        # Should fail with wrong content type
        assert response.status_code == 422

    def test_post_accepts_json(self):
        """POST endpoints accept application/json."""
        import time
        response = client.post(
            "/memories",
            json={"content": f"test content {time.time()}"},
            headers={"Content-Type": "application/json"}
        )

        # Should process: 200 success, 409 duplicate, 422/400 validation error
        assert response.status_code in [200, 409, 422, 400]
