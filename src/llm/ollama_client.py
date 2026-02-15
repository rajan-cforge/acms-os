"""
Ollama LLM Client - Local AI inference.

Production-grade Ollama client with:
- Async HTTP client (aiohttp)
- Streaming support
- Circuit breaker pattern
- Retry with exponential backoff
- Connection pooling

Cost: $0 (local inference - no API costs)
Performance: Depends on local hardware (GPU recommended)
"""

import asyncio
import json
import os
import time
import logging
from typing import AsyncIterator, Optional, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

import aiohttp

from src.utils.logging import get_correlation_id

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation - requests allowed
    OPEN = "open"          # Failing - reject all requests
    HALF_OPEN = "half_open"  # Testing - allow one request to test recovery


@dataclass
class CircuitBreaker:
    """Circuit breaker for Ollama availability.

    Prevents cascade failures when Ollama is unavailable.
    Opens after `failure_threshold` consecutive failures.
    Allows test request after `recovery_timeout` seconds.
    """
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: float = 0.0

    def record_failure(self):
        """Record a failure and potentially open the circuit."""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker OPEN after {self.failure_count} failures"
            )

    def record_success(self):
        """Record a success and close the circuit."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def should_allow_request(self) -> bool:
        """Check if request should be allowed."""
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if recovery timeout has elapsed
            if time.time() - self.last_failure_time >= self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                logger.info("Circuit breaker transitioning to HALF_OPEN")
                return True
            return False

        # HALF_OPEN - allow one test request
        return True


class OllamaClient:
    """Production-grade Ollama client for local LLM inference.

    Features:
    - Async HTTP client with connection pooling
    - Streaming and non-streaming completions
    - Circuit breaker for fault tolerance
    - Retry with exponential backoff
    - Zero cost (local inference)

    Example:
        client = OllamaClient()
        response = await client.complete("What is Python?")

        # Streaming
        async for chunk in client.stream_complete("Tell me a story"):
            print(chunk, end="", flush=True)
    """

    # Pricing: $0 (local inference)
    PRICING = {'input': 0, 'output': 0}

    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: float = 120.0,  # Increased for 70B model
        max_retries: int = 3
    ):
        """Initialize Ollama client.

        Args:
            base_url: Ollama API base URL (default: from OLLAMA_BASE_URL env or localhost:11434)
            model: Model to use (default: from OLLAMA_MODEL env or llama3.2:latest)
            timeout: Request timeout in seconds (120s for large models)
            max_retries: Maximum retry attempts for transient errors
        """
        # Use environment variables with sensible defaults
        default_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        default_model = os.getenv("OLLAMA_MODEL", "llama3.2:latest")

        self.base_url = (base_url or default_url).rstrip('/')
        self.model = model or default_model
        self.timeout = timeout
        self.max_retries = max_retries
        self.circuit = CircuitBreaker()
        self._session: Optional[aiohttp.ClientSession] = None

        logger.info(
            f"OllamaClient initialized",
            extra={
                'base_url': self.base_url,
                'model': model,
                'timeout': timeout,
                'correlation_id': get_correlation_id()
            }
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session with connection pooling.

        Returns:
            aiohttp.ClientSession: Reusable HTTP session
        """
        if self._session is None or self._session.closed:
            # For streaming with large models (70B), we need:
            # - total=None: No limit on total request time (streaming can be long)
            # - sock_read=300: 5 min between chunks (model may think for a while)
            # - sock_connect=30: 30s to establish connection
            timeout = aiohttp.ClientTimeout(
                total=None,  # No total timeout for streaming
                sock_read=300,  # 5 min between data chunks
                sock_connect=30  # 30s to connect
            )
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def is_available(self) -> bool:
        """Health check - verify Ollama is running.

        Returns:
            bool: True if Ollama is reachable and responding
        """
        try:
            session = await self._get_session()
            async with session.get(f"{self.base_url}/api/tags") as resp:
                return resp.status == 200
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            return False

    def _check_circuit(self):
        """Check circuit breaker and raise if open.

        Raises:
            Exception: If circuit breaker is open
        """
        if not self.circuit.should_allow_request():
            raise Exception(
                f"Circuit breaker is open. "
                f"Retry after {self.circuit.recovery_timeout}s"
            )

    async def complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs
    ) -> str:
        """Generate non-streaming completion.

        Args:
            prompt: Input prompt
            model: Model override (default: instance model)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            system: System prompt (optional)
            **kwargs: Additional Ollama parameters

        Returns:
            str: Generated text

        Raises:
            ValueError: If prompt is empty
            Exception: If circuit breaker is open
            aiohttp.ClientError: On connection errors
        """
        # Validation
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        # Check circuit breaker
        self._check_circuit()

        correlation_id = get_correlation_id()
        use_model = model or self.model

        logger.info(
            "Ollama completion request",
            extra={
                'model': use_model,
                'prompt_length': len(prompt),
                'correlation_id': correlation_id
            }
        )

        # Build request payload
        payload = {
            "model": use_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }

        if system:
            payload["system"] = system

        # Add any additional kwargs to options
        payload["options"].update(kwargs.get("options", {}))

        # Execute with retry
        last_error = None
        for attempt in range(self.max_retries):
            try:
                session = await self._get_session()
                async with session.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.circuit.record_success()

                        response_text = data.get("response", "")

                        logger.info(
                            "Ollama completion success",
                            extra={
                                'model': use_model,
                                'response_length': len(response_text),
                                'correlation_id': correlation_id
                            }
                        )

                        return response_text

                    elif resp.status >= 500:
                        # Server error - retry
                        last_error = aiohttp.ClientResponseError(
                            request_info=resp.request_info,
                            history=resp.history,
                            status=resp.status,
                            message=f"Server error: {resp.status}"
                        )
                        logger.warning(
                            f"Ollama server error (attempt {attempt + 1}): {resp.status}"
                        )
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue

                    else:
                        # Client error - don't retry
                        resp.raise_for_status()

            except asyncio.TimeoutError:
                last_error = asyncio.TimeoutError()
                logger.warning(f"Ollama timeout (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                continue

            except aiohttp.ClientConnectorError as e:
                self.circuit.record_failure()
                logger.error(f"Ollama connection error: {e}")
                raise

            except aiohttp.ClientResponseError as e:
                if e.status >= 400 and e.status < 500:
                    # Client error - don't retry
                    raise
                last_error = e
                continue

        # All retries exhausted
        self.circuit.record_failure()
        if last_error:
            raise last_error
        raise Exception("All retry attempts failed")

    async def stream_complete(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """Generate streaming completion.

        Args:
            prompt: Input prompt
            model: Model override (default: instance model)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (0.0-1.0)
            system: System prompt (optional)
            **kwargs: Additional Ollama parameters

        Yields:
            str: Response chunks as they're generated

        Raises:
            ValueError: If prompt is empty
            Exception: If circuit breaker is open
            aiohttp.ClientError: On connection errors
        """
        # Validation
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        # Check circuit breaker
        self._check_circuit()

        correlation_id = get_correlation_id()
        use_model = model or self.model

        logger.info(
            "Ollama streaming request",
            extra={
                'model': use_model,
                'prompt_length': len(prompt),
                'correlation_id': correlation_id
            }
        )

        # Build request payload
        payload = {
            "model": use_model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature
            }
        }

        if system:
            payload["system"] = system

        payload["options"].update(kwargs.get("options", {}))

        try:
            session = await self._get_session()
            async with session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as resp:
                if resp.status != 200:
                    resp.raise_for_status()

                # Stream NDJSON responses
                async for line in resp.content:
                    if line:
                        try:
                            data = json.loads(line.decode('utf-8'))
                            chunk = data.get("response", "")
                            if chunk:
                                yield chunk

                            # Check if done
                            if data.get("done", False):
                                self.circuit.record_success()
                                logger.info(
                                    "Ollama streaming complete",
                                    extra={'correlation_id': correlation_id}
                                )
                                break

                        except json.JSONDecodeError:
                            continue

        except aiohttp.ClientConnectorError as e:
            self.circuit.record_failure()
            logger.error(f"Ollama connection error during stream: {e}")
            raise

        except asyncio.TimeoutError as e:
            logger.error(f"Ollama streaming timeout: {type(e).__name__}")
            raise Exception("Ollama streaming timeout - response took too long")

        except aiohttp.ServerTimeoutError as e:
            logger.error(f"Ollama server timeout: {type(e).__name__}")
            raise Exception("Ollama server timeout - try again")

        except Exception as e:
            error_msg = str(e) if str(e) else f"{type(e).__name__} (no message)"
            logger.error(f"Ollama streaming error: {error_msg}")
            raise Exception(error_msg) if error_msg else e

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> float:
        """Calculate cost in USD for a request.

        Always returns $0.00 for local inference.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            float: Always 0.0 (local inference is free)
        """
        return 0.0

    async def close(self):
        """Clean up HTTP session.

        Should be called when done using the client.
        """
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.debug("Ollama client session closed")


# Convenience function for quick usage
async def ollama_complete(
    prompt: str,
    model: str = "llama3.2:latest",
    **kwargs
) -> str:
    """Quick one-shot completion without managing client lifecycle.

    Args:
        prompt: Input prompt
        model: Model to use
        **kwargs: Additional parameters

    Returns:
        str: Generated text
    """
    client = OllamaClient(model=model)
    try:
        return await client.complete(prompt, **kwargs)
    finally:
        await client.close()
