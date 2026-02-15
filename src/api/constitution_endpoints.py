"""Financial Constitution API Endpoints.

Sprint 4: Financial Constitution for UX Improvements

REST API for managing investment rules, allocation targets, and compliance monitoring.

PRIVACY: Dollar amounts NEVER sent to LLM. All values encrypted at rest.
"""

import json
import logging
from datetime import date, datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.storage.database import get_db_pool


def parse_json_field(value):
    """Parse a JSON field that might be a string or already a dict."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/constitution", tags=["constitution"])

# Default user ID (matches database default)
DEFAULT_USER_ID = "00000000-0000-0000-0000-000000000001"


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class AllocationBucket(BaseModel):
    """Allocation bucket definition."""
    bucket_id: str
    name: str
    display_name: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    target_percent: float
    min_percent: Optional[float] = None
    max_percent: Optional[float] = None
    security_tags: List[str] = []
    security_types: List[str] = []
    sectors: List[str] = []
    is_active: bool = True
    sort_order: int = 0


class CreateBucketRequest(BaseModel):
    """Request to create allocation bucket."""
    name: str
    display_name: str
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    target_percent: float = Field(ge=0, le=100)
    min_percent: Optional[float] = Field(None, ge=0)
    max_percent: Optional[float] = Field(None, le=100)
    security_tags: List[str] = []
    security_types: List[str] = []
    sectors: List[str] = []


class UpdateBucketRequest(BaseModel):
    """Request to update allocation bucket."""
    display_name: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None
    icon: Optional[str] = None
    target_percent: Optional[float] = Field(None, ge=0, le=100)
    min_percent: Optional[float] = Field(None, ge=0)
    max_percent: Optional[float] = Field(None, le=100)
    security_tags: Optional[List[str]] = None
    security_types: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    is_active: Optional[bool] = None
    sort_order: Optional[int] = None


class ConstitutionRule(BaseModel):
    """Constitution rule definition."""
    rule_id: str
    name: str
    description: Optional[str] = None
    rule_type: str
    parameters: dict
    severity: str = "warning"
    is_active: bool = True


class CreateRuleRequest(BaseModel):
    """Request to create constitution rule."""
    name: str
    description: Optional[str] = None
    rule_type: str  # 'allocation', 'position_limit', 'sector_limit', 'custom'
    parameters: dict
    severity: str = "warning"


class AllocationStatus(BaseModel):
    """Current allocation status for a bucket."""
    bucket_id: str
    name: str
    display_name: str
    color: Optional[str] = None
    icon: Optional[str] = None
    target_percent: float
    actual_percent: float
    drift_percent: float
    status: str  # 'on_target', 'under', 'over'
    value: Optional[float] = None  # Decrypted for display


class ComplianceResult(BaseModel):
    """Compliance check result for a rule."""
    rule_id: str
    name: str
    rule_type: str
    severity: str
    passed: bool
    message: str
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None


class PortfolioSummary(BaseModel):
    """Portfolio summary with allocations and compliance."""
    snapshot_date: str
    total_value: float  # Decrypted
    allocations: List[AllocationStatus]
    compliance: List[ComplianceResult]
    rules_passed: int
    rules_warned: int
    rules_failed: int
    overall_status: str  # 'compliant', 'warning', 'non_compliant'


class RebalanceAction(BaseModel):
    """Rebalance recommendation."""
    recommendation_id: str
    action: str  # 'buy', 'sell', 'hold'
    ticker: Optional[str] = None
    security_name: Optional[str] = None
    bucket_name: str
    current_percent: float
    target_percent: float
    change_percent: float
    change_value: Optional[float] = None  # Decrypted
    reason: str
    priority: int


# ============================================================================
# BUCKET ENDPOINTS
# ============================================================================

@router.get("/buckets", response_model=List[AllocationBucket])
async def list_buckets(
    include_inactive: bool = Query(False),
    user_id: str = Query(DEFAULT_USER_ID)
):
    """List all allocation buckets."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        query = """
            SELECT
                bucket_id, name, display_name, description, color, icon,
                target_percent, min_percent, max_percent,
                security_tags, security_types, sectors,
                is_active, sort_order
            FROM allocation_buckets
            WHERE user_id = $1
        """
        params = [user_id]

        if not include_inactive:
            query += " AND is_active = TRUE"

        query += " ORDER BY sort_order, name"

        rows = await conn.fetch(query, *params)

        return [
            AllocationBucket(
                bucket_id=str(row['bucket_id']),
                name=row['name'],
                display_name=row['display_name'],
                description=row['description'],
                color=row['color'],
                icon=row['icon'],
                target_percent=row['target_percent'],
                min_percent=row['min_percent'],
                max_percent=row['max_percent'],
                security_tags=row['security_tags'] or [],
                security_types=row['security_types'] or [],
                sectors=row['sectors'] or [],
                is_active=row['is_active'],
                sort_order=row['sort_order'] or 0
            )
            for row in rows
        ]


@router.post("/buckets", response_model=AllocationBucket)
async def create_bucket(
    request: CreateBucketRequest,
    user_id: str = Query(DEFAULT_USER_ID)
):
    """Create a new allocation bucket."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO allocation_buckets (
                user_id, name, display_name, description, color, icon,
                target_percent, min_percent, max_percent,
                security_tags, security_types, sectors
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING bucket_id, name, display_name, description, color, icon,
                target_percent, min_percent, max_percent,
                security_tags, security_types, sectors, is_active, sort_order
        """, user_id, request.name, request.display_name, request.description,
            request.color, request.icon, request.target_percent,
            request.min_percent, request.max_percent,
            request.security_tags, request.security_types, request.sectors)

        return AllocationBucket(
            bucket_id=str(row['bucket_id']),
            name=row['name'],
            display_name=row['display_name'],
            description=row['description'],
            color=row['color'],
            icon=row['icon'],
            target_percent=row['target_percent'],
            min_percent=row['min_percent'],
            max_percent=row['max_percent'],
            security_tags=row['security_tags'] or [],
            security_types=row['security_types'] or [],
            sectors=row['sectors'] or [],
            is_active=row['is_active'],
            sort_order=row['sort_order'] or 0
        )


@router.patch("/buckets/{bucket_id}", response_model=AllocationBucket)
async def update_bucket(bucket_id: UUID, request: UpdateBucketRequest):
    """Update an allocation bucket."""
    pool = await get_db_pool()

    # Build update clause
    updates = ["updated_at = NOW()"]
    params = [bucket_id]
    param_idx = 2

    if request.display_name is not None:
        updates.append(f"display_name = ${param_idx}")
        params.append(request.display_name)
        param_idx += 1

    if request.description is not None:
        updates.append(f"description = ${param_idx}")
        params.append(request.description)
        param_idx += 1

    if request.color is not None:
        updates.append(f"color = ${param_idx}")
        params.append(request.color)
        param_idx += 1

    if request.icon is not None:
        updates.append(f"icon = ${param_idx}")
        params.append(request.icon)
        param_idx += 1

    if request.target_percent is not None:
        updates.append(f"target_percent = ${param_idx}")
        params.append(request.target_percent)
        param_idx += 1

    if request.min_percent is not None:
        updates.append(f"min_percent = ${param_idx}")
        params.append(request.min_percent)
        param_idx += 1

    if request.max_percent is not None:
        updates.append(f"max_percent = ${param_idx}")
        params.append(request.max_percent)
        param_idx += 1

    if request.security_tags is not None:
        updates.append(f"security_tags = ${param_idx}")
        params.append(request.security_tags)
        param_idx += 1

    if request.security_types is not None:
        updates.append(f"security_types = ${param_idx}")
        params.append(request.security_types)
        param_idx += 1

    if request.sectors is not None:
        updates.append(f"sectors = ${param_idx}")
        params.append(request.sectors)
        param_idx += 1

    if request.is_active is not None:
        updates.append(f"is_active = ${param_idx}")
        params.append(request.is_active)
        param_idx += 1

    if request.sort_order is not None:
        updates.append(f"sort_order = ${param_idx}")
        params.append(request.sort_order)
        param_idx += 1

    update_clause = ", ".join(updates)

    async with pool.acquire() as conn:
        row = await conn.fetchrow(f"""
            UPDATE allocation_buckets
            SET {update_clause}
            WHERE bucket_id = $1
            RETURNING bucket_id, name, display_name, description, color, icon,
                target_percent, min_percent, max_percent,
                security_tags, security_types, sectors, is_active, sort_order
        """, *params)

        if not row:
            raise HTTPException(status_code=404, detail="Bucket not found")

        return AllocationBucket(
            bucket_id=str(row['bucket_id']),
            name=row['name'],
            display_name=row['display_name'],
            description=row['description'],
            color=row['color'],
            icon=row['icon'],
            target_percent=row['target_percent'],
            min_percent=row['min_percent'],
            max_percent=row['max_percent'],
            security_tags=row['security_tags'] or [],
            security_types=row['security_types'] or [],
            sectors=row['sectors'] or [],
            is_active=row['is_active'],
            sort_order=row['sort_order'] or 0
        )


@router.delete("/buckets/{bucket_id}")
async def delete_bucket(bucket_id: UUID):
    """Soft delete an allocation bucket."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE allocation_buckets
            SET is_active = FALSE, updated_at = NOW()
            WHERE bucket_id = $1 AND is_active = TRUE
        """, bucket_id)

        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Bucket not found")

        return {"status": "deleted", "bucket_id": str(bucket_id)}


# ============================================================================
# RULE ENDPOINTS
# ============================================================================

@router.get("/rules", response_model=List[ConstitutionRule])
async def list_rules(
    rule_type: Optional[str] = Query(None),
    include_inactive: bool = Query(False),
    user_id: str = Query(DEFAULT_USER_ID)
):
    """List all constitution rules."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        query = """
            SELECT rule_id, name, description, rule_type, parameters, severity, is_active
            FROM constitution_rules
            WHERE user_id = $1
        """
        params = [user_id]

        if not include_inactive:
            query += " AND is_active = TRUE"

        if rule_type:
            query += f" AND rule_type = ${len(params) + 1}"
            params.append(rule_type)

        query += " ORDER BY severity DESC, name"

        rows = await conn.fetch(query, *params)

        return [
            ConstitutionRule(
                rule_id=str(row['rule_id']),
                name=row['name'],
                description=row['description'],
                rule_type=row['rule_type'],
                parameters=parse_json_field(row['parameters']),
                severity=row['severity'],
                is_active=row['is_active']
            )
            for row in rows
        ]


@router.post("/rules", response_model=ConstitutionRule)
async def create_rule(
    request: CreateRuleRequest,
    user_id: str = Query(DEFAULT_USER_ID)
):
    """Create a new constitution rule."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO constitution_rules (
                user_id, name, description, rule_type, parameters, severity
            ) VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING rule_id, name, description, rule_type, parameters, severity, is_active
        """, user_id, request.name, request.description, request.rule_type,
            request.parameters, request.severity)

        return ConstitutionRule(
            rule_id=str(row['rule_id']),
            name=row['name'],
            description=row['description'],
            rule_type=row['rule_type'],
            parameters=parse_json_field(row['parameters']),
            severity=row['severity'],
            is_active=row['is_active']
        )


@router.delete("/rules/{rule_id}")
async def delete_rule(rule_id: UUID):
    """Soft delete a constitution rule."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE constitution_rules
            SET is_active = FALSE, updated_at = NOW()
            WHERE rule_id = $1 AND is_active = TRUE
        """, rule_id)

        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Rule not found")

        return {"status": "deleted", "rule_id": str(rule_id)}


# ============================================================================
# PORTFOLIO ANALYSIS ENDPOINTS
# ============================================================================

@router.get("/portfolio/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    user_id: str = Query(DEFAULT_USER_ID),
    snapshot_date: Optional[str] = Query(None)
):
    """Get portfolio summary with allocations and compliance status."""
    pool = await get_db_pool()
    target_date = date.fromisoformat(snapshot_date) if snapshot_date else date.today()

    async with pool.acquire() as conn:
        # Get latest snapshot
        snapshot = await conn.fetchrow("""
            SELECT
                snapshot_id, snapshot_date, total_value_encrypted,
                allocations, rules_passed, rules_warned, rules_failed,
                compliance_details
            FROM allocation_snapshots
            WHERE user_id = $1 AND snapshot_date <= $2
            ORDER BY snapshot_date DESC
            LIMIT 1
        """, user_id, target_date)

        if not snapshot:
            # No snapshot, return empty/default
            buckets = await conn.fetch("""
                SELECT bucket_id, name, display_name, color, icon, target_percent
                FROM allocation_buckets
                WHERE user_id = $1 AND is_active = TRUE
                ORDER BY sort_order
            """, user_id)

            return PortfolioSummary(
                snapshot_date=target_date.isoformat(),
                total_value=0,
                allocations=[
                    AllocationStatus(
                        bucket_id=str(b['bucket_id']),
                        name=b['name'],
                        display_name=b['display_name'],
                        color=b['color'],
                        icon=b['icon'],
                        target_percent=b['target_percent'],
                        actual_percent=0,
                        drift_percent=-b['target_percent'],
                        status='under',
                        value=0
                    )
                    for b in buckets
                ],
                compliance=[],
                rules_passed=0,
                rules_warned=0,
                rules_failed=0,
                overall_status='unknown'
            )

        # Decrypt total value
        from src.integrations.plaid import PlaidSyncService
        sync = PlaidSyncService(db_pool=pool)
        total_value = sync._decrypt(snapshot['total_value_encrypted'])

        # Parse allocations
        allocations_data = snapshot['allocations'] or []
        allocations = []

        for alloc in allocations_data:
            actual = alloc.get('actual_percent', 0)
            target = alloc.get('target_percent', 0)
            drift = actual - target

            if abs(drift) < 2:
                status = 'on_target'
            elif drift < 0:
                status = 'under'
            else:
                status = 'over'

            value = sync._decrypt(alloc.get('value_encrypted', '')) if alloc.get('value_encrypted') else None

            allocations.append(AllocationStatus(
                bucket_id=alloc.get('bucket_id', ''),
                name=alloc.get('name', ''),
                display_name=alloc.get('display_name', alloc.get('name', '')),
                color=alloc.get('color'),
                icon=alloc.get('icon'),
                target_percent=target,
                actual_percent=actual,
                drift_percent=drift,
                status=status,
                value=value
            ))

        # Parse compliance
        compliance_data = snapshot['compliance_details'] or []
        compliance = [
            ComplianceResult(**c) for c in compliance_data
        ]

        # Determine overall status
        if snapshot['rules_failed'] > 0:
            overall_status = 'non_compliant'
        elif snapshot['rules_warned'] > 0:
            overall_status = 'warning'
        else:
            overall_status = 'compliant'

        return PortfolioSummary(
            snapshot_date=snapshot['snapshot_date'].isoformat(),
            total_value=total_value,
            allocations=allocations,
            compliance=compliance,
            rules_passed=snapshot['rules_passed'] or 0,
            rules_warned=snapshot['rules_warned'] or 0,
            rules_failed=snapshot['rules_failed'] or 0,
            overall_status=overall_status
        )


@router.get("/portfolio/rebalance", response_model=List[RebalanceAction])
async def get_rebalance_recommendations(
    user_id: str = Query(DEFAULT_USER_ID),
    min_priority: int = Query(0)
):
    """Get rebalancing recommendations."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        # Get latest snapshot
        snapshot = await conn.fetchrow("""
            SELECT snapshot_id
            FROM allocation_snapshots
            WHERE user_id = $1
            ORDER BY snapshot_date DESC
            LIMIT 1
        """, user_id)

        if not snapshot:
            return []

        # Get recommendations
        rows = await conn.fetch("""
            SELECT
                r.recommendation_id, r.action, r.ticker, r.security_name,
                r.current_value_encrypted, r.target_value_encrypted,
                r.change_value_encrypted, r.change_percent,
                r.reason, r.priority,
                b.name as bucket_name, b.target_percent
            FROM rebalance_recommendations r
            LEFT JOIN allocation_buckets b ON r.bucket_id = b.bucket_id
            WHERE r.snapshot_id = $1
              AND r.status = 'pending'
              AND r.priority >= $2
            ORDER BY r.priority DESC, r.action
        """, snapshot['snapshot_id'], min_priority)

        # Decrypt values
        from src.integrations.plaid import PlaidSyncService
        sync = PlaidSyncService(db_pool=pool)

        recommendations = []
        for row in rows:
            change_value = sync._decrypt(row['change_value_encrypted']) if row['change_value_encrypted'] else None

            recommendations.append(RebalanceAction(
                recommendation_id=str(row['recommendation_id']),
                action=row['action'],
                ticker=row['ticker'],
                security_name=row['security_name'],
                bucket_name=row['bucket_name'] or 'Unknown',
                current_percent=0,  # Would need to calculate
                target_percent=row['target_percent'] or 0,
                change_percent=row['change_percent'] or 0,
                change_value=change_value,
                reason=row['reason'] or '',
                priority=row['priority'] or 0
            ))

        return recommendations


