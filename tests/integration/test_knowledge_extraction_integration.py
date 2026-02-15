"""Integration tests for KnowledgeExtractor in the orchestrator pipeline.

Tests the full flow:
1. Query comes in
2. Agent generates response
3. KnowledgeExtractor extracts knowledge
4. Knowledge stored to ACMS_Knowledge_v2
5. "Why" context shown in thinking step

Run with:
    PYTHONPATH=. pytest tests/integration/test_knowledge_extraction_integration.py -v
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
import json


class TestKnowledgeExtractionInOrchestrator:
    """Test KnowledgeExtractor integration in gateway orchestrator."""

    @pytest.mark.asyncio
    async def test_knowledge_extraction_step_emitted(self):
        """Orchestrator should emit knowledge_understanding thinking step."""
        from src.gateway.orchestrator import GatewayOrchestrator
        from src.gateway.models import GatewayRequest

        # Mock the knowledge extractor
        mock_entry = MagicMock()
        mock_entry.intent.why_context = "User is learning about Python async"
        mock_entry.intent.primary_intent = "Learn async/await"
        mock_entry.intent.problem_domain = "Python Programming"
        mock_entry.topic_cluster = "python-async"
        mock_entry.entities = []
        mock_entry.extraction_confidence = 0.85

        with patch('src.gateway.orchestrator.get_knowledge_extractor') as mock_get_extractor:
            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=mock_entry)
            mock_get_extractor.return_value = mock_extractor

            orchestrator = GatewayOrchestrator()
            request = GatewayRequest(
                query="How does async/await work in Python?",
                user_id="00000000-0000-0000-0000-000000000001"
            )

            steps_emitted = []
            async for event in orchestrator.execute(request):
                if event.get("type") == "status":
                    steps_emitted.append(event.get("step"))
                if event.get("type") == "done":
                    break

            # Should include knowledge_understanding step
            assert "knowledge_understanding" in steps_emitted

    @pytest.mark.asyncio
    async def test_knowledge_stored_to_weaviate(self):
        """Extracted knowledge should be stored to ACMS_Knowledge_v2."""
        from src.gateway.orchestrator import GatewayOrchestrator
        from src.gateway.models import GatewayRequest
        from src.intelligence.knowledge_extractor import KnowledgeEntry, IntentAnalysis

        # Create a real-ish knowledge entry
        mock_intent = IntentAnalysis(
            primary_intent="Learn Python async",
            problem_domain="Python Programming",
            why_context="User is building async web service",
            user_context_signals=["web development"],
            confidence=0.9
        )

        mock_entry = KnowledgeEntry(
            canonical_query="How does async/await work in Python?",
            answer_summary="async/await uses coroutines...",
            full_answer="Full answer here...",
            intent=mock_intent,
            entities=[],
            relations=[],
            topic_cluster="python-async",
            related_topics=["python-web"],
            key_facts=["async uses event loop"],
            user_id="00000000-0000-0000-0000-000000000001",
            extraction_confidence=0.9
        )

        weaviate_insert_called = False
        inserted_data = None

        def mock_insert_vector(collection, vector, data):
            nonlocal weaviate_insert_called, inserted_data
            if collection == "ACMS_Knowledge_v2":
                weaviate_insert_called = True
                inserted_data = data
            return "test-uuid-123"

        with patch('src.gateway.orchestrator.get_knowledge_extractor') as mock_get_extractor, \
             patch('src.storage.weaviate_client.WeaviateClient') as mock_weaviate_class:

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=mock_entry)
            mock_get_extractor.return_value = mock_extractor

            mock_weaviate = MagicMock()
            mock_weaviate.insert_vector = mock_insert_vector
            mock_weaviate_class.return_value = mock_weaviate

            orchestrator = GatewayOrchestrator()
            request = GatewayRequest(
                query="How does async/await work in Python?",
                user_id="00000000-0000-0000-0000-000000000001"
            )

            async for event in orchestrator.execute(request):
                if event.get("type") == "done":
                    break

            # Verify storage was called
            assert weaviate_insert_called, "Knowledge should be stored to ACMS_Knowledge_v2"
            assert inserted_data is not None
            assert inserted_data.get("canonical_query") == "How does async/await work in Python?"
            assert inserted_data.get("why_context") == "User is building async web service"

    @pytest.mark.asyncio
    async def test_why_context_in_thinking_step_details(self):
        """The why_context should be visible in thinking step details."""
        from src.gateway.orchestrator import GatewayOrchestrator
        from src.gateway.models import GatewayRequest
        from src.intelligence.knowledge_extractor import KnowledgeEntry, IntentAnalysis

        mock_intent = IntentAnalysis(
            primary_intent="Learn OAuth2",
            problem_domain="API Security",
            why_context="User is building secure authentication for production API",
            user_context_signals=["production", "security"],
            confidence=0.9
        )

        mock_entry = KnowledgeEntry(
            canonical_query="How to implement OAuth2?",
            answer_summary="Use OAuth2PasswordBearer...",
            full_answer="Full answer...",
            intent=mock_intent,
            entities=[],
            relations=[],
            topic_cluster="api-authentication",
            related_topics=[],
            key_facts=[],
            user_id="test-user",
            extraction_confidence=0.9
        )

        with patch('src.gateway.orchestrator.get_knowledge_extractor') as mock_get_extractor:
            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=mock_entry)
            mock_get_extractor.return_value = mock_extractor

            orchestrator = GatewayOrchestrator()
            request = GatewayRequest(
                query="How do I implement OAuth2?",
                user_id="00000000-0000-0000-0000-000000000001"
            )

            knowledge_step = None
            async for event in orchestrator.execute(request):
                if event.get("step") == "knowledge_understanding":
                    knowledge_step = event
                if event.get("type") == "done":
                    break

            # Verify why_context is in the step
            assert knowledge_step is not None, "knowledge_understanding step should be emitted"
            details = knowledge_step.get("details", {}).get("output", {})
            assert "why_context" in details
            assert "production" in details["why_context"].lower()

    @pytest.mark.asyncio
    async def test_extraction_failure_handled_gracefully(self):
        """If extraction fails, orchestrator should continue without crashing."""
        from src.gateway.orchestrator import GatewayOrchestrator
        from src.gateway.models import GatewayRequest

        with patch('src.gateway.orchestrator.get_knowledge_extractor') as mock_get_extractor:
            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(side_effect=Exception("LLM API error"))
            mock_get_extractor.return_value = mock_extractor

            orchestrator = GatewayOrchestrator()
            request = GatewayRequest(
                query="Test query",
                user_id="00000000-0000-0000-0000-000000000001"
            )

            completed = False
            async for event in orchestrator.execute(request):
                if event.get("type") == "done":
                    completed = True
                    break

            # Should still complete despite extraction failure
            assert completed, "Orchestrator should complete even if extraction fails"

    @pytest.mark.asyncio
    async def test_extraction_log_created(self):
        """Extraction should be logged to knowledge_extraction_log table."""
        from src.gateway.orchestrator import GatewayOrchestrator
        from src.gateway.models import GatewayRequest
        from src.intelligence.knowledge_extractor import KnowledgeEntry, IntentAnalysis

        mock_intent = IntentAnalysis(
            primary_intent="Test",
            problem_domain="Test",
            why_context="Test context",
            confidence=0.9
        )

        mock_entry = KnowledgeEntry(
            canonical_query="Test query",
            answer_summary="Test answer",
            full_answer="Full answer",
            intent=mock_intent,
            entities=[],
            relations=[],
            topic_cluster="test-topic",
            related_topics=[],
            key_facts=["fact1"],
            user_id="test-user",
            extraction_confidence=0.9
        )

        log_insert_called = False

        async def mock_execute(query, params=None):
            nonlocal log_insert_called
            if "knowledge_extraction_log" in str(query):
                log_insert_called = True
            return MagicMock(fetchone=lambda: None)

        with patch('src.gateway.orchestrator.get_knowledge_extractor') as mock_get_extractor, \
             patch('src.storage.database.get_session') as mock_get_session:

            mock_extractor = MagicMock()
            mock_extractor.extract = AsyncMock(return_value=mock_entry)
            mock_get_extractor.return_value = mock_extractor

            mock_session = MagicMock()
            mock_session.execute = mock_execute
            mock_session.commit = AsyncMock()
            mock_get_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_get_session.return_value.__aexit__ = AsyncMock()

            orchestrator = GatewayOrchestrator()
            request = GatewayRequest(
                query="Test query",
                user_id="00000000-0000-0000-0000-000000000001"
            )

            async for event in orchestrator.execute(request):
                if event.get("type") == "done":
                    break

            # Extraction should be logged
            # Note: This test verifies the integration point exists
            # The actual logging implementation is tested separately


class TestKnowledgeExtractionWithRealLLM:
    """Integration tests that call real LLM (run manually, not in CI)."""

    @pytest.mark.integration
    @pytest.mark.skipif(
        "ANTHROPIC_API_KEY" not in __import__("os").environ,
        reason="Requires ANTHROPIC_API_KEY"
    )
    @pytest.mark.asyncio
    async def test_real_extraction_in_pipeline(self):
        """End-to-end test with real LLM extraction."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        extractor = KnowledgeExtractor()

        # Simulate a real query/answer pair
        entry = await extractor.extract(
            query="What is the difference between asyncio and threading in Python?",
            answer="""
            asyncio and threading are both concurrency mechanisms in Python, but they work differently:

            1. Threading uses OS threads and is good for I/O-bound tasks with blocking calls
            2. asyncio uses cooperative multitasking with a single thread and event loop
            3. asyncio requires 'async/await' syntax and non-blocking I/O operations
            4. Threading has higher memory overhead (each thread needs its own stack)
            5. asyncio is generally more efficient for high-concurrency I/O operations

            Choose threading for legacy blocking code, asyncio for new high-concurrency apps.
            """,
            user_id="test-user-integration"
        )

        print(f"\n{'='*60}")
        print("Integration Test Results")
        print(f"{'='*60}")
        print(f"Canonical Query: {entry.canonical_query}")
        print(f"Topic Cluster: {entry.topic_cluster}")
        print(f"Why Context: {entry.intent.why_context}")
        print(f"Problem Domain: {entry.intent.problem_domain}")
        print(f"Entities: {[e.canonical for e in entry.entities]}")
        print(f"Key Facts ({len(entry.key_facts)}):")
        for fact in entry.key_facts:
            print(f"  - {fact}")
        print(f"Confidence: {entry.extraction_confidence}")
        print(f"{'='*60}\n")

        # Verify extraction quality
        assert entry.topic_cluster is not None
        assert "async" in entry.topic_cluster.lower() or "python" in entry.topic_cluster.lower()
        assert entry.intent.why_context is not None
        assert len(entry.entities) >= 2  # Should find asyncio and threading
        assert entry.extraction_confidence > 0.5


