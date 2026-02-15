"""Claude Opus 4.5 agent wrapper.

Reuses existing ClaudeGenerator from src/generation/claude_generator.py.
Best for: Complex analysis, software engineering, agentic workflows.
Premium tier model with best reasoning quality.
"""

import os
from typing import AsyncIterator, Optional
import logging
from src.gateway.agents.base_agent import BaseAgent
from src.generation.claude_generator import ClaudeGenerator

logger = logging.getLogger(__name__)


class ClaudeSonnetAgent(BaseAgent):
    """Claude Opus 4.5 agent - Premium tier for complex tasks."""

    def __init__(self):
        """Initialize Claude Opus agent."""
        super().__init__("Claude Opus 4.5")

        # Reuse existing ClaudeGenerator (now uses Opus 4.5)
        self.generator = ClaudeGenerator()

        # Pricing for Opus 4.5 (Nov 2025)
        self.cost_per_1m_input_tokens = 5.0  # $5/1M input tokens
        self.cost_per_1m_output_tokens = 25.0  # $25/1M output tokens

    async def generate(
        self,
        query: str,
        context: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming response using Claude Sonnet.

        Args:
            query: User question/prompt
            context: Optional context from memory system
            **kwargs: Additional parameters (max_tokens, temperature, etc)

        Yields:
            str: Response chunks (streaming)
        """
        # Stream response using ClaudeGenerator (it handles context formatting)
        full_response = ""
        try:
            async for chunk in self.generator.generate_stream(
                prompt=query,
                context=context,  # Pass context directly to generator
                max_tokens=kwargs.get("max_tokens", 4096),
                temperature=kwargs.get("temperature", 0.7)
            ):
                full_response += chunk
                yield chunk

            logger.info(
                f"Claude Sonnet generated {len(full_response)} chars "
                f"(query: ~{len(query)} chars, context: ~{len(context) if context else 0} chars)"
            )

        except Exception as e:
            logger.error(f"Claude Sonnet generation error: {e}")
            yield f"\n\n[Error: {str(e)}]"

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for Claude Sonnet query.

        Args:
            input_tokens: Estimated input token count
            output_tokens: Estimated output token count

        Returns:
            float: Estimated cost in USD

        Example:
            cost = agent.estimate_cost(1000, 500)
            # (1000/1M * $3) + (500/1M * $15) = $0.003 + $0.0075 = $0.0105
        """
        input_cost = (input_tokens / 1_000_000) * self.cost_per_1m_input_tokens
        output_cost = (output_tokens / 1_000_000) * self.cost_per_1m_output_tokens
        total_cost = input_cost + output_cost

        logger.debug(
            f"Cost estimate: {input_tokens} in + {output_tokens} out = ${total_cost:.6f}"
        )

        return round(total_cost, 6)

    def get_metadata(self) -> dict:
        """Get Claude Opus metadata.

        Returns:
            dict: Agent capabilities and pricing
        """
        return {
            "agent_name": self.agent_name,
            "model": "claude-opus-4-5-20251101",
            "supports_streaming": True,
            "supports_context": True,
            "max_tokens": 64000,
            "best_for": ["complex_analysis", "software_engineering", "agentic", "synthesis"],
            "cost_per_1m_input": self.cost_per_1m_input_tokens,
            "cost_per_1m_output": self.cost_per_1m_output_tokens,
            "average_latency_ms": 4000,
            "tier": "premium"
        }
