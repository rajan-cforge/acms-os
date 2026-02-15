"""
User Role Definitions and Access Mappings

Five-role hierarchy with privacy level access control.
"""

from enum import Enum
from typing import List
from .tiers import PrivacyLevel


class UserRole(Enum):
    """
    User roles for role-based access control (RBAC)

    Roles (from most to least privileged):
    - ADMIN: System administrators (access: ALL levels including LOCAL_ONLY for own data)
    - MANAGER: Department managers (access: PUBLIC, INTERNAL, CONFIDENTIAL)
    - LEAD: Team leads (access: PUBLIC, INTERNAL, CONFIDENTIAL)
    - MEMBER: Team members (access: PUBLIC, INTERNAL)
    - VIEWER: Read-only users (access: PUBLIC only)

    Note: LOCAL_ONLY is special - accessible ONLY by owner, regardless of role
    """

    ADMIN = "admin"
    MANAGER = "manager"
    LEAD = "lead"
    MEMBER = "member"
    VIEWER = "viewer"

    def __str__(self):
        return self.value


def get_accessible_levels(role: UserRole) -> List[PrivacyLevel]:
    """
    Get privacy levels accessible to a given user role

    Args:
        role: User role to check

    Returns:
        List of PrivacyLevel enums accessible to this role

    Note:
        LOCAL_ONLY is included in ADMIN's list but requires owner check.
        Other roles can only access their own LOCAL_ONLY content.
    """
    access_map = {
        UserRole.ADMIN: [
            PrivacyLevel.PUBLIC,
            PrivacyLevel.INTERNAL,
            PrivacyLevel.CONFIDENTIAL,
            PrivacyLevel.LOCAL_ONLY  # Can access own LOCAL_ONLY
        ],
        UserRole.MANAGER: [
            PrivacyLevel.PUBLIC,
            PrivacyLevel.INTERNAL,
            PrivacyLevel.CONFIDENTIAL
        ],
        UserRole.LEAD: [
            PrivacyLevel.PUBLIC,
            PrivacyLevel.INTERNAL,
            PrivacyLevel.CONFIDENTIAL
        ],
        UserRole.MEMBER: [
            PrivacyLevel.PUBLIC,
            PrivacyLevel.INTERNAL
        ],
        UserRole.VIEWER: [
            PrivacyLevel.PUBLIC
        ]
    }

    return access_map[role]
