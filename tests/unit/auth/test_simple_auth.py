"""Unit tests for SimpleAuth authentication service.

Tests verify that:
1. Passwords are hashed securely
2. Password verification works correctly
3. JWT tokens are generated with correct claims
4. Token validation extracts user context
5. Expired tokens are rejected
6. Invalid tokens are rejected

TDD spec from ACMS_Combined_Code_Review_Refactor_TDD_Spec.md
"""

import pytest
import time
from datetime import timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.auth.simple_auth import SimpleAuth, TokenPair, UserContext, AuthError


@pytest.fixture
def auth():
    """Get SimpleAuth instance with known secret."""
    return SimpleAuth(
        secret_key="test-secret-key-for-testing",
        access_token_ttl=timedelta(hours=1),
        refresh_token_ttl=timedelta(days=7)
    )


class TestPasswordHashing:
    """Test password hashing functionality."""

    @pytest.mark.unit
    def test_hash_password_returns_string(self, auth):
        """hash_password should return a string."""
        hashed = auth.hash_password("test_password")
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    @pytest.mark.unit
    def test_hash_password_is_not_plain(self, auth):
        """Hashed password should not be the plain password."""
        password = "test_password"
        hashed = auth.hash_password(password)
        assert hashed != password

    @pytest.mark.unit
    def test_hash_password_is_deterministic_argon2(self, auth):
        """Same password should produce verifiable hash."""
        password = "test_password"
        hashed = auth.hash_password(password)
        # Verify works even though hash contains random salt
        assert auth.verify_password(password, hashed)

    @pytest.mark.unit
    def test_different_passwords_different_hashes(self, auth):
        """Different passwords should produce different hashes."""
        hash1 = auth.hash_password("password1")
        hash2 = auth.hash_password("password2")
        assert hash1 != hash2


class TestPasswordVerification:
    """Test password verification functionality."""

    @pytest.mark.unit
    def test_verify_correct_password(self, auth):
        """Correct password should verify."""
        password = "correct_password"
        hashed = auth.hash_password(password)
        assert auth.verify_password(password, hashed) is True

    @pytest.mark.unit
    def test_reject_wrong_password(self, auth):
        """Wrong password should not verify."""
        hashed = auth.hash_password("correct_password")
        assert auth.verify_password("wrong_password", hashed) is False

    @pytest.mark.unit
    def test_reject_empty_password(self, auth):
        """Empty password should not verify against real hash."""
        hashed = auth.hash_password("real_password")
        assert auth.verify_password("", hashed) is False

    @pytest.mark.unit
    def test_reject_invalid_hash_format(self, auth):
        """Invalid hash format should not verify."""
        assert auth.verify_password("password", "invalid_hash") is False


class TestTokenGeneration:
    """Test JWT token generation."""

    @pytest.mark.unit
    def test_create_tokens_returns_pair(self, auth):
        """create_tokens should return TokenPair."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )
        assert isinstance(tokens, TokenPair)
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "Bearer"

    @pytest.mark.unit
    def test_access_token_is_valid_jwt(self, auth):
        """Access token should be valid JWT format."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )
        # JWT has 3 parts separated by dots
        parts = tokens.access_token.split('.')
        assert len(parts) == 3

    @pytest.mark.unit
    def test_tokens_include_user_id(self, auth):
        """Tokens should contain user_id in claims."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )
        user_ctx = auth.validate_token(tokens.access_token)
        assert user_ctx.user_id == "user123"

    @pytest.mark.unit
    def test_tokens_include_role(self, auth):
        """Tokens should contain role in claims."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="admin",
            tenant_id="tenant456"
        )
        user_ctx = auth.validate_token(tokens.access_token)
        assert user_ctx.role == "admin"

    @pytest.mark.unit
    def test_tokens_include_tenant_id(self, auth):
        """Tokens should contain tenant_id in claims."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )
        user_ctx = auth.validate_token(tokens.access_token)
        assert user_ctx.tenant_id == "tenant456"

    @pytest.mark.unit
    def test_tokens_include_optional_email(self, auth):
        """Tokens should include email if provided."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456",
            email="user@example.com"
        )
        user_ctx = auth.validate_token(tokens.access_token)
        assert user_ctx.email == "user@example.com"


