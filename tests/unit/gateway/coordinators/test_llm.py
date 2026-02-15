"""Unit tests for LLMCoordinator.

Tests verify that:
1. Agent selection works based on intent
2. Prompts are built correctly
3. Streaming works with events
4. Circuit breaker protection is active
5. Fallback agents are tried on failure

TDD spec from ACMS_Combined_Code_Review_Refactor_TDD_Spec.md
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from src.gateway.coordinators.llm import (
    LLMCoordinator, StreamEvent, StreamEventType, PromptConfig
)
from src.gateway.coordinators.query_planner import QueryPlan
from src.gateway.coordinators.retrieval import RetrievalResult, RetrievalSource
from src.gateway.circuit_breaker import CircuitOpenError


@pytest.fixture
def mock_agent():
    """Mock LLM agent with streaming."""
    agent = Mock()

    async def mock_stream(prompt):
        yield "Hello"
        yield " "
        yield "world"

    agent.stream = mock_stream
    return agent


@pytest.fixture
def mock_failing_agent():
    """Mock LLM agent that fails."""
    agent = Mock()

    async def mock_stream(prompt):
        raise Exception("LLM error")
        yield  # Make it a generator

    agent.stream = mock_stream
    return agent


@pytest.fixture
def mock_agent_selector():
    """Mock agent selector."""
    selector = Mock()
    selector.select = Mock(return_value="claude")
    return selector


@pytest.fixture
def query_plan():
    """Sample query plan."""
    return QueryPlan(
        original_query="test query",
        sanitized_query="test query",
        augmented_queries=["test query"],
        intent="general",
        intent_confidence=0.85,
        allow_web_search=False,
        needs_web_search=False,
        web_search_reason=None
    )


@pytest.fixture
def retrieval_result():
    """Sample retrieval result."""
    return RetrievalResult(
        context="test context",
        sanitized_context="sanitized test context",
        sources=[],
        web_results=[],
        cache_hits=0,
        knowledge_hits=0,
        memory_hits=0,
        web_hits=0,
        total_sources=0,
        is_context_clean=True,
        sanitization_count=0,
        trace_id="test123"
    )


@pytest.fixture
def coordinator(mock_agent, mock_agent_selector):
    """Get LLMCoordinator with mocks."""
    return LLMCoordinator(
        agents={"claude": mock_agent},
        agent_selector=mock_agent_selector,
        default_agent="claude",
        fallback_agents=["claude", "gpt"],
        enable_circuit_breaker=False  # Disable for unit tests
    )


class TestLLMCoordinatorBasic:
    """Test basic LLMCoordinator functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stream_returns_events(self, coordinator, query_plan, retrieval_result):
        """stream() should yield StreamEvent objects."""
        events = []
        async for event in coordinator.stream(
            plan=query_plan,
            retrieval_result=retrieval_result,
            user_id="user1"
        ):
            events.append(event)
        assert len(events) > 0
        assert all(isinstance(e, StreamEvent) for e in events)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stream_starts_with_started_event(self, coordinator, query_plan, retrieval_result):
        """First event should be STARTED."""
        events = []
        async for event in coordinator.stream(
            plan=query_plan,
            retrieval_result=retrieval_result,
            user_id="user1"
        ):
            events.append(event)
        assert events[0].event_type == StreamEventType.STARTED

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stream_ends_with_completed_event(self, coordinator, query_plan, retrieval_result):
        """Last event should be COMPLETED."""
        events = []
        async for event in coordinator.stream(
            plan=query_plan,
            retrieval_result=retrieval_result,
            user_id="user1"
        ):
            events.append(event)
        assert events[-1].event_type == StreamEventType.COMPLETED
        assert events[-1].is_final is True


