"""Tests for Memory Service - TDD: Write tests FIRST.

Phase 1: Memory Service
Goal: Single interface for all memory operations with idempotency

Run with: PYTHONPATH=. pytest tests/unit/memory/test_memory_service.py -v
"""
import pytest
from uuid import uuid4
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import hashlib

from src.memory.models import MemoryType, MemoryTier, PrivacyLevel, MemoryItem
from src.memory.memory_service import MemoryService


class TestMemoryServiceInit:
    """Test Memory Service initialization."""

    def test_service_initializes(self):
        """Service should initialize without errors."""
        # Use mocks to avoid real DB/Weaviate connections
        with patch('src.memory.memory_service.WeaviateClient'):
            with patch('src.memory.memory_service.OpenAIEmbeddings'):
                service = MemoryService()
                assert service is not None


class TestContentHashing:
    """Test content hashing for idempotency/deduplication."""

    def test_same_content_same_hash(self):
        """Same content should produce same hash."""
        with patch('src.memory.memory_service.WeaviateClient'):
            with patch('src.memory.memory_service.OpenAIEmbeddings'):
                service = MemoryService()

                hash1 = service._compute_hash("Test content")
                hash2 = service._compute_hash("Test content")

                assert hash1 == hash2

    def test_different_content_different_hash(self):
        """Different content should produce different hash."""
        with patch('src.memory.memory_service.WeaviateClient'):
            with patch('src.memory.memory_service.OpenAIEmbeddings'):
                service = MemoryService()

                hash1 = service._compute_hash("Content A")
                hash2 = service._compute_hash("Content B")

                assert hash1 != hash2

    def test_hash_is_sha256(self):
        """Hash should be SHA256 (64 hex chars)."""
        with patch('src.memory.memory_service.WeaviateClient'):
            with patch('src.memory.memory_service.OpenAIEmbeddings'):
                service = MemoryService()

                hash_result = service._compute_hash("Test")

                assert len(hash_result) == 64
                assert all(c in '0123456789abcdef' for c in hash_result)


class TestCollectionMapping:
    """Test memory type to collection mapping."""

    def test_episodic_maps_to_raw(self):
        """EPISODIC should map to ACMS_Raw_v1."""
        with patch('src.memory.memory_service.WeaviateClient'):
            with patch('src.memory.memory_service.OpenAIEmbeddings'):
                service = MemoryService()
                assert service._get_collection(MemoryType.EPISODIC) == "ACMS_Raw_v1"

    def test_semantic_maps_to_knowledge(self):
        """SEMANTIC should map to ACMS_Knowledge_v1."""
        with patch('src.memory.memory_service.WeaviateClient'):
            with patch('src.memory.memory_service.OpenAIEmbeddings'):
                service = MemoryService()
                assert service._get_collection(MemoryType.SEMANTIC) == "ACMS_Knowledge_v1"

    def test_cache_entry_maps_to_enriched(self):
        """CACHE_ENTRY should map to ACMS_Enriched_v1."""
        with patch('src.memory.memory_service.WeaviateClient'):
            with patch('src.memory.memory_service.OpenAIEmbeddings'):
                service = MemoryService()
                assert service._get_collection(MemoryType.CACHE_ENTRY) == "ACMS_Enriched_v1"

    def test_document_maps_to_memory_items(self):
        """DOCUMENT should map to ACMS_MemoryItems_v1."""
        with patch('src.memory.memory_service.WeaviateClient'):
            with patch('src.memory.memory_service.OpenAIEmbeddings'):
                service = MemoryService()
                assert service._get_collection(MemoryType.DOCUMENT) == "ACMS_MemoryItems_v1"


