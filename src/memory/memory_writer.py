"""Memory Writer - Policy-enforced memory storage.

This module enforces the tiered memory storage policy (Dec 2025 - Updated):
1. ACMS_Raw_v1: All Q&A pairs (unified collection, 101K records)
2. ACMS_Knowledge_v2: Structured knowledge with intent, entities, topics, facts

NOTE: Dec 2025 cleanup removed old collections:
- ACMS_Enriched_v1 → merged into ACMS_Raw_v1
- ACMS_Knowledge_v1 → replaced by ACMS_Knowledge_v2

Features:
- Idempotency keys to prevent duplicates
- Quality gate enforcement
- Tiered storage based on quality scores
- Knowledge extraction integration (Claude Sonnet 4)
- Cache metadata for invalidation

Part of Sprint 2 Architecture (Days 8-9).
"""

import logging
import hashlib
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from enum import Enum

from src.gateway.tracing import get_trace_id

logger = logging.getLogger(__name__)


class StorageTier(Enum):
    """Memory storage tiers."""
    RAW = "raw"           # All Q&A pairs
    ENRICHED = "enriched"  # Quality > 0.8
    KNOWLEDGE = "knowledge"  # Extracted facts + quality > 0.85


@dataclass
class QualityScore:
    """Quality assessment for a response."""
    overall: float
    relevance: float
    completeness: float
    accuracy: float
    source_quality: float

    @property
    def tier(self) -> StorageTier:
        """Determine storage tier based on quality."""
        if self.overall >= 0.85:
            return StorageTier.KNOWLEDGE
        elif self.overall >= 0.8:
            return StorageTier.ENRICHED
        return StorageTier.RAW

    @classmethod
    def assess(cls, answer: str, sources: List[Dict], question: str) -> "QualityScore":
        """Assess quality of an answer.

        Args:
            answer: The LLM response
            sources: Sources used for the answer
            question: The original question

        Returns:
            QualityScore with component scores
        """
        # Relevance: Based on answer length (longer = more complete, up to a point)
        answer_len = len(answer) if answer else 0
        relevance = min(1.0, answer_len / 500) if answer else 0.0

        # Completeness: Based on answer structure
        completeness = 0.8 if answer_len > 100 else 0.5

        # Source quality: Based on number of sources
        source_count = len(sources) if sources else 0
        source_quality = min(1.0, source_count / 3) if sources else 0.5

        # Accuracy: Default value (would need LLM evaluation for real accuracy)
        accuracy = 0.7

        # Overall weighted average
        overall = (relevance * 0.25 + completeness * 0.25 +
                   accuracy * 0.25 + source_quality * 0.25)

        return cls(
            overall=overall,
            relevance=relevance,
            completeness=completeness,
            accuracy=accuracy,
            source_quality=source_quality
        )

    def to_dict(self) -> dict:
        return {
            "overall": round(self.overall, 3),
            "relevance": round(self.relevance, 3),
            "completeness": round(self.completeness, 3),
            "accuracy": round(self.accuracy, 3),
            "source_quality": round(self.source_quality, 3),
            "tier": self.tier.value
        }


@dataclass
class WriteResult:
    """Result of a memory write operation."""
    raw_id: Optional[str] = None
    enriched_id: Optional[str] = None
    knowledge_ids: List[str] = field(default_factory=list)
    quality: Optional[QualityScore] = None
    facts_extracted: int = 0
    idempotency_key: str = ""
    was_duplicate: bool = False
    trace_id: str = ""

    def to_dict(self) -> dict:
        return {
            "raw_id": self.raw_id,
            "enriched_id": self.enriched_id,
            "knowledge_ids": self.knowledge_ids,
            "quality": self.quality.to_dict() if self.quality else None,
            "facts_extracted": self.facts_extracted,
            "idempotency_key": self.idempotency_key[:16] if self.idempotency_key else None,
            "was_duplicate": self.was_duplicate,
            "trace_id": self.trace_id
        }


