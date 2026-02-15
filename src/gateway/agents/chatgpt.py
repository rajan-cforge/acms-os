"""ChatGPT (GPT-5.1) agent wrapper.

Best for: Creative writing, adaptive reasoning, coding tasks.
GPT-5.1 features adaptive reasoning - fast on simple queries, deep on complex ones.
"""

import os
from typing import AsyncIterator, Optional
import logging
from openai import AsyncOpenAI
from src.gateway.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ChatGPTAgent(BaseAgent):
    """ChatGPT (GPT-5.1) agent - Adaptive reasoning for creative and coding tasks."""

    def __init__(self):
        """Initialize ChatGPT agent."""
        super().__init__("ChatGPT (GPT-5.1)")

        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.client = AsyncOpenAI(api_key=api_key)
        # GPT-5.1 (Nov 2025) - adaptive reasoning model
        # Variants: gpt-5.1, gpt-5.1-instant, gpt-5.1-thinking, gpt-5.1-codex
        self.model = os.getenv("OPENAI_MODEL", "gpt-5.1")  # Default to gpt-5.1

        # Pricing for GPT-5.1 (Nov 2025) - estimated similar to GPT-4o
        self.cost_per_1m_input_tokens = 2.5  # $2.50/1M input tokens
        self.cost_per_1m_output_tokens = 10.0  # $10/1M output tokens

    async def generate(
        self,
        query: str,
        context: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming response using ChatGPT.

        Args:
            query: User question/prompt
            context: Optional context from memory system
            **kwargs: Additional parameters (max_tokens, temperature, etc)

        Yields:
            str: Response chunks (streaming)
        """
        # Build messages with context if provided
        messages = []

        if context:
            messages.append({
                "role": "system",
                "content": f"Context from memory system:\n{context}"
            })

        messages.append({
            "role": "user",
            "content": query
        })

        # Stream response using OpenAI API
        full_response = ""
        try:
            # GPT-5.x and o1/o3 models require max_completion_tokens instead of max_tokens
            max_tokens_value = kwargs.get("max_tokens", 2048)
            token_param = (
                {"max_completion_tokens": max_tokens_value}
                if self.model.startswith(("gpt-5", "o1", "o3"))
                else {"max_tokens": max_tokens_value}
            )

            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=kwargs.get("temperature", 0.7),
                stream=True,
                **token_param
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content

            logger.info(
                f"ChatGPT generated {len(full_response)} chars "
                f"(model: {self.model})"
            )

        except Exception as e:
            logger.error(f"ChatGPT generation error: {e}")
            yield f"\n\n[Error: {str(e)}]"

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for ChatGPT query.

        Args:
            input_tokens: Estimated input token count
            output_tokens: Estimated output token count

        Returns:
            float: Estimated cost in USD

        Example:
            cost = agent.estimate_cost(1000, 500)
            # (1000/1M * $10) + (500/1M * $30) = $0.01 + $0.015 = $0.025
        """
        input_cost = (input_tokens / 1_000_000) * self.cost_per_1m_input_tokens
        output_cost = (output_tokens / 1_000_000) * self.cost_per_1m_output_tokens
        total_cost = input_cost + output_cost

        logger.debug(
            f"ChatGPT cost estimate: {input_tokens} in + {output_tokens} out = ${total_cost:.6f}"
        )

        return round(total_cost, 6)

    def get_metadata(self) -> dict:
        """Get ChatGPT metadata.

        Returns:
            dict: Agent capabilities and pricing
        """
        return {
            "agent_name": self.agent_name,
            "model": self.model,
            "supports_streaming": True,
            "supports_context": True,
            "max_tokens": 8192,
            "best_for": ["creative", "conversation", "coding", "adaptive_reasoning"],
            "cost_per_1m_input": self.cost_per_1m_input_tokens,
            "cost_per_1m_output": self.cost_per_1m_output_tokens,
            "average_latency_ms": 1500,
            "note": "GPT-5.1 with adaptive reasoning - fast on simple, deep on complex"
        }