@router.post("/portfolio/rebalance/{recommendation_id}/dismiss")
async def dismiss_recommendation(
    recommendation_id: UUID,
    reason: str = Query("User dismissed")
):
    """Dismiss a rebalancing recommendation."""
    pool = await get_db_pool()

    async with pool.acquire() as conn:
        result = await conn.execute("""
            UPDATE rebalance_recommendations
            SET status = 'dismissed',
                dismissed_at = NOW(),
                dismissed_reason = $2
            WHERE recommendation_id = $1 AND status = 'pending'
        """, recommendation_id, reason)

        if result == "UPDATE 0":
            raise HTTPException(status_code=404, detail="Recommendation not found")

        return {"status": "dismissed", "recommendation_id": str(recommendation_id)}


# ============================================================================
# ALLOCATION CHART DATA
# ============================================================================

@router.get("/portfolio/chart-data")
async def get_allocation_chart_data(
    user_id: str = Query(DEFAULT_USER_ID),
    days: int = Query(30, ge=1, le=365)
):
    """Get allocation history for charts."""
    pool = await get_db_pool()
    start_date = date.today()

    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT snapshot_date, allocations
            FROM allocation_snapshots
            WHERE user_id = $1
              AND snapshot_date >= NOW() - INTERVAL '$2 days'
            ORDER BY snapshot_date
        """, user_id, days)

        # Transform for charting
        chart_data = []
        for row in rows:
            entry = {"date": row['snapshot_date'].isoformat()}
            for alloc in (row['allocations'] or []):
                entry[alloc.get('name', 'unknown')] = alloc.get('actual_percent', 0)
            chart_data.append(entry)

        # Get bucket colors
        buckets = await conn.fetch("""
            SELECT name, color FROM allocation_buckets
            WHERE user_id = $1 AND is_active = TRUE
        """, user_id)

        colors = {b['name']: b['color'] for b in buckets}

        return {
            "data": chart_data,
            "colors": colors
        }