class TestCreateMemory:
    """Test memory creation with idempotency."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked dependencies."""
        with patch('src.memory.memory_service.WeaviateClient') as mock_weaviate:
            with patch('src.memory.memory_service.OpenAIEmbeddings') as mock_embeddings:
                # Setup mock embedding
                mock_embeddings_instance = MagicMock()
                mock_embeddings_instance.generate_embedding.return_value = [0.1] * 768
                mock_embeddings.return_value = mock_embeddings_instance

                # Setup mock weaviate
                mock_weaviate_instance = MagicMock()
                mock_weaviate_instance.insert_vector.return_value = "vector-uuid-123"
                mock_weaviate_instance.semantic_search.return_value = []
                mock_weaviate.return_value = mock_weaviate_instance

                service = MemoryService()
                service._weaviate = mock_weaviate_instance
                service._embeddings = mock_embeddings_instance

                yield service

    @pytest.mark.asyncio
    async def test_create_returns_memory_with_id(self, mock_service):
        """Create should return memory with generated ID."""
        item = MemoryItem(
            user_id=uuid4(),
            content="Test memory content",
            memory_type=MemoryType.SEMANTIC
        )

        # Mock no existing memory (not a duplicate)
        mock_service._find_by_hash = AsyncMock(return_value=None)
        mock_service._store_in_db = AsyncMock(return_value=True)

        result = await mock_service.create_memory(item)

        assert result is not None
        assert result.memory_id is not None
        assert result.content == "Test memory content"

    @pytest.mark.asyncio
    async def test_create_is_idempotent(self, mock_service):
        """Creating same content twice returns existing memory."""
        user_id = uuid4()
        item = MemoryItem(
            user_id=user_id,
            content="Duplicate content",
            memory_type=MemoryType.SEMANTIC
        )

        # First call: no existing
        mock_service._find_by_hash = AsyncMock(return_value=None)
        mock_service._store_in_db = AsyncMock(return_value=True)

        result1 = await mock_service.create_memory(item)
        first_id = result1.memory_id

        # Second call: return existing
        existing = MemoryItem(
            memory_id=first_id,
            user_id=user_id,
            content="Duplicate content",
            memory_type=MemoryType.SEMANTIC
        )
        mock_service._find_by_hash = AsyncMock(return_value=existing)

        result2 = await mock_service.create_memory(item)

        # Should return same ID (idempotent!)
        assert result2.memory_id == first_id

    @pytest.mark.asyncio
    async def test_create_generates_embedding(self, mock_service):
        """Create should generate embedding for content."""
        item = MemoryItem(
            user_id=uuid4(),
            content="Content to embed",
            memory_type=MemoryType.SEMANTIC
        )

        mock_service._find_by_hash = AsyncMock(return_value=None)
        mock_service._store_in_db = AsyncMock(return_value=True)

        await mock_service.create_memory(item)

        # Verify embedding was generated
        mock_service._embeddings.generate_embedding.assert_called_once_with("Content to embed")

    @pytest.mark.asyncio
    async def test_create_stores_in_correct_collection(self, mock_service):
        """SEMANTIC memory should go to ACMS_Knowledge_v1."""
        item = MemoryItem(
            user_id=uuid4(),
            content="User fact",
            memory_type=MemoryType.SEMANTIC
        )

        mock_service._find_by_hash = AsyncMock(return_value=None)
        mock_service._store_in_db = AsyncMock(return_value=True)

        await mock_service.create_memory(item)

        # Verify stored in correct collection
        mock_service._weaviate.insert_vector.assert_called_once()
        call_args = mock_service._weaviate.insert_vector.call_args
        assert call_args[1]['collection'] == "ACMS_Knowledge_v1"


class TestGetMemory:
    """Test memory retrieval."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked dependencies."""
        with patch('src.memory.memory_service.WeaviateClient') as mock_weaviate:
            with patch('src.memory.memory_service.OpenAIEmbeddings') as mock_embeddings:
                mock_embeddings_instance = MagicMock()
                mock_weaviate_instance = MagicMock()

                service = MemoryService()
                service._weaviate = mock_weaviate_instance
                service._embeddings = mock_embeddings_instance

                yield service

    @pytest.mark.asyncio
    async def test_get_returns_none_for_missing(self, mock_service):
        """Get non-existent memory returns None."""
        mock_service._fetch_from_db = AsyncMock(return_value=None)

        result = await mock_service.get_memory(str(uuid4()))

        assert result is None

    @pytest.mark.asyncio
    async def test_get_returns_memory_item(self, mock_service):
        """Get existing memory returns MemoryItem."""
        memory_id = uuid4()
        expected = MemoryItem(
            memory_id=memory_id,
            user_id=uuid4(),
            content="Test content",
            memory_type=MemoryType.SEMANTIC
        )

        mock_service._fetch_from_db = AsyncMock(return_value=expected)

        result = await mock_service.get_memory(str(memory_id))

        assert result is not None
        assert result.memory_id == memory_id
        assert result.content == "Test content"


