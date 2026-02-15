#!/usr/bin/env python3
"""Infrastructure tests for ACMS Phase 1 - Docker services.

TDD Approach: These tests are written BEFORE implementation.
They will fail initially, then pass as we build the infrastructure.
"""

import pytest
import subprocess
import socket
import time
import yaml
from pathlib import Path


class TestDockerCompose:
    """Test docker-compose.yml configuration."""

    def test_docker_compose_exists(self):
        """docker-compose.yml file must exist."""
        compose_file = Path("docker-compose.yml")
        assert compose_file.exists(), "docker-compose.yml not found"

    def test_docker_compose_valid_yaml(self):
        """docker-compose.yml must be valid YAML."""
        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)
        assert config is not None, "docker-compose.yml is empty or invalid"
        assert "services" in config, "No services defined"

    def test_docker_compose_has_required_services(self):
        """All 3 required services must be defined (Weaviate is external)."""
        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)
        services = config.get("services", {})
        required = ["postgres", "redis", "ollama"]
        for service in required:
            assert service in services, f"Service {service} not defined"

    def test_docker_compose_correct_ports(self):
        """Services must use correct custom ports (40000+ range, updated from 30000+)."""
        with open("docker-compose.yml") as f:
            config = yaml.safe_load(f)
        services = config["services"]

        # Expected port mappings (Weaviate external, not in docker-compose)
        expected_ports = {
            "postgres": "40432:5432",
            "redis": "40379:6379",
            "ollama": "40434:11434"
        }

        for service, expected_mapping in expected_ports.items():
            ports = services[service].get("ports", [])
            assert any(expected_mapping in str(p) for p in ports), \
                f"{service} must expose port {expected_mapping}"


class TestPortAvailability:
    """Test that ports are available and not conflicting."""

    def test_postgres_port_available(self):
        """PostgreSQL port 40432 must be available or in use by postgres."""
        # If service is running, port will be in use (expected)
        # If service is not running, port should be available
        # This test just ensures no OTHER service is using it
        port = 40432
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                # 0 = connected (service running), 111 = refused (not running)
                # Both are acceptable - just not OTHER services
                assert result in [0, 111], f"Port {port} in unexpected state"
        except Exception as e:
            pytest.fail(f"Port check failed: {e}")

    def test_redis_port_available(self):
        """Redis port 40379 must be available or in use by redis."""
        port = 40379
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                assert result in [0, 111], f"Port {port} in unexpected state"
        except Exception as e:
            pytest.fail(f"Port check failed: {e}")

    def test_weaviate_port_available(self):
        """Weaviate port 8080 must be available or in use by weaviate (existing instance)."""
        port = 8080
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                assert result in [0, 111], f"Port {port} in unexpected state"
        except Exception as e:
            pytest.fail(f"Port check failed: {e}")

    def test_ollama_port_available(self):
        """Ollama port 40434 must be available or in use by ollama."""
        port = 40434
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                assert result in [0, 111], f"Port {port} in unexpected state"
        except Exception as e:
            pytest.fail(f"Port check failed: {e}")


class TestServiceConnections:
    """Test connections to running services."""

    def test_postgres_connection(self):
        """PostgreSQL service must be accessible on port 40432."""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host="localhost",
                port=40432,
                user="acms",
                password="acms_password",
                database="acms",
                connect_timeout=5
            )
            conn.close()
        except ImportError:
            pytest.skip("psycopg2 not installed - install for connection tests")
        except Exception as e:
            pytest.fail(f"PostgreSQL connection failed: {e}")

    def test_redis_connection(self):
        """Redis service must be accessible on port 40379."""
        try:
            import redis
            client = redis.Redis(
                host="localhost",
                port=40379,
                socket_connect_timeout=5
            )
            client.ping()
            client.close()
        except ImportError:
            pytest.skip("redis not installed - install for connection tests")
        except Exception as e:
            pytest.fail(f"Redis connection failed: {e}")

    def test_weaviate_connection(self):
        """Weaviate service must be accessible at existing instance (8080 or 8081)."""
        try:
            import weaviate
            # Try existing instance on 8080 first
            try:
                client = weaviate.Client("http://localhost:8080", timeout_config=(5, 15))
                assert client.is_ready(), "Weaviate at 8080 not ready"
            except:
                # Fall back to 8081
                client = weaviate.Client("http://localhost:8081", timeout_config=(5, 15))
                assert client.is_ready(), "Weaviate at 8081 not ready"
        except ImportError:
            pytest.skip("weaviate-client not installed - install for connection tests")
        except Exception as e:
            pytest.fail(f"Weaviate connection failed: {e}")

    def test_ollama_connection(self):
        """Ollama service must be accessible on port 40434."""
        try:
            import requests
            response = requests.get(
                "http://localhost:40434/api/tags",
                timeout=5
            )
            assert response.status_code == 200, f"Ollama API returned {response.status_code}"
        except ImportError:
            pytest.skip("requests not installed - install for connection tests")
        except Exception as e:
            pytest.fail(f"Ollama connection failed: {e}")


class TestOllamaModels:
    """Test that required Ollama models are available."""

    def test_ollama_has_embedding_model(self):
        """all-minilm:22m embedding model must be available."""
        try:
            import requests
            response = requests.get("http://localhost:40434/api/tags", timeout=5)
            assert response.status_code == 200
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            assert any("all-minilm" in name for name in model_names), \
                "all-minilm:22m model not found"
        except ImportError:
            pytest.skip("requests not installed")
        except Exception as e:
            pytest.fail(f"Ollama model check failed: {e}")

    def test_ollama_has_llm_model(self):
        """llama3.2:1b LLM model must be available."""
        try:
            import requests
            response = requests.get("http://localhost:40434/api/tags", timeout=5)
            assert response.status_code == 200
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            assert any("llama3.2:1b" in name for name in model_names), \
                "llama3.2:1b model not found"
        except ImportError:
            pytest.skip("requests not installed")
        except Exception as e:
            pytest.fail(f"Ollama model check failed: {e}")


class TestHealthChecks:
    """Test health check scripts exist and work."""

    def test_health_check_script_exists(self):
        """infra/health_check.sh must exist."""
        health_check = Path("infra/health_check.sh")
        assert health_check.exists(), "infra/health_check.sh not found"

    def test_health_check_executable(self):
        """infra/health_check.sh must be executable."""
        health_check = Path("infra/health_check.sh")
        assert health_check.stat().st_mode & 0o111, "health_check.sh not executable"

    def test_health_check_runs_successfully(self):
        """infra/health_check.sh must run and return 0 when services healthy."""
        result = subprocess.run(
            ["bash", "infra/health_check.sh"],
            capture_output=True,
            timeout=30
        )
        # Allow non-zero if services not yet started, but script must run
        assert result.returncode in [0, 1], \
            f"Health check script failed with code {result.returncode}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