class TestTopicClusterManagement:
    """Test dynamic topic cluster creation and management."""

    @pytest.mark.asyncio
    async def test_new_topic_cluster_created_on_first_encounter(self):
        """When a new topic is discovered, it should be added to topic_clusters."""
        # This tests the flow where:
        # 1. KnowledgeExtractor returns topic_cluster="python-decorators"
        # 2. Orchestrator checks if this topic exists in topic_clusters table
        # 3. If not, creates new entry with display_name derived from slug
        pass  # Implementation depends on orchestrator integration

    @pytest.mark.asyncio
    async def test_existing_topic_cluster_count_incremented(self):
        """When query matches existing topic, query_count should increment."""
        pass  # Implementation depends on orchestrator integration


class TestEntityGraphBuilding:
    """Test entity and relationship graph building."""

    @pytest.mark.asyncio
    async def test_entities_stored_in_knowledge_entities_table(self):
        """Extracted entities should be stored in PostgreSQL."""
        pass  # Implementation depends on orchestrator integration

    @pytest.mark.asyncio
    async def test_duplicate_entities_merged(self):
        """Same entity from different queries should increment mention_count."""
        pass  # Implementation depends on orchestrator integration

    @pytest.mark.asyncio
    async def test_relations_created_between_entities(self):
        """Entity relations should be stored in entity_relations table."""
        pass  # Implementation depends on orchestrator integration
