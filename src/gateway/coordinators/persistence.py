"""Persistence Coordinator - Metrics, memory writing, and caching.

Responsibilities:
1. Save query history and metrics
2. Extract facts from Q&A pairs
3. Apply quality gate for memory storage
4. Manage cache entries with TTL
5. Handle feedback/rating updates

Part of Sprint 2 Architecture & Resilience (Days 6-7).
"""

import logging
import hashlib
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

from src.gateway.tracing import get_trace_id

logger = logging.getLogger(__name__)


class QualityTier(Enum):
    """Quality tiers for memory storage."""
    RAW = "raw"           # All Q&A pairs (with TTL)
    ENRICHED = "enriched"  # Quality > 0.8
    KNOWLEDGE = "knowledge"  # Extracted facts + quality > 0.85


@dataclass
class QualityScore:
    """Quality assessment for a response."""
    overall: float  # 0.0 - 1.0
    relevance: float
    completeness: float
    accuracy: float
    source_quality: float
    tier: QualityTier

    @classmethod
    def assess(cls, answer: str, sources: List[Dict], question: str) -> "QualityScore":
        """Assess quality of an answer."""
        # Simple heuristic scoring
        relevance = min(1.0, len(answer) / 500) if answer else 0.0
        completeness = 0.8 if len(answer) > 100 else 0.5
        source_quality = min(1.0, len(sources) / 3) if sources else 0.5
        accuracy = 0.7  # Default, would need LLM evaluation for real accuracy

        overall = (relevance + completeness + accuracy + source_quality) / 4

        # Determine tier
        if overall >= 0.85:
            tier = QualityTier.KNOWLEDGE
        elif overall >= 0.8:
            tier = QualityTier.ENRICHED
        else:
            tier = QualityTier.RAW

        return cls(
            overall=overall,
            relevance=relevance,
            completeness=completeness,
            accuracy=accuracy,
            source_quality=source_quality,
            tier=tier
        )


@dataclass
class PersistenceResult:
    """Result of persistence operations."""
    query_history_id: Optional[str] = None
    memory_id: Optional[str] = None
    cache_key: Optional[str] = None
    quality_score: Optional[QualityScore] = None
    facts_extracted: int = 0
    saved_to_raw: bool = False
    saved_to_enriched: bool = False
    saved_to_knowledge: bool = False
    trace_id: str = ""

    def to_dict(self) -> dict:
        return {
            "query_history_id": self.query_history_id,
            "memory_id": self.memory_id,
            "cache_key": self.cache_key,
            "quality_score": self.quality_score.overall if self.quality_score else None,
            "quality_tier": self.quality_score.tier.value if self.quality_score else None,
            "facts_extracted": self.facts_extracted,
            "saved_to_raw": self.saved_to_raw,
            "saved_to_enriched": self.saved_to_enriched,
            "saved_to_knowledge": self.saved_to_knowledge,
            "trace_id": self.trace_id
        }