class TestTokenValidation:
    """Test JWT token validation."""

    @pytest.mark.unit
    def test_validate_valid_token(self, auth):
        """Valid token should validate successfully."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )
        user_ctx = auth.validate_token(tokens.access_token)
        assert isinstance(user_ctx, UserContext)
        assert user_ctx.user_id == "user123"

    @pytest.mark.unit
    def test_validate_returns_user_context(self, auth):
        """validate_token should return UserContext."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )
        user_ctx = auth.validate_token(tokens.access_token)
        assert isinstance(user_ctx, UserContext)

    @pytest.mark.unit
    def test_reject_invalid_token(self, auth):
        """Invalid token should raise AuthError."""
        with pytest.raises(AuthError) as exc_info:
            auth.validate_token("invalid.token.here")
        assert exc_info.value.code in ["invalid_token", "invalid_signature"]

    @pytest.mark.unit
    def test_reject_tampered_token(self, auth):
        """Tampered token should raise AuthError."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )
        # Tamper with the token
        parts = tokens.access_token.split('.')
        tampered = parts[0] + '.' + parts[1] + 'tampered.' + parts[2]

        with pytest.raises(AuthError):
            auth.validate_token(tampered)

    @pytest.mark.unit
    def test_reject_wrong_secret_token(self):
        """Token from different secret should fail."""
        auth1 = SimpleAuth(secret_key="secret1")
        auth2 = SimpleAuth(secret_key="secret2")

        tokens = auth1.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )

        with pytest.raises(AuthError):
            auth2.validate_token(tokens.access_token)


class TestTokenExpiration:
    """Test token expiration handling."""

    @pytest.mark.unit
    def test_expired_token_rejected(self):
        """Expired token should raise AuthError."""
        # Create auth with very short TTL
        auth = SimpleAuth(
            secret_key="test-secret",
            access_token_ttl=timedelta(milliseconds=1)
        )

        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )

        # Wait for token to expire
        time.sleep(0.01)

        with pytest.raises(AuthError) as exc_info:
            auth.validate_token(tokens.access_token)
        assert exc_info.value.code == "token_expired"

    @pytest.mark.unit
    def test_valid_token_not_expired(self, auth):
        """Valid token within TTL should not be rejected."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )
        # Should not raise
        user_ctx = auth.validate_token(tokens.access_token)
        assert user_ctx.user_id == "user123"


class TestRefreshToken:
    """Test refresh token functionality."""

    @pytest.mark.unit
    def test_refresh_token_valid(self, auth):
        """Refresh token should be valid."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )
        user_ctx = auth.validate_token(tokens.refresh_token, token_type="refresh")
        assert user_ctx.user_id == "user123"

    @pytest.mark.unit
    def test_refresh_access_token(self, auth):
        """Should be able to get new tokens using refresh token."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )

        new_tokens = auth.refresh_access_token(tokens.refresh_token)

        assert isinstance(new_tokens, TokenPair)
        # Verify the new tokens are valid and contain same user info
        user_ctx = auth.validate_token(new_tokens.access_token)
        assert user_ctx.user_id == "user123"
        assert user_ctx.role == "member"

    @pytest.mark.unit
    def test_cannot_use_access_as_refresh(self, auth):
        """Access token should not work as refresh token."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )

        with pytest.raises(AuthError) as exc_info:
            auth.validate_token(tokens.access_token, token_type="refresh")
        assert exc_info.value.code == "invalid_token_type"


class TestUserContext:
    """Test UserContext dataclass."""

    @pytest.mark.unit
    def test_user_context_to_dict(self, auth):
        """to_dict should return dict with user info."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="admin",
            tenant_id="tenant456",
            email="user@example.com"
        )
        user_ctx = auth.validate_token(tokens.access_token)
        d = user_ctx.to_dict()

        assert d["user_id"] == "user123"
        assert d["role"] == "admin"
        assert d["tenant_id"] == "tenant456"
        assert d["email"] == "user@example.com"

    @pytest.mark.unit
    def test_user_context_has_expiration(self, auth):
        """UserContext should include expiration time."""
        tokens = auth.create_tokens(
            user_id="user123",
            role="member",
            tenant_id="tenant456"
        )
        user_ctx = auth.validate_token(tokens.access_token)
        assert user_ctx.exp is not None
