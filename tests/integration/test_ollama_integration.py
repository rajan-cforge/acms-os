"""
Integration Tests for Ollama

End-to-end tests verifying Ollama integration with ACMS gateway.
Requires Ollama to be running for live tests.

Tests:
- Full gateway flow with Ollama agent
- Ollama embeddings in search pipeline
- Fallback behavior when Ollama unavailable
"""

import pytest
import asyncio
import os
from unittest.mock import Mock, AsyncMock, patch

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


class TestOllamaGatewayIntegration:
    """End-to-end gateway tests with Ollama agent."""

    @pytest.mark.asyncio
    async def test_ollama_agent_available(self):
        """Test that OllamaAgent can be instantiated."""
        from src.gateway.agents.ollama import OllamaAgent

        agent = OllamaAgent()

        assert agent.agent_name == "Ollama Local"
        assert agent.model == os.getenv("OLLAMA_MODEL", "llama3.2:latest")

    @pytest.mark.asyncio
    async def test_ollama_agent_metadata(self):
        """Test OllamaAgent metadata is correct."""
        from src.gateway.agents.ollama import OllamaAgent

        agent = OllamaAgent()
        metadata = agent.get_metadata()

        assert metadata["cost_per_million"] == 0
        assert "privacy-sensitive" in metadata["best_for"]
        assert metadata["supports_streaming"] is True

    @pytest.mark.asyncio
    async def test_ollama_in_agent_pool(self):
        """Test Ollama is registered in gateway orchestrator."""
        from src.gateway.orchestrator import GatewayOrchestrator
        from src.gateway.models import AgentType

        # Create orchestrator with mocked dependencies
        with patch('src.gateway.orchestrator.MemoryCRUD'):
            with patch('src.gateway.orchestrator.DualMemoryService'):
                orchestrator = GatewayOrchestrator()

        assert AgentType.OLLAMA in orchestrator.agents
        assert orchestrator.agents[AgentType.OLLAMA].agent_name == "Ollama Local"

    @pytest.mark.asyncio
    async def test_agent_type_ollama_exists(self):
        """Test AgentType.OLLAMA enum value exists."""
        from src.gateway.models import AgentType

        assert hasattr(AgentType, 'OLLAMA')
        assert AgentType.OLLAMA.value == "ollama"

    @pytest.mark.asyncio
    async def test_ollama_cost_estimation(self):
        """Test Ollama always returns $0 cost."""
        from src.gateway.agents.ollama import OllamaAgent

        agent = OllamaAgent()

        # Test various token counts
        assert agent.estimate_cost(0, 0) == 0.0
        assert agent.estimate_cost(1000, 1000) == 0.0
        assert agent.estimate_cost(100000, 100000) == 0.0


class TestOllamaClientIntegration:
    """Integration tests for OllamaClient."""

    @pytest.mark.asyncio
    async def test_ollama_client_init(self):
        """Test OllamaClient initialization."""
        from src.llm.ollama_client import OllamaClient

        client = OllamaClient()

        assert client.base_url == "http://localhost:40434"
        assert client.model == "llama3.2:latest"
        assert client.timeout == 60.0

    @pytest.mark.asyncio
    async def test_ollama_client_cost_calculation(self):
        """Test OllamaClient always returns $0 cost."""
        from src.llm.ollama_client import OllamaClient

        client = OllamaClient()

        cost = client.calculate_cost(input_tokens=1000000, output_tokens=1000000)
        assert cost == 0.0

    @pytest.mark.asyncio
    async def test_ollama_client_empty_prompt(self):
        """Test OllamaClient rejects empty prompts."""
        from src.llm.ollama_client import OllamaClient

        client = OllamaClient()

        with pytest.raises(ValueError, match="Prompt cannot be empty"):
            await client.complete("")


class TestOllamaEmbeddingsIntegration:
    """Integration tests for OllamaEmbeddings."""

    def test_ollama_embeddings_init(self):
        """Test OllamaEmbeddings initialization."""
        from src.embeddings.ollama_embeddings import OllamaEmbeddings

        embeddings = OllamaEmbeddings()

        assert embeddings.dimensions == 768
        assert embeddings.model == "nomic-embed-text"

    def test_ollama_embeddings_cache_stats(self):
        """Test cache statistics tracking."""
        from src.embeddings.ollama_embeddings import OllamaEmbeddings

        embeddings = OllamaEmbeddings()
        embeddings._cache_hits = 10
        embeddings._cache_misses = 5

        stats = embeddings.get_cache_stats()

        assert stats["hits"] == 10
        assert stats["misses"] == 5
        assert stats["total"] == 15

    def test_ollama_embeddings_empty_text_error(self):
        """Test empty text raises ValueError."""
        from src.embeddings.ollama_embeddings import OllamaEmbeddings

        embeddings = OllamaEmbeddings()

        with pytest.raises(ValueError, match="Text cannot be empty"):
            embeddings.generate_embedding("")


