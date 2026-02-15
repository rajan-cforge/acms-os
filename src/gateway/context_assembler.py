"""Context assembler for AI Gateway.

Gathers relevant memories from ACMS storage and formats them for agent consumption.
Supports multiple context strategies based on intent type.
Includes thread context for conversation continuity.

Cognitive Architecture Sprint 4: Schema-Driven Context
- Expertise level detection based on TopicSummaries
- Response calibration to user's knowledge depth
- Knowledge gap awareness for scaffolding
"""

import logging
from typing import List, Dict, Any, Optional
from src.storage.memory_crud import MemoryCRUD
from src.gateway.models import IntentType, ThreadContext

logger = logging.getLogger(__name__)

# Minimum relevance threshold for including memories in context
# Memories with similarity < 60% are considered too irrelevant
RELEVANCE_THRESHOLD = 0.60

# ============================================================
# EXPERTISE LEVEL CONFIGURATION (Sprint 4)
# ============================================================
# Cognitive Principle: Schema-Driven Comprehension
# Expert comprehension differs from novice because experts have
# rich schemas organizing knowledge. Calibrate responses accordingly.

EXPERTISE_THRESHOLDS = {
    "beginner": 3,       # 1-3 entries = beginner
    "intermediate": 10,  # 4-10 entries = intermediate
    "advanced": 25,      # 11-25 entries = advanced
    "expert": 100,       # 26+ entries = expert
}

EXPERTISE_EMOJIS = {
    "first_encounter": "✨",
    "beginner": "🌱",
    "intermediate": "🌿",
    "advanced": "🔬",
    "expert": "🏗️",
}

CALIBRATION_INSTRUCTIONS = {
    "first_encounter": (
        "This is a NEW TOPIC for the user. "
        "They have no prior interaction history with ACMS on this topic. "
        "Provide a comprehensive introduction, define key terms, "
        "and offer to explore specific areas of interest."
    ),
    "beginner": (
        "The user is a BEGINNER in this topic. "
        "Please explain concepts clearly, define technical terms, "
        "avoid jargon, and don't assume prior knowledge. "
        "Use analogies where helpful."
    ),
    "intermediate": (
        "The user has INTERMEDIATE knowledge of this topic. "
        "You can assume familiarity with basic concepts, but "
        "explain more advanced topics. Focus on practical applications."
    ),
    "advanced": (
        "The user has ADVANCED knowledge of this topic. "
        "You can use technical terminology and discuss implementation details. "
        "Focus on nuances, edge cases, and best practices."
    ),
    "expert": (
        "The user is an EXPERT in this topic. "
        "Engage at a peer level with technical depth. "
        "Challenge assumptions, discuss trade-offs, and explore advanced patterns. "
        "They likely know the basics - focus on novel insights."
    ),
}


