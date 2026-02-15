"""Integration tests for memory_items → insights/reports data flow.

Validates that Chrome extension captures (memory_items) correctly flow
through topic extraction to appear in Insights and Reports.

Root cause being tested:
- Extensions create memory_items (95K entries)
- InsightsEngine previously ONLY queried query_history (389 entries)
- Fix: UNION queries that combine both sources via topic_extractions

Run with: pytest tests/integration/test_memory_insights_integration.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.intelligence.topic_extractor import (
    TopicExtractor,
    TopicExtractionResult,
    ExtractionMethod,
    ExtractableItem,
)
from src.intelligence.insights_engine import InsightsEngine
from src.intelligence.report_generator import ReportGenerator, KnowledgeGrowth


# Test constants
TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_TENANT_ID = "default"


class TestTopicExtractionDB:
    """Tests for topic extraction database functions."""

    @pytest.mark.asyncio
    async def test_save_extraction_for_memory_items(self):
        """Can save topic extraction for memory_items source type."""
        # Mock DB session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=MagicMock())
        mock_session.commit = AsyncMock()

        extractor = TopicExtractor(db_session=mock_session)

        result = TopicExtractionResult(
            topics=["kubernetes", "docker"],
            primary_topic="kubernetes",
            method=ExtractionMethod.KEYWORD,
            confidence=0.8,
            tokens_used=0,
            cached=False
        )

        # Save extraction - should use INSERT with ON CONFLICT
        await extractor._save_extraction(
            tenant_id=TEST_TENANT_ID,
            source_type="memory_items",  # Chrome extension source
            source_id=str(uuid4()),
            user_id=TEST_USER_ID,
            result=result,
            trace_id="test-trace"
        )

        # Verify execute was called with INSERT
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        sql = str(call_args[0][0])
        assert "INSERT INTO topic_extractions" in sql
        assert "ON CONFLICT" in sql
        assert "source_type" in sql

    @pytest.mark.asyncio
    async def test_get_cached_extraction_returns_hit(self):
        """Cache hit returns existing extraction."""
        # Mock DB session with cached result
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": str(uuid4()),
            "topics": ["python", "fastapi"],
            "primary_topic": "python",
            "extraction_method": "keyword",
            "extractor_version": "v1_keyword_20241115",
            "confidence": 0.8,
            "tokens_used": 0,
            "created_at": datetime.now()
        }

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        extractor = TopicExtractor(db_session=mock_session)

        cached = await extractor._get_cached_extraction(
            tenant_id=TEST_TENANT_ID,
            source_type="memory_items",
            source_id="test-memory-id"
        )

        assert cached is not None
        assert cached["topics"] == ["python", "fastapi"]
        assert cached["primary_topic"] == "python"

    @pytest.mark.asyncio
    async def test_batch_extract_memory_items(self):
        """Batch extraction processes memory_items correctly."""
        extractor = TopicExtractor(db_session=None, llm_provider=None)

        items = [
            ExtractableItem(
                source_type="memory_items",
                source_id=f"mem-{i}",
                text=f"Python is great for data science. Using pandas for analysis.",
                user_id=TEST_USER_ID,
                tenant_id=TEST_TENANT_ID
            )
            for i in range(3)
        ]

        result = await extractor.batch_extract(items, budget_usd=0.0)

        assert result.items_processed == 3
        assert len(result.results) == 3
        # Should find python-related topics
        all_topics = []
        for r in result.results:  # results is a List, not dict
            all_topics.extend(r.topics)
        assert "python" in all_topics


class TestInsightsEngineMemoryIntegration:
    """Tests for InsightsEngine memory_items queries."""

    @pytest.mark.asyncio
    async def test_get_key_stats_includes_memories(self):
        """Key stats include memories_captured from memory_items."""
        # Mock DB session with proper row structure
        mock_session = AsyncMock()

        # Mock first query (query_history stats) - returns tuple row
        stats_row = (100, 5.0, 2000, 'claude', 0.5)  # count, cost, latency, agent, cache_rate
        query_result = MagicMock()
        query_result.fetchone = MagicMock(return_value=stats_row)

        # Mock second query (memory count)
        memory_result = MagicMock()
        memory_result.fetchone = MagicMock(return_value=(5000,))

        mock_session.execute = AsyncMock(side_effect=[query_result, memory_result])

        engine = InsightsEngine(db_session=mock_session)

        # Patch _get_top_topics to avoid more DB calls
        with patch.object(engine, '_get_top_topics', return_value=[]):
            stats = await engine._get_key_stats(
                user_id=TEST_USER_ID,
                tenant_id=TEST_TENANT_ID,
                period_start=datetime.now().date() - timedelta(days=7),
                period_end=datetime.now().date(),
                scope="user"
            )

        # The key is that memories_captured field exists and is populated
        assert "memories_captured" in stats

    @pytest.mark.asyncio
    async def test_get_queries_for_topic_includes_memories(self):
        """Topic queries include memory_items via UNION."""
        # This tests that _get_queries_for_topic returns both
        # query_history and memory_items sources

        mock_session = AsyncMock()

        # Mock UNION query result with both sources
        mock_rows = [
            # query_history row
            ("query-123", "How to deploy?", "Use kubectl...", datetime.now(),
             "claude", ["kubernetes"], "query_history"),
            # memory_items row
            ("mem-456", "Captured Memory", "Docker compose setup...", datetime.now(),
             "extension_capture", ["docker"], "memory_items"),
        ]
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=mock_rows)

        mock_session.execute = AsyncMock(return_value=mock_result)

        engine = InsightsEngine(db_session=mock_session)

        queries = await engine._get_queries_for_topic(
            user_id=TEST_USER_ID,
            tenant_id=TEST_TENANT_ID,
            topic="kubernetes",
            period_start=datetime.now().date() - timedelta(days=7),
            period_end=datetime.now().date()
        )

        assert len(queries) == 2

        # Verify we got both source types
        source_tables = [q.get("source_table") for q in queries]
        assert "query_history" in source_tables
        assert "memory_items" in source_tables

    @pytest.mark.asyncio
    async def test_sample_queries_include_memories(self):
        """Sample queries for topic analysis include memory content."""
        mock_session = AsyncMock()

        # Mock UNION query result - returns (content, source_type) tuples
        # The function extracts row[0] (content) as strings
        mock_rows = [
            ("Sample from desktop chat", "query"),
            ("Sample from Chrome extension", "memory"),
        ]
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=mock_rows)

        mock_session.execute = AsyncMock(return_value=mock_result)

        engine = InsightsEngine(db_session=mock_session)

        samples = await engine._get_sample_queries_for_topic(
            user_id=TEST_USER_ID,
            tenant_id=TEST_TENANT_ID,
            topic="python",
            period_start=datetime.now().date() - timedelta(days=7),
            period_end=datetime.now().date(),
            limit=10
        )

        # Function returns List[str] containing content only
        assert len(samples) == 2
        assert "Sample from desktop chat" in samples
        assert "Sample from Chrome extension" in samples


class TestReportGeneratorMemoryStats:
    """Tests for ReportGenerator memory statistics."""

    def test_knowledge_growth_includes_memories(self):
        """KnowledgeGrowth dataclass has memories_captured field."""
        kg = KnowledgeGrowth(
            new_qa_pairs=100,
            facts_extracted=50,
            memories_promoted=10,
            memories_captured=5000,  # New field
            topics_mastered=["python", "kubernetes"],
            topics_in_progress=["rust"],
            extension_sources={"chatgpt": 3000, "claude": 1500, "gemini": 500}
        )

        assert kg.memories_captured == 5000
        assert kg.extension_sources["chatgpt"] == 3000

        # Test to_dict includes new fields
        kg_dict = kg.to_dict()
        assert "memories_captured" in kg_dict
        assert "extension_sources" in kg_dict
        assert kg_dict["memories_captured"] == 5000

    @pytest.mark.asyncio
    async def test_get_summary_data_queries_memory_items(self):
        """_get_summary_data queries memory_items for stats."""
        mock_session = AsyncMock()

        # Mock agent stats query
        agent_result = MagicMock()
        agent_result.fetchall = MagicMock(return_value=[
            ("claude", 100, 0.50, 2000),
        ])

        # Mock memory stats query
        mem_result = MagicMock()
        mem_result.fetchone = MagicMock(return_value=(
            5000,   # total_memories
            3000,   # chatgpt_captures
            1500,   # claude_captures
            400,    # gemini_captures
            100,    # perplexity_captures
        ))

        mock_session.execute = AsyncMock(side_effect=[agent_result, mem_result])

        generator = ReportGenerator(db_session=mock_session, insights_engine=None)

        data = await generator._get_summary_data(
            user_id=TEST_USER_ID,
            tenant_id=TEST_TENANT_ID,
            period_start=datetime.now().date() - timedelta(days=7),
            period_end=datetime.now().date(),
            scope="user"
        )

        assert "key_stats" in data
        assert data["key_stats"].get("memories_captured") == 5000

        assert "extension_breakdown" in data
        assert data["extension_breakdown"]["chatgpt"] == 3000
        assert data["extension_breakdown"]["claude"] == 1500

    def test_build_knowledge_growth_uses_memory_stats(self):
        """_build_knowledge_growth includes memory stats."""
        generator = ReportGenerator(db_session=None, insights_engine=None)

        data = {
            "key_stats": {
                "total_queries": 100,
                "facts_extracted": 50,
                "memories_promoted": 10,
                "memories_captured": 5000,
            },
            "top_topics": [],
            "extension_breakdown": {
                "chatgpt": 3000,
                "claude": 1500,
                "gemini": 500
            }
        }

        kg = generator._build_knowledge_growth(data)

        assert kg.memories_captured == 5000
        assert kg.extension_sources["chatgpt"] == 3000


class TestPrivacyFiltering:
    """Tests for RBAC and privacy filtering in memory queries."""

    @pytest.mark.asyncio
    async def test_memory_queries_filter_privacy_level(self):
        """Memory queries include privacy_level IN ('PUBLIC', 'INTERNAL')."""
        mock_session = AsyncMock()

        # Mock all queries - the function makes multiple DB calls
        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=(100, 5.0, 2000, 'claude', 0.5))
        mock_result.fetchall = MagicMock(return_value=[])

        mock_session.execute = AsyncMock(return_value=mock_result)

        engine = InsightsEngine(db_session=mock_session)

        await engine._get_key_stats(
            user_id=TEST_USER_ID,
            tenant_id=TEST_TENANT_ID,
            period_start=datetime.now().date() - timedelta(days=7),
            period_end=datetime.now().date(),
            scope="user"
        )

        # Check all executed SQL for privacy filter
        call_args = mock_session.execute.call_args_list
        all_sqls = [str(call[0][0]) for call in call_args]

        # At least one query should have privacy_level filter (memory_items query)
        has_privacy_filter = any(
            "privacy_level" in sql and "PUBLIC" in sql and "INTERNAL" in sql
            for sql in all_sqls
        )
        assert has_privacy_filter, f"No privacy filter found in queries: {all_sqls}"

    @pytest.mark.asyncio
    async def test_queries_for_topic_filter_confidential(self):
        """Topic queries exclude CONFIDENTIAL memories."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.fetchall = MagicMock(return_value=[])
        mock_session.execute = AsyncMock(return_value=mock_result)

        engine = InsightsEngine(db_session=mock_session)

        await engine._get_queries_for_topic(
            user_id=TEST_USER_ID,
            tenant_id=TEST_TENANT_ID,
            topic="python",
            period_start=datetime.now().date() - timedelta(days=7),
            period_end=datetime.now().date()
        )

        # Verify UNION query includes privacy filter for memory_items
        call_args = mock_session.execute.call_args
        sql = str(call_args[0][0])

        # memory_items part should have privacy filter
        assert "privacy_level IN ('PUBLIC', 'INTERNAL')" in sql


