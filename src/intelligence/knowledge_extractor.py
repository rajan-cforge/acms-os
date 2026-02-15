"""Knowledge Extractor - Intelligent knowledge extraction using Claude Sonnet 4.

Extracts structured knowledge from Q&A interactions:
- Intent analysis (the "why" behind queries)
- Entity and relationship extraction
- Dynamic topic clustering
- Atomic fact extraction

This replaces the old fact_extractor.py which only extracted simple facts.

Usage:
    extractor = KnowledgeExtractor()
    entry = await extractor.extract(
        query="How do I implement OAuth2?",
        answer="To implement OAuth2...",
        user_id="user-123"
    )
    print(entry.why_context)  # "User is building secure API authentication"
"""

import os
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum

import anthropic

logger = logging.getLogger(__name__)


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class IntentAnalysis:
    """Analysis of user's intent behind a query."""
    primary_intent: str  # What user is trying to achieve
    problem_domain: str  # Area/field this relates to
    why_context: str  # Human-readable "why" explanation
    user_context_signals: List[str] = field(default_factory=list)  # Inferred context clues
    confidence: float = 0.8  # Confidence in this analysis


@dataclass
class Entity:
    """A named entity extracted from content."""
    name: str  # Entity name as mentioned
    canonical: str  # Normalized lowercase form
    entity_type: str  # framework, language, concept, tool, protocol, library
    importance: str = "mentioned"  # primary, secondary, mentioned


@dataclass
class Relation:
    """A relationship between two entities."""
    from_entity: str  # Source entity (canonical name)
    to_entity: str  # Target entity (canonical name)
    relation_type: str  # USES, IMPLEMENTS, PART_OF, ALTERNATIVE_TO, REQUIRES, PRODUCES


@dataclass
class KnowledgeEntry:
    """Complete knowledge extraction result."""
    canonical_query: str  # Normalized question
    answer_summary: str  # Condensed answer
    full_answer: str  # Complete answer
    intent: IntentAnalysis  # Intent analysis
    entities: List[Entity]  # Extracted entities
    relations: List[Relation]  # Entity relationships
    topic_cluster: str  # Primary topic slug
    related_topics: List[str]  # Related topic slugs
    key_facts: List[str]  # Atomic facts
    user_id: str
    source_query_id: Optional[str] = None
    extraction_model: str = "claude-sonnet-4-20250514"
    extraction_confidence: float = 0.8
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# Extraction Prompt
# ============================================================================

EXTRACTION_PROMPT = """You are a knowledge extraction system for a developer's personal knowledge base.

Analyze this Q&A interaction and extract structured knowledge.

## Query
{query}

## Answer
{answer}

## Your Task

Extract the following in JSON format. Be thorough but concise.

```json
{{
  "intent_analysis": {{
    "primary_intent": "What is the user fundamentally trying to learn or accomplish? (1 sentence)",
    "problem_domain": "What area/field does this relate to? (e.g., API Security, Database Design, Machine Learning)",
    "why_context": "A 1-2 sentence explanation of WHY the user is asking this - what's their likely goal or situation?",
    "user_context_signals": ["List", "of", "inferred", "context", "clues"],
    "confidence": 0.85
  }},
  "entities": [
    {{
      "name": "Entity name as mentioned (e.g., FastAPI)",
      "canonical": "normalized_lowercase (e.g., fastapi)",
      "type": "framework|language|concept|tool|protocol|library",
      "importance": "primary|secondary|mentioned"
    }}
  ],
  "relations": [
    {{
      "from": "source entity canonical name",
      "to": "target entity canonical name",
      "type": "USES|IMPLEMENTS|PART_OF|ALTERNATIVE_TO|REQUIRES|PRODUCES"
    }}
  ],
  "topic_cluster": "descriptive-slug-for-primary-topic",
  "related_topics": ["other-relevant-topic-slugs"],
  "key_facts": [
    "Standalone factual statements from the answer (max 5)",
    "Each should be self-contained and useful out of context",
    "Don't start with 'It', 'This', or reference the user"
  ],
  "canonical_query": "A cleaned, normalized version of the question",
  "answer_summary": "A 2-3 sentence summary of the key points in the answer"
}}
```

Rules:
1. The "why_context" MUST explain the user's likely situation/goal, not just restate the question
2. Entity canonicals should be lowercase with no spaces (use underscores if needed)
3. Only extract facts that are genuinely useful to remember long-term
4. If the query is trivial/greeting/meta, return minimal extraction with confidence < 0.3
5. Topic clusters should be descriptive slugs like "api-authentication" or "python-async-patterns"
6. Return valid JSON only - no markdown code blocks or extra text
"""


