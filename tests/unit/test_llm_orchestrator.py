"""Tests for LLM Orchestrator.

Tests unified LLM interface, model selection, and quality validation.
"""

import pytest
from src.llm.orchestrator import (
    LLMOrchestrator,
    OrchestratorResult,
    Query,
    QualityValidator,
    get_llm_orchestrator
)
from src.llm.agent_registry import AgentRegistry
from src.llm.prompt_builder import PromptBuilder


class TestQuery:
    """Tests for Query dataclass."""

    def test_query_minimal(self):
        """Test creating Query with minimal fields."""
        query = Query(text="Test question")

        assert query.text == "Test question"
        assert query.user_id == ""
        assert query.intent == "GENERAL"
        assert query.context == ""
        assert query.conversation_history == []
        assert query.preferences == {}

    def test_query_full(self):
        """Test creating Query with all fields."""
        query = Query(
            text="Test question",
            user_id="user-123",
            intent="ANALYSIS",
            context="Some context",
            conversation_history=[{"role": "user", "content": "Hi"}],
            preferences={"preferred_model": "gpt-4o"}
        )

        assert query.text == "Test question"
        assert query.user_id == "user-123"
        assert query.intent == "ANALYSIS"
        assert query.context == "Some context"
        assert len(query.conversation_history) == 1
        assert query.preferences["preferred_model"] == "gpt-4o"


class TestOrchestratorResult:
    """Tests for OrchestratorResult dataclass."""

    def test_result_creation(self):
        """Test creating OrchestratorResult."""
        result = OrchestratorResult(
            answer="Test answer",
            model_used="claude-sonnet",
            quality_score=0.85,
            sources=["source1"],
            latency_ms=1500.5,
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.00045,
            metadata={"intent": "ANALYSIS"}
        )

        assert result.answer == "Test answer"
        assert result.model_used == "claude-sonnet"
        assert result.quality_score == 0.85
        assert result.latency_ms == 1500.5
        assert result.cost_usd == 0.00045


class TestQualityValidator:
    """Tests for QualityValidator class."""

    def test_score_good_response(self):
        """Test scoring a good response."""
        validator = QualityValidator()

        score = validator.score(
            response="This is a detailed and helpful response that addresses the question with relevant information from the context.",
            query="What is the capital of France?",
            sources=["Wikipedia"],
            context="France is a country in Europe. Its capital is Paris."
        )

        assert 0.6 <= score <= 1.0

    def test_score_empty_response(self):
        """Test scoring an empty response gets lower score."""
        validator = QualityValidator()

        score_empty = validator.score(
            response="",
            query="Test question",
            sources=[],
            context=""
        )

        score_good = validator.score(
            response="This is a helpful and detailed response.",
            query="Test question",
            sources=[],
            context=""
        )

        # Empty should score lower than good response
        assert score_empty < score_good

    def test_score_very_short_response(self):
        """Test scoring very short response."""
        validator = QualityValidator()

        score = validator.score(
            response="OK",
            query="Test question",
            sources=[],
            context=""
        )

        assert score < 0.8

    def test_score_response_uses_context(self):
        """Test response that uses context scores higher."""
        validator = QualityValidator()

        # Response uses context keywords
        score_with_context = validator.score(
            response="Based on the context, Python is a great programming language that is easy to learn.",
            query="Tell me about Python",
            sources=[],
            context="Python is a programming language. It is easy to learn."
        )

        # Response ignores context
        score_without_context = validator.score(
            response="I don't have any information about that topic.",
            query="Tell me about Python",
            sources=[],
            context="Python is a programming language. It is easy to learn."
        )

        assert score_with_context > score_without_context

    def test_score_no_context_provided(self):
        """Test scoring when no context was provided."""
        validator = QualityValidator()

        score = validator.score(
            response="This is a reasonable response to the question.",
            query="General question",
            sources=[],
            context=""
        )

        # Should still get reasonable score
        assert 0.5 <= score <= 1.0


