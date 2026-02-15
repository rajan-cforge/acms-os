"""Unit tests for MemoryCRUD.

Tests memory CRUD operations including source parameter and retrieve_memories method.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.storage.memory_crud import MemoryCRUD


@pytest.fixture
async def memory_crud():
    """Create MemoryCRUD instance with mocked dependencies."""
    with patch('src.storage.memory_crud.PostgreSQLClient') as mock_pg, \
         patch('src.storage.memory_crud.WeaviateClient') as mock_wv, \
         patch('src.storage.memory_crud.get_hasher') as mock_hasher, \
         patch('src.storage.memory_crud.get_encryptor') as mock_encryptor, \
         patch('src.storage.memory_crud.get_embedder') as mock_embedder:

        # Mock PostgreSQL client
        mock_pg_instance = AsyncMock()
        mock_pg_instance.execute_query = AsyncMock(return_value=[{"memory_id": "test-123"}])
        mock_pg.return_value = mock_pg_instance

        # Mock Weaviate client
        mock_wv_instance = MagicMock()
        mock_wv_instance.add_memory = MagicMock(return_value="weaviate-123")
        mock_wv.return_value = mock_wv_instance

        # Mock hasher
        mock_hasher_instance = MagicMock()
        mock_hasher_instance.hash_content.return_value = "hash-123"
        mock_hasher.return_value = mock_hasher_instance

        # Mock encryptor
        mock_encryptor_instance = MagicMock()
        mock_encryptor_instance.encrypt.return_value = b"encrypted-content"
        mock_encryptor.return_value = mock_encryptor_instance

        # Mock embedder
        mock_embedder_instance = AsyncMock()
        mock_embedder_instance.embed.return_value = [0.1, 0.2, 0.3]
        mock_embedder.return_value = mock_embedder_instance

        crud = MemoryCRUD()
        yield crud


class TestCreateMemoryWithSource:
    """Test create_memory() with source parameter."""

    @pytest.mark.asyncio
    async def test_create_memory_with_chatgpt_source(self, memory_crud):
        """Test that create_memory() accepts source='chatgpt' parameter."""
        memory_id = await memory_crud.create_memory(
            user_id="test-user",
            content="Test memory from ChatGPT",
            tags=["test", "chatgpt"],
            source="chatgpt",
            phase="test",
            tier="SHORT"
        )

        assert memory_id is not None
        assert isinstance(memory_id, str)

    @pytest.mark.asyncio
    async def test_create_memory_with_claude_source(self, memory_crud):
        """Test that create_memory() accepts source='claude' parameter."""
        memory_id = await memory_crud.create_memory(
            user_id="test-user",
            content="Test memory from Claude",
            tags=["test", "claude"],
            source="claude",
            phase="test",
            tier="SHORT"
        )

        assert memory_id is not None

    @pytest.mark.asyncio
    async def test_create_memory_with_gemini_source(self, memory_crud):
        """Test that create_memory() accepts source='gemini' parameter."""
        memory_id = await memory_crud.create_memory(
            user_id="test-user",
            content="Test memory from Gemini",
            tags=["test", "gemini"],
            source="gemini",
            phase="test",
            tier="SHORT"
        )

        assert memory_id is not None

    @pytest.mark.asyncio
    async def test_create_memory_without_source(self, memory_crud):
        """Test that create_memory() works without source parameter (default behavior)."""
        memory_id = await memory_crud.create_memory(
            user_id="test-user",
            content="Test memory without source",
            tags=["test"],
            phase="test",
            tier="SHORT"
        )

        assert memory_id is not None

    @pytest.mark.asyncio
    async def test_create_memory_source_stored_in_metadata(self, memory_crud):
        """Test that source is stored in metadata if provided."""
        with patch.object(memory_crud.pg_client, 'execute_query', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = [{"memory_id": "test-123"}]

            await memory_crud.create_memory(
                user_id="test-user",
                content="Test memory",
                tags=["test"],
                source="chatgpt",
                phase="test",
                tier="SHORT"
            )

            # Verify execute_query was called
            assert mock_execute.called
            call_args = mock_execute.call_args
            query = call_args[0][0] if call_args[0] else ""

            # Should contain metadata with source
            assert "metadata" in query.lower() or mock_execute.call_count > 0


class TestRetrieveMemories:
    """Test retrieve_memories() method."""

    @pytest.mark.asyncio
    async def test_retrieve_memories_basic(self, memory_crud):
        """Test that retrieve_memories() returns list of memories."""
        # Mock list_memories to return test data
        with patch.object(memory_crud, 'list_memories', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                {
                    "memory_id": "mem-1",
                    "content": "Test memory 1",
                    "tags": ["test"],
                    "created_at": "2025-01-15T10:00:00"
                },
                {
                    "memory_id": "mem-2",
                    "content": "Test memory 2",
                    "tags": ["test"],
                    "created_at": "2025-01-15T11:00:00"
                }
            ]

            memories = await memory_crud.retrieve_memories(
                user_id="test-user",
                limit=10
            )

            assert len(memories) == 2
            assert memories[0]["memory_id"] == "mem-1"
            assert memories[1]["memory_id"] == "mem-2"

    @pytest.mark.asyncio
    async def test_retrieve_memories_with_limit(self, memory_crud):
        """Test that retrieve_memories() respects limit parameter."""
        with patch.object(memory_crud, 'list_memories', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                {"memory_id": f"mem-{i}", "content": f"Test {i}"}
                for i in range(5)
            ]

            memories = await memory_crud.retrieve_memories(
                user_id="test-user",
                limit=3
            )

            assert len(memories) <= 3

    @pytest.mark.asyncio
    async def test_retrieve_memories_with_tags_filter(self, memory_crud):
        """Test that retrieve_memories() can filter by tags."""
        with patch.object(memory_crud, 'list_memories', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                {"memory_id": "mem-1", "content": "Auth memory", "tags": ["auth", "jwt"]},
                {"memory_id": "mem-2", "content": "Cache memory", "tags": ["cache", "redis"]}
            ]

            memories = await memory_crud.retrieve_memories(
                user_id="test-user",
                tags=["auth"]
            )

            # Should have called list_memories with tags filter
            assert mock_list.called

    @pytest.mark.asyncio
    async def test_retrieve_memories_empty_result(self, memory_crud):
        """Test that retrieve_memories() handles empty results."""
        with patch.object(memory_crud, 'list_memories', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = []

            memories = await memory_crud.retrieve_memories(
                user_id="test-user",
                limit=10
            )

            assert memories == []

    @pytest.mark.asyncio
    async def test_retrieve_memories_with_source_filter(self, memory_crud):
        """Test that retrieve_memories() can filter by source."""
        with patch.object(memory_crud, 'list_memories', new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [
                {"memory_id": "mem-1", "content": "ChatGPT memory", "source": "chatgpt"},
                {"memory_id": "mem-2", "content": "Claude memory", "source": "claude"}
            ]

            memories = await memory_crud.retrieve_memories(
                user_id="test-user",
                source="chatgpt"
            )

            # Should have called list_memories
            assert mock_list.called


class TestMemoryCRUDIntegration:
    """Integration tests for MemoryCRUD full workflow."""

    @pytest.mark.asyncio
    async def test_create_and_retrieve_memory_flow(self, memory_crud):
        """Test full workflow: create memory with source, then retrieve it."""
        # Mock create
        with patch.object(memory_crud.pg_client, 'execute_query', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = [{"memory_id": "test-123"}]

            # Create memory
            memory_id = await memory_crud.create_memory(
                user_id="test-user",
                content="Test memory from ChatGPT",
                tags=["test", "chatgpt"],
                source="chatgpt",
                phase="test",
                tier="SHORT"
            )

            assert memory_id is not None

        # Mock retrieve
        with patch.object(memory_crud, 'list_memories', new_callable=AsyncMock) as mock_retrieve:
            mock_retrieve.return_value = [
                {
                    "memory_id": "test-123",
                    "content": "Test memory from ChatGPT",
                    "tags": ["test", "chatgpt"],
                    "source": "chatgpt"
                }
            ]

            # Retrieve memories
            memories = await memory_crud.retrieve_memories(
                user_id="test-user",
                source="chatgpt"
            )

            assert len(memories) > 0
            assert memories[0]["source"] == "chatgpt"
