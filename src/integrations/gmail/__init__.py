# src/integrations/gmail/__init__.py
"""
Gmail Integration Module

Provides email intelligence features:
- OAuth2 authentication with secure token storage
- Email listing and metadata retrieval
- Sender importance scoring
- AI-powered email summarization
- Action tracking for learning

Usage:
    from src.integrations.gmail import GoogleOAuthClient, GmailClient

    # OAuth flow
    oauth = GoogleOAuthClient(db_pool=pool)
    auth_url = oauth.get_authorization_url(scopes=["gmail.readonly"])

    # After user authorizes
    tokens = await oauth.exchange_code(code)

    # Gmail operations
    async with GmailClient(oauth) as gmail:
        emails = await gmail.list_messages(max_results=50)
"""

from .oauth import GoogleOAuthClient, OAuthTokens, TokenEncryption
from .client import GmailClient
from .models import EmailMetadata, EmailDetail
from .sender_model import SenderImportanceModel, SenderScore
from .exceptions import (
    GmailError,
    OAuthError,
    TokenExpiredError,
    TokenRefreshError,
    GmailAPIError,
    RateLimitError,
    EmailNotFoundError,
)

__all__ = [
    "GoogleOAuthClient",
    "OAuthTokens",
    "TokenEncryption",
    "GmailClient",
    "EmailMetadata",
    "EmailDetail",
    "SenderImportanceModel",
    "SenderScore",
    "GmailError",
    "OAuthError",
    "TokenExpiredError",
    "TokenRefreshError",
    "GmailAPIError",
    "RateLimitError",
    "EmailNotFoundError",
]
