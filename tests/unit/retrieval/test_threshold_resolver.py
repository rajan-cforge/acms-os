"""Unit tests for ThresholdResolver.

Tests the cognitive science-inspired adaptive threshold system that
adjusts similarity thresholds based on query intent (pattern separation
vs pattern completion).

Run with: PYTHONPATH=. pytest tests/unit/retrieval/test_threshold_resolver.py -v
"""

import pytest
from datetime import datetime, timezone

from src.retrieval.threshold_resolver import (
    RetrievalMode,
    ThresholdResolver,
    ThresholdSet,
    THRESHOLD_MAP,
    resolve_retrieval_mode,
)


# ============================================================
# RETRIEVAL MODE ENUM TESTS
# ============================================================

class TestRetrievalMode:
    """Tests for RetrievalMode enum."""

    def test_enum_values(self):
        """Verify enum has correct values."""
        assert RetrievalMode.EXACT_RECALL.value == "exact"
        assert RetrievalMode.CONCEPTUAL_EXPLORE.value == "explore"
        assert RetrievalMode.TROUBLESHOOT.value == "troubleshoot"
        assert RetrievalMode.COMPARE.value == "compare"
        assert RetrievalMode.DEFAULT.value == "default"

    def test_enum_members_count(self):
        """Verify enum has exactly 5 members."""
        assert len(RetrievalMode) == 5


# ============================================================
# THRESHOLD SET TESTS
# ============================================================

class TestThresholdSet:
    """Tests for ThresholdSet dataclass."""

    def test_basic_creation(self):
        """Test ThresholdSet creation."""
        ts = ThresholdSet(
            cache=0.95,
            raw=0.85,
            knowledge=0.60
        )
        assert ts.cache == 0.95
        assert ts.raw == 0.85
        assert ts.knowledge == 0.60

    def test_to_dict(self):
        """Test ThresholdSet to_dict method."""
        ts = ThresholdSet(cache=0.95, raw=0.85, knowledge=0.60)
        d = ts.to_dict()
        assert d == {"cache": 0.95, "raw": 0.85, "knowledge": 0.60}


# ============================================================
# THRESHOLD MAP TESTS
# ============================================================

class TestThresholdMap:
    """Tests for the threshold map configuration."""

    def test_all_modes_have_thresholds(self):
        """Verify all retrieval modes have threshold configurations."""
        for mode in RetrievalMode:
            assert mode in THRESHOLD_MAP, f"Mode {mode} missing from THRESHOLD_MAP"

    def test_threshold_values_in_valid_range(self):
        """Verify all threshold values are between 0 and 1."""
        for mode, thresholds in THRESHOLD_MAP.items():
            assert 0 <= thresholds.cache <= 1, f"{mode} cache threshold invalid"
            assert 0 <= thresholds.raw <= 1, f"{mode} raw threshold invalid"
            assert 0 <= thresholds.knowledge <= 1, f"{mode} knowledge threshold invalid"

    def test_exact_recall_has_highest_thresholds(self):
        """Verify exact recall mode has highest thresholds (pattern separation)."""
        exact = THRESHOLD_MAP[RetrievalMode.EXACT_RECALL]
        explore = THRESHOLD_MAP[RetrievalMode.CONCEPTUAL_EXPLORE]

        # Exact recall should have higher thresholds than exploration
        assert exact.cache > explore.cache
        assert exact.raw > explore.raw
        assert exact.knowledge > explore.knowledge

    def test_conceptual_explore_has_lowest_thresholds(self):
        """Verify conceptual explore has lowest thresholds (pattern completion)."""
        explore = THRESHOLD_MAP[RetrievalMode.CONCEPTUAL_EXPLORE]

        for mode in [RetrievalMode.EXACT_RECALL, RetrievalMode.TROUBLESHOOT, RetrievalMode.COMPARE]:
            other = THRESHOLD_MAP[mode]
            # Explore should allow more matches
            assert explore.knowledge <= other.knowledge, \
                f"Explore knowledge should be <= {mode} knowledge"


# ============================================================
# MODE DETECTION TESTS
# ============================================================