class PersistenceCoordinator:
    """Coordinates all persistence operations.

    Handles:
    - Query history logging
    - Quality assessment
    - Tiered memory storage (raw, enriched, knowledge)
    - Fact extraction
    - Cache management

    Usage:
        coordinator = PersistenceCoordinator(
            query_history_crud=...,
            memory_crud=...,
            fact_extractor=...,
            quality_gate=...
        )
        result = await coordinator.persist(
            question=question,
            answer=answer,
            sources=sources,
            user_id=user_id,
            trace_id=trace_id
        )
    """

    def __init__(
        self,
        query_history_crud=None,
        memory_crud=None,
        fact_extractor=None,
        quality_gate=None,
        enable_caching: bool = False,  # Disabled by default (Nov 2025)
        enable_facts: bool = True
    ):
        """Initialize persistence coordinator.

        Args:
            query_history_crud: Query history storage
            memory_crud: Memory storage
            fact_extractor: Fact extraction service
            quality_gate: Quality assessment gate
            enable_caching: Whether to cache responses
            enable_facts: Whether to extract facts
        """
        self.query_history_crud = query_history_crud
        self.memory_crud = memory_crud
        self.fact_extractor = fact_extractor
        self.quality_gate = quality_gate
        self.enable_caching = enable_caching
        self.enable_facts = enable_facts

    async def persist(
        self,
        question: str,
        answer: str,
        sources: List[Dict[str, Any]],
        user_id: str,
        tenant_id: str,
        agent_used: str,
        model_version: str,
        conversation_id: Optional[str] = None,
        from_cache: bool = False,
        response_time_ms: Optional[int] = None
    ) -> PersistenceResult:
        """Persist query results.

        Args:
            question: User question
            answer: LLM response
            sources: Sources used
            user_id: User identifier
            tenant_id: Tenant identifier
            agent_used: Agent that generated response
            model_version: Model version used
            conversation_id: Optional conversation ID
            from_cache: Whether response was from cache
            response_time_ms: Response time in milliseconds

        Returns:
            PersistenceResult with persistence details
        """
        trace_id = get_trace_id()
        result = PersistenceResult(trace_id=trace_id)

        # Step 1: Save to query history (always)
        result.query_history_id = await self._save_query_history(
            question=question,
            answer=answer,
            user_id=user_id,
            agent_used=agent_used,
            from_cache=from_cache,
            response_time_ms=response_time_ms,
            conversation_id=conversation_id
        )

        # Step 2: Assess quality
        result.quality_score = QualityScore.assess(answer, sources, question)
        logger.info(
            f"[{trace_id}] Quality: {result.quality_score.overall:.2f} "
            f"({result.quality_score.tier.value})"
        )

        # Step 3: Save to appropriate tier based on quality
        if not from_cache:  # Don't re-save cached responses
            await self._save_to_memory_tiers(
                question=question,
                answer=answer,
                sources=sources,
                user_id=user_id,
                tenant_id=tenant_id,
                quality=result.quality_score,
                agent_used=agent_used,
                model_version=model_version,
                result=result
            )

        # Step 4: Extract facts if high quality
        if self.enable_facts and result.quality_score.tier == QualityTier.KNOWLEDGE:
            result.facts_extracted = await self._extract_and_save_facts(
                question=question,
                answer=answer,
                user_id=user_id,
                tenant_id=tenant_id
            )

        return result

    async def _save_query_history(
        self,
        question: str,
        answer: str,
        user_id: str,
        agent_used: str,
        from_cache: bool,
        response_time_ms: Optional[int],
        conversation_id: Optional[str]
    ) -> Optional[str]:
        """Save to query history."""
        if not self.query_history_crud:
            return None

        try:
            entry_id = await self.query_history_crud.save(
                query=question,
                response=answer,
                user_id=user_id,
                agent=agent_used,
                from_cache=from_cache,
                response_time_ms=response_time_ms,
                conversation_id=conversation_id
            )
            logger.debug(f"[{get_trace_id()}] Saved query history: {entry_id}")
            return entry_id
        except Exception as e:
            logger.error(f"[{get_trace_id()}] Failed to save query history: {e}")
            return None

    async def _save_to_memory_tiers(
        self,
        question: str,
        answer: str,
        sources: List[Dict],
        user_id: str,
        tenant_id: str,
        quality: QualityScore,
        agent_used: str,
        model_version: str,
        result: PersistenceResult
    ) -> None:
        """Save to appropriate memory tiers based on quality."""
        if not self.memory_crud:
            return

        # Generate idempotency key
        idempotency_key = self._make_idempotency_key(
            question, answer, tenant_id, model_version
        )

        # RAW tier: Save all Q&A pairs
        try:
            raw_id = await self._save_to_raw(
                question=question,
                answer=answer,
                user_id=user_id,
                tenant_id=tenant_id,
                idempotency_key=idempotency_key,
                quality_score=quality.overall
            )
            result.saved_to_raw = True
            result.memory_id = raw_id
        except Exception as e:
            logger.error(f"[{get_trace_id()}] Failed to save to raw: {e}")

        # ENRICHED tier: Quality > 0.8
        if quality.tier in [QualityTier.ENRICHED, QualityTier.KNOWLEDGE]:
            try:
                await self._save_to_enriched(
                    question=question,
                    answer=answer,
                    user_id=user_id,
                    tenant_id=tenant_id,
                    idempotency_key=idempotency_key,
                    quality_score=quality.overall,
                    agent_used=agent_used
                )
                result.saved_to_enriched = True
            except Exception as e:
                logger.error(f"[{get_trace_id()}] Failed to save to enriched: {e}")

    async def _save_to_raw(
        self,
        question: str,
        answer: str,
        user_id: str,
        tenant_id: str,
        idempotency_key: str,
        quality_score: float
    ) -> Optional[str]:
        """Save to raw tier (ACMS_Raw_v1)."""
        # Implementation would save to Weaviate raw collection
        logger.debug(f"[{get_trace_id()}] Would save to ACMS_Raw_v1")
        return idempotency_key[:16]

    async def _save_to_enriched(
        self,
        question: str,
        answer: str,
        user_id: str,
        tenant_id: str,
        idempotency_key: str,
        quality_score: float,
        agent_used: str
    ) -> Optional[str]:
        """Save to enriched tier (ACMS_Enriched_v1)."""
        # Implementation would save to Weaviate enriched collection
        logger.debug(f"[{get_trace_id()}] Would save to ACMS_Enriched_v1")
        return idempotency_key[:16]

    async def _extract_and_save_facts(
        self,
        question: str,
        answer: str,
        user_id: str,
        tenant_id: str
    ) -> int:
        """Extract facts and save to knowledge tier."""
        if not self.fact_extractor:
            return 0

        try:
            facts = await self.fact_extractor.extract(question, answer)
            logger.info(f"[{get_trace_id()}] Extracted {len(facts)} facts")
            # Would save facts to ACMS_Knowledge_v1
            return len(facts)
        except Exception as e:
            logger.error(f"[{get_trace_id()}] Fact extraction failed: {e}")
            return 0

    def _make_idempotency_key(
        self,
        question: str,
        answer: str,
        tenant_id: str,
        model_version: str
    ) -> str:
        """Create deterministic key to prevent duplicate writes."""
        content = f"{question}|{answer}|{tenant_id}|{model_version}"
        return hashlib.sha256(content.encode()).hexdigest()

    async def update_feedback(
        self,
        query_history_id: str,
        rating: int,
        feedback_text: Optional[str] = None
    ) -> bool:
        """Update feedback for a query.

        Args:
            query_history_id: Query history entry ID
            rating: 1 (thumbs down) or 5 (thumbs up)
            feedback_text: Optional feedback text

        Returns:
            True if update succeeded
        """
        if not self.query_history_crud:
            return False

        try:
            await self.query_history_crud.update_feedback(
                query_id=query_history_id,
                rating=rating,
                feedback_text=feedback_text
            )
            logger.info(f"[{get_trace_id()}] Updated feedback for {query_history_id}")
            return True
        except Exception as e:
            logger.error(f"[{get_trace_id()}] Failed to update feedback: {e}")
            return False

    def get_cache_metadata(
        self,
        question: str,
        model_version: str,
        prompt_version: str
    ) -> Dict[str, Any]:
        """Get cache metadata for a response.

        Cache entries must include this metadata for invalidation.
        """
        return {
            "embedding_model": "text-embedding-3-small",
            "prompt_version": prompt_version,
            "llm_model": model_version,
            "created_at": datetime.utcnow().isoformat(),
            "trace_id": get_trace_id()
        }
