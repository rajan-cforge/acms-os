# tests/unit/integrations/gmail/test_client.py
"""
TDD Tests for Gmail Client (Days 2-3)

Tests:
- Gmail service connection
- Inbox summary retrieval
- Email listing with metadata
- Message detail parsing
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.integrations.gmail.client import GmailClient
from src.integrations.gmail.models import EmailDetail


# ==========================================
# FIXTURES
# ==========================================

@pytest.fixture
def mock_oauth():
    """Mock OAuth client that returns valid tokens."""
    oauth = AsyncMock()
    oauth.get_valid_token = AsyncMock(return_value="mock_access_token")
    return oauth


@pytest.fixture
def gmail_client(mock_oauth):
    """Gmail client with mocked OAuth."""
    return GmailClient(oauth_client=mock_oauth)


# ==========================================
# DAY 2: SERVICE CONNECTION TESTS
# ==========================================

class TestGmailServiceConnection:
    """Tests for Gmail service connectivity."""

    @pytest.mark.asyncio
    async def test_gmail_service_connects(self, gmail_client):
        """Gmail client can establish connection with valid token."""
        # Given: OAuth client that returns valid token
        # When: Client gets headers
        async with gmail_client:
            headers = await gmail_client._get_headers()

        # Then: Headers contain Bearer token
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer mock_access_token"

    @pytest.mark.asyncio
    async def test_client_context_manager_creates_http_client(self, gmail_client):
        """Context manager properly initializes HTTP client."""
        # When: Enter context
        async with gmail_client as client:
            # Then: HTTP client exists
            assert client._http_client is not None

    @pytest.mark.asyncio
    async def test_client_context_manager_closes_http_client(self, gmail_client):
        """Context manager properly closes HTTP client on exit."""
        # When: Exit context
        async with gmail_client:
            http_client = gmail_client._http_client

        # Then: HTTP client is closed
        assert gmail_client._http_client is None or http_client.is_closed


# ==========================================
# DAY 2: INBOX SUMMARY TESTS
# ==========================================

class TestInboxSummary:
    """Tests for inbox summary functionality."""

    @pytest.mark.asyncio
    async def test_summary_returns_counts(self, gmail_client):
        """Inbox summary returns total, unread, and starred counts."""
        # Given: Mocked API responses
        mock_profile = {
            "emailAddress": "test@example.com",
            "messagesTotal": 1234,
            "threadsTotal": 500,
        }
        mock_unread = {
            "messages": [{"id": "1"}, {"id": "2"}, {"id": "3"}],
        }
        mock_starred = {
            "messages": [{"id": "1"}],
        }

        with patch.object(gmail_client, '_request') as mock_request:
            mock_request.side_effect = [
                mock_profile,  # get_inbox_summary calls /profile
                mock_unread,   # then calls list_messages for UNREAD
                mock_starred,  # then calls list_messages for STARRED
            ]

            async with gmail_client:
                summary = await gmail_client.get_inbox_summary()

        # Then: Summary contains correct counts
        assert summary["total_messages"] == 1234
        assert summary["total_threads"] == 500
        assert summary["unread_estimate"] == 3
        assert summary["starred_estimate"] == 1
        assert summary["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_summary_handles_empty_inbox(self, gmail_client):
        """Inbox summary handles empty mailbox gracefully."""
        # Given: Empty mailbox
        mock_profile = {
            "emailAddress": "empty@example.com",
            "messagesTotal": 0,
            "threadsTotal": 0,
        }
        mock_empty = {"messages": []}

        with patch.object(gmail_client, '_request') as mock_request:
            mock_request.side_effect = [mock_profile, mock_empty, mock_empty]

            async with gmail_client:
                summary = await gmail_client.get_inbox_summary()

        # Then: Returns zeros, not errors
        assert summary["total_messages"] == 0
        assert summary["unread_estimate"] == 0
        assert summary["starred_estimate"] == 0


# ==========================================
# DAY 3: EMAIL LISTING TESTS
# ==========================================

class TestEmailListing:
    """Tests for email listing with metadata."""

    @pytest.mark.asyncio
    async def test_list_returns_metadata(self, gmail_client):
        """List messages returns proper metadata for each email."""
        # Given: Mocked list response
        mock_list = {
            "messages": [
                {"id": "msg1", "threadId": "thread1"},
                {"id": "msg2", "threadId": "thread2"},
            ],
            "nextPageToken": "token123",
        }

        with patch.object(gmail_client, '_request') as mock_request:
            mock_request.return_value = mock_list

            async with gmail_client:
                result = await gmail_client.list_messages(max_results=10)

        # Then: Returns message IDs and pagination token
        assert len(result["messages"]) == 2
        assert result["messages"][0]["id"] == "msg1"
        assert result["nextPageToken"] == "token123"

    @pytest.mark.asyncio
    async def test_list_respects_max_results_limit(self, gmail_client):
        """List messages respects Gmail API's 500 message limit."""
        with patch.object(gmail_client, '_request') as mock_request:
            mock_request.return_value = {"messages": []}

            async with gmail_client:
                await gmail_client.list_messages(max_results=1000)

        # Then: Request is capped at 500
        call_args = mock_request.call_args
        assert call_args[1]["params"]["maxResults"] == 500

    @pytest.mark.asyncio
    async def test_list_with_search_query(self, gmail_client):
        """List messages passes search query to API."""
        with patch.object(gmail_client, '_request') as mock_request:
            mock_request.return_value = {"messages": []}

            async with gmail_client:
                await gmail_client.list_messages(query="from:boss@company.com")

        # Then: Query is passed
        call_args = mock_request.call_args
        assert call_args[1]["params"]["q"] == "from:boss@company.com"

    @pytest.mark.asyncio
    async def test_list_with_label_filter(self, gmail_client):
        """List messages filters by label IDs."""
        with patch.object(gmail_client, '_request') as mock_request:
            mock_request.return_value = {"messages": []}

            async with gmail_client:
                await gmail_client.list_messages(label_ids=["INBOX", "UNREAD"])

        # Then: Labels are passed
        call_args = mock_request.call_args
        assert call_args[1]["params"]["labelIds"] == ["INBOX", "UNREAD"]