class ContextAssembler:
    """Assembles context from memories for agent execution."""

    def __init__(self):
        """Initialize context assembler."""
        self.memory_crud = MemoryCRUD()
        logger.info("ContextAssembler initialized")

    async def assemble_context(
        self,
        query: str,
        user_id: str,
        intent: IntentType,
        context_limit: int = 5,
        sources: Optional[List[str]] = None
    ) -> str:
        """Assemble context from relevant memories.

        Args:
            query: User query
            user_id: User identifier
            intent: Detected intent type
            context_limit: Maximum number of memories to retrieve
            sources: Optional filter by sources (e.g., ["chatgpt", "gemini"])

        Returns:
            str: Formatted context for agent consumption

        Context Strategy:
            - MEMORY_QUERY: Retrieve up to 20 memories (comprehensive)
            - ANALYSIS: Retrieve 5-10 memories (focused)
            - CREATIVE: No context needed (0 memories)
            - Others: Standard 5 memories
        """
        # Adjust context limit based on intent
        if intent == IntentType.MEMORY_QUERY:
            # Memory queries need comprehensive context
            context_limit = min(context_limit, 20)
        elif intent == IntentType.CREATIVE:
            # Creative tasks don't need context
            logger.info("Creative intent: Skipping context retrieval")
            return ""
        elif intent == IntentType.ANALYSIS:
            # Analysis benefits from moderate context
            context_limit = min(context_limit, 10)

        # Retrieve relevant memories
        try:
            memories = await self.memory_crud.search_memories(
                query=query,
                user_id=user_id,
                limit=context_limit,
                privacy_filter=["PUBLIC", "INTERNAL", "CONFIDENTIAL"]
            )

            # Filter by sources if specified
            if sources:
                memories = [
                    m for m in memories
                    if m.get("source") in sources
                ]

            # Filter by relevance threshold
            # Only include memories with similarity >= 60%
            original_count = len(memories)
            memories = [
                m for m in memories
                if m.get("similarity", 0.0) >= RELEVANCE_THRESHOLD
            ]
            filtered_count = original_count - len(memories)

            if filtered_count > 0:
                logger.info(
                    f"Filtered out {filtered_count} low-relevance memories "
                    f"(< {RELEVANCE_THRESHOLD:.0%} similarity)"
                )

            # Check if passthrough mode (no relevant memories)
            if len(memories) == 0 and original_count > 0:
                logger.info(
                    f"[PASSTHROUGH] All {original_count} memories below {RELEVANCE_THRESHOLD:.0%} threshold → "
                    f"Using AI general knowledge (no memory augmentation)"
                )

            logger.info(
                f"Retrieved {len(memories)} relevant memories for intent: {intent.value}"
            )

            # Format context
            return self._format_context(memories, intent)

        except Exception as e:
            logger.error(f"Error retrieving memories: {e}")
            return ""

    def _format_context(
        self,
        memories: List[Dict[str, Any]],
        intent: IntentType
    ) -> str:
        """Format memories into context string.

        Args:
            memories: List of memory dictionaries
            intent: Intent type for context formatting

        Returns:
            str: Formatted context

        Formatting Strategy:
            - Include memory content, source, timestamp
            - For MEMORY_QUERY: Include tags and similarity scores
            - For CODE_GENERATION: Focus on code snippets
            - Keep total < 10K chars to stay within token limits
        """
        if not memories:
            return ""

        context_parts = []

        # Header
        context_parts.append(
            f"Relevant context from your memory system ({len(memories)} memories):\n"
        )

        # Format each memory
        for i, memory in enumerate(memories, 1):
            content = memory.get("content", "")
            source = memory.get("source", "unknown")
            timestamp = memory.get("created_at", "unknown")
            similarity = memory.get("similarity", 0.0)
            tags = memory.get("tags", [])

            # Truncate very long memories
            if len(content) > 2000:
                content = content[:2000] + "... [truncated]"

            # Build memory entry
            memory_entry = f"\n--- Memory {i} (Source: {source}, Similarity: {similarity:.2f}) ---\n"

            if intent == IntentType.MEMORY_QUERY:
                # Include tags for memory queries
                memory_entry += f"Tags: {', '.join(tags)}\n"
                memory_entry += f"Timestamp: {timestamp}\n"

            memory_entry += f"{content}\n"

            context_parts.append(memory_entry)

            # Stop if context getting too large (< 10K chars total)
            if len("".join(context_parts)) > 10000:
                context_parts.append(
                    "\n[Additional memories truncated to stay within token limit]\n"
                )
                break

        return "".join(context_parts)

    async def get_cross_source_context(
        self,
        query: str,
        user_id: str,
        sources: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get memories grouped by source for cross-source synthesis.

        Args:
            query: User query
            user_id: User identifier
            sources: List of sources to query (e.g., ["chatgpt", "gemini", "claude"])

        Returns:
            dict: Memories grouped by source
                  {"chatgpt": [...], "gemini": [...], "claude": [...]}

        Use Case:
            For "universal brain" queries that need to synthesize across
            multiple AI tool conversations.
        """
        grouped_memories = {}

        for source in sources:
            try:
                memories = await self.memory_crud.search_memories(
                    query=query,
                    user_id=user_id,
                    limit=10,  # Up to 10 per source
                    privacy_filter=["PUBLIC", "INTERNAL", "CONFIDENTIAL"]
                )

                # Filter to only this source
                source_memories = [
                    m for m in memories
                    if m.get("source", "").lower() == source.lower()
                ]

                # Apply relevance threshold
                source_memories = [
                    m for m in source_memories
                    if m.get("similarity", 0.0) >= RELEVANCE_THRESHOLD
                ]

                grouped_memories[source] = source_memories

                logger.info(
                    f"Retrieved {len(source_memories)} memories from {source}"
                )

            except Exception as e:
                logger.error(f"Error retrieving memories from {source}: {e}")
                grouped_memories[source] = []

        return grouped_memories

    # ============================================================
    # SCHEMA-DRIVEN CONTEXT (Sprint 4)
    # ============================================================

    def _get_expertise_thresholds(self) -> Dict[str, int]:
        """Get expertise level thresholds.

        Returns:
            Dict mapping level name to minimum knowledge_depth
        """
        return EXPERTISE_THRESHOLDS.copy()

    def _get_expertise_emoji(self, level: str) -> str:
        """Get emoji for expertise level.

        Args:
            level: Expertise level (beginner, intermediate, advanced, expert)

        Returns:
            Emoji string
        """
        return EXPERTISE_EMOJIS.get(level, "🌱")

    def _determine_expertise_level(
        self,
        topic: str,
        summaries: List[Any],
        total_query_count: int = None
    ) -> str:
        """Determine user's expertise level for a topic.

        Cognitive basis: Schema-driven comprehension.
        Uses relative depth (% of total queries) combined with absolute depth,
        on a logarithmic scale. This prevents the "everything is expert" problem
        when total query count is high.

        Args:
            topic: Topic to check expertise for
            summaries: List of TopicSummary objects
            total_query_count: Optional total queries (calculated if not provided)

        Returns:
            Expertise level string (first_encounter, beginner, intermediate, advanced, expert)
        """
        import math

        # Find summary for this topic
        topic_depth = 0
        for s in summaries:
            slug = getattr(s, 'topic_slug', None)
            if slug and slug.lower() == topic.lower():
                topic_depth = getattr(s, 'knowledge_depth', 0)
                break

        if topic_depth == 0:
            return "first_encounter"

        # Get total queries for relative calculation
        if total_query_count is None or total_query_count == 0:
            total_query_count = sum(
                getattr(s, 'knowledge_depth', 0) for s in summaries
            )

        if total_query_count == 0:
            return "beginner"

        # Relative share of total knowledge
        relative_share = topic_depth / max(total_query_count, 1)

        # Log-scaled absolute depth (diminishing returns)
        # log2(758) ≈ 9.6, log2(87) ≈ 6.4, log2(10) ≈ 3.3
        log_depth = math.log2(topic_depth + 1)

        # Combined score: weighted blend of relative and absolute
        # Max log_depth ≈ 10 for 1000+ queries, normalize to 0-1
        normalized_log = min(log_depth / 10.0, 1.0)
        # Relative share: top topic might be 18% (757/4159)
        normalized_relative = min(relative_share / 0.20, 1.0)

        combined_score = (normalized_log * 0.6) + (normalized_relative * 0.4)

        # Thresholds calibrated for realistic distribution
        if combined_score >= 0.75:      # ~top 3-4 topics
            return "expert"
        elif combined_score >= 0.50:    # ~next 5-6 topics
            return "advanced"
        elif combined_score >= 0.25:    # moderate engagement
            return "intermediate"
        elif topic_depth >= 3:          # at least some interaction
            return "beginner"
        else:
            return "first_encounter"

    def _get_calibration_instructions(self, level: str) -> str:
        """Get LLM calibration instructions for expertise level.

        Args:
            level: Expertise level

        Returns:
            Calibration instruction string
        """
        return CALIBRATION_INSTRUCTIONS.get(level, CALIBRATION_INSTRUCTIONS["beginner"])

    async def _fetch_user_topic_summaries(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Any]:
        """Fetch user's topic summaries from storage.

        Args:
            user_id: User identifier
            limit: Max summaries to fetch

        Returns:
            List of TopicSummary objects
        """
        try:
            from src.storage.weaviate_client import get_weaviate_client

            client = get_weaviate_client()
            # Query ACMS_Topics_v1 collection
            # Implementation depends on Weaviate setup
            # For now, return empty list (populated by compaction)
            return []

        except ImportError:
            logger.debug("[SchemaContext] Weaviate client not available")
            return []
        except Exception as e:
            logger.warning(f"[SchemaContext] Failed to fetch topic summaries: {e}")
            return []

    async def build_schema_context(
        self,
        user_id: str,
        query_topic: str
    ) -> str:
        """Build schema context for expertise-calibrated responses.

        Cognitive Principle: Schema-Driven Comprehension
        Calibrates AI responses to user's expertise level based on
        their accumulated knowledge in TopicSummaries.

        Args:
            user_id: User identifier
            query_topic: Topic of the current query

        Returns:
            Schema context string for system prompt injection
        """
        try:
            # Fetch user's topic summaries
            summaries = await self._fetch_user_topic_summaries(user_id)

            # Determine expertise level
            level = self._determine_expertise_level(query_topic, summaries)
            emoji = self._get_expertise_emoji(level)

            # Get calibration instructions
            calibration = self._get_calibration_instructions(level)

            # Build context
            parts = [
                "# User Knowledge Context",
                f"",
                f"Topic: {query_topic}",
                f"User Expertise: {emoji} {level.title()}",
                f"",
                calibration,
            ]

            # Add related topics if available
            related_topics = self._find_related_topics(query_topic, summaries)
            if related_topics:
                parts.append("")
                parts.append(f"Related topics user knows: {', '.join(related_topics)}")

            # Add knowledge gaps if available
            gaps = self._get_topic_gaps(query_topic, summaries)
            if gaps:
                parts.append("")
                parts.append(f"Knowledge gaps to address: {', '.join(gaps[:3])}")

            return "\n".join(parts)

        except Exception as e:
            logger.error(f"[SchemaContext] Failed to build schema context: {e}")
            # Return minimal default context
            return (
                "# User Knowledge Context\n"
                f"Topic: {query_topic}\n"
                "User Expertise: 🌱 Beginner\n"
                "\n"
                f"{CALIBRATION_INSTRUCTIONS['beginner']}"
            )

    def _find_related_topics(
        self,
        query_topic: str,
        summaries: List[Any]
    ) -> List[str]:
        """Find topics related to the query that user knows.

        Args:
            query_topic: Current query topic
            summaries: User's topic summaries

        Returns:
            List of related topic slugs
        """
        related = []

        # Simple heuristic: topics with overlapping words or common domains
        query_words = set(query_topic.lower().split())

        for s in summaries:
            slug = getattr(s, 'topic_slug', '')
            if slug.lower() == query_topic.lower():
                continue

            # Check for word overlap
            topic_words = set(slug.lower().replace('-', ' ').replace('_', ' ').split())
            if query_words & topic_words:
                related.append(slug)
                continue

            # Check common domain keywords
            devops_keywords = {'docker', 'kubernetes', 'k8s', 'helm', 'terraform', 'ansible'}
            web_keywords = {'react', 'vue', 'angular', 'javascript', 'typescript', 'css', 'html'}
            data_keywords = {'python', 'pandas', 'numpy', 'sql', 'postgresql', 'mongodb'}

            for domain_keywords in [devops_keywords, web_keywords, data_keywords]:
                if query_topic.lower() in domain_keywords and slug.lower() in domain_keywords:
                    related.append(slug)
                    break

        return related[:5]  # Limit to 5 related topics

    def _get_topic_gaps(
        self,
        query_topic: str,
        summaries: List[Any]
    ) -> List[str]:
        """Get knowledge gaps for the query topic.

        Args:
            query_topic: Current query topic
            summaries: User's topic summaries

        Returns:
            List of knowledge gap strings
        """
        for s in summaries:
            slug = getattr(s, 'topic_slug', '')
            if slug.lower() == query_topic.lower():
                return getattr(s, 'knowledge_gaps', [])

        return []

    def format_cross_source_context(
        self,
        grouped_memories: Dict[str, List[Dict[str, Any]]]
    ) -> str:
        """Format cross-source memories for synthesis.

        Args:
            grouped_memories: Memories grouped by source

        Returns:
            str: Formatted context showing chronological progression across sources
        """
        context_parts = [
            "Cross-source context synthesis:\n",
            "=" * 60 + "\n\n"
        ]

        for source, memories in grouped_memories.items():
            if not memories:
                continue

            context_parts.append(f"From {source.upper()} ({len(memories)} memories):\n")
            context_parts.append("-" * 60 + "\n")

            for i, memory in enumerate(memories, 1):
                content = memory.get("content", "")
                timestamp = memory.get("created_at", "unknown")

                # Truncate long content
                if len(content) > 500:
                    content = content[:500] + "..."

                context_parts.append(
                    f"{i}. [{timestamp}] {content}\n\n"
                )

            context_parts.append("\n")

        return "".join(context_parts)

    def format_thread_context(
        self,
        thread_context: Optional[ThreadContext],
        max_summary_chars: int = 2000,
        max_turns_chars: int = 4000
    ) -> str:
        """Format thread context for conversation continuity.

        Args:
            thread_context: Thread context with summary, entities, and recent turns
            max_summary_chars: Maximum characters for summary section
            max_turns_chars: Maximum characters for recent turns section

        Returns:
            str: Formatted thread context with delimiters

        Delimiters per spec:
            BEGIN_CONVERSATION_SUMMARY / END_CONVERSATION_SUMMARY
            BEGIN_ENTITY_NOTES / END_ENTITY_NOTES
            BEGIN_RECENT_TURNS / END_RECENT_TURNS
        """
        if not thread_context:
            return ""

        parts = []

        # Conversation summary (rolling memory)
        if thread_context.summary:
            summary = thread_context.summary
            if len(summary) > max_summary_chars:
                summary = summary[:max_summary_chars] + "... [truncated]"

            parts.append("BEGIN_CONVERSATION_SUMMARY")
            parts.append(summary)
            parts.append("END_CONVERSATION_SUMMARY")
            parts.append("")

        # Entity disambiguation notes
        if thread_context.entities:
            entity_notes = []
            for entity_name, entity_info in thread_context.entities.items():
                if isinstance(entity_info, dict):
                    entity_type = entity_info.get("type", "unknown")
                    not_type = entity_info.get("not", "")
                    note = f"- {entity_name}: {entity_type}"
                    if not_type:
                        note += f" (NOT: {not_type})"
                    entity_notes.append(note)
                else:
                    entity_notes.append(f"- {entity_name}: {entity_info}")

            if entity_notes:
                parts.append("BEGIN_ENTITY_NOTES")
                parts.append("The following entities have been disambiguated in this conversation:")
                parts.extend(entity_notes)
                parts.append("END_ENTITY_NOTES")
                parts.append("")

        # Recent turns (short-term memory)
        if thread_context.recent_turns:
            turns_text = []
            total_chars = 0

            for turn in thread_context.recent_turns:
                role = turn.get("role", "unknown")
                content = turn.get("content", "")

                # Truncate individual turn if very long
                if len(content) > 1500:
                    content = content[:1500] + "..."

                turn_text = f"[{role.upper()}]: {content}"

                # Stop if we're over the limit
                if total_chars + len(turn_text) > max_turns_chars:
                    turns_text.append("... [earlier turns truncated]")
                    break

                turns_text.append(turn_text)
                total_chars += len(turn_text)

            if turns_text:
                parts.append("BEGIN_RECENT_TURNS")
                parts.append(f"Recent conversation ({len(thread_context.recent_turns)} turns total):")
                parts.extend(turns_text)
                parts.append("END_RECENT_TURNS")
                parts.append("")

        # Current topics (if any)
        if thread_context.topic_stack:
            parts.append(f"Current topics being discussed: {', '.join(thread_context.topic_stack[-3:])}")
            parts.append("")

        if not parts:
            return ""

        logger.info(
            f"Formatted thread context: summary={len(thread_context.summary or '')} chars, "
            f"entities={len(thread_context.entities)}, "
            f"turns={len(thread_context.recent_turns)}"
        )

        return "\n".join(parts)

    def build_full_context(
        self,
        thread_context: Optional[ThreadContext],
        memory_context: str,
        web_context: Optional[str] = None,
        schema_context: Optional[str] = None
    ) -> str:
        """Build full context combining thread, memory, web, and schema contexts.

        Args:
            thread_context: Thread context for continuity
            memory_context: Retrieved memory context
            web_context: Optional web search results
            schema_context: Optional schema context for expertise calibration (Sprint 4)

        Returns:
            str: Full formatted context for LLM prompt

        Structure per spec:
            1. Schema context (expertise calibration) - NEW Sprint 4
            2. Thread context (summary + entities + recent turns)
            3. Retrieved RAG context (memories)
            4. Web search results (if any)
        """
        parts = []

        # Schema context first (expertise calibration - Sprint 4)
        # Cognitive basis: Schema-driven comprehension should frame the response
        if schema_context:
            parts.append(schema_context)
            parts.append("")

        # Thread context (conversation continuity)
        thread_ctx_str = self.format_thread_context(thread_context)
        if thread_ctx_str:
            parts.append("# Conversation Context")
            parts.append(thread_ctx_str)

        # Memory context (RAG)
        if memory_context:
            parts.append("BEGIN_RETRIEVED_CONTEXT")
            parts.append(memory_context)
            parts.append("END_RETRIEVED_CONTEXT")
            parts.append("")

        # Web search results
        if web_context:
            parts.append("# Web Search Results")
            parts.append(web_context)
            parts.append("")

        if not parts:
            return ""

        return "\n".join(parts)


# Global instance
_context_assembler_instance = None


def get_context_assembler() -> ContextAssembler:
    """Get global context assembler instance.

    Returns:
        ContextAssembler: Global instance
    """
    global _context_assembler_instance
    if _context_assembler_instance is None:
        _context_assembler_instance = ContextAssembler()
    return _context_assembler_instance
