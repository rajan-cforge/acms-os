"""Agent selection based on intent type.

Maps IntentType to the most appropriate AgentType based on:
- Agent capabilities (terminal, code, creative, research)
- Cost optimization (ChatGPT cheaper for creative)
- Quality (Claude Sonnet best for analysis)
"""

import logging
from typing import Optional
from src.gateway.models import IntentType, AgentType

logger = logging.getLogger(__name__)


# Intent → Agent routing rules
# NOTE: CLAUDE_CODE is currently a STUB (Week 4 TODO)
# Route code/terminal intents to CLAUDE_SONNET until implemented
AGENT_ROUTING = {
    IntentType.TERMINAL_COMMAND: AgentType.CLAUDE_SONNET,  # TODO: CLAUDE_CODE when implemented
    IntentType.CODE_GENERATION: AgentType.CLAUDE_SONNET,   # TODO: CLAUDE_CODE when implemented
    IntentType.FILE_OPERATION: AgentType.CLAUDE_SONNET,    # TODO: CLAUDE_CODE when implemented
    IntentType.ANALYSIS: AgentType.CLAUDE_SONNET,
    IntentType.CREATIVE: AgentType.CHATGPT,  # Cheaper, good enough for creative
    IntentType.RESEARCH: AgentType.GEMINI,  # Has web search capabilities
    IntentType.MEMORY_QUERY: AgentType.CLAUDE_SONNET,  # Best for synthesis
}


class AgentSelector:
    """Selects the best agent for a given intent."""

    def __init__(self, available_agents: Optional[list] = None):
        """Initialize agent selector with routing rules.

        Args:
            available_agents: List of AgentType that are actually initialized
        """
        self.routing = AGENT_ROUTING
        self.available_agents = available_agents or []
        logger.info("AgentSelector initialized with %d routing rules, %d available agents",
                    len(self.routing), len(self.available_agents))

    def set_available_agents(self, available_agents: list):
        """Update available agents list."""
        self.available_agents = available_agents
        logger.info("Available agents updated: %s", [a.value for a in available_agents])

    def select_agent(
        self,
        intent: IntentType,
        manual_override: Optional[AgentType] = None
    ) -> AgentType:
        """Select the best agent for an intent.

        Args:
            intent: Detected intent type
            manual_override: Optional user-specified agent (bypasses routing)

        Returns:
            AgentType: Selected agent

        Routing Logic:
            1. If manual_override provided and available, use it
            2. Otherwise, use AGENT_ROUTING map if agent available
            3. Fall back to first available agent (prefer Ollama)
            4. Default to OLLAMA as last resort
        """
        # Manual override takes precedence (if available)
        if manual_override:
            if not self.available_agents or manual_override in self.available_agents:
                logger.info(
                    "Manual agent override: %s (ignoring intent: %s)",
                    manual_override.value, intent.value
                )
                return manual_override
            else:
                logger.warning(
                    "Manual override %s not available, falling back",
                    manual_override.value
                )

        # Use routing map
        preferred_agent = self.routing.get(intent, AgentType.CLAUDE_SONNET)

        # Check if preferred agent is available
        if self.available_agents and preferred_agent not in self.available_agents:
            # Fall back to Ollama if available, otherwise first available
            if AgentType.OLLAMA in self.available_agents:
                agent = AgentType.OLLAMA
                logger.info(
                    "Preferred agent %s not available, using Ollama for intent: %s",
                    preferred_agent.value, intent.value
                )
            elif self.available_agents:
                agent = self.available_agents[0]
                logger.info(
                    "Preferred agent %s not available, using %s for intent: %s",
                    preferred_agent.value, agent.value, intent.value
                )
            else:
                agent = AgentType.OLLAMA
                logger.warning("No agents available, defaulting to Ollama")
        else:
            agent = preferred_agent

        logger.info(
            "Agent selected: %s for intent: %s",
            agent.value, intent.value
        )

        return agent

    def get_agent_capabilities(self, agent: AgentType) -> dict:
        """Get capabilities and cost info for an agent.

        Args:
            agent: Agent type

        Returns:
            dict: Agent capabilities and metadata
        """
        capabilities = {
            AgentType.CLAUDE_CODE: {
                "capabilities": ["terminal", "code_generation", "file_ops"],
                "cost_per_1k_tokens": 0.015,
                "average_latency_ms": 3500,
                "quality": "high",
                "note": "Week 4 implementation - currently stubbed"
            },
            AgentType.CLAUDE_SONNET: {
                "capabilities": ["analysis", "synthesis", "memory_query"],
                "cost_per_1k_tokens": 0.015,
                "average_latency_ms": 3000,
                "quality": "highest",
                "note": "Best for analysis and synthesis"
            },
            AgentType.CHATGPT: {
                "capabilities": ["creative", "general", "conversation"],
                "cost_per_1k_tokens": 0.003,  # 5x cheaper!
                "average_latency_ms": 1800,
                "quality": "medium-high",
                "note": "Cost-optimized for creative tasks"
            },
            AgentType.GEMINI: {
                "capabilities": ["research", "web_search", "general"],
                "cost_per_1k_tokens": 0.010,
                "average_latency_ms": 4000,
                "quality": "high",
                "note": "Has web search for research tasks"
            }
        }

        return capabilities.get(agent, {})

    def explain_routing(self, intent: IntentType) -> str:
        """Explain why a particular agent was selected for an intent.

        Args:
            intent: Intent type

        Returns:
            str: Human-readable explanation
        """
        agent = self.routing.get(intent, AgentType.CLAUDE_SONNET)
        capabilities = self.get_agent_capabilities(agent)

        explanation = f"Intent '{intent.value}' → Agent '{agent.value}'\n"
        explanation += f"Reason: {capabilities.get('note', 'Best match for this intent')}\n"
        explanation += f"Cost: ${capabilities.get('cost_per_1k_tokens', 0)}/1K tokens\n"
        explanation += f"Quality: {capabilities.get('quality', 'unknown')}\n"

        return explanation


# Global selector instance
_selector_instance = None


def get_agent_selector() -> AgentSelector:
    """Get global agent selector instance.

    Returns:
        AgentSelector: Global selector instance
    """
    global _selector_instance
    if _selector_instance is None:
        _selector_instance = AgentSelector()
    return _selector_instance