class TestOllamaProviderIntegration:
    """Integration tests for OllamaProvider in LLM providers."""

    @pytest.mark.asyncio
    async def test_ollama_provider_init(self):
        """Test OllamaProvider initialization."""
        from src.llm.providers import OllamaProvider

        provider = OllamaProvider()

        assert provider.model == "llama3.2:latest"
        assert provider.base_url == "http://localhost:40434"

    @pytest.mark.asyncio
    async def test_ollama_provider_in_factory(self):
        """Test Ollama provider can be created via factory."""
        from src.llm.factory import get_llm_client
        from src.llm.ollama_client import OllamaClient

        client = get_llm_client(provider='ollama')

        assert isinstance(client, OllamaClient)


class TestOllamaCircuitBreaker:
    """Tests for circuit breaker behavior."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_initial_state(self):
        """Test circuit breaker starts in closed state."""
        from src.llm.ollama_client import OllamaClient, CircuitState

        client = OllamaClient()

        assert client.circuit.state == CircuitState.CLOSED
        assert client.circuit.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_breaker_records_failures(self):
        """Test circuit breaker records failures."""
        from src.llm.ollama_client import CircuitBreaker, CircuitState

        breaker = CircuitBreaker(failure_threshold=3)

        breaker.record_failure()
        assert breaker.failure_count == 1
        assert breaker.state == CircuitState.CLOSED

        breaker.record_failure()
        assert breaker.failure_count == 2
        assert breaker.state == CircuitState.CLOSED

        breaker.record_failure()
        assert breaker.failure_count == 3
        assert breaker.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_on_success(self):
        """Test circuit breaker resets on success."""
        from src.llm.ollama_client import CircuitBreaker, CircuitState

        breaker = CircuitBreaker()
        breaker.failure_count = 3
        breaker.state = CircuitState.HALF_OPEN

        breaker.record_success()

        assert breaker.failure_count == 0
        assert breaker.state == CircuitState.CLOSED


class TestOllamaLiveIntegration:
    """Live integration tests (require running Ollama).

    These tests are skipped if Ollama is not available.
    """

    @pytest.fixture
    def check_ollama(self):
        """Check if Ollama is running and skip if not."""
        import aiohttp

        async def check():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get("http://localhost:40434/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        return resp.status == 200
            except Exception:
                return False

        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        available = loop.run_until_complete(check())
        if not available:
            pytest.skip("Ollama not available - skipping live test")

    @pytest.mark.asyncio
    async def test_live_ollama_completion(self, check_ollama):
        """Test live completion with Ollama."""
        from src.llm.ollama_client import OllamaClient

        client = OllamaClient()

        try:
            response = await client.complete(
                "What is 2 + 2? Answer in one word.",
                max_tokens=10
            )

            assert len(response) > 0
            assert "4" in response or "four" in response.lower()
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_live_ollama_streaming(self, check_ollama):
        """Test live streaming with Ollama."""
        from src.llm.ollama_client import OllamaClient

        client = OllamaClient()

        try:
            chunks = []
            async for chunk in client.stream_complete(
                "Say hello.",
                max_tokens=20
            ):
                chunks.append(chunk)

            response = "".join(chunks)
            assert len(response) > 0
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_live_ollama_agent(self, check_ollama):
        """Test live OllamaAgent generation."""
        from src.gateway.agents.ollama import OllamaAgent

        agent = OllamaAgent()

        chunks = []
        async for chunk in agent.generate("Say hello in one word."):
            chunks.append(chunk)

        response = "".join(chunks)
        assert len(response) > 0

    @pytest.mark.asyncio
    async def test_live_ollama_embeddings(self, check_ollama):
        """Test live embedding generation with Ollama."""
        from src.embeddings.ollama_embeddings import OllamaEmbeddings

        # Check if embedding model is available
        embeddings = OllamaEmbeddings(use_cache=False)

        try:
            vec = embeddings.generate_embedding("Hello world")

            assert isinstance(vec, list)
            assert len(vec) == 768
            assert all(isinstance(v, float) for v in vec)
        except RuntimeError as e:
            if "model not found" in str(e).lower():
                pytest.skip("Ollama embedding model not available")
            raise
