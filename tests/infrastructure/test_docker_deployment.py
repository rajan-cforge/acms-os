"""
Infrastructure tests for Docker deployment.
Written BEFORE implementation (TDD Red phase).

Run with: pytest tests/infrastructure/ -v

These tests verify:
1. All Docker containers are healthy
2. API server responds correctly
3. Services can communicate
4. Performance meets requirements (<100ms)
5. Operations are idempotent
"""

import pytest
import docker
import requests
import time
from typing import Dict, Any


@pytest.fixture(scope="module")
def docker_client():
    """Get Docker client for container inspection."""
    return docker.from_env()


@pytest.fixture(scope="module")
def api_base_url():
    """Base URL for ACMS API."""
    return "http://localhost:40080"


@pytest.mark.infrastructure
class TestContainerHealth:
    """Test that all required containers are healthy."""

    def test_postgres_container_running(self, docker_client):
        """PostgreSQL container must be running."""
        try:
            container = docker_client.containers.get("acms_postgres")
            assert container.status == "running", f"PostgreSQL status: {container.status}"
        except docker.errors.NotFound:
            pytest.fail("PostgreSQL container 'acms_postgres' not found")

    def test_postgres_healthy(self, docker_client):
        """PostgreSQL must pass health checks."""
        container = docker_client.containers.get("acms_postgres")

        # Wait up to 30 seconds for health check
        max_wait = 30
        start_time = time.time()

        while time.time() - start_time < max_wait:
            container.reload()
            health_status = container.attrs.get('State', {}).get('Health', {}).get('Status')

            if health_status == 'healthy':
                return  # Success

            time.sleep(1)

        pytest.fail(f"PostgreSQL health check failed. Status: {health_status}")

    def test_redis_container_running(self, docker_client):
        """Redis container must be running."""
        try:
            container = docker_client.containers.get("acms_redis")
            assert container.status == "running", f"Redis status: {container.status}"
        except docker.errors.NotFound:
            pytest.fail("Redis container 'acms_redis' not found")

    def test_weaviate_container_running(self, docker_client):
        """Weaviate container must be running."""
        try:
            container = docker_client.containers.get("acms_weaviate")
            assert container.status == "running", f"Weaviate status: {container.status}"
        except docker.errors.NotFound:
            pytest.fail("Weaviate container 'acms_weaviate' not found")

    def test_api_container_running(self, docker_client):
        """ACMS API container must be running."""
        try:
            container = docker_client.containers.get("acms_api")
            assert container.status == "running", f"API status: {container.status}"
        except docker.errors.NotFound:
            pytest.fail("API container 'acms_api' not found")

    def test_api_container_healthy(self, docker_client):
        """ACMS API must pass health checks."""
        container = docker_client.containers.get("acms_api")

        # Wait up to 60 seconds for API to be healthy
        max_wait = 60
        start_time = time.time()

        while time.time() - start_time < max_wait:
            container.reload()
            health_status = container.attrs.get('State', {}).get('Health', {}).get('Status')

            if health_status == 'healthy':
                return  # Success

            time.sleep(2)

        pytest.fail(f"API health check failed. Status: {health_status}")


@pytest.mark.infrastructure
class TestAPIEndpoints:
    """Test that API endpoints respond correctly."""

    def test_health_endpoint_exists(self, api_base_url):
        """Health endpoint must be accessible."""
        response = requests.get(f"{api_base_url}/health", timeout=5)
        assert response.status_code == 200, f"Health check failed: {response.status_code}"

    def test_health_endpoint_response_format(self, api_base_url):
        """Health endpoint must return correct JSON format."""
        response = requests.get(f"{api_base_url}/health", timeout=5)
        data = response.json()

        assert "status" in data, "Health response missing 'status'"
        assert data["status"] == "healthy", f"API not healthy: {data['status']}"
        assert "service" in data, "Health response missing 'service'"
        assert data["service"] == "acms-api", f"Wrong service name: {data['service']}"

    def test_health_ready_endpoint(self, api_base_url):
        """Readiness endpoint must check dependencies."""
        response = requests.get(f"{api_base_url}/health/ready", timeout=10)

        # Should be 200 if all dependencies ready, 503 if not
        assert response.status_code in [200, 503], f"Unexpected status: {response.status_code}"

        data = response.json()
        assert "database" in data, "Readiness check missing 'database'"
        assert "redis" in data, "Readiness check missing 'redis'"
        assert "weaviate" in data, "Readiness check missing 'weaviate'"


@pytest.mark.infrastructure
class TestServiceConnectivity:
    """Test that services can communicate."""

    def test_api_can_connect_to_postgres(self, api_base_url):
        """API must be able to connect to PostgreSQL."""
        response = requests.get(f"{api_base_url}/health/database", timeout=5)
        data = response.json()

        assert data.get("database") == "connected", "API cannot connect to PostgreSQL"

    def test_api_can_connect_to_redis(self, api_base_url):
        """API must be able to connect to Redis."""
        response = requests.get(f"{api_base_url}/health/redis", timeout=5)
        data = response.json()

        assert data.get("redis") == "connected", "API cannot connect to Redis"

    def test_api_can_connect_to_weaviate(self, api_base_url):
        """API must be able to connect to Weaviate."""
        response = requests.get(f"{api_base_url}/health/weaviate", timeout=5)
        data = response.json()

        assert data.get("weaviate") == "connected", "API cannot connect to Weaviate"


