"""Memory CRUD operations for ACMS.

Provides high-level interface for memory storage, retrieval, and search.
Integrates PostgreSQL, Weaviate, OpenAI embeddings, and encryption.

Complete pipeline:
1. Content -> Hash (deduplication)
2. Content -> Encrypt (XChaCha20-Poly1305)
3. Content -> Embed (OpenAI text-embedding-3-small 768-dim)
4. Store metadata in PostgreSQL
5. Store vector in Weaviate
6. Return memory_id
"""

import hashlib
import re
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from uuid import uuid4, UUID

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import User, MemoryItem, AuditLog
from src.storage.database import get_session, get_db_pool
from src.storage.encryption import get_global_encryption_manager
from src.storage.weaviate_client import WeaviateClient
from src.storage.ollama_client import get_global_ollama_client
from src.embeddings.openai_embeddings import OpenAIEmbeddings

# PHASE 0: Data Flow Audit (Dec 2025)
from src.audit.logger import get_audit_logger
from src.audit.models import DataClassification
from src.core.simple_crs import SimpleCRS
from src.core.privacy_detector import get_privacy_detector


class MemoryCRUD:
    """Memory CRUD operations with full storage pipeline.

    Example:
        crud = MemoryCRUD()
        memory_id = await crud.create_memory(
            user_id="uuid",
            content="Memory content",
            tags=["tag1", "tag2"],
            phase="phase1"
        )
    """

    def __init__(
        self,
        encryption_manager=None,
        weaviate_client=None,
        ollama_client=None,
        openai_embeddings=None,
        crs_engine=None,
        privacy_detector=None,
    ):
        """Initialize memory CRUD.

        Args:
            encryption_manager: Optional custom encryption manager
            weaviate_client: Optional custom Weaviate client
            ollama_client: Optional custom Ollama client (fallback)
            openai_embeddings: Optional custom OpenAI embeddings client
            crs_engine: Optional custom CRS engine
            privacy_detector: Optional custom privacy detector
        """
        self.encryption = encryption_manager or get_global_encryption_manager()
        self.weaviate = weaviate_client or WeaviateClient()

        # Ollama is now optional (kept as fallback, but not required)
        try:
            self.ollama = ollama_client or get_global_ollama_client()
        except (ConnectionError, ValueError) as e:
            print(f"[MemoryCRUD] Ollama not available: {e}")
            self.ollama = None  # Will use OpenAI only

        self.openai_embeddings = openai_embeddings or OpenAIEmbeddings()
        self.crs = crs_engine or SimpleCRS()
        self.privacy = privacy_detector or get_privacy_detector()

        # Ensure Weaviate collection exists
        self.weaviate.setup_acms_collection()

    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA256 hash of content for deduplication.

        Args:
            content: Memory content

        Returns:
            str: SHA256 hash (64 characters)
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    def _is_qa_pollution(self, content: str) -> bool:
        """Detect Q&A format pollution in memory content.

        PHASE A (Emergency Triage): Filter out Q&A pairs from memory search
        to immediately improve insight quality.

        Detects patterns like:
        - "Q: ... A: ..." format (from ask endpoint pollution)
        - "User: ... Assistant: ..." format (conversation pollution)
        - "Query: ... Response: ..." format (query pollution)

        Args:
            content: Memory content to check

        Returns:
            bool: True if content appears to be Q&A pollution
        """
        if not content:
            return False

        # Patterns that indicate Q&A pollution
        qa_patterns = [
            r'^Q:\s*.+\n+A:\s*.+',  # "Q: ... A: ..." format
            r'^User:\s*.+\n+Assistant:\s*.+',  # Conversation format
            r'^Query:\s*.+\n+Response:\s*.+',  # Query format
            r'^Question:\s*.+\n+Answer:\s*.+',  # Question/Answer format
        ]

        # Check if content matches any Q&A pattern
        for pattern in qa_patterns:
            if re.search(pattern, content, re.IGNORECASE | re.DOTALL):
                return True

        return False

    async def create_memory(
        self,
        user_id: str,
        content: str,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
        phase: Optional[str] = None,
        tier: str = "SHORT",
        privacy_level: Optional[str] = None,
        auto_detect_privacy: bool = True,
        checkpoint: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Create a new memory (full storage pipeline).

        Pipeline:
        1. Hash content (deduplication check)
        2. Detect/validate privacy level
        3. Encrypt content (XChaCha20-Poly1305)
        4. Generate embedding (Ollama 384-dim)
        5. Store in PostgreSQL
        6. Store vector in Weaviate
        7. Log to audit

        Args:
            user_id: User UUID
            content: Memory content (plaintext)
            tags: Optional tags
            source: Optional source (chatgpt, claude, gemini, etc.)
            phase: Optional phase/context
            tier: Memory tier (SHORT/MID/LONG)
            privacy_level: Privacy level (PUBLIC/INTERNAL/CONFIDENTIAL/LOCAL_ONLY)
                          If None and auto_detect_privacy=True, will auto-detect
            auto_detect_privacy: If True, auto-detect privacy from content/tags
            checkpoint: Optional checkpoint number
            metadata: Optional additional metadata

        Returns:
            str: Memory UUID, or None if duplicate detected
        """
        # Compute content hash
        content_hash = self._compute_content_hash(content)

        # Determine privacy level
        if privacy_level is None and auto_detect_privacy:
            privacy_level = self.privacy.detect_privacy_level(content, tags)
        elif privacy_level is None:
            privacy_level = "INTERNAL"  # Safe default

        # Validate privacy level
        if not self.privacy.validate_privacy_level(privacy_level):
            raise ValueError(f"Invalid privacy level: {privacy_level}")

        async with get_session() as session:
            # Check for duplicate
            stmt = select(MemoryItem).where(
                MemoryItem.user_id == UUID(user_id),
                MemoryItem.content_hash == content_hash,
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Duplicate found
                await self._log_audit(
                    session,
                    user_id=user_id,
                    action="create_memory_duplicate",
                    resource_type="memory",
                    resource_id=str(existing.memory_id),
                    status="skipped",
                )
                return None

            # Encrypt content
            encrypted_content = self.encryption.encrypt_to_base64(content)

            # Generate embedding (OpenAI 1536d - Dec 2025)
            embedding_start = time.time()
            embedding = self.openai_embeddings.generate_embedding(content)
            embedding_latency = (time.time() - embedding_start) * 1000

            # Store vector in Weaviate (ACMS_Raw_v1 unified collection - Dec 2025)
            vector_data = {
                "content": content,
                "content_hash": content_hash,
                "user_id": user_id,
                "source_type": "memory_item",
                "source_id": str(uuid4()),  # Temporary, will update with actual
                "agent": source or "user",
                "privacy_level": privacy_level,
                "tags": tags or [],
                "cost_usd": 0.0,
                "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
            embedding_vector_id = self.weaviate.insert_vector(
                collection="ACMS_Raw_v1",
                vector=embedding,
                data=vector_data,
            )

            # Prepare metadata (include source if provided)
            final_metadata = metadata.copy() if metadata else {}
            if source:
                final_metadata["source"] = source

            # Create memory record
            memory = MemoryItem(
                memory_id=uuid4(),
                user_id=UUID(user_id),
                content=content,
                content_hash=content_hash,
                encrypted_content=encrypted_content,
                embedding_vector_id=embedding_vector_id,
                tier=tier,
                phase=phase,
                tags=tags or [],
                privacy_level=privacy_level,
                checkpoint=checkpoint,
                metadata_json=final_metadata,
            )

            session.add(memory)
            await session.flush()

            # Update Weaviate with actual source_id
            self.weaviate.update_vector(
                collection="ACMS_Raw_v1",
                uuid=embedding_vector_id,
                data={"source_id": str(memory.memory_id)},
            )

            # Log audit (legacy)
            await self._log_audit(
                session,
                user_id=user_id,
                action="create_memory",
                resource_type="memory",
                resource_id=str(memory.memory_id),
                status="success",
            )

            # ──────────────────────────────────────────────────────────
            # AUDIT: Log memory creation (TRANSFORM) - Phase 0 Data Flow
            # ──────────────────────────────────────────────────────────
            try:
                audit = get_audit_logger()

                # Map privacy level string to DataClassification
                data_class_map = {
                    "PUBLIC": DataClassification.PUBLIC,
                    "INTERNAL": DataClassification.INTERNAL,
                    "CONFIDENTIAL": DataClassification.CONFIDENTIAL,
                    "LOCAL_ONLY": DataClassification.LOCAL_ONLY,
                }
                data_classification = data_class_map.get(
                    privacy_level.upper() if privacy_level else "INTERNAL",
                    DataClassification.INTERNAL
                )

                await audit.log_transform(
                    source="memory",
                    operation="create",
                    destination="weaviate",
                    item_count=1,
                    data_classification=data_classification,
                    metadata={
                        "memory_id": str(memory.memory_id),
                        "tier": tier,
                        "source": source,
                        "content_length": len(content),
                        "has_embedding": embedding_vector_id is not None,
                        "embedding_latency_ms": round(embedding_latency, 2),
                        "user_id": user_id
                    }
                )
            except Exception as audit_error:
                # Don't fail memory creation if audit logging fails
                pass  # Silent fail - memory creation is more important

            await session.commit()
            return str(memory.memory_id)

    async def get_memory(
        self,
        memory_id: str,
        decrypt: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Get memory by ID.

        Args:
            memory_id: Memory UUID
            decrypt: Whether to decrypt content

        Returns:
            dict: Memory data, or None if not found
        """
        async with get_session() as session:
            stmt = select(MemoryItem).where(MemoryItem.memory_id == UUID(memory_id))
            result = await session.execute(stmt)
            memory = result.scalar_one_or_none()

            if not memory:
                return None

            # Increment access count
            memory.access_count += 1
            memory.last_accessed = datetime.utcnow()

            # Build response BEFORE commit (while still in session context)
            data = {
                "memory_id": str(memory.memory_id),
                "user_id": str(memory.user_id),
                "content": memory.content,
                "content_hash": memory.content_hash,
                "encrypted_content": memory.encrypted_content if not decrypt else None,
                "embedding_vector_id": memory.embedding_vector_id,
                "tier": memory.tier,
                "phase": memory.phase,
                "tags": memory.tags,
                "privacy_level": memory.privacy_level,
                "crs_score": memory.crs_score,
                "access_count": memory.access_count,
                "last_accessed": memory.last_accessed,
                "created_at": memory.created_at,
                "updated_at": memory.updated_at,
                "checkpoint": memory.checkpoint,
                "metadata": memory.metadata_json,
            }

            # Decrypt if requested
            if decrypt and memory.encrypted_content:
                try:
                    decrypted = self.encryption.decrypt_from_base64(memory.encrypted_content)
                    data["decrypted_content"] = decrypted
                except Exception as e:
                    data["decryption_error"] = str(e)

            await session.commit()
            return data

    async def update_memory(
        self,
        memory_id: str,
        content: Optional[str] = None,
        tags: Optional[List[str]] = None,
        tier: Optional[str] = None,
        phase: Optional[str] = None,
        privacy_level: Optional[str] = None,
        crs_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update memory fields.

        Args:
            memory_id: Memory UUID
            content: Optional new content (triggers re-encryption & re-embedding)
            tags: Optional new tags
            tier: Optional new tier
            phase: Optional new phase
            privacy_level: Optional new privacy level
            crs_score: Optional new CRS score
            metadata: Optional new metadata

        Returns:
            bool: True if updated, False if not found
        """
        async with get_session() as session:
            stmt = select(MemoryItem).where(MemoryItem.memory_id == UUID(memory_id))
            result = await session.execute(stmt)
            memory = result.scalar_one_or_none()

            if not memory:
                return False

            # Update fields
            if content is not None:
                memory.content = content
                memory.content_hash = self._compute_content_hash(content)
                memory.encrypted_content = self.encryption.encrypt_to_base64(content)

                # Re-generate embedding (OpenAI 1536d)
                embedding = self.openai_embeddings.generate_embedding(content)

                # Update Weaviate
                self.weaviate.update_vector(
                    collection="ACMS_Raw_v1",
                    uuid=memory.embedding_vector_id,
                    vector=embedding,
                    data={"content": content},
                )

            if tags is not None:
                memory.tags = tags
                self.weaviate.update_vector(
                    collection="ACMS_Raw_v1",
                    uuid=memory.embedding_vector_id,
                    data={"tags": tags},
                )

            if tier is not None:
                memory.tier = tier
                # Note: ACMS_Raw_v1 doesn't have tier field, skip update

            if phase is not None:
                memory.phase = phase

            if privacy_level is not None:
                # Validate privacy level
                if not self.privacy.validate_privacy_level(privacy_level):
                    raise ValueError(f"Invalid privacy level: {privacy_level}")
                memory.privacy_level = privacy_level
                self.weaviate.update_vector(
                    collection="ACMS_Raw_v1",
                    uuid=memory.embedding_vector_id,
                    data={"privacy_level": privacy_level},
                )

            if crs_score is not None:
                memory.crs_score = crs_score

            if metadata is not None:
                memory.metadata_json = metadata

            memory.updated_at = datetime.utcnow()

            # Log audit
            await self._log_audit(
                session,
                user_id=str(memory.user_id),
                action="update_memory",
                resource_type="memory",
                resource_id=memory_id,
                status="success",
            )

            await session.commit()
            return True

    async def delete_memory(self, memory_id: str) -> bool:
        """Delete memory from PostgreSQL and Weaviate.

        Args:
            memory_id: Memory UUID

        Returns:
            bool: True if deleted, False if not found
        """
        async with get_session() as session:
            stmt = select(MemoryItem).where(MemoryItem.memory_id == UUID(memory_id))
            result = await session.execute(stmt)
            memory = result.scalar_one_or_none()

            if not memory:
                return False

            # Delete from Weaviate
            if memory.embedding_vector_id:
                self.weaviate.delete_vector(
                    collection="ACMS_Raw_v1",
                    uuid=memory.embedding_vector_id,
                )

            # Log audit
            await self._log_audit(
                session,
                user_id=str(memory.user_id),
                action="delete_memory",
                resource_type="memory",
                resource_id=memory_id,
                status="success",
            )

            # Delete from PostgreSQL
            await session.delete(memory)
            await session.commit()
            return True

    async def list_memories(
        self,
        user_id: Optional[str] = None,
        tag: Optional[str] = None,
        phase: Optional[str] = None,
        tier: Optional[str] = None,
        privacy_level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        calculate_crs: bool = False,
    ) -> List[Dict[str, Any]]:
        """List memories with filters and optional CRS calculation.

        Args:
            user_id: Optional user filter
            tag: Optional tag filter
            phase: Optional phase filter
            tier: Optional tier filter
            privacy_level: Optional privacy level filter
            limit: Max results
            offset: Pagination offset
            calculate_crs: If True, recalculate CRS scores for all memories

        Returns:
            List[dict]: Memory records
        """
        async with get_session() as session:
            stmt = select(MemoryItem)

            if user_id:
                stmt = stmt.where(MemoryItem.user_id == UUID(user_id))
            if tag:
                stmt = stmt.where(MemoryItem.tags.contains([tag]))
            if phase:
                stmt = stmt.where(MemoryItem.phase == phase)
            if tier:
                stmt = stmt.where(MemoryItem.tier == tier)
            if privacy_level:
                stmt = stmt.where(MemoryItem.privacy_level == privacy_level)

            stmt = stmt.order_by(MemoryItem.created_at.desc())
            stmt = stmt.limit(limit).offset(offset)

            result = await session.execute(stmt)
            memories = result.scalars().all()

            # Optionally recalculate CRS scores
            if calculate_crs:
                current_time = datetime.utcnow()
                for m in memories:
                    # Use stored distance or default semantic similarity
                    semantic_similarity = 0.8  # Default for list view (no query)
                    m.crs_score = self.crs.calculate_score(
                        semantic_similarity=semantic_similarity,
                        created_at=m.created_at,
                        tier=m.tier,
                        now=current_time
                    )
                await session.commit()

            return [
                {
                    "memory_id": str(m.memory_id),
                    "user_id": str(m.user_id),
                    "content": m.content[:200] + "..." if len(m.content) > 200 else m.content,
                    "tier": m.tier,
                    "phase": m.phase,
                    "tags": m.tags,
                    "privacy_level": m.privacy_level,
                    "crs_score": round(m.crs_score, 4) if m.crs_score else 0.0,
                    "access_count": m.access_count,
                    "created_at": m.created_at,
                }
                for m in memories
            ]

    async def retrieve_memories(
        self,
        user_id: str,
        limit: int = 10,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve memories (simplified wrapper around list_memories).

        Used by Gateway context assembler for simple memory retrieval.

        Args:
            user_id: User UUID
            limit: Max results
            tags: Optional tags filter (list of tags)
            source: Optional source filter (chatgpt, claude, gemini, etc.)

        Returns:
            List[dict]: Memory records

        Example:
            memories = await crud.retrieve_memories(
                user_id="uuid",
                limit=15,
                source="chatgpt"
            )
        """
        # If source filter is provided, we need to filter by metadata
        if source:
            # Get all memories (unfiltered) and filter in Python
            all_memories = await self.list_memories(
                user_id=user_id,
                limit=limit * 2,  # Get more to account for filtering
            )

            # Filter by source in metadata
            filtered = [
                m for m in all_memories
                if m.get("metadata", {}).get("source") == source
            ]

            return filtered[:limit]

        # If tags filter is provided, pass it to list_memories
        if tags:
            # list_memories accepts single tag, so if multiple tags, we get all and filter
            all_memories = await self.list_memories(
                user_id=user_id,
                limit=limit * 2,
            )

            # Filter by tags
            filtered = [
                m for m in all_memories
                if any(tag in m.get("tags", []) for tag in tags)
            ]

            return filtered[:limit]

        # Simple case: no filters, just pass through to list_memories
        return await self.list_memories(
            user_id=user_id,
            limit=limit,
        )

    async def search_memories(
        self,
        query: str,
        user_id: Optional[str] = None,
        limit: int = 10,
        privacy_filter: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Semantic search for memories with CRS scoring and privacy filtering.

        Args:
            query: Search query
            user_id: Optional user filter
            limit: Max results
            privacy_filter: Optional list of privacy levels to include
                           (e.g., ["PUBLIC", "INTERNAL", "CONFIDENTIAL"])
                           If None, includes all levels

        Returns:
            List[dict]: Search results with CRS scores and distances
        """
        # Generate query embedding (OpenAI 1536d - upgraded Dec 2025)
        query_embedding = self.openai_embeddings.generate_embedding(query)

        # Search Weaviate unified collection (get more results for filtering)
        search_limit = limit * 3 if privacy_filter else limit * 2
        results = self.weaviate.semantic_search(
            collection="ACMS_Raw_v1",  # Unified collection (101K objects)
            query_vector=query_embedding,
            limit=search_limit,
        )

        # Filter by user if specified
        if user_id:
            results = [r for r in results if r["properties"].get("user_id") == user_id]

        # Filter by privacy level if specified
        if privacy_filter:
            results = [
                r for r in results
                if r["properties"].get("privacy_level") in privacy_filter
            ]

        # PHASE A: Filter out Q&A pollution to improve insight quality
        # This is a temporary fix until Week 6 dual vector DB is implemented
        qa_filtered = []
        qa_pollution_count = 0
        for r in results:
            content = r["properties"].get("content", "")
            if self._is_qa_pollution(content):
                qa_pollution_count += 1
            else:
                qa_filtered.append(r)

        # Log filtering stats for monitoring
        if qa_pollution_count > 0:
            print(f"[MemoryCRUD] Filtered {qa_pollution_count} Q&A polluted memories from search results")

        results = qa_filtered

        # Limit results
        results = results[:limit]

        # Enrich with PostgreSQL data and calculate CRS
        enriched = []
        current_time = datetime.utcnow()

        async with get_session() as session:
            for result in results:
                # New schema uses source_id (was memory_id in old schema)
                source_id = result["properties"].get("source_id") or result["properties"].get("memory_id")
                if not source_id:
                    continue

                # Try to look up in PostgreSQL for additional metadata
                try:
                    stmt = select(MemoryItem).where(MemoryItem.memory_id == UUID(source_id))
                    db_result = await session.execute(stmt)
                    memory = db_result.scalar_one_or_none()
                except (ValueError, TypeError):
                    # Invalid UUID (might be query_history) - use vector result directly
                    memory = None

                if memory:
                    # Calculate CRS score
                    semantic_similarity = 1.0 - result["distance"]  # Convert distance to similarity
                    crs_score = self.crs.calculate_score(
                        semantic_similarity=semantic_similarity,
                        created_at=memory.created_at,
                        tier=memory.tier,
                        now=current_time
                    )

                    # Update memory with new CRS score
                    memory.crs_score = crs_score

                    enriched.append({
                        "memory_id": str(memory.memory_id),
                        "content": memory.content,
                        "tier": memory.tier,
                        "phase": memory.phase,
                        "tags": memory.tags,
                        "privacy_level": memory.privacy_level,
                        "crs_score": round(crs_score, 4),
                        "distance": result["distance"],
                        "similarity": round(semantic_similarity, 4),  # FIX: Add similarity field for orchestrator
                        "created_at": memory.created_at,
                    })
                else:
                    # Fallback for query_history items (no PostgreSQL record)
                    # Use vector result properties directly
                    props = result["properties"]
                    semantic_similarity = 1.0 - result["distance"]
                    enriched.append({
                        "memory_id": source_id,
                        "content": props.get("content", ""),
                        "tier": "CORE",  # Default tier for query_history
                        "phase": None,
                        "tags": props.get("tags", []),
                        "privacy_level": props.get("privacy_level", "PUBLIC"),
                        "crs_score": round(semantic_similarity, 4),  # Use similarity as CRS for queries
                        "distance": result["distance"],
                        "similarity": round(semantic_similarity, 4),
                        "created_at": props.get("created_at"),
                        "source_type": props.get("source_type", "unknown"),
                    })

            # Commit CRS score updates (only for memory items)
            await session.commit()

        # Sort by CRS score (highest first)
        enriched.sort(key=lambda x: x["crs_score"], reverse=True)

        return enriched

    async def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit logs.

        Args:
            user_id: Optional user filter
            action: Optional action filter
            limit: Max results

        Returns:
            List[dict]: Audit log records
        """
        async with get_session() as session:
            stmt = select(AuditLog)

            if user_id:
                stmt = stmt.where(AuditLog.user_id == UUID(user_id))
            if action:
                stmt = stmt.where(AuditLog.action == action)

            stmt = stmt.order_by(AuditLog.timestamp.desc()).limit(limit)

            result = await session.execute(stmt)
            logs = result.scalars().all()

            return [
                {
                    "audit_id": str(log.audit_id),
                    "user_id": str(log.user_id) if log.user_id else None,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "status": log.status,
                    "timestamp": log.timestamp,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                }
                for log in logs
            ]

    async def _log_audit(
        self,
        session: AsyncSession,
        user_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        status: str,
        error_message: Optional[str] = None,
    ):
        """Log an audit entry.

        Args:
            session: Database session
            user_id: User UUID
            action: Action performed
            resource_type: Resource type
            resource_id: Resource ID
            status: Status (success/failure/skipped)
            error_message: Optional error message
        """
        audit = AuditLog(
            audit_id=uuid4(),
            user_id=UUID(user_id),
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status=status,
            error_message=error_message,
            timestamp=datetime.utcnow(),
        )
        session.add(audit)


if __name__ == "__main__":
    import asyncio

    async def test():
        print("Testing MemoryCRUD...")

        crud = MemoryCRUD()

        # Test create
        user_id = str(uuid4())
        memory_id = await crud.create_memory(
            user_id=user_id,
            content="This is a test memory for CRUD operations",
            tags=["test", "crud"],
            phase="test",
        )
        print(f"✅ Created memory: {memory_id}")

        # Test get
        memory = await crud.get_memory(memory_id)
        print(f"✅ Retrieved memory: {memory['content'][:50]}...")

        # Test update
        updated = await crud.update_memory(
            memory_id=memory_id,
            tags=["test", "crud", "updated"],
            crs_score=0.85,
        )
        print(f"✅ Updated memory: {updated}")

        # Test search
        results = await crud.search_memories(
            query="test CRUD operations",
            user_id=user_id,
            limit=5,
        )
        print(f"✅ Search found {len(results)} results")

        # Test list
        memories = await crud.list_memories(user_id=user_id)
        print(f"✅ Listed {len(memories)} memories")

        # Test audit logs
        logs = await crud.get_audit_logs(user_id=user_id)
        print(f"✅ Retrieved {len(logs)} audit logs")

        # Test delete
        deleted = await crud.delete_memory(memory_id)
        print(f"✅ Deleted memory: {deleted}")

        print("\n✅ All MemoryCRUD tests passed!")

    asyncio.run(test())
