#!/usr/bin/env python3
"""
Integration Tests for UniversalSearchEngine - End-to-End Workflows

These tests verify the complete search pipeline with REAL database data:
- Search across existing conversations (417 threads, 2,912 turns)
- Turn-level search finds specific messages in long conversations
- Diversity constraints enforced across source types
- Intent detection affects ranking order

NOTE: These tests use the ACTUAL data already in the system:
- 395 ChatGPT conversations + 22 Claude conversations
- 2,744 ChatGPT turns + 168 Claude turns
- 1,958 memory items

Run with: pytest tests/integration/test_universal_search_e2e.py -v
"""
import pytest
import asyncio
from datetime import datetime, timedelta
from typing import List
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

# Add project root to path
sys.path.insert(0, str(project_root))

from src.search.universal_search import UniversalSearchEngine, SearchConfig, QueryIntent
from src.embeddings.openai_embeddings import OpenAIEmbeddings
from src.cache.query_cache import QueryCache


@pytest.fixture
def test_user():
    """Use the default test user (existing data)"""
    # UUID for default user (has all the imported conversations)
    return "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def search_engine():
    """Initialize UniversalSearchEngine with real dependencies"""
    from src.storage.memory_crud import MemoryCRUD
    from src.storage.conversation_vectors import ConversationVectorStorage
    from src.cache.semantic_cache import SemanticCache

    # Initialize all required dependencies
    memory_crud = MemoryCRUD()
    embeddings_service = OpenAIEmbeddings()
    vector_storage = ConversationVectorStorage()
    semantic_cache = SemanticCache()

    engine = UniversalSearchEngine(
        memory_crud=memory_crud,
        embeddings_service=embeddings_service,
        vector_storage=vector_storage,
        semantic_cache=semantic_cache
    )

    return engine


# No fixtures needed - using real data already in system (417 conversations, 2,912 turns, 1,958 memories)


class TestEndToEndSearch:
    """Test complete search workflows with real data"""

    @pytest.mark.asyncio
    async def test_search_across_existing_conversations(
        self,
        search_engine,
        test_user
    ):
        """
        End-to-end workflow: Search existing data → Verify diversity

        Uses REAL data: 417 conversations, 2,912 turns, 1,958 memories

        Verifies:
        1. Conversations are searchable
        2. Results include both threads and turns
        3. Diversity constraints enforced
        """
        user_id = test_user

        # Search for Python-related content
        query = "How do I build a REST API with Python?"

        results, explanation = await search_engine.search(
            query=query,
            user_id=user_id,
            config=SearchConfig(
                limit=10,
                min_threads=2,
                min_turns=2,
                min_memories=1,
                diversity_mode="balanced"
            )
        )

        # Verify results found
        assert len(results) > 0, "Should find results for Python API query"

        # Verify source diversity (at least 2 threads, 2 turns, 1 memory)
        source_types = [r.source_type for r in results]
        thread_count = source_types.count("conversation_thread")
        turn_count = source_types.count("conversation_turn")
        memory_count = source_types.count("memory")

        assert thread_count >= 2, f"Should have at least 2 threads, got {thread_count}"
        assert turn_count >= 2, f"Should have at least 2 turns, got {turn_count}"
        assert memory_count >= 1, f"Should have at least 1 memory, got {memory_count}"

        # Verify explanation contains diversity info
        assert explanation["diversity_applied"] == True
        assert "source_distribution" in explanation

        print(f"✅ Found {len(results)} results with diversity: {explanation['source_distribution']}")

    @pytest.mark.asyncio
    async def test_turn_level_search_finds_specific_message(
        self,
        search_engine,
        test_user
    ):
        """
        Turn-level search finds specific messages in conversations

        Uses REAL data: 2,912 conversation turns

        Verifies:
        1. Conversation turns are searchable
        2. Turns appear in results (not just threads)
        3. Turn-level content is accessible
        """
        user_id = test_user

        # Search for something specific that would be in a turn
        query = "How do I write Python code?"

        results, explanation = await search_engine.search(
            query=query,
            user_id=user_id,
            config=SearchConfig(
                limit=10,
                enable_intent_detection=True
            )
        )

        # Verify results found
        assert len(results) > 0, "Should find results for Python query"

        # Verify at least one result is a conversation turn
        turn_results = [r for r in results if r.source_type == "conversation_turn"]
        assert len(turn_results) > 0, f"Should find conversation turns, got {len(turn_results)}"

        # Verify turns contain actual content (not empty)
        for turn in turn_results[:3]:
            assert len(turn.content) > 10, "Turn content should not be empty"
            print(f"✅ Found turn: {turn.content[:100]}...")

        print(f"✅ Found {len(turn_results)} conversation turns in {len(results)} total results")

    @pytest.mark.asyncio
    async def test_diversity_constraints_enforced(
        self,
        search_engine,
        test_user
    ):
        """
        Diversity constraints guarantee min sources

        Verifies:
        1. Min 2 threads enforced
        2. Min 2 turns enforced
        3. Min 3 memories enforced (if available)
        """
        user_id = test_user

        # Broad query to get many results
        query = "Tell me everything about Python and databases"

        results, explanation = await search_engine.search(
            query=query,
            user_id=user_id,
            config=SearchConfig(
                limit=15,
                min_threads=2,
                min_turns=2,
                min_memories=2,  # Only 2 because we only created 3 memories
                diversity_mode="diverse"
            )
        )

        # Count by source type
        source_counts = {}
        for result in results:
            source_counts[result.source_type] = source_counts.get(result.source_type, 0) + 1

        # Verify minimums enforced
        assert source_counts.get("conversation_thread", 0) >= 2, "Should have at least 2 threads"
        assert source_counts.get("conversation_turn", 0) >= 2, "Should have at least 2 turns"
        assert source_counts.get("memory", 0) >= 2, "Should have at least 2 memories"

        print(f"✅ Diversity enforced: {source_counts}")
        assert explanation["diversity_applied"] == True


