"""
Privacy Tier System (Week 6 Task 1)

Four-level privacy system with role-based access control:
- PUBLIC: Company-wide knowledge
- INTERNAL: Team-level information
- CONFIDENTIAL: Sensitive business data
- LOCAL_ONLY: Personal notes (owner-only access)
"""

from .tiers import PrivacyLevel
from .roles import UserRole, get_accessible_levels
from .filter import PrivacyFilter

__all__ = [
    "PrivacyLevel",
    "UserRole",
    "get_accessible_levels",
    "PrivacyFilter",
]
