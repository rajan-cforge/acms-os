"""End-to-End tests for LLM Orchestrator.

Tests the full orchestration flow:
1. Model selection based on intent
2. Prompt building from templates
3. Quality validation

Blueprint Section 6 - Integration Tests
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.llm.orchestrator import (
    LLMOrchestrator,
    OrchestratorResult,
    Query,
    QualityValidator
)
from src.llm.agent_registry import AgentRegistry
from src.llm.prompt_builder import PromptBuilder


class TestOrchestratorIntentRouting:
    """Test orchestrator routes to correct models based on intent."""

    def test_analysis_intent_selects_analysis_model(self):
        """Test that ANALYSIS intent selects appropriate model."""
        orchestrator = LLMOrchestrator()

        model = orchestrator._select_model("ANALYSIS", {})

        # Should select model good at analysis
        agent = orchestrator.agents.get_agent(model)
        assert agent is not None
        assert "analysis" in agent.strengths or "reasoning" in agent.strengths

    def test_creative_intent_selects_creative_model(self):
        """Test that CREATIVE intent selects appropriate model."""
        orchestrator = LLMOrchestrator()

        model = orchestrator._select_model("CREATIVE", {})

        agent = orchestrator.agents.get_agent(model)
        assert agent is not None

    def test_simple_intent_selects_cheap_model(self):
        """Test that SIMPLE intent selects cost-effective model."""
        orchestrator = LLMOrchestrator()

        model = orchestrator._select_model("SIMPLE", {})

        agent = orchestrator.agents.get_agent(model)
        assert agent is not None
        assert "cheap" in agent.strengths or "fast" in agent.strengths


class TestOrchestratorPromptBuilding:
    """Test orchestrator builds appropriate prompts."""

    def test_prompt_includes_question(self):
        """Test that built prompt includes the question."""
        orchestrator = LLMOrchestrator()

        prompt = orchestrator.prompt_builder.build_for_intent(
            intent="ANALYSIS",
            question="What is machine learning?",
            context=""
        )

        assert "machine learning" in prompt.lower()

    def test_prompt_includes_context(self):
        """Test that built prompt includes context when provided."""
        orchestrator = LLMOrchestrator()

        context = "Machine learning is a subset of AI."
        prompt = orchestrator.prompt_builder.build_for_intent(
            intent="MEMORY_QUERY",
            question="What is ML?",
            context=context
        )

        assert "subset of AI" in prompt

    def test_different_intents_use_different_templates(self):
        """Test that different intents produce different prompts."""
        orchestrator = LLMOrchestrator()

        analysis_prompt = orchestrator.prompt_builder.build_for_intent(
            intent="ANALYSIS",
            question="Test question",
            context=""
        )

        creative_prompt = orchestrator.prompt_builder.build_for_intent(
            intent="CREATIVE",
            question="Test question",
            context=""
        )

        # Templates should be different
        # (They'll contain the same question but different instructions)
        assert analysis_prompt != creative_prompt


class TestOrchestratorQualityValidation:
    """Test orchestrator validates response quality."""

    def test_quality_score_range(self):
        """Test quality scores are in valid range."""
        validator = QualityValidator()

        score = validator.score(
            response="This is a test response.",
            query="What is this?",
            sources=[],
            context=""
        )

        assert 0 <= score <= 1

    def test_better_response_scores_higher(self):
        """Test that better responses score higher."""
        validator = QualityValidator()

        context = "Python is a programming language used for web development."

        # Good response uses context
        good_score = validator.score(
            response="Python is a programming language that is commonly used for web development.",
            query="What is Python?",
            sources=[],
            context=context
        )

        # Poor response ignores context
        poor_score = validator.score(
            response="I don't know.",
            query="What is Python?",
            sources=[],
            context=context
        )

        assert good_score > poor_score


class TestOrchestratorFullFlow:
    """End-to-end tests for full orchestrator flow."""

    @pytest.mark.asyncio
    async def test_answer_produces_result(self):
        """Test that answer() produces an OrchestratorResult."""
        orchestrator = LLMOrchestrator()

        result = await orchestrator.answer(
            Query(
                text="What is Python?",
                intent="GENERAL",
                context="Python is a programming language."
            )
        )

        assert isinstance(result, OrchestratorResult)
        assert result.answer is not None
        assert result.model_used is not None
        assert 0 <= result.quality_score <= 1
        assert result.latency_ms >= 0
        assert result.cost_usd >= 0

    @pytest.mark.asyncio
    async def test_answer_tracks_statistics(self):
        """Test that answer() updates statistics."""
        orchestrator = LLMOrchestrator()

        initial_requests = orchestrator.stats["requests"]

        await orchestrator.answer(Query(text="Test"))
        await orchestrator.answer(Query(text="Test 2"))

        assert orchestrator.stats["requests"] == initial_requests + 2
        assert orchestrator.stats["total_latency_ms"] > 0

    @pytest.mark.asyncio
    async def test_model_override_respected(self):
        """Test that model_override parameter is respected."""
        orchestrator = LLMOrchestrator()

        result = await orchestrator.answer(
            Query(text="Test", intent="ANALYSIS"),
            model_override="gpt-4o"
        )

        assert result.model_used == "gpt-4o"

    @pytest.mark.asyncio
    async def test_user_preference_respected(self):
        """Test that user preferences affect model selection."""
        orchestrator = LLMOrchestrator()

        result = await orchestrator.answer(
            Query(
                text="Test",
                intent="GENERAL",
                preferences={"preferred_model": "gemini-flash"}
            )
        )

        assert result.model_used == "gemini-flash"

    @pytest.mark.asyncio
    async def test_metadata_included_in_result(self):
        """Test that result includes relevant metadata."""
        orchestrator = LLMOrchestrator()

        result = await orchestrator.answer(
            Query(
                text="Test question",
                intent="MEMORY_QUERY",
                context="Some context here"
            )
        )

        assert "intent" in result.metadata
        assert result.metadata["intent"] == "MEMORY_QUERY"
        assert "prompt_template" in result.metadata
        assert "context_length" in result.metadata


class TestOrchestratorCostTracking:
    """Test orchestrator tracks costs correctly."""

    @pytest.mark.asyncio
    async def test_cost_calculated(self):
        """Test that cost is calculated for each request."""
        orchestrator = LLMOrchestrator()

        result = await orchestrator.answer(Query(text="Test"))

        # Cost should be calculated (may be 0 for very small requests)
        assert result.cost_usd >= 0
        assert isinstance(result.cost_usd, float)

    @pytest.mark.asyncio
    async def test_total_cost_tracked(self):
        """Test that total cost is accumulated."""
        orchestrator = LLMOrchestrator()

        initial_cost = orchestrator.stats["total_cost_usd"]

        await orchestrator.answer(Query(text="Test 1"))
        await orchestrator.answer(Query(text="Test 2"))

        assert orchestrator.stats["total_cost_usd"] >= initial_cost

    def test_cost_estimation_realistic(self):
        """Test that cost estimation is realistic."""
        registry = AgentRegistry()

        # 10K input, 1K output for claude-sonnet
        # Should be around $0.045
        cost = registry.estimate_cost("claude-sonnet", 10000, 1000)

        assert 0.04 < cost < 0.05


class TestOrchestratorErrorHandling:
    """Test orchestrator handles errors gracefully."""

    @pytest.mark.asyncio
    async def test_handles_empty_query(self):
        """Test handling of empty query."""
        orchestrator = LLMOrchestrator()

        result = await orchestrator.answer(Query(text=""))

        # Should not crash, returns some result
        assert result is not None

    @pytest.mark.asyncio
    async def test_handles_very_long_query(self):
        """Test handling of very long query."""
        orchestrator = LLMOrchestrator()

        long_query = "What is Python? " * 100

        result = await orchestrator.answer(Query(text=long_query))

        assert result is not None

    @pytest.mark.asyncio
    async def test_handles_unknown_intent(self):
        """Test handling of unknown intent."""
        orchestrator = LLMOrchestrator()

        result = await orchestrator.answer(
            Query(text="Test", intent="UNKNOWN_INTENT_TYPE")
        )

        # Should fall back gracefully
        assert result is not None
        assert result.model_used is not None


class TestOrchestratorWithRealComponents:
    """Integration tests using real (not mocked) components."""

    def test_agent_registry_integration(self):
        """Test orchestrator integrates with agent registry."""
        orchestrator = LLMOrchestrator()

        # Should have access to all agents
        agents = orchestrator.agents.list_agents()

        assert len(agents) > 0
        assert "claude-sonnet" in agents
        assert "gpt-4o" in agents

    def test_prompt_builder_integration(self):
        """Test orchestrator integrates with prompt builder."""
        orchestrator = LLMOrchestrator()

        # Should have access to all templates
        templates = orchestrator.prompt_builder.list_templates()

        assert len(templates) > 0
        assert "retrieval_augmented" in templates

    def test_quality_validator_integration(self):
        """Test orchestrator integrates with quality validator."""
        orchestrator = LLMOrchestrator()

        # Quality validator should work
        score = orchestrator.quality_validator.score(
            response="Test response",
            query="Test query",
            sources=[],
            context=""
        )

        assert 0 <= score <= 1
