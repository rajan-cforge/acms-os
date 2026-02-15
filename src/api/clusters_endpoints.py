"""Memory Clusters API Endpoints for ACMS.

Sprint 2: Memory Clustering for UX Improvements

Endpoints:
- GET /api/v2/clusters - List all clusters
- GET /api/v2/clusters/{cluster_id} - Get cluster details
- GET /api/v2/clusters/{cluster_id}/members - Get cluster members
- PATCH /api/v2/clusters/{cluster_id} - Update cluster
- DELETE /api/v2/clusters/{cluster_id} - Delete cluster
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.storage.database import get_db_pool

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/clusters", tags=["clusters"])


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ClusterSummary(BaseModel):
    """Summary of a memory cluster."""
    cluster_id: str
    canonical_topic: str
    display_name: str
    member_count: int
    first_memory_at: Optional[datetime] = None
    last_memory_at: Optional[datetime] = None
    avg_quality_score: Optional[float] = None


class ClusterDetail(BaseModel):
    """Detailed cluster information."""
    cluster_id: str
    canonical_topic: str
    display_name: str
    description: Optional[str] = None
    member_count: int
    first_memory_at: Optional[datetime] = None
    last_memory_at: Optional[datetime] = None
    avg_quality_score: Optional[float] = None
    centroid_vector_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime


class ClusterMember(BaseModel):
    """A memory belonging to a cluster."""
    memory_id: str
    content: Optional[str] = None
    similarity_score: float
    is_canonical: bool
    added_at: datetime
    created_at: Optional[datetime] = None


class ClustersResponse(BaseModel):
    """Response for listing clusters."""
    clusters: List[ClusterSummary]
    total: int
    limit: int
    offset: int


class ClusterMembersResponse(BaseModel):
    """Response for listing cluster members."""
    cluster_id: str
    members: List[ClusterMember]
    total: int
    limit: int
    offset: int


class ClusterUpdate(BaseModel):
    """Request body for updating a cluster."""
    display_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = Field(None, max_length=500)


class DeleteResponse(BaseModel):
    """Response for delete operations."""
    deleted: bool
    cluster_id: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("", response_model=ClustersResponse)
async def list_clusters(
    user_id: str = Query("default", description="User ID"),
    limit: int = Query(50, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sort_by: str = Query("member_count", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc/desc)")
) -> ClustersResponse:
    """List memory clusters with member counts.

    Returns paginated list of clusters sorted by member count or recency.
    """
    pool = await get_db_pool()

    # Validate sort parameters
    valid_sort_fields = {"member_count", "last_memory_at", "created_at", "display_name"}
    if sort_by not in valid_sort_fields:
        sort_by = "member_count"

    sort_direction = "DESC" if sort_order.lower() == "desc" else "ASC"

    async with pool.acquire() as conn:
        # Get clusters
        clusters = await conn.fetch(f"""
            SELECT
                cluster_id,
                canonical_topic,
                display_name,
                member_count,
                first_memory_at,
                last_memory_at,
                avg_quality_score
            FROM memory_clusters
            WHERE is_active = TRUE
            ORDER BY {sort_by} {sort_direction}
            LIMIT $1 OFFSET $2
        """, limit, offset)

        # Get total count
        total = await conn.fetchval("""
            SELECT COUNT(*) FROM memory_clusters WHERE is_active = TRUE
        """)

    return ClustersResponse(
        clusters=[
            ClusterSummary(
                cluster_id=str(c['cluster_id']),
                canonical_topic=c['canonical_topic'],
                display_name=c['display_name'],
                member_count=c['member_count'],
                first_memory_at=c['first_memory_at'],
                last_memory_at=c['last_memory_at'],
                avg_quality_score=c['avg_quality_score']
            )
            for c in clusters
        ],
        total=total or 0,
        limit=limit,
        offset=offset
    )


@router.get("/{cluster_id}", response_model=ClusterDetail)
async def get_cluster(cluster_id: str) -> ClusterDetail:
    """Get detailed information about a specific cluster.

    Args:
        cluster_id: UUID of the cluster

    Returns:
        Cluster details including member count and metadata

    Raises:
        HTTPException: 404 if cluster not found
    """
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        cluster = await conn.fetchrow("""
            SELECT
                cluster_id,
                canonical_topic,
                display_name,
                description,
                member_count,
                first_memory_at,
                last_memory_at,
                avg_quality_score,
                centroid_vector_id,
                is_active,
                created_at,
                updated_at
            FROM memory_clusters
            WHERE cluster_id = $1
        """, cluster_id)

    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    return ClusterDetail(
        cluster_id=str(cluster['cluster_id']),
        canonical_topic=cluster['canonical_topic'],
        display_name=cluster['display_name'],
        description=cluster['description'],
        member_count=cluster['member_count'],
        first_memory_at=cluster['first_memory_at'],
        last_memory_at=cluster['last_memory_at'],
        avg_quality_score=cluster['avg_quality_score'],
        centroid_vector_id=cluster['centroid_vector_id'],
        is_active=cluster['is_active'],
        created_at=cluster['created_at'],
        updated_at=cluster['updated_at']
    )


@router.get("/{cluster_id}/members", response_model=ClusterMembersResponse)
async def get_cluster_members(
    cluster_id: str,
    limit: int = Query(20, ge=1, le=100, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset")
) -> ClusterMembersResponse:
    """Get memories belonging to a cluster.

    Returns members sorted by similarity score (most representative first).

    Args:
        cluster_id: UUID of the cluster
        limit: Maximum number of members to return
        offset: Pagination offset

    Returns:
        List of cluster members with similarity scores
    """
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        # Verify cluster exists
        cluster_exists = await conn.fetchval("""
            SELECT 1 FROM memory_clusters WHERE cluster_id = $1
        """, cluster_id)

        if not cluster_exists:
            raise HTTPException(status_code=404, detail="Cluster not found")

        # Get members with content preview
        members = await conn.fetch("""
            SELECT
                mcm.memory_id,
                mcm.similarity_score,
                mcm.is_canonical,
                mcm.added_at,
                qh.question || ' ' || COALESCE(qh.answer, '') as content,
                qh.created_at
            FROM memory_cluster_members mcm
            LEFT JOIN query_history qh ON qh.query_id = mcm.memory_id
            WHERE mcm.cluster_id = $1
            ORDER BY mcm.similarity_score DESC, mcm.is_canonical DESC
            LIMIT $2 OFFSET $3
        """, cluster_id, limit, offset)

        # Get total count
        total = await conn.fetchval("""
            SELECT COUNT(*) FROM memory_cluster_members WHERE cluster_id = $1
        """, cluster_id)

    return ClusterMembersResponse(
        cluster_id=cluster_id,
        members=[
            ClusterMember(
                memory_id=str(m['memory_id']),
                content=m['content'][:500] if m['content'] else None,
                similarity_score=m['similarity_score'],
                is_canonical=m['is_canonical'],
                added_at=m['added_at'],
                created_at=m['created_at']
            )
            for m in members
        ],
        total=total or 0,
        limit=limit,
        offset=offset
    )


@router.patch("/{cluster_id}", response_model=ClusterDetail)
async def update_cluster(
    cluster_id: str,
    update: ClusterUpdate = None,
    display_name: Optional[str] = Query(None, max_length=100),
    description: Optional[str] = Query(None, max_length=500)
) -> ClusterDetail:
    """Update a cluster's display name or description.

    Args:
        cluster_id: UUID of the cluster
        update: Update fields (from body)
        display_name: Display name (from query param, fallback)
        description: Description (from query param, fallback)

    Returns:
        Updated cluster details

    Raises:
        HTTPException: 404 if cluster not found
    """
    pool = await get_db_pool()

    # Get values from body or query params
    new_display_name = update.display_name if update else display_name
    new_description = update.description if update else description

    if not new_display_name and not new_description:
        raise HTTPException(status_code=400, detail="Nothing to update")

    async with pool.acquire() as conn:
        # Build update query dynamically
        updates = []
        params = [cluster_id]
        param_idx = 2

        if new_display_name:
            updates.append(f"display_name = ${param_idx}")
            params.append(new_display_name)
            param_idx += 1

        if new_description:
            updates.append(f"description = ${param_idx}")
            params.append(new_description)
            param_idx += 1

        updates.append("updated_at = NOW()")

        query = f"""
            UPDATE memory_clusters
            SET {', '.join(updates)}
            WHERE cluster_id = $1
            RETURNING *
        """

        cluster = await conn.fetchrow(query, *params)

    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    return ClusterDetail(
        cluster_id=str(cluster['cluster_id']),
        canonical_topic=cluster['canonical_topic'],
        display_name=cluster['display_name'],
        description=cluster['description'],
        member_count=cluster['member_count'],
        first_memory_at=cluster['first_memory_at'],
        last_memory_at=cluster['last_memory_at'],
        avg_quality_score=cluster['avg_quality_score'],
        centroid_vector_id=cluster['centroid_vector_id'],
        is_active=cluster['is_active'],
        created_at=cluster['created_at'],
        updated_at=cluster['updated_at']
    )


@router.delete("/{cluster_id}", response_model=DeleteResponse)
async def delete_cluster(cluster_id: str) -> DeleteResponse:
    """Delete a cluster (soft delete).

    Members are unassigned but memories are not deleted.

    Args:
        cluster_id: UUID of the cluster

    Returns:
        Deletion confirmation

    Raises:
        HTTPException: 404 if cluster not found
    """
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        # Soft delete (set is_active = FALSE)
        result = await conn.execute("""
            UPDATE memory_clusters
            SET is_active = FALSE, updated_at = NOW()
            WHERE cluster_id = $1 AND is_active = TRUE
        """, cluster_id)

        # Check if any row was affected
        affected = result.split()[-1]  # "UPDATE X" -> "X"

    if affected == "0":
        raise HTTPException(status_code=404, detail="Cluster not found")

    return DeleteResponse(deleted=True, cluster_id=cluster_id)


@router.post("/{cluster_id}/refresh", response_model=ClusterDetail)
async def refresh_cluster(cluster_id: str) -> ClusterDetail:
    """Refresh cluster aggregates (member count, date range, avg score).

    Call this after manual changes to cluster membership.

    Args:
        cluster_id: UUID of the cluster

    Returns:
        Updated cluster details
    """
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        # Update aggregates from membership table
        await conn.execute("""
            UPDATE memory_clusters mc
            SET
                member_count = COALESCE((
                    SELECT COUNT(*) FROM memory_cluster_members
                    WHERE cluster_id = mc.cluster_id
                ), 0),
                first_memory_at = (
                    SELECT MIN(qh.created_at)
                    FROM memory_cluster_members mcm
                    JOIN query_history qh ON qh.query_id = mcm.memory_id
                    WHERE mcm.cluster_id = mc.cluster_id
                ),
                last_memory_at = (
                    SELECT MAX(qh.created_at)
                    FROM memory_cluster_members mcm
                    JOIN query_history qh ON qh.query_id = mcm.memory_id
                    WHERE mcm.cluster_id = mc.cluster_id
                ),
                updated_at = NOW()
            WHERE cluster_id = $1
        """, cluster_id)

        # Fetch updated cluster
        cluster = await conn.fetchrow("""
            SELECT * FROM memory_clusters WHERE cluster_id = $1
        """, cluster_id)

    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")

    return ClusterDetail(
        cluster_id=str(cluster['cluster_id']),
        canonical_topic=cluster['canonical_topic'],
        display_name=cluster['display_name'],
        description=cluster['description'],
        member_count=cluster['member_count'],
        first_memory_at=cluster['first_memory_at'],
        last_memory_at=cluster['last_memory_at'],
        avg_quality_score=cluster['avg_quality_score'],
        centroid_vector_id=cluster['centroid_vector_id'],
        is_active=cluster['is_active'],
        created_at=cluster['created_at'],
        updated_at=cluster['updated_at']
    )