class TestLLMOrchestrator:
    """Tests for LLMOrchestrator class."""

    def test_init_default(self):
        """Test initialization with defaults."""
        orchestrator = LLMOrchestrator()

        assert orchestrator.agents is not None
        assert orchestrator.prompt_builder is not None
        assert orchestrator.quality_validator is not None

    def test_init_custom_components(self):
        """Test initialization with custom components."""
        registry = AgentRegistry()
        builder = PromptBuilder()
        validator = QualityValidator()

        orchestrator = LLMOrchestrator(
            agent_registry=registry,
            prompt_builder=builder,
            quality_validator=validator
        )

        assert orchestrator.agents is registry
        assert orchestrator.prompt_builder is builder
        assert orchestrator.quality_validator is validator

    def test_select_model_analysis(self):
        """Test model selection for analysis intent."""
        orchestrator = LLMOrchestrator()

        model = orchestrator._select_model("ANALYSIS", {})

        assert model is not None
        # Should select claude-sonnet for analysis
        assert model == "claude-sonnet"

    def test_select_model_with_preference(self):
        """Test model selection honors user preference."""
        orchestrator = LLMOrchestrator()

        model = orchestrator._select_model(
            "ANALYSIS",
            {"preferred_model": "gpt-4o"}
        )

        assert model == "gpt-4o"

    def test_select_model_invalid_preference_fallback(self):
        """Test model selection falls back if preference invalid."""
        orchestrator = LLMOrchestrator()

        model = orchestrator._select_model(
            "ANALYSIS",
            {"preferred_model": "nonexistent-model"}
        )

        # Should fall back to intent-based selection
        assert model == "claude-sonnet"

    def test_estimate_tokens(self):
        """Test token estimation."""
        orchestrator = LLMOrchestrator()

        # Approximately 4 chars per token
        tokens = orchestrator._estimate_tokens("1234567890" * 10)  # 100 chars

        assert 20 <= tokens <= 30  # ~25 expected

    def test_estimate_tokens_empty(self):
        """Test token estimation for empty string."""
        orchestrator = LLMOrchestrator()

        tokens = orchestrator._estimate_tokens("")

        assert tokens >= 1  # Minimum 1

    @pytest.mark.asyncio
    async def test_answer_basic(self):
        """Test basic answer generation."""
        orchestrator = LLMOrchestrator()

        result = await orchestrator.answer(
            Query(
                text="What is Python?",
                intent="GENERAL",
                context="Python is a programming language."
            )
        )

        assert isinstance(result, OrchestratorResult)
        assert result.model_used in orchestrator.agents.list_agents()
        assert result.latency_ms > 0
        assert result.input_tokens > 0

    @pytest.mark.asyncio
    async def test_answer_with_model_override(self):
        """Test answer with model override."""
        orchestrator = LLMOrchestrator()

        result = await orchestrator.answer(
            Query(text="Test", intent="GENERAL"),
            model_override="gpt-4o"
        )

        assert result.model_used == "gpt-4o"

    @pytest.mark.asyncio
    async def test_answer_updates_stats(self):
        """Test that answer updates orchestrator stats."""
        orchestrator = LLMOrchestrator()

        initial_requests = orchestrator.stats["requests"]

        await orchestrator.answer(Query(text="Test"))

        assert orchestrator.stats["requests"] == initial_requests + 1
        assert orchestrator.stats["total_latency_ms"] > 0

    def test_get_stats(self):
        """Test getting orchestrator statistics."""
        orchestrator = LLMOrchestrator()

        stats = orchestrator.get_stats()

        assert "requests" in stats
        assert "total_latency_ms" in stats
        assert "total_cost_usd" in stats
        assert "avg_latency_ms" in stats
        assert "avg_cost_usd" in stats

    @pytest.mark.asyncio
    async def test_answer_includes_metadata(self):
        """Test that answer result includes metadata."""
        orchestrator = LLMOrchestrator()

        result = await orchestrator.answer(
            Query(
                text="Test question",
                intent="ANALYSIS",
                context="Test context"
            )
        )

        assert "intent" in result.metadata
        assert result.metadata["intent"] == "ANALYSIS"
        assert "prompt_template" in result.metadata
        assert "context_length" in result.metadata


class TestGlobalOrchestrator:
    """Tests for global orchestrator instance."""

    def test_get_llm_orchestrator_singleton(self):
        """Test that get_llm_orchestrator returns singleton."""
        orch1 = get_llm_orchestrator()
        orch2 = get_llm_orchestrator()

        assert orch1 is orch2

    def test_global_orchestrator_functional(self):
        """Test that global orchestrator is functional."""
        orchestrator = get_llm_orchestrator()

        assert orchestrator.agents is not None
        assert len(orchestrator.agents.list_agents()) > 0


class TestOrchestratorIntegration:
    """Integration tests for orchestrator with real components."""

    @pytest.mark.asyncio
    async def test_full_flow_memory_query(self):
        """Test full orchestration flow for memory query."""
        orchestrator = LLMOrchestrator()

        result = await orchestrator.answer(
            Query(
                text="What are my coding preferences?",
                user_id="test-user",
                intent="MEMORY_QUERY",
                context="User prefers Python and uses vim. User likes dark mode."
            )
        )

        assert isinstance(result, OrchestratorResult)
        assert result.answer is not None
        assert result.quality_score > 0
        assert result.cost_usd >= 0

    @pytest.mark.asyncio
    async def test_full_flow_analysis(self):
        """Test full orchestration flow for analysis."""
        orchestrator = LLMOrchestrator()

        result = await orchestrator.answer(
            Query(
                text="Analyze the performance of this approach",
                intent="ANALYSIS",
                context="The approach uses caching to reduce latency by 50%."
            )
        )

        assert isinstance(result, OrchestratorResult)
        assert result.metadata["intent"] == "ANALYSIS"

    @pytest.mark.asyncio
    async def test_full_flow_no_context(self):
        """Test orchestration when no context is available."""
        orchestrator = LLMOrchestrator()

        result = await orchestrator.answer(
            Query(
                text="What is machine learning?",
                intent="GENERAL",
                context=""  # No context
            )
        )

        assert isinstance(result, OrchestratorResult)
        # Should still produce an answer
        assert result.answer is not None
