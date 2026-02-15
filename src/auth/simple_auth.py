"""Simple authentication service with password hashing and JWT tokens.

Provides:
- Argon2 password hashing (memory-hard, side-channel resistant)
- JWT access/refresh token generation
- Token validation and user extraction
- Role-based user context creation

Part of Sprint 1 Security Foundation (Days 4-5).
"""

import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from dataclasses import dataclass
import hashlib
import hmac
import base64
import json
import logging

# Use passlib for password hashing if available, otherwise fallback
try:
    from passlib.hash import argon2
    ARGON2_AVAILABLE = True
except ImportError:
    ARGON2_AVAILABLE = False

# Use PyJWT if available
try:
    import jwt
    JWT_AVAILABLE = True
except ImportError:
    JWT_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class TokenPair:
    """JWT access and refresh token pair."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # seconds


@dataclass
class UserContext:
    """Authenticated user context for requests."""
    user_id: str
    role: str
    tenant_id: str
    email: Optional[str] = None
    exp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "role": self.role,
            "tenant_id": self.tenant_id,
            "email": self.email
        }


class AuthError(Exception):
    """Authentication error."""
    def __init__(self, message: str, code: str = "auth_error"):
        super().__init__(message)
        self.message = message
        self.code = code


class SimpleAuth:
    """Simple authentication service.

    Provides password hashing and JWT token management.
    Uses Argon2 for passwords and HS256 for JWTs.

    Usage:
        auth = SimpleAuth(secret_key="your-secret-key")

        # Hash password for storage
        hashed = auth.hash_password("user_password")

        # Verify password
        if auth.verify_password("user_password", hashed):
            # Create tokens
            tokens = auth.create_tokens(user_id, role, tenant_id)

        # Validate token
        user_ctx = auth.validate_token(tokens.access_token)
    """

    def __init__(
        self,
        secret_key: Optional[str] = None,
        access_token_ttl: timedelta = timedelta(hours=1),
        refresh_token_ttl: timedelta = timedelta(days=7),
        algorithm: str = "HS256"
    ):
        """Initialize authentication service.

        Args:
            secret_key: JWT signing key. If not provided, reads from env or generates random.
            access_token_ttl: Access token lifetime (default: 1 hour)
            refresh_token_ttl: Refresh token lifetime (default: 7 days)
            algorithm: JWT algorithm (default: HS256)
        """
        self.secret_key = secret_key or os.getenv("ACMS_JWT_SECRET") or secrets.token_hex(32)
        self.access_token_ttl = access_token_ttl
        self.refresh_token_ttl = refresh_token_ttl
        self.algorithm = algorithm

        # Warn if using auto-generated key (not persistent)
        if not secret_key and not os.getenv("ACMS_JWT_SECRET"):
            logger.warning(
                "ACMS_JWT_SECRET not set - using random key. "
                "Tokens will be invalidated on restart."
            )

    def hash_password(self, password: str) -> str:
        """Hash a password using Argon2.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        if ARGON2_AVAILABLE:
            return argon2.hash(password)
        else:
            # Fallback: PBKDF2-SHA256 (less secure but no dependencies)
            salt = secrets.token_bytes(32)
            key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
            return f"pbkdf2:{base64.b64encode(salt).decode()}:{base64.b64encode(key).decode()}"

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash.

        Args:
            password: Plain text password
            hashed: Stored password hash

        Returns:
            True if password matches, False otherwise
        """
        try:
            if ARGON2_AVAILABLE and not hashed.startswith("pbkdf2:"):
                return argon2.verify(password, hashed)
            else:
                # PBKDF2 fallback verification
                parts = hashed.split(":")
                if len(parts) != 3 or parts[0] != "pbkdf2":
                    return False
                salt = base64.b64decode(parts[1])
                stored_key = base64.b64decode(parts[2])
                key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
                return hmac.compare_digest(key, stored_key)
        except Exception as e:
            logger.error(f"Password verification failed: {e}")
            return False

    def create_tokens(
        self,
        user_id: str,
        role: str,
        tenant_id: str,
        email: Optional[str] = None
    ) -> TokenPair:
        """Create access and refresh tokens for a user.

        Args:
            user_id: Unique user identifier
            role: User role (public, member, admin)
            tenant_id: Tenant/organization identifier
            email: Optional user email

        Returns:
            TokenPair with access_token and refresh_token
        """
        now = datetime.now(timezone.utc)

        # Access token payload
        access_payload = {
            "sub": user_id,
            "role": role,
            "tenant_id": tenant_id,
            "email": email,
            "type": "access",
            "iat": now,
            "exp": now + self.access_token_ttl
        }

        # Refresh token payload
        refresh_payload = {
            "sub": user_id,
            "role": role,
            "tenant_id": tenant_id,
            "type": "refresh",
            "iat": now,
            "exp": now + self.refresh_token_ttl
        }

        if JWT_AVAILABLE:
            access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
            refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm)
        else:
            # Simple fallback JWT encoding (not production-grade)
            access_token = self._simple_encode(access_payload)
            refresh_token = self._simple_encode(refresh_payload)

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=int(self.access_token_ttl.total_seconds())
        )

    def validate_token(self, token: str, token_type: str = "access") -> UserContext:
        """Validate a JWT token and extract user context.

        Args:
            token: JWT token string
            token_type: Expected token type ("access" or "refresh")

        Returns:
            UserContext with user information

        Raises:
            AuthError: If token is invalid or expired
        """
        try:
            if JWT_AVAILABLE:
                try:
                    payload = jwt.decode(
                        token,
                        self.secret_key,
                        algorithms=[self.algorithm]
                    )
                except jwt.ExpiredSignatureError:
                    raise AuthError("Token has expired", code="token_expired")
                except jwt.InvalidTokenError as e:
                    raise AuthError(f"Invalid token: {e}", code="invalid_token")
            else:
                # Fallback decoder - raises AuthError directly
                payload = self._simple_decode(token)

            # Verify token type AFTER decoding (so we know the token is valid)
            if payload.get("type") != token_type:
                raise AuthError(
                    f"Invalid token type: expected {token_type}",
                    code="invalid_token_type"
                )

            return UserContext(
                user_id=payload["sub"],
                role=payload.get("role", "member"),
                tenant_id=payload.get("tenant_id", "default"),
                email=payload.get("email"),
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc) if "exp" in payload else None
            )

        except AuthError:
            # Re-raise AuthErrors as-is
            raise
        except Exception as e:
            raise AuthError(f"Invalid token: {e}", code="invalid_token")

    def refresh_access_token(self, refresh_token: str) -> TokenPair:
        """Create new access token using refresh token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            New TokenPair with fresh access token

        Raises:
            AuthError: If refresh token is invalid
        """
        user_ctx = self.validate_token(refresh_token, token_type="refresh")

        return self.create_tokens(
            user_id=user_ctx.user_id,
            role=user_ctx.role,
            tenant_id=user_ctx.tenant_id,
            email=user_ctx.email
        )

    def _simple_encode(self, payload: dict) -> str:
        """Simple JWT encoding fallback (not cryptographically secure)."""
        # Convert datetime to timestamp
        payload_copy = payload.copy()
        for key in ['iat', 'exp']:
            if key in payload_copy and isinstance(payload_copy[key], datetime):
                payload_copy[key] = int(payload_copy[key].timestamp())

        header = base64.urlsafe_b64encode(
            json.dumps({"alg": "HS256", "typ": "JWT"}).encode()
        ).rstrip(b'=').decode()

        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload_copy).encode()
        ).rstrip(b'=').decode()

        message = f"{header}.{payload_b64}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        signature_b64 = base64.urlsafe_b64encode(signature).rstrip(b'=').decode()

        return f"{message}.{signature_b64}"

    def _simple_decode(self, token: str) -> dict:
        """Simple JWT decoding fallback."""
        parts = token.split('.')
        if len(parts) != 3:
            raise AuthError("Invalid token format", code="invalid_token")

        header, payload_b64, signature = parts

        # Verify signature
        message = f"{header}.{payload_b64}"
        expected_sig = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).digest()
        expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b'=').decode()

        if not hmac.compare_digest(signature, expected_sig_b64):
            raise AuthError("Invalid token signature", code="invalid_signature")

        # Decode payload
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += '=' * padding

        payload = json.loads(base64.urlsafe_b64decode(payload_b64))

        # Check expiration
        if 'exp' in payload:
            if datetime.now(timezone.utc).timestamp() > payload['exp']:
                raise AuthError("Token has expired", code="token_expired")

        return payload


# Singleton instance
_auth_service: Optional[SimpleAuth] = None


def get_auth_service() -> SimpleAuth:
    """Get the singleton auth service instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = SimpleAuth()
    return _auth_service