class TestIdempotency:
    """Tests for topic extraction idempotency."""

    def test_unique_key_generation(self):
        """Same inputs produce same idempotency key."""
        extractor = TopicExtractor(db_session=None)

        key1 = extractor.get_idempotency_key(
            TEST_TENANT_ID, "memory_items", "mem-123"
        )
        key2 = extractor.get_idempotency_key(
            TEST_TENANT_ID, "memory_items", "mem-123"
        )

        assert key1 == key2

    def test_different_source_types_different_keys(self):
        """query_history and memory_items produce different keys."""
        extractor = TopicExtractor(db_session=None)

        key_qh = extractor.get_idempotency_key(
            TEST_TENANT_ID, "query_history", "id-123"
        )
        key_mi = extractor.get_idempotency_key(
            TEST_TENANT_ID, "memory_items", "id-123"
        )

        assert key_qh != key_mi

    @pytest.mark.asyncio
    async def test_extraction_cached_on_repeat(self):
        """Repeated extraction uses cache."""
        # Mock DB with cache hit
        mock_row = MagicMock()
        mock_row._mapping = {
            "id": str(uuid4()),
            "topics": ["python"],
            "primary_topic": "python",
            "extraction_method": "keyword",
            "extractor_version": "v1_keyword_20241115",
            "confidence": 0.8,
            "tokens_used": 0,
            "created_at": datetime.now()
        }

        mock_result = MagicMock()
        mock_result.fetchone = MagicMock(return_value=mock_row)

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)

        extractor = TopicExtractor(db_session=mock_session)

        result = await extractor.extract_topics_idempotent(
            source_type="memory_items",
            source_id="mem-123",
            text="Python programming example",
            user_id=TEST_USER_ID
        )

        # Should return cached result
        assert result.cached is True
        assert result.topics == ["python"]


