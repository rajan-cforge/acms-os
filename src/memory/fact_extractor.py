"""Fact Extractor - LLM-based extraction of facts from raw content.

This module prevents Q&A pollution by extracting only meaningful facts
from raw conversation content before storage.

Usage:
    extractor = FactExtractor()
    facts = await extractor.extract("Q: What is Python? A: Python is a programming language...")
    # Returns: ["Python is a programming language"]
"""

import os
import json
import logging
from typing import List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)

# Extraction prompt - tells LLM what to extract
EXTRACTION_PROMPT = """You are a knowledge extraction system. Your job is to extract useful, standalone facts from content.

Rules:
1. Extract ONLY factual information worth remembering long-term
2. Convert questions into declarative statements
3. Remove conversational fluff (greetings, thanks, filler)
4. Each fact should be self-contained (understandable without context)
5. Return 0-3 facts per input (0 if nothing useful)
6. Do NOT include the question itself, only the answer/fact
7. Do NOT include meta-information like "the user asked about..."

Input Content:
{content}

Output format (JSON array of strings):
["fact 1", "fact 2"]

If no useful facts, return: []
"""


class FactExtractor:
    """Extract facts from raw content using LLM.

    This prevents Q&A pollution by only storing extracted facts,
    not raw question-answer pairs.
    """

    def __init__(self, model: str = "gpt-4o-mini"):
        """Initialize extractor.

        Args:
            model: OpenAI model to use (gpt-4o-mini is cheap and fast)
        """
        self._client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self._model = model
        logger.info(f"[FactExtractor] Initialized with model: {model}")

    async def extract(self, content: str) -> List[str]:
        """Extract facts from raw content.

        Args:
            content: Raw content (may be Q&A, conversation, etc.)

        Returns:
            List of extracted facts (may be empty)
        """
        if not content or len(content) < 20:
            return []

        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {
                        "role": "system",
                        "content": "You extract knowledge facts. Output JSON array only."
                    },
                    {
                        "role": "user",
                        "content": EXTRACTION_PROMPT.format(content=content[:2000])  # Limit input
                    }
                ],
                temperature=0.1,  # Low temperature for consistency
                max_tokens=500
            )

            # Parse response
            result = response.choices[0].message.content.strip()

            # Handle markdown code blocks
            if result.startswith("```"):
                result = result.split("```")[1]
                if result.startswith("json"):
                    result = result[4:]

            facts = json.loads(result)

            if not isinstance(facts, list):
                return []

            # Filter out short facts
            facts = [f for f in facts if isinstance(f, str) and len(f) > 20]

            logger.info(f"[FactExtractor] Extracted {len(facts)} facts from {len(content)} chars")
            return facts

        except json.JSONDecodeError as e:
            logger.warning(f"[FactExtractor] JSON parse error: {e}")
            return []
        except Exception as e:
            logger.error(f"[FactExtractor] Extraction error: {e}")
            return []

    def is_qa_format(self, content: str) -> bool:
        """Check if content looks like Q&A format.

        Args:
            content: Content to check

        Returns:
            True if content appears to be Q&A format
        """
        content_lower = content.lower()
        qa_patterns = [
            ("q:", "a:"),
            ("question:", "answer:"),
            ("user:", "assistant:"),
            ("human:", "ai:"),
            ("query:", "response:")
        ]

        for q_pattern, a_pattern in qa_patterns:
            if q_pattern in content_lower and a_pattern in content_lower:
                return True

        return False

    async def should_extract(self, content: str) -> bool:
        """Determine if content needs extraction.

        Args:
            content: Content to check

        Returns:
            True if content should go through extraction
        """
        # Q&A format always needs extraction
        if self.is_qa_format(content):
            return True

        # Very short content doesn't need extraction
        if len(content) < 50:
            return False

        # Long content might benefit from extraction
        if len(content) > 500:
            return True

        return False
