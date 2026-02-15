"""Agent Registry - Central repository of LLM agent information.

Defines each model's capabilities, costs, and strengths.
Used by LLMOrchestrator for model selection.

Blueprint Section 5.1 - Agent Registry
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """LLM Provider identifiers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    OLLAMA = "ollama"


@dataclass
class AgentInfo:
    """Information about an LLM agent.

    Attributes:
        name: Full model name (e.g., "claude-sonnet-4-20250514")
        provider: Provider enum (anthropic, openai, google, ollama)
        cost_per_million_input: Cost per 1M input tokens in USD
        cost_per_million_output: Cost per 1M output tokens in USD
        max_tokens: Maximum context window size
        max_output_tokens: Maximum output tokens
        strengths: List of task types this model excels at
        default_temperature: Recommended temperature for this model
        supports_streaming: Whether model supports streaming responses
        supports_tools: Whether model supports tool/function calling
    """
    name: str
    provider: ModelProvider
    cost_per_million_input: float
    cost_per_million_output: float
    max_tokens: int
    max_output_tokens: int
    strengths: List[str]
    default_temperature: float
    supports_streaming: bool = True
    supports_tools: bool = True


# Agent Registry - Single source of truth for model capabilities
AGENTS: Dict[str, AgentInfo] = {
    "claude-sonnet": AgentInfo(
        name="claude-sonnet-4-20250514",
        provider=ModelProvider.ANTHROPIC,
        cost_per_million_input=3.0,
        cost_per_million_output=15.0,
        max_tokens=200_000,
        max_output_tokens=8192,
        strengths=["analysis", "synthesis", "reasoning", "memory_query", "long_context"],
        default_temperature=0.3,
        supports_streaming=True,
        supports_tools=True,
    ),
    "claude-opus": AgentInfo(
        name="claude-opus-4-20250514",
        provider=ModelProvider.ANTHROPIC,
        cost_per_million_input=15.0,
        cost_per_million_output=75.0,
        max_tokens=200_000,
        max_output_tokens=8192,
        strengths=["complex_reasoning", "code_generation", "critical_analysis"],
        default_temperature=0.2,
        supports_streaming=True,
        supports_tools=True,
    ),
    "gpt-5.1": AgentInfo(
        name="gpt-5.1",
        provider=ModelProvider.OPENAI,
        cost_per_million_input=1.25,
        cost_per_million_output=10.0,
        max_tokens=128_000,
        max_output_tokens=16384,
        strengths=["general", "creative", "conversation", "code", "reasoning"],
        default_temperature=0.5,
        supports_streaming=True,
        supports_tools=True,
    ),
    "gpt-4o-mini": AgentInfo(
        name="gpt-4o-mini",
        provider=ModelProvider.OPENAI,
        cost_per_million_input=0.15,
        cost_per_million_output=0.6,
        max_tokens=128_000,
        max_output_tokens=16384,
        strengths=["cheap", "fast", "simple_tasks", "query_rewriting"],
        default_temperature=0.3,
        supports_streaming=True,
        supports_tools=True,
    ),
    "gemini-flash": AgentInfo(
        name="gemini-3-flash-preview",
        provider=ModelProvider.GOOGLE,
        cost_per_million_input=0.50,
        cost_per_million_output=3.0,
        max_tokens=1_000_000,
        max_output_tokens=8192,
        strengths=["fast", "research", "web_search", "factual", "agentic"],
        default_temperature=0.4,
        supports_streaming=True,
        supports_tools=True,
    ),
    "gemini-pro": AgentInfo(
        name="gemini-3-pro-preview",
        provider=ModelProvider.GOOGLE,
        cost_per_million_input=2.0,
        cost_per_million_output=12.0,
        max_tokens=1_000_000,
        max_output_tokens=8192,
        strengths=["long_context", "research", "analysis", "multimodal", "reasoning"],
        default_temperature=0.4,
        supports_streaming=True,
        supports_tools=True,
    ),
    "ollama-llama3": AgentInfo(
        name="llama3:8b",
        provider=ModelProvider.OLLAMA,
        cost_per_million_input=0.0,  # Free (local)
        cost_per_million_output=0.0,
        max_tokens=8192,
        max_output_tokens=4096,
        strengths=["free", "private", "local"],
        default_temperature=0.7,
        supports_streaming=True,
        supports_tools=False,
    ),
}


class AgentRegistry:
    """Registry for LLM agent information and selection.

    Example:
        registry = AgentRegistry()
        agent = registry.get_agent("claude-sonnet")
        cost = registry.estimate_cost("claude-sonnet", input_tokens=1000, output_tokens=500)
    """

    def __init__(self, agents: Optional[Dict[str, AgentInfo]] = None):
        """Initialize registry.

        Args:
            agents: Optional custom agents dict (for testing)
        """
        self.agents = agents or AGENTS.copy()
        logger.info(f"[AgentRegistry] Initialized with {len(self.agents)} agents")

    def get_agent(self, key: str) -> Optional[AgentInfo]:
        """Get agent info by key.

        Args:
            key: Agent key (e.g., "claude-sonnet", "gpt-5.1")

        Returns:
            AgentInfo or None if not found
        """
        return self.agents.get(key)

    def list_agents(self) -> List[str]:
        """List all available agent keys.

        Returns:
            List of agent keys
        """
        return list(self.agents.keys())

    def find_by_strength(self, strength: str) -> List[str]:
        """Find agents by strength.

        Args:
            strength: Strength to search for (e.g., "analysis", "cheap")

        Returns:
            List of agent keys with this strength
        """
        matches = []
        for key, agent in self.agents.items():
            if strength in agent.strengths:
                matches.append(key)
        return matches

    def find_cheapest(self, min_context: int = 0) -> Optional[str]:
        """Find cheapest agent meeting context requirements.

        Args:
            min_context: Minimum context window size needed

        Returns:
            Agent key or None
        """
        candidates = [
            (k, a) for k, a in self.agents.items()
            if a.max_tokens >= min_context
        ]

        if not candidates:
            return None

        # Sort by total cost (input + output)
        candidates.sort(
            key=lambda x: x[1].cost_per_million_input + x[1].cost_per_million_output
        )

        return candidates[0][0]

    def estimate_cost(
        self,
        agent_key: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Estimate cost for a request.

        Args:
            agent_key: Agent key
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        agent = self.get_agent(agent_key)
        if not agent:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * agent.cost_per_million_input
        output_cost = (output_tokens / 1_000_000) * agent.cost_per_million_output

        return input_cost + output_cost

    def select_for_intent(self, intent: str) -> str:
        """Select best agent for an intent.

        Args:
            intent: Intent type (analysis, creative, research, etc.)

        Returns:
            Agent key
        """
        # Intent → preferred strengths mapping
        intent_strengths = {
            "ANALYSIS": ["analysis", "reasoning"],
            "CREATIVE": ["creative", "general"],
            "RESEARCH": ["research", "web_search"],
            "CODE_GENERATION": ["code_generation", "code"],
            "MEMORY_QUERY": ["memory_query", "synthesis"],
            "SIMPLE": ["cheap", "fast"],
        }

        strengths = intent_strengths.get(intent.upper(), ["general"])

        # Find agents with matching strengths
        for strength in strengths:
            matches = self.find_by_strength(strength)
            if matches:
                logger.debug(f"[AgentRegistry] Intent '{intent}' → agent '{matches[0]}'")
                return matches[0]

        # Default to claude-sonnet
        return "claude-sonnet"


# Global registry instance
_registry_instance: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    """Get global agent registry instance.

    Returns:
        AgentRegistry: Global instance
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AgentRegistry()
    return _registry_instance
