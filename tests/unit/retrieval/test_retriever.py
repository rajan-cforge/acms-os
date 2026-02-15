"""Tests for Retriever - Stage 1 of retrieval pipeline.

TDD: Write tests FIRST, then implement.

Run with: PYTHONPATH=. pytest tests/unit/retrieval/test_retriever.py -v
"""
import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import uuid4

from src.retrieval.retriever import Retriever, RawResult


class TestRawResult:
    """Test RawResult dataclass."""

    def test_raw_result_has_required_fields(self):
        """RawResult should have uuid, content, distance, source, properties."""
        result = RawResult(
            uuid="test-uuid",
            content="Test content",
            distance=0.15,
            source="knowledge",
            properties={"user_id": "user-123"}
        )

        assert result.uuid == "test-uuid"
        assert result.content == "Test content"
        assert result.distance == 0.15
        assert result.source == "knowledge"

    def test_similarity_property(self):
        """Similarity should be 1.0 - distance."""
        result = RawResult(
            uuid="1",
            content="test",
            distance=0.2,
            source="vec",
            properties={}
        )

        assert result.similarity == 0.8


class TestRetrieverInit:
    """Test Retriever initialization."""

    def test_retriever_initializes(self):
        """Retriever should initialize with default client."""
        with patch('src.retrieval.retriever.WeaviateClient'):
            retriever = Retriever()
            assert retriever is not None

    def test_retriever_accepts_custom_client(self):
        """Retriever should accept custom Weaviate client."""
        mock_client = Mock()
        retriever = Retriever(weaviate_client=mock_client)
        assert retriever._weaviate == mock_client


class TestRetrieverRetrieve:
    """Test Retriever.retrieve() method."""

    @pytest.fixture
    def mock_retriever(self):
        """Create retriever with mocked Weaviate."""
        mock_weaviate = MagicMock()
        mock_weaviate.semantic_search.return_value = [
            {
                "uuid": str(uuid4()),
                "distance": 0.1,
                "properties": {
                    "content": "Result 1",
                    "user_id": "user-123",
                    "memory_type": "SEMANTIC",
                    "privacy_level": "INTERNAL"
                }
            },
            {
                "uuid": str(uuid4()),
                "distance": 0.2,
                "properties": {
                    "content": "Result 2",
                    "user_id": "user-123",
                    "memory_type": "SEMANTIC",
                    "privacy_level": "PUBLIC"
                }
            }
        ]

        retriever = Retriever(weaviate_client=mock_weaviate)
        return retriever

    @pytest.mark.asyncio
    async def test_retrieve_returns_raw_results(self, mock_retriever):
        """Retrieve should return list of RawResult objects."""
        results = await mock_retriever.retrieve(
            query_embedding=[0.1] * 768,
            text_query="test query",
            filters={"user_id": "user-123"},
            limit=10
        )

        assert isinstance(results, list)
        assert all(isinstance(r, RawResult) for r in results)

    @pytest.mark.asyncio
    async def test_retrieve_empty_query_returns_empty(self, mock_retriever):
        """Empty query should return empty results."""
        results = await mock_retriever.retrieve(
            query_embedding=[],
            text_query="",
            filters={},
            limit=10
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_retrieve_filters_by_user(self, mock_retriever):
        """Results should be filtered by user_id."""
        # Add result from different user
        mock_retriever._weaviate.semantic_search.return_value.append({
            "uuid": str(uuid4()),
            "distance": 0.05,
            "properties": {
                "content": "Other user's content",
                "user_id": "other-user",
                "memory_type": "SEMANTIC",
                "privacy_level": "INTERNAL"
            }
        })

        results = await mock_retriever.retrieve(
            query_embedding=[0.1] * 768,
            text_query="test",
            filters={"user_id": "user-123"},
            limit=10
        )

        # Should only have user-123's results
        for r in results:
            assert r.properties.get("user_id") == "user-123"

    @pytest.mark.asyncio
    async def test_retrieve_filters_by_privacy(self, mock_retriever):
        """Results should be filtered by privacy_level."""
        results = await mock_retriever.retrieve(
            query_embedding=[0.1] * 768,
            text_query="test",
            filters={
                "user_id": "user-123",
                "privacy_level": ["PUBLIC"]  # Only PUBLIC
            },
            limit=10
        )

        # Should only have PUBLIC results
        for r in results:
            assert r.properties.get("privacy_level") == "PUBLIC"

    @pytest.mark.asyncio
    async def test_retrieve_respects_limit(self, mock_retriever):
        """Results should respect limit parameter."""
        results = await mock_retriever.retrieve(
            query_embedding=[0.1] * 768,
            text_query="test",
            filters={"user_id": "user-123"},
            limit=1
        )

        assert len(results) <= 1

    @pytest.mark.asyncio
    async def test_retrieve_searches_multiple_collections(self, mock_retriever):
        """Should search specified collections."""
        await mock_retriever.retrieve(
            query_embedding=[0.1] * 768,
            text_query="test",
            filters={"user_id": "user-123"},
            limit=10,
            sources=["knowledge", "enriched"]
        )

        # Should have called semantic_search for each collection
        calls = mock_retriever._weaviate.semantic_search.call_args_list
        assert len(calls) >= 1


class TestCollectionMapping:
    """Test source to collection mapping."""

    def test_knowledge_source_maps_correctly(self):
        """'knowledge' should map to ACMS_Knowledge_v1."""
        mock_client = Mock()
        retriever = Retriever(weaviate_client=mock_client)

        assert retriever.COLLECTION_MAP["knowledge"] == "ACMS_Knowledge_v1"

    def test_enriched_source_maps_correctly(self):
        """'enriched' should map to ACMS_Enriched_v1."""
        mock_client = Mock()
        retriever = Retriever(weaviate_client=mock_client)

        assert retriever.COLLECTION_MAP["enriched"] == "ACMS_Enriched_v1"

    def test_raw_source_maps_correctly(self):
        """'raw' should map to ACMS_Raw_v1."""
        mock_client = Mock()
        retriever = Retriever(weaviate_client=mock_client)

        assert retriever.COLLECTION_MAP["raw"] == "ACMS_Raw_v1"