class TestAgentSelection:
    """Test agent selection."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_uses_agent_selector(self, coordinator, query_plan, retrieval_result, mock_agent_selector):
        """Should use agent selector when available."""
        events = []
        async for event in coordinator.stream(
            plan=query_plan,
            retrieval_result=retrieval_result,
            user_id="user1"
        ):
            events.append(event)
        # Agent selector should have been called
        mock_agent_selector.select.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_respects_preferred_agent(self, coordinator, query_plan, retrieval_result):
        """Should use preferred_agent when provided."""
        events = []
        async for event in coordinator.stream(
            plan=query_plan,
            retrieval_result=retrieval_result,
            user_id="user1",
            preferred_agent="claude"
        ):
            events.append(event)
        # Started event should have correct agent
        assert events[0].agent == "claude"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_on_unknown_agent(self, coordinator, query_plan, retrieval_result):
        """Should return error event for unknown agent."""
        events = []
        async for event in coordinator.stream(
            plan=query_plan,
            retrieval_result=retrieval_result,
            user_id="user1",
            preferred_agent="unknown_agent"
        ):
            events.append(event)
        assert events[0].event_type == StreamEventType.ERROR
        assert "not available" in events[0].error


class TestPromptBuilding:
    """Test prompt building."""

    @pytest.mark.unit
    def test_build_prompt_basic(self, coordinator):
        """Should build basic prompt."""
        config = PromptConfig()
        prompt = coordinator._build_prompt("question", "context", config)
        assert "question" in prompt
        assert "context" in prompt

    @pytest.mark.unit
    def test_build_prompt_with_system(self, coordinator):
        """Should include system prompt."""
        config = PromptConfig(system_prompt="You are a helpful assistant.")
        prompt = coordinator._build_prompt("question", "context", config)
        assert "helpful assistant" in prompt

    @pytest.mark.unit
    def test_build_prompt_truncates_long_context(self, coordinator):
        """Should truncate long context."""
        config = PromptConfig(max_context_chars=100)
        long_context = "x" * 200
        prompt = coordinator._build_prompt("question", long_context, config)
        assert "[Context truncated...]" in prompt


class TestStreaming:
    """Test streaming functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_streams_token_events(self, coordinator, query_plan, retrieval_result):
        """Should yield TOKEN events during streaming."""
        events = []
        async for event in coordinator.stream(
            plan=query_plan,
            retrieval_result=retrieval_result,
            user_id="user1"
        ):
            events.append(event)

        token_events = [e for e in events if e.event_type == StreamEventType.TOKEN]
        assert len(token_events) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_token_count_increases(self, coordinator, query_plan, retrieval_result):
        """Token count should increase with each token."""
        events = []
        async for event in coordinator.stream(
            plan=query_plan,
            retrieval_result=retrieval_result,
            user_id="user1"
        ):
            events.append(event)

        token_events = [e for e in events if e.event_type == StreamEventType.TOKEN]
        if token_events:
            counts = [e.token_count for e in token_events]
            assert counts == sorted(counts)  # Increasing order

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_completed_has_full_response(self, coordinator, query_plan, retrieval_result):
        """COMPLETED event should have full response."""
        events = []
        async for event in coordinator.stream(
            plan=query_plan,
            retrieval_result=retrieval_result,
            user_id="user1"
        ):
            events.append(event)

        completed = [e for e in events if e.event_type == StreamEventType.COMPLETED]
        assert len(completed) == 1
        assert completed[0].content == "Hello world"


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_event_on_failure(self, mock_failing_agent, mock_agent_selector, query_plan, retrieval_result):
        """Should yield ERROR event on LLM failure."""
        coordinator = LLMCoordinator(
            agents={"claude": mock_failing_agent},
            agent_selector=mock_agent_selector,
            default_agent="claude",
            fallback_agents=[],
            enable_circuit_breaker=False
        )

        events = []
        async for event in coordinator.stream(
            plan=query_plan,
            retrieval_result=retrieval_result,
            user_id="user1"
        ):
            events.append(event)

        error_events = [e for e in events if e.event_type == StreamEventType.ERROR]
        assert len(error_events) > 0


