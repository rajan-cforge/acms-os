"""Dual Memory Service - Week 6 Day 3 (Updated Dec 2025)

Implements parallel search across:
1. ACMS_Raw_v1 (raw Q&A pairs - 101K records)
2. ACMS_Knowledge_v2 (structured knowledge with intent, entities, topics, facts)

Replaces single-memory search with intelligent dual-source retrieval.

NOTE: Dec 2025 - Updated to use new unified collections after cleanup.
Old collections (ACMS_Enriched_v1, ACMS_Knowledge_v1) have been deleted.
"""

import asyncio
import hashlib
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID, uuid4

from src.storage.weaviate_client import WeaviateClient
from src.storage.database import get_session
from sqlalchemy import text


class DualMemoryService:
    """Service for searching across raw Q&A and knowledge base in parallel.

    Architecture (Dec 2025 - Updated):
    - ACMS_Raw_v1: Raw Q&A pairs (101K records, 1536d embeddings)
    - ACMS_Knowledge_v2: Structured knowledge (intent, entities, topics, facts)
    - Query Metrics: Logs all queries for enrichment pipeline

    Usage:
        service = DualMemoryService()
        raw_hits, knowledge = await service.search_dual(
            query="What is ACMS?",
            query_vector=[0.1, 0.2, ...],
            user_id="uuid",
            conversation_id="uuid"
        )
    """

    def __init__(self):
        """Initialize dual memory service with Weaviate client."""
        self.weaviate = WeaviateClient()

    async def search_dual(
        self,
        query: str,
        query_vector: List[float],
        user_id: str,
        conversation_id: Optional[str] = None,
        cache_limit: int = 5,
        knowledge_limit: int = 10,
        cache_threshold: float = 0.85,
        knowledge_threshold: float = 0.60
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Search cache and knowledge in parallel.

        Args:
            query: User's query text
            query_vector: 768-dim embedding from OpenAI
            user_id: UUID of user making query
            conversation_id: Optional conversation UUID
            cache_limit: Max cache results to return
            knowledge_limit: Max knowledge results to return
            cache_threshold: Minimum similarity for cache hits (0.85 = very similar)
            knowledge_threshold: Minimum similarity for knowledge (0.60 = relevant)

        Returns:
            Tuple of (cache_hits, knowledge_facts)
            - cache_hits: List of raw Q&A from ACMS_Raw_v1
            - knowledge_facts: List of structured knowledge from ACMS_Knowledge_v2
        """

        # Parallel search in both collections
        cache_task = asyncio.to_thread(
            self._search_cache,
            query_vector,
            cache_limit,
            cache_threshold
        )

        knowledge_task = asyncio.to_thread(
            self._search_knowledge,
            query_vector,
            user_id,
            knowledge_limit,
            knowledge_threshold
        )

        # Wait for both searches
        cache_hits, knowledge_facts = await asyncio.gather(cache_task, knowledge_task)

        return cache_hits, knowledge_facts

    def _search_cache(
        self,
        query_vector: List[float],
        limit: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Search ACMS_Raw_v1 for similar Q&A pairs.

        Args:
            query_vector: Query embedding (1536d)
            limit: Max results
            threshold: Minimum similarity (0.85 = very high)

        Returns:
            List of raw Q&A hits with structure:
            {
                'id': 'uuid',
                'canonical_query': 'extracted from content',
                'summarized_answer': 'extracted from content',
                'confidence_score': similarity,
                'usage_count': 0,
                'distance': 0.02,
                'similarity': 0.98
            }
        """
        try:
            results = self.weaviate.semantic_search(
                collection="ACMS_Raw_v1",
                query_vector=query_vector,
                limit=limit * 2  # Get more, filter by threshold
            )

            # Filter by similarity threshold
            filtered = []
            for r in results:
                distance = r.get('distance', 1.0)
                similarity = 1 - distance  # Convert distance to similarity

                if similarity >= threshold:
                    props = r['properties']
                    content = props.get('content', '')

                    # Parse Q&A from content (format: "Q: ...\nA: ...")
                    canonical_query = content
                    summarized_answer = ""
                    if "Q:" in content and "A:" in content:
                        parts = content.split("A:", 1)
                        canonical_query = parts[0].replace("Q:", "").strip()[:500]
                        summarized_answer = parts[1].strip()[:2000] if len(parts) > 1 else ""

                    filtered.append({
                        'id': r['uuid'],
                        'canonical_query': canonical_query,
                        'summarized_answer': summarized_answer,
                        'confidence_score': similarity,  # Use similarity as confidence
                        'usage_count': 0,  # Not tracked in ACMS_Raw_v1
                        'original_agent': props.get('agent', ''),
                        'distance': distance,
                        'similarity': similarity,
                        'source': 'raw'
                    })

            # Sort by similarity (descending) and limit
            filtered.sort(key=lambda x: x['similarity'], reverse=True)
            return filtered[:limit]

        except Exception as e:
            print(f"[DualMemory] Raw search error: {e}")
            return []

    def _search_knowledge(
        self,
        query_vector: List[float],
        user_id: str,
        limit: int,
        threshold: float
    ) -> List[Dict[str, Any]]:
        """Search ACMS_Knowledge_v2 for structured knowledge.

        Args:
            query_vector: Query embedding (1536d)
            user_id: Filter by user_id
            limit: Max results
            threshold: Minimum similarity (0.60 = relevant)

        Returns:
            List of knowledge entries with structure:
            {
                'id': 'uuid',
                'content': 'canonical_query + answer_summary',
                'source_type': 'knowledge',
                'confidence': extraction_confidence,
                'tags': related_topics,
                'distance': 0.35,
                'similarity': 0.65
            }
        """
        try:
            results = self.weaviate.semantic_search(
                collection="ACMS_Knowledge_v2",
                query_vector=query_vector,
                limit=limit * 2  # Get more, filter by threshold and user_id
            )

            # Filter by similarity threshold and user_id
            filtered = []
            for r in results:
                props = r['properties']

                # Check user_id match (optional - may want all knowledge)
                if user_id and props.get('user_id') and props.get('user_id') != user_id:
                    continue

                distance = r.get('distance', 1.0)
                similarity = 1 - distance

                if similarity >= threshold:
                    # Combine canonical_query and answer_summary as content
                    content = f"{props.get('canonical_query', '')}\n{props.get('answer_summary', '')}"

                    filtered.append({
                        'id': r['uuid'],
                        'content': content,
                        'source_type': 'knowledge',
                        'confidence': props.get('extraction_confidence', 0.0),
                        'tags': props.get('related_topics', []),
                        'privacy_level': 'PUBLIC',  # Knowledge entries are derived
                        'verified': True,  # Extracted by Claude Sonnet 4
                        'topic_cluster': props.get('topic_cluster', ''),
                        'primary_intent': props.get('primary_intent', ''),
                        'distance': distance,
                        'similarity': similarity,
                        'source': 'knowledge'
                    })

            # Sort by similarity (descending) and limit
            filtered.sort(key=lambda x: x['similarity'], reverse=True)
            return filtered[:limit]

        except Exception as e:
            print(f"[DualMemory] Knowledge search error: {e}")
            return []

    async def log_query_metrics(
        self,
        query_text: str,
        conversation_id: Optional[str],
        agent_used: str,
        latency_ms: int,
        cost_usd: float,
        memories_used: int,
        search_used: bool,
        query_intent: Optional[str] = None
    ) -> UUID:
        """Log query to query_metrics table for enrichment pipeline.

        Args:
            query_text: User's query
            conversation_id: Optional conversation UUID
            agent_used: "CLAUDE_SONNET", "GPT_4O", etc.
            latency_ms: Response time in milliseconds
            cost_usd: Cost of this query
            memories_used: Number of memories retrieved
            search_used: Whether web search was used
            query_intent: Optional intent classification

        Returns:
            UUID of created query_metrics row
        """
        query_hash = hashlib.sha256(query_text.encode()).hexdigest()
        query_id = uuid4()

        async with get_session() as db:
            try:
                await db.execute(
                    text("""
                        INSERT INTO query_metrics (
                            id,
                            conversation_id,
                            query_hash,
                            query_text,
                            query_intent,
                            agent_used,
                            latency_ms,
                            cost_usd,
                            memories_used,
                            search_used,
                            enrichment_status,
                            created_at
                        ) VALUES (
                            :id,
                            :conversation_id,
                            :query_hash,
                            :query_text,
                            :query_intent,
                            :agent_used,
                            :latency_ms,
                            :cost_usd,
                            :memories_used,
                            :search_used,
                            'pending',
                            :created_at
                        )
                    """),
                    {
                        "id": str(query_id),
                        "conversation_id": conversation_id,
                        "query_hash": query_hash,
                        "query_text": query_text,
                        "query_intent": query_intent,
                        "agent_used": agent_used,
                        "latency_ms": latency_ms,
                        "cost_usd": cost_usd,
                        "memories_used": memories_used,
                        "search_used": search_used,
                        "created_at": datetime.utcnow()
                    }
                )
                await db.commit()
                return query_id
            except Exception as e:
                print(f"[DualMemory] Error logging query metrics: {e}")
                await db.rollback()
                return query_id

    async def update_cache_hit(self, cache_id: str) -> None:
        """Update hit statistics when a raw Q&A is reused.

        NOTE: Dec 2025 - ACMS_Raw_v1 doesn't track usage_count.
        This method is kept for API compatibility but does minimal work.

        Args:
            cache_id: UUID of ACMS_Raw_v1 entry
        """
        try:
            # ACMS_Raw_v1 doesn't have usage_count or cost_savings fields
            # Just log the hit for now - could be enhanced later
            print(f"[DualMemory] Raw hit for {cache_id[:8]}...")

        except Exception as e:
            print(f"[DualMemory] Error updating cache hit: {e}")

    def close(self):
        """Close Weaviate connection."""
        self.weaviate.close()
