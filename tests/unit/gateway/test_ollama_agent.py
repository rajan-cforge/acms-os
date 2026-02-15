"""
Tests for Ollama Gateway Agent

TDD Implementation - Tests written before implementation
Total: 15 tests

Purpose: Gateway agent for local LLM streaming with context injection
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import AsyncIterator

# Import will fail until implementation exists - expected for TDD
try:
    from src.gateway.agents.ollama import OllamaAgent
except ImportError:
    OllamaAgent = None


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_agent_name():
    """Test OllamaAgent has correct agent name"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent()

    assert agent.agent_name == "Ollama Local"


@pytest.mark.asyncio
async def test_default_model():
    """Test OllamaAgent uses default model"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent()

    assert agent.model == "llama3.2:latest"


@pytest.mark.asyncio
async def test_custom_model():
    """Test OllamaAgent with custom model"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent(model="mistral:7b")

    assert agent.model == "mistral:7b"


@pytest.mark.asyncio
async def test_custom_base_url():
    """Test OllamaAgent with custom Ollama URL"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent(base_url="http://custom:11434")

    assert agent.client.base_url == "http://custom:11434"


# ============================================================================
# METADATA TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_metadata_structure():
    """Test get_metadata() returns correct structure"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent()
    metadata = agent.get_metadata()

    assert "agent_name" in metadata
    assert "model" in metadata
    assert "supports_streaming" in metadata
    assert "supports_context" in metadata
    assert "cost_per_million" in metadata
    assert "best_for" in metadata


@pytest.mark.asyncio
async def test_metadata_values():
    """Test get_metadata() returns correct values"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent()
    metadata = agent.get_metadata()

    assert metadata["agent_name"] == "Ollama Local"
    assert metadata["supports_streaming"] is True
    assert metadata["supports_context"] is True
    assert metadata["cost_per_million"] == 0  # Free!
    assert "privacy-sensitive" in metadata["best_for"]
    assert "offline" in metadata["best_for"]


# ============================================================================
# GENERATE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_generate_streams_response():
    """Test generate() yields streaming chunks"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent()

    # Mock the client's stream_complete to yield chunks
    async def mock_stream(*args, **kwargs):
        chunks = ["Hello", " ", "world", "!"]
        for chunk in chunks:
            yield chunk

    with patch.object(agent.client, 'stream_complete', side_effect=mock_stream):
        result_chunks = []
        async for chunk in agent.generate(query="Say hello"):
            result_chunks.append(chunk)

    assert "".join(result_chunks) == "Hello world!"


@pytest.mark.asyncio
async def test_generate_with_context():
    """Test generate() correctly injects context into prompt"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent()
    captured_prompt = None

    async def mock_stream(prompt, **kwargs):
        nonlocal captured_prompt
        captured_prompt = prompt
        yield "Response"

    with patch.object(agent.client, 'stream_complete', side_effect=mock_stream):
        async for _ in agent.generate(
            query="What is Python?",
            context="Python is a programming language."
        ):
            pass

    assert captured_prompt is not None
    assert "Python is a programming language." in captured_prompt
    assert "What is Python?" in captured_prompt


@pytest.mark.asyncio
async def test_generate_without_context():
    """Test generate() works without context"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent()
    captured_prompt = None

    async def mock_stream(prompt, **kwargs):
        nonlocal captured_prompt
        captured_prompt = prompt
        yield "Response"

    with patch.object(agent.client, 'stream_complete', side_effect=mock_stream):
        async for _ in agent.generate(query="Hello"):
            pass

    assert captured_prompt is not None
    assert captured_prompt == "Hello"


@pytest.mark.asyncio
async def test_generate_error_handling():
    """Test generate() yields error message on failure"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent()

    async def mock_stream_error(*args, **kwargs):
        raise ConnectionError("Ollama unavailable")
        yield  # Make it a generator

    with patch.object(agent.client, 'stream_complete', side_effect=mock_stream_error):
        result_chunks = []
        async for chunk in agent.generate(query="Test"):
            result_chunks.append(chunk)

    response = "".join(result_chunks)
    assert "[Error:" in response or "unavailable" in response.lower()


@pytest.mark.asyncio
async def test_generate_empty_query():
    """Test generate() handles empty query gracefully"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent()

    # Should either yield error or raise ValueError
    result_chunks = []
    try:
        async for chunk in agent.generate(query=""):
            result_chunks.append(chunk)
    except ValueError:
        pass  # Also acceptable

    # Either got error chunks or ValueError was raised
    if result_chunks:
        response = "".join(result_chunks)
        assert "error" in response.lower() or len(response) == 0


# ============================================================================
# COST ESTIMATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_estimate_cost_zero():
    """Test estimate_cost() always returns $0.00"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent()

    cost = agent.estimate_cost(input_tokens=1000, output_tokens=500)

    assert cost == 0.0


@pytest.mark.asyncio
async def test_cost_not_affected_by_tokens():
    """Test cost stays $0 regardless of token count"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent()

    # Even with massive token counts
    cost1 = agent.estimate_cost(input_tokens=0, output_tokens=0)
    cost2 = agent.estimate_cost(input_tokens=100000, output_tokens=50000)
    cost3 = agent.estimate_cost(input_tokens=1000000, output_tokens=1000000)

    assert cost1 == 0.0
    assert cost2 == 0.0
    assert cost3 == 0.0


# ============================================================================
# INTEGRATION WITH BASE AGENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_inherits_base_agent():
    """Test OllamaAgent properly inherits from BaseAgent"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    from src.gateway.agents.base_agent import BaseAgent

    agent = OllamaAgent()

    assert isinstance(agent, BaseAgent)


@pytest.mark.asyncio
async def test_has_generate_method():
    """Test OllamaAgent implements generate() as AsyncIterator"""
    if OllamaAgent is None:
        pytest.skip("OllamaAgent not implemented yet")

    agent = OllamaAgent()

    # Mock the client
    async def mock_stream(*args, **kwargs):
        yield "test"

    with patch.object(agent.client, 'stream_complete', side_effect=mock_stream):
        result = agent.generate(query="test")

        # Should return an async iterator
        assert hasattr(result, '__aiter__')
        assert hasattr(result, '__anext__')
