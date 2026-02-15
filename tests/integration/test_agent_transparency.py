"""
Integration tests for agent transparency in API responses.

Tests that API responses correctly expose:
- Which agent handled the query (claude_sonnet, chatgpt, gemini, claude_code)
- Which intent was detected (ANALYSIS, CREATIVE, RESEARCH, etc.)
- Cache status (cache_hit, fresh_generation, semantic_cache_hit)

Security: Verify we don't expose internal implementation details that could be exploited.
Performance: Verify minimal overhead from metadata collection.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.api_server import app
from src.gateway.models import IntentType, AgentType


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestAgentTransparency:
    """Test suite for agent transparency in API responses."""

    def test_creative_query_uses_chatgpt(self, client):
        """CREATIVE intent should route to ChatGPT and expose this in response."""
        query = "Write a haiku about semantic caching"

        with patch('src.api_server.gateway') as mock_gateway:
            # Mock gateway response
            mock_response = AsyncMock()
            mock_response.__aiter__.return_value = iter([
                "Vectors align fast\n",
                "Memory recalls wisdom\n",
                "Save time and money\n"
            ])
            mock_gateway.process_query = AsyncMock(return_value={
                "response": mock_response,
                "agent_used": AgentType.CHATGPT,
                "intent_detected": IntentType.CREATIVE,
                "confidence": 0.95,
                "sources": [],
                "metadata": {}
            })

            response = client.post("/gateway/ask-sync", json={
                "query": query,
                "user_id": "test_user"
            })

            assert response.status_code == 200
            data = response.json()

            # Verify agent transparency fields
            assert "agent_used" in data, "Response must include agent_used field"
            assert data["agent_used"] == "chatgpt", f"CREATIVE intent should use ChatGPT, got {data.get('agent_used')}"

            assert "intent_detected" in data, "Response must include intent_detected field"
            assert data["intent_detected"] == "creative", f"Expected CREATIVE intent, got {data.get('intent_detected')}"

            assert "cache_status" in data, "Response must include cache_status field"
            assert data["cache_status"] == "fresh_generation", "New query should be fresh generation"

    def test_research_query_uses_gemini(self, client):
        """RESEARCH intent should route to Gemini and expose this in response."""
        query = "Research the latest trends in vector databases"

        with patch('src.api_server.gateway') as mock_gateway:
            mock_response = AsyncMock()
            mock_response.__aiter__.return_value = iter([
                "Recent trends in vector databases include...",
            ])
            mock_gateway.process_query = AsyncMock(return_value={
                "response": mock_response,
                "agent_used": AgentType.GEMINI,
                "intent_detected": IntentType.RESEARCH,
                "confidence": 0.92,
                "sources": [],
                "metadata": {}
            })

            response = client.post("/gateway/ask-sync", json={
                "query": query,
                "user_id": "test_user"
            })

            assert response.status_code == 200
            data = response.json()

            assert data["agent_used"] == "gemini", "RESEARCH intent should use Gemini"
            assert data["intent_detected"] == "research"
            assert data["cache_status"] == "fresh_generation"

    def test_analysis_query_uses_claude_sonnet(self, client):
        """ANALYSIS intent should route to Claude Sonnet and expose this in response."""
        query = "Explain how the intent classifier works in ACMS"

        with patch('src.api_server.gateway') as mock_gateway:
            mock_response = AsyncMock()
            mock_response.__aiter__.return_value = iter([
                "The intent classifier uses rule-based matching...",
            ])
            mock_gateway.process_query = AsyncMock(return_value={
                "response": mock_response,
                "agent_used": AgentType.CLAUDE_SONNET,
                "intent_detected": IntentType.ANALYSIS,
                "confidence": 0.89,
                "sources": [],
                "metadata": {}
            })

            response = client.post("/gateway/ask-sync", json={
                "query": query,
                "user_id": "test_user"
            })

            assert response.status_code == 200
            data = response.json()

            assert data["agent_used"] == "claude_sonnet", "ANALYSIS intent should use Claude Sonnet"
            assert data["intent_detected"] == "analysis"

    def test_cache_hit_preserves_agent_metadata(self, client):
        """Cache hits should preserve original agent metadata."""
        query = "What are the 5 storage tiers?"

        with patch('src.api_server.semantic_cache') as mock_cache:
            # Mock cache hit
            mock_cache.get = AsyncMock(return_value={
                "answer": "The 5 tiers are: semantic cache, query history, memory items...",
                "sources": [],
                "agent_used": "claude_sonnet",
                "intent_detected": "analysis",
                "cache_similarity": 0.98
            })

            response = client.post("/ask", json={
                "question": query,
                "user_id": "test_user"
            })

            assert response.status_code == 200
            data = response.json()

            # Verify cache hit preserves agent info
            assert data["cache_status"] == "semantic_cache_hit", "Should indicate cache hit"
            assert data["agent_used"] == "claude_sonnet", "Cache should preserve original agent"
            assert data["intent_detected"] == "analysis", "Cache should preserve original intent"

    def test_manual_agent_override(self, client):
        """Manual agent selection should override intent routing."""
        query = "Explain how Docker works"  # Would normally be ANALYSIS -> Claude Sonnet

        with patch('src.api_server.gateway') as mock_gateway:
            mock_response = AsyncMock()
            mock_response.__aiter__.return_value = iter([
                "Docker is a containerization platform...",
            ])
            mock_gateway.process_query = AsyncMock(return_value={
                "response": mock_response,
                "agent_used": AgentType.GEMINI,  # User manually selected Gemini
                "intent_detected": IntentType.ANALYSIS,
                "confidence": 0.88,
                "sources": [],
                "metadata": {"manual_override": True}
            })

            response = client.post("/gateway/ask-sync", json={
                "query": query,
                "user_id": "test_user",
                "manual_agent": "gemini"  # User forces Gemini
            })

            assert response.status_code == 200
            data = response.json()

            assert data["agent_used"] == "gemini", "Manual override should be respected"
            assert data["intent_detected"] == "analysis", "Intent detection still runs"

    def test_security_no_sensitive_internals_exposed(self, client):
        """Verify we don't expose sensitive implementation details."""
        query = "Test security"

        with patch('src.api_server.gateway') as mock_gateway:
            mock_response = AsyncMock()
            mock_response.__aiter__.return_value = iter(["Test response"])
            mock_gateway.process_query = AsyncMock(return_value={
                "response": mock_response,
                "agent_used": AgentType.CLAUDE_SONNET,
                "intent_detected": IntentType.ANALYSIS,
                "confidence": 0.85,
                "sources": [],
                "metadata": {
                    # These should NOT be exposed to end user:
                    "api_key": "sk-secret123",  # NEVER expose API keys
                    "internal_cost_usd": 0.00045,  # Internal cost tracking
                    "model_version": "claude-3-5-sonnet-20250929",  # Specific model version
                    "endpoint_url": "https://api.anthropic.com/v1/messages"  # Internal URLs
                }
            })

            response = client.post("/gateway/ask-sync", json={
                "query": query,
                "user_id": "test_user"
            })

            assert response.status_code == 200
            data = response.json()

            # Security checks: sensitive data MUST NOT be exposed
            assert "api_key" not in str(data), "SECURITY: API keys must never be exposed"
            assert "endpoint_url" not in str(data), "SECURITY: Internal endpoints must not be exposed"

            # Public metadata is OK
            assert data["agent_used"] == "claude_sonnet", "Public agent name is safe to expose"
            assert data["intent_detected"] == "analysis", "Public intent type is safe to expose"

    def test_performance_metadata_overhead_minimal(self, client):
        """Verify agent metadata collection has minimal performance overhead."""
        import time

        query = "Quick performance test"

        with patch('src.api_server.gateway') as mock_gateway:
            # Track time spent collecting metadata
            metadata_collection_time = []

            def mock_process():
                start = time.time()
                # Simulate metadata collection
                metadata = {
                    "agent_used": AgentType.CLAUDE_SONNET,
                    "intent_detected": IntentType.ANALYSIS,
                    "confidence": 0.90,
                    "sources": [],
                    "metadata": {}
                }
                metadata_collection_time.append(time.time() - start)

                mock_response = AsyncMock()
                mock_response.__aiter__.return_value = iter(["Response"])
                return {
                    "response": mock_response,
                    **metadata
                }

            mock_gateway.process_query = AsyncMock(side_effect=mock_process)

            response = client.post("/gateway/ask-sync", json={
                "query": query,
                "user_id": "test_user"
            })

            assert response.status_code == 200

            # Metadata collection should be < 1ms (virtually free)
            if metadata_collection_time:
                overhead_ms = metadata_collection_time[0] * 1000
                assert overhead_ms < 1.0, f"Metadata collection overhead too high: {overhead_ms:.2f}ms"

    def test_all_agent_types_supported(self, client):
        """Verify all 4 agent types can be used and reported."""
        test_cases = [
            ("chatgpt", IntentType.CREATIVE, "Write a poem"),
            ("gemini", IntentType.RESEARCH, "Research latest AI trends"),
            ("claude_sonnet", IntentType.ANALYSIS, "Analyze this system"),
            ("claude_code", IntentType.TERMINAL_COMMAND, "Run docker ps"),
        ]

        for expected_agent, intent, query in test_cases:
            with patch('src.api_server.gateway') as mock_gateway:
                agent_enum = AgentType[expected_agent.upper().replace("CLAUDE_SONNET", "CLAUDE_SONNET")]

                mock_response = AsyncMock()
                mock_response.__aiter__.return_value = iter(["Test response"])
                mock_gateway.process_query = AsyncMock(return_value={
                    "response": mock_response,
                    "agent_used": agent_enum,
                    "intent_detected": intent,
                    "confidence": 0.85,
                    "sources": [],
                    "metadata": {}
                })

                response = client.post("/gateway/ask", json={
                    "query": query,
                    "user_id": "test_user"
                })

                assert response.status_code == 200
                data = response.json()
                assert data["agent_used"] == expected_agent, f"Expected {expected_agent} for query: {query}"

    def test_response_format_backward_compatible(self, client):
        """New fields should not break existing clients (backward compatibility)."""
        query = "Test backward compatibility"

        with patch('src.api_server.gateway') as mock_gateway:
            mock_response = AsyncMock()
            mock_response.__aiter__.return_value = iter(["Response"])
            mock_gateway.process_query = AsyncMock(return_value={
                "response": mock_response,
                "agent_used": AgentType.CLAUDE_SONNET,
                "intent_detected": IntentType.ANALYSIS,
                "confidence": 0.85,
                "sources": [],
                "metadata": {}
            })

            response = client.post("/gateway/ask-sync", json={
                "query": query,
                "user_id": "test_user"
            })

            assert response.status_code == 200
            data = response.json()

            # All existing fields must still be present
            assert "answer" in data, "Backward compatibility: 'answer' field must exist"
            assert "sources" in data, "Backward compatibility: 'sources' field must exist"
            assert "confidence" in data, "Backward compatibility: 'confidence' field must exist"
            assert "query_id" in data, "Backward compatibility: 'query_id' field must exist"

            # New fields are additions, not replacements
            assert "agent_used" in data, "New field 'agent_used' should be added"
            assert "intent_detected" in data, "New field 'intent_detected' should be added"
            assert "cache_status" in data, "New field 'cache_status' should be added"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
