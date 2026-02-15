"""
E2E Test Configuration and Shared Fixtures

Sets up the test environment for end-to-end testing.
"""

import pytest
import httpx
import os
from pathlib import Path


# Configuration
BASE_URL = os.environ.get("ACMS_API_URL", "http://localhost:40080")
TIMEOUT = float(os.environ.get("ACMS_TEST_TIMEOUT", "30.0"))


def pytest_configure(config):
    """Configure pytest for E2E testing."""
    config.addinivalue_line(
        "markers", "e2e: End-to-end test that requires running services"
    )
    config.addinivalue_line(
        "markers", "slow: Test that takes a long time to run"
    )


@pytest.fixture(scope="session")
def api_base_url():
    """Base URL for API requests."""
    return BASE_URL


@pytest.fixture(scope="session")
def sync_client():
    """Session-scoped synchronous HTTP client."""
    with httpx.Client(base_url=BASE_URL, timeout=TIMEOUT) as client:
        yield client


@pytest.fixture
def api_client():
    """Test-scoped synchronous HTTP client."""
    return httpx.Client(base_url=BASE_URL, timeout=TIMEOUT)


@pytest.fixture
async def async_client():
    """Test-scoped async HTTP client."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        yield client


@pytest.fixture(scope="session")
def test_user_id():
    """Generate unique test user ID for isolation."""
    import uuid
    return f"e2e-test-{uuid.uuid4().hex[:8]}"


@pytest.fixture
def unique_query():
    """Generate unique query string for test isolation."""
    import uuid
    return f"Test query {uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="session", autouse=True)
def verify_services_running(sync_client):
    """Verify required services are running before tests."""
    try:
        response = sync_client.get("/health")
        assert response.status_code == 200, "API server not healthy"
    except httpx.ConnectError:
        pytest.skip(
            f"Cannot connect to API at {BASE_URL}. "
            "Ensure docker-compose is running: `docker-compose up -d`"
        )


@pytest.fixture
def create_test_knowledge(api_client, test_user_id):
    """Factory fixture to create test knowledge items."""
    created_ids = []

    def _create(content: str, confidence: float = 0.7):
        response = api_client.post(
            "/api/knowledge",
            json={
                "content": content,
                "user_id": test_user_id,
                "confidence": confidence,
                "source": "e2e_test"
            }
        )
        if response.status_code == 200:
            knowledge_id = response.json().get("id")
            created_ids.append(knowledge_id)
            return knowledge_id
        return None

    yield _create

    # Cleanup
    for kid in created_ids:
        api_client.delete(f"/api/knowledge/{kid}")


@pytest.fixture
def create_test_nudge(api_client, test_user_id):
    """Factory fixture to create test nudges."""
    created_ids = []

    def _create(
        nudge_type: str = "review_reminder",
        title: str = "Test nudge",
        priority: str = "medium"
    ):
        response = api_client.post(
            "/api/nudges",
            json={
                "user_id": test_user_id,
                "nudge_type": nudge_type,
                "title": title,
                "message": "Test nudge message",
                "priority": priority
            }
        )
        if response.status_code == 200:
            nudge_id = response.json().get("id")
            created_ids.append(nudge_id)
            return nudge_id
        return None

    yield _create

    # Cleanup
    for nid in created_ids:
        api_client.post(
            "/api/nudges/dismiss",
            json={"nudge_id": nid, "user_id": test_user_id}
        )


# Performance tracking fixture
@pytest.fixture
def response_timer():
    """Track response times for performance assertions."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.elapsed = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.elapsed = time.time() - self.start_time
            return self.elapsed

        def assert_under(self, max_seconds: float, message: str = ""):
            assert self.elapsed is not None, "Timer not stopped"
            assert self.elapsed < max_seconds, (
                f"Response took {self.elapsed:.3f}s, expected < {max_seconds}s. {message}"
            )

    return Timer()
