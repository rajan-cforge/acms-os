# src/integrations/gmail/client.py
"""
Gmail API Client Wrapper

Provides a clean interface to Gmail API with:
- Automatic token refresh
- Retry with exponential backoff
- Rate limit handling
- Consistent error handling
- Audit logging
"""

import logging
import base64
import asyncio
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from .oauth import GoogleOAuthClient
from .models import EmailMetadata, EmailDetail
from .exceptions import GmailAPIError, RateLimitError, EmailNotFoundError

logger = logging.getLogger(__name__)

# Gmail API base URL
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

# Rate limit settings
MAX_RETRIES = 3
RETRY_MIN_WAIT = 1  # seconds
RETRY_MAX_WAIT = 30  # seconds


class GmailClient:
    """
    Gmail API Client with automatic token refresh and error handling.

    Usage:
        async with GmailClient(oauth_client) as gmail:
            emails = await gmail.list_messages(max_results=50)
            email = await gmail.get_message(message_id)
    """

    def __init__(
        self,
        oauth_client: GoogleOAuthClient,
        user_id: str = "default",
    ):
        self.oauth = oauth_client
        self.user_id = user_id
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._http_client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._http_client:
            await self._http_client.aclose()

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers with valid token."""
        token = await self.oauth.get_valid_token(self.user_id)
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
        retry=retry_if_exception_type((httpx.HTTPStatusError, RateLimitError)),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Gmail API.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (appended to base URL)
            params: Query parameters
            json_data: JSON body for POST/PUT

        Returns:
            Response JSON as dict

        Raises:
            GmailAPIError: For API errors
            RateLimitError: When rate limited (triggers retry)
        """
        client = await self._get_client()
        headers = await self._get_headers()
        url = f"{GMAIL_API_BASE}{endpoint}"

        response = await client.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=json_data,
        )

        # Handle rate limiting
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            logger.warning(f"Rate limited, waiting {retry_after}s")
            await asyncio.sleep(retry_after)
            raise RateLimitError(f"Rate limited, retry after {retry_after}s")

        # Handle errors
        if response.status_code >= 400:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get("error", {}).get("message", response.text)

            if response.status_code == 404:
                raise EmailNotFoundError(endpoint.split("/")[-1])

            raise GmailAPIError(
                f"Gmail API error {response.status_code}: {error_msg}"
            )

        return response.json() if response.content else {}

    # ==========================================
    # MESSAGE LISTING
    # ==========================================

    async def list_messages(
        self,
        max_results: int = 50,
        query: Optional[str] = None,
        label_ids: Optional[List[str]] = None,
        include_spam_trash: bool = False,
        page_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        List messages in user's mailbox.

        Args:
            max_results: Maximum number of messages to return
            query: Gmail search query (e.g., "from:boss@company.com")
            label_ids: Filter by label IDs (e.g., ["INBOX", "UNREAD"])
            include_spam_trash: Include spam and trash
            page_token: Token for pagination

        Returns:
            Dict with 'messages' list and optional 'nextPageToken'
        """
        params = {
            "maxResults": min(max_results, 500),  # Gmail API limit
        }

        if query:
            params["q"] = query
        if label_ids:
            params["labelIds"] = label_ids
        if include_spam_trash:
            params["includeSpamTrash"] = "true"
        if page_token:
            params["pageToken"] = page_token

        result = await self._request("GET", "/messages", params=params)

        # Audit log
        try:
            from src.audit.logger import get_audit_logger
            audit = get_audit_logger()
            await audit.log_ingress(
                source="gmail",
                operation="list_messages",
                item_count=len(result.get("messages", [])),
                metadata={
                    "query": query,
                    "max_results": max_results,
                    "has_next_page": "nextPageToken" in result,
                }
            )
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")

        return result

    async def get_message(
        self,
        message_id: str,
        format: str = "metadata",  # 'minimal', 'metadata', 'full', 'raw'
        metadata_headers: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Get a specific message by ID.

        Args:
            message_id: Gmail message ID
            format: Response format level
            metadata_headers: Headers to include if format='metadata'

        Returns:
            Full message data
        """
        params = {"format": format}

        if format == "metadata" and metadata_headers:
            params["metadataHeaders"] = metadata_headers

        result = await self._request(
            "GET",
            f"/messages/{message_id}",
            params=params
        )

        return result

    async def get_message_detail(self, message_id: str) -> EmailDetail:
        """
        Get full message details parsed into EmailDetail model.

        Args:
            message_id: Gmail message ID

        Returns:
            EmailDetail with parsed content
        """
        raw_message = await self.get_message(
            message_id,
            format="full",
        )

        return self._parse_message_detail(raw_message)

    def _parse_message_detail(self, raw: Dict[str, Any]) -> EmailDetail:
        """Parse raw Gmail message into EmailDetail."""
        headers = {
            h["name"].lower(): h["value"]
            for h in raw.get("payload", {}).get("headers", [])
        }

        # Extract body
        body_text = self._extract_body(raw.get("payload", {}))

        return EmailDetail(
            gmail_message_id=raw["id"],
            gmail_thread_id=raw["threadId"],
            sender_email=self._parse_email_address(headers.get("from", "")),
            sender_name=self._parse_sender_name(headers.get("from", "")),
            subject=headers.get("subject", "(no subject)"),
            snippet=raw.get("snippet", ""),
            body_text=body_text,
            received_at=self._parse_internal_date(raw.get("internalDate")),
            labels=raw.get("labelIds", []),
            is_read="UNREAD" not in raw.get("labelIds", []),
            is_starred="STARRED" in raw.get("labelIds", []),
        )

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Extract plain text body from message payload."""
        # Check for direct body
        if payload.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(
                payload["body"]["data"]
            ).decode("utf-8", errors="replace")

        # Check parts (multipart messages)
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                if part.get("body", {}).get("data"):
                    return base64.urlsafe_b64decode(
                        part["body"]["data"]
                    ).decode("utf-8", errors="replace")
            # Recurse into nested parts
            if part.get("parts"):
                result = self._extract_body(part)
                if result:
                    return result

        return ""

    @staticmethod
    def _parse_email_address(from_header: str) -> str:
        """Extract email address from From header."""
        import re
        match = re.search(r'<([^>]+)>', from_header)
        if match:
            return match.group(1).lower()
        return from_header.lower().strip()

    @staticmethod
    def _parse_sender_name(from_header: str) -> str:
        """Extract sender name from From header."""
        import re
        match = re.search(r'^([^<]+)<', from_header)
        if match:
            return match.group(1).strip().strip('"')
        return ""

    @staticmethod
    def _parse_internal_date(internal_date: Optional[str]) -> datetime:
        """Parse Gmail internal date (milliseconds since epoch)."""
        if internal_date:
            timestamp_ms = int(internal_date)
            return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
        return datetime.now(timezone.utc)

    # ==========================================
    # INBOX SUMMARY
    # ==========================================

    async def get_inbox_summary(self) -> Dict[str, Any]:
        """
        Get inbox summary statistics with accurate counts.

        Uses Gmail labels API for exact unread/starred counts.

        Returns:
            Dict with counts: total, unread, starred, email
        """
        # Get profile for total count and email
        profile = await self._request("GET", "/profile")

        # Get INBOX label for accurate unread count
        inbox_label = await self.get_label("INBOX")

        # Get STARRED label for starred count
        starred_label = await self.get_label("STARRED")

        return {
            "total_messages": profile.get("messagesTotal", 0),
            "total_threads": profile.get("threadsTotal", 0),
            "inbox_total": inbox_label.get("messagesTotal", 0),
            "unread_count": inbox_label.get("messagesUnread", 0),
            "starred_count": starred_label.get("messagesTotal", 0),
            "email": profile.get("emailAddress"),
        }

    # ==========================================
    # LABELS
    # ==========================================

    async def get_label(self, label_id: str) -> Dict[str, Any]:
        """
        Get label details including message counts.

        Args:
            label_id: Label ID (e.g., 'INBOX', 'STARRED', 'UNREAD')

        Returns:
            Label data with messagesTotal, messagesUnread, etc.
        """
        return await self._request("GET", f"/labels/{label_id}")

    async def list_labels(self) -> List[Dict[str, Any]]:
        """List all labels in the mailbox."""
        result = await self._request("GET", "/labels")
        return result.get("labels", [])

    # ==========================================
    # MODIFICATIONS (Phase 1C)
    # ==========================================

    async def modify_message(
        self,
        message_id: str,
        add_labels: Optional[List[str]] = None,
        remove_labels: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Modify message labels (mark read, archive, etc.).

        Args:
            message_id: Gmail message ID
            add_labels: Labels to add
            remove_labels: Labels to remove

        Returns:
            Modified message data
        """
        body = {}
        if add_labels:
            body["addLabelIds"] = add_labels
        if remove_labels:
            body["removeLabelIds"] = remove_labels

        result = await self._request(
            "POST",
            f"/messages/{message_id}/modify",
            json_data=body
        )

        # Audit log
        try:
            from src.audit.logger import get_audit_logger
            audit = get_audit_logger()
            await audit.log_transform(
                source="gmail",
                operation="modify_message",
                destination="gmail_api",
                item_count=1,
                metadata={
                    "message_id": message_id,
                    "add_labels": add_labels,
                    "remove_labels": remove_labels,
                }
            )
        except Exception as e:
            logger.warning(f"Audit log failed: {e}")

        return result

    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """Mark message as read."""
        return await self.modify_message(
            message_id,
            remove_labels=["UNREAD"]
        )

    async def mark_as_unread(self, message_id: str) -> Dict[str, Any]:
        """Mark message as unread."""
        return await self.modify_message(
            message_id,
            add_labels=["UNREAD"]
        )

    async def archive_message(self, message_id: str) -> Dict[str, Any]:
        """Archive message (remove from inbox)."""
        return await self.modify_message(
            message_id,
            remove_labels=["INBOX"]
        )

    async def star_message(self, message_id: str) -> Dict[str, Any]:
        """Star a message."""
        return await self.modify_message(
            message_id,
            add_labels=["STARRED"]
        )

    async def trash_message(self, message_id: str) -> Dict[str, Any]:
        """Move message to trash."""
        return await self._request(
            "POST",
            f"/messages/{message_id}/trash"
        )
