"""
Unit Tests for UniversalSearchEngine - TDD Approach

Testing Strategy:
1. Query Intent Detection
2. Multi-Signal Ranking
3. Source Type Boosting
4. Diversity Guarantees
5. Freshness Decay
6. Result Explanation

Best Practices:
- Descriptive test names
- Arrange-Act-Assert pattern
- Mock external dependencies
- Test edge cases
- Verify logging
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from src.search.universal_search import (
    UniversalSearchEngine,
    QueryIntent,
    SearchConfig,
    SearchResult
)


class TestQueryIntentDetection:
    """Test query intent classification"""

    def test_detect_exploratory_intent(self):
        """EXPLORATORY: 'everything about', 'comprehensive'"""
        assert QueryIntent.detect("Tell me everything about Rajan") == QueryIntent.EXPLORATORY
        assert QueryIntent.detect("Give me comprehensive info on ACMS") == QueryIntent.EXPLORATORY
        assert QueryIntent.detect("All about Python programming") == QueryIntent.EXPLORATORY

    def test_detect_biographical_intent(self):
        """BIOGRAPHICAL: 'who is', 'tell me about'"""
        assert QueryIntent.detect("Who is Rajan?") == QueryIntent.BIOGRAPHICAL
        assert QueryIntent.detect("Tell me about Claude") == QueryIntent.BIOGRAPHICAL
        assert QueryIntent.detect("Background on the founder") == QueryIntent.BIOGRAPHICAL

    def test_detect_howto_intent(self):
        """HOWTO: 'how to', 'tutorial'"""
        assert QueryIntent.detect("How to fix Docker errors") == QueryIntent.HOWTO
        assert QueryIntent.detect("How do I install Weaviate?") == QueryIntent.HOWTO
        assert QueryIntent.detect("Tutorial for FastAPI") == QueryIntent.HOWTO

    def test_detect_factual_intent(self):
        """FACTUAL: 'what is', 'define'"""
        assert QueryIntent.detect("What is vector search?") == QueryIntent.FACTUAL
        assert QueryIntent.detect("Define semantic cache") == QueryIntent.FACTUAL
        assert QueryIntent.detect("Explain embeddings") == QueryIntent.FACTUAL

    def test_detect_troubleshoot_intent(self):
        """TROUBLESHOOT: 'error', 'fix', 'broken'"""
        assert QueryIntent.detect("Error connecting to database") == QueryIntent.TROUBLESHOOT
        assert QueryIntent.detect("Fix broken API endpoint") == QueryIntent.TROUBLESHOOT
        assert QueryIntent.detect("PostgreSQL connection timeout") == QueryIntent.TROUBLESHOOT

    def test_detect_general_intent_fallback(self):
        """GENERAL: No specific intent keywords"""
        assert QueryIntent.detect("Random query here") == QueryIntent.GENERAL
        assert QueryIntent.detect("Search for something") == QueryIntent.GENERAL


class TestMultiSignalRanking:
    """Test multi-signal ranking algorithm"""

    @pytest.fixture
    def search_engine(self):
        """Create mock search engine"""
        memory_crud = Mock()
        embeddings = Mock()
        vector_storage = Mock()
        return UniversalSearchEngine(memory_crud, embeddings, vector_storage)

    @pytest.mark.asyncio
    async def test_ranking_combines_five_signals(self, search_engine):
        """
        Final score should combine:
        1. Semantic similarity (40%)
        2. Source type boost (20%)
        3. Freshness boost (15%)
        4. Feedback score (15%)
        5. Diversity bonus (10%)
        """
        result = SearchResult(
            memory_id="test_123",
            content="Test content",
            source_type="conversation_turn",
            relevance_score=0.85,  # 85% semantic match
            boosted_score=0.0,  # Will be calculated
            created_at=datetime.utcnow() - timedelta(days=2),
            tags=["test"],
            privacy_level="INTERNAL",
            excerpt="Test...",
            metadata={},
            ranking_signals={}
        )

        # Apply ranking boosts (using singular method for testing)
        boosted = search_engine._apply_ranking_boost(
            result,
            intent=QueryIntent.HOWTO,
            config=SearchConfig()
        )

        # Verify all signals applied
        assert "semantic_similarity" in boosted.ranking_signals
        assert "source_boost" in boosted.ranking_signals
        assert "freshness_boost" in boosted.ranking_signals
        assert "feedback_score" in boosted.ranking_signals
        assert "diversity_bonus" in boosted.ranking_signals

        # Verify formula: semantic(40%) + source(20%) + fresh(15%) + feedback(15%) + diversity(10%)
        expected_score = (
            0.85 * 0.40 +  # Semantic: 85% * 40% weight
            boosted.ranking_signals["source_boost"] * 0.20 +
            boosted.ranking_signals["freshness_boost"] * 0.15 +
            boosted.ranking_signals["feedback_score"] * 0.15 +
            boosted.ranking_signals["diversity_bonus"] * 0.10
        )

        assert abs(boosted.boosted_score - expected_score) < 0.01  # Float precision

    def test_logging_ranking_signals(self, search_engine, caplog):
        """Verify ranking signals are logged for debugging"""
        result = SearchResult(
            memory_id="test_123",
            content="Test",
            source_type="memory",
            relevance_score=0.90,
            boosted_score=0.0,
            created_at=datetime.utcnow(),
            tags=[],
            privacy_level="PUBLIC",
            excerpt="Test",
            metadata={},
            ranking_signals={}
        )

        with caplog.at_level("DEBUG"):
            search_engine._apply_ranking_boost(result, QueryIntent.GENERAL, SearchConfig())

        # Should log ranking breakdown
        assert "Ranking signals applied" in caplog.text or "boosted_score" in caplog.text


class TestSourceTypeBoosting:
    """Test source type boost weights"""

    @pytest.fixture
    def search_engine(self):
        memory_crud = Mock()
        embeddings = Mock()
        vector_storage = Mock()
        return UniversalSearchEngine(memory_crud, embeddings, vector_storage)

    def test_qa_pair_highest_boost(self, search_engine):
        """QA pairs (knowledge base) should have highest boost: 1.30x"""
        result_qa = SearchResult(
            memory_id="qa_1",
            content="Q: How to X? A: Do Y",
            source_type="qa_pair",
            relevance_score=0.80,
            boosted_score=0.0,
            created_at=datetime.utcnow(),
            tags=["knowledge_base"],
            privacy_level="PUBLIC",
            excerpt="",
            metadata={},
            ranking_signals={}
        )

        boosted_qa = search_engine._apply_ranking_boost(result_qa, QueryIntent.GENERAL, SearchConfig())
        assert boosted_qa.ranking_signals["source_boost"] >= 1.25  # At least 1.25x

    def test_conversation_turn_high_boost(self, search_engine):
        """Conversation turns should have 1.25x boost for HOWTO queries"""
        result_turn = SearchResult(
            memory_id="turn_1",
            content="Step 1: Do this. Step 2: Do that.",
            source_type="conversation_turn",
            relevance_score=0.80,
            boosted_score=0.0,
            created_at=datetime.utcnow(),
            tags=[],
            privacy_level="PUBLIC",
            excerpt="",
            metadata={},
            ranking_signals={}
        )

        boosted = search_engine._apply_ranking_boost(result_turn, QueryIntent.HOWTO, SearchConfig())
        assert boosted.ranking_signals["source_boost"] >= 1.20  # Should be boosted for HOWTO

    def test_conversation_thread_moderate_boost(self, search_engine):
        """Conversation threads should have 1.10x boost for BIOGRAPHICAL"""
        result_thread = SearchResult(
            memory_id="thread_1",
            content="Full conversation about Rajan's background...",
            source_type="conversation_thread",
            relevance_score=0.80,
            boosted_score=0.0,
            created_at=datetime.utcnow(),
            tags=[],
            privacy_level="PUBLIC",
            excerpt="",
            metadata={},
            ranking_signals={}
        )

        boosted = search_engine._apply_ranking_boost(result_thread, QueryIntent.BIOGRAPHICAL, SearchConfig())
        assert boosted.ranking_signals["source_boost"] >= 1.05  # Moderate boost

    def test_memory_baseline_no_boost(self, search_engine):
        """Regular memories should have 1.00x (baseline, no boost)"""
        result_memory = SearchResult(
            memory_id="mem_1",
            content="Random memory",
            source_type="memory",
            relevance_score=0.80,
            boosted_score=0.0,
            created_at=datetime.utcnow(),
            tags=[],
            privacy_level="PUBLIC",
            excerpt="",
            metadata={},
            ranking_signals={}
        )

        boosted = search_engine._apply_ranking_boost(result_memory, QueryIntent.GENERAL, SearchConfig())
        assert boosted.ranking_signals["source_boost"] == 1.0  # Baseline


class TestDiversityGuarantees:
    """Test diversity constraint enforcement"""

    @pytest.fixture
    def search_engine(self):
        memory_crud = Mock()
        embeddings = Mock()
        vector_storage = Mock()
        return UniversalSearchEngine(memory_crud, embeddings, vector_storage)

    def test_diversity_enforces_minimums(self, search_engine):
        """
        Should guarantee minimum per source type:
        - min 2 memories
        - min 2 conversation_threads
        - min 2 conversation_turns
        """
        # Create 20 high-scoring memory results (would dominate top 10)
        memory_results = [
            SearchResult(
                memory_id=f"mem_{i}",
                content="Memory content",
                source_type="memory",
                relevance_score=0.95,  # Very high score
                boosted_score=0.95,
                created_at=datetime.utcnow(),
                tags=[],
                privacy_level="PUBLIC",
                excerpt="",
                metadata={},
                ranking_signals={"source_boost": 1.0}
            )
            for i in range(20)
        ]

        # Add 2 lower-scoring conversation threads
        thread_results = [
            SearchResult(
                memory_id=f"thread_{i}",
                content="Thread content",
                source_type="conversation_thread",
                relevance_score=0.70,  # Lower score
                boosted_score=0.70,
                created_at=datetime.utcnow(),
                tags=[],
                privacy_level="PUBLIC",
                excerpt="",
                metadata={},
                ranking_signals={"source_boost": 1.0}
            )
            for i in range(2)
        ]

        # Add 2 lower-scoring conversation turns
        turn_results = [
            SearchResult(
                memory_id=f"turn_{i}",
                content="Turn content",
                source_type="conversation_turn",
                relevance_score=0.65,  # Even lower
                boosted_score=0.65,
                created_at=datetime.utcnow(),
                tags=[],
                privacy_level="PUBLIC",
                excerpt="",
                metadata={},
                ranking_signals={"source_boost": 1.0}
            )
            for i in range(2)
        ]

        all_results = memory_results + thread_results + turn_results

        # Apply diversity constraints
        config = SearchConfig(
            limit=10,
            min_memories=2,
            min_threads=2,
            min_turns=2
        )
        diverse_results = search_engine._apply_diversity_constraints(
            all_results,
            config,
            QueryIntent.EXPLORATORY
        )

        # Count by source type
        source_counts = {}
        for result in diverse_results[:10]:  # Top 10 only
            source_counts[result.source_type] = source_counts.get(result.source_type, 0) + 1

        # Verify minimums enforced
        assert source_counts.get("memory", 0) >= 2, "Should have at least 2 memories"
        assert source_counts.get("conversation_thread", 0) >= 2, "Should have at least 2 threads"
        assert source_counts.get("conversation_turn", 0) >= 2, "Should have at least 2 turns"

    def test_diversity_logs_enforcement(self, search_engine, caplog):
        """Verify diversity enforcement is logged"""
        results = [
            SearchResult(
                memory_id=f"mem_{i}",
                content="Content",
                source_type="memory",
                relevance_score=0.90,
                boosted_score=0.90,
                created_at=datetime.utcnow(),
                tags=[],
                privacy_level="PUBLIC",
                excerpt="",
                metadata={},
                ranking_signals={}
            )
            for i in range(10)
        ]

        config = SearchConfig(min_memories=2, min_threads=2, min_turns=2)

        with caplog.at_level("INFO"):
            search_engine._apply_diversity_constraints(results, config, QueryIntent.EXPLORATORY)

        # Should log diversity actions
        assert "diversity" in caplog.text.lower() or "guaranteed" in caplog.text.lower()


class TestFreshnessDecay:
    """Test time-based ranking adjustments"""

    @pytest.fixture
    def search_engine(self):
        memory_crud = Mock()
        embeddings = Mock()
        vector_storage = Mock()
        return UniversalSearchEngine(memory_crud, embeddings, vector_storage)

    def test_troubleshoot_prefers_recent(self, search_engine):
        """TROUBLESHOOT intent should strongly boost recent results"""
        # Recent result (2 days old)
        recent = datetime.utcnow() - timedelta(days=2)
        boost_recent = search_engine._calculate_freshness_boost(recent, QueryIntent.TROUBLESHOOT)

        # Old result (60 days old)
        old = datetime.utcnow() - timedelta(days=60)
        boost_old = search_engine._calculate_freshness_boost(old, QueryIntent.TROUBLESHOOT)

        # Recent should be boosted significantly more
        assert boost_recent > boost_old
        assert boost_recent >= 1.10  # At least 10% boost for recent troubleshooting

    def test_factual_no_time_bias(self, search_engine):
        """FACTUAL intent should not boost by time (evergreen content)"""
        recent = datetime.utcnow() - timedelta(days=2)
        old = datetime.utcnow() - timedelta(days=365)

        boost_recent = search_engine._calculate_freshness_boost(recent, QueryIntent.FACTUAL)
        boost_old = search_engine._calculate_freshness_boost(old, QueryIntent.FACTUAL)

        # Should be equal (no time bias for facts)
        assert boost_recent == boost_old == 1.0

    def test_howto_no_time_bias(self, search_engine):
        """HOWTO intent should not boost by time (tutorials are evergreen)"""
        recent = datetime.utcnow() - timedelta(days=2)
        old = datetime.utcnow() - timedelta(days=365)

        boost_recent = search_engine._calculate_freshness_boost(recent, QueryIntent.HOWTO)
        boost_old = search_engine._calculate_freshness_boost(old, QueryIntent.HOWTO)

        # Should be equal (no time bias for tutorials)
        assert boost_recent == boost_old == 1.0


class TestResultExplanation:
    """Test ranking explanation for debugging"""

    @pytest.fixture
    def search_engine(self):
        memory_crud = Mock()
        embeddings = Mock()
        vector_storage = Mock()
        return UniversalSearchEngine(memory_crud, embeddings, vector_storage)

    def test_explanation_includes_query_intent(self, search_engine):
        """Explanation should show detected intent"""
        results = []
        config = SearchConfig(limit=10)

        explanation = search_engine._build_explanation(
            results=results,
            query="Tell me everything about Rajan",
            intent=QueryIntent.EXPLORATORY,
            config=config,
            tier_counts={"memories": 5, "threads": 3, "turns": 2}
        )

        assert "query_intent" in explanation
        assert explanation["query_intent"] == QueryIntent.EXPLORATORY

    def test_explanation_includes_source_distribution(self, search_engine):
        """Explanation should show distribution by source type"""
        results = [
            SearchResult(
                memory_id=f"mem_{i}",
                content="",
                source_type="memory" if i < 5 else "conversation_thread",
                relevance_score=0.80,
                boosted_score=0.80,
                created_at=datetime.utcnow(),
                tags=[],
                privacy_level="PUBLIC",
                excerpt="",
                metadata={},
                ranking_signals={}
            )
            for i in range(10)
        ]

        explanation = search_engine._build_explanation(
            results=results,
            query="Test query",
            intent=QueryIntent.GENERAL,
            config=SearchConfig(),
            tier_counts={"memories": 5, "threads": 5}
        )

        assert "source_distribution" in explanation
        assert explanation["source_distribution"]["memory"] == 5
        assert explanation["source_distribution"]["conversation_thread"] == 5

    def test_explanation_includes_diversity_flag(self, search_engine):
        """Explanation should indicate if diversity was applied"""
        explanation = search_engine._build_explanation(
            results=[],
            query="Test",
            intent=QueryIntent.GENERAL,
            config=SearchConfig(min_memories=2, min_threads=2),
            tier_counts={}
        )

        assert "diversity_applied" in explanation
        assert explanation["diversity_applied"] is True  # Config has diversity constraints


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.fixture
    def search_engine(self):
        memory_crud = Mock()
        embeddings = Mock()
        vector_storage = Mock()
        return UniversalSearchEngine(memory_crud, embeddings, vector_storage)

    def test_empty_results_returns_empty_list(self, search_engine):
        """Empty results should return empty list, not error"""
        diverse = search_engine._apply_diversity_constraints(
            [],
            SearchConfig(),
            QueryIntent.GENERAL
        )
        assert diverse == []

    def test_fewer_results_than_limit_returns_all(self, search_engine):
        """If only 3 results exist but limit=10, return all 3"""
        results = [
            SearchResult(
                memory_id=f"mem_{i}",
                content="",
                source_type="memory",
                relevance_score=0.80,
                boosted_score=0.80,
                created_at=datetime.utcnow(),
                tags=[],
                privacy_level="PUBLIC",
                excerpt="",
                metadata={},
                ranking_signals={}
            )
            for i in range(3)
        ]

        diverse = search_engine._apply_diversity_constraints(
            results,
            SearchConfig(limit=10),
            QueryIntent.GENERAL
        )

        assert len(diverse) == 3  # All 3 returned, not error

    @pytest.mark.asyncio
    async def test_search_logs_errors_gracefully(self, search_engine, caplog):
        """If tier search fails, log error but continue with other tiers"""
        # Mock one tier failing
        search_engine.memory_crud.search_memories = AsyncMock(side_effect=Exception("DB error"))

        with caplog.at_level("ERROR"):
            # Should not crash, should log error
            try:
                config = SearchConfig()
                await search_engine._search_memories("test query", None, config)
            except Exception:
                pass  # Expected

        # Should have logged the error
        assert "error" in caplog.text.lower() or "exception" in caplog.text.lower()


# Integration Tests (require database)
class TestIntegration:
    """Integration tests with actual database (marked for later)"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_exploratory_query(self):
        """
        End-to-end test: Import conversations → Ask question → Verify diversity

        TODO: Implement after unit tests pass
        """
        pytest.skip("Integration test - run after unit tests pass")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_howto_query(self):
        """
        End-to-end test: HOWTO query should boost conversation turns

        TODO: Implement after unit tests pass
        """
        pytest.skip("Integration test - run after unit tests pass")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])
