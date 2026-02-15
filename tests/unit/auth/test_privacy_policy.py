"""Unit tests for Privacy Policy RBAC.

Tests verify that:
1. Each role gets correct privacy tiers
2. Access filters are built correctly
3. Post-filtering catches database bypasses
4. Write permissions are enforced
5. External API rules are respected

TDD spec from ACMS_Combined_Code_Review_Refactor_TDD_Spec.md
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.privacy.policy import (
    allowed_privacy_tiers,
    can_access_tier,
    get_access_filter,
    build_weaviate_filter,
    build_postgres_filter,
    filter_results_by_access,
    should_send_to_external_api,
    validate_write_permission,
    AccessFilter
)


class TestAllowedPrivacyTiers:
    """Test role to tier mapping."""

    @pytest.mark.unit
    def test_public_only_gets_public(self):
        """Public role should only access PUBLIC tier."""
        tiers = allowed_privacy_tiers("public")
        assert tiers == ["PUBLIC"]

    @pytest.mark.unit
    def test_member_gets_public_and_internal(self):
        """Member role should access PUBLIC and INTERNAL."""
        tiers = allowed_privacy_tiers("member")
        assert "PUBLIC" in tiers
        assert "INTERNAL" in tiers
        assert "CONFIDENTIAL" not in tiers

    @pytest.mark.unit
    def test_admin_gets_all_tiers(self):
        """Admin role should access all tiers."""
        tiers = allowed_privacy_tiers("admin")
        assert "PUBLIC" in tiers
        assert "INTERNAL" in tiers
        assert "CONFIDENTIAL" in tiers

    @pytest.mark.unit
    def test_unknown_role_defaults_to_public(self):
        """Unknown role should default to PUBLIC only."""
        tiers = allowed_privacy_tiers("unknown_role")
        assert tiers == ["PUBLIC"]


class TestCanAccessTier:
    """Test tier access checking."""

    @pytest.mark.unit
    def test_public_can_access_public(self):
        """Public role can access PUBLIC tier."""
        assert can_access_tier("public", "PUBLIC") is True

    @pytest.mark.unit
    def test_public_cannot_access_internal(self):
        """Public role cannot access INTERNAL tier."""
        assert can_access_tier("public", "INTERNAL") is False

    @pytest.mark.unit
    def test_member_can_access_internal(self):
        """Member role can access INTERNAL tier."""
        assert can_access_tier("member", "INTERNAL") is True

    @pytest.mark.unit
    def test_member_cannot_access_confidential(self):
        """Member role cannot access CONFIDENTIAL tier."""
        assert can_access_tier("member", "CONFIDENTIAL") is False

    @pytest.mark.unit
    def test_admin_can_access_confidential(self):
        """Admin role can access CONFIDENTIAL tier."""
        assert can_access_tier("admin", "CONFIDENTIAL") is True

    @pytest.mark.unit
    def test_case_insensitive_tier(self):
        """Tier comparison should be case insensitive."""
        assert can_access_tier("admin", "confidential") is True
        assert can_access_tier("admin", "CONFIDENTIAL") is True


class TestGetAccessFilter:
    """Test access filter generation."""

    @pytest.mark.unit
    def test_filter_has_correct_tiers(self):
        """Filter should have role-appropriate tiers."""
        filter = get_access_filter("member", "user123", "tenant456")
        assert "PUBLIC" in filter.privacy_tiers
        assert "INTERNAL" in filter.privacy_tiers

    @pytest.mark.unit
    def test_filter_has_user_id(self):
        """Filter should include user_id."""
        filter = get_access_filter("member", "user123", "tenant456")
        assert filter.user_id == "user123"

    @pytest.mark.unit
    def test_filter_has_tenant_id(self):
        """Filter should include tenant_id."""
        filter = get_access_filter("member", "user123", "tenant456")
        assert filter.tenant_id == "tenant456"

    @pytest.mark.unit
    def test_member_requires_own_user(self):
        """Member filter should require own user for INTERNAL."""
        filter = get_access_filter("member", "user123", "tenant456")
        assert filter.require_own_user is True

    @pytest.mark.unit
    def test_admin_does_not_require_own_user(self):
        """Admin filter should not require own user."""
        filter = get_access_filter("admin", "admin1", "tenant456")
        assert filter.require_own_user is False


class TestBuildWeaviateFilter:
    """Test Weaviate filter building."""

    @pytest.mark.unit
    def test_weaviate_filter_has_privacy_operator(self):
        """Weaviate filter should filter by privacy tiers."""
        access = get_access_filter("member", "user123", "tenant456")
        wf = build_weaviate_filter(access)

        # Should have And operator with operands
        assert wf.get("operator") == "And" or "path" in wf

    @pytest.mark.unit
    def test_weaviate_filter_includes_tenant(self):
        """Weaviate filter should include tenant constraint."""
        access = get_access_filter("member", "user123", "tenant456")
        wf = build_weaviate_filter(access)

        # Check that tenant filter exists somewhere in the structure
        filter_str = str(wf)
        assert "tenant_id" in filter_str
        assert "tenant456" in filter_str


class TestBuildPostgresFilter:
    """Test PostgreSQL filter building."""

    @pytest.mark.unit
    def test_postgres_filter_has_tiers(self):
        """Postgres filter should have privacy_levels list."""
        access = get_access_filter("member", "user123", "tenant456")
        pf = build_postgres_filter(access)

        assert "privacy_levels" in pf
        assert "PUBLIC" in pf["privacy_levels"]

    @pytest.mark.unit
    def test_postgres_filter_has_tenant(self):
        """Postgres filter should have tenant_id."""
        access = get_access_filter("member", "user123", "tenant456")
        pf = build_postgres_filter(access)

        assert pf["tenant_id"] == "tenant456"

    @pytest.mark.unit
    def test_postgres_filter_member_has_user_id(self):
        """Member filter should include user_id constraint."""
        access = get_access_filter("member", "user123", "tenant456")
        pf = build_postgres_filter(access)

        assert pf.get("user_id") == "user123"
        assert pf.get("require_own_user") is True


class TestFilterResultsByAccess:
    """Test post-query filtering."""

    @pytest.mark.unit
    def test_allows_matching_tier(self):
        """Results with allowed tier should pass."""
        access = AccessFilter(
            privacy_tiers=["PUBLIC", "INTERNAL"],
            user_id="user123",
            tenant_id="tenant456",
            require_own_user=False
        )
        results = [
            {"id": "1", "privacy_level": "PUBLIC"},
            {"id": "2", "privacy_level": "INTERNAL"}
        ]
        filtered = filter_results_by_access(results, access)
        assert len(filtered) == 2

    @pytest.mark.unit
    def test_blocks_disallowed_tier(self):
        """Results with disallowed tier should be filtered."""
        access = AccessFilter(
            privacy_tiers=["PUBLIC"],
            user_id="user123",
            tenant_id="tenant456",
            require_own_user=False
        )
        results = [
            {"id": "1", "privacy_level": "PUBLIC"},
            {"id": "2", "privacy_level": "CONFIDENTIAL"}
        ]
        filtered = filter_results_by_access(results, access)
        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    @pytest.mark.unit
    def test_member_blocks_other_user_internal(self):
        """Member should not see other user's INTERNAL data."""
        access = AccessFilter(
            privacy_tiers=["PUBLIC", "INTERNAL"],
            user_id="user123",
            tenant_id="tenant456",
            require_own_user=True
        )
        results = [
            {"id": "1", "privacy_level": "PUBLIC", "user_id": "other"},
            {"id": "2", "privacy_level": "INTERNAL", "user_id": "other"},
            {"id": "3", "privacy_level": "INTERNAL", "user_id": "user123"}
        ]
        filtered = filter_results_by_access(results, access)
        assert len(filtered) == 2
        # Should have PUBLIC from other user and INTERNAL from own user
        ids = [r["id"] for r in filtered]
        assert "1" in ids
        assert "3" in ids
        assert "2" not in ids


