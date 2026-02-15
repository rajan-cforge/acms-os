"""Unit tests for ClaudeGenerator.

Tests Claude API integration including streaming functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.generation.claude_generator import ClaudeGenerator


@pytest.fixture
def claude_generator():
    """Create ClaudeGenerator instance with mocked Anthropic client."""
    with patch('src.generation.claude_generator.AsyncAnthropic') as mock_anthropic:
        # Mock Anthropic client
        mock_client = AsyncMock()
        mock_anthropic.return_value = mock_client

        generator = ClaudeGenerator()
        generator.client = mock_client

        yield generator


class TestClaudeGeneratorStreaming:
    """Test generate_stream() method for SSE streaming."""

    @pytest.mark.asyncio
    async def test_generate_stream_yields_chunks(self, claude_generator):
        """Test that generate_stream() yields text chunks."""
        # Mock streaming response
        mock_chunk1 = MagicMock()
        mock_chunk1.type = "content_block_delta"
        mock_chunk1.delta = MagicMock()
        mock_chunk1.delta.type = "text_delta"
        mock_chunk1.delta.text = "Hello "

        mock_chunk2 = MagicMock()
        mock_chunk2.type = "content_block_delta"
        mock_chunk2.delta = MagicMock()
        mock_chunk2.delta.type = "text_delta"
        mock_chunk2.delta.text = "world!"

        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = [mock_chunk1, mock_chunk2]

        # Mock Anthropic messages.create to return stream
        claude_generator.client.messages.create = AsyncMock(return_value=mock_stream)

        # Test streaming
        chunks = []
        async for chunk in claude_generator.generate_stream(
            prompt="Test prompt",
            max_tokens=100
        ):
            chunks.append(chunk)

        assert len(chunks) == 2
        assert chunks[0] == "Hello "
        assert chunks[1] == "world!"
        assert "".join(chunks) == "Hello world!"

    @pytest.mark.asyncio
    async def test_generate_stream_with_context(self, claude_generator):
        """Test that generate_stream() accepts context parameter."""
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = []
        claude_generator.client.messages.create = AsyncMock(return_value=mock_stream)

        chunks = []
        async for chunk in claude_generator.generate_stream(
            prompt="What is JWT?",
            context="Previous discussion about authentication",
            max_tokens=100
        ):
            chunks.append(chunk)

        # Verify messages.create was called
        assert claude_generator.client.messages.create.called

    @pytest.mark.asyncio
    async def test_generate_stream_handles_empty_response(self, claude_generator):
        """Test that generate_stream() handles empty streaming response."""
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = []
        claude_generator.client.messages.create = AsyncMock(return_value=mock_stream)

        chunks = []
        async for chunk in claude_generator.generate_stream(
            prompt="Test",
            max_tokens=100
        ):
            chunks.append(chunk)

        assert chunks == []

    @pytest.mark.asyncio
    async def test_generate_stream_filters_non_text_deltas(self, claude_generator):
        """Test that generate_stream() only yields text deltas."""
        # Mock mixed response (text + non-text chunks)
        mock_chunk1 = MagicMock()
        mock_chunk1.type = "content_block_start"  # Non-text

        mock_chunk2 = MagicMock()
        mock_chunk2.type = "content_block_delta"
        mock_chunk2.delta = MagicMock()
        mock_chunk2.delta.type = "text_delta"
        mock_chunk2.delta.text = "Hello"

        mock_chunk3 = MagicMock()
        mock_chunk3.type = "message_stop"  # Non-text

        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = [mock_chunk1, mock_chunk2, mock_chunk3]
        claude_generator.client.messages.create = AsyncMock(return_value=mock_stream)

        chunks = []
        async for chunk in claude_generator.generate_stream(
            prompt="Test",
            max_tokens=100
        ):
            chunks.append(chunk)

        # Should only yield the text delta
        assert len(chunks) == 1
        assert chunks[0] == "Hello"

    @pytest.mark.asyncio
    async def test_generate_stream_uses_correct_model(self, claude_generator):
        """Test that generate_stream() uses claude-3-7-sonnet model."""
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = []
        claude_generator.client.messages.create = AsyncMock(return_value=mock_stream)

        async for _ in claude_generator.generate_stream(
            prompt="Test",
            max_tokens=100
        ):
            pass

        # Verify correct model was used
        call_kwargs = claude_generator.client.messages.create.call_args[1]
        assert call_kwargs["model"] == "claude-3-7-sonnet-20250219"

    @pytest.mark.asyncio
    async def test_generate_stream_passes_max_tokens(self, claude_generator):
        """Test that generate_stream() respects max_tokens parameter."""
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = []
        claude_generator.client.messages.create = AsyncMock(return_value=mock_stream)

        async for _ in claude_generator.generate_stream(
            prompt="Test",
            max_tokens=500
        ):
            pass

        # Verify max_tokens was passed
        call_kwargs = claude_generator.client.messages.create.call_args[1]
        assert call_kwargs["max_tokens"] == 500

    @pytest.mark.asyncio
    async def test_generate_stream_sets_stream_true(self, claude_generator):
        """Test that generate_stream() enables streaming in API call."""
        mock_stream = AsyncMock()
        mock_stream.__aiter__.return_value = []
        claude_generator.client.messages.create = AsyncMock(return_value=mock_stream)

        async for _ in claude_generator.generate_stream(
            prompt="Test",
            max_tokens=100
        ):
            pass

        # Verify stream=True was set
        call_kwargs = claude_generator.client.messages.create.call_args[1]
        assert call_kwargs["stream"] is True


class TestClaudeGeneratorErrorHandling:
    """Test error handling in generate_stream()."""

    @pytest.mark.asyncio
    async def test_generate_stream_handles_api_error(self, claude_generator):
        """Test that generate_stream() handles Anthropic API errors gracefully."""
        # Mock API error
        claude_generator.client.messages.create = AsyncMock(
            side_effect=Exception("API rate limit exceeded")
        )

        # Should raise exception (or yield error message depending on implementation)
        with pytest.raises(Exception) as exc_info:
            async for _ in claude_generator.generate_stream(
                prompt="Test",
                max_tokens=100
            ):
                pass

        assert "API rate limit exceeded" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_stream_handles_network_error(self, claude_generator):
        """Test that generate_stream() handles network errors."""
        claude_generator.client.messages.create = AsyncMock(
            side_effect=ConnectionError("Network unreachable")
        )

        with pytest.raises(ConnectionError):
            async for _ in claude_generator.generate_stream(
                prompt="Test",
                max_tokens=100
            ):
                pass


class TestClaudeGeneratorExistingMethods:
    """Test existing generate() method still works."""

    @pytest.mark.asyncio
    async def test_generate_method_exists(self, claude_generator):
        """Test that original generate() method still exists."""
        # Mock non-streaming response
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Test response"

        claude_generator.client.messages.create = AsyncMock(return_value=mock_response)

        response = await claude_generator.generate(
            prompt="Test",
            max_tokens=100
        )

        assert response == "Test response"

    @pytest.mark.asyncio
    async def test_generate_with_history_exists(self, claude_generator):
        """Test that generate_with_history() method still exists."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Test response"

        claude_generator.client.messages.create = AsyncMock(return_value=mock_response)

        response = await claude_generator.generate_with_history(
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=100
        )

        assert response == "Test response"
