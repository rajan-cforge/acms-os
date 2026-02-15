"""
Tests for Ollama LLM Client

TDD Implementation - Tests written before implementation
Total: 28 tests

Purpose: Local LLM inference with circuit breaker, retry, and streaming
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import aiohttp

# Import will fail until implementation exists - expected for TDD
try:
    from src.llm.ollama_client import OllamaClient, CircuitBreaker, CircuitState
except ImportError:
    # Define stubs for TDD - tests can be written before implementation
    OllamaClient = None
    CircuitBreaker = None
    CircuitState = None


# ============================================================================
# INITIALIZATION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_init_with_defaults():
    """Test OllamaClient initializes with default values"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    assert client.base_url == "http://localhost:40434"
    assert client.model == "llama3.2:latest"
    assert client.timeout == 60.0
    assert client.max_retries == 3


@pytest.mark.asyncio
async def test_init_with_custom_url():
    """Test OllamaClient with custom base URL"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient(base_url="http://custom-ollama:11434")

    assert client.base_url == "http://custom-ollama:11434"


@pytest.mark.asyncio
async def test_init_with_custom_model():
    """Test OllamaClient with custom model name"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient(model="mistral:7b")

    assert client.model == "mistral:7b"


@pytest.mark.asyncio
async def test_init_strips_trailing_slash():
    """Test that trailing slash is stripped from base_url"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient(base_url="http://localhost:40434/")

    assert client.base_url == "http://localhost:40434"


# ============================================================================
# HEALTH CHECK TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_health_check_success():
    """Test is_available() returns True when Ollama is running"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    # Mock successful API response
    mock_response = AsyncMock()
    mock_response.status = 200

    with patch('aiohttp.ClientSession.get', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
        result = await client.is_available()

    assert result is True


@pytest.mark.asyncio
async def test_health_check_failure():
    """Test is_available() returns False when Ollama is down"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    with patch('aiohttp.ClientSession.get', side_effect=aiohttp.ClientError("Connection refused")):
        result = await client.is_available()

    assert result is False


@pytest.mark.asyncio
async def test_health_check_non_200():
    """Test is_available() returns False for non-200 status"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    mock_response = AsyncMock()
    mock_response.status = 503

    with patch('aiohttp.ClientSession.get', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))):
        result = await client.is_available()

    assert result is False


# ============================================================================
# COMPLETION TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_complete_simple_prompt():
    """Test basic completion with simple prompt"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    # Mock Ollama API response
    mock_response_data = {
        "model": "llama3.2:latest",
        "response": "Python is a programming language.",
        "done": True
    }

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_response_data)

    with patch.object(client, '_get_session') as mock_session:
        mock_session.return_value.post = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        result = await client.complete("What is Python?")

    assert "Python" in result or "programming" in result.lower()


@pytest.mark.asyncio
async def test_complete_with_system_prompt():
    """Test completion with system prompt"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    mock_response_data = {
        "response": "I am a helpful coding assistant.",
        "done": True
    }

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_response_data)

    with patch.object(client, '_get_session') as mock_session:
        mock_session.return_value.post = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        result = await client.complete(
            prompt="Who are you?",
            system="You are a helpful coding assistant."
        )

    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_complete_with_temperature():
    """Test completion with custom temperature"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    mock_response_data = {"response": "Creative response", "done": True}
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_response_data)

    with patch.object(client, '_get_session') as mock_session:
        mock_session.return_value.post = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        # High temperature for creative responses
        result = await client.complete("Tell me a joke", temperature=0.9)

    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_complete_empty_prompt_error():
    """Test that empty prompt raises ValueError"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        await client.complete("")


@pytest.mark.asyncio
async def test_complete_whitespace_prompt_error():
    """Test that whitespace-only prompt raises ValueError"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    with pytest.raises(ValueError, match="Prompt cannot be empty"):
        await client.complete("   \n\t   ")


@pytest.mark.asyncio
async def test_complete_timeout():
    """Test that timeout is handled gracefully"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient(timeout=1.0)

    with patch.object(client, '_get_session') as mock_session:
        mock_session.return_value.post = AsyncMock(side_effect=asyncio.TimeoutError())

        with pytest.raises(asyncio.TimeoutError):
            await client.complete("Test prompt")


@pytest.mark.asyncio
async def test_complete_connection_error():
    """Test handling of connection refused error"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    with patch.object(client, '_get_session') as mock_session:
        mock_session.return_value.post = AsyncMock(
            side_effect=aiohttp.ClientConnectorError(Mock(), Mock())
        )

        with pytest.raises(aiohttp.ClientConnectorError):
            await client.complete("Test prompt")


# ============================================================================
# STREAMING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_stream_complete_chunks():
    """Test streaming completion yields chunks correctly"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    # Mock streaming response with NDJSON
    async def mock_read_chunks():
        chunks = [
            b'{"response": "Hello", "done": false}\n',
            b'{"response": " world", "done": false}\n',
            b'{"response": "!", "done": true}\n',
        ]
        for chunk in chunks:
            yield chunk

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content.iter_any = mock_read_chunks

    with patch.object(client, '_get_session') as mock_session:
        mock_session.return_value.post = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        result_chunks = []
        async for chunk in client.stream_complete("Test"):
            result_chunks.append(chunk)

    assert "".join(result_chunks) == "Hello world!"


