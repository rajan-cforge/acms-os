# src/integrations/plaid/oauth.py
"""
Plaid OAuth Flow Handler

Manages the Plaid Link flow and secure token storage.
Access tokens are encrypted with Fernet (AES-256) before storage.

SECURITY:
- Access tokens NEVER logged in plain text
- Tokens encrypted immediately after exchange
- Encryption key from environment variable
"""

import os
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID

from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)


class PlaidOAuth:
    """
    Handles Plaid OAuth flow with secure token storage.

    Usage:
        oauth = PlaidOAuth(db_pool)

        # Start Link flow
        link_token = await oauth.create_link_token(user_id="user123")

        # Complete flow after user links account
        item = await oauth.handle_link_success(public_token, institution_name)

        # Get decrypted token for API calls
        access_token = await oauth.get_access_token(item_id)
    """

    def __init__(self, db_pool=None):
        """
        Initialize OAuth handler.

        Args:
            db_pool: AsyncPG connection pool
        """
        self.db_pool = db_pool

        # Initialize encryption
        encryption_key = os.getenv("PLAID_ENCRYPTION_KEY")
        if not encryption_key:
            # Generate and warn - in production, this should be set
            logger.warning(
                "PLAID_ENCRYPTION_KEY not set. Generating temporary key. "
                "SET THIS IN PRODUCTION!"
            )
            encryption_key = Fernet.generate_key().decode()

        self.cipher = Fernet(encryption_key.encode() if isinstance(encryption_key, str) else encryption_key)

        # Initialize Plaid client
        from .client import PlaidClient
        self.plaid = PlaidClient()

        logger.info("PlaidOAuth initialized with Fernet encryption")

    def _encrypt(self, value: str) -> str:
        """Encrypt a string value."""
        return self.cipher.encrypt(value.encode()).decode()

    def _decrypt(self, encrypted: str) -> str:
        """Decrypt an encrypted string."""
        return self.cipher.decrypt(encrypted.encode()).decode()

    async def create_link_token(
        self,
        user_id: str = "default",
        products: list = None,
        redirect_uri: str = None,
    ) -> Dict[str, Any]:
        """
        Create a Plaid Link token for the frontend.

        Args:
            user_id: User identifier
            products: Products to request (default: investments, transactions)
            redirect_uri: OAuth redirect URI (required for OAuth institutions in production)

        Returns:
            Dict with link_token, expiration
        """
        if products is None:
            products = ["investments", "transactions"]

        result = self.plaid.create_link_token(
            user_id=user_id,
            products=products,
            redirect_uri=redirect_uri,
        )

        logger.info(f"Link token created for user {user_id} (redirect_uri: {redirect_uri})")
        return result

    async def handle_link_success(
        self,
        public_token: str,
        institution_name: str = None,
        user_id: str = "default",
    ) -> Dict[str, Any]:
        """
        Handle successful Plaid Link completion.

        Exchanges public token for access token and stores encrypted.

        Args:
            public_token: Public token from Link success callback
            institution_name: Name of the linked institution
            user_id: User identifier

        Returns:
            Dict with item_id, institution info
        """
        # Exchange public token for access token
        access_token, item_id = self.plaid.exchange_public_token(public_token)

        # Get item details
        item_info = self.plaid.get_item(access_token)

        # Encrypt access token IMMEDIATELY
        encrypted_token = self._encrypt(access_token)

        # Store in database
        from src.storage.database import get_db_connection

        async with get_db_connection() as conn:
            # Check if we need to create plaid_tokens table or use existing structure
            await conn.execute("""
                INSERT INTO plaid_tokens (
                    user_id, access_token_encrypted, item_id, institution_id,
                    institution_name, products, consent_expiration,
                    is_active, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, NOW(), NOW())
                ON CONFLICT (item_id) DO UPDATE SET
                    access_token_encrypted = EXCLUDED.access_token_encrypted,
                    updated_at = NOW()
            """,
                user_id,
                encrypted_token,
                item_id,
                item_info.get("institution_id"),
                institution_name,
                item_info.get("billed_products", []),
                item_info.get("consent_expiration"),
            )

        logger.info(f"Plaid item {item_id} stored securely")

        return {
            "item_id": item_id,
            "institution_id": item_info.get("institution_id"),
            "institution_name": institution_name,
            "products": item_info.get("billed_products", []),
        }

    async def get_access_token(self, item_id: str) -> Optional[str]:
        """
        Get decrypted access token for API calls.

        Args:
            item_id: Plaid Item ID

        Returns:
            Decrypted access token or None if not found
        """
        from src.storage.database import get_db_connection

        async with get_db_connection() as conn:
            row = await conn.fetchrow("""
                SELECT access_token_encrypted
                FROM plaid_tokens
                WHERE item_id = $1 AND is_active = TRUE
            """, item_id)

        if not row:
            logger.warning(f"No active token found for item {item_id}")
            return None

        # Decrypt and return
        return self._decrypt(row["access_token_encrypted"])

    async def get_connection_status(self, user_id: str = "default") -> Dict[str, Any]:
        """
        Get Plaid connection status for a user.

        Returns:
            Dict with connected status, institutions, last sync times
        """
        from src.storage.database import get_db_connection

        async with get_db_connection() as conn:
            rows = await conn.fetch("""
                SELECT
                    item_id, institution_id, institution_name,
                    products, consent_expiration, is_active,
                    last_successful_sync, error_code, error_message,
                    created_at
                FROM plaid_tokens
                WHERE user_id = $1
                ORDER BY created_at DESC
            """, user_id)

        if not rows:
            return {
                "connected": False,
                "institutions": [],
                "message": "No Plaid connections found. Connect your accounts to get started.",
            }

        institutions = []
        for row in rows:
            institutions.append({
                "item_id": row["item_id"],
                "institution_id": row["institution_id"],
                "institution_name": row["institution_name"],
                "products": row["products"],
                "is_active": row["is_active"],
                "last_sync": row["last_successful_sync"].isoformat() if row["last_successful_sync"] else None,
                "error": row["error_message"] if row["error_code"] else None,
                "connected_at": row["created_at"].isoformat(),
            })

        active_count = sum(1 for i in institutions if i["is_active"])

        return {
            "connected": active_count > 0,
            "active_connections": active_count,
            "institutions": institutions,
        }

    async def disconnect(self, item_id: str) -> bool:
        """
        Disconnect a Plaid Item (revoke access).

        Args:
            item_id: Plaid Item ID to disconnect

        Returns:
            True if successful
        """
        from src.storage.database import get_db_connection

        # Get access token
        access_token = await self.get_access_token(item_id)
        if not access_token:
            logger.warning(f"No token found for item {item_id}")
            return False

        try:
            # Revoke with Plaid
            self.plaid.remove_item(access_token)

            # Mark as inactive in DB
            async with get_db_connection() as conn:
                await conn.execute("""
                    UPDATE plaid_tokens
                    SET is_active = FALSE, updated_at = NOW()
                    WHERE item_id = $1
                """, item_id)

            logger.info(f"Plaid item {item_id} disconnected")
            return True
        except Exception as e:
            logger.error(f"Failed to disconnect item {item_id}: {e}")
            raise

    async def refresh_token_if_needed(self, item_id: str) -> bool:
        """
        Check if token needs refresh and handle if needed.

        Plaid access tokens don't expire, but consent may.
        This handles consent expiration warnings.
        """
        from src.storage.database import get_db_connection

        async with get_db_connection() as conn:
            row = await conn.fetchrow("""
                SELECT consent_expiration
                FROM plaid_tokens
                WHERE item_id = $1 AND is_active = TRUE
            """, item_id)

        if not row or not row["consent_expiration"]:
            return True  # No expiration set

        # Check if consent expires within 30 days
        now = datetime.now(timezone.utc)
        expires = row["consent_expiration"]

        if expires < now:
            logger.warning(f"Consent expired for item {item_id}")
            return False
        elif (expires - now).days < 30:
            logger.warning(
                f"Consent for item {item_id} expires in {(expires - now).days} days. "
                "User should re-link."
            )

        return True
