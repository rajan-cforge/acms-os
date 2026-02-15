"""Unit tests for authentication endpoints.

Sprint 3 Day 11-12: Login Screen + Role Badge UI

Tests cover:
1. User registration
2. User login
3. Token refresh
4. Current user info
5. Default user creation
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.auth.simple_auth import SimpleAuth, TokenPair, UserContext, AuthError


class TestSimpleAuth:
    """Tests for SimpleAuth service."""

    def test_init_with_secret_key(self):
        """Should initialize with provided secret key."""
        auth = SimpleAuth(secret_key="test-secret-key")
        assert auth.secret_key == "test-secret-key"

    def test_init_without_secret_key(self):
        """Should generate random key if not provided."""
        auth = SimpleAuth()
        assert auth.secret_key is not None
        assert len(auth.secret_key) > 0

    def test_hash_password(self):
        """Should hash password."""
        auth = SimpleAuth()
        password = "mypassword123"
        hashed = auth.hash_password(password)

        # Hash should be different from original
        assert hashed != password
        # Hash should be non-empty
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Should verify correct password."""
        auth = SimpleAuth()
        password = "mypassword123"
        hashed = auth.hash_password(password)

        assert auth.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Should reject incorrect password."""
        auth = SimpleAuth()
        password = "mypassword123"
        hashed = auth.hash_password(password)

        assert auth.verify_password("wrongpassword", hashed) is False

    def test_create_tokens(self):
        """Should create access and refresh tokens."""
        auth = SimpleAuth()
        tokens = auth.create_tokens(
            user_id="user-123",
            role="member",
            tenant_id="tenant-1",
            email="test@example.com"
        )

        assert isinstance(tokens, TokenPair)
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "Bearer"
        assert tokens.expires_in > 0

    def test_validate_access_token(self):
        """Should validate access token and return user context."""
        auth = SimpleAuth()
        tokens = auth.create_tokens(
            user_id="user-123",
            role="member",
            tenant_id="tenant-1",
            email="test@example.com"
        )

        user_ctx = auth.validate_token(tokens.access_token)

        assert isinstance(user_ctx, UserContext)
        assert user_ctx.user_id == "user-123"
        assert user_ctx.role == "member"
        assert user_ctx.tenant_id == "tenant-1"
        assert user_ctx.email == "test@example.com"

    def test_validate_refresh_token(self):
        """Should validate refresh token."""
        auth = SimpleAuth()
        tokens = auth.create_tokens(
            user_id="user-123",
            role="admin",
            tenant_id="tenant-1"
        )

        user_ctx = auth.validate_token(tokens.refresh_token, token_type="refresh")

        assert user_ctx.user_id == "user-123"
        assert user_ctx.role == "admin"

    def test_validate_token_wrong_type(self):
        """Should reject token with wrong type."""
        auth = SimpleAuth()
        tokens = auth.create_tokens(
            user_id="user-123",
            role="member",
            tenant_id="tenant-1"
        )

        # Try to use refresh token as access token
        with pytest.raises(AuthError) as exc:
            auth.validate_token(tokens.refresh_token, token_type="access")

        assert "invalid token type" in str(exc.value).lower()

    def test_validate_invalid_token(self):
        """Should reject invalid token."""
        auth = SimpleAuth()

        with pytest.raises(AuthError):
            auth.validate_token("invalid-token")

    def test_refresh_access_token(self):
        """Should create new tokens from refresh token."""
        auth = SimpleAuth()
        original_tokens = auth.create_tokens(
            user_id="user-123",
            role="member",
            tenant_id="tenant-1"
        )

        new_tokens = auth.refresh_access_token(original_tokens.refresh_token)

        # New tokens should be valid
        assert new_tokens.access_token is not None
        assert new_tokens.refresh_token is not None

        # New access token should be valid and contain same user info
        user_ctx = auth.validate_token(new_tokens.access_token)
        assert user_ctx.user_id == "user-123"
        assert user_ctx.role == "member"
        assert user_ctx.tenant_id == "tenant-1"

    def test_token_contains_all_claims(self):
        """Token should contain all required claims."""
        auth = SimpleAuth()
        tokens = auth.create_tokens(
            user_id="user-123",
            role="admin",
            tenant_id="tenant-1",
            email="admin@example.com"
        )

        user_ctx = auth.validate_token(tokens.access_token)

        assert user_ctx.user_id == "user-123"
        assert user_ctx.role == "admin"
        assert user_ctx.tenant_id == "tenant-1"
        assert user_ctx.email == "admin@example.com"
        assert user_ctx.exp is not None


class TestUserContext:
    """Tests for UserContext dataclass."""

    def test_to_dict(self):
        """Should convert to dictionary."""
        ctx = UserContext(
            user_id="user-123",
            role="member",
            tenant_id="tenant-1",
            email="test@example.com"
        )

        d = ctx.to_dict()

        assert d["user_id"] == "user-123"
        assert d["role"] == "member"
        assert d["tenant_id"] == "tenant-1"
        assert d["email"] == "test@example.com"


class TestAuthError:
    """Tests for AuthError exception."""

    def test_auth_error_message(self):
        """Should contain message and code."""
        error = AuthError("Token expired", code="token_expired")

        assert error.message == "Token expired"
        assert error.code == "token_expired"
        assert str(error) == "Token expired"

    def test_auth_error_default_code(self):
        """Should have default code."""
        error = AuthError("Something went wrong")

        assert error.code == "auth_error"


class TestTokenPair:
    """Tests for TokenPair dataclass."""

    def test_token_pair_defaults(self):
        """Should have sensible defaults."""
        pair = TokenPair(
            access_token="access123",
            refresh_token="refresh456"
        )

        assert pair.access_token == "access123"
        assert pair.refresh_token == "refresh456"
        assert pair.token_type == "Bearer"
        assert pair.expires_in == 3600


class TestRBACRoles:
    """Tests for role-based access."""

    def test_public_role_token(self):
        """Should create token with public role."""
        auth = SimpleAuth()
        tokens = auth.create_tokens(
            user_id="user-1",
            role="public",
            tenant_id="tenant-1"
        )

        user_ctx = auth.validate_token(tokens.access_token)
        assert user_ctx.role == "public"

    def test_member_role_token(self):
        """Should create token with member role."""
        auth = SimpleAuth()
        tokens = auth.create_tokens(
            user_id="user-1",
            role="member",
            tenant_id="tenant-1"
        )

        user_ctx = auth.validate_token(tokens.access_token)
        assert user_ctx.role == "member"

    def test_admin_role_token(self):
        """Should create token with admin role."""
        auth = SimpleAuth()
        tokens = auth.create_tokens(
            user_id="user-1",
            role="admin",
            tenant_id="tenant-1"
        )

        user_ctx = auth.validate_token(tokens.access_token)
        assert user_ctx.role == "admin"


class TestPasswordHashing:
    """Tests for password hashing security."""

    def test_different_passwords_different_hashes(self):
        """Different passwords should produce different hashes."""
        auth = SimpleAuth()

        hash1 = auth.hash_password("password1")
        hash2 = auth.hash_password("password2")

        assert hash1 != hash2

    def test_same_password_different_hashes(self):
        """Same password should produce different hashes (due to salt)."""
        auth = SimpleAuth()

        hash1 = auth.hash_password("samepassword")
        hash2 = auth.hash_password("samepassword")

        # With proper salting, same password produces different hashes
        assert hash1 != hash2

    def test_empty_password_rejected(self):
        """Empty password should still hash (but verification fails)."""
        auth = SimpleAuth()

        # Empty password should hash without error
        hash_empty = auth.hash_password("")

        # But verification with non-empty should fail
        assert auth.verify_password("password", hash_empty) is False


class TestTokenExpiration:
    """Tests for token expiration handling."""

    def test_access_token_has_expiration(self):
        """Access token should have expiration."""
        auth = SimpleAuth()
        tokens = auth.create_tokens(
            user_id="user-1",
            role="member",
            tenant_id="tenant-1"
        )

        user_ctx = auth.validate_token(tokens.access_token)
        assert user_ctx.exp is not None

    def test_expired_token_rejected(self):
        """Expired token should be rejected."""
        from datetime import timedelta

        # Create auth with very short token lifetime
        auth = SimpleAuth(
            access_token_ttl=timedelta(seconds=-1)  # Already expired
        )

        tokens = auth.create_tokens(
            user_id="user-1",
            role="member",
            tenant_id="tenant-1"
        )

        with pytest.raises(AuthError) as exc:
            auth.validate_token(tokens.access_token)

        assert "expired" in str(exc.value).lower()


class TestGetAuthService:
    """Tests for auth service singleton."""

    def test_get_auth_service_returns_instance(self):
        """Should return SimpleAuth instance."""
        from src.auth.simple_auth import get_auth_service

        auth = get_auth_service()
        assert isinstance(auth, SimpleAuth)

    def test_get_auth_service_singleton(self):
        """Should return same instance."""
        from src.auth.simple_auth import get_auth_service

        auth1 = get_auth_service()
        auth2 = get_auth_service()

        assert auth1 is auth2
