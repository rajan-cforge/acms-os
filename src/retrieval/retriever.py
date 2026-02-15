"""Retriever - Stage 1 of retrieval pipeline.

Responsibilities:
- Vector search in Weaviate collections
- Apply user/privacy filters
- Return raw results for ranking

Does NOT:
- Rank results (that's Ranker's job)
- Build context (that's ContextBuilder's job)
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from src.storage.weaviate_client import WeaviateClient

logger = logging.getLogger(__name__)


@dataclass
class RawResult:
    """Raw result from vector search.

    Attributes:
        uuid: Weaviate object UUID
        content: Memory content text
        distance: Vector distance (lower = more similar)
        source: Source collection identifier
        properties: Full properties dict from Weaviate
    """
    uuid: str
    content: str
    distance: float
    source: str
    properties: Dict[str, Any]

    @property
    def similarity(self) -> float:
        """Convert distance to similarity (0-1).

        Similarity = 1.0 - distance
        Higher similarity = more relevant
        """
        return 1.0 - self.distance


class Retriever:
    """Stage 1: Raw retrieval from vector stores.

    Fetches raw results from Weaviate collections without ranking.
    Applies basic filters (user_id, privacy_level).

    Example:
        retriever = Retriever()
        results = await retriever.retrieve(
            query_embedding=[0.1] * 768,
            text_query="python preferences",
            filters={"user_id": "uuid", "privacy_level": ["PUBLIC", "INTERNAL"]},
            limit=20
        )
    """

    # Map source names to Weaviate collections (Dec 2025 - Cleaned up)
    # Only 2 collections remain after cleanup:
    # - ACMS_Raw_v1: All Q&A pairs (101K records)
    # - ACMS_Knowledge_v2: Extracted knowledge with intent/entities/facts
    COLLECTION_MAP = {
        "raw": "ACMS_Raw_v1",
        "knowledge": "ACMS_Knowledge_v2"
    }

    # Default sources to search - prioritize knowledge (structured) over raw (Q&A pairs)
    DEFAULT_SOURCES = ["knowledge", "raw"]

    def __init__(self, weaviate_client: Optional[WeaviateClient] = None):
        """Initialize retriever.

        Args:
            weaviate_client: Optional custom Weaviate client (for testing)
        """
        self._weaviate = weaviate_client or WeaviateClient()
        logger.info("[Retriever] Initialized with %d source collections", len(self.COLLECTION_MAP))

    async def retrieve(
        self,
        query_embedding: List[float],
        text_query: str,
        filters: Dict[str, Any],
        limit: int = 20,
        sources: Optional[List[str]] = None
    ) -> List[RawResult]:
        """Retrieve raw results from vector stores.

        Args:
            query_embedding: 768-dim query embedding vector
            text_query: Original query text (for logging/debugging)
            filters: Dict with user_id, privacy_level, etc.
            limit: Maximum results per collection
            sources: Which sources to search (default: knowledge, enriched)

        Returns:
            List of RawResult (unsorted, unranked)
        """
        # Early exit for empty query
        if not query_embedding or not text_query:
            logger.debug("[Retriever] Empty query, returning empty results")
            return []

        sources = sources or self.DEFAULT_SOURCES
        all_results: List[RawResult] = []

        for source in sources:
            if source not in self.COLLECTION_MAP:
                logger.warning(f"[Retriever] Unknown source: {source}")
                continue

            collection = self.COLLECTION_MAP[source]

            try:
                raw = self._weaviate.semantic_search(
                    collection=collection,
                    query_vector=query_embedding,
                    limit=limit * 2  # Get more for filtering
                )

                # Convert to RawResult and apply filters
                for r in raw:
                    props = r.get("properties", {})

                    # Apply user filter
                    if "user_id" in filters:
                        if props.get("user_id") != filters["user_id"]:
                            continue

                    # Apply privacy filter
                    if "privacy_level" in filters:
                        allowed_levels = filters["privacy_level"]
                        if isinstance(allowed_levels, list):
                            if props.get("privacy_level") not in allowed_levels:
                                continue
                        elif props.get("privacy_level") != allowed_levels:
                            continue

                    all_results.append(RawResult(
                        uuid=r.get("uuid", ""),
                        content=props.get("content", ""),
                        distance=r.get("distance", 1.0),
                        source=source,
                        properties=props
                    ))

                logger.debug(
                    f"[Retriever] {collection}: {len(raw)} raw → "
                    f"{len([r for r in all_results if r.source == source])} after filter"
                )

            except Exception as e:
                logger.error(f"[Retriever] Error searching {collection}: {e}")
                continue

        # Apply limit across all sources
        if len(all_results) > limit:
            # Keep top by similarity (lowest distance first)
            all_results.sort(key=lambda r: r.distance)
            all_results = all_results[:limit]

        logger.info(
            f"[Retriever] Retrieved {len(all_results)} results from {sources} "
            f"for query: '{text_query[:50]}...'"
        )

        return all_results

    async def retrieve_by_ids(
        self,
        memory_ids: List[str],
        source: str = "knowledge"
    ) -> List[RawResult]:
        """Retrieve specific memories by ID.

        Args:
            memory_ids: List of memory UUIDs
            source: Which collection to search

        Returns:
            List of RawResult for found memories
        """
        if source not in self.COLLECTION_MAP:
            return []

        collection = self.COLLECTION_MAP[source]
        results = []

        for memory_id in memory_ids:
            try:
                obj = self._weaviate.get_vector_by_uuid(collection, memory_id)
                if obj:
                    props = obj.get("properties", {})
                    results.append(RawResult(
                        uuid=memory_id,
                        content=props.get("content", ""),
                        distance=0.0,  # Exact match
                        source=source,
                        properties=props
                    ))
            except Exception as e:
                logger.warning(f"[Retriever] Could not fetch {memory_id}: {e}")

        return results
