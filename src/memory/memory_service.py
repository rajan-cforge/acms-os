"""Memory Service - Single interface for all memory operations.

Phase 1: Centralized memory management with idempotency.

This service provides:
- CRUD operations for typed memories
- Idempotent create (same content = same ID)
- Correct routing to Weaviate collections by type
- Search across multiple collections

All API routes should use this service instead of direct DB access.
"""

import hashlib
import logging
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timezone

from src.memory.models import (
    MemoryType,
    MemoryTier,
    PrivacyLevel,
    MemoryItem,
    CandidateMemory
)
from src.memory.fact_extractor import FactExtractor
from src.storage.weaviate_client import WeaviateClient
from src.embeddings.openai_embeddings import OpenAIEmbeddings
from src.storage.database import get_session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Feature flag: Enable LLM extraction for new memories
ENABLE_EXTRACTION = True


class MemoryService:
    """Centralized memory service with typed operations.

    All API routes should use this service instead of direct DB access.
    Provides idempotency, correct collection routing, and unified search.

    Example:
        service = MemoryService()

        # Create a semantic memory (user fact)
        memory = await service.create_memory(MemoryItem(
            user_id=user_uuid,
            content="User prefers Python",
            memory_type=MemoryType.SEMANTIC
        ))

        # Search across all collections
        results = await service.search_memories(
            query="python preferences",
            user_id=str(user_uuid)
        )
    """

    # Collection mapping by memory type (Dec 2025 - Updated)
    # Old collections deleted: ACMS_Knowledge_v1, ACMS_Enriched_v1, ACMS_MemoryItems_v1
    COLLECTION_MAP = {
        MemoryType.EPISODIC: "ACMS_Raw_v1",
        MemoryType.SEMANTIC: "ACMS_Knowledge_v2",
        MemoryType.CACHE_ENTRY: "ACMS_Raw_v1",  # Cache merged into raw
        MemoryType.DOCUMENT: "ACMS_Raw_v1"      # Documents merged into raw
    }

    def __init__(
        self,
        weaviate_client: Optional[WeaviateClient] = None,
        embeddings_client: Optional[OpenAIEmbeddings] = None,
        fact_extractor: Optional[FactExtractor] = None
    ):
        """Initialize memory service.

        Args:
            weaviate_client: Optional custom Weaviate client (for testing)
            embeddings_client: Optional custom embeddings client (for testing)
            fact_extractor: Optional custom fact extractor (for testing)
        """
        self._weaviate = weaviate_client or WeaviateClient()
        self._embeddings = embeddings_client or OpenAIEmbeddings()
        self._extractor = fact_extractor or FactExtractor()

        if ENABLE_EXTRACTION:
            logger.info("[MemoryService] Initialized with LLM extraction ENABLED")
        else:
            logger.info("[MemoryService] Initialized with typed memory support")

    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content for deduplication.

        Used for idempotency: same content → same hash → same memory.

        Args:
            content: Memory content text

        Returns:
            64-character hex string (SHA256)
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _get_collection(self, memory_type: MemoryType) -> str:
        """Get Weaviate collection name for memory type.

        Args:
            memory_type: Type of memory

        Returns:
            Collection name string
        """
        return self.COLLECTION_MAP[memory_type]

    async def create_memory(self, item: MemoryItem) -> MemoryItem:
        """Create memory with idempotency and optional LLM extraction.

        If ENABLE_EXTRACTION is True and content is Q&A format:
        - Extract facts using LLM
        - Store each fact as separate SEMANTIC memory
        - Return first extracted fact's memory

        If content already exists for this user, returns existing memory.
        Otherwise creates new memory with embedding in correct collection.

        Args:
            item: MemoryItem to create

        Returns:
            MemoryItem with memory_id (new or existing)
        """
        # P1: LLM Extraction - prevent Q&A pollution
        if ENABLE_EXTRACTION and await self._extractor.should_extract(item.content):
            logger.info(f"[MemoryService] Content needs extraction: {len(item.content)} chars")

            facts = await self._extractor.extract(item.content)

            if facts:
                logger.info(f"[MemoryService] Extracted {len(facts)} facts from Q&A")

                # Store each extracted fact
                created_memories = []
                for fact in facts:
                    fact_item = MemoryItem(
                        user_id=item.user_id,
                        content=fact,
                        memory_type=MemoryType.SEMANTIC,  # Facts go to Knowledge
                        tier=item.tier,
                        tags=item.tags + ["auto_extracted"],
                        privacy_level=item.privacy_level,
                        confidence_score=0.8,  # Extracted facts have good confidence
                        metadata={
                            **item.metadata,
                            "source": "extracted_from_qa",
                            "original_length": len(item.content)
                        }
                    )
                    created = await self._create_single_memory(fact_item)
                    created_memories.append(created)

                # Return first created memory
                if created_memories:
                    return created_memories[0]

            else:
                logger.info("[MemoryService] No facts extracted, skipping storage")
                # Return a placeholder indicating nothing was stored
                item.metadata["status"] = "no_facts_extracted"
                return item

        # Standard path: create single memory
        return await self._create_single_memory(item)

    async def _create_single_memory(self, item: MemoryItem) -> MemoryItem:
        """Create a single memory (internal method).

        Args:
            item: MemoryItem to create

        Returns:
            MemoryItem with memory_id
        """
        # Compute content hash for idempotency
        content_hash = self._compute_hash(item.content)
        item.content_hash = content_hash

        # Check for existing (idempotency)
        existing = await self._find_by_hash(item.user_id, content_hash)
        if existing:
            logger.info(f"[MemoryService] Idempotent hit: returning existing memory {existing.memory_id}")
            return existing

        # Generate embedding
        embedding = self._embeddings.generate_embedding(item.content)

        # Get correct collection
        collection = self._get_collection(item.memory_type)

        # Store in Weaviate
        vector_id = self._weaviate.insert_vector(
            collection=collection,
            vector=embedding,
            data=item.to_weaviate_data()
        )
        item.embedding_vector_id = vector_id

        # Store in PostgreSQL
        await self._store_in_db(item)

        logger.info(
            f"[MemoryService] Created {item.memory_type.value} memory "
            f"{item.memory_id} in {collection}"
        )

        return item

    async def get_memory(self, memory_id: str) -> Optional[MemoryItem]:
        """Get memory by ID.

        Args:
            memory_id: UUID string

        Returns:
            MemoryItem if found, None otherwise
        """
        return await self._fetch_from_db(memory_id)

    async def update_memory(
        self,
        memory_id: str,
        updates: Dict[str, Any]
    ) -> Optional[MemoryItem]:
        """Update memory fields.

        Idempotent: same updates result in same state.

        Args:
            memory_id: UUID string
            updates: Dict of fields to update

        Returns:
            Updated MemoryItem if found, None otherwise
        """
        existing = await self._fetch_from_db(memory_id)
        if not existing:
            return None

        # Apply updates
        for key, value in updates.items():
            if hasattr(existing, key):
                setattr(existing, key, value)

        existing.updated_at = datetime.now(timezone.utc)

        # If content changed, regenerate embedding
        if 'content' in updates:
            embedding = self._embeddings.generate_embedding(existing.content)
            existing.content_hash = self._compute_hash(existing.content)

            # Update Weaviate
            if existing.embedding_vector_id:
                self._weaviate.update_vector(
                    collection=self._get_collection(existing.memory_type),
                    uuid=existing.embedding_vector_id,
                    vector=embedding,
                    data=existing.to_weaviate_data()
                )

        # Update PostgreSQL
        await self._update_in_db(existing)

        return existing

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete memory from all stores.

        Idempotent: deleting non-existent returns True.

        Args:
            memory_id: UUID string

        Returns:
            True (always - idempotent)
        """
        existing = await self._fetch_from_db(memory_id)

        if existing:
            # Delete from Weaviate
            if existing.embedding_vector_id:
                try:
                    self._weaviate.delete_vector(
                        collection=self._get_collection(existing.memory_type),
                        uuid=existing.embedding_vector_id
                    )
                except Exception as e:
                    logger.warning(f"[MemoryService] Weaviate delete error: {e}")

            # Delete from PostgreSQL
            await self._delete_from_db(memory_id)

            logger.info(f"[MemoryService] Deleted memory {memory_id}")

        # Idempotent: return True even if didn't exist
        return True

    async def search_memories(
        self,
        query: str,
        user_id: str,
        limit: int = 10,
        memory_types: Optional[List[MemoryType]] = None,
        privacy_filter: Optional[List[PrivacyLevel]] = None
    ) -> List[Dict[str, Any]]:
        """Search memories across collections.

        Args:
            query: Search query text
            user_id: Filter by user
            limit: Maximum results
            memory_types: Filter by types (default: all)
            privacy_filter: Filter by privacy levels

        Returns:
            List of search results with similarity scores
        """
        # Generate query embedding
        query_embedding = self._embeddings.generate_embedding(query)

        # Determine which collections to search
        if memory_types:
            collections = [self._get_collection(t) for t in memory_types]
        else:
            # Default: search SEMANTIC and CACHE_ENTRY (not EPISODIC/DOCUMENT)
            collections = [
                self.COLLECTION_MAP[MemoryType.SEMANTIC],
                self.COLLECTION_MAP[MemoryType.CACHE_ENTRY]
            ]

        all_results = []

        for collection in collections:
            try:
                results = self._weaviate.semantic_search(
                    collection=collection,
                    query_vector=query_embedding,
                    limit=limit * 2  # Get more for filtering
                )

                # Filter by user_id
                for r in results:
                    props = r.get("properties", {})
                    if props.get("user_id") == user_id:
                        # Apply privacy filter if specified
                        if privacy_filter:
                            if props.get("privacy_level") not in [p.value for p in privacy_filter]:
                                continue

                        all_results.append({
                            "memory_id": props.get("memory_id"),
                            "content": props.get("content"),
                            "memory_type": props.get("memory_type"),
                            "similarity": 1.0 - r.get("distance", 1.0),
                            "distance": r.get("distance", 1.0),
                            "user_id": props.get("user_id"),
                            "tags": props.get("tags", []),
                            "collection": collection
                        })

            except Exception as e:
                logger.warning(f"[MemoryService] Search error in {collection}: {e}")
                continue

        # Sort by similarity and limit
        all_results.sort(key=lambda x: x["similarity"], reverse=True)
        return all_results[:limit]

    async def list_memories(
        self,
        user_id: str,
        memory_type: Optional[MemoryType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[MemoryItem]:
        """List memories with filters.

        Args:
            user_id: Filter by user
            memory_type: Filter by type
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of MemoryItem objects
        """
        return await self._list_from_db(user_id, memory_type, limit, offset)

    # ─────────────────────────────────────────────────────────────────────
    # Private methods (database operations)
    # ─────────────────────────────────────────────────────────────────────

    async def _find_by_hash(
        self,
        user_id: UUID,
        content_hash: str
    ) -> Optional[MemoryItem]:
        """Find existing memory by content hash for idempotency.

        Args:
            user_id: User UUID
            content_hash: SHA256 hash of content

        Returns:
            MemoryItem if found, None otherwise
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT memory_id, user_id, content, content_hash,
                               tier, phase, tags, privacy_level, crs_score,
                               embedding_vector_id, created_at, updated_at,
                               metadata_json
                        FROM memory_items
                        WHERE user_id = :user_id AND content_hash = :content_hash
                        LIMIT 1
                    """),
                    {"user_id": str(user_id), "content_hash": content_hash}
                )
                row = result.fetchone()

                if row:
                    return MemoryItem(
                        memory_id=UUID(row[0]),
                        user_id=UUID(row[1]),
                        content=row[2],
                        content_hash=row[3],
                        tier=MemoryTier(row[4]) if row[4] else MemoryTier.SHORT,
                        memory_type=MemoryType.SEMANTIC,  # Default, would need DB column
                        tags=row[6] or [],
                        privacy_level=PrivacyLevel(row[7]) if row[7] else PrivacyLevel.INTERNAL,
                        confidence_score=row[8] or 0.5,
                        embedding_vector_id=row[9],
                        metadata=row[12] or {}
                    )
                return None

        except Exception as e:
            logger.error(f"[MemoryService] _find_by_hash error: {e}")
            return None

    async def _store_in_db(self, item: MemoryItem) -> bool:
        """Store memory in PostgreSQL.

        Args:
            item: MemoryItem to store

        Returns:
            True if successful
        """
        try:
            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO memory_items (
                            memory_id, user_id, content, content_hash,
                            tier, phase, tags, privacy_level, crs_score,
                            embedding_vector_id, metadata_json, created_at, updated_at
                        ) VALUES (
                            :memory_id, :user_id, :content, :content_hash,
                            :tier, :phase, :tags, :privacy_level, :crs_score,
                            :embedding_vector_id, :metadata_json, :created_at, :updated_at
                        )
                        ON CONFLICT (memory_id) DO NOTHING
                    """),
                    {
                        "memory_id": str(item.memory_id),
                        "user_id": str(item.user_id),
                        "content": item.content,
                        "content_hash": item.content_hash,
                        "tier": item.tier.value,
                        "phase": None,
                        "tags": item.tags,
                        "privacy_level": item.privacy_level.value,
                        "crs_score": item.confidence_score,
                        "embedding_vector_id": item.embedding_vector_id,
                        "metadata_json": item.metadata,
                        "created_at": item.created_at,
                        "updated_at": item.updated_at
                    }
                )
                await session.commit()
                return True

        except Exception as e:
            logger.error(f"[MemoryService] _store_in_db error: {e}")
            return False

    async def _fetch_from_db(self, memory_id: str) -> Optional[MemoryItem]:
        """Fetch memory from PostgreSQL.

        Args:
            memory_id: UUID string

        Returns:
            MemoryItem if found, None otherwise
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT memory_id, user_id, content, content_hash,
                               tier, phase, tags, privacy_level, crs_score,
                               embedding_vector_id, created_at, updated_at,
                               metadata_json
                        FROM memory_items
                        WHERE memory_id = :memory_id
                    """),
                    {"memory_id": memory_id}
                )
                row = result.fetchone()

                if row:
                    return MemoryItem(
                        memory_id=UUID(row[0]),
                        user_id=UUID(row[1]),
                        content=row[2],
                        content_hash=row[3],
                        tier=MemoryTier(row[4]) if row[4] else MemoryTier.SHORT,
                        memory_type=MemoryType.SEMANTIC,  # Default
                        tags=row[6] or [],
                        privacy_level=PrivacyLevel(row[7]) if row[7] else PrivacyLevel.INTERNAL,
                        confidence_score=row[8] or 0.5,
                        embedding_vector_id=row[9],
                        metadata=row[12] or {}
                    )
                return None

        except Exception as e:
            logger.error(f"[MemoryService] _fetch_from_db error: {e}")
            return None

    async def _update_in_db(self, item: MemoryItem) -> bool:
        """Update memory in PostgreSQL.

        Args:
            item: MemoryItem with updated fields

        Returns:
            True if successful
        """
        try:
            async with get_session() as session:
                await session.execute(
                    text("""
                        UPDATE memory_items SET
                            content = :content,
                            content_hash = :content_hash,
                            tier = :tier,
                            tags = :tags,
                            privacy_level = :privacy_level,
                            crs_score = :crs_score,
                            metadata_json = :metadata_json,
                            updated_at = :updated_at
                        WHERE memory_id = :memory_id
                    """),
                    {
                        "memory_id": str(item.memory_id),
                        "content": item.content,
                        "content_hash": item.content_hash,
                        "tier": item.tier.value,
                        "tags": item.tags,
                        "privacy_level": item.privacy_level.value,
                        "crs_score": item.confidence_score,
                        "metadata_json": item.metadata,
                        "updated_at": item.updated_at
                    }
                )
                await session.commit()
                return True

        except Exception as e:
            logger.error(f"[MemoryService] _update_in_db error: {e}")
            return False

    async def _delete_from_db(self, memory_id: str) -> bool:
        """Delete memory from PostgreSQL.

        Args:
            memory_id: UUID string

        Returns:
            True if successful
        """
        try:
            async with get_session() as session:
                await session.execute(
                    text("DELETE FROM memory_items WHERE memory_id = :memory_id"),
                    {"memory_id": memory_id}
                )
                await session.commit()
                return True

        except Exception as e:
            logger.error(f"[MemoryService] _delete_from_db error: {e}")
            return False

    async def _list_from_db(
        self,
        user_id: str,
        memory_type: Optional[MemoryType],
        limit: int,
        offset: int
    ) -> List[MemoryItem]:
        """List memories from PostgreSQL.

        Args:
            user_id: Filter by user
            memory_type: Optional type filter
            limit: Max results
            offset: Pagination offset

        Returns:
            List of MemoryItem objects
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT memory_id, user_id, content, content_hash,
                               tier, phase, tags, privacy_level, crs_score,
                               embedding_vector_id, created_at, updated_at,
                               metadata_json
                        FROM memory_items
                        WHERE user_id = :user_id
                        ORDER BY created_at DESC
                        LIMIT :limit OFFSET :offset
                    """),
                    {"user_id": user_id, "limit": limit, "offset": offset}
                )
                rows = result.fetchall()

                return [
                    MemoryItem(
                        memory_id=UUID(row[0]),
                        user_id=UUID(row[1]),
                        content=row[2],
                        content_hash=row[3],
                        tier=MemoryTier(row[4]) if row[4] else MemoryTier.SHORT,
                        memory_type=MemoryType.SEMANTIC,  # Default
                        tags=row[6] or [],
                        privacy_level=PrivacyLevel(row[7]) if row[7] else PrivacyLevel.INTERNAL,
                        confidence_score=row[8] or 0.5,
                        embedding_vector_id=row[9],
                        metadata=row[12] or {}
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"[MemoryService] _list_from_db error: {e}")
            return []
