"""
Unit tests for Privacy Tier System (Week 6 Task 1)

Test Coverage:
- Privacy level enum validation
- User role access mappings
- Privacy filter logic
- Owner-based access for LOCAL_ONLY
- Edge cases and security scenarios

Following TDD: Write tests FIRST, then implement
"""

import pytest
from src.privacy.tiers import PrivacyLevel
from src.privacy.roles import UserRole, get_accessible_levels
from src.privacy.filter import PrivacyFilter


class TestPrivacyLevels:
    """Test privacy level enum and basic properties"""

    def test_privacy_levels_exist(self):
        """Verify all four privacy levels are defined"""
        assert PrivacyLevel.PUBLIC
        assert PrivacyLevel.INTERNAL
        assert PrivacyLevel.CONFIDENTIAL
        assert PrivacyLevel.LOCAL_ONLY

    def test_privacy_level_values(self):
        """Verify privacy level string values"""
        assert PrivacyLevel.PUBLIC.value == "PUBLIC"
        assert PrivacyLevel.INTERNAL.value == "INTERNAL"
        assert PrivacyLevel.CONFIDENTIAL.value == "CONFIDENTIAL"
        assert PrivacyLevel.LOCAL_ONLY.value == "LOCAL_ONLY"


class TestUserRoles:
    """Test user role definitions and access mappings"""

    def test_user_roles_exist(self):
        """Verify all five user roles are defined"""
        assert UserRole.ADMIN
        assert UserRole.MANAGER
        assert UserRole.LEAD
        assert UserRole.MEMBER
        assert UserRole.VIEWER

    def test_admin_has_access_to_all_levels(self):
        """Admin role should access all four privacy levels"""
        levels = get_accessible_levels(UserRole.ADMIN)
        assert len(levels) == 4
        assert PrivacyLevel.PUBLIC in levels
        assert PrivacyLevel.INTERNAL in levels
        assert PrivacyLevel.CONFIDENTIAL in levels
        assert PrivacyLevel.LOCAL_ONLY in levels

    def test_manager_accesses_confidential_but_not_others_local(self):
        """Manager can access CONFIDENTIAL but not others' LOCAL_ONLY"""
        levels = get_accessible_levels(UserRole.MANAGER)
        assert PrivacyLevel.PUBLIC in levels
        assert PrivacyLevel.INTERNAL in levels
        assert PrivacyLevel.CONFIDENTIAL in levels
        # LOCAL_ONLY only accessible to owner, not by role

    def test_lead_accesses_confidential_but_not_others_local(self):
        """Lead can access CONFIDENTIAL but not others' LOCAL_ONLY"""
        levels = get_accessible_levels(UserRole.LEAD)
        assert PrivacyLevel.PUBLIC in levels
        assert PrivacyLevel.INTERNAL in levels
        assert PrivacyLevel.CONFIDENTIAL in levels

    def test_member_cannot_access_confidential(self):
        """Member role should NOT access CONFIDENTIAL"""
        levels = get_accessible_levels(UserRole.MEMBER)
        assert PrivacyLevel.PUBLIC in levels
        assert PrivacyLevel.INTERNAL in levels
        assert PrivacyLevel.CONFIDENTIAL not in levels

    def test_viewer_only_sees_public(self):
        """Viewer role should ONLY access PUBLIC"""
        levels = get_accessible_levels(UserRole.VIEWER)
        assert len(levels) == 1
        assert PrivacyLevel.PUBLIC in levels
        assert PrivacyLevel.INTERNAL not in levels
        assert PrivacyLevel.CONFIDENTIAL not in levels


