"""
CORS Configuration Tests - Phase 0, Task 0.2

Tests that CORS is properly configured to:
1. Allow requests from Electron desktop app (file:// protocol)
2. Allow requests from localhost:8080 (future web interface)
3. BLOCK requests from all other origins (security)

Following TDD: These tests will FAIL initially, then we fix the code.
"""

import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.api_server import app


class TestCORSConfiguration:
    """Test CORS security configuration"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_cors_allows_electron_app(self, client):
        """
        Test that Electron desktop app can access API.

        Electron apps using file:// protocol send Origin: null
        """
        response = client.get(
            "/health",
            headers={"Origin": "null"}
        )

        # Should allow null origin (Electron file:// protocol)
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        # For null origin, server should echo back "null" or "*"
        allowed_origin = response.headers.get("access-control-allow-origin")
        assert allowed_origin in ["null", "*"], \
            f"Expected null or * for Electron app, got: {allowed_origin}"

    def test_cors_allows_localhost_8080(self, client):
        """
        Test that localhost:8080 can access API.

        This is for future web interface development.
        """
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:8080"}
        )

        # Should allow localhost:8080
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        allowed_origin = response.headers.get("access-control-allow-origin")
        assert allowed_origin in ["http://localhost:8080", "*"], \
            f"Expected http://localhost:8080 or *, got: {allowed_origin}"

    def test_cors_allows_localhost_3000(self, client):
        """
        Test that localhost:3000 can access API.

        Common dev server port for React/Next.js if we add web UI.
        """
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )

        # Should allow localhost:3000 for development
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        allowed_origin = response.headers.get("access-control-allow-origin")
        assert allowed_origin in ["http://localhost:3000", "*"], \
            f"Expected http://localhost:3000 or *, got: {allowed_origin}"

    def test_cors_blocks_external_origin(self, client):
        """
        CRITICAL SECURITY TEST

        Test that external origins (e.g., evil.com) CANNOT access API.
        This prevents CSRF attacks and unauthorized access.
        """
        response = client.get(
            "/health",
            headers={"Origin": "https://evil.com"}
        )

        # Response should still be 200 (health check works)
        assert response.status_code == 200

        # BUT: CORS header should NOT allow evil.com
        allowed_origin = response.headers.get("access-control-allow-origin")

        # CRITICAL: Must NOT be "*" (wildcard) or "https://evil.com"
        assert allowed_origin != "https://evil.com", \
            "SECURITY VIOLATION: evil.com should be blocked!"

        # If wildcard is used, this test should FAIL (that's the point - we need to fix it)
        assert allowed_origin != "*", \
            "SECURITY VIOLATION: Wildcard CORS allows ANY origin including evil.com!"

    def test_cors_blocks_other_localhost_ports(self, client):
        """
        Test that random localhost ports are blocked.

        Only specific ports (8080, 3000) should be allowed.
        """
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:9999"}
        )

        # Response should still be 200
        assert response.status_code == 200

        # BUT: CORS header should NOT allow port 9999
        allowed_origin = response.headers.get("access-control-allow-origin")

        # Should NOT be the random port or wildcard
        assert allowed_origin != "http://localhost:9999", \
            "Random localhost port should be blocked!"

        assert allowed_origin != "*", \
            "Wildcard CORS allows ANY port including unauthorized ones!"

    def test_cors_preflight_request(self, client):
        """
        Test CORS preflight (OPTIONS) request.

        Browsers send OPTIONS before POST/PUT/DELETE requests.
        """
        response = client.options(
            "/ask",
            headers={
                "Origin": "http://localhost:8080",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type"
            }
        )

        # Preflight should be allowed
        assert response.status_code in [200, 204]

        # Should include CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
        assert "access-control-allow-headers" in response.headers

        # Should allow POST method
        allowed_methods = response.headers.get("access-control-allow-methods", "")
        assert "POST" in allowed_methods

    def test_cors_credentials_allowed(self, client):
        """
        Test that credentials (cookies, auth headers) are allowed.

        Important for future authentication system.
        """
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:8080"}
        )

        # Should allow credentials
        assert "access-control-allow-credentials" in response.headers
        assert response.headers.get("access-control-allow-credentials") == "true"

    def test_environment_based_cors_development(self, client, monkeypatch):
        """
        Test that CORS is relaxed in development environment.

        In dev, we might want to allow more origins for testing.
        """
        # Set environment to development
        monkeypatch.setenv("ENVIRONMENT", "development")

        # In development, localhost origins should be allowed
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:8080"}
        )

        assert response.status_code == 200
        allowed_origin = response.headers.get("access-control-allow-origin")
        assert "localhost" in allowed_origin or allowed_origin == "*"

    def test_environment_based_cors_production(self, client, monkeypatch):
        """
        Test that CORS is strict in production environment.

        In production, ONLY specific origins should be allowed.
        """
        # Set environment to production
        monkeypatch.setenv("ENVIRONMENT", "production")

        # In production, evil.com should be blocked
        response = client.get(
            "/health",
            headers={"Origin": "https://evil.com"}
        )

        assert response.status_code == 200
        allowed_origin = response.headers.get("access-control-allow-origin")

        # MUST NOT allow wildcard or evil.com in production
        assert allowed_origin != "*", "Production MUST NOT use wildcard CORS!"
        assert allowed_origin != "https://evil.com", "Production MUST block evil.com!"


class TestCORSSecurityScenarios:
    """Test real-world attack scenarios"""

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_csrf_attack_blocked(self, client):
        """
        Test that CSRF attack from malicious site is blocked.

        Scenario: User visits evil.com, which tries to call ACMS API
        with user's cookies/credentials.
        """
        # Evil site tries to store memory
        response = client.post(
            "/memories",
            json={
                "content": "Stolen data from evil.com",
                "metadata": {"source": "evil"}
            },
            headers={"Origin": "https://evil.com"}
        )

        # Request might succeed (API works)
        # BUT: Browser would block response due to CORS
        allowed_origin = response.headers.get("access-control-allow-origin")

        assert allowed_origin != "https://evil.com", \
            "SECURITY VIOLATION: Evil site should not get CORS access!"
        assert allowed_origin != "*", \
            "SECURITY VIOLATION: Wildcard allows evil.com to access API!"

    def test_subdomain_blocked(self, client):
        """
        Test that subdomains are explicitly checked.

        Evil.localhost.com should NOT be allowed even though it contains "localhost".
        """
        response = client.get(
            "/health",
            headers={"Origin": "http://evil.localhost.com"}
        )

        assert response.status_code == 200
        allowed_origin = response.headers.get("access-control-allow-origin")

        # Should NOT allow subdomain
        assert allowed_origin != "http://evil.localhost.com", \
            "Subdomain should be blocked!"
        assert allowed_origin != "*", \
            "Wildcard allows subdomains!"

    def test_port_manipulation_blocked(self, client):
        """
        Test that port manipulation is blocked.

        localhost:8080 is allowed, but localhost:8081 should be blocked.
        """
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:8081"}
        )

        assert response.status_code == 200
        allowed_origin = response.headers.get("access-control-allow-origin")

        # Should NOT allow different port
        assert allowed_origin != "http://localhost:8081", \
            "Different port should be blocked!"
        assert allowed_origin != "*", \
            "Wildcard allows any port!"


class TestCORSDocumentation:
    """Tests that document CORS behavior for future developers"""

    def test_cors_allows_electron_documentation(self):
        """
        DOCUMENTATION: Why we allow Origin: null

        Electron apps using file:// protocol send "Origin: null"
        We MUST allow this for desktop app to work.

        This is safe because:
        1. Desktop app runs on user's machine (trusted)
        2. File:// has no network access (can't be attacked)
        3. Electron has nodeIntegration enabled (already trusted)
        """
        assert True, "See docstring for explanation"

    def test_cors_blocks_wildcard_documentation(self):
        """
        DOCUMENTATION: Why wildcard CORS is dangerous

        allow_origins=["*"] means ANY website can call our API:
        - evil.com can steal user data
        - evil.com can modify memories
        - evil.com can exhaust API quota
        - evil.com can perform CSRF attacks

        NEVER use wildcard in production!
        """
        assert True, "See docstring for explanation"

    def test_cors_localhost_ports_documentation(self):
        """
        DOCUMENTATION: Why we allow specific localhost ports

        - 8080: Desktop app API (already running here)
        - 3000: Common dev server port (React, Next.js, Vite)
        - null: Electron file:// protocol

        Other ports are blocked to prevent:
        - Malicious local services (malware, dev tools gone rogue)
        - Port scanning attacks
        - Unauthorized third-party apps
        """
        assert True, "See docstring for explanation"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
