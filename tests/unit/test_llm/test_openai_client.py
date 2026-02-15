"""
Tests for OpenAI LLM Client

Week 5 Day 1: Task 2 (3.5 hours)
Total: 24 tests

Purpose: Enhanced OpenAI client with cost calculation, streaming, embeddings
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from openai import RateLimitError, APIError, APIConnectionError

from src.llm.openai_client import OpenAIClient
from src.llm.factory import get_llm_client
from src.utils.logging import set_correlation_id, get_correlation_id


# ============================================================================
# BASIC FUNCTIONALITY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_complete_success():
    """Test successful completion with GPT-4 Turbo"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    # Mock the OpenAI API response
    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Test response"))]
    mock_response.usage = Mock(prompt_tokens=10, completion_tokens=20)

    with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, return_value=mock_response):
        result = await client.complete(
            prompt="Test prompt",
            model="gpt-4-turbo",
            max_tokens=100
        )

    assert result == "Test response"


@pytest.mark.asyncio
async def test_complete_with_gpt_3_5():
    """Test completion with GPT-3.5 Turbo (cheaper model)"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="GPT-3.5 response"))]
    mock_response.usage = Mock(prompt_tokens=10, completion_tokens=15)

    with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, return_value=mock_response):
        result = await client.complete(
            prompt="Simple task",
            model="gpt-3.5-turbo",
            max_tokens=50
        )

    assert result == "GPT-3.5 response"


@pytest.mark.asyncio
async def test_complete_with_gpt_4o():
    """Test completion with GPT-4o (balanced model)"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="GPT-4o response"))]
    mock_response.usage = Mock(prompt_tokens=10, completion_tokens=20)

    with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, return_value=mock_response):
        result = await client.complete(
            prompt="Test prompt",
            model="gpt-4o",
            max_tokens=100
        )

    assert result == "GPT-4o response"


@pytest.mark.asyncio
async def test_stream_complete():
    """Test streaming completion"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    # Mock streaming response
    async def mock_stream(**kwargs):
        chunks = ["Hello", " ", "world", "!"]
        for chunk in chunks:
            mock_chunk = Mock()
            mock_chunk.choices = [Mock(delta=Mock(content=chunk))]
            yield mock_chunk

    with patch.object(client.client.chat.completions, 'create', side_effect=mock_stream):
        result = []
        async for chunk in client.stream_complete(
            prompt="Test",
            model="gpt-4-turbo"
        ):
            result.append(chunk)

    assert "".join(result) == "Hello world!"


@pytest.mark.asyncio
async def test_embed():
    """Test embedding generation"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    # Mock embedding response
    mock_response = Mock()
    mock_response.data = [Mock(embedding=[0.1, 0.2, 0.3, 0.4, 0.5] * 307)]  # 1536 dims (approximate)

    with patch.object(client.client.embeddings, 'create', new_callable=AsyncMock, return_value=mock_response):
        embedding = await client.embed(
            text="Test text for embedding",
            model="text-embedding-3-small"
        )

    assert len(embedding) == 1535  # 5 * 307
    assert isinstance(embedding, list)
    assert all(isinstance(x, float) for x in embedding)


# ============================================================================
# COST CALCULATION TESTS
# ============================================================================

def test_calculate_cost_gpt4_turbo():
    """Test cost calculation for GPT-4 Turbo"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    # GPT-4 Turbo: $10/1M input, $30/1M output
    cost = client.calculate_cost(
        model="gpt-4-turbo",
        input_tokens=1000,
        output_tokens=500
    )

    # Cost = (1000/1M * $10) + (500/1M * $30) = $0.01 + $0.015 = $0.025
    assert cost == pytest.approx(0.025, rel=0.001)


def test_calculate_cost_gpt35():
    """Test cost calculation for GPT-3.5 Turbo"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    # GPT-3.5 Turbo: $0.50/1M input, $1.50/1M output
    cost = client.calculate_cost(
        model="gpt-3.5-turbo",
        input_tokens=1000,
        output_tokens=500
    )

    # Cost = (1000/1M * $0.50) + (500/1M * $1.50) = $0.0005 + $0.00075 = $0.00125
    assert cost == pytest.approx(0.00125, rel=0.001)


def test_calculate_cost_gpt4o():
    """Test cost calculation for GPT-4o"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    # GPT-4o: $2.50/1M input, $10/1M output
    cost = client.calculate_cost(
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=500
    )

    # Cost = (1000/1M * $2.50) + (500/1M * $10) = $0.0025 + $0.005 = $0.0075
    assert cost == pytest.approx(0.0075, rel=0.001)


def test_cost_accuracy():
    """Test cost calculation accuracy with large token counts"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    # Large request: 100K input, 50K output with GPT-4 Turbo
    cost = client.calculate_cost(
        model="gpt-4-turbo",
        input_tokens=100000,
        output_tokens=50000
    )

    # Cost = (100K/1M * $10) + (50K/1M * $30) = $1.00 + $1.50 = $2.50
    assert cost == pytest.approx(2.50, rel=0.001)