class TestPrivacyFilter:
    """Test privacy filtering logic for search results"""

    def test_filter_removes_confidential_for_member(self):
        """Member should not see CONFIDENTIAL results"""
        filter = PrivacyFilter(UserRole.MEMBER, "user123")
        results = [
            {"id": 1, "content": "Public doc", "privacy_level": "PUBLIC"},
            {"id": 2, "content": "Secret budget", "privacy_level": "CONFIDENTIAL"}
        ]
        filtered = filter.filter_results(results)

        assert len(filtered) == 1
        assert filtered[0]["content"] == "Public doc"

    def test_filter_keeps_confidential_for_manager(self):
        """Manager should see CONFIDENTIAL results"""
        filter = PrivacyFilter(UserRole.MANAGER, "manager123")
        results = [
            {"id": 1, "content": "Public doc", "privacy_level": "PUBLIC"},
            {"id": 2, "content": "Secret budget", "privacy_level": "CONFIDENTIAL"}
        ]
        filtered = filter.filter_results(results)

        assert len(filtered) == 2

    def test_local_only_accessible_to_owner_only(self):
        """LOCAL_ONLY content only accessible to owner"""
        filter = PrivacyFilter(UserRole.MEMBER, "user123")
        result = {
            "id": 1,
            "content": "My notes",
            "privacy_level": "LOCAL_ONLY",
            "owner_id": "user123"
        }

        # Owner can access their own LOCAL_ONLY
        assert filter.can_access(
            PrivacyLevel.LOCAL_ONLY,
            owner_id="user123"
        ) == True

    def test_local_only_not_accessible_to_other_users(self):
        """LOCAL_ONLY content NOT accessible to other users"""
        filter = PrivacyFilter(UserRole.MEMBER, "user123")

        # Other user cannot access someone else's LOCAL_ONLY
        assert filter.can_access(
            PrivacyLevel.LOCAL_ONLY,
            owner_id="user456"
        ) == False

    def test_admin_cannot_see_others_local_only(self):
        """Even ADMIN cannot access others' LOCAL_ONLY (privacy guarantee)"""
        filter = PrivacyFilter(UserRole.ADMIN, "admin123")
        result = {
            "id": 1,
            "content": "User's private notes",
            "privacy_level": "LOCAL_ONLY",
            "owner_id": "user456"
        }

        # Admin cannot access other user's LOCAL_ONLY
        assert filter.can_access(
            PrivacyLevel.LOCAL_ONLY,
            owner_id="user456"
        ) == False

    def test_viewer_only_sees_public(self):
        """Viewer should only see PUBLIC results"""
        filter = PrivacyFilter(UserRole.VIEWER, "viewer123")
        results = [
            {"id": 1, "content": "Public doc", "privacy_level": "PUBLIC"},
            {"id": 2, "content": "Internal memo", "privacy_level": "INTERNAL"},
            {"id": 3, "content": "Secret", "privacy_level": "CONFIDENTIAL"}
        ]
        filtered = filter.filter_results(results)

        assert len(filtered) == 1
        assert filtered[0]["content"] == "Public doc"

    def test_filter_handles_missing_privacy_level(self):
        """Results without privacy_level default to PUBLIC"""
        filter = PrivacyFilter(UserRole.VIEWER, "viewer123")
        results = [
            {"id": 1, "content": "Legacy doc"}  # No privacy_level field
        ]
        filtered = filter.filter_results(results)

        # Should default to PUBLIC and be visible to viewer
        assert len(filtered) == 1

    def test_filter_handles_missing_owner_id_for_local_only(self):
        """LOCAL_ONLY without owner_id should be inaccessible"""
        filter = PrivacyFilter(UserRole.MEMBER, "user123")
        results = [
            {"id": 1, "content": "Orphaned local", "privacy_level": "LOCAL_ONLY"}
            # Missing owner_id
        ]
        filtered = filter.filter_results(results)

        # Should be filtered out (cannot determine ownership)
        assert len(filtered) == 0


class TestPrivacySecurityScenarios:
    """Test security edge cases and attack scenarios"""

    def test_cannot_bypass_filter_with_case_variation(self):
        """Privacy level check should be case-insensitive"""
        filter = PrivacyFilter(UserRole.MEMBER, "user123")
        results = [
            {"id": 1, "content": "Secret", "privacy_level": "confidential"},  # lowercase
            {"id": 2, "content": "Secret2", "privacy_level": "Confidential"},  # mixed
        ]
        filtered = filter.filter_results(results)

        # Member should not see any confidential (case variations)
        assert len(filtered) == 0

    def test_empty_results_list_returns_empty(self):
        """Filter should handle empty results gracefully"""
        filter = PrivacyFilter(UserRole.MEMBER, "user123")
        filtered = filter.filter_results([])

        assert filtered == []

    def test_none_owner_id_not_equals_any_user_id(self):
        """None owner_id should not match any user"""
        filter = PrivacyFilter(UserRole.MEMBER, "user123")

        assert filter.can_access(
            PrivacyLevel.LOCAL_ONLY,
            owner_id=None
        ) == False