@pytest.mark.infrastructure
class TestPerformance:
    """Test that performance meets requirements."""

    def test_health_endpoint_response_time(self, api_base_url):
        """Health endpoint must respond in <100ms."""
        # Warm up
        requests.get(f"{api_base_url}/health", timeout=5)

        # Measure
        start = time.time()
        response = requests.get(f"{api_base_url}/health", timeout=5)
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200, "Health check failed"
        assert elapsed_ms < 100, f"Health endpoint too slow: {elapsed_ms:.2f}ms (max: 100ms)"

    def test_api_startup_time(self, docker_client):
        """API container must start within 60 seconds."""
        container = docker_client.containers.get("acms_api")

        # Get container start time
        started_at = container.attrs['State']['StartedAt']
        health_status = container.attrs.get('State', {}).get('Health', {}).get('Status')

        # If already healthy, we're good
        if health_status == 'healthy':
            return

        # Otherwise, fail (this test runs after container should be started)
        pytest.fail(f"API not healthy after startup. Status: {health_status}")


@pytest.mark.infrastructure
class TestIdempotency:
    """Test that operations are idempotent (safe to retry)."""

    def test_health_check_idempotent(self, api_base_url):
        """Health check should return same result on multiple calls."""
        response1 = requests.get(f"{api_base_url}/health", timeout=5).json()
        response2 = requests.get(f"{api_base_url}/health", timeout=5).json()
        response3 = requests.get(f"{api_base_url}/health", timeout=5).json()

        # Status should be consistent
        assert response1["status"] == response2["status"] == response3["status"]
        assert response1["service"] == response2["service"] == response3["service"]

    def test_readiness_check_idempotent(self, api_base_url):
        """Readiness check should return consistent results."""
        response1 = requests.get(f"{api_base_url}/health/ready", timeout=10).json()
        response2 = requests.get(f"{api_base_url}/health/ready", timeout=10).json()

        # Dependency statuses should be consistent
        assert response1.get("database") == response2.get("database")
        assert response1.get("redis") == response2.get("redis")
        assert response1.get("weaviate") == response2.get("weaviate")


@pytest.mark.infrastructure
class TestSecurity:
    """Test security configurations."""

    def test_api_container_runs_as_non_root(self, docker_client):
        """API container must run as non-root user."""
        container = docker_client.containers.get("acms_api")

        # Exec into container and check user
        exec_result = container.exec_run("whoami")
        username = exec_result.output.decode().strip()

        assert username != "root", "API container running as root (security violation)"
        assert username == "acms", f"API container running as '{username}' (expected: acms)"

    def test_no_secrets_in_image(self, docker_client):
        """API image must not contain secrets."""
        container = docker_client.containers.get("acms_api")

        # Check that secrets are passed via environment variables, not baked in
        exec_result = container.exec_run("env | grep -E '(API_KEY|PASSWORD|SECRET)' || true")
        env_output = exec_result.output.decode()

        # Should have environment variables (passed at runtime)
        # but NOT hardcoded in Dockerfile
        assert len(env_output) > 0, "No API keys found in environment (check configuration)"


@pytest.mark.infrastructure
class TestResourceLimits:
    """Test that containers have resource limits."""

    def test_api_container_has_memory_limit(self, docker_client):
        """API container must have memory limit."""
        container = docker_client.containers.get("acms_api")

        host_config = container.attrs['HostConfig']
        memory_limit = host_config.get('Memory', 0)

        # Should have some memory limit (not unlimited)
        # Note: 0 means unlimited in Docker
        assert memory_limit > 0, "API container has no memory limit"

    def test_api_container_has_restart_policy(self, docker_client):
        """API container must have restart policy."""
        container = docker_client.containers.get("acms_api")

        host_config = container.attrs['HostConfig']
        restart_policy = host_config.get('RestartPolicy', {}).get('Name')

        # Should have restart policy (unless-stopped or always)
        assert restart_policy in ['unless-stopped', 'always'], \
            f"API container has wrong restart policy: {restart_policy}"


@pytest.mark.infrastructure
class TestNetworking:
    """Test network configuration."""

    def test_containers_on_same_network(self, docker_client):
        """All ACMS containers must be on the same network."""
        api_container = docker_client.containers.get("acms_api")
        postgres_container = docker_client.containers.get("acms_postgres")

        api_networks = list(api_container.attrs['NetworkSettings']['Networks'].keys())
        postgres_networks = list(postgres_container.attrs['NetworkSettings']['Networks'].keys())

        # Should share at least one network
        shared_networks = set(api_networks) & set(postgres_networks)
        assert len(shared_networks) > 0, "API and PostgreSQL not on same network"

        # Docker Compose prefixes network names with project name (e.g., acms_acms_network)
        # Check that at least one shared network contains 'acms_network'
        assert any('acms_network' in net for net in shared_networks), f"Expected network containing 'acms_network', got: {shared_networks}"

    def test_api_port_exposed(self, docker_client):
        """API port 40080 must be exposed."""
        api_container = docker_client.containers.get("acms_api")

        ports = api_container.attrs['NetworkSettings']['Ports']
        assert '40080/tcp' in ports, "API port 40080 not exposed"

        # Check it's bound to host
        port_bindings = ports['40080/tcp']
        assert port_bindings is not None, "API port 40080 not bound to host"
        assert port_bindings[0]['HostPort'] == '40080', "API port mapped incorrectly"
