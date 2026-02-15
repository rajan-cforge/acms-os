"""Unit tests for RBAC access filters.

Tests the canonical RBAC filter contract defined in PRD:
- PUBLIC: only privacy_level == PUBLIC
- MEMBER: PUBLIC + INTERNAL where user_id == current_user
- ADMIN: ALL + cross-user allowed when scope=org

Run with: pytest tests/unit/intelligence/test_rbac_filters.py -v
"""

import pytest
from src.security.access_filter import (
    Role,
    PrivacyLevel,
    AccessFilter,
    UserContext,
    build_access_filter,
    allowed_privacy_levels,
    require_admin_for_org_scope,
    build_member_or_filter,
)


class TestUserContext:
    """Tests for UserContext dataclass."""

    def test_create_with_role_enum(self):
        """UserContext works with Role enum."""
        ctx = UserContext(user_id="u1", role=Role.MEMBER, tenant_id="t1")
        assert ctx.role == Role.MEMBER
        assert ctx.user_id == "u1"
        assert ctx.tenant_id == "t1"

    def test_create_with_role_string(self):
        """UserContext converts string role to enum."""
        ctx = UserContext(user_id="u1", role="member", tenant_id="t1")
        assert ctx.role == Role.MEMBER

    def test_default_tenant(self):
        """UserContext defaults to 'default' tenant."""
        ctx = UserContext(user_id="u1", role=Role.PUBLIC)
        assert ctx.tenant_id == "default"


class TestAllowedPrivacyLevels:
    """Tests for privacy level access by role."""

    def test_public_only_public(self):
        """PUBLIC role only sees PUBLIC privacy level."""
        levels = allowed_privacy_levels(Role.PUBLIC)
        assert levels == [PrivacyLevel.PUBLIC]
        assert PrivacyLevel.INTERNAL not in levels
        assert PrivacyLevel.CONFIDENTIAL not in levels
        assert PrivacyLevel.LOCAL_ONLY not in levels

    def test_member_public_and_internal(self):
        """MEMBER role sees PUBLIC and INTERNAL."""
        levels = allowed_privacy_levels(Role.MEMBER)
        assert PrivacyLevel.PUBLIC in levels
        assert PrivacyLevel.INTERNAL in levels
        assert PrivacyLevel.CONFIDENTIAL not in levels
        assert PrivacyLevel.LOCAL_ONLY not in levels

    def test_admin_all_except_local_only(self):
        """ADMIN role sees PUBLIC, INTERNAL, CONFIDENTIAL (not LOCAL_ONLY)."""
        levels = allowed_privacy_levels(Role.ADMIN)
        assert PrivacyLevel.PUBLIC in levels
        assert PrivacyLevel.INTERNAL in levels
        assert PrivacyLevel.CONFIDENTIAL in levels
        assert PrivacyLevel.LOCAL_ONLY not in levels  # Never leaves client