@dataclass
class CacheMetadata:
    """Metadata for cache entries (for invalidation)."""
    embedding_model: str
    prompt_version: str
    llm_model: str
    quality_score: float
    trace_id: str
    created_at: str
    ttl_seconds: int = 86400  # 24 hours default

    def to_dict(self) -> dict:
        return {
            "embedding_model": self.embedding_model,
            "prompt_version": self.prompt_version,
            "llm_model": self.llm_model,
            "quality_score": round(self.quality_score, 3),
            "trace_id": self.trace_id,
            "created_at": self.created_at,
            "ttl_seconds": self.ttl_seconds
        }


class MemoryWriter:
    """Policy-enforced memory writer.

    Implements tiered storage policy:
    - Raw tier: All Q&A pairs (always saved)
    - Enriched tier: Quality > 0.8
    - Knowledge tier: Extracted facts + quality > 0.85

    Features:
    - Idempotency keys prevent duplicate writes
    - Quality gate determines storage tier
    - Fact extraction for knowledge tier
    - Cache metadata for invalidation

    Usage:
        writer = MemoryWriter(
            raw_storage=weaviate_raw,
            enriched_storage=weaviate_enriched,
            knowledge_storage=weaviate_knowledge,
            fact_extractor=fact_extractor
        )
        result = await writer.write(
            question="What is X?",
            answer="X is Y because...",
            sources=[...],
            user_id="user1",
            tenant_id="tenant1",
            model_version="claude-3-sonnet"
        )
    """

    # Quality thresholds
    ENRICHED_THRESHOLD = 0.8
    KNOWLEDGE_THRESHOLD = 0.85

    # TTL settings (seconds)
    RAW_TTL = 7 * 24 * 3600  # 7 days
    ENRICHED_TTL = 30 * 24 * 3600  # 30 days
    KNOWLEDGE_TTL = None  # No expiration for knowledge

    def __init__(
        self,
        raw_storage=None,
        enriched_storage=None,
        knowledge_storage=None,
        fact_extractor=None,
        embedding_model: str = "text-embedding-3-small",
        enable_facts: bool = True,
        enable_enriched: bool = True
    ):
        """Initialize memory writer.

        Args:
            raw_storage: Storage for raw Q&A pairs
            enriched_storage: Storage for enriched entries
            knowledge_storage: Storage for knowledge facts
            fact_extractor: Service for extracting facts
            embedding_model: Embedding model name
            enable_facts: Whether to extract facts
            enable_enriched: Whether to write to enriched tier
        """
        self.raw_storage = raw_storage
        self.enriched_storage = enriched_storage
        self.knowledge_storage = knowledge_storage
        self.fact_extractor = fact_extractor
        self.embedding_model = embedding_model
        self.enable_facts = enable_facts
        self.enable_enriched = enable_enriched

    async def write(
        self,
        question: str,
        answer: str,
        sources: List[Dict[str, Any]],
        user_id: str,
        tenant_id: str,
        model_version: str,
        prompt_version: str = "v1.0",
        agent_used: str = "unknown",
        conversation_id: Optional[str] = None,
        skip_if_cached: bool = True
    ) -> WriteResult:
        """Write Q&A to appropriate memory tiers.

        Args:
            question: The user question
            answer: The LLM answer
            sources: Sources used for the answer
            user_id: User identifier
            tenant_id: Tenant identifier
            model_version: LLM model version
            prompt_version: System prompt version
            agent_used: Agent that generated the answer
            conversation_id: Optional conversation ID
            skip_if_cached: Skip write if response was from cache

        Returns:
            WriteResult with IDs and quality info
        """
        trace_id = get_trace_id()
        result = WriteResult(trace_id=trace_id)

        # Generate idempotency key
        result.idempotency_key = self._make_idempotency_key(
            question, answer, tenant_id, model_version
        )

        # Check for duplicate
        if await self._check_duplicate(result.idempotency_key):
            result.was_duplicate = True
            logger.info(f"[{trace_id}] Duplicate write skipped: {result.idempotency_key[:16]}")
            return result

        # Assess quality
        result.quality = QualityScore.assess(answer, sources, question)
        logger.info(
            f"[{trace_id}] Quality: {result.quality.overall:.2f} "
            f"({result.quality.tier.value})"
        )

        # Build cache metadata
        metadata = CacheMetadata(
            embedding_model=self.embedding_model,
            prompt_version=prompt_version,
            llm_model=model_version,
            quality_score=result.quality.overall,
            trace_id=trace_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            ttl_seconds=self.RAW_TTL
        )

        # Step 1: Always write to RAW tier
        result.raw_id = await self._write_raw(
            question=question,
            answer=answer,
            user_id=user_id,
            tenant_id=tenant_id,
            idempotency_key=result.idempotency_key,
            metadata=metadata,
            agent_used=agent_used
        )

        # Step 2: Write to ENRICHED if quality meets threshold
        if (self.enable_enriched and
            result.quality.tier in [StorageTier.ENRICHED, StorageTier.KNOWLEDGE]):
            metadata.ttl_seconds = self.ENRICHED_TTL
            result.enriched_id = await self._write_enriched(
                question=question,
                answer=answer,
                user_id=user_id,
                tenant_id=tenant_id,
                idempotency_key=result.idempotency_key,
                metadata=metadata,
                agent_used=agent_used,
                quality_score=result.quality.overall
            )

        # Step 3: Extract facts and write to KNOWLEDGE if high quality
        if (self.enable_facts and
            result.quality.tier == StorageTier.KNOWLEDGE):
            facts = await self._extract_facts(question, answer)
            result.facts_extracted = len(facts)

            for fact in facts:
                fact_id = await self._write_knowledge(
                    fact=fact,
                    source_question=question,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    trace_id=trace_id
                )
                if fact_id:
                    result.knowledge_ids.append(fact_id)

        return result

    def _make_idempotency_key(
        self,
        question: str,
        answer: str,
        tenant_id: str,
        model_version: str
    ) -> str:
        """Create deterministic key to prevent duplicate writes.

        Args:
            question: The user question
            answer: The LLM answer
            tenant_id: Tenant identifier
            model_version: Model version

        Returns:
            SHA-256 hash of content
        """
        content = f"{question}|{answer}|{tenant_id}|{model_version}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def _check_duplicate(self, idempotency_key: str) -> bool:
        """Check if entry already exists.

        Args:
            idempotency_key: The idempotency key to check

        Returns:
            True if duplicate exists
        """
        if not self.raw_storage:
            return False

        try:
            # Check if key exists in raw storage
            if hasattr(self.raw_storage, 'exists_by_key'):
                return await self.raw_storage.exists_by_key(idempotency_key)
        except Exception as e:
            logger.warning(f"[{get_trace_id()}] Duplicate check failed: {e}")

        return False

    async def _write_raw(
        self,
        question: str,
        answer: str,
        user_id: str,
        tenant_id: str,
        idempotency_key: str,
        metadata: CacheMetadata,
        agent_used: str
    ) -> Optional[str]:
        """Write to RAW tier (ACMS_Raw_v1)."""
        if not self.raw_storage:
            logger.debug(f"[{get_trace_id()}] Raw storage not configured")
            return None

        try:
            entry_id = await self.raw_storage.save(
                content=f"Q: {question}\nA: {answer}",
                user_id=user_id,
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
                metadata=metadata.to_dict(),
                ttl_seconds=self.RAW_TTL
            )
            logger.debug(f"[{get_trace_id()}] Saved to raw: {entry_id}")
            return entry_id
        except Exception as e:
            logger.error(f"[{get_trace_id()}] Raw write failed: {e}")
            return None

    async def _write_enriched(
        self,
        question: str,
        answer: str,
        user_id: str,
        tenant_id: str,
        idempotency_key: str,
        metadata: CacheMetadata,
        agent_used: str,
        quality_score: float
    ) -> Optional[str]:
        """Write to ENRICHED tier (merged into ACMS_Raw_v1 as of Dec 2025)."""
        if not self.enriched_storage:
            logger.debug(f"[{get_trace_id()}] Enriched storage not configured")
            return None

        try:
            entry_id = await self.enriched_storage.save(
                content=f"Q: {question}\nA: {answer}",
                user_id=user_id,
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
                metadata=metadata.to_dict(),
                quality_score=quality_score,
                agent=agent_used,
                ttl_seconds=self.ENRICHED_TTL
            )
            logger.debug(f"[{get_trace_id()}] Saved to enriched: {entry_id}")
            return entry_id
        except Exception as e:
            logger.error(f"[{get_trace_id()}] Enriched write failed: {e}")
            return None

    async def _extract_facts(
        self,
        question: str,
        answer: str
    ) -> List[Dict[str, Any]]:
        """Extract facts from Q&A pair."""
        if not self.fact_extractor:
            return []

        try:
            facts = await self.fact_extractor.extract(question, answer)
            logger.info(f"[{get_trace_id()}] Extracted {len(facts)} facts")
            return facts
        except Exception as e:
            logger.error(f"[{get_trace_id()}] Fact extraction failed: {e}")
            return []

    async def _write_knowledge(
        self,
        fact: Dict[str, Any],
        source_question: str,
        user_id: str,
        tenant_id: str,
        trace_id: str
    ) -> Optional[str]:
        """Write fact to KNOWLEDGE tier (ACMS_Knowledge_v2 as of Dec 2025)."""
        if not self.knowledge_storage:
            logger.debug(f"[{trace_id}] Knowledge storage not configured")
            return None

        try:
            entry_id = await self.knowledge_storage.save(
                fact=fact.get("content", str(fact)),
                source_question=source_question,
                user_id=user_id,
                tenant_id=tenant_id,
                confidence=fact.get("confidence", 0.85),
                trace_id=trace_id
            )
            logger.debug(f"[{trace_id}] Saved fact to knowledge: {entry_id}")
            return entry_id
        except Exception as e:
            logger.error(f"[{trace_id}] Knowledge write failed: {e}")
            return None

    async def invalidate_by_prompt_version(self, old_version: str) -> int:
        """Invalidate cache entries with old prompt version.

        Args:
            old_version: The prompt version to invalidate

        Returns:
            Number of entries invalidated
        """
        count = 0
        for storage in [self.raw_storage, self.enriched_storage]:
            if storage and hasattr(storage, 'delete_by_metadata'):
                try:
                    deleted = await storage.delete_by_metadata(
                        {"prompt_version": old_version}
                    )
                    count += deleted
                except Exception as e:
                    logger.error(f"[{get_trace_id()}] Invalidation failed: {e}")
        return count

    async def invalidate_by_model(self, old_model: str) -> int:
        """Invalidate cache entries with old LLM model.

        Args:
            old_model: The model version to invalidate

        Returns:
            Number of entries invalidated
        """
        count = 0
        for storage in [self.raw_storage, self.enriched_storage]:
            if storage and hasattr(storage, 'delete_by_metadata'):
                try:
                    deleted = await storage.delete_by_metadata(
                        {"llm_model": old_model}
                    )
                    count += deleted
                except Exception as e:
                    logger.error(f"[{get_trace_id()}] Invalidation failed: {e}")
        return count

    def get_quality_thresholds(self) -> Dict[str, float]:
        """Get current quality thresholds."""
        return {
            "enriched_threshold": self.ENRICHED_THRESHOLD,
            "knowledge_threshold": self.KNOWLEDGE_THRESHOLD
        }

    def get_ttl_settings(self) -> Dict[str, Optional[int]]:
        """Get current TTL settings."""
        return {
            "raw_ttl_seconds": self.RAW_TTL,
            "enriched_ttl_seconds": self.ENRICHED_TTL,
            "knowledge_ttl_seconds": self.KNOWLEDGE_TTL
        }
