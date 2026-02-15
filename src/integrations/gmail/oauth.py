# src/integrations/gmail/oauth.py
"""
OAuth2 Token Management with Encryption at Rest

Security Model:
- Tokens encrypted using Fernet symmetric encryption
- Key derived via PBKDF2 from master secret
- Master secret from env var or machine-derived fallback
- Refresh tokens proactively before expiry
- All operations logged to audit trail
"""

import os
import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from .exceptions import OAuthError, TokenExpiredError, TokenRefreshError

logger = logging.getLogger(__name__)

# Constants
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"
TOKEN_REFRESH_BUFFER_MINUTES = 5  # Refresh 5 min before expiry


@dataclass
class OAuthTokens:
    """Decrypted OAuth tokens with metadata."""
    access_token: str
    refresh_token: str
    expiry: datetime
    scopes: List[str]
    email: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        """Check if token is expired or about to expire."""
        buffer = timedelta(minutes=TOKEN_REFRESH_BUFFER_MINUTES)
        now = datetime.now(timezone.utc)
        expiry = self.expiry if self.expiry.tzinfo else self.expiry.replace(tzinfo=timezone.utc)
        return now >= (expiry - buffer)


class TokenEncryption:
    """
    Encrypts OAuth tokens at rest using Fernet symmetric encryption.

    Key Derivation:
    - Uses PBKDF2 with SHA256
    - 100,000 iterations (OWASP recommendation)
    - Static salt for deterministic key derivation
    """

    # Static salt - okay because master secret is unique per install
    SALT = b'acms-oauth-tokens-v1'
    ITERATIONS = 100_000

    def __init__(self, master_secret: Optional[str] = None):
        """
        Initialize encryption with master secret.

        Args:
            master_secret: Secret key for encryption. If None, uses
                          ACMS_TOKEN_SECRET env var or machine-derived fallback.
        """
        self.master_secret = master_secret or self._get_master_secret()
        self._fernet = self._create_fernet()

    def _get_master_secret(self) -> str:
        """Get master secret from env or derive from machine."""
        # Priority 1: Environment variable
        secret = os.getenv("ACMS_TOKEN_SECRET")
        if secret:
            return secret

        # Priority 2: Machine-derived (fallback, less secure)
        logger.warning(
            "ACMS_TOKEN_SECRET not set. Using machine-derived secret. "
            "Set ACMS_TOKEN_SECRET in production for better security."
        )
        import uuid
        machine_id = str(uuid.getnode())  # MAC address based
        return f"acms-machine-{machine_id}-oauth-v1"

    def _create_fernet(self) -> Fernet:
        """Create Fernet instance from master secret using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.SALT,
            iterations=self.ITERATIONS,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(self.master_secret.encode())
        )
        return Fernet(key)

    def encrypt(self, plaintext: str) -> str:
        """Encrypt a string value."""
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt a string value."""
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except InvalidToken:
            raise OAuthError("Failed to decrypt token - key may have changed")