class TestFallback:
    """Test fallback agent functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_tries_fallback_on_circuit_open(
        self, mock_agent, mock_agent_selector, query_plan, retrieval_result
    ):
        """Should try fallback agents when circuit breaker trips."""
        # Create an agent that triggers CircuitOpenError
        circuit_open_agent = Mock()

        async def raise_circuit_open(prompt):
            raise CircuitOpenError("claude", 30.0)
            yield  # Make it a generator

        circuit_open_agent.stream = raise_circuit_open

        coordinator = LLMCoordinator(
            agents={"claude": circuit_open_agent, "gpt": mock_agent},
            agent_selector=mock_agent_selector,
            default_agent="claude",
            fallback_agents=["claude", "gpt"],
            enable_circuit_breaker=True
        )

        events = []
        async for event in coordinator.stream(
            plan=query_plan,
            retrieval_result=retrieval_result,
            user_id="user1"
        ):
            events.append(event)

        # Should have completed with fallback agent
        completed = [e for e in events if e.event_type == StreamEventType.COMPLETED]
        assert len(completed) == 1
        assert completed[0].agent == "gpt"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_error_event_when_all_fallbacks_fail(
        self, mock_failing_agent, mock_agent_selector, query_plan, retrieval_result
    ):
        """Should yield error when all fallbacks fail."""
        coordinator = LLMCoordinator(
            agents={"claude": mock_failing_agent},
            agent_selector=mock_agent_selector,
            default_agent="claude",
            fallback_agents=["claude"],
            enable_circuit_breaker=False
        )

        events = []
        async for event in coordinator.stream(
            plan=query_plan,
            retrieval_result=retrieval_result,
            user_id="user1"
        ):
            events.append(event)

        # Should have error event
        error_events = [e for e in events if e.event_type == StreamEventType.ERROR]
        assert len(error_events) > 0


class TestStreamEventSerialization:
    """Test StreamEvent serialization."""

    @pytest.mark.unit
    def test_to_dict(self):
        """StreamEvent should serialize to dict."""
        event = StreamEvent(
            event_type=StreamEventType.TOKEN,
            content="hello",
            agent="claude",
            token_count=1,
            is_final=False
        )
        d = event.to_dict()

        assert d["type"] == "token"
        assert d["content"] == "hello"
        assert d["agent"] == "claude"
        assert d["token_count"] == 1

    @pytest.mark.unit
    def test_to_dict_with_error(self):
        """StreamEvent error should serialize."""
        event = StreamEvent(
            event_type=StreamEventType.ERROR,
            error="Something went wrong"
        )
        d = event.to_dict()

        assert d["type"] == "error"
        assert d["error"] == "Something went wrong"


class TestAgentHealth:
    """Test agent health reporting."""

    @pytest.mark.unit
    def test_get_available_agents(self, coordinator):
        """Should list available agents."""
        agents = coordinator.get_available_agents()
        assert "claude" in agents

    @pytest.mark.unit
    def test_get_agent_health(self, coordinator):
        """Should report agent health status."""
        health = coordinator.get_agent_health()
        assert "claude" in health
        assert "state" in health["claude"] or "circuit_breaker" in health["claude"]


class TestPromptConfig:
    """Test PromptConfig defaults."""

    @pytest.mark.unit
    def test_default_values(self):
        """PromptConfig should have sensible defaults."""
        config = PromptConfig()
        assert config.max_context_chars == 8000
        assert config.include_sources is True

    @pytest.mark.unit
    def test_custom_values(self):
        """PromptConfig should accept custom values."""
        config = PromptConfig(
            system_prompt="Custom prompt",
            max_context_chars=4000,
            include_sources=False
        )
        assert config.system_prompt == "Custom prompt"
        assert config.max_context_chars == 4000
        assert config.include_sources is False