class TestBuildAccessFilter:
    """Tests for build_access_filter function."""

    def test_public_only_sees_public(self):
        """PUBLIC role can only access PUBLIC privacy level."""
        ctx = UserContext(user_id="u1", role=Role.PUBLIC, tenant_id="t1")
        f = build_access_filter(ctx, scope="org")

        assert f.allowed_privacy_levels == [PrivacyLevel.PUBLIC]
        assert f.user_id_filter is None  # No user filter for public
        assert f.tenant_id == "t1"
        assert f.cross_user_allowed is False

    def test_member_internal_scoped_to_self(self):
        """MEMBER can see PUBLIC + own INTERNAL only."""
        ctx = UserContext(user_id="u1", role=Role.MEMBER, tenant_id="t1")
        f = build_access_filter(ctx, scope="user")

        assert PrivacyLevel.PUBLIC in f.allowed_privacy_levels
        assert PrivacyLevel.INTERNAL in f.allowed_privacy_levels
        assert PrivacyLevel.CONFIDENTIAL not in f.allowed_privacy_levels

        # INTERNAL must be scoped to user
        assert f.user_id_filter == "u1"
        assert f.cross_user_allowed is False

    def test_member_scope_org_still_filtered(self):
        """MEMBER with scope=org is still filtered to own data."""
        ctx = UserContext(user_id="u1", role=Role.MEMBER, tenant_id="t1")
        f = build_access_filter(ctx, scope="org")

        # Member doesn't get cross-user access even with org scope
        assert f.user_id_filter == "u1"
        assert f.cross_user_allowed is False

    def test_admin_user_scope(self):
        """ADMIN with scope=user sees own data only."""
        ctx = UserContext(user_id="admin1", role=Role.ADMIN, tenant_id="t1")
        f = build_access_filter(ctx, scope="user")

        assert PrivacyLevel.CONFIDENTIAL in f.allowed_privacy_levels
        assert f.user_id_filter == "admin1"  # Filtered to self
        assert f.cross_user_allowed is False

    def test_admin_org_scope(self):
        """ADMIN with scope=org sees all data within tenant."""
        ctx = UserContext(user_id="admin1", role=Role.ADMIN, tenant_id="t1")
        f = build_access_filter(ctx, scope="org")

        assert PrivacyLevel.CONFIDENTIAL in f.allowed_privacy_levels
        assert f.user_id_filter is None  # No user filter
        assert f.tenant_id == "t1"
        assert f.cross_user_allowed is True


class TestAccessFilterPostgres:
    """Tests for PostgreSQL WHERE clause generation."""

    def test_to_postgres_where_public(self):
        """PUBLIC role generates correct WHERE clause."""
        ctx = UserContext(user_id="u1", role=Role.PUBLIC, tenant_id="default")
        f = build_access_filter(ctx, scope="user")

        where = f.to_postgres_where()
        assert "tenant_id = 'default'" in where
        assert "privacy_level IN ('PUBLIC')" in where
        assert "user_id" not in where  # No user filter

    def test_to_postgres_where_member(self):
        """MEMBER role generates correct WHERE clause."""
        ctx = UserContext(user_id="user-123", role=Role.MEMBER, tenant_id="default")
        f = build_access_filter(ctx, scope="user")

        where = f.to_postgres_where()
        assert "tenant_id = 'default'" in where
        assert "'PUBLIC'" in where
        assert "'INTERNAL'" in where
        assert "user_id = 'user-123'" in where

    def test_to_postgres_where_with_alias(self):
        """PostgreSQL clause works with table alias."""
        ctx = UserContext(user_id="u1", role=Role.MEMBER, tenant_id="default")
        f = build_access_filter(ctx, scope="user")

        where = f.to_postgres_where(table_alias="qh")
        assert "qh.tenant_id" in where
        assert "qh.privacy_level" in where
        assert "qh.user_id" in where

    def test_to_postgres_params_safe(self):
        """Parameterized query prevents SQL injection."""
        ctx = UserContext(
            user_id="'; DROP TABLE users; --",  # SQL injection attempt
            role=Role.MEMBER,
            tenant_id="default"
        )
        f = build_access_filter(ctx, scope="user")

        clause, params = f.to_postgres_params()

        # Clause uses placeholders, not literal values
        assert ":user_id" in clause
        assert "DROP TABLE" not in clause

        # Params contain the raw (potentially dangerous) value
        # which will be properly escaped by the DB driver
        assert params["user_id"] == "'; DROP TABLE users; --"


