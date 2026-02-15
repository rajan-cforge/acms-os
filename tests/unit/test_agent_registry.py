"""Tests for Agent Registry.

Tests model information, cost estimation, and intent-based selection.
"""

import pytest
from src.llm.agent_registry import (
    AgentRegistry,
    AgentInfo,
    ModelProvider,
    AGENTS,
    get_agent_registry
)


class TestAgentInfo:
    """Tests for AgentInfo dataclass."""

    def test_agent_info_creation(self):
        """Test creating AgentInfo with all fields."""
        agent = AgentInfo(
            name="test-model",
            provider=ModelProvider.OPENAI,
            cost_per_million_input=1.0,
            cost_per_million_output=2.0,
            max_tokens=100_000,
            max_output_tokens=4096,
            strengths=["analysis", "code"],
            default_temperature=0.5,
            supports_streaming=True,
            supports_tools=True
        )

        assert agent.name == "test-model"
        assert agent.provider == ModelProvider.OPENAI
        assert agent.cost_per_million_input == 1.0
        assert agent.cost_per_million_output == 2.0
        assert agent.max_tokens == 100_000
        assert "analysis" in agent.strengths

    def test_default_values(self):
        """Test default values for optional fields."""
        agent = AgentInfo(
            name="test-model",
            provider=ModelProvider.OPENAI,
            cost_per_million_input=1.0,
            cost_per_million_output=2.0,
            max_tokens=100_000,
            max_output_tokens=4096,
            strengths=["general"],
            default_temperature=0.5
        )

        assert agent.supports_streaming is True
        assert agent.supports_tools is True


class TestAgentRegistry:
    """Tests for AgentRegistry class."""

    def test_get_agent_exists(self):
        """Test getting an existing agent."""
        registry = AgentRegistry()

        agent = registry.get_agent("claude-sonnet")

        assert agent is not None
        assert agent.name == "claude-sonnet-4-20250514"
        assert agent.provider == ModelProvider.ANTHROPIC

    def test_get_agent_not_exists(self):
        """Test getting non-existent agent returns None."""
        registry = AgentRegistry()

        agent = registry.get_agent("nonexistent-model")

        assert agent is None

    def test_list_agents(self):
        """Test listing all agents."""
        registry = AgentRegistry()

        agents = registry.list_agents()

        assert isinstance(agents, list)
        assert len(agents) > 0
        assert "claude-sonnet" in agents
        assert "gpt-4o" in agents

    def test_find_by_strength_analysis(self):
        """Test finding agents by strength."""
        registry = AgentRegistry()

        matches = registry.find_by_strength("analysis")

        assert len(matches) > 0
        assert "claude-sonnet" in matches

    def test_find_by_strength_cheap(self):
        """Test finding cheap agents."""
        registry = AgentRegistry()

        matches = registry.find_by_strength("cheap")

        assert len(matches) > 0
        assert "gemini-flash" in matches
        assert "gpt-4o-mini" in matches

    def test_find_by_strength_none_found(self):
        """Test finding by non-existent strength."""
        registry = AgentRegistry()

        matches = registry.find_by_strength("nonexistent")

        assert matches == []

    def test_find_cheapest(self):
        """Test finding cheapest agent."""
        registry = AgentRegistry()

        cheapest = registry.find_cheapest()

        assert cheapest is not None
        # Ollama is free
        assert cheapest == "ollama-llama3"

    def test_find_cheapest_with_context_requirement(self):
        """Test finding cheapest agent with context requirement."""
        registry = AgentRegistry()

        # Require at least 100K context (ollama only has 8K)
        cheapest = registry.find_cheapest(min_context=100_000)

        assert cheapest is not None
        assert cheapest != "ollama-llama3"  # Ollama excluded
        # Should be gemini-flash (0.075 + 0.3 = 0.375)
        assert cheapest == "gemini-flash"

    def test_estimate_cost_zero_tokens(self):
        """Test cost estimation with zero tokens."""
        registry = AgentRegistry()

        cost = registry.estimate_cost("claude-sonnet", 0, 0)

        assert cost == 0.0

    def test_estimate_cost_realistic(self):
        """Test realistic cost estimation."""
        registry = AgentRegistry()

        # 10K input, 1K output for claude-sonnet
        # Input: 10K / 1M * 3.0 = 0.03
        # Output: 1K / 1M * 15.0 = 0.015
        # Total: 0.045
        cost = registry.estimate_cost("claude-sonnet", 10_000, 1_000)

        assert 0.04 < cost < 0.05

    def test_estimate_cost_unknown_agent(self):
        """Test cost estimation for unknown agent."""
        registry = AgentRegistry()

        cost = registry.estimate_cost("nonexistent", 1000, 500)

        assert cost == 0.0

    def test_select_for_intent_analysis(self):
        """Test model selection for analysis intent."""
        registry = AgentRegistry()

        agent = registry.select_for_intent("ANALYSIS")

        assert agent is not None
        # Should select an agent with analysis strength
        agent_info = registry.get_agent(agent)
        assert "analysis" in agent_info.strengths or "reasoning" in agent_info.strengths

    def test_select_for_intent_creative(self):
        """Test model selection for creative intent."""
        registry = AgentRegistry()

        agent = registry.select_for_intent("CREATIVE")

        assert agent is not None

    def test_select_for_intent_simple(self):
        """Test model selection for simple tasks."""
        registry = AgentRegistry()

        agent = registry.select_for_intent("SIMPLE")

        assert agent is not None
        # Should select cheap/fast agent
        agent_info = registry.get_agent(agent)
        assert "cheap" in agent_info.strengths or "fast" in agent_info.strengths

    def test_select_for_intent_unknown(self):
        """Test model selection for unknown intent defaults gracefully."""
        registry = AgentRegistry()

        agent = registry.select_for_intent("UNKNOWN_INTENT")

        # Should return an agent (falls back to "general" strength)
        assert agent is not None
        # gpt-4o has "general" in strengths so it's selected
        agent_info = registry.get_agent(agent)
        assert agent_info is not None


