# src/integrations/gmail/exceptions.py
"""
Gmail Integration Exceptions

Provides a hierarchy of exceptions for Gmail operations:
- GmailError: Base exception for all Gmail errors
- OAuthError: OAuth flow errors
- TokenExpiredError: Token expiration
- TokenRefreshError: Failed token refresh
- GmailAPIError: Gmail API errors
- RateLimitError: Rate limit exceeded
- EmailNotFoundError: Email not found
"""


class GmailError(Exception):
    """Base exception for Gmail integration errors."""
    pass


class OAuthError(GmailError):
    """OAuth flow errors (missing credentials, invalid code, etc.)."""
    pass


class TokenExpiredError(OAuthError):
    """Token has expired and cannot be refreshed."""
    pass


class TokenRefreshError(OAuthError):
    """Failed to refresh token (user may need to re-authenticate)."""
    pass


class GmailAPIError(GmailError):
    """Gmail API returned an error."""

    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.status_code = status_code


class RateLimitError(GmailAPIError):
    """Gmail API rate limit exceeded."""

    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class EmailNotFoundError(GmailAPIError):
    """Email message not found."""

    def __init__(self, message_id: str):
        super().__init__(f"Email not found: {message_id}", status_code=404)
        self.message_id = message_id