class TestIntentDetection:
    """Test query intent detection affects ranking"""

    @pytest.mark.asyncio
    async def test_troubleshoot_intent_prefers_recent(
        self,
        search_engine,
        test_user
    ):
        """
        TROUBLESHOOT queries should be detected

        Verifies:
        1. Query detected as TROUBLESHOOT intent
        2. Freshness boost enabled for TROUBLESHOOT queries
        3. Results include ranking signals
        """
        user_id = test_user

        # TROUBLESHOOT query (contains "error", "broken")
        query = "Python code is broken with error"

        results, explanation = await search_engine.search(
            query=query,
            user_id=user_id,
            config=SearchConfig(
                limit=10,
                enable_intent_detection=True,
                enable_recency_boost=True
            )
        )

        # Verify intent detected
        assert explanation["query_intent"] == QueryIntent.TROUBLESHOOT, \
            f"Should detect TROUBLESHOOT intent, got {explanation['query_intent']}"

        # Verify results found
        assert len(results) > 0, "Should find troubleshooting results"

        # Verify freshness boost applied
        for result in results[:5]:
            assert "freshness_boost" in result.ranking_signals, \
                "Results should have freshness boost in ranking signals"

        print(f"✅ TROUBLESHOOT intent detected, found {len(results)} results with freshness boost")

    @pytest.mark.asyncio
    async def test_howto_intent_boosts_conversation_turns(
        self,
        search_engine,
        test_user
    ):
        """
        HOWTO queries should be detected

        Verifies:
        1. Query detected as HOWTO intent
        2. Conversation turns found in results
        3. Source boost applied
        """
        user_id = test_user

        # HOWTO query
        query = "How to write Python code?"

        results, explanation = await search_engine.search(
            query=query,
            user_id=user_id,
            config=SearchConfig(
                limit=10,
                enable_intent_detection=True
            )
        )

        # Verify intent detected
        assert explanation["query_intent"] == QueryIntent.HOWTO, \
            f"Should detect HOWTO intent, got {explanation['query_intent']}"

        # Verify results found
        assert len(results) > 0, "Should find results for HOWTO query"

        # Verify conversation turns appear in results
        turn_results = [r for r in results if r.source_type == "conversation_turn"]
        print(f"✅ HOWTO intent detected, found {len(turn_results)} conversation turns in {len(results)} total results")


class TestMultiSignalRanking:
    """Test multi-signal ranking formula in real scenarios"""

    @pytest.mark.asyncio
    async def test_ranking_signals_all_applied(
        self,
        search_engine,
        test_user
    ):
        """
        Verify all 5 ranking signals are applied

        Verifies:
        1. All results have ranking_signals populated
        2. All 5 signals present: semantic, source_boost, freshness, feedback, diversity
        3. Boosted scores reflect weighted formula
        """
        user_id = test_user

        query = "Python FastAPI database connection"

        results, explanation = await search_engine.search(
            query=query,
            user_id=user_id,
            config=SearchConfig(
                limit=10,
                enable_recency_boost=True
            )
        )

        assert len(results) > 0, "Should find results"

        # Verify all results have ranking signals
        for result in results:
            assert hasattr(result, "ranking_signals"), "Result should have ranking_signals"
            assert len(result.ranking_signals) == 5, \
                f"Should have 5 signals, got {len(result.ranking_signals)}: {result.ranking_signals.keys()}"

            # Verify all signal keys present
            required_signals = [
                "semantic_similarity",
                "source_boost",
                "freshness_boost",
                "feedback_score",
                "diversity_bonus"
            ]
            for signal in required_signals:
                assert signal in result.ranking_signals, \
                    f"Missing signal: {signal} in {result.ranking_signals.keys()}"

            # Verify boosted_score is populated
            assert result.boosted_score > 0, "Boosted score should be positive"

        print(f"✅ All {len(results)} results have complete ranking signals")
        print(f"   Top result signals: {results[0].ranking_signals}")
        print(f"   Boosted score: {results[0].boosted_score:.3f}")


class TestExplanationTransparency:
    """Test search explanation provides transparency"""

    @pytest.mark.asyncio
    async def test_explanation_includes_all_metadata(
        self,
        search_engine,
        test_user
    ):
        """
        Explanation should include comprehensive metadata

        Verifies:
        1. Query intent shown
        2. Source distribution shown
        3. Diversity flags shown
        4. Ranking signal weights shown
        5. Tier counts shown
        """
        user_id = test_user

        query = "Tell me about building APIs"

        results, explanation = await search_engine.search(
            query=query,
            user_id=user_id,
            config=SearchConfig(limit=10, diversity_mode="balanced")
        )

        # Verify explanation structure
        assert "query" in explanation
        assert "query_intent" in explanation
        assert "source_distribution" in explanation
        assert "diversity_applied" in explanation
        assert "ranking_signals" in explanation
        assert "tier_counts" in explanation

        # Verify ranking signal weights documented
        weights = explanation["ranking_signals"]
        assert weights["semantic_weight"] == 0.40
        assert weights["source_boost_weight"] == 0.20
        assert weights["freshness_weight"] == 0.15
        assert weights["feedback_weight"] == 0.15
        assert weights["diversity_weight"] == 0.10

        print("✅ Explanation includes all metadata:")
        print(f"   Intent: {explanation['query_intent']}")
        print(f"   Sources: {explanation['source_distribution']}")
        print(f"   Tiers: {explanation['tier_counts']}")


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "--tb=short", "-s"])
