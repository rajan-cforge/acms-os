"""Tests for ContextBuilder - Stage 3 of retrieval pipeline.

TDD: Write tests FIRST, then implement.

Run with: PYTHONPATH=. pytest tests/unit/retrieval/test_context_builder.py -v
"""
import pytest

from src.retrieval.retriever import RawResult
from src.retrieval.ranker import ScoredResult
from src.retrieval.context_builder import ContextBuilder


class TestContextBuilderInit:
    """Test ContextBuilder initialization."""

    def test_builder_initializes_with_default_budget(self):
        """Builder should initialize with default token budget."""
        builder = ContextBuilder()
        assert builder.max_tokens == 4000

    def test_builder_accepts_custom_budget(self):
        """Builder should accept custom token budget."""
        builder = ContextBuilder(max_tokens=2000)
        assert builder.max_tokens == 2000


class TestContextBuilding:
    """Test context building logic."""

    @pytest.fixture
    def builder(self):
        return ContextBuilder(max_tokens=1000)

    @pytest.fixture
    def sample_results(self):
        """Create sample scored results."""
        return [
            ScoredResult(
                item=RawResult(
                    uuid="1",
                    content="First result content about Python programming",
                    distance=0.1,
                    source="knowledge",
                    properties={}
                ),
                score=0.9,
                breakdown={}
            ),
            ScoredResult(
                item=RawResult(
                    uuid="2",
                    content="Second result about data science with Python",
                    distance=0.2,
                    source="knowledge",
                    properties={}
                ),
                score=0.8,
                breakdown={}
            ),
        ]

    def test_build_returns_string(self, builder, sample_results):
        """Build should return context string."""
        context = builder.build(sample_results)
        assert isinstance(context, str)

    def test_respects_token_budget(self, builder):
        """Context should not exceed token budget."""
        # Create results that would exceed 1000 tokens (~4000 chars)
        large_results = [
            ScoredResult(
                item=RawResult(
                    uuid=str(i),
                    content="X" * 2000,  # ~500 tokens each
                    distance=0.1,
                    source="k",
                    properties={}
                ),
                score=0.9 - i * 0.1,
                breakdown={}
            )
            for i in range(5)
        ]

        context = builder.build(large_results)

        # Rough token count (4 chars ≈ 1 token)
        approx_tokens = len(context) / 4
        assert approx_tokens <= 1100  # Some margin for formatting

    def test_preserves_order(self, builder, sample_results):
        """Higher-scored items should appear first."""
        context = builder.build(sample_results)

        # First result should appear before second
        first_pos = context.find("First result")
        second_pos = context.find("Second result")

        if first_pos != -1 and second_pos != -1:
            assert first_pos < second_pos

    def test_handles_empty_results(self, builder):
        """Empty results should return empty string."""
        context = builder.build([])
        assert context == ""

    def test_includes_content(self, builder, sample_results):
        """Context should include result content."""
        context = builder.build(sample_results)

        assert "Python programming" in context or "First result" in context

    def test_deduplicates_similar_content(self, builder):
        """Near-duplicate content should be removed."""
        duplicate_results = [
            ScoredResult(
                item=RawResult(
                    uuid="1",
                    content="Python is a programming language for beginners",
                    distance=0.1,
                    source="k",
                    properties={}
                ),
                score=0.9,
                breakdown={}
            ),
            ScoredResult(
                item=RawResult(
                    uuid="2",
                    content="Python is a programming language for beginners and experts",
                    distance=0.15,
                    source="k",
                    properties={}
                ),
                score=0.85,
                breakdown={}
            ),
        ]

        context = builder.build(duplicate_results)

        # Should only have one mention (deduplicated)
        count = context.count("Python is a programming language")
        assert count <= 1


class TestTokenEstimation:
    """Test token counting/estimation."""

    def test_estimate_tokens(self):
        """Token estimation should be reasonable."""
        builder = ContextBuilder()

        # ~1 token per 4 characters (rough estimate)
        text = "This is a test sentence with about forty characters."
        tokens = builder._estimate_tokens(text)

        assert 10 <= tokens <= 20