class TestAccessFilterWeaviate:
    """Tests for Weaviate filter generation."""

    def test_to_weaviate_filter_public(self):
        """PUBLIC role generates correct Weaviate filter."""
        ctx = UserContext(user_id="u1", role=Role.PUBLIC, tenant_id="default")
        f = build_access_filter(ctx, scope="user")

        wf = f.to_weaviate_filter()

        # Should have tenant and privacy filters
        assert wf["operator"] == "And"
        operands = wf["operands"]

        tenant_filter = [o for o in operands if o.get("path") == ["tenant_id"]][0]
        assert tenant_filter["valueText"] == "default"

        privacy_filter = [o for o in operands if o.get("path") == ["privacy_level"]][0]
        assert privacy_filter["valueText"] == "PUBLIC"

    def test_to_weaviate_filter_admin_org(self):
        """ADMIN org scope generates correct Weaviate filter."""
        ctx = UserContext(user_id="admin1", role=Role.ADMIN, tenant_id="default")
        f = build_access_filter(ctx, scope="org")

        wf = f.to_weaviate_filter()

        # Should have multiple privacy levels
        privacy_filter = None
        for operand in wf.get("operands", [wf]):
            if operand.get("path") == ["privacy_level"]:
                privacy_filter = operand
                break

        assert privacy_filter is not None
        # Should use ContainsAny for multiple values
        if "valueTextArray" in privacy_filter:
            assert "PUBLIC" in privacy_filter["valueTextArray"]
            assert "CONFIDENTIAL" in privacy_filter["valueTextArray"]


class TestRequireAdminForOrgScope:
    """Tests for admin validation on org scope."""

    def test_admin_allowed_org_scope(self):
        """Admin can use org scope."""
        ctx = UserContext(user_id="admin1", role=Role.ADMIN, tenant_id="default")
        # Should not raise
        require_admin_for_org_scope(ctx, "org")

    def test_member_denied_org_scope(self):
        """Member cannot use org scope."""
        ctx = UserContext(user_id="u1", role=Role.MEMBER, tenant_id="default")
        with pytest.raises(PermissionError) as exc_info:
            require_admin_for_org_scope(ctx, "org")
        assert "admin role" in str(exc_info.value)

    def test_public_denied_org_scope(self):
        """Public cannot use org scope."""
        ctx = UserContext(user_id="u1", role=Role.PUBLIC, tenant_id="default")
        with pytest.raises(PermissionError):
            require_admin_for_org_scope(ctx, "org")

    def test_user_scope_allowed_for_all(self):
        """User scope is allowed for all roles."""
        for role in [Role.PUBLIC, Role.MEMBER, Role.ADMIN]:
            ctx = UserContext(user_id="u1", role=role, tenant_id="default")
            # Should not raise
            require_admin_for_org_scope(ctx, "user")


class TestBuildMemberOrFilter:
    """Tests for MongoDB/Weaviate-style $or filter."""

    def test_member_or_filter_structure(self):
        """Member $or filter has correct structure."""
        ctx = UserContext(user_id="user-123", role=Role.MEMBER, tenant_id="default")
        f = build_member_or_filter(ctx)

        assert f["tenant_id"] == "default"
        assert "$or" in f

        or_clauses = f["$or"]
        assert len(or_clauses) == 2

        # First clause: PUBLIC for anyone
        assert or_clauses[0] == {"privacy_level": "PUBLIC"}

        # Second clause: INTERNAL only for this user
        assert or_clauses[1] == {
            "privacy_level": "INTERNAL",
            "user_id": "user-123"
        }


class TestAccessFilterRepr:
    """Tests for AccessFilter string representation."""

    def test_repr_readable(self):
        """AccessFilter repr is readable for debugging."""
        f = AccessFilter(
            allowed_privacy_levels=[PrivacyLevel.PUBLIC, PrivacyLevel.INTERNAL],
            user_id_filter="user-123",
            tenant_id="default",
            cross_user_allowed=False
        )

        repr_str = repr(f)
        assert "PUBLIC" in repr_str
        assert "INTERNAL" in repr_str
        assert "user-123" in repr_str
        assert "cross_user=False" in repr_str

    def test_to_dict_for_logging(self):
        """AccessFilter can be converted to dict for logging."""
        f = AccessFilter(
            allowed_privacy_levels=[PrivacyLevel.PUBLIC],
            user_id_filter=None,
            tenant_id="default",
            cross_user_allowed=False
        )

        d = f.to_dict()
        assert d["allowed_privacy_levels"] == ["PUBLIC"]
        assert d["user_id_filter"] is None
        assert d["tenant_id"] == "default"
