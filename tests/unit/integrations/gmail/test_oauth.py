# tests/unit/integrations/gmail/test_oauth.py
"""
TDD Tests for Gmail OAuth Implementation

Write these tests FIRST, then implement the OAuth module.
Following TDD: Red → Green → Refactor
"""

import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse, parse_qs


class TestTokenEncryption:
    """Test token encryption/decryption functionality."""

    def test_encryption_produces_different_output(self):
        """Encrypting same value should produce different ciphertext each time (Fernet adds randomness)."""
        from src.integrations.gmail.oauth import TokenEncryption

        encryption = TokenEncryption(master_secret="test-secret-key-12345")
        plaintext = "my-secret-token"

        encrypted1 = encryption.encrypt(plaintext)
        encrypted2 = encryption.encrypt(plaintext)

        # Fernet adds timestamp + random IV, so encryptions differ
        assert encrypted1 != encrypted2
        assert encrypted1 != plaintext
        assert encrypted2 != plaintext

    def test_decryption_returns_original(self):
        """Decrypting should return the original plaintext."""
        from src.integrations.gmail.oauth import TokenEncryption

        encryption = TokenEncryption(master_secret="test-secret-key-12345")
        original = "my-secret-access-token-xyz123"

        encrypted = encryption.encrypt(original)
        decrypted = encryption.decrypt(encrypted)

        assert decrypted == original

    def test_different_keys_cannot_decrypt(self):
        """Tokens encrypted with one key cannot be decrypted with another."""
        from src.integrations.gmail.oauth import TokenEncryption
        from src.integrations.gmail.exceptions import OAuthError

        encryption1 = TokenEncryption(master_secret="key-one")
        encryption2 = TokenEncryption(master_secret="key-two")

        encrypted = encryption1.encrypt("secret-data")

        with pytest.raises(OAuthError):
            encryption2.decrypt(encrypted)

    def test_uses_env_var_when_no_secret_provided(self):
        """Should use ACMS_TOKEN_SECRET env var when no secret provided."""
        from src.integrations.gmail.oauth import TokenEncryption

        with patch.dict(os.environ, {"ACMS_TOKEN_SECRET": "env-secret-key"}):
            encryption = TokenEncryption()
            assert encryption.master_secret == "env-secret-key"

    def test_falls_back_to_machine_derived_secret(self):
        """Should derive secret from machine ID when env var not set."""
        from src.integrations.gmail.oauth import TokenEncryption

        # Remove env var if set
        env_backup = os.environ.pop("ACMS_TOKEN_SECRET", None)
        try:
            encryption = TokenEncryption()
            assert "acms-machine-" in encryption.master_secret
        finally:
            if env_backup:
                os.environ["ACMS_TOKEN_SECRET"] = env_backup


class TestOAuthTokens:
    """Test OAuthTokens dataclass."""

    def test_is_expired_when_past_expiry(self):
        """Token should be expired when past expiry time."""
        from src.integrations.gmail.oauth import OAuthTokens

        tokens = OAuthTokens(
            access_token="token",
            refresh_token="refresh",
            expiry=datetime.utcnow() - timedelta(hours=1),
            scopes=["gmail.readonly"],
        )

        assert tokens.is_expired is True

    def test_is_expired_within_buffer(self):
        """Token should be expired when within refresh buffer (5 min)."""
        from src.integrations.gmail.oauth import OAuthTokens

        tokens = OAuthTokens(
            access_token="token",
            refresh_token="refresh",
            expiry=datetime.utcnow() + timedelta(minutes=3),  # Only 3 min left
            scopes=["gmail.readonly"],
        )

        assert tokens.is_expired is True

    def test_is_not_expired_with_time_remaining(self):
        """Token should not be expired when plenty of time remaining."""
        from src.integrations.gmail.oauth import OAuthTokens

        tokens = OAuthTokens(
            access_token="token",
            refresh_token="refresh",
            expiry=datetime.utcnow() + timedelta(hours=1),
            scopes=["gmail.readonly"],
        )

        assert tokens.is_expired is False