class TestEndToEndFlow:
    """End-to-end tests for the complete data flow."""

    @pytest.mark.asyncio
    async def test_memory_to_insight_flow(self):
        """Memory capture → topic extraction → insights flow."""
        # 1. Simulate memory capture from Chrome extension
        memory_content = """
        Today I learned about Kubernetes deployment strategies.
        Rolling updates and blue-green deployments are useful for zero-downtime releases.
        """

        # 2. Extract topics (no DB, keyword extraction)
        extractor = TopicExtractor(db_session=None, llm_provider=None)
        result = await extractor.extract_topics_idempotent(
            source_type="memory_items",
            source_id=str(uuid4()),
            text=memory_content,
            user_id=TEST_USER_ID
        )

        # Should find kubernetes topic
        assert "kubernetes" in result.topics
        assert result.primary_topic == "kubernetes"

        # 3. Verify topic would appear in insights queries
        # (actual DB integration would show this in insights)
        assert result.method == ExtractionMethod.KEYWORD
        assert result.confidence > 0.5

    @pytest.mark.asyncio
    async def test_batch_extraction_maintains_user_isolation(self):
        """Batch extraction maintains user_id for RBAC."""
        extractor = TopicExtractor(db_session=None)

        user1_items = [
            ExtractableItem(
                source_type="memory_items",
                source_id="mem-1",
                text="Python programming",
                user_id="user-1",
                tenant_id=TEST_TENANT_ID
            )
        ]

        user2_items = [
            ExtractableItem(
                source_type="memory_items",
                source_id="mem-2",
                text="JavaScript development",
                user_id="user-2",
                tenant_id=TEST_TENANT_ID
            )
        ]

        result1 = await extractor.batch_extract(user1_items)
        result2 = await extractor.batch_extract(user2_items)

        # Results should be separate
        assert len(result1.results) == 1
        assert len(result2.results) == 1

        # Different keys for different users
        key1 = extractor.get_idempotency_key(
            TEST_TENANT_ID, "memory_items", "mem-1"
        )
        key2 = extractor.get_idempotency_key(
            TEST_TENANT_ID, "memory_items", "mem-2"
        )
        assert key1 != key2