@pytest.mark.asyncio
async def test_stream_empty_response():
    """Test handling of empty streaming response"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    async def mock_read_empty():
        return
        yield  # Make it a generator

    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.content.iter_any = mock_read_empty

    with patch.object(client, '_get_session') as mock_session:
        mock_session.return_value.post = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )

        result_chunks = []
        async for chunk in client.stream_complete("Test"):
            result_chunks.append(chunk)

    assert result_chunks == []


@pytest.mark.asyncio
async def test_stream_connection_error():
    """Test error during streaming"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    with patch.object(client, '_get_session') as mock_session:
        mock_session.return_value.post = AsyncMock(
            side_effect=aiohttp.ClientError("Connection lost")
        )

        with pytest.raises(aiohttp.ClientError):
            async for _ in client.stream_complete("Test"):
                pass


# ============================================================================
# CIRCUIT BREAKER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_circuit_breaker_opens_after_failures():
    """Test circuit breaker opens after threshold failures"""
    if OllamaClient is None or CircuitBreaker is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()
    client.circuit.failure_threshold = 3

    # Simulate 3 failures
    with patch.object(client, '_get_session') as mock_session:
        mock_session.return_value.post = AsyncMock(
            side_effect=aiohttp.ClientError("Connection failed")
        )

        for _ in range(3):
            try:
                await client.complete("Test")
            except:
                pass

    assert client.circuit.state == CircuitState.OPEN


@pytest.mark.asyncio
async def test_circuit_breaker_rejects_when_open():
    """Test circuit breaker rejects requests when open"""
    if OllamaClient is None or CircuitState is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()
    client.circuit.state = CircuitState.OPEN
    client.circuit.last_failure_time = time.time()

    with pytest.raises(Exception, match="Circuit breaker is open"):
        await client.complete("Test")


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_after_timeout():
    """Test circuit breaker transitions to half-open after recovery timeout"""
    if OllamaClient is None or CircuitState is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()
    client.circuit.state = CircuitState.OPEN
    client.circuit.recovery_timeout = 0.1  # Short timeout for test
    client.circuit.last_failure_time = time.time() - 1.0  # Timeout expired

    # Should allow one test request
    mock_response_data = {"response": "Success", "done": True}
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_response_data)

    with patch.object(client, '_get_session') as mock_session:
        mock_session.return_value.post = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        result = await client.complete("Test")

    # Circuit should be closed after successful request
    assert client.circuit.state == CircuitState.CLOSED


@pytest.mark.asyncio
async def test_circuit_breaker_closes_on_success():
    """Test circuit breaker closes after successful request in half-open state"""
    if OllamaClient is None or CircuitState is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()
    client.circuit.state = CircuitState.HALF_OPEN

    mock_response_data = {"response": "Success", "done": True}
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=mock_response_data)

    with patch.object(client, '_get_session') as mock_session:
        mock_session.return_value.post = AsyncMock(
            return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response))
        )
        await client.complete("Test")

    assert client.circuit.state == CircuitState.CLOSED
    assert client.circuit.failure_count == 0


# ============================================================================
# RETRY TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_retry_on_transient_error():
    """Test retries on 503 Service Unavailable"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient(max_retries=3)

    # First two calls fail with 503, third succeeds
    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            mock_resp = AsyncMock()
            mock_resp.status = 503
            mock_resp.raise_for_status = Mock(side_effect=aiohttp.ClientResponseError(
                request_info=Mock(), history=(), status=503
            ))
            return AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))
        else:
            mock_resp = AsyncMock()
            mock_resp.status = 200
            mock_resp.json = AsyncMock(return_value={"response": "Success", "done": True})
            return AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))

    with patch.object(client, '_get_session') as mock_session:
        mock_session.return_value.post = mock_post
        result = await client.complete("Test")

    assert call_count == 3
    assert result == "Success"


@pytest.mark.asyncio
async def test_no_retry_on_4xx():
    """Test no retry for client errors (4xx)"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient(max_retries=3)

    call_count = 0

    async def mock_post(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        mock_resp = AsyncMock()
        mock_resp.status = 400
        mock_resp.raise_for_status = Mock(side_effect=aiohttp.ClientResponseError(
            request_info=Mock(), history=(), status=400, message="Bad Request"
        ))
        return AsyncMock(__aenter__=AsyncMock(return_value=mock_resp))

    with patch.object(client, '_get_session') as mock_session:
        mock_session.return_value.post = mock_post

        with pytest.raises(aiohttp.ClientResponseError):
            await client.complete("Test")

    # Should only be called once (no retry)
    assert call_count == 1


# ============================================================================
# COST CALCULATION TESTS
# ============================================================================

def test_calculate_cost_always_zero():
    """Test cost calculation always returns $0 for local inference"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    cost = client.calculate_cost(input_tokens=1000, output_tokens=500)

    assert cost == 0.0


def test_calculate_cost_large_tokens_still_zero():
    """Test cost is $0 even for large token counts"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    # Even with massive token counts, local inference is free
    cost = client.calculate_cost(input_tokens=1000000, output_tokens=500000)

    assert cost == 0.0


# ============================================================================
# SESSION MANAGEMENT TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_session_reuse():
    """Test HTTP session is reused across requests"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    session1 = await client._get_session()
    session2 = await client._get_session()

    assert session1 is session2


@pytest.mark.asyncio
async def test_close_session():
    """Test session is properly closed"""
    if OllamaClient is None:
        pytest.skip("OllamaClient not implemented yet")

    client = OllamaClient()

    # Create session
    session = await client._get_session()
    assert client._session is not None

    # Close session
    await client.close()

    # Verify closed
    assert client._session is None or client._session.closed
