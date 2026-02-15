"""Ollama Gateway Agent - Local LLM integration.

Gateway agent for local Ollama-hosted models.
Provides streaming responses with context injection.

Features:
- Streaming responses via AsyncIterator
- Context-aware prompting
- Zero cost ($0/query)
- Privacy-sensitive (data stays local)

Use for:
- Privacy-sensitive queries
- Offline scenarios
- High-volume workloads
- Cost-sensitive applications
"""

from typing import AsyncIterator, Optional
import logging
import os

from src.gateway.agents.base_agent import BaseAgent
from src.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class OllamaAgent(BaseAgent):
    """Ollama agent for local LLM inference.

    Inherits from BaseAgent and implements streaming generation
    with Ollama-hosted models.

    Example:
        agent = OllamaAgent()
        async for chunk in agent.generate("What is Python?"):
            print(chunk, end="", flush=True)
    """

    def __init__(
        self,
        model: str = None,
        base_url: str = None
    ):
        """Initialize Ollama agent.

        Args:
            model: Model to use (default: from env or llama3.2:latest)
            base_url: Ollama API URL (default: from env or Docker network)
        """
        super().__init__(agent_name="Ollama Local")

        # Use environment variables with sensible defaults
        # Default model: llama3.2:latest (lightweight, 2GB)
        self.model = model or os.getenv("OLLAMA_MODEL", "llama3.2:latest")
        self.model_name = self.model  # For logging compatibility

        # Default to Docker container Ollama
        default_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        url = base_url or default_url

        self.client = OllamaClient(
            base_url=url,
            model=self.model
        )

        logger.info(
            f"OllamaAgent initialized with model: {self.model}, url: {url}"
        )

    async def generate(
        self,
        query: str,
        context: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming response from Ollama.

        Args:
            query: User question/prompt
            context: Optional context from memory system
            **kwargs: Additional parameters (temperature, etc.)

        Yields:
            str: Response chunks (streaming)

        Example:
            async for chunk in agent.generate("Hello", context="..."):
                print(chunk, end="", flush=True)
        """
        # Build prompt with context if provided
        if context:
            prompt = f"""Context information:
{context}

Based on the context above, please answer the following question:
{query}

Provide a helpful, accurate response based on the context provided."""
        else:
            prompt = query

        logger.info(
            f"OllamaAgent generating response for query: {query[:50]}..."
        )

        try:
            async for chunk in self.client.stream_complete(
                prompt=prompt,
                model=self.model,
                temperature=kwargs.get("temperature", 0.7),
                max_tokens=kwargs.get("max_tokens", 2000)
            ):
                yield chunk

        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            # Yield error message to user
            yield f"\n\n[Error: Ollama unavailable - {str(e)}. Please check if Ollama is running.]"

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for a query.

        Local inference = $0.00 always.

        Args:
            input_tokens: Estimated input token count
            output_tokens: Estimated output token count

        Returns:
            float: Always 0.0 (free local inference)
        """
        return 0.0

    def get_metadata(self) -> dict:
        """Get agent metadata (capabilities, pricing, etc).

        Returns:
            dict: Agent metadata for UI and selection
        """
        return {
            "agent_name": self.agent_name,
            "model": self.model,
            "supports_streaming": True,
            "supports_context": True,
            "cost_per_million": 0,  # Free!
            "best_for": [
                "privacy-sensitive",
                "offline",
                "high-volume",
                "cost-conscious"
            ],
            "limitations": [
                "slower than cloud APIs",
                "depends on local hardware",
                "may have lower quality than GPT-4/Claude"
            ],
            "privacy": "local-only"
        }

    async def is_available(self) -> bool:
        """Check if Ollama is available.

        Returns:
            bool: True if Ollama is reachable
        """
        return await self.client.is_available()