class TestDeleteMemory:
    """Test memory deletion with idempotency."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked dependencies."""
        with patch('src.memory.memory_service.WeaviateClient') as mock_weaviate:
            with patch('src.memory.memory_service.OpenAIEmbeddings') as mock_embeddings:
                mock_weaviate_instance = MagicMock()

                service = MemoryService()
                service._weaviate = mock_weaviate_instance

                yield service

    @pytest.mark.asyncio
    async def test_delete_existing_returns_true(self, mock_service):
        """Deleting existing memory returns True."""
        memory_id = str(uuid4())

        mock_service._fetch_from_db = AsyncMock(return_value=MemoryItem(
            memory_id=uuid4(),
            user_id=uuid4(),
            content="To delete",
            memory_type=MemoryType.SEMANTIC
        ))
        mock_service._delete_from_db = AsyncMock(return_value=True)

        result = await mock_service.delete_memory(memory_id)

        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_true(self, mock_service):
        """Deleting non-existent memory returns True (idempotent)."""
        mock_service._fetch_from_db = AsyncMock(return_value=None)

        result = await mock_service.delete_memory(str(uuid4()))

        # Idempotent: deleting non-existent is still "success"
        assert result is True


class TestSearchMemories:
    """Test memory search functionality."""

    @pytest.fixture
    def mock_service(self):
        """Create service with mocked dependencies."""
        with patch('src.memory.memory_service.WeaviateClient') as mock_weaviate:
            with patch('src.memory.memory_service.OpenAIEmbeddings') as mock_embeddings:
                mock_embeddings_instance = MagicMock()
                mock_embeddings_instance.generate_embedding.return_value = [0.1] * 768
                mock_embeddings.return_value = mock_embeddings_instance

                mock_weaviate_instance = MagicMock()
                mock_weaviate.return_value = mock_weaviate_instance

                service = MemoryService()
                service._weaviate = mock_weaviate_instance
                service._embeddings = mock_embeddings_instance

                yield service

    @pytest.mark.asyncio
    async def test_search_returns_list(self, mock_service):
        """Search should return list of results."""
        mock_service._weaviate.semantic_search.return_value = [
            {
                "uuid": str(uuid4()),
                "distance": 0.1,
                "properties": {
                    "content": "Result 1",
                    "memory_type": "SEMANTIC",
                    "user_id": str(uuid4())
                }
            }
        ]

        results = await mock_service.search_memories(
            query="test query",
            user_id=str(uuid4()),
            limit=10
        )

        assert isinstance(results, list)
        assert len(results) >= 0

    @pytest.mark.asyncio
    async def test_search_filters_by_user(self, mock_service):
        """Search should filter results by user_id."""
        user_id = str(uuid4())
        other_user = str(uuid4())

        mock_service._weaviate.semantic_search.return_value = [
            {
                "uuid": str(uuid4()),
                "distance": 0.1,
                "properties": {"content": "Mine", "user_id": user_id, "memory_type": "SEMANTIC"}
            },
            {
                "uuid": str(uuid4()),
                "distance": 0.2,
                "properties": {"content": "Other's", "user_id": other_user, "memory_type": "SEMANTIC"}
            }
        ]

        results = await mock_service.search_memories(
            query="test",
            user_id=user_id,
            limit=10
        )

        # Should only return user's memories
        for r in results:
            assert r.get("user_id") == user_id or r.get("properties", {}).get("user_id") == user_id

    @pytest.mark.asyncio
    async def test_search_respects_limit(self, mock_service):
        """Search should respect limit parameter."""
        # Return more results than limit
        mock_service._weaviate.semantic_search.return_value = [
            {"uuid": str(uuid4()), "distance": 0.1, "properties": {"content": f"Result {i}", "user_id": str(uuid4()), "memory_type": "SEMANTIC"}}
            for i in range(20)
        ]

        results = await mock_service.search_memories(
            query="test",
            user_id=str(uuid4()),
            limit=5
        )

        assert len(results) <= 5
