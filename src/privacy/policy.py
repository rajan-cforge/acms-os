"""Privacy policy - Single authoritative source for RBAC access rules.

This module defines the ONE place where privacy tier access is determined.
All retrieval paths MUST use these functions to ensure consistent enforcement.

User's 3-Tier Model:
| Role   | Privacy Access               | Scope            |
|--------|------------------------------|------------------|
| Public | PUBLIC only                  | No cross-user    |
| Member | PUBLIC + INTERNAL (own)      | Own user_id only |
| Admin  | PUBLIC + INTERNAL + CONFID.  | Cross-org, audit |

Part of Sprint 1 Security Foundation (Days 4-5).
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

from src.gateway.tracing import get_trace_id

logger = logging.getLogger(__name__)


# Privacy tier definitions
PRIVACY_TIERS = {
    "PUBLIC": 0,       # Anyone can access
    "INTERNAL": 1,     # Authenticated users only, may be scoped to user
    "CONFIDENTIAL": 2, # Admin access only
    "LOCAL_ONLY": 3    # Never sent to external APIs
}

# Role definitions
ROLE_HIERARCHY = {
    "public": 0,    # Unauthenticated/minimal access
    "member": 1,    # Authenticated team member
    "admin": 2      # Full admin access
}


@dataclass
class AccessFilter:
    """Filter to apply when retrieving memories."""
    privacy_tiers: List[str]
    user_id: Optional[str]
    tenant_id: str
    require_own_user: bool = False  # If True, INTERNAL requires user_id match


def allowed_privacy_tiers(role: str) -> List[str]:
    """Get list of privacy tiers accessible by role.

    This is the CANONICAL function for determining tier access.
    All retrieval code MUST use this function.

    Args:
        role: User role (public, member, admin)

    Returns:
        List of accessible privacy tier names
    """
    if role == "admin":
        return ["PUBLIC", "INTERNAL", "CONFIDENTIAL"]
    elif role == "member":
        return ["PUBLIC", "INTERNAL"]
    else:  # public or unknown
        return ["PUBLIC"]


def can_access_tier(role: str, tier: str) -> bool:
    """Check if a role can access a specific tier.

    Args:
        role: User role
        tier: Privacy tier name

    Returns:
        True if role can access tier
    """
    allowed = allowed_privacy_tiers(role)
    return tier.upper() in allowed


def get_access_filter(
    role: str,
    user_id: str,
    tenant_id: str
) -> AccessFilter:
    """Get the complete access filter for a user.

    This is the CANONICAL function for building retrieval filters.
    Encapsulates all the logic for what a user can access.

    Args:
        role: User role (public, member, admin)
        user_id: User identifier
        tenant_id: Tenant/organization identifier

    Returns:
        AccessFilter with all restrictions
    """
    tiers = allowed_privacy_tiers(role)

    # Members can only access INTERNAL data that belongs to them
    require_own_user = role == "member"

    return AccessFilter(
        privacy_tiers=tiers,
        user_id=user_id,
        tenant_id=tenant_id,
        require_own_user=require_own_user
    )


def build_weaviate_filter(access_filter: AccessFilter) -> Dict[str, Any]:
    """Build Weaviate filter from access filter.

    Weaviate v4 uses GraphQL-style filters:
    {
        "operator": "And",
        "operands": [
            {"path": ["privacy_level"], "operator": "ContainsAny", "valueTextArray": [...]},
            {"path": ["tenant_id"], "operator": "Equal", "valueText": "..."}
        ]
    }

    Args:
        access_filter: AccessFilter object

    Returns:
        Weaviate filter dictionary
    """
    operands = []

    # Privacy tier filter
    operands.append({
        "path": ["privacy_level"],
        "operator": "ContainsAny",
        "valueTextArray": access_filter.privacy_tiers
    })

    # Tenant filter
    operands.append({
        "path": ["tenant_id"],
        "operator": "Equal",
        "valueText": access_filter.tenant_id
    })

    # User-specific filter for INTERNAL data
    if access_filter.require_own_user:
        # For members: PUBLIC from anyone OR (INTERNAL and own user_id)
        operands.append({
            "operator": "Or",
            "operands": [
                {
                    "path": ["privacy_level"],
                    "operator": "Equal",
                    "valueText": "PUBLIC"
                },
                {
                    "operator": "And",
                    "operands": [
                        {
                            "path": ["privacy_level"],
                            "operator": "Equal",
                            "valueText": "INTERNAL"
                        },
                        {
                            "path": ["user_id"],
                            "operator": "Equal",
                            "valueText": access_filter.user_id
                        }
                    ]
                }
            ]
        })

    if len(operands) == 1:
        return operands[0]

    return {
        "operator": "And",
        "operands": operands
    }


def build_postgres_filter(access_filter: AccessFilter) -> Dict[str, Any]:
    """Build PostgreSQL filter dictionary for ORM queries.

    Returns dict that can be used with SQLAlchemy filters:
        query.filter(MemoryItem.privacy_level.in_(filter['privacy_levels']))
        query.filter(MemoryItem.tenant_id == filter['tenant_id'])

    Args:
        access_filter: AccessFilter object

    Returns:
        Dictionary with filter parameters
    """
    result = {
        "privacy_levels": access_filter.privacy_tiers,
        "tenant_id": access_filter.tenant_id
    }

    if access_filter.require_own_user:
        result["user_id"] = access_filter.user_id
        result["require_own_user"] = True

    return result


def audit_access(
    user_id: str,
    role: str,
    tenant_id: str,
    tiers_searched: List[str],
    results_per_tier: Dict[str, int],
    action: str = "memory_retrieval"
) -> None:
    """Log access for audit trail.

    Every memory retrieval operation MUST call this function.
    Provides compliance evidence for who accessed what data.

    Args:
        user_id: User who performed the access
        role: User's role at time of access
        tenant_id: Tenant context
        tiers_searched: Which privacy tiers were searched
        results_per_tier: Count of results per tier
        action: Type of access performed
    """
    trace_id = get_trace_id()

    logger.info(
        f"[{trace_id}] AUDIT: {action} | "
        f"user={user_id} role={role} tenant={tenant_id} | "
        f"tiers={tiers_searched} | "
        f"results={results_per_tier}"
    )


def filter_results_by_access(
    results: List[Dict[str, Any]],
    access_filter: AccessFilter
) -> List[Dict[str, Any]]:
    """Post-filter results to ensure access compliance.

    Defense-in-depth: Even if database filter fails, this catches it.
    Should never actually filter anything if DB filter works correctly.

    Args:
        results: Query results from database
        access_filter: User's access filter

    Returns:
        Filtered results (should be same as input if DB filter worked)
    """
    allowed_tiers = set(access_filter.privacy_tiers)
    filtered = []
    denied_count = 0

    for result in results:
        tier = result.get("privacy_level", "PUBLIC").upper()

        if tier not in allowed_tiers:
            denied_count += 1
            continue

        # For INTERNAL, check user ownership if required
        if access_filter.require_own_user and tier == "INTERNAL":
            result_user = result.get("user_id")
            if result_user != access_filter.user_id:
                denied_count += 1
                continue

        filtered.append(result)

    if denied_count > 0:
        trace_id = get_trace_id()
        logger.warning(
            f"[{trace_id}] Post-filter denied {denied_count} results - "
            f"DB filter may not be working correctly"
        )

    return filtered


def should_send_to_external_api(privacy_level: str) -> bool:
    """Check if content with this privacy level can be sent to external APIs.

    LOCAL_ONLY and CONFIDENTIAL content should NEVER be sent to:
    - Tavily (web search)
    - OpenAI (embeddings, chat)
    - Anthropic (chat)
    - Gemini (chat)

    Args:
        privacy_level: Privacy tier of the content

    Returns:
        True if content can be sent to external APIs
    """
    blocked_tiers = {"LOCAL_ONLY", "CONFIDENTIAL"}
    return privacy_level.upper() not in blocked_tiers


def validate_write_permission(
    role: str,
    target_tier: str,
    target_user_id: str,
    requesting_user_id: str
) -> bool:
    """Check if user can write to specified tier/user.

    Args:
        role: User's role
        target_tier: Privacy tier of content being written
        target_user_id: User who will own the content
        requesting_user_id: User making the request

    Returns:
        True if write is allowed
    """
    # Admins can write to any tier for any user
    if role == "admin":
        return True

    # Members can only write INTERNAL/PUBLIC for themselves
    if role == "member":
        if target_tier.upper() == "CONFIDENTIAL":
            return False
        return target_user_id == requesting_user_id

    # Public users cannot write
    return False