# ============================================================================
# Knowledge Extractor
# ============================================================================

class KnowledgeExtractor:
    """Extract structured knowledge from Q&A using Claude Sonnet 4.

    Features:
    - Intent analysis (the "why")
    - Entity and relationship extraction
    - Dynamic topic clustering
    - Atomic fact extraction
    """

    # Content limits to avoid excessive token usage
    MAX_QUERY_CHARS = 4000
    MAX_ANSWER_CHARS = 12000
    MAX_TOTAL_CHARS = 15000

    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        """Initialize the knowledge extractor.

        Args:
            model: Claude model to use (default: claude-sonnet-4)

        Raises:
            ValueError: If ANTHROPIC_API_KEY is not set
        """
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY environment variable is required for KnowledgeExtractor"
            )

        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        logger.info(f"[KnowledgeExtractor] Initialized with model: {model}")

    async def _call_claude(self, prompt: str) -> Dict[str, Any]:
        """Call Claude API and parse JSON response.

        Args:
            prompt: The formatted prompt to send

        Returns:
            Parsed JSON response as dict

        Raises:
            Exception: If API call fails or response isn't valid JSON
        """
        try:
            message = self._client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            response_text = message.content[0].text.strip()

            # Handle potential markdown code blocks
            if response_text.startswith("```"):
                # Extract JSON from code block
                lines = response_text.split("\n")
                json_lines = []
                in_block = False
                for line in lines:
                    if line.startswith("```"):
                        in_block = not in_block
                        continue
                    if in_block or (not line.startswith("```") and json_lines):
                        json_lines.append(line)
                response_text = "\n".join(json_lines)

            return json.loads(response_text)

        except json.JSONDecodeError as e:
            logger.error(f"[KnowledgeExtractor] JSON parse error: {e}")
            logger.debug(f"Response was: {response_text[:500]}...")
            raise
        except anthropic.APIError as e:
            logger.error(f"[KnowledgeExtractor] API error: {e}")
            raise

    def _truncate_content(self, query: str, answer: str) -> Tuple[str, str]:
        """Truncate query and answer to fit within limits.

        Args:
            query: Original query
            answer: Original answer

        Returns:
            Tuple of (truncated_query, truncated_answer)
        """
        truncated_query = query[:self.MAX_QUERY_CHARS]
        truncated_answer = answer[:self.MAX_ANSWER_CHARS]

        # Ensure total is under limit
        total = len(truncated_query) + len(truncated_answer)
        if total > self.MAX_TOTAL_CHARS:
            # Prioritize query, trim answer
            available_for_answer = self.MAX_TOTAL_CHARS - len(truncated_query)
            truncated_answer = answer[:max(available_for_answer, 1000)]

        return truncated_query, truncated_answer

    async def extract_intent(
        self,
        query: str,
        answer: str
    ) -> IntentAnalysis:
        """Extract intent analysis from Q&A.

        Args:
            query: User's question
            answer: AI's response

        Returns:
            IntentAnalysis with why_context and related fields
        """
        query, answer = self._truncate_content(query, answer)
        prompt = EXTRACTION_PROMPT.format(query=query, answer=answer)
        response = await self._call_claude(prompt)

        intent_data = response.get("intent_analysis", {})
        return IntentAnalysis(
            primary_intent=intent_data.get("primary_intent", "Unknown"),
            problem_domain=intent_data.get("problem_domain", "General"),
            why_context=intent_data.get("why_context", "Unable to determine context"),
            user_context_signals=intent_data.get("user_context_signals", []),
            confidence=intent_data.get("confidence", 0.5)
        )

    async def extract_entities(
        self,
        content: str
    ) -> Tuple[List[Entity], List[Relation]]:
        """Extract entities and relationships from content.

        Args:
            content: Text content to analyze

        Returns:
            Tuple of (entities list, relations list)
        """
        # Use a simplified prompt for just entity extraction
        prompt = f"""Extract named entities and their relationships from this text.
Return JSON with "entities" and "relations" arrays.

Text: {content[:self.MAX_TOTAL_CHARS]}

Entities should have: name, canonical (lowercase), type (framework|language|concept|tool|protocol|library), importance (primary|secondary|mentioned)
Relations should have: from (canonical), to (canonical), type (USES|IMPLEMENTS|PART_OF|ALTERNATIVE_TO|REQUIRES|PRODUCES)

Return valid JSON only."""

        response = await self._call_claude(prompt)

        entities = []
        for e in response.get("entities", []):
            entities.append(Entity(
                name=e.get("name", ""),
                canonical=e.get("canonical", "").lower().replace(" ", "_"),
                entity_type=e.get("type", "concept"),
                importance=e.get("importance", "mentioned")
            ))

        relations = []
        for r in response.get("relations", []):
            relations.append(Relation(
                from_entity=r.get("from", ""),
                to_entity=r.get("to", ""),
                relation_type=r.get("type", "RELATED_TO")
            ))

        return entities, relations

    async def extract_topic_cluster(
        self,
        query: str,
        entities: List[Entity]
    ) -> Tuple[str, List[str]]:
        """Extract topic cluster for this query.

        Args:
            query: User's question
            entities: Previously extracted entities

        Returns:
            Tuple of (primary topic slug, related topic slugs)
        """
        entity_names = [e.canonical for e in entities]

        prompt = f"""Determine the primary topic cluster for this query.
Return JSON with "topic_cluster" (slug format like "api-authentication") and "related_topics" (list of slugs).

Query: {query[:1000]}
Entities found: {entity_names}

The topic should be descriptive and specific. Use lowercase-with-dashes format.
Return valid JSON only."""

        response = await self._call_claude(prompt)

        topic = response.get("topic_cluster", "general")
        related = response.get("related_topics", [])

        # Ensure slug format
        topic = self._to_slug(topic)
        related = [self._to_slug(t) for t in related]

        return topic, related

    def _to_slug(self, text: str) -> str:
        """Convert text to slug format."""
        slug = text.lower()
        slug = re.sub(r'[^a-z0-9\-]', '-', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        return slug or "general"

    async def extract_facts(self, answer: str) -> List[str]:
        """Extract atomic facts from answer.

        Args:
            answer: AI response text

        Returns:
            List of self-contained fact strings (0-5)
        """
        prompt = f"""Extract 0-5 standalone facts from this text.
Each fact must be self-contained (understandable without context).
Don't start facts with "It", "This", or reference "the user".
Return JSON with "key_facts" array of strings.

Text: {answer[:self.MAX_ANSWER_CHARS]}

Return valid JSON only."""

        response = await self._call_claude(prompt)

        facts = response.get("key_facts", [])

        # Filter out trivial or context-dependent facts
        valid_facts = []
        for fact in facts:
            if not isinstance(fact, str):
                continue
            if len(fact) < 20:
                continue
            if fact.lower().startswith(("it ", "this ", "the user")):
                continue
            valid_facts.append(fact)

        return valid_facts[:5]  # Max 5 facts

    async def extract(
        self,
        query: str,
        answer: str,
        user_id: str,
        source_query_id: Optional[str] = None
    ) -> KnowledgeEntry:
        """Perform full knowledge extraction.

        This is the main entry point that extracts all knowledge components
        in a single LLM call for efficiency.

        Args:
            query: User's question
            answer: AI's response
            user_id: User identifier
            source_query_id: Optional ID of source query

        Returns:
            Complete KnowledgeEntry with all extracted information
        """
        query_trunc, answer_trunc = self._truncate_content(query, answer)

        # Handle empty/trivial input
        if not query.strip() or not answer.strip():
            return self._create_minimal_entry(
                query, answer, user_id, source_query_id, confidence=0.1
            )

        # Single LLM call for full extraction
        prompt = EXTRACTION_PROMPT.format(query=query_trunc, answer=answer_trunc)

        try:
            response = await self._call_claude(prompt)
        except Exception as e:
            logger.error(f"[KnowledgeExtractor] Extraction failed: {e}")
            raise

        # Parse intent analysis
        intent_data = response.get("intent_analysis", {})
        intent = IntentAnalysis(
            primary_intent=intent_data.get("primary_intent", "Unknown"),
            problem_domain=intent_data.get("problem_domain", "General"),
            why_context=intent_data.get("why_context", "Unable to determine context"),
            user_context_signals=intent_data.get("user_context_signals", []),
            confidence=intent_data.get("confidence", 0.5)
        )

        # Parse entities
        entities = []
        for e in response.get("entities", []):
            entities.append(Entity(
                name=e.get("name", ""),
                canonical=e.get("canonical", "").lower().replace(" ", "_"),
                entity_type=e.get("type", "concept"),
                importance=e.get("importance", "mentioned")
            ))

        # Parse relations
        relations = []
        for r in response.get("relations", []):
            relations.append(Relation(
                from_entity=r.get("from", ""),
                to_entity=r.get("to", ""),
                relation_type=r.get("type", "RELATED_TO")
            ))

        # Get topic cluster
        topic_cluster = self._to_slug(response.get("topic_cluster", "general"))
        related_topics = [
            self._to_slug(t) for t in response.get("related_topics", [])
        ]

        # Get facts
        facts = response.get("key_facts", [])
        valid_facts = [
            f for f in facts
            if isinstance(f, str) and len(f) > 20
            and not f.lower().startswith(("it ", "this ", "the user"))
        ][:5]

        # Determine overall confidence
        confidence = intent.confidence
        if not entities and not valid_facts:
            confidence = min(confidence, 0.3)  # Low confidence if nothing extracted
        if len(query) < 10:
            confidence = min(confidence, 0.2)  # Very short query

        return KnowledgeEntry(
            canonical_query=response.get("canonical_query", query),
            answer_summary=response.get("answer_summary", answer[:200]),
            full_answer=answer,
            intent=intent,
            entities=entities,
            relations=relations,
            topic_cluster=topic_cluster,
            related_topics=related_topics,
            key_facts=valid_facts,
            user_id=user_id,
            source_query_id=source_query_id,
            extraction_model=self.model,
            extraction_confidence=confidence,
            created_at=datetime.now(timezone.utc)
        )

    def _create_minimal_entry(
        self,
        query: str,
        answer: str,
        user_id: str,
        source_query_id: Optional[str],
        confidence: float
    ) -> KnowledgeEntry:
        """Create a minimal entry for trivial/empty content."""
        return KnowledgeEntry(
            canonical_query=query or "",
            answer_summary=answer[:200] if answer else "",
            full_answer=answer or "",
            intent=IntentAnalysis(
                primary_intent="Unknown",
                problem_domain="General",
                why_context="Insufficient context to determine intent",
                user_context_signals=[],
                confidence=confidence
            ),
            entities=[],
            relations=[],
            topic_cluster="general",
            related_topics=[],
            key_facts=[],
            user_id=user_id,
            source_query_id=source_query_id,
            extraction_model=self.model,
            extraction_confidence=confidence
        )


# Global instance cache
_extractor_instance: Optional[KnowledgeExtractor] = None


def get_knowledge_extractor(model: str = "claude-sonnet-4-20250514") -> KnowledgeExtractor:
    """Get or create global KnowledgeExtractor instance.

    Args:
        model: Claude model to use

    Returns:
        KnowledgeExtractor instance
    """
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = KnowledgeExtractor(model=model)
    return _extractor_instance
