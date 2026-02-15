"""Base agent abstract class for AI Gateway.

All agent implementations must inherit from BaseAgent and implement:
- generate(): Streaming response generation
- estimate_cost(): Cost estimation for query
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
import logging

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all AI agents."""

    def __init__(self, agent_name: str):
        """Initialize base agent.

        Args:
            agent_name: Human-readable agent name (e.g., "Claude Sonnet 4.5")
        """
        self.agent_name = agent_name
        logger.info(f"{agent_name} agent initialized")

    @abstractmethod
    async def generate(
        self,
        query: str,
        context: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming response to query.

        Args:
            query: User question/prompt
            context: Optional context from memory system
            **kwargs: Agent-specific parameters

        Yields:
            str: Response chunks (streaming)

        Example:
            async for chunk in agent.generate("Hello", context="..."):
                print(chunk, end="", flush=True)
        """
        pass

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a query.

        Args:
            input_tokens: Estimated input token count
            output_tokens: Estimated output token count

        Returns:
            float: Estimated cost in USD

        Example:
            cost = agent.estimate_cost(100, 500)  # $0.015
        """
        pass

    def get_metadata(self) -> dict:
        """Get agent metadata (capabilities, pricing, etc).

        Returns:
            dict: Agent metadata
        """
        return {
            "agent_name": self.agent_name,
            "supports_streaming": True,
            "supports_context": True
        }
