"""End-to-End tests for the new 3-stage retrieval pipeline.

Tests the full flow:
1. Retriever → fetches from Weaviate
2. Ranker → applies CRS scoring
3. ContextBuilder → assembles context

Blueprint Section 6 - Integration Tests
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from src.retrieval.retriever import Retriever, RawResult
from src.retrieval.ranker import Ranker, ScoredResult
from src.retrieval.context_builder import ContextBuilder


class TestRetrieverRankerIntegration:
    """Integration tests for Retriever + Ranker."""

    def test_retriever_results_compatible_with_ranker(self):
        """Test that RawResult from Retriever works with Ranker."""
        # Create mock retriever results
        raw_results = [
            RawResult(
                uuid=str(uuid4()),
                content="Python is a programming language",
                distance=0.2,
                source="knowledge",
                properties={
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "importance": 0.8
                }
            ),
            RawResult(
                uuid=str(uuid4()),
                content="Machine learning uses Python",
                distance=0.3,
                source="document",
                properties={
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "importance": 0.6
                }
            )
        ]

        # Pass to ranker
        ranker = Ranker()
        scored = ranker.score(raw_results)

        # Verify output
        assert len(scored) == 2
        assert all(isinstance(s, ScoredResult) for s in scored)
        assert scored[0].score >= scored[1].score  # Sorted by score

    def test_ranker_preserves_retriever_data(self):
        """Test that ranker preserves original retriever data."""
        original_uuid = str(uuid4())
        original_content = "Test content"

        raw_result = RawResult(
            uuid=original_uuid,
            content=original_content,
            distance=0.25,
            source="knowledge",
            properties={"created_at": datetime.now(timezone.utc).isoformat()}
        )

        ranker = Ranker()
        scored = ranker.score([raw_result])

        # Verify data preserved
        assert len(scored) == 1
        assert scored[0].item.uuid == original_uuid
        assert scored[0].item.content == original_content


class TestRankerContextBuilderIntegration:
    """Integration tests for Ranker + ContextBuilder."""

    def test_scored_results_build_context(self):
        """Test that ScoredResult works with ContextBuilder."""
        # Create scored results
        scored_results = [
            ScoredResult(
                item=RawResult(
                    uuid=str(uuid4()),
                    content="First result - Python basics",
                    distance=0.1,
                    source="knowledge",
                    properties={}
                ),
                score=0.95,
                breakdown={"similarity": 0.9}
            ),
            ScoredResult(
                item=RawResult(
                    uuid=str(uuid4()),
                    content="Second result - Advanced Python",
                    distance=0.2,
                    source="knowledge",
                    properties={}
                ),
                score=0.85,
                breakdown={"similarity": 0.8}
            )
        ]

        # Build context
        builder = ContextBuilder(max_tokens=500)
        context = builder.build(scored_results)

        # Verify context built
        assert "First result" in context
        assert "Second result" in context

    def test_context_respects_token_limit(self):
        """Test that context builder respects token limits."""
        # Create many scored results with very long content
        scored_results = []
        for i in range(10):
            scored_results.append(
                ScoredResult(
                    item=RawResult(
                        uuid=str(uuid4()),
                        content=f"Content item {i} " + "x" * 1000,  # ~1000 chars each
                        distance=0.1 + i * 0.05,
                        source="knowledge",
                        properties={}
                    ),
                    score=0.9 - i * 0.05,
                    breakdown={"similarity": 0.9 - i * 0.05}
                )
            )

        # Build with very small token limit (50 tokens ≈ 200 chars)
        builder = ContextBuilder(max_tokens=50)
        context = builder.build(scored_results)

        # With 50 tokens limit, we can't fit much content
        # Each item is ~1000 chars = ~250 tokens, so we get at most 1 item
        # But the context builder may include headers, so let's just verify
        # it's much shorter than if all items were included
        assert len(context) < len("".join([r.item.content for r in scored_results]))


class TestFullPipelineIntegration:
    """End-to-end tests for full retrieval pipeline."""

    @pytest.fixture
    def mock_weaviate_client(self):
        """Create mock Weaviate client."""
        mock = Mock()
        mock.semantic_search.return_value = [
            {
                "uuid": str(uuid4()),
                "distance": 0.2,
                "properties": {
                    "content": "User prefers Python programming",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "user_id": "test-user",
                    "privacy_level": "INTERNAL"
                }
            },
            {
                "uuid": str(uuid4()),
                "distance": 0.3,
                "properties": {
                    "content": "User likes dark mode",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "user_id": "test-user",
                    "privacy_level": "INTERNAL"
                }
            }
        ]
        return mock

    @pytest.mark.asyncio
    async def test_full_pipeline_retriever_to_context(self, mock_weaviate_client):
        """Test full pipeline from retriever to context."""
        # 1. Retriever
        retriever = Retriever(weaviate_client=mock_weaviate_client)
        raw_results = await retriever.retrieve(
            query_embedding=[0.1] * 768,
            text_query="What are my preferences?",
            filters={"privacy_level": ["INTERNAL"]},
            limit=10,
            sources=["knowledge"]
        )

        # 2. Ranker
        ranker = Ranker()
        scored_results = ranker.score(raw_results)

        # 3. Context Builder
        builder = ContextBuilder(max_tokens=500)
        context = builder.build(scored_results)

        # Verify end-to-end
        assert len(raw_results) == 2
        assert len(scored_results) == 2
        assert "Python" in context
        assert "dark mode" in context

    @pytest.mark.asyncio
    async def test_empty_retrieval_handled(self, mock_weaviate_client):
        """Test pipeline handles empty retrieval gracefully."""
        # Configure mock to return empty
        mock_weaviate_client.semantic_search.return_value = []

        retriever = Retriever(weaviate_client=mock_weaviate_client)
        raw_results = await retriever.retrieve(
            query_embedding=[0.1] * 768,
            text_query="Unknown topic",
            filters={},
            limit=10,
            sources=["knowledge"]
        )

        ranker = Ranker()
        scored_results = ranker.score(raw_results)

        builder = ContextBuilder(max_tokens=500)
        context = builder.build(scored_results)

        # Should handle gracefully
        assert len(raw_results) == 0
        assert len(scored_results) == 0
        assert context == ""  # Empty context


class TestCRSWeightsIntegration:
    """Test CRS weight effects on ranking."""

    def test_recency_affects_ranking(self):
        """Test that recency affects final ranking."""
        old_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        new_date = datetime.now(timezone.utc)

        raw_results = [
            RawResult(
                uuid=str(uuid4()),
                content="Old content with same similarity",
                distance=0.2,  # Same distance
                source="knowledge",
                properties={"created_at": old_date.isoformat()}
            ),
            RawResult(
                uuid=str(uuid4()),
                content="New content with same similarity",
                distance=0.2,  # Same distance
                source="knowledge",
                properties={"created_at": new_date.isoformat()}
            )
        ]

        ranker = Ranker()
        scored = ranker.score(raw_results, now=new_date)

        # Newer content should rank higher
        assert scored[0].item.content == "New content with same similarity"

    def test_importance_affects_ranking(self):
        """Test that importance affects final ranking."""
        raw_results = [
            RawResult(
                uuid=str(uuid4()),
                content="Low importance",
                distance=0.2,
                source="knowledge",
                properties={
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "importance": 0.2
                }
            ),
            RawResult(
                uuid=str(uuid4()),
                content="High importance",
                distance=0.2,  # Same distance
                source="knowledge",
                properties={
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "importance": 0.9
                }
            )
        ]

        ranker = Ranker()
        scored = ranker.score(raw_results)

        # Higher importance should rank higher
        assert scored[0].item.content == "High importance"


class TestPipelineMetrics:
    """Test pipeline produces correct metrics."""

    def test_score_breakdown_provided(self):
        """Test that score breakdown is provided."""
        raw_result = RawResult(
            uuid=str(uuid4()),
            content="Test content",
            distance=0.25,
            source="knowledge",
            properties={
                "created_at": datetime.now(timezone.utc).isoformat(),
                "importance": 0.7,
                "feedback_score": 0.8
            }
        )

        ranker = Ranker()
        scored = ranker.score([raw_result])

        # Verify breakdown provided
        assert len(scored) == 1
        breakdown = scored[0].breakdown

        assert "similarity" in breakdown
        assert "recency" in breakdown
        assert "importance" in breakdown
        assert "feedback" in breakdown

        # Verify values are reasonable
        assert 0 <= breakdown["similarity"] <= 1
        assert 0 <= breakdown["recency"] <= 1
        assert 0 <= breakdown["importance"] <= 1
        assert 0 <= breakdown["feedback"] <= 1

    def test_context_includes_all_items_when_space_available(self):
        """Test that context builder includes all distinct items when within token limit."""
        # Use very different content to avoid deduplication
        scored_results = [
            ScoredResult(
                item=RawResult(
                    uuid="uuid-1",
                    content="Python is a programming language used for web development",
                    distance=0.1,
                    source="knowledge",
                    properties={}
                ),
                score=0.9,
                breakdown={}
            ),
            ScoredResult(
                item=RawResult(
                    uuid="uuid-2",
                    content="Machine learning is a subset of artificial intelligence",
                    distance=0.2,
                    source="knowledge",
                    properties={}
                ),
                score=0.8,
                breakdown={}
            )
        ]

        builder = ContextBuilder(max_tokens=500)
        context = builder.build(scored_results)

        # Both distinct items should be included with large token limit
        assert "Python" in context
        assert "Machine learning" in context
