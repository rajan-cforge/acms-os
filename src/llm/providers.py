"""
LLM Provider Abstraction - Production Implementation

Provides a unified interface for multiple LLM providers with:
- Async I/O (non-blocking)
- Error handling with graceful fallbacks
- Cost optimization (use cheaper models for simple tasks)
- Easy swapping between providers (ChatGPT → Ollama)

Design Principles:
1. Abstract Base Class (LLMProvider) defines interface
2. Concrete implementations for each provider
3. Factory function for easy instantiation
4. Dependency injection for testing
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import asyncio

# Import OpenAI client
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Import existing Claude generator
from src.generation.claude_generator import ClaudeGenerator

# Configure logging
logger = logging.getLogger(__name__)


# ==========================================
# ABSTRACT BASE CLASS
# ==========================================

class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement:
    - generate(): Single text generation
    - generate_list(): Generate a list of items
    - is_available(): Health check
    """

    def __init__(self, model: str):
        """
        Initialize LLM provider.

        Args:
            model: Model identifier (e.g., "gpt-4o-mini", "llama2:7b")
        """
        self.model = model
        self._available = None  # Cache availability check

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.3,
        **kwargs
    ) -> str:
        """
        Generate text from prompt.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0=deterministic, 1=creative)
            **kwargs: Provider-specific parameters

        Returns:
            Generated text (string)

        Raises:
            Exception: On generation failure
        """
        pass

    @abstractmethod
    async def generate_list(
        self,
        prompt: str,
        max_items: int = 5,
        temperature: float = 0.3,
        **kwargs
    ) -> List[str]:
        """
        Generate a list of items from prompt.

        Useful for query decomposition, synonym generation, etc.

        Args:
            prompt: Input prompt (should request a list)
            max_items: Maximum number of items
            temperature: Sampling temperature
            **kwargs: Provider-specific parameters

        Returns:
            List of strings

        Raises:
            Exception: On generation failure
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if provider is available and healthy.

        Returns:
            True if provider can be used, False otherwise
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model='{self.model}')"


# ==========================================
# CHATGPT PROVIDER
# ==========================================

class ChatGPTProvider(LLMProvider):
    """
    ChatGPT provider using OpenAI API.

    Advantages:
    - Cheap (gpt-4o-mini: $0.15/1M input tokens)
    - Fast (< 1 second response time)
    - Good for simple tasks (query rewriting)

    Use for:
    - Query rewriting
    - Query decomposition
    - Synonym generation
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini"
    ):
        """
        Initialize ChatGPT provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use (default: gpt-4o-mini)
        """
        super().__init__(model)

        if not OPENAI_AVAILABLE:
            raise ImportError(
                "OpenAI package not installed. Run: pip install openai"
            )

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = AsyncOpenAI(api_key=self.api_key)
        logger.info(f"ChatGPTProvider initialized with model: {model}")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.3,
        **kwargs
    ) -> str:
        """
        Generate text using ChatGPT.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            **kwargs: Additional OpenAI parameters

        Returns:
            Generated text

        Raises:
            Exception: On API failure
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that rewrites queries for semantic search. Be concise and specific."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )

            generated_text = response.choices[0].message.content.strip()
            logger.debug(f"ChatGPT generated: {generated_text[:50]}...")
            return generated_text

        except Exception as e:
            logger.error(f"ChatGPT generation failed: {e}")
            raise

    async def generate_list(
        self,
        prompt: str,
        max_items: int = 5,
        temperature: float = 0.3,
        **kwargs
    ) -> List[str]:
        """
        Generate a list of items using ChatGPT.

        Args:
            prompt: Input prompt (should request a list)
            max_items: Maximum number of items
            temperature: Sampling temperature
            **kwargs: Additional OpenAI parameters

        Returns:
            List of strings (one per line from response)
        """
        try:
            # Add instruction to return numbered list
            enhanced_prompt = f"{prompt}\n\nReturn exactly {max_items} items, one per line, numbered 1-{max_items}."

            response_text = await self.generate(
                prompt=enhanced_prompt,
                max_tokens=max_items * 20,  # More tokens for lists
                temperature=temperature,
                **kwargs
            )

            # Parse response into list
            lines = response_text.strip().split('\n')
            items = []

            for line in lines:
                # Remove numbering (1., 2., 3., etc.)
                cleaned = line.strip()
                cleaned = cleaned.lstrip('0123456789.-) ')
                if cleaned:
                    items.append(cleaned)

            # Limit to max_items
            return items[:max_items]

        except Exception as e:
            logger.error(f"ChatGPT list generation failed: {e}")
            raise

    async def is_available(self) -> bool:
        """
        Check if ChatGPT API is available.

        Returns:
            True if API is reachable, False otherwise
        """
        if self._available is not None:
            return self._available

        try:
            # Simple test generation
            await self.generate("Test", max_tokens=5)
            self._available = True
            logger.info("ChatGPT provider is available")
            return True
        except Exception as e:
            logger.warning(f"ChatGPT provider unavailable: {e}")
            self._available = False
            return False


# ==========================================
# OLLAMA PROVIDER (STUB)
# ==========================================

class OllamaProvider(LLMProvider):
    """
    Ollama provider for local LLMs.

    Advantages:
    - Free (no API costs)
    - Private (data doesn't leave server)
    - Fast (on GPU)

    Use for:
    - Privacy-sensitive queries
    - High-volume workloads
    - Offline scenarios
    """

    def __init__(
        self,
        base_url: str = "http://localhost:40434",
        model: str = "llama3.2:latest"
    ):
        """
        Initialize Ollama provider.

        Args:
            base_url: Ollama API base URL
            model: Model to use (e.g., "llama3.2:latest", "mistral:7b")
        """
        super().__init__(model)
        self.base_url = base_url

        # Import and use OllamaClient
        from src.llm.ollama_client import OllamaClient
        self.client = OllamaClient(base_url=base_url, model=model)

        logger.info(f"OllamaProvider initialized with model: {model}")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.3,
        **kwargs
    ) -> str:
        """
        Generate text using Ollama.

        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0=deterministic, 1=creative)
            **kwargs: Provider-specific parameters

        Returns:
            Generated text (string)
        """
        try:
            result = await self.client.complete(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            return result
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    async def generate_list(
        self,
        prompt: str,
        max_items: int = 5,
        temperature: float = 0.3,
        **kwargs
    ) -> List[str]:
        """
        Generate a list of items using Ollama.

        Args:
            prompt: Input prompt (should request a list)
            max_items: Maximum number of items
            temperature: Sampling temperature
            **kwargs: Provider-specific parameters

        Returns:
            List of strings (one per line from response)
        """
        try:
            # Add instruction to return numbered list
            enhanced_prompt = f"{prompt}\n\nReturn exactly {max_items} items, one per line, numbered 1-{max_items}."

            response_text = await self.generate(
                prompt=enhanced_prompt,
                max_tokens=max_items * 30,
                temperature=temperature,
                **kwargs
            )

            # Parse response into list
            lines = response_text.strip().split('\n')
            items = []

            for line in lines:
                # Remove numbering (1., 2., 3., etc.)
                cleaned = line.strip()
                cleaned = cleaned.lstrip('0123456789.-) ')
                if cleaned:
                    items.append(cleaned)

            # Limit to max_items
            return items[:max_items]

        except Exception as e:
            logger.error(f"Ollama list generation failed: {e}")
            raise

    async def is_available(self) -> bool:
        """
        Check if Ollama is available.

        Returns:
            True if Ollama API is reachable, False otherwise
        """
        if self._available is not None:
            return self._available

        try:
            available = await self.client.is_available()
            self._available = available
            if available:
                logger.info("Ollama provider is available")
            else:
                logger.warning("Ollama provider unavailable")
            return available
        except Exception as e:
            logger.warning(f"Ollama provider unavailable: {e}")
            self._available = False
            return False


# ==========================================
# CLAUDE PROVIDER (WRAPPER)
# ==========================================

class ClaudeProvider(LLMProvider):
    """
    Claude provider wrapping existing ClaudeGenerator.

    Advantages:
    - Highest quality reasoning (Opus 4.5)
    - Best for complex queries
    - Already integrated in ACMS

    Use for:
    - Complex reasoning tasks
    - High-stakes queries
    - When quality > cost
    """

    def __init__(
        self,
        claude_generator: Optional[ClaudeGenerator] = None,
        model: str = "claude-opus-4-5"
    ):
        """
        Initialize Claude provider.

        Args:
            claude_generator: Existing ClaudeGenerator instance (for DI)
            model: Model identifier (for logging)
        """
        super().__init__(model)
        self.claude = claude_generator or ClaudeGenerator()
        logger.info(f"ClaudeProvider initialized with model: {model}")

    async def generate(
        self,
        prompt: str,
        max_tokens: int = 150,
        temperature: float = 0.3,
        **kwargs
    ) -> str:
        """
        Generate text using Claude.

        Wraps existing ClaudeGenerator.generate() method.
        """
        try:
            result = await self.claude.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            return result
        except Exception as e:
            logger.error(f"Claude generation failed: {e}")
            raise

    async def generate_list(
        self,
        prompt: str,
        max_items: int = 5,
        temperature: float = 0.3,
        **kwargs
    ) -> List[str]:
        """
        Generate list using Claude.
        """
        try:
            enhanced_prompt = f"{prompt}\n\nReturn exactly {max_items} items, one per line."
            response_text = await self.generate(
                prompt=enhanced_prompt,
                max_tokens=max_items * 30,
                temperature=temperature
            )

            lines = [line.strip() for line in response_text.split('\n') if line.strip()]
            return lines[:max_items]
        except Exception as e:
            logger.error(f"Claude list generation failed: {e}")
            raise

    async def is_available(self) -> bool:
        """
        Check if Claude is available.

        Assumes Claude is always available (already used in ACMS).
        """
        return True


# ==========================================
# FACTORY FUNCTION
# ==========================================

def create_llm_provider(
    provider_name: str = "chatgpt",
    **kwargs
) -> LLMProvider:
    """
    Factory function to create LLM provider.

    Args:
        provider_name: Provider to create ("chatgpt", "ollama", "claude")
        **kwargs: Provider-specific parameters

    Returns:
        LLMProvider instance

    Raises:
        ValueError: If provider_name is unknown

    Example:
        >>> provider = create_llm_provider("chatgpt", model="gpt-4")
        >>> result = await provider.generate("Rewrite: database info")
    """
    providers = {
        "chatgpt": ChatGPTProvider,
        "openai": ChatGPTProvider,  # Alias
        "gpt": ChatGPTProvider,     # Alias
        "ollama": OllamaProvider,
        "claude": ClaudeProvider,
    }

    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(
            f"Unknown provider: {provider_name}. "
            f"Available: {list(providers.keys())}"
        )

    logger.info(f"Creating LLM provider: {provider_name}")
    return provider_class(**kwargs)
