"""Google Gemini 3 Flash agent wrapper.

Best for: Fast responses, complex reasoning, research, multimodal (text, audio, images, video, PDFs, code).
Features: 1M token context, optimized for speed and intelligence.
"""

import os
from typing import AsyncIterator, Optional
import logging
import google.generativeai as genai
from src.gateway.agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class GeminiAgent(BaseAgent):
    """Google Gemini 3 Flash agent - Fast and intelligent."""

    def __init__(self):
        """Initialize Gemini agent."""
        super().__init__("Google Gemini 3 Flash")

        # Pricing for Gemini 3 Flash (Dec 2025)
        # Preview pricing - check ai.google.dev for current rates
        self.cost_per_1m_input_tokens = 0.10  # Estimated preview pricing
        self.cost_per_1m_output_tokens = 0.40  # Estimated preview pricing

        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GEMINI_API_KEY not set - Gemini agent will not be available")
            self.model = None
            return

        genai.configure(api_key=api_key)

        # Gemini 3 Flash Preview (Dec 2025) - Fast and intelligent
        # Features: 1M token context, optimized for speed
        self.model = genai.GenerativeModel('gemini-3-flash-preview')

    async def generate(
        self,
        query: str,
        context: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming response using Gemini.

        Args:
            query: User question/prompt
            context: Optional context from memory system
            **kwargs: Additional parameters

        Yields:
            str: Response chunks (streaming)
        """
        # Check if model is available
        if not self.model:
            yield "[Error: Gemini API key not configured]"
            return

        # Build prompt with context if provided
        if context:
            full_prompt = f"""Context from memory system and web search:
{context}

User question:
{query}

Please answer the user's question using the provided context. If web search results are included above, cite them with source names."""
        else:
            # No context - direct answer
            full_prompt = query

        # Stream response using Gemini
        full_response = ""
        try:
            response = await self.model.generate_content_async(
                full_prompt,
                stream=True
            )

            async for chunk in response:
                if chunk.text:
                    full_response += chunk.text
                    yield chunk.text

            logger.info(
                f"Gemini generated {len(full_response)} chars "
                f"(input: ~{len(full_prompt)} chars)"
            )

        except Exception as e:
            logger.error(f"Gemini generation error: {e}")
            yield f"\n\n[Error: {str(e)}]"

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for Gemini query.

        Args:
            input_tokens: Estimated input token count
            output_tokens: Estimated output token count

        Returns:
            float: Estimated cost in USD

        Example:
            cost = agent.estimate_cost(1000, 500)
            # (1000/1M * $0.5) + (500/1M * $1.5) = $0.0005 + $0.00075 = $0.00125
        """
        input_cost = (input_tokens / 1_000_000) * self.cost_per_1m_input_tokens
        output_cost = (output_tokens / 1_000_000) * self.cost_per_1m_output_tokens
        total_cost = input_cost + output_cost

        logger.debug(
            f"Gemini cost estimate: {input_tokens} in + {output_tokens} out = ${total_cost:.6f}"
        )

        return round(total_cost, 6)

    def get_metadata(self) -> dict:
        """Get Gemini metadata.

        Returns:
            dict: Agent capabilities and pricing
        """
        return {
            "agent_name": self.agent_name,
            "model": "gemini-3-flash-preview",
            "supports_streaming": True,
            "supports_context": True,
            "max_tokens": 1000000,  # Gemini 3 Flash has 1M token context window
            "best_for": ["research", "complex_reasoning", "multimodal", "fast_responses", "code_analysis"],
            "cost_per_1m_input": self.cost_per_1m_input_tokens,
            "cost_per_1m_output": self.cost_per_1m_output_tokens,
            "average_latency_ms": 1500,
            "note": "Gemini 3 Flash Preview - 1M context, fast and intelligent"
        }