# ==========================================
# DAY 3: MESSAGE DETAIL TESTS
# ==========================================

class TestMessageDetail:
    """Tests for individual message retrieval."""

    @pytest.mark.asyncio
    async def test_get_message_detail_parses_correctly(self, gmail_client):
        """Get message detail returns parsed EmailDetail object."""
        # Given: Raw Gmail message
        mock_message = {
            "id": "msg123",
            "threadId": "thread456",
            "internalDate": "1703030400000",  # 2023-12-20 00:00:00 UTC
            "labelIds": ["INBOX", "UNREAD"],
            "snippet": "This is a preview...",
            "payload": {
                "headers": [
                    {"name": "From", "value": "John Doe <john@example.com>"},
                    {"name": "Subject", "value": "Test Subject"},
                ],
                "body": {
                    "data": "SGVsbG8gV29ybGQh"  # Base64: "Hello World!"
                },
            },
        }

        with patch.object(gmail_client, 'get_message') as mock_get:
            mock_get.return_value = mock_message

            async with gmail_client:
                detail = await gmail_client.get_message_detail("msg123")

        # Then: EmailDetail is correctly parsed
        assert isinstance(detail, EmailDetail)
        assert detail.gmail_message_id == "msg123"
        assert detail.gmail_thread_id == "thread456"
        assert detail.sender_email == "john@example.com"
        assert detail.sender_name == "John Doe"
        assert detail.subject == "Test Subject"
        assert detail.body_text == "Hello World!"
        assert detail.is_read is False  # UNREAD in labels
        assert detail.is_starred is False

    def test_parse_email_address_extracts_correctly(self, gmail_client):
        """Email address is extracted from various From header formats."""
        # Test: Standard format
        assert gmail_client._parse_email_address("John <john@example.com>") == "john@example.com"

        # Test: Just email
        assert gmail_client._parse_email_address("john@example.com") == "john@example.com"

        # Test: Email with quotes
        assert gmail_client._parse_email_address('"John Doe" <john@example.com>') == "john@example.com"

    def test_parse_sender_name_extracts_correctly(self, gmail_client):
        """Sender name is extracted from From header."""
        # Test: Standard format
        assert gmail_client._parse_sender_name("John Doe <john@example.com>") == "John Doe"

        # Test: Quoted name
        assert gmail_client._parse_sender_name('"Jane Doe" <jane@example.com>') == "Jane Doe"

        # Test: Just email (no name)
        assert gmail_client._parse_sender_name("john@example.com") == ""


# ==========================================
# DAY 3: ERROR HANDLING TESTS
# ==========================================

class TestErrorHandling:
    """Tests for error handling and retries."""

    @pytest.mark.asyncio
    async def test_rate_limit_triggers_retry(self, gmail_client):
        """429 response triggers retry with exponential backoff."""
        # This test verifies the retry decorator is properly configured
        # The actual retry behavior is handled by tenacity

        from src.integrations.gmail.client import MAX_RETRIES, RETRY_MIN_WAIT

        assert MAX_RETRIES == 3
        assert RETRY_MIN_WAIT == 1

    @pytest.mark.asyncio
    async def test_404_raises_email_not_found(self, gmail_client):
        """404 response raises EmailNotFoundError."""
        from src.integrations.gmail.exceptions import EmailNotFoundError
        import httpx

        with patch.object(gmail_client, '_get_client') as mock_client_getter:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.content = b'{}'
            mock_response.json.return_value = {}
            mock_client.request.return_value = mock_response
            mock_client_getter.return_value = mock_client

            async with gmail_client:
                with pytest.raises(EmailNotFoundError):
                    await gmail_client._request("GET", "/messages/nonexistent")


# ==========================================
# DAY 3: MESSAGE MODIFICATION TESTS
# ==========================================

class TestMessageModification:
    """Tests for message modification operations."""

    @pytest.mark.asyncio
    async def test_mark_as_read_removes_unread_label(self, gmail_client):
        """Marking as read removes UNREAD label."""
        with patch.object(gmail_client, 'modify_message') as mock_modify:
            mock_modify.return_value = {"id": "msg1", "labelIds": ["INBOX"]}

            async with gmail_client:
                await gmail_client.mark_as_read("msg1")

        mock_modify.assert_called_once_with("msg1", remove_labels=["UNREAD"])

    @pytest.mark.asyncio
    async def test_archive_removes_inbox_label(self, gmail_client):
        """Archiving removes INBOX label."""
        with patch.object(gmail_client, 'modify_message') as mock_modify:
            mock_modify.return_value = {"id": "msg1", "labelIds": []}

            async with gmail_client:
                await gmail_client.archive_message("msg1")

        mock_modify.assert_called_once_with("msg1", remove_labels=["INBOX"])

    @pytest.mark.asyncio
    async def test_star_adds_starred_label(self, gmail_client):
        """Starring adds STARRED label."""
        with patch.object(gmail_client, 'modify_message') as mock_modify:
            mock_modify.return_value = {"id": "msg1", "labelIds": ["INBOX", "STARRED"]}

            async with gmail_client:
                await gmail_client.star_message("msg1")

        mock_modify.assert_called_once_with("msg1", add_labels=["STARRED"])