class TestShouldSendToExternalApi:
    """Test external API send permissions."""

    @pytest.mark.unit
    def test_public_can_send_external(self):
        """PUBLIC content can be sent to external APIs."""
        assert should_send_to_external_api("PUBLIC") is True

    @pytest.mark.unit
    def test_internal_can_send_external(self):
        """INTERNAL content can be sent to external APIs."""
        assert should_send_to_external_api("INTERNAL") is True

    @pytest.mark.unit
    def test_confidential_blocked_external(self):
        """CONFIDENTIAL content must NOT be sent to external APIs."""
        assert should_send_to_external_api("CONFIDENTIAL") is False

    @pytest.mark.unit
    def test_local_only_blocked_external(self):
        """LOCAL_ONLY content must NEVER be sent to external APIs."""
        assert should_send_to_external_api("LOCAL_ONLY") is False


class TestValidateWritePermission:
    """Test write permission validation."""

    @pytest.mark.unit
    def test_admin_can_write_anything(self):
        """Admin can write to any tier for any user."""
        assert validate_write_permission("admin", "CONFIDENTIAL", "other", "admin1") is True
        assert validate_write_permission("admin", "INTERNAL", "other", "admin1") is True
        assert validate_write_permission("admin", "PUBLIC", "other", "admin1") is True

    @pytest.mark.unit
    def test_member_can_write_own_internal(self):
        """Member can write INTERNAL for themselves."""
        assert validate_write_permission("member", "INTERNAL", "user123", "user123") is True

    @pytest.mark.unit
    def test_member_can_write_own_public(self):
        """Member can write PUBLIC for themselves."""
        assert validate_write_permission("member", "PUBLIC", "user123", "user123") is True

    @pytest.mark.unit
    def test_member_cannot_write_confidential(self):
        """Member cannot write CONFIDENTIAL."""
        assert validate_write_permission("member", "CONFIDENTIAL", "user123", "user123") is False

    @pytest.mark.unit
    def test_member_cannot_write_for_others(self):
        """Member cannot write for other users."""
        assert validate_write_permission("member", "INTERNAL", "other", "user123") is False

    @pytest.mark.unit
    def test_public_cannot_write(self):
        """Public role cannot write anything."""
        assert validate_write_permission("public", "PUBLIC", "user123", "user123") is False