class GoogleOAuthClient:
    """
    Google OAuth2 Client with token management.

    Handles:
    - Authorization URL generation
    - Token exchange (code → tokens)
    - Token refresh
    - Secure storage via TokenEncryption
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        redirect_uri: Optional[str] = None,
        db_pool=None,  # asyncpg pool
    ):
        self.client_id = client_id or os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = redirect_uri or os.getenv(
            "GOOGLE_REDIRECT_URI",
            "http://localhost:40080/oauth/callback"
        )
        self.db_pool = db_pool
        self.encryption = TokenEncryption()

        if not self.client_id or not self.client_secret:
            raise OAuthError(
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set"
            )

    def get_authorization_url(
        self,
        scopes: List[str],
        state: Optional[str] = None,
    ) -> str:
        """
        Generate Google OAuth authorization URL.

        Args:
            scopes: List of OAuth scopes to request
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(scopes),
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",        # Always show consent for refresh token
        }
        if state:
            params["state"] = state

        return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"

    async def exchange_code(
        self,
        code: str,
        user_id: str = "default",
    ) -> OAuthTokens:
        """
        Exchange authorization code for tokens.

        Args:
            code: Authorization code from OAuth callback
            user_id: User identifier for token storage

        Returns:
            OAuthTokens with access and refresh tokens
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "code": code,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )

        if response.status_code != 200:
            logger.error(f"Token exchange failed: {response.text}")
            raise OAuthError(f"Token exchange failed: {response.status_code}")

        data = response.json()

        # Calculate expiry
        expires_in = data.get("expires_in", 3600)
        expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Get user info
        email = await self._get_user_email(data["access_token"])

        tokens = OAuthTokens(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            expiry=expiry,
            scopes=data.get("scope", "").split(),
            email=email,
        )

        # Store encrypted tokens
        if self.db_pool:
            await self._store_tokens(tokens, user_id)

        # Audit log
        try:
            from src.audit.logger import get_audit_logger
            audit = get_audit_logger()
            await audit.log_ingress(
                source="oauth",
                operation="token_exchange",
                item_count=1,
                metadata={
                    "provider": "google",
                    "email": email,
                    "scopes": tokens.scopes,
                    # Never log actual tokens!
                }
            )
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")

        return tokens

    async def get_valid_token(self, user_id: str = "default") -> str:
        """
        Get a valid access token, refreshing if necessary.

        Args:
            user_id: User identifier

        Returns:
            Valid access token string

        Raises:
            OAuthError: If no tokens or refresh fails
        """
        tokens = await self._load_tokens(user_id)

        if tokens is None:
            raise OAuthError("No tokens found - user needs to authenticate")

        if tokens.is_expired:
            logger.info("Access token expired, refreshing...")
            tokens = await self._refresh_tokens(tokens, user_id)

        return tokens.access_token

    async def _refresh_tokens(
        self,
        tokens: OAuthTokens,
        user_id: str,
    ) -> OAuthTokens:
        """Refresh expired tokens."""
        if not tokens.refresh_token:
            raise TokenRefreshError("No refresh token available")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": tokens.refresh_token,
                    "grant_type": "refresh_token",
                },
            )

        if response.status_code != 200:
            logger.error(f"Token refresh failed: {response.text}")
            raise TokenRefreshError(
                "Token refresh failed - user may need to re-authenticate"
            )

        data = response.json()

        expires_in = data.get("expires_in", 3600)
        expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        new_tokens = OAuthTokens(
            access_token=data["access_token"],
            # Refresh token may not be returned; keep existing
            refresh_token=data.get("refresh_token", tokens.refresh_token),
            expiry=expiry,
            scopes=data.get("scope", "").split() or tokens.scopes,
            email=tokens.email,
        )

        # Update stored tokens
        if self.db_pool:
            await self._store_tokens(new_tokens, user_id)

        logger.info("Successfully refreshed OAuth tokens")
        return new_tokens

    async def _get_user_email(self, access_token: str) -> Optional[str]:
        """Get user email from Google userinfo endpoint."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    GOOGLE_USERINFO_URL,
                    headers={"Authorization": f"Bearer {access_token}"},
                )
            if response.status_code == 200:
                return response.json().get("email")
        except Exception as e:
            logger.warning(f"Failed to get user email: {e}")
        return None

    async def _store_tokens(
        self,
        tokens: OAuthTokens,
        user_id: str,
    ) -> None:
        """Store encrypted tokens in database."""
        encrypted_access = self.encryption.encrypt(tokens.access_token)
        encrypted_refresh = self.encryption.encrypt(tokens.refresh_token)

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO oauth_tokens (
                    provider, user_id,
                    access_token_encrypted, refresh_token_encrypted,
                    token_expiry, scopes, email, last_used_at
                ) VALUES (
                    'google', $1, $2, $3, $4, $5, $6, NOW()
                )
                ON CONFLICT (provider, user_id) DO UPDATE SET
                    access_token_encrypted = EXCLUDED.access_token_encrypted,
                    refresh_token_encrypted = EXCLUDED.refresh_token_encrypted,
                    token_expiry = EXCLUDED.token_expiry,
                    scopes = EXCLUDED.scopes,
                    email = EXCLUDED.email,
                    last_used_at = NOW(),
                    updated_at = NOW()
            """,
                user_id,
                encrypted_access,
                encrypted_refresh,
                tokens.expiry,
                tokens.scopes,
                tokens.email,
            )

    async def _load_tokens(self, user_id: str) -> Optional[OAuthTokens]:
        """Load and decrypt tokens from database."""
        if not self.db_pool:
            return None

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    access_token_encrypted,
                    refresh_token_encrypted,
                    token_expiry,
                    scopes,
                    email
                FROM oauth_tokens
                WHERE provider = 'google' AND user_id = $1
            """, user_id)

        if not row:
            return None

        try:
            return OAuthTokens(
                access_token=self.encryption.decrypt(row["access_token_encrypted"]),
                refresh_token=self.encryption.decrypt(row["refresh_token_encrypted"]),
                expiry=row["token_expiry"],
                scopes=list(row["scopes"]) if row["scopes"] else [],
                email=row["email"],
            )
        except OAuthError:
            logger.error("Failed to decrypt stored tokens")
            return None

    async def revoke_tokens(self, user_id: str = "default") -> bool:
        """Revoke tokens and remove from storage."""
        tokens = await self._load_tokens(user_id)

        if tokens:
            # Revoke with Google
            try:
                async with httpx.AsyncClient() as client:
                    await client.post(
                        "https://oauth2.googleapis.com/revoke",
                        params={"token": tokens.access_token},
                    )
            except Exception as e:
                logger.warning(f"Token revocation failed: {e}")

        # Remove from database regardless
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    DELETE FROM oauth_tokens
                    WHERE provider = 'google' AND user_id = $1
                """, user_id)

        logger.info(f"Revoked tokens for user {user_id}")
        return True