class TestGlobalRegistry:
    """Tests for global registry instance."""

    def test_get_agent_registry_singleton(self):
        """Test that get_agent_registry returns singleton."""
        registry1 = get_agent_registry()
        registry2 = get_agent_registry()

        assert registry1 is registry2

    def test_global_registry_has_agents(self):
        """Test that global registry is populated."""
        registry = get_agent_registry()

        assert len(registry.list_agents()) > 0


class TestBuiltInAgents:
    """Tests for built-in agent definitions."""

    def test_claude_sonnet_in_registry(self):
        """Test claude-sonnet is properly defined."""
        assert "claude-sonnet" in AGENTS

        agent = AGENTS["claude-sonnet"]
        assert agent.provider == ModelProvider.ANTHROPIC
        assert agent.max_tokens >= 200_000
        assert "analysis" in agent.strengths

    def test_gpt4o_in_registry(self):
        """Test gpt-4o is properly defined."""
        assert "gpt-4o" in AGENTS

        agent = AGENTS["gpt-4o"]
        assert agent.provider == ModelProvider.OPENAI
        assert agent.max_tokens >= 128_000

    def test_gemini_flash_in_registry(self):
        """Test gemini-flash is properly defined."""
        assert "gemini-flash" in AGENTS

        agent = AGENTS["gemini-flash"]
        assert agent.provider == ModelProvider.GOOGLE
        assert "cheap" in agent.strengths

    def test_all_agents_have_required_fields(self):
        """Test all agents have required fields populated."""
        for key, agent in AGENTS.items():
            assert agent.name, f"{key} missing name"
            assert agent.provider, f"{key} missing provider"
            assert agent.max_tokens > 0, f"{key} missing max_tokens"
            assert len(agent.strengths) > 0, f"{key} missing strengths"
