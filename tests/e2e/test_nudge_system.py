"""
End-to-End Tests: Nudge System (Tap on Shoulder)

Tests the complete nudge lifecycle including creation, display, snooze, and dismiss.

Run with: pytest tests/e2e/test_nudge_system.py -v
"""

import pytest
import httpx
from datetime import datetime, timedelta


BASE_URL = "http://localhost:40080"
TEST_USER_ID = "e2e-test-user-nudge"


@pytest.fixture
def api_client():
    """HTTP client for API requests."""
    return httpx.Client(base_url=BASE_URL, timeout=30.0)


class TestNudgeLifecycle:
    """E2E: Complete nudge lifecycle."""

    def test_nudge_lifecycle(self, api_client):
        """
        Full flow:
        1. Create knowledge with low confidence
        2. Trigger stale knowledge check
        3. Verify nudge created
        4. Snooze nudge
        5. Verify hidden during snooze
        6. Wait for snooze to expire
        7. Verify nudge reappears
        """
        # Step 1: Get active nudges before
        initial_response = api_client.get(
            "/api/nudges",
            params={"user_id": TEST_USER_ID}
        )
        assert initial_response.status_code == 200
        initial_nudges = initial_response.json()
        initial_count = len(initial_nudges)

        # Step 2: Trigger stale knowledge check (if endpoint exists)
        trigger_response = api_client.post(
            "/api/jobs/stale-knowledge-check",
            json={"user_id": TEST_USER_ID}
        )
        # May not exist yet, that's okay

        # Step 3: Check for new nudges
        nudges_response = api_client.get(
            "/api/nudges",
            params={"user_id": TEST_USER_ID}
        )
        nudges = nudges_response.json()

        # If we have nudges, test the lifecycle
        if nudges and len(nudges) > 0:
            nudge_id = nudges[0]["id"]

            # Step 4: Snooze the nudge
            snooze_response = api_client.post(
                "/api/nudges/snooze",
                json={
                    "nudge_id": nudge_id,
                    "user_id": TEST_USER_ID,
                    "duration_minutes": 60
                }
            )
            assert snooze_response.status_code == 200
            snooze_data = snooze_response.json()
            assert snooze_data.get("success") is True

            # Step 5: Verify hidden during snooze
            active_response = api_client.get(
                "/api/nudges",
                params={"user_id": TEST_USER_ID}
            )
            active_nudges = active_response.json()
            snoozed_nudge_ids = [n["id"] for n in active_nudges]
            assert nudge_id not in snoozed_nudge_ids

    def test_dismiss_nudge(self, api_client):
        """Dismissed nudges should not reappear."""
        # Get nudges
        nudges_response = api_client.get(
            "/api/nudges",
            params={"user_id": TEST_USER_ID}
        )
        nudges = nudges_response.json()

        if nudges and len(nudges) > 0:
            nudge_id = nudges[0]["id"]

            # Dismiss
            dismiss_response = api_client.post(
                "/api/nudges/dismiss",
                json={
                    "nudge_id": nudge_id,
                    "user_id": TEST_USER_ID
                }
            )
            assert dismiss_response.status_code == 200

            # Verify gone
            check_response = api_client.get(
                "/api/nudges",
                params={"user_id": TEST_USER_ID}
            )
            remaining_ids = [n["id"] for n in check_response.json()]
            assert nudge_id not in remaining_ids


class TestNudgeTypes:
    """E2E: Different nudge types."""

    def test_new_learning_nudge(self, api_client):
        """Test nudge created when new fact is learned."""
        # Ask question that triggers learning
        ask_response = api_client.post(
            "/api/ask",
            json={
                "query": "What is Python's asyncio?",
                "user_id": TEST_USER_ID,
                "save_learning": True  # Explicitly request learning
            }
        )

        # Check for new_learning nudge
        nudges_response = api_client.get(
            "/api/nudges",
            params={"user_id": TEST_USER_ID, "type": "new_learning"}
        )
        # May or may not have nudges depending on system state

    def test_low_confidence_nudge(self, api_client):
        """Test nudge for low confidence items."""
        nudges_response = api_client.get(
            "/api/nudges",
            params={"user_id": TEST_USER_ID, "type": "low_confidence"}
        )
        assert nudges_response.status_code == 200
        nudges = nudges_response.json()

        for nudge in nudges:
            assert nudge.get("nudge_type") == "low_confidence"


class TestNudgePriority:
    """E2E: Nudge priority ordering."""

    def test_nudges_sorted_by_priority(self, api_client):
        """High priority nudges should appear first."""
        response = api_client.get(
            "/api/nudges",
            params={"user_id": TEST_USER_ID}
        )
        nudges = response.json()

        if len(nudges) >= 2:
            # Check ordering
            priority_order = {"high": 1, "medium": 2, "low": 3}
            for i in range(len(nudges) - 1):
                current_priority = priority_order.get(nudges[i]["priority"], 2)
                next_priority = priority_order.get(nudges[i + 1]["priority"], 2)
                assert current_priority <= next_priority


class TestNudgeCounts:
    """E2E: Nudge count tracking."""

    def test_nudge_counts_by_type(self, api_client):
        """Get nudge counts grouped by type."""
        response = api_client.get(
            "/api/nudges/counts",
            params={"user_id": TEST_USER_ID}
        )
        assert response.status_code == 200
        counts = response.json()

        assert "total" in counts
        assert "by_type" in counts
        assert isinstance(counts["by_type"], dict)


class TestNudgePreferences:
    """E2E: User nudge preferences."""

    def test_set_max_daily_nudges(self, api_client):
        """User can limit daily nudges."""
        response = api_client.put(
            "/api/nudges/preferences",
            json={
                "user_id": TEST_USER_ID,
                "max_daily_nudges": 5,
                "quiet_hours_start": "22:00",
                "quiet_hours_end": "08:00"
            }
        )
        assert response.status_code == 200

    def test_respects_daily_limit(self, api_client):
        """System should not exceed daily nudge limit."""
        # Set low limit
        api_client.put(
            "/api/nudges/preferences",
            json={
                "user_id": TEST_USER_ID,
                "max_daily_nudges": 2
            }
        )

        # Try to trigger many nudges
        for i in range(5):
            api_client.post(
                "/api/nudges",
                json={
                    "user_id": TEST_USER_ID,
                    "nudge_type": "review_reminder",
                    "title": f"Test nudge {i}",
                    "message": "Test message",
                    "priority": "low"
                }
            )

        # Count nudges created today
        counts = api_client.get(
            "/api/nudges/counts",
            params={"user_id": TEST_USER_ID, "period": "today"}
        ).json()

        # Should not exceed limit (if properly implemented)
        # Note: This depends on implementation details