class TestModeDetection:
    """Tests for automatic retrieval mode detection."""

    def test_exact_recall_detection(self):
        """Test detection of exact recall queries."""
        exact_queries = [
            "What was the exact command I used to deploy?",
            "What were the API credentials?",
            "What was the configuration value for timeout?",
            "Show me the exact error message",
            "What command did I run yesterday?",
        ]
        for query in exact_queries:
            mode = resolve_retrieval_mode(query)
            assert mode == RetrievalMode.EXACT_RECALL, \
                f"'{query}' should be EXACT_RECALL, got {mode}"

    def test_conceptual_explore_detection(self):
        """Test detection of conceptual exploration queries."""
        explore_queries = [
            "What do I know about Kubernetes?",
            "Tell me everything about OAuth",
            "What have I learned about React hooks?",
            "Summarize my knowledge on databases",
            "What topics have I explored?",
        ]
        for query in explore_queries:
            mode = resolve_retrieval_mode(query)
            assert mode == RetrievalMode.CONCEPTUAL_EXPLORE, \
                f"'{query}' should be CONCEPTUAL_EXPLORE, got {mode}"

    def test_troubleshoot_detection(self):
        """Test detection of troubleshooting queries."""
        troubleshoot_queries = [
            "Why is the API failing?",
            "Debug this connection error",
            "Fix the authentication issue",
            "What's causing the timeout?",
            "Troubleshoot the memory leak",
            "Help me diagnose this crash",
        ]
        for query in troubleshoot_queries:
            mode = resolve_retrieval_mode(query)
            assert mode == RetrievalMode.TROUBLESHOOT, \
                f"'{query}' should be TROUBLESHOOT, got {mode}"

    def test_compare_detection(self):
        """Test detection of comparison queries."""
        compare_queries = [
            "What's the difference between REST and GraphQL?",
            "Compare PostgreSQL and MongoDB",
            "Difference between async and sync",
            "How does React compare to Vue?",
            "Compare Kubernetes and Docker Swarm",
        ]
        for query in compare_queries:
            mode = resolve_retrieval_mode(query)
            assert mode == RetrievalMode.COMPARE, \
                f"'{query}' should be COMPARE, got {mode}"

    def test_default_for_ambiguous_queries(self):
        """Test that ambiguous queries get DEFAULT mode."""
        ambiguous_queries = [
            "How do I implement user authentication?",
            "What's the best way to structure a React app?",
            "Explain how Redis caching works",
            "Help me with database optimization",
        ]
        for query in ambiguous_queries:
            mode = resolve_retrieval_mode(query)
            assert mode == RetrievalMode.DEFAULT, \
                f"'{query}' should be DEFAULT, got {mode}"

    def test_intent_hint_overrides_detection(self):
        """Test that explicit intent hint overrides automatic detection."""
        query = "How do I fix this?"  # Would normally be TROUBLESHOOT

        # But with explicit intent hint
        mode = resolve_retrieval_mode(query, intent_hint="explore")
        assert mode == RetrievalMode.CONCEPTUAL_EXPLORE

        mode = resolve_retrieval_mode(query, intent_hint="exact")
        assert mode == RetrievalMode.EXACT_RECALL


# ============================================================
# THRESHOLD RESOLVER CLASS TESTS
# ============================================================

class TestThresholdResolver:
    """Tests for ThresholdResolver class."""

    @pytest.fixture
    def resolver(self):
        """Create a ThresholdResolver instance."""
        return ThresholdResolver()

    def test_resolve_default_mode(self, resolver):
        """Test resolving thresholds for default mode."""
        thresholds = resolver.resolve("Some general question")

        assert isinstance(thresholds, ThresholdSet)
        assert thresholds.cache == THRESHOLD_MAP[RetrievalMode.DEFAULT].cache
        assert thresholds.raw == THRESHOLD_MAP[RetrievalMode.DEFAULT].raw
        assert thresholds.knowledge == THRESHOLD_MAP[RetrievalMode.DEFAULT].knowledge

    def test_resolve_exact_recall(self, resolver):
        """Test resolving thresholds for exact recall."""
        thresholds = resolver.resolve("What was the exact command?")

        assert thresholds.cache == THRESHOLD_MAP[RetrievalMode.EXACT_RECALL].cache
        assert thresholds.raw == THRESHOLD_MAP[RetrievalMode.EXACT_RECALL].raw
        assert thresholds.knowledge == THRESHOLD_MAP[RetrievalMode.EXACT_RECALL].knowledge

    def test_resolve_with_explicit_mode(self, resolver):
        """Test resolving with explicit mode."""
        thresholds = resolver.resolve(
            "Some query",
            mode=RetrievalMode.CONCEPTUAL_EXPLORE
        )

        assert thresholds == THRESHOLD_MAP[RetrievalMode.CONCEPTUAL_EXPLORE]

    def test_resolve_returns_copy(self, resolver):
        """Test that resolve returns a copy, not the original."""
        thresholds1 = resolver.resolve("What do I know about Python?")
        thresholds2 = resolver.resolve("What do I know about Python?")

        # Should be equal but not the same object
        assert thresholds1 == thresholds2
        assert thresholds1 is not thresholds2

    def test_get_mode_for_query(self, resolver):
        """Test getting mode for a query without resolving thresholds."""
        mode = resolver.get_mode("What was the exact error?")
        assert mode == RetrievalMode.EXACT_RECALL

        mode = resolver.get_mode("What do I know about databases?")
        assert mode == RetrievalMode.CONCEPTUAL_EXPLORE

    def test_all_modes_accessible(self, resolver):
        """Test that all modes are accessible via get_thresholds_for_mode."""
        for mode in RetrievalMode:
            thresholds = resolver.get_thresholds_for_mode(mode)
            assert thresholds is not None
            assert isinstance(thresholds, ThresholdSet)


