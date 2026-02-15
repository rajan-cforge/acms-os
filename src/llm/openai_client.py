"""
OpenAI LLM Client

Production-grade OpenAI client with:
- Cost calculation
- Streaming support
- Embeddings
- Correlation ID logging
- Comprehensive error handling

Implementation Status: COMPLETE
Week 5 Day 1: Task 2 (3.5 hours)
"""

import logging
from typing import AsyncIterator, Dict, Any
from openai import AsyncOpenAI, RateLimitError, APIError

from src.utils.logging import get_correlation_id

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    Production-grade OpenAI client.

    Features:
    - Chat completions (non-streaming and streaming)
    - Embeddings
    - Accurate cost calculation
    - Correlation ID logging
    - Comprehensive error handling
    """

    # Pricing as of December 2025 (per 1M tokens)
    # Source: https://openai.com/api/pricing/
    PRICING = {
        'gpt-5.1': {'input': 1.25, 'output': 10.00},
        'gpt-4o-mini': {'input': 0.15, 'output': 0.60},
        'text-embedding-3-small': {'input': 0.02, 'output': 0},
        'text-embedding-3-large': {'input': 0.13, 'output': 0},
    }

    def __init__(self, api_key: str):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key (must start with 'sk-')

        Raises:
            ValueError: If API key is invalid
        """
        # Validate API key format
        if not api_key or not api_key.startswith('sk-'):
            raise ValueError("Invalid OpenAI API key: must start with 'sk-'")

        self.api_key = api_key
        self.client = AsyncOpenAI(api_key=api_key)

        logger.info(
            "OpenAI client initialized",
            extra={
                'api_key_prefix': api_key[:10] + '...',
                'correlation_id': get_correlation_id()
            }
        )

    def _get_token_param(self, model: str, max_tokens: int) -> Dict[str, int]:
        """
        Get the correct token parameter based on model.

        Newer OpenAI models (gpt-5.x, o1, o3) use 'max_completion_tokens'
        instead of 'max_tokens'.

        Args:
            model: Model name
            max_tokens: Maximum tokens value

        Returns:
            Dict with the correct parameter name and value
        """
        # Models that require max_completion_tokens
        new_style_models = ('gpt-5', 'o1', 'o3')

        if any(model.startswith(prefix) for prefix in new_style_models):
            return {'max_completion_tokens': max_tokens}
        else:
            return {'max_tokens': max_tokens}

    async def complete(
        self,
        prompt: str,
        model: str = 'gpt-5.1',
        max_tokens: int = 1000,
        temperature: float = 0.7,
        timeout: int = 60,
        **kwargs
    ) -> str:
        """
        Generate chat completion (non-streaming).

        Args:
            prompt: Input prompt
            model: Model to use (gpt-5.1, gpt-4o-mini)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            timeout: Request timeout in seconds
            **kwargs: Additional OpenAI parameters

        Returns:
            str: Generated text

        Raises:
            ValueError: If prompt is empty or max_tokens is invalid
            RateLimitError: If rate limit is exceeded
            APIError: If OpenAI API returns an error
        """
        # Validation
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

        correlation_id = get_correlation_id()

        logger.info(
            "OpenAI completion request",
            extra={
                'model': model,
                'max_tokens': max_tokens,
                'prompt_length': len(prompt),
                'correlation_id': correlation_id
            }
        )

        try:
            # Newer models (gpt-5.x, o1) use max_completion_tokens instead of max_tokens
            token_param = self._get_token_param(model, max_tokens)

            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                timeout=timeout,
                **token_param,
                **kwargs
            )

            content = response.choices[0].message.content

            # Calculate cost
            usage = response.usage
            cost = self.calculate_cost(
                model=model,
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens
            )

            logger.info(
                "OpenAI completion success",
                extra={
                    'model': model,
                    'input_tokens': usage.prompt_tokens,
                    'output_tokens': usage.completion_tokens,
                    'cost': round(cost, 6),
                    'correlation_id': correlation_id
                }
            )

            return content

        except RateLimitError as e:
            logger.error(
                f"OpenAI rate limit exceeded: {e}",
                extra={'correlation_id': correlation_id}
            )
            raise

        except APIError as e:
            logger.error(
                f"OpenAI API error: {e}",
                extra={'correlation_id': correlation_id}
            )
            raise

        except Exception as e:
            logger.error(
                f"Unexpected error: {e}",
                extra={'correlation_id': correlation_id},
                exc_info=True
            )
            raise

    async def stream_complete(
        self,
        prompt: str,
        model: str = 'gpt-5.1',
        max_tokens: int = 1000,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate streaming chat completion.

        Args:
            prompt: Input prompt
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional OpenAI parameters

        Yields:
            str: Text chunks as they're generated

        Raises:
            ValueError: If prompt is empty or max_tokens is invalid
            RateLimitError: If rate limit is exceeded
            APIError: If OpenAI API returns an error
        """
        # Validation
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

        correlation_id = get_correlation_id()

        logger.info(
            "OpenAI streaming request",
            extra={
                'model': model,
                'prompt_length': len(prompt),
                'correlation_id': correlation_id
            }
        )

        try:
            # Newer models (gpt-5.x, o1) use max_completion_tokens instead of max_tokens
            token_param = self._get_token_param(model, max_tokens)

            # Get streaming response
            stream = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                stream=True,
                **token_param,
                **kwargs
            )

            # Iterate over stream chunks
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            logger.info(
                "OpenAI streaming completed",
                extra={'correlation_id': correlation_id}
            )

        except Exception as e:
            logger.error(
                f"Streaming error: {e}",
                extra={'correlation_id': correlation_id},
                exc_info=True
            )
            raise

    async def embed(
        self,
        text: str,
        model: str = 'text-embedding-3-small'
    ) -> list[float]:
        """
        Generate text embeddings.

        Args:
            text: Text to embed
            model: Embedding model (text-embedding-3-small or text-embedding-3-large)

        Returns:
            list[float]: Embedding vector (1536 dimensions for small, 3072 for large)

        Raises:
            ValueError: If text is empty
            APIError: If OpenAI API returns an error
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        correlation_id = get_correlation_id()

        logger.info(
            "OpenAI embedding request",
            extra={
                'model': model,
                'text_length': len(text),
                'correlation_id': correlation_id
            }
        )

        try:
            response = await self.client.embeddings.create(
                model=model,
                input=text
            )

            embedding = response.data[0].embedding

            logger.info(
                "OpenAI embedding success",
                extra={
                    'model': model,
                    'embedding_dim': len(embedding),
                    'correlation_id': correlation_id
                }
            )

            return embedding

        except Exception as e:
            logger.error(
                f"Embedding error: {e}",
                extra={'correlation_id': correlation_id},
                exc_info=True
            )
            raise

    def calculate_cost(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """
        Calculate cost in USD for a request.

        Args:
            model: Model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            float: Cost in USD (e.g., 0.025 = $0.025 = 2.5 cents)
        """
        if model not in self.PRICING:
            logger.warning(
                f"Unknown model for pricing: {model}, returning $0",
                extra={'correlation_id': get_correlation_id()}
            )
            return 0.0

        pricing = self.PRICING[model]

        # Cost = (tokens / 1M) * price_per_1M
        input_cost = (input_tokens / 1_000_000) * pricing['input']
        output_cost = (output_tokens / 1_000_000) * pricing['output']

        total_cost = input_cost + output_cost

        return round(total_cost, 8)  # Round to 8 decimal places for precision
