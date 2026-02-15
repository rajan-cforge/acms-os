"""ContextBuilder - Stage 3 of retrieval pipeline.

Token-budgeted context assembly from ranked results.

Responsibilities:
- Assemble context string from scored results
- Respect token budget (default 4000)
- Deduplicate similar content
- Format for LLM consumption

Does NOT:
- Fetch data (Retriever's job)
- Rank results (Ranker's job)
"""

import logging
from typing import List, Optional
from difflib import SequenceMatcher

from src.retrieval.ranker import ScoredResult

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Stage 3: Token-budgeted context assembly.

    Takes ranked results and builds a context string that:
    - Fits within token budget
    - Prioritizes highest-scored items
    - Removes near-duplicates
    - Formats cleanly for LLM input

    Example:
        builder = ContextBuilder(max_tokens=4000)
        context = builder.build(scored_results)
        # context is ready for LLM prompt
    """

    # Characters per token (rough estimate)
    CHARS_PER_TOKEN = 4

    # Similarity threshold for deduplication
    SIMILARITY_THRESHOLD = 0.8

    def __init__(self, max_tokens: int = 4000):
        """Initialize context builder.

        Args:
            max_tokens: Maximum tokens for context (default 4000)
        """
        self.max_tokens = max_tokens
        self.max_chars = max_tokens * self.CHARS_PER_TOKEN

        logger.info(f"[ContextBuilder] Initialized with max_tokens={max_tokens}")

    def build(self, scored_results: List[ScoredResult]) -> str:
        """Build context string from scored results.

        Args:
            scored_results: Ranked results from Ranker (highest first)

        Returns:
            Formatted context string within token budget
        """
        if not scored_results:
            return ""

        # Deduplicate similar content
        unique_results = self._deduplicate(scored_results)

        # Build context within budget
        context_parts = []
        total_chars = 0

        for i, result in enumerate(unique_results):
            content = result.item.content

            # Format entry
            entry = self._format_entry(content, i + 1, result.score)
            entry_chars = len(entry)

            # Check budget
            if total_chars + entry_chars > self.max_chars:
                # Try truncating this entry
                remaining = self.max_chars - total_chars - 50  # Leave room for "..."
                if remaining > 100:
                    truncated = content[:remaining] + "..."
                    entry = self._format_entry(truncated, i + 1, result.score)
                    context_parts.append(entry)
                break

            context_parts.append(entry)
            total_chars += entry_chars

        # Join with separators
        context = "\n\n".join(context_parts)

        logger.info(
            f"[ContextBuilder] Built context: {len(unique_results)} items, "
            f"~{self._estimate_tokens(context)} tokens"
        )

        return context

    def _format_entry(self, content: str, index: int, score: float) -> str:
        """Format a single context entry.

        Args:
            content: Memory content
            index: Entry number
            score: Relevance score

        Returns:
            Formatted entry string
        """
        # Simple format for now
        return f"[Memory {index}] (relevance: {score:.2f})\n{content}"

    def _deduplicate(
        self,
        results: List[ScoredResult]
    ) -> List[ScoredResult]:
        """Remove near-duplicate content.

        Uses sequence matching to detect similar content.
        Keeps the higher-scored version.

        Args:
            results: Scored results (already sorted by score)

        Returns:
            Deduplicated list
        """
        unique = []
        seen_content = []

        for result in results:
            content = result.item.content.lower()

            # Check against already-seen content
            is_duplicate = False
            for seen in seen_content:
                similarity = SequenceMatcher(None, content, seen).ratio()
                if similarity >= self.SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique.append(result)
                seen_content.append(content)

        if len(unique) < len(results):
            logger.debug(
                f"[ContextBuilder] Deduplicated: {len(results)} → {len(unique)}"
            )

        return unique

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        return len(text) // self.CHARS_PER_TOKEN
