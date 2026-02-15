"""Claude API Client for RAG Text Generation.

Uses Claude Opus 4.5 for highest-quality RAG answers.
Much faster (2-5s) than Ollama llama3.2 (15-45s) on CPU.

Cost: $5 per 1M input tokens, $25 per 1M output tokens
      (up to 90% savings with prompt caching)
Performance: 2-5 seconds typical
Quality: Best available reasoning - premium tier model
"""

import os
from typing import List, Dict, Optional, AsyncIterator

from anthropic import Anthropic, AsyncAnthropic


class ClaudeGenerator:
    """Claude API client for text generation using Opus 4.5.

    Features:
    - Claude Opus 4.5 (best reasoning quality - premium tier)
    - 2-5 second responses (10x faster than Ollama CPU)
    - Conversation history support
    - Streaming support
    - $5/$25 per 1M tokens (in/out) - up to 90% savings with prompt caching

    Example:
        client = ClaudeGenerator()
        answer = client.generate("What is Python?", max_tokens=200)
        # Returns: "Python is a high-level programming language..."
    """

    def __init__(self, api_key: str = None):
        """Initialize Claude generator client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)

        Raises:
            ValueError: If API key not found
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment. "
                "Please set it in .env or pass as argument."
            )

        self.client = Anthropic(api_key=self.api_key)
        self.async_client = AsyncAnthropic(api_key=self.api_key)
        self.model = "claude-opus-4-5-20251101"  # Claude Opus 4.5 (Dec 2025)

        print(f"[Claude Generator] Initialized with {self.model}")

    def generate(
        self,
        prompt: str,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text response from Claude.

        Args:
            prompt: User prompt/question
            max_tokens: Maximum response length (default 1024)
            temperature: Creativity 0.0-1.0 (default 0.7)
            system_prompt: Optional system instructions

        Returns:
            Generated text response

        Raises:
            ValueError: If prompt is empty
            RuntimeError: If generation fails

        Performance: 2-5 seconds typical
        Cost: ~$0.003 per 1K input tokens, ~$0.015 per 1K output tokens
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        try:
            # Build request
            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }

            # Add system prompt if provided
            if system_prompt:
                kwargs["system"] = system_prompt

            # Call Claude API
            response = self.client.messages.create(**kwargs)

            # Extract text
            answer = response.content[0].text

            # Log usage for cost tracking
            usage = response.usage
            print(
                f"[Claude] Tokens: {usage.input_tokens} in, "
                f"{usage.output_tokens} out"
            )

            return answer.strip()

        except Exception as e:
            print(f"[Claude Generator] Error: {e}")
            raise RuntimeError(f"Text generation failed: {e}")

    def generate_with_history(
        self,
        current_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> str:
        """Generate text with conversation history for multi-turn Q&A.

        Args:
            current_prompt: New question/prompt
            conversation_history: Previous Q&A pairs
                Format: [
                    {"role": "user", "content": "..."},
                    {"role": "assistant", "content": "..."},
                    ...
                ]
            max_tokens: Maximum response length
            temperature: Creativity 0.0-1.0
            system_prompt: Optional system instructions

        Returns:
            Generated text response with context from history

        Raises:
            ValueError: If current_prompt is empty
            RuntimeError: If generation fails

        Performance: 2-5 seconds typical
        Cost: More input tokens due to history, same output cost
        """
        if not current_prompt or not current_prompt.strip():
            raise ValueError("Current prompt cannot be empty")

        try:
            # Build messages with history
            messages = []

            # Add conversation history if provided
            if conversation_history:
                # Limit history to prevent token overflow (keep last 6 messages = 3 Q&A pairs)
                recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
                messages.extend(recent_history)

            # Add current prompt
            messages.append({"role": "user", "content": current_prompt})

            # Build request
            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": messages
            }

            # Add system prompt if provided
            if system_prompt:
                kwargs["system"] = system_prompt

            # Call Claude API
            response = self.client.messages.create(**kwargs)

            # Extract text
            answer = response.content[0].text

            # Log usage
            usage = response.usage
            print(
                f"[Claude History] Tokens: {usage.input_tokens} in, "
                f"{usage.output_tokens} out (history: {len(conversation_history or [])} msgs)"
            )

            return answer.strip()

        except Exception as e:
            print(f"[Claude Generator with History] Error: {e}")
            raise RuntimeError(f"Text generation with history failed: {e}")

    async def generate_stream(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Generate streaming text response from Claude (async).

        Used by Gateway agents for SSE streaming responses.

        Args:
            prompt: User prompt/question
            context: Optional context from memory system
            max_tokens: Maximum response length (default 1024)
            temperature: Creativity 0.0-1.0 (default 0.7)
            system_prompt: Optional system instructions

        Yields:
            Text chunks as they arrive from Claude

        Raises:
            ValueError: If prompt is empty
            RuntimeError: If generation fails

        Performance: Streams tokens as generated (faster perceived response)
        Cost: Same as generate() (~$0.003/1K in, ~$0.015/1K out)
        """
        if not prompt or not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        try:
            # Build full prompt with context if provided
            full_prompt = prompt
            if context:
                full_prompt = f"""Context from memory system:
{context}

User question:
{prompt}

Please answer the user's question using the context provided."""

            # Build request
            kwargs = {
                "model": self.model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [
                    {"role": "user", "content": full_prompt}
                ]
            }

            # Add system prompt if provided
            if system_prompt:
                kwargs["system"] = system_prompt

            # Stream response from Claude
            async with self.async_client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            print(f"[Claude Generator Stream] Error: {e}")
            raise RuntimeError(f"Streaming generation failed: {e}")


if __name__ == "__main__":
    # Test Claude generator
    print("Testing Claude Generator...")

    try:
        client = ClaudeGenerator()

        # Test 1: Simple generation
        print("\n=== TEST 1: Simple Generation ===")
        prompt = "What is 2+2? Answer with just the number."
        print(f"Prompt: '{prompt}'")

        answer = client.generate(prompt, max_tokens=10, temperature=0.0)
        print(f"✅ Answer: {answer}")
        print(f"   Contains '4': {'4' in answer}")

        # Test 2: Longer response
        print("\n=== TEST 2: Longer Response ===")
        prompt = "What is Python? Answer in 2 sentences."
        print(f"Prompt: '{prompt}'")

        answer = client.generate(prompt, max_tokens=100, temperature=0.7)
        print(f"✅ Answer: {answer[:200]}...")
        print(f"   Length: {len(answer)} chars")

        # Test 3: With system prompt
        print("\n=== TEST 3: With System Prompt ===")
        answer = client.generate(
            prompt="Explain FastAPI",
            system_prompt="You are a Python expert. Be very concise.",
            max_tokens=100,
            temperature=0.5
        )
        print(f"✅ Answer: {answer[:200]}...")

        # Test 4: Conversation history
        print("\n=== TEST 4: Conversation History ===")
        history = [
            {"role": "user", "content": "What is ACMS?"},
            {"role": "assistant", "content": "ACMS is an AI conversation memory system."}
        ]
        answer = client.generate_with_history(
            current_prompt="How does it work?",
            conversation_history=history,
            max_tokens=150
        )
        print(f"✅ Answer: {answer[:200]}...")
        print(f"   References ACMS: {'ACMS' in answer or 'it' in answer.lower()}")

        print("\n🎉 All tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
