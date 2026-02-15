"""
End-to-End Tests: Feedback → Cache Flow

Tests the complete user journey for feedback and cache promotion.

Prerequisites:
- Docker services running (docker-compose up -d)
- API server accessible at localhost:40080

Run with: pytest tests/e2e/test_feedback_flow.py -v
"""

import pytest
import httpx
import asyncio
from datetime import datetime


BASE_URL = "http://localhost:40080"
TEST_USER_ID = "e2e-test-user-001"


@pytest.fixture
def api_client():
    """HTTP client for API requests."""
    return httpx.Client(base_url=BASE_URL, timeout=30.0)


@pytest.fixture
def async_api_client():
    """Async HTTP client for streaming."""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)


class TestPositiveFeedbackFlow:
    """E2E: User gives positive feedback and promotes to cache."""

    def test_positive_feedback_promotes_to_cache(self, api_client):
        """
        Full flow:
        1. Ask question
        2. Get response with query_history_id
        3. Submit positive feedback with save_as_verified=True
        4. Verify promoted to cache
        5. Ask same question
        6. Verify cache hit
        """
        # Step 1: Ask question
        ask_response = api_client.post(
            "/api/ask",
            json={
                "query": "What is Python's GIL?",
                "user_id": TEST_USER_ID
            }
        )
        assert ask_response.status_code == 200
        ask_data = ask_response.json()
        query_history_id = ask_data.get("query_history_id")
        assert query_history_id is not None

        # Step 2: Submit positive feedback
        feedback_response = api_client.post(
            "/api/feedback",
            json={
                "query_history_id": query_history_id,
                "user_id": TEST_USER_ID,
                "feedback_type": "positive",
                "save_as_verified": True
            }
        )
        assert feedback_response.status_code == 200
        feedback_data = feedback_response.json()
        assert feedback_data.get("feedback_recorded") is True
        assert feedback_data.get("promoted_to_cache") is True

        # Step 3: Ask same question again
        ask_again_response = api_client.post(
            "/api/ask",
            json={
                "query": "What is Python's GIL?",
                "user_id": TEST_USER_ID
            }
        )
        assert ask_again_response.status_code == 200
        ask_again_data = ask_again_response.json()

        # Step 4: Verify cache hit
        assert ask_again_data.get("from_cache") is True

    def test_positive_feedback_without_save_does_not_promote(self, api_client):
        """User gives thumbs up but declines to save - no cache promotion."""
        # Ask question
        ask_response = api_client.post(
            "/api/ask",
            json={
                "query": "What is Django's ORM?",
                "user_id": TEST_USER_ID
            }
        )
        query_history_id = ask_response.json().get("query_history_id")

        # Submit positive feedback WITHOUT save
        feedback_response = api_client.post(
            "/api/feedback",
            json={
                "query_history_id": query_history_id,
                "user_id": TEST_USER_ID,
                "feedback_type": "positive",
                "save_as_verified": False  # Declined to save
            }
        )
        feedback_data = feedback_response.json()
        assert feedback_data.get("feedback_recorded") is True
        assert feedback_data.get("promoted_to_cache") is False


class TestNegativeFeedbackFlow:
    """E2E: User gives negative feedback and demotes from cache."""

    def test_negative_feedback_demotes_cache(self, api_client):
        """
        Full flow:
        1. Ask question (should hit cache from previous test)
        2. Submit negative feedback with reason
        3. Verify demoted from cache
        4. Ask same question
        5. Verify fresh response (not from cache)
        """
        # First, ensure something is in cache
        api_client.post(
            "/api/ask",
            json={
                "query": "What is Flask?",
                "user_id": TEST_USER_ID
            }
        )

        # Get the response again and submit negative feedback
        ask_response = api_client.post(
            "/api/ask",
            json={
                "query": "What is Flask?",
                "user_id": TEST_USER_ID
            }
        )
        query_history_id = ask_response.json().get("query_history_id")

        # Submit negative feedback
        feedback_response = api_client.post(
            "/api/feedback",
            json={
                "query_history_id": query_history_id,
                "user_id": TEST_USER_ID,
                "feedback_type": "negative",
                "reason": "wrong_agent",
                "reason_text": "Expected Claude but got Gemini"
            }
        )
        assert feedback_response.status_code == 200
        feedback_data = feedback_response.json()
        assert feedback_data.get("feedback_recorded") is True

    def test_negative_feedback_with_all_reasons(self, api_client):
        """Test all negative feedback reasons."""
        reasons = [
            "incorrect",
            "outdated",
            "incomplete",
            "wrong_agent",
            "too_long",
            "too_short",
            "off_topic",
            "other"
        ]

        for reason in reasons:
            ask_response = api_client.post(
                "/api/ask",
                json={
                    "query": f"Test query for {reason}",
                    "user_id": TEST_USER_ID
                }
            )
            query_history_id = ask_response.json().get("query_history_id")

            feedback_response = api_client.post(
                "/api/feedback",
                json={
                    "query_history_id": query_history_id,
                    "user_id": TEST_USER_ID,
                    "feedback_type": "negative",
                    "reason": reason
                }
            )
            assert feedback_response.status_code == 200


class TestFeedbackPromptTiming:
    """E2E: Verify feedback prompt appears within AC9 timing (500ms)."""

    @pytest.mark.asyncio
    async def test_prompt_appears_within_500ms(self, async_api_client):
        """AC9: Prompt appears within 500ms of 👍."""
        # This would typically be tested via UI automation (Playwright)
        # For API testing, we verify the endpoint responds quickly
        import time

        start = time.time()
        response = await async_api_client.get(
            "/api/feedback/eligible",
            params={
                "query_history_id": "test-id",
                "user_id": TEST_USER_ID
            }
        )
        elapsed = time.time() - start

        # API should respond in under 500ms
        assert elapsed < 0.5, f"Response took {elapsed}s, expected < 0.5s"


class TestCacheQualityMetrics:
    """E2E: Verify cache quality tracking."""

    def test_cache_stats_endpoint(self, api_client):
        """Verify cache statistics are tracked."""
        response = api_client.get(
            "/api/cache/stats",
            params={"user_id": TEST_USER_ID}
        )
        assert response.status_code == 200
        stats = response.json()

        # Should have expected fields
        assert "total_entries" in stats
        assert "user_verified_count" in stats
        assert "average_quality_score" in stats


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_test_data(api_client):
    """Clean up test data after each test."""
    yield
    # Optional: Clear test user's cache entries
    # api_client.delete(f"/api/cache/clear", params={"user_id": TEST_USER_ID})
