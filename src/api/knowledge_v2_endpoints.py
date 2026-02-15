"""Knowledge V2 API Endpoints.

Sprint 3: Knowledge Consolidation for UX Improvements

REST API for consolidated knowledge management.
"""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.storage.database import get_db_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/knowledge", tags=["knowledge-v2"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class KnowledgeItem(BaseModel):
    """Consolidated knowledge item."""
    knowledge_id: str
    canonical_content: str
    knowledge_type: Optional[str] = None
    domain_path: Optional[str] = None
    effective_confidence: float
    base_confidence: float
    source_count: int
    source_boost: float
    verification_boost: float
    is_verified: bool
    is_active: bool
    needs_review: bool
    first_derived_at: datetime
    last_confirmed_at: Optional[datetime] = None


class KnowledgeListResponse(BaseModel):
    """Response for knowledge list."""
    items: List[KnowledgeItem]
    total: int
    offset: int
    limit: int


class ProvenanceItem(BaseModel):
    """Source provenance for knowledge."""
    provenance_id: str
    source_type: str
    source_id: str
    source_timestamp: Optional[datetime] = None
    source_preview: Optional[str] = None
    contribution_type: str
    confidence_at_extraction: Optional[float] = None
    created_at: datetime


class KnowledgeDetailResponse(BaseModel):
    """Detailed knowledge response with provenance."""
    knowledge: KnowledgeItem
    provenance: List[ProvenanceItem]


class DomainStats(BaseModel):
    """Domain statistics."""
    domain_id: str
    name: str
    display_name: str
    parent_path: Optional[str] = None
    level: int
    knowledge_count: int
    verified_count: int
    icon: Optional[str] = None
    color: Optional[str] = None


class DomainTreeNode(BaseModel):
    """Domain tree node for hierarchical display."""
    domain: DomainStats
    children: List["DomainTreeNode"] = []


class VerifyRequest(BaseModel):
    """Request to verify knowledge."""
    verified_by: str = Field(default="user")


class UpdateKnowledgeRequest(BaseModel):
    """Request to update knowledge content."""
    canonical_content: Optional[str] = None
    domain_path: Optional[str] = None
    knowledge_type: Optional[str] = None
    needs_review: Optional[bool] = None


class ConfidenceBreakdown(BaseModel):
    """Confidence score breakdown."""
    base_confidence: float
    source_boost: float
    verification_boost: float
    effective_confidence: float
    source_count: int
    is_verified: bool
    indicator_dots: str
    indicator_color: str


# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/", response_model=KnowledgeListResponse)
async def list_knowledge(
    domain: Optional[str] = Query(None, description="Filter by domain path"),
    knowledge_type: Optional[str] = Query(None, description="Filter by type"),
    verified_only: bool = Query(False, description="Only verified items"),
    needs_review: bool = Query(False, description="Only items needing review"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0),
    search: Optional[str] = Query(None, description="Search content"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """List consolidated knowledge items with filtering."""
    pool = await get_db_pool()

    # Build query
    conditions = ["is_active = TRUE"]
    params = []
    param_idx = 1

    if domain:
        conditions.append(f"domain_path LIKE ${param_idx}")
        params.append(f"{domain}%")
        param_idx += 1

    if knowledge_type:
        conditions.append(f"knowledge_type = ${param_idx}")
        params.append(knowledge_type)
        param_idx += 1

    if verified_only:
        conditions.append("is_verified = TRUE")

    if needs_review:
        conditions.append("needs_review = TRUE")

    if min_confidence > 0:
        conditions.append(f"effective_confidence >= ${param_idx}")
        params.append(min_confidence)
        param_idx += 1

    if search:
        conditions.append(f"canonical_content ILIKE ${param_idx}")
        params.append(f"%{search}%")
        param_idx += 1

    where_clause = " AND ".join(conditions)

    async with pool.acquire() as conn:
        # Get total count
        count_query = f"""
            SELECT COUNT(*) FROM consolidated_knowledge
            WHERE {where_clause}
        """
        total = await conn.fetchval(count_query, *params)

        # Get items
        params.extend([limit, offset])
        query = f"""
            SELECT
                knowledge_id, canonical_content, knowledge_type, domain_path,
                effective_confidence, base_confidence, source_count,
                source_boost, verification_boost, is_verified, is_active,
                needs_review, first_derived_at, last_confirmed_at
            FROM consolidated_knowledge
            WHERE {where_clause}
            ORDER BY effective_confidence DESC, source_count DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        rows = await conn.fetch(query, *params)

        items = [
            KnowledgeItem(
                knowledge_id=str(row['knowledge_id']),
                canonical_content=row['canonical_content'],
                knowledge_type=row['knowledge_type'],
                domain_path=row['domain_path'],
                effective_confidence=row['effective_confidence'] or 0.5,
                base_confidence=row['base_confidence'] or 0.5,
                source_count=row['source_count'] or 1,
                source_boost=row['source_boost'] or 0.0,
                verification_boost=row['verification_boost'] or 0.0,
                is_verified=row['is_verified'] or False,
                is_active=row['is_active'],
                needs_review=row['needs_review'] or False,
                first_derived_at=row['first_derived_at'],
                last_confirmed_at=row['last_confirmed_at']
            )
            for row in rows
        ]

        return KnowledgeListResponse(
            items=items,
            total=total,
            offset=offset,
            limit=limit
        )


@router.get("/domains", response_model=List[DomainStats])
async def list_domains():
    """List all knowledge domains with statistics."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                domain_id, name, display_name, parent_path, level,
                knowledge_count, verified_count, icon, color
            FROM knowledge_domains
            WHERE is_active = TRUE
            ORDER BY level, name
        """)

        return [
            DomainStats(
                domain_id=str(row['domain_id']),
                name=row['name'],
                display_name=row['display_name'],
                parent_path=row['parent_path'],
                level=row['level'],
                knowledge_count=row['knowledge_count'] or 0,
                verified_count=row['verified_count'] or 0,
                icon=row['icon'],
                color=row['color']
            )
            for row in rows
        ]


@router.get("/domains/tree", response_model=List[DomainTreeNode])
async def get_domain_tree():
    """Get hierarchical domain tree."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                domain_id, name, display_name, parent_path, level,
                knowledge_count, verified_count, icon, color
            FROM knowledge_domains
            WHERE is_active = TRUE
            ORDER BY level, name
        """)

        # Build domain stats
        domains = {
            row['name']: DomainStats(
                domain_id=str(row['domain_id']),
                name=row['name'],
                display_name=row['display_name'],
                parent_path=row['parent_path'],
                level=row['level'],
                knowledge_count=row['knowledge_count'] or 0,
                verified_count=row['verified_count'] or 0,
                icon=row['icon'],
                color=row['color']
            )
            for row in rows
        }

        # Build tree
        nodes = {name: DomainTreeNode(domain=domain) for name, domain in domains.items()}
        root_nodes = []

        for name, node in nodes.items():
            parent = domains[name].parent_path
            if parent is None:
                root_nodes.append(node)
            elif parent in nodes:
                nodes[parent].children.append(node)

        return root_nodes


@router.get("/{knowledge_id}", response_model=KnowledgeDetailResponse)
async def get_knowledge(knowledge_id: UUID):
    """Get knowledge item with provenance."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        # Get knowledge
        row = await conn.fetchrow("""
            SELECT
                knowledge_id, canonical_content, knowledge_type, domain_path,
                effective_confidence, base_confidence, source_count,
                source_boost, verification_boost, is_verified, is_active,
                needs_review, first_derived_at, last_confirmed_at
            FROM consolidated_knowledge
            WHERE knowledge_id = $1 AND is_active = TRUE
        """, knowledge_id)

        if not row:
            raise HTTPException(status_code=404, detail="Knowledge not found")

        knowledge = KnowledgeItem(
            knowledge_id=str(row['knowledge_id']),
            canonical_content=row['canonical_content'],
            knowledge_type=row['knowledge_type'],
            domain_path=row['domain_path'],
            effective_confidence=row['effective_confidence'] or 0.5,
            base_confidence=row['base_confidence'] or 0.5,
            source_count=row['source_count'] or 1,
            source_boost=row['source_boost'] or 0.0,
            verification_boost=row['verification_boost'] or 0.0,
            is_verified=row['is_verified'] or False,
            is_active=row['is_active'],
            needs_review=row['needs_review'] or False,
            first_derived_at=row['first_derived_at'],
            last_confirmed_at=row['last_confirmed_at']
        )

        # Get provenance
        prov_rows = await conn.fetch("""
            SELECT
                provenance_id, source_type, source_id, source_timestamp,
                source_preview, contribution_type, confidence_at_extraction,
                created_at
            FROM knowledge_provenance
            WHERE knowledge_id = $1
            ORDER BY created_at DESC
        """, knowledge_id)

        provenance = [
            ProvenanceItem(
                provenance_id=str(row['provenance_id']),
                source_type=row['source_type'],
                source_id=str(row['source_id']),
                source_timestamp=row['source_timestamp'],
                source_preview=row['source_preview'],
                contribution_type=row['contribution_type'],
                confidence_at_extraction=row['confidence_at_extraction'],
                created_at=row['created_at']
            )
            for row in prov_rows
        ]

        return KnowledgeDetailResponse(knowledge=knowledge, provenance=provenance)


@router.get("/{knowledge_id}/confidence", response_model=ConfidenceBreakdown)
async def get_confidence_breakdown(knowledge_id: UUID):
    """Get detailed confidence breakdown for knowledge item."""
    from src.jobs.knowledge_consolidation import get_confidence_indicator

    pool = await get_db_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT
                base_confidence, source_boost, verification_boost,
                effective_confidence, source_count, is_verified
            FROM consolidated_knowledge
            WHERE knowledge_id = $1 AND is_active = TRUE
        """, knowledge_id)

        if not row:
            raise HTTPException(status_code=404, detail="Knowledge not found")

        dots, color = get_confidence_indicator(row['effective_confidence'] or 0.5)

        return ConfidenceBreakdown(
            base_confidence=row['base_confidence'] or 0.5,
            source_boost=row['source_boost'] or 0.0,
            verification_boost=row['verification_boost'] or 0.0,
            effective_confidence=row['effective_confidence'] or 0.5,
            source_count=row['source_count'] or 1,
            is_verified=row['is_verified'] or False,
            indicator_dots=dots,
            indicator_color=color
        )


@router.post("/{knowledge_id}/verify", response_model=KnowledgeItem)
async def verify_knowledge(knowledge_id: UUID, request: VerifyRequest):
    """Mark knowledge as verified by user."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE consolidated_knowledge
            SET
                is_verified = TRUE,
                verification_boost = 0.25,
                verified_at = NOW(),
                verified_by = $2,
                updated_at = NOW()
            WHERE knowledge_id = $1 AND is_active = TRUE
            RETURNING
                knowledge_id, canonical_content, knowledge_type, domain_path,
                effective_confidence, base_confidence, source_count,
                source_boost, verification_boost, is_verified, is_active,
                needs_review, first_derived_at, last_confirmed_at
        """, knowledge_id, request.verified_by)

        if not row:
            raise HTTPException(status_code=404, detail="Knowledge not found")

        return KnowledgeItem(
            knowledge_id=str(row['knowledge_id']),
            canonical_content=row['canonical_content'],
            knowledge_type=row['knowledge_type'],
            domain_path=row['domain_path'],
            effective_confidence=row['effective_confidence'] or 0.5,
            base_confidence=row['base_confidence'] or 0.5,
            source_count=row['source_count'] or 1,
            source_boost=row['source_boost'] or 0.0,
            verification_boost=row['verification_boost'] or 0.0,
            is_verified=row['is_verified'] or False,
            is_active=row['is_active'],
            needs_review=row['needs_review'] or False,
            first_derived_at=row['first_derived_at'],
            last_confirmed_at=row['last_confirmed_at']
        )


@router.post("/{knowledge_id}/unverify", response_model=KnowledgeItem)
async def unverify_knowledge(knowledge_id: UUID):
    """Remove verification from knowledge item."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE consolidated_knowledge
            SET
                is_verified = FALSE,
                verification_boost = 0.0,
                verified_at = NULL,
                verified_by = NULL,
                updated_at = NOW()
            WHERE knowledge_id = $1 AND is_active = TRUE
            RETURNING
                knowledge_id, canonical_content, knowledge_type, domain_path,
                effective_confidence, base_confidence, source_count,
                source_boost, verification_boost, is_verified, is_active,
                needs_review, first_derived_at, last_confirmed_at
        """, knowledge_id)

        if not row:
            raise HTTPException(status_code=404, detail="Knowledge not found")

        return KnowledgeItem(
            knowledge_id=str(row['knowledge_id']),
            canonical_content=row['canonical_content'],
            knowledge_type=row['knowledge_type'],
            domain_path=row['domain_path'],
            effective_confidence=row['effective_confidence'] or 0.5,
            base_confidence=row['base_confidence'] or 0.5,
            source_count=row['source_count'] or 1,
            source_boost=row['source_boost'] or 0.0,
            verification_boost=row['verification_boost'] or 0.0,
            is_verified=row['is_verified'] or False,
            is_active=row['is_active'],
            needs_review=row['needs_review'] or False,
            first_derived_at=row['first_derived_at'],
            last_confirmed_at=row['last_confirmed_at']
        )


@router.patch("/{knowledge_id}", response_model=KnowledgeItem)
async def update_knowledge(knowledge_id: UUID, request: UpdateKnowledgeRequest):
    """Update knowledge item content or metadata."""
    pool = await get_db_pool()

    # Build update clause
    updates = ["updated_at = NOW()"]
    params = [knowledge_id]
    param_idx = 2

    if request.canonical_content is not None:
        updates.append(f"canonical_content = ${param_idx}")
        params.append(request.canonical_content)
        param_idx += 1

    if request.domain_path is not None:
        updates.append(f"domain_path = ${param_idx}")
        params.append(request.domain_path)
        param_idx += 1

    if request.knowledge_type is not None:
        updates.append(f"knowledge_type = ${param_idx}")
        params.append(request.knowledge_type)
        param_idx += 1

    if request.needs_review is not None:
        updates.append(f"needs_review = ${param_idx}")
        params.append(request.needs_review)
        param_idx += 1

    update_clause = ", ".join(updates)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"""
            UPDATE consolidated_knowledge
            SET {update_clause}
            WHERE knowledge_id = $1 AND is_active = TRUE
            RETURNING
                knowledge_id, canonical_content, knowledge_type, domain_path,
                effective_confidence, base_confidence, source_count,
                source_boost, verification_boost, is_verified, is_active,
                needs_review, first_derived_at, last_confirmed_at
        """, *params)

        if not row:
            raise HTTPException(status_code=404, detail="Knowledge not found")

        return KnowledgeItem(
            knowledge_id=str(row['knowledge_id']),
            canonical_content=row['canonical_content'],
            knowledge_type=row['knowledge_type'],
            domain_path=row['domain_path'],
            effective_confidence=row['effective_confidence'] or 0.5,
            base_confidence=row['base_confidence'] or 0.5,
            source_count=row['source_count'] or 1,
            source_boost=row['source_boost'] or 0.0,
            verification_boost=row['verification_boost'] or 0.0,
            is_verified=row['is_verified'] or False,
            is_active=row['is_active'],
            needs_review=row['needs_review'] or False,
            first_derived_at=row['first_derived_at'],
            last_confirmed_at=row['last_confirmed_at']
        )


@router.delete("/{knowledge_id}")
async def delete_knowledge(knowledge_id: UUID):
    """Soft delete knowledge item."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE consolidated_knowledge
            SET is_active = FALSE, updated_at = NOW()
            WHERE knowledge_id = $1 AND is_active = TRUE
        """, knowledge_id)

        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Knowledge not found")

        return {"status": "deleted", "knowledge_id": str(knowledge_id)}


@router.get("/stats/summary")
async def get_knowledge_stats():
    """Get summary statistics for knowledge base."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        stats = await conn.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE is_verified = TRUE) as verified,
                COUNT(*) FILTER (WHERE needs_review = TRUE) as needs_review,
                AVG(effective_confidence) as avg_confidence,
                AVG(source_count) as avg_sources,
                COUNT(DISTINCT domain_path) as domain_count
            FROM consolidated_knowledge
            WHERE is_active = TRUE
        """)

        # Top domains
        top_domains = await conn.fetch("""
            SELECT domain_path, COUNT(*) as count
            FROM consolidated_knowledge
            WHERE is_active = TRUE AND domain_path IS NOT NULL
            GROUP BY domain_path
            ORDER BY count DESC
            LIMIT 5
        """)

        return {
            "total": stats['total'] or 0,
            "verified": stats['verified'] or 0,
            "needs_review": stats['needs_review'] or 0,
            "avg_confidence": round(stats['avg_confidence'] or 0, 2),
            "avg_sources": round(stats['avg_sources'] or 1, 1),
            "domain_count": stats['domain_count'] or 0,
            "top_domains": [
                {"domain": row['domain_path'], "count": row['count']}
                for row in top_domains
            ]
        }


# Required for Pydantic self-referential model
DomainTreeNode.model_rebuild()