# ============================================================
# EDGE CASE TESTS
# ============================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def resolver(self):
        return ThresholdResolver()

    def test_empty_query(self, resolver):
        """Test handling of empty query."""
        thresholds = resolver.resolve("")
        # Should default to DEFAULT mode
        assert thresholds == THRESHOLD_MAP[RetrievalMode.DEFAULT]

    def test_very_long_query(self, resolver):
        """Test handling of very long query."""
        long_query = "word " * 10000
        # Should not raise exception
        thresholds = resolver.resolve(long_query)
        assert thresholds is not None

    def test_unicode_query(self, resolver):
        """Test handling of unicode query."""
        unicode_query = "What was the exact \u5e38\u7528 command?"
        # Should not raise exception
        thresholds = resolver.resolve(unicode_query)
        assert thresholds is not None

    def test_special_characters(self, resolver):
        """Test handling of special characters."""
        special_query = "What's the difference between `async` and `await`?"
        thresholds = resolver.resolve(special_query)
        assert thresholds is not None

    def test_case_insensitive_detection(self, resolver):
        """Test that mode detection is case insensitive."""
        query_lower = "what was the exact command?"
        query_upper = "WHAT WAS THE EXACT COMMAND?"

        mode_lower = resolver.get_mode(query_lower)
        mode_upper = resolver.get_mode(query_upper)

        assert mode_lower == mode_upper == RetrievalMode.EXACT_RECALL


# ============================================================
# COGNITIVE PRINCIPLES TESTS
# ============================================================

class TestCognitivePrinciples:
    """Tests that verify cognitive science principles are properly implemented."""

    @pytest.fixture
    def resolver(self):
        return ThresholdResolver()

    def test_pattern_separation_vs_completion(self, resolver):
        """
        Test the cognitive principle of pattern separation vs completion.

        Pattern Separation (Dentate Gyrus): Need to distinguish similar memories
        - High thresholds for exact recall queries
        - Only return highly similar matches

        Pattern Completion (CA3): Recall full memory from partial cues
        - Lower thresholds for exploration queries
        - Allow more diverse matches to trigger related memories
        """
        exact_thresholds = resolver.resolve("What was the exact error message?")
        explore_thresholds = resolver.resolve("What do I know about errors?")

        # Pattern separation should have higher thresholds
        assert exact_thresholds.cache > explore_thresholds.cache
        assert exact_thresholds.raw > explore_thresholds.raw
        assert exact_thresholds.knowledge > explore_thresholds.knowledge

    def test_troubleshoot_balanced_recall(self, resolver):
        """
        Test that troubleshooting uses balanced thresholds.

        Troubleshooting needs both:
        - Exact error messages (pattern separation)
        - Related context (pattern completion)

        Should have moderate thresholds.
        """
        trouble_thresholds = resolver.resolve("Why is the API failing?")
        exact_thresholds = resolver.resolve("What was the exact error?")
        explore_thresholds = resolver.resolve("What do I know about APIs?")

        # Troubleshoot should be between exact and explore
        assert explore_thresholds.knowledge <= trouble_thresholds.knowledge <= exact_thresholds.knowledge

    def test_compare_allows_diverse_matches(self, resolver):
        """
        Test that comparison queries allow diverse matches.

        Comparing X and Y needs information about both topics,
        which may have different embeddings.
        """
        compare_thresholds = resolver.resolve("Difference between REST and GraphQL?")
        default_thresholds = resolver.resolve("How do I use REST?")

        # Compare should allow more diverse matches (lower knowledge threshold)
        assert compare_thresholds.knowledge <= default_thresholds.knowledge