class TestGoogleOAuthClient:
    """Test GoogleOAuthClient functionality."""

    @pytest.fixture
    def mock_db_pool(self):
        """Create mock database pool."""
        pool = MagicMock()
        conn = AsyncMock()
        pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)
        return pool

    def test_raises_error_when_credentials_missing(self):
        """Should raise OAuthError when CLIENT_ID/SECRET not set."""
        from src.integrations.gmail.oauth import GoogleOAuthClient
        from src.integrations.gmail.exceptions import OAuthError

        # Clear env vars
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(OAuthError) as exc_info:
                GoogleOAuthClient()

            assert "GOOGLE_CLIENT_ID" in str(exc_info.value)

    def test_authorization_url_contains_required_params(self):
        """Authorization URL should contain all required OAuth params."""
        from src.integrations.gmail.oauth import GoogleOAuthClient

        with patch.dict(os.environ, {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-secret",
        }):
            client = GoogleOAuthClient()
            url = client.get_authorization_url(
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
                state="test-state-123",
            )

            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            assert "accounts.google.com" in parsed.netloc
            assert params["client_id"][0] == "test-client-id"
            assert params["response_type"][0] == "code"
            assert params["access_type"][0] == "offline"
            assert params["prompt"][0] == "consent"
            assert params["state"][0] == "test-state-123"
            assert "gmail.readonly" in params["scope"][0]

    def test_authorization_url_uses_correct_redirect_uri(self):
        """Authorization URL should use configured redirect URI."""
        from src.integrations.gmail.oauth import GoogleOAuthClient

        with patch.dict(os.environ, {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-secret",
            "GOOGLE_REDIRECT_URI": "http://localhost:40080/oauth/callback",
        }):
            client = GoogleOAuthClient()
            url = client.get_authorization_url(scopes=["gmail.readonly"])

            parsed = urlparse(url)
            params = parse_qs(parsed.query)

            assert params["redirect_uri"][0] == "http://localhost:40080/oauth/callback"

    @pytest.mark.asyncio
    async def test_exchange_code_stores_encrypted_tokens(self, mock_db_pool):
        """Token exchange should store encrypted tokens in database."""
        from src.integrations.gmail.oauth import GoogleOAuthClient

        with patch.dict(os.environ, {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-secret",
            "ACMS_TOKEN_SECRET": "test-encryption-key",
        }):
            client = GoogleOAuthClient(db_pool=mock_db_pool)

            # Mock the HTTP response
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "access_token": "new-access-token",
                "refresh_token": "new-refresh-token",
                "expires_in": 3600,
                "scope": "https://www.googleapis.com/auth/gmail.readonly",
            }

            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__ = AsyncMock(
                    return_value=MagicMock(post=AsyncMock(return_value=mock_response))
                )
                mock_client.return_value.__aexit__ = AsyncMock(return_value=None)

                # Mock user email fetch
                with patch.object(client, "_get_user_email", return_value="test@gmail.com"):
                    tokens = await client.exchange_code("auth-code-123")

            assert tokens.access_token == "new-access-token"
            assert tokens.email == "test@gmail.com"

    @pytest.mark.asyncio
    async def test_get_valid_token_returns_existing_when_not_expired(self, mock_db_pool):
        """Should return existing token when not expired."""
        from src.integrations.gmail.oauth import GoogleOAuthClient, OAuthTokens

        with patch.dict(os.environ, {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-secret",
            "ACMS_TOKEN_SECRET": "test-encryption-key",
        }):
            client = GoogleOAuthClient(db_pool=mock_db_pool)

            # Mock loading valid tokens
            valid_tokens = OAuthTokens(
                access_token="valid-token",
                refresh_token="refresh-token",
                expiry=datetime.utcnow() + timedelta(hours=1),
                scopes=["gmail.readonly"],
            )

            with patch.object(client, "_load_tokens", return_value=valid_tokens):
                token = await client.get_valid_token()

            assert token == "valid-token"

    @pytest.mark.asyncio
    async def test_get_valid_token_refreshes_when_expired(self, mock_db_pool):
        """Should refresh token when expired."""
        from src.integrations.gmail.oauth import GoogleOAuthClient, OAuthTokens

        with patch.dict(os.environ, {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-secret",
            "ACMS_TOKEN_SECRET": "test-encryption-key",
        }):
            client = GoogleOAuthClient(db_pool=mock_db_pool)

            # Mock loading expired tokens
            expired_tokens = OAuthTokens(
                access_token="expired-token",
                refresh_token="refresh-token",
                expiry=datetime.utcnow() - timedelta(hours=1),
                scopes=["gmail.readonly"],
            )

            # Mock refreshed tokens
            refreshed_tokens = OAuthTokens(
                access_token="new-valid-token",
                refresh_token="refresh-token",
                expiry=datetime.utcnow() + timedelta(hours=1),
                scopes=["gmail.readonly"],
            )

            with patch.object(client, "_load_tokens", return_value=expired_tokens):
                with patch.object(client, "_refresh_tokens", return_value=refreshed_tokens):
                    token = await client.get_valid_token()

            assert token == "new-valid-token"

    @pytest.mark.asyncio
    async def test_get_valid_token_raises_when_no_tokens(self, mock_db_pool):
        """Should raise OAuthError when no tokens stored."""
        from src.integrations.gmail.oauth import GoogleOAuthClient
        from src.integrations.gmail.exceptions import OAuthError

        with patch.dict(os.environ, {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-secret",
        }):
            client = GoogleOAuthClient(db_pool=mock_db_pool)

            with patch.object(client, "_load_tokens", return_value=None):
                with pytest.raises(OAuthError) as exc_info:
                    await client.get_valid_token()

                assert "authenticate" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_revoke_tokens_removes_from_database(self, mock_db_pool):
        """Revoke should remove tokens from database."""
        from src.integrations.gmail.oauth import GoogleOAuthClient, OAuthTokens

        with patch.dict(os.environ, {
            "GOOGLE_CLIENT_ID": "test-client-id",
            "GOOGLE_CLIENT_SECRET": "test-secret",
            "ACMS_TOKEN_SECRET": "test-encryption-key",
        }):
            client = GoogleOAuthClient(db_pool=mock_db_pool)

            tokens = OAuthTokens(
                access_token="token-to-revoke",
                refresh_token="refresh",
                expiry=datetime.utcnow() + timedelta(hours=1),
                scopes=["gmail.readonly"],
            )

            with patch.object(client, "_load_tokens", return_value=tokens):
                with patch("httpx.AsyncClient") as mock_http:
                    mock_http.return_value.__aenter__ = AsyncMock(
                        return_value=MagicMock(post=AsyncMock())
                    )
                    mock_http.return_value.__aexit__ = AsyncMock()

                    result = await client.revoke_tokens()

            assert result is True
            # Verify database delete was called
            conn = mock_db_pool.acquire.return_value.__aenter__.return_value
            conn.execute.assert_called()
