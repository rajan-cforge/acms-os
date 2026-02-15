"""
Privacy Filter for Search Results

Filters memory/search results based on user role and ownership.
"""

from typing import List, Optional
from .tiers import PrivacyLevel
from .roles import UserRole, get_accessible_levels


class PrivacyFilter:
    """
    Filter search results based on user access permissions

    Implements role-based access control (RBAC) with special handling
    for LOCAL_ONLY content (owner-only access).

    Example:
        >>> filter = PrivacyFilter(UserRole.MEMBER, "user123")
        >>> results = [
        ...     {"content": "Public doc", "privacy_level": "PUBLIC"},
        ...     {"content": "Secret", "privacy_level": "CONFIDENTIAL"}
        ... ]
        >>> filtered = filter.filter_results(results)
        >>> # Returns only public doc (member cannot see confidential)
    """

    def __init__(self, user_role: UserRole, user_id: str):
        """
        Initialize privacy filter

        Args:
            user_role: Role of the current user
            user_id: Unique identifier of the current user
        """
        self.user_role = user_role
        self.user_id = user_id
        self.accessible_levels = get_accessible_levels(user_role)

    def can_access(
        self,
        privacy_level: PrivacyLevel,
        owner_id: Optional[str] = None
    ) -> bool:
        """
        Check if user can access content at given privacy level

        Args:
            privacy_level: Privacy level of the content
            owner_id: Owner of the content (required for LOCAL_ONLY)

        Returns:
            True if user can access, False otherwise

        Security Rules:
            - LOCAL_ONLY: Only owner can access (even ADMIN cannot)
            - Other levels: Check role permissions via accessible_levels
        """
        # Special case: LOCAL_ONLY is owner-only
        if privacy_level == PrivacyLevel.LOCAL_ONLY:
            # Must have owner_id and it must match user_id
            if owner_id is None:
                return False
            return owner_id == self.user_id

        # Other levels: check role permissions
        return privacy_level in self.accessible_levels

    def filter_results(self, results: List[dict]) -> List[dict]:
        """
        Filter search results based on privacy permissions

        Args:
            results: List of result dicts with privacy_level and owner_id fields

        Returns:
            Filtered list containing only accessible results

        Note:
            - Results without privacy_level default to PUBLIC
            - Case-insensitive privacy level matching
            - Invalid privacy levels are filtered out (safe default)
        """
        filtered = []

        for result in results:
            # Get privacy level (default to PUBLIC if missing)
            privacy_str = result.get('privacy_level', 'PUBLIC')

            # Convert to PrivacyLevel enum (case-insensitive)
            try:
                privacy_level = PrivacyLevel(privacy_str.upper())
            except (ValueError, AttributeError):
                # Invalid privacy level - skip for safety
                continue

            # Get owner (may be None)
            owner_id = result.get('owner_id')

            # Check access
            if self.can_access(privacy_level, owner_id):
                filtered.append(result)

        return filtered