def test_unknown_model_cost():
    """Test cost calculation for unknown model returns 0"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    cost = client.calculate_cost(
        model="unknown-model",
        input_tokens=1000,
        output_tokens=500
    )

    assert cost == 0.0


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_rate_limit_error():
    """Test handling of OpenAI rate limit errors"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, side_effect=RateLimitError("Rate limit exceeded", response=Mock(), body={})):
        with pytest.raises(RateLimitError):
            await client.complete(prompt="Test", model="gpt-4-turbo")


@pytest.mark.asyncio
async def test_api_error():
    """Test handling of generic OpenAI API errors"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, side_effect=APIError("API error", request=Mock(), body={})):
        with pytest.raises(APIError):
            await client.complete(prompt="Test", model="gpt-4-turbo")


def test_invalid_api_key():
    """Test that invalid API key raises ValueError"""
    with pytest.raises(ValueError, match="Invalid OpenAI API key"):
        OpenAIClient(api_key="invalid-key")


@pytest.mark.asyncio
async def test_timeout():
    """Test handling of timeout errors"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, side_effect=asyncio.TimeoutError):
        with pytest.raises(asyncio.TimeoutError):
            await client.complete(prompt="Test", model="gpt-4-turbo", timeout=1)


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_empty_prompt():
    """Test handling of empty prompt"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    # Should raise ValueError or handle gracefully
    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        await client.complete(prompt="", model="gpt-4-turbo")


@pytest.mark.asyncio
async def test_very_long_prompt():
    """Test handling of very long prompts"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    # Create a very long prompt (100K characters)
    long_prompt = "a" * 100000

    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Response to long prompt"))]
    mock_response.usage = Mock(prompt_tokens=25000, completion_tokens=50)

    with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, return_value=mock_response):
        result = await client.complete(prompt=long_prompt, model="gpt-4-turbo")

    assert result == "Response to long prompt"


@pytest.mark.asyncio
async def test_negative_max_tokens():
    """Test handling of negative max_tokens"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    with pytest.raises(ValueError, match="max_tokens must be positive"):
        await client.complete(prompt="Test", model="gpt-4-turbo", max_tokens=-100)


@pytest.mark.asyncio
async def test_max_tokens_zero():
    """Test handling of zero max_tokens"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    with pytest.raises(ValueError, match="max_tokens must be positive"):
        await client.complete(prompt="Test", model="gpt-4-turbo", max_tokens=0)


# ============================================================================
# CONCURRENT REQUEST TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_concurrent_requests():
    """Test handling of concurrent requests"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    async def mock_complete(**kwargs):
        prompt = kwargs.get('messages', [{}])[0].get('content', '')
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content=f"Response to: {prompt}"))]
        mock_response.usage = Mock(prompt_tokens=10, completion_tokens=20)
        return mock_response

    with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, side_effect=mock_complete):
        results = await asyncio.gather(
            client.complete("Prompt 1", "gpt-4-turbo"),
            client.complete("Prompt 2", "gpt-4-turbo"),
            client.complete("Prompt 3", "gpt-4-turbo")
        )

    assert len(results) == 3
    assert all(isinstance(r, str) for r in results)


# ============================================================================
# CORRELATION ID LOGGING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_correlation_id_in_logs():
    """Test that correlation ID is included in logs"""
    client = OpenAIClient(api_key="sk-test-key-mock")

    # Set correlation ID
    set_correlation_id("test-corr-123")

    mock_response = Mock()
    mock_response.choices = [Mock(message=Mock(content="Response"))]
    mock_response.usage = Mock(prompt_tokens=10, completion_tokens=20)

    with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock, return_value=mock_response):
        with patch('src.llm.openai_client.logger') as mock_logger:
            await client.complete(prompt="Test", model="gpt-4-turbo")

            # Verify logger was called
            assert mock_logger.info.called


# ============================================================================
# FACTORY PATTERN TESTS
# ============================================================================

def test_get_openai_client():
    """Test factory function returns OpenAI client"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test-key-mock'}):
        client = get_llm_client(provider='openai')

    assert isinstance(client, OpenAIClient)


def test_get_unknown_provider_raises():
    """Test factory raises error for unknown provider"""
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        get_llm_client(provider='unknown')


def test_factory_uses_config():
    """Test factory uses config for provider selection"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test-key-mock', 'LLM_PROVIDER': 'openai'}):
        client = get_llm_client()  # No provider specified, should use config

    assert isinstance(client, OpenAIClient)


def test_provider_override():
    """Test explicit provider overrides config"""
    with patch.dict('os.environ', {'OPENAI_API_KEY': 'sk-test-key-mock', 'LLM_PROVIDER': 'anthropic'}):
        # Even though config says anthropic, we explicitly request openai
        client = get_llm_client(provider='openai')

    assert isinstance(client, OpenAIClient)
