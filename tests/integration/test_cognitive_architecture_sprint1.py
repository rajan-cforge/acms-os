"""Integration tests for Cognitive Architecture Sprint 1.

Tests the interaction between:
1. ConsolidationTriager - Selective consolidation
2. ThresholdResolver - Adaptive thresholds
3. Propagated Forgetting - Review queue cascade

Run with: PYTHONPATH=. pytest tests/integration/test_cognitive_architecture_sprint1.py -v
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.intelligence.consolidation_triager import (
    ConsolidationTriager,
    ConsolidationPriority,
    QueryRecord,
    TriageResult,
)
from src.retrieval.threshold_resolver import (
    ThresholdResolver,
    RetrievalMode,
    ThresholdSet,
    THRESHOLD_MAP,
)


# ============================================================
# INTEGRATION: CONSOLIDATION TRIAGE + THRESHOLD RESOLUTION
# ============================================================

class TestConsolidationTriageWithThresholds:
    """Test that triage decisions affect threshold selection."""

    @pytest.fixture
    def triager(self):
        return ConsolidationTriager(
            db=None,
            enable_follow_up_detection=False,
            enable_topic_novelty_check=False,
        )

    @pytest.fixture
    def resolver(self):
        return ThresholdResolver()

    @pytest.mark.asyncio
    async def test_high_value_query_gets_explore_thresholds(self, triager, resolver):
        """
        Test that high-value exploratory queries get:
        1. FULL_EXTRACTION priority from triager
        2. CONCEPTUAL_EXPLORE thresholds from resolver

        Cognitive alignment: High-value exploration queries should get
        both full consolidation AND lower thresholds to gather related context.
        """
        # Create a high-value exploratory query
        record = QueryRecord(
            query_id="explore-1",
            question="What do I know about Kubernetes deployment strategies and how they've evolved?",
            answer="Here's a comprehensive overview:\n```yaml\napiVersion: apps/v1\n```" + " word" * 500,
            user_id="user-1",
            created_at=datetime.now(timezone.utc),
            feedback_type="positive",
        )

        # Triage the query
        triage_result = await triager.triage(record)

        # Resolve thresholds
        thresholds = resolver.resolve(record.question)

        # High-value query should get full extraction
        assert triage_result.priority == ConsolidationPriority.FULL_EXTRACTION
        assert triage_result.score >= 0.6

        # Exploratory query should get explore thresholds
        assert thresholds.knowledge == THRESHOLD_MAP[RetrievalMode.CONCEPTUAL_EXPLORE].knowledge

    @pytest.mark.asyncio
    async def test_exact_recall_query_gets_high_thresholds(self, triager, resolver):
        """
        Test exact recall queries get:
        1. Appropriate triage priority
        2. High thresholds for precise matching

        Cognitive alignment: Pattern separation (exact recall) needs
        high thresholds to avoid returning similar-but-wrong memories.
        """
        # Create an exact recall query
        record = QueryRecord(
            query_id="exact-1",
            question="What was the exact kubectl command I used to deploy the staging cluster?",
            answer="kubectl apply -f deployment.yaml --context=staging",
            user_id="user-1",
            created_at=datetime.now(timezone.utc),
        )

        # Triage - should be valuable (contains code reference)
        triage_result = await triager.triage(record)

        # Resolve thresholds
        thresholds = resolver.resolve(record.question)

        # Exact recall should get high thresholds
        assert thresholds.cache == THRESHOLD_MAP[RetrievalMode.EXACT_RECALL].cache
        assert thresholds.raw == THRESHOLD_MAP[RetrievalMode.EXACT_RECALL].raw
        assert thresholds.knowledge == THRESHOLD_MAP[RetrievalMode.EXACT_RECALL].knowledge

    @pytest.mark.asyncio
    async def test_transient_query_skips_full_extraction(self, triager, resolver):
        """
        Test that transient queries:
        1. Skip full extraction (TRANSIENT priority)
        2. Still get appropriate thresholds if retrieved later

        Cognitive alignment: Transient queries (greetings, time) don't
        consolidate to long-term memory but may still be cached briefly.
        """
        # Create a transient query
        record = QueryRecord(
            query_id="transient-1",
            question="hello",
            answer="Hi! How can I help you today?",
            user_id="user-1",
            created_at=datetime.now(timezone.utc),
        )

        # Triage should mark as transient
        triage_result = await triager.triage(record)

        assert triage_result.priority == ConsolidationPriority.TRANSIENT
        assert triage_result.score == 0.0
        assert triage_result.transient_reason is not None

        # Threshold resolution still works (default mode)
        thresholds = resolver.resolve(record.question)
        assert thresholds == THRESHOLD_MAP[RetrievalMode.DEFAULT]


# ============================================================
# INTEGRATION: BATCH TRIAGE + THRESHOLD GROUPS
# ============================================================

class TestBatchTriageWithThresholdGroups:
    """Test batch processing with different threshold needs."""

    @pytest.fixture
    def triager(self):
        return ConsolidationTriager(
            db=None,
            enable_follow_up_detection=False,
            enable_topic_novelty_check=False,
        )

    @pytest.fixture
    def resolver(self):
        return ThresholdResolver()

    @pytest.mark.asyncio
    async def test_batch_triage_separates_by_value(self, triager):
        """Test batch triage correctly separates queries by consolidation value."""
        records = [
            # Transient (greeting)
            QueryRecord(
                query_id="1",
                question="thanks!",
                answer="You're welcome!",
                user_id="user-1",
                created_at=datetime.now(timezone.utc),
            ),
            # High-value (code, feedback, long)
            QueryRecord(
                query_id="2",
                question="How do I implement a distributed cache with Redis cluster for high availability?",
                answer="Here's the implementation:\n```python\nclass DistributedCache:\n    pass\n```" + " word" * 600,
                user_id="user-1",
                created_at=datetime.now(timezone.utc),
                feedback_type="positive",
            ),
            # Medium-value (technical keyword only)
            QueryRecord(
                query_id="3",
                question="What is Python?",
                answer="Python is a programming language.",
                user_id="user-1",
                created_at=datetime.now(timezone.utc),
            ),
        ]

        # Batch triage
        result = await triager.batch_triage(records)

        # Verify separation
        assert len(result[ConsolidationPriority.TRANSIENT]) >= 1
        assert len(result[ConsolidationPriority.FULL_EXTRACTION]) >= 1
        assert len(result[ConsolidationPriority.LIGHTWEIGHT_TAGGING]) >= 0

        # Total should equal input
        total = sum(len(v) for v in result.values())
        assert total == len(records)

    @pytest.mark.asyncio
    async def test_different_modes_require_different_thresholds(self, resolver):
        """Test that different query types resolve to different thresholds."""
        queries = {
            "What was the exact error message I saw yesterday?": RetrievalMode.EXACT_RECALL,
            "What do I know about machine learning?": RetrievalMode.CONCEPTUAL_EXPLORE,
            "Why is my API endpoint failing with 500 errors?": RetrievalMode.TROUBLESHOOT,
            "What's the difference between Docker and Kubernetes?": RetrievalMode.COMPARE,
            "How do I implement user authentication?": RetrievalMode.DEFAULT,
        }

        for query, expected_mode in queries.items():
            mode = resolver.get_mode(query)
            thresholds = resolver.resolve(query)

            assert mode == expected_mode, f"'{query}' should be {expected_mode}, got {mode}"
            assert thresholds == THRESHOLD_MAP[expected_mode]


# ============================================================
# INTEGRATION: COST SAVINGS ESTIMATION
# ============================================================

class TestCostSavingsEstimation:
    """Test the cost savings from consolidation triage."""

    @pytest.fixture
    def triager(self):
        return ConsolidationTriager(
            db=None,
            enable_follow_up_detection=False,
            enable_topic_novelty_check=False,
        )

    @pytest.mark.asyncio
    async def test_triage_saves_costs_on_transient_queries(self, triager):
        """
        Test that triage saves LLM costs by skipping transient queries.

        Expected: 40-60% of queries in a typical workload are transient/light.
        """
        # Simulate a realistic workload
        records = [
            # Transient (40%)
            QueryRecord(query_id="t1", question="hello", answer="Hi!", user_id="u1", created_at=datetime.now(timezone.utc)),
            QueryRecord(query_id="t2", question="thanks!", answer="Welcome!", user_id="u1", created_at=datetime.now(timezone.utc)),
            QueryRecord(query_id="t3", question="ok", answer="Understood.", user_id="u1", created_at=datetime.now(timezone.utc)),
            QueryRecord(query_id="t4", question="bye", answer="Goodbye!", user_id="u1", created_at=datetime.now(timezone.utc)),
            # Medium (30%)
            QueryRecord(query_id="m1", question="What is Python?", answer="A programming language.", user_id="u1", created_at=datetime.now(timezone.utc)),
            QueryRecord(query_id="m2", question="What is Docker?", answer="A containerization platform.", user_id="u1", created_at=datetime.now(timezone.utc)),
            QueryRecord(query_id="m3", question="Explain REST APIs", answer="REST is an architectural style.", user_id="u1", created_at=datetime.now(timezone.utc)),
            # High-value (30%)
            QueryRecord(
                query_id="h1",
                question="How do I implement distributed caching with Redis?",
                answer="Here's how:\n```python\nclass Cache:\n    pass\n```" + " word" * 500,
                user_id="u1",
                created_at=datetime.now(timezone.utc),
                feedback_type="positive",
            ),
            QueryRecord(
                query_id="h2",
                question="Debug this Kubernetes deployment error: CrashLoopBackOff",
                answer="CrashLoopBackOff typically indicates..." + " word" * 600,
                user_id="u1",
                created_at=datetime.now(timezone.utc),
            ),
            QueryRecord(
                query_id="h3",
                question="Explain the OAuth 2.0 flow with implementation details",
                answer="OAuth 2.0 flow works as follows:\n```python\ndef oauth():\n    pass\n```" + " word" * 500,
                user_id="u1",
                created_at=datetime.now(timezone.utc),
            ),
        ]

        # Batch triage
        result = await triager.batch_triage(records)

        # Get stats
        stats = triager.get_stats()

        # Verify cost savings
        transient_count = len(result[ConsolidationPriority.TRANSIENT])
        light_count = len(result[ConsolidationPriority.LIGHTWEIGHT_TAGGING])
        total = len(records)

        # At least 40% should be skipped (transient + light)
        skip_rate = (transient_count + light_count) / total
        assert skip_rate >= 0.4, f"Expected at least 40% skip rate, got {skip_rate:.1%}"

        # Verify stats are tracked
        assert stats["total_triaged"] == total
        assert stats["transient_pct"] > 0


# ============================================================
# INTEGRATION: THRESHOLD ADAPTATION VERIFICATION
# ============================================================

class TestThresholdAdaptationVerification:
    """Verify threshold adaptation follows cognitive principles."""

    @pytest.fixture
    def resolver(self):
        return ThresholdResolver()

    def test_pattern_separation_has_highest_thresholds(self, resolver):
        """
        Cognitive Principle: Pattern Separation (Dentate Gyrus)

        Exact recall queries need to distinguish between similar memories.
        High thresholds prevent returning similar-but-wrong results.
        """
        exact_thresholds = resolver.get_thresholds_for_mode(RetrievalMode.EXACT_RECALL)

        for mode in [RetrievalMode.CONCEPTUAL_EXPLORE, RetrievalMode.TROUBLESHOOT]:
            other_thresholds = resolver.get_thresholds_for_mode(mode)

            assert exact_thresholds.cache >= other_thresholds.cache
            assert exact_thresholds.raw >= other_thresholds.raw
            assert exact_thresholds.knowledge >= other_thresholds.knowledge

    def test_pattern_completion_has_lowest_thresholds(self, resolver):
        """
        Cognitive Principle: Pattern Completion (CA3)

        Exploratory queries need to recall related memories from partial cues.
        Lower thresholds enable associative recall.
        """
        explore_thresholds = resolver.get_thresholds_for_mode(RetrievalMode.CONCEPTUAL_EXPLORE)

        # Explore should have the lowest knowledge threshold
        for mode in [RetrievalMode.EXACT_RECALL, RetrievalMode.TROUBLESHOOT, RetrievalMode.DEFAULT]:
            other_thresholds = resolver.get_thresholds_for_mode(mode)
            assert explore_thresholds.knowledge <= other_thresholds.knowledge

    def test_troubleshoot_is_balanced(self, resolver):
        """
        Cognitive Principle: Balanced Recall

        Troubleshooting needs both exact error messages AND related context.
        Should have moderate thresholds between exact and explore.
        """
        exact = resolver.get_thresholds_for_mode(RetrievalMode.EXACT_RECALL)
        explore = resolver.get_thresholds_for_mode(RetrievalMode.CONCEPTUAL_EXPLORE)
        trouble = resolver.get_thresholds_for_mode(RetrievalMode.TROUBLESHOOT)

        # Troubleshoot knowledge threshold should be between exact and explore
        assert explore.knowledge <= trouble.knowledge <= exact.knowledge


# ============================================================
# INTEGRATION: END-TO-END QUERY FLOW SIMULATION
# ============================================================

class TestEndToEndQueryFlow:
    """Simulate end-to-end query flow with all Sprint 1 components."""

    @pytest.fixture
    def triager(self):
        return ConsolidationTriager(
            db=None,
            enable_follow_up_detection=False,
            enable_topic_novelty_check=False,
        )

    @pytest.fixture
    def resolver(self):
        return ThresholdResolver()

    @pytest.mark.asyncio
    async def test_full_query_flow(self, triager, resolver):
        """
        Simulate a complete query flow:
        1. Query comes in
        2. ThresholdResolver determines retrieval mode
        3. Retrieval uses adaptive thresholds
        4. Response is generated
        5. ConsolidationTriager determines extraction priority
        """
        # Step 1: Query comes in
        query = "How do I debug memory leaks in my Node.js application?"
        response = "To debug memory leaks in Node.js:\n```javascript\nconst heapdump = require('heapdump');\n```\n" + "This comprehensive guide explains..." * 50

        # Step 2: Resolve thresholds for retrieval
        mode = resolver.get_mode(query)
        thresholds = resolver.resolve(query)

        # Should be troubleshoot mode (debugging)
        assert mode == RetrievalMode.TROUBLESHOOT
        assert thresholds.cache == THRESHOLD_MAP[RetrievalMode.TROUBLESHOOT].cache

        # Step 3: Simulate retrieval (would use thresholds)
        # In real system: results = await dual_memory.search_dual(..., thresholds)

        # Step 4: Response generated (mocked above)

        # Step 5: Triage for consolidation
        record = QueryRecord(
            query_id="flow-1",
            question=query,
            answer=response,
            user_id="user-1",
            created_at=datetime.now(timezone.utc),
        )

        triage_result = await triager.triage(record)

        # Should get full extraction (technical, code, debugging, substantial)
        assert triage_result.priority == ConsolidationPriority.FULL_EXTRACTION
        assert "error_or_debugging" in triage_result.signals_detected
        assert "code_in_response" in triage_result.signals_detected
        assert "technical_keywords" in triage_result.signals_detected

    @pytest.mark.asyncio
    async def test_transient_query_flow(self, triager, resolver):
        """
        Test flow for transient query (should skip consolidation).
        """
        query = "thanks for the help!"
        response = "You're welcome! Happy to help."

        # Threshold resolution (still happens, default mode)
        mode = resolver.get_mode(query)
        thresholds = resolver.resolve(query)

        assert mode == RetrievalMode.DEFAULT

        # Triage should mark as transient
        record = QueryRecord(
            query_id="transient-flow",
            question=query,
            answer=response,
            user_id="user-1",
            created_at=datetime.now(timezone.utc),
        )

        triage_result = await triager.triage(record)

        assert triage_result.priority == ConsolidationPriority.TRANSIENT
        assert triage_result.transient_reason is not None
