# src/api/gmail_endpoints.py
"""
Gmail REST API Endpoints for Desktop UI

Provides endpoints for:
- OAuth2 flow (connect, callback, status, revoke)
- Inbox summary and insights
- Email listing and details
- Email actions (mark read, archive, etc.)
- Task/event creation from emails

All endpoints create audit events for data flow visibility.
"""

import os
import logging
from typing import Optional, List
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


# ==========================================
# RESPONSE MODELS
# ==========================================

class ConnectionStatus(BaseModel):
    """Gmail connection status."""
    connected: bool
    email: Optional[str] = None
    scopes: List[str] = []


class AuthUrlResponse(BaseModel):
    """OAuth authorization URL response."""
    auth_url: str
    state: str


class InboxSummary(BaseModel):
    """Inbox overview statistics."""
    total_emails: int
    unread_count: int
    priority_count: int
    starred_count: int
    connected_email: str


# ==========================================
# OAUTH ENDPOINTS
# ==========================================

@router.get("/status", response_model=ConnectionStatus)
async def get_connection_status(request: Request):
    """
    Check if Gmail is connected.

    Returns connection status, email address, and granted scopes.
    """
    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient

        db_pool = request.app.state.db_pool
        oauth = GoogleOAuthClient(db_pool=db_pool)

        tokens = await oauth._load_tokens("default")

        if tokens:
            return ConnectionStatus(
                connected=True,
                email=tokens.email,
                scopes=tokens.scopes,
            )
        else:
            return ConnectionStatus(connected=False)

    except Exception as e:
        logger.warning(f"Failed to check Gmail status: {e}")
        return ConnectionStatus(connected=False)


@router.get("/connect", response_model=AuthUrlResponse)
async def initiate_oauth(request: Request):
    """
    Start OAuth flow.

    Returns authorization URL to redirect user to Google consent screen.
    """
    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient

        oauth = GoogleOAuthClient()

        # Generate state for CSRF protection
        state = str(uuid4())

        # Request read-only scope for Phase 1A
        scopes = [
            "https://www.googleapis.com/auth/gmail.readonly",
            "https://www.googleapis.com/auth/userinfo.email",
        ]

        auth_url = oauth.get_authorization_url(scopes=scopes, state=state)

        # Store state in session (for CSRF validation in callback)
        # For now, we'll trust the state parameter

        return AuthUrlResponse(auth_url=auth_url, state=state)

    except Exception as e:
        logger.error(f"Failed to initiate OAuth: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from Google"),
    state: Optional[str] = Query(None, description="State parameter for CSRF"),
    error: Optional[str] = Query(None, description="Error from Google"),
):
    """
    Handle OAuth callback from Google.

    Exchanges authorization code for tokens and stores them.
    Redirects to desktop app success/error page.
    """
    if error:
        logger.error(f"OAuth error from Google: {error}")
        # Redirect to error page
        return RedirectResponse(url=f"/?gmail_error={error}")

    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient

        db_pool = request.app.state.db_pool
        oauth = GoogleOAuthClient(db_pool=db_pool)

        # Exchange code for tokens
        tokens = await oauth.exchange_code(code, user_id="default")

        logger.info(f"Gmail connected for: {tokens.email}")

        # Redirect to success page
        return RedirectResponse(url=f"/?gmail_connected=true&email={tokens.email}")

    except Exception as e:
        logger.error(f"OAuth callback failed: {e}")
        return RedirectResponse(url=f"/?gmail_error={str(e)}")


@router.post("/disconnect")
async def disconnect_gmail(request: Request):
    """
    Disconnect Gmail by revoking tokens.

    Removes stored tokens and revokes access with Google.
    """
    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient

        db_pool = request.app.state.db_pool
        oauth = GoogleOAuthClient(db_pool=db_pool)

        await oauth.revoke_tokens("default")

        return {"success": True, "message": "Gmail disconnected"}

    except Exception as e:
        logger.error(f"Failed to disconnect Gmail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# INBOX ENDPOINTS (Phase 1A)
# ==========================================

@router.get("/summary", response_model=InboxSummary)
async def get_inbox_summary(request: Request):
    """
    Get inbox overview statistics with accurate counts from Gmail.

    Returns counts for inbox total, unread, priority, and starred emails.
    """
    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient
        from src.integrations.gmail.client import GmailClient

        db_pool = request.app.state.db_pool
        oauth = GoogleOAuthClient(db_pool=db_pool)

        async with GmailClient(oauth) as gmail:
            summary = await gmail.get_inbox_summary()

        return InboxSummary(
            total_emails=summary.get("inbox_total", 0),  # Inbox total, not all messages
            unread_count=summary.get("unread_count", 0),  # Accurate from labels API
            priority_count=0,  # Will be calculated after sender scoring
            starred_count=summary.get("starred_count", 0),
            connected_email=summary.get("email", ""),
        )

    except Exception as e:
        logger.error(f"Failed to get inbox summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emails")
async def list_emails(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    days: Optional[int] = Query(None, ge=1, le=365, description="Filter emails from last N days (7, 30, 90, 120)"),
    query: Optional[str] = Query(None, description="Gmail search query"),
    unread_only: bool = Query(False),
    sort_by_priority: bool = Query(True, description="Sort by importance score"),
):
    """
    Get paginated email list with importance scoring.

    Returns email metadata (not full content) for quick display.
    Includes importance_score and is_priority for each email.

    Use `days` parameter to filter by timeline (e.g., days=7 for last week).
    """
    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient
        from src.integrations.gmail.client import GmailClient
        from src.integrations.gmail.sender_model import SenderImportanceModel

        db_pool = request.app.state.db_pool
        oauth = GoogleOAuthClient(db_pool=db_pool)

        # Get user email for domain comparison
        tokens = await oauth._load_tokens("default")
        user_email = tokens.email if tokens else ""

        label_ids = ["INBOX"]
        if unread_only:
            label_ids.append("UNREAD")

        # Build query with optional timeline filter
        search_query = query or ""
        if days:
            date_filter = f"newer_than:{days}d"
            search_query = f"{date_filter} {search_query}".strip()

        async with GmailClient(oauth) as gmail:
            result = await gmail.list_messages(
                max_results=limit,
                query=search_query if search_query else None,
                label_ids=label_ids,
            )

            # Get metadata for each message
            emails = []
            for msg in result.get("messages", [])[:limit]:
                try:
                    detail = await gmail.get_message(
                        msg["id"],
                        format="metadata",
                        metadata_headers=["From", "Subject", "Date"],
                    )

                    # Parse headers
                    headers = {
                        h["name"].lower(): h["value"]
                        for h in detail.get("payload", {}).get("headers", [])
                    }

                    # Extract sender email for scoring
                    from_header = headers.get("from", "")
                    sender_email = GmailClient._parse_email_address(from_header)

                    emails.append({
                        "message_id": detail["id"],
                        "thread_id": detail["threadId"],
                        "subject": headers.get("subject", "(no subject)"),
                        "from": from_header,
                        "sender_email": sender_email,
                        "date": headers.get("date", ""),
                        "snippet": detail.get("snippet", ""),
                        "is_read": "UNREAD" not in detail.get("labelIds", []),
                        "is_starred": "STARRED" in detail.get("labelIds", []),
                        "labels": detail.get("labelIds", []),
                    })
                except Exception as e:
                    logger.warning(f"Failed to get message {msg['id']}: {e}")
                    continue

        # Apply importance scoring
        if emails and user_email:
            sender_model = SenderImportanceModel(db_pool=db_pool)
            emails = await sender_model.score_emails_batch(
                emails,
                user_email=user_email,
            )
        else:
            # Add default scores if no user email
            for email in emails:
                email["importance_score"] = 0
                email["is_priority"] = False
                email["score_factors"] = {}

        # Apply category detection
        from src.integrations.gmail.intelligence import categorize_emails_batch
        emails, category_counts = categorize_emails_batch(emails)

        # Sort by priority if requested (already sorted by score_emails_batch)
        if not sort_by_priority:
            # Keep original order (by date/Gmail default)
            emails.sort(key=lambda x: x.get("date", ""), reverse=True)

        # Count priority emails
        priority_count = sum(1 for e in emails if e.get("is_priority", False))

        return {
            "emails": emails,
            "total_count": len(emails),
            "priority_count": priority_count,
            "category_counts": category_counts,
            "has_more": "nextPageToken" in result,
        }

    except Exception as e:
        logger.error(f"Failed to list emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emails/{message_id}")
async def get_email_detail(request: Request, message_id: str):
    """
    Get full email details.

    Returns complete email with body text for display.
    """
    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient
        from src.integrations.gmail.client import GmailClient

        db_pool = request.app.state.db_pool
        oauth = GoogleOAuthClient(db_pool=db_pool)

        async with GmailClient(oauth) as gmail:
            detail = await gmail.get_message_detail(message_id)

        return {
            "message_id": detail.gmail_message_id,
            "thread_id": detail.gmail_thread_id,
            "sender_email": detail.sender_email,
            "sender_name": detail.sender_name,
            "subject": detail.subject,
            "snippet": detail.snippet,
            "body_text": detail.body_text,
            "received_at": detail.received_at.isoformat(),
            "is_read": detail.is_read,
            "is_starred": detail.is_starred,
            "labels": detail.labels,
            "gmail_link": f"https://mail.google.com/mail/u/0/#inbox/{message_id}",
        }

    except Exception as e:
        logger.error(f"Failed to get email {message_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emails/{message_id}/gmail-link")
async def get_gmail_link(message_id: str):
    """
    Get direct link to email in Gmail.

    Returns URL that opens the email in Gmail web interface.
    """
    return {
        "url": f"https://mail.google.com/mail/u/0/#inbox/{message_id}"
    }


# ==========================================
# SYNC ENDPOINT
# ==========================================

@router.post("/sync")
async def trigger_sync(request: Request):
    """
    Incremental sync - check recent emails.
    """
    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient
        from src.integrations.gmail.sync_service import GmailSyncService

        db_pool = request.app.state.db_pool
        oauth = GoogleOAuthClient(db_pool=db_pool)
        sync = GmailSyncService(db_pool, oauth)

        result = await sync.sync_incremental(max_emails=50)

        return {
            "success": True,
            **result,
        }

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-history")
async def sync_full_history(
    request: Request,
    max_sent: int = Query(500, ge=50, le=1000, description="Max sent emails to analyze"),
    max_inbox: int = Query(500, ge=50, le=1000, description="Max inbox emails to analyze"),
):
    """
    Full historical sync - analyze sent/inbox patterns.

    Builds sender importance data from:
    - Sent folder: who you reply to (reply frequency)
    - Inbox: read/unread patterns (open rate)

    This is a one-time operation that should be run after connecting Gmail.
    Takes 30-60 seconds depending on email volume.
    """
    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient
        from src.integrations.gmail.sync_service import GmailSyncService

        db_pool = request.app.state.db_pool
        oauth = GoogleOAuthClient(db_pool=db_pool)
        sync = GmailSyncService(db_pool, oauth)

        result = await sync.sync_full_history(
            max_sent=max_sent,
            max_inbox=max_inbox,
        )

        return result

    except Exception as e:
        logger.error(f"Full sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-metadata")
async def sync_email_metadata(
    request: Request,
    max_emails: int = Query(100, ge=10, le=500, description="Max emails to sync"),
    days: int = Query(30, ge=1, le=90, description="Number of days of history"),
):
    """
    Sync email metadata to database for insight extraction.

    Phase 1.5: Populates email_metadata table that EmailInsightExtractor
    reads from to generate unified_insights for cross-source queries.

    Run this after connecting Gmail to enable Email + Chat queries.
    """
    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient
        from src.integrations.gmail.sync_service import GmailSyncService

        db_pool = request.app.state.db_pool
        oauth = GoogleOAuthClient(db_pool=db_pool)
        sync = GmailSyncService(db_pool, oauth)

        result = await sync.sync_email_metadata(
            max_emails=max_emails,
            days=days,
        )

        return result

    except Exception as e:
        logger.error(f"Email metadata sync failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# VIP MANAGEMENT ENDPOINTS
# ==========================================

class SenderAction(BaseModel):
    """Request body for sender actions."""
    sender_email: str


@router.post("/vip")
async def add_vip_sender(request: Request, body: SenderAction):
    """
    Mark a sender as VIP.

    VIP senders get a significant importance score bonus.
    """
    try:
        from src.integrations.gmail.sender_model import SenderImportanceModel

        db_pool = request.app.state.db_pool
        sender_model = SenderImportanceModel(db_pool=db_pool)

        await sender_model.add_vip(body.sender_email)

        return {
            "success": True,
            "message": f"{body.sender_email} marked as VIP",
        }

    except Exception as e:
        logger.error(f"Failed to add VIP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/vip")
async def remove_vip_sender(request: Request, body: SenderAction):
    """
    Remove VIP status from a sender.
    """
    try:
        from src.integrations.gmail.sender_model import SenderImportanceModel

        db_pool = request.app.state.db_pool
        sender_model = SenderImportanceModel(db_pool=db_pool)

        await sender_model.remove_vip(body.sender_email)

        return {
            "success": True,
            "message": f"VIP status removed from {body.sender_email}",
        }

    except Exception as e:
        logger.error(f"Failed to remove VIP: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mute")
async def mute_sender(request: Request, body: SenderAction):
    """
    Mute a sender.

    Muted senders always have importance score of 0.
    """
    try:
        from src.integrations.gmail.sender_model import SenderImportanceModel

        db_pool = request.app.state.db_pool
        sender_model = SenderImportanceModel(db_pool=db_pool)

        await sender_model.mute_sender(body.sender_email)

        return {
            "success": True,
            "message": f"{body.sender_email} muted",
        }

    except Exception as e:
        logger.error(f"Failed to mute sender: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/mute")
async def unmute_sender(request: Request, body: SenderAction):
    """
    Unmute a sender.
    """
    try:
        from src.integrations.gmail.sender_model import SenderImportanceModel

        db_pool = request.app.state.db_pool
        sender_model = SenderImportanceModel(db_pool=db_pool)

        await sender_model.unmute_sender(body.sender_email)

        return {
            "success": True,
            "message": f"{body.sender_email} unmuted",
        }

    except Exception as e:
        logger.error(f"Failed to unmute sender: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# LEARNING SIGNALS (Email Actions)
# ==========================================

class EmailActionRequest(BaseModel):
    """Request body for logging email actions."""
    gmail_message_id: str
    sender_email: str
    action_type: str  # 'open_in_gmail', 'mark_read', 'star', 'create_task', etc.
    action_metadata: Optional[dict] = None


@router.post("/actions")
async def log_email_action(request: Request, body: EmailActionRequest):
    """
    Log user action on an email for learning signal capture.

    Used to train sender importance model based on user behavior:
    - open_in_gmail: User clicked through to Gmail
    - mark_read: User marked as read
    - star: User starred the email
    - create_task: User created a task from email
    - create_event: User created a calendar event from email
    - archive: User archived the email
    - delete: User deleted the email

    These signals help personalize email prioritization.
    """
    valid_actions = [
        'open', 'open_in_gmail', 'mark_read', 'mark_unread',
        'archive', 'delete', 'star', 'unstar', 'reply', 'forward',
        'create_task', 'create_event', 'snooze', 'unsnooze',
    ]

    if body.action_type not in valid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action_type. Valid actions: {', '.join(valid_actions)}"
        )

    try:
        db_pool = request.app.state.db_pool

        # Insert action into email_actions table
        async with db_pool.acquire() as conn:
            # First, try to find email_id from email_metadata
            email_id = await conn.fetchval(
                "SELECT id FROM email_metadata WHERE gmail_message_id = $1",
                body.gmail_message_id
            )

            # Insert action (serialize metadata to JSON for PostgreSQL JSONB)
            import json
            metadata_json = json.dumps(body.action_metadata) if body.action_metadata else '{}'

            await conn.execute("""
                INSERT INTO email_actions (
                    email_id, gmail_message_id, sender_email,
                    action_type, action_source, action_metadata
                ) VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            """,
                email_id,  # May be None if email not in metadata cache
                body.gmail_message_id,
                body.sender_email,
                body.action_type,
                'acms',  # Action originated from ACMS UI
                metadata_json,
            )

        # Audit log the learning signal
        try:
            from src.audit.logger import get_audit_logger

            audit = get_audit_logger()
            await audit.log_transform(
                source="gmail",
                operation="learning_signal_capture",
                destination="local",
                item_count=1,
                metadata={
                    "action_type": body.action_type,
                    "sender_email": body.sender_email,
                    "gmail_message_id": body.gmail_message_id,
                }
            )
        except Exception as e:
            logger.warning(f"Audit log failed for learning signal: {e}")

        logger.info(
            f"[Learning] Captured action: {body.action_type} "
            f"for {body.sender_email}"
        )

        return {
            "success": True,
            "action_type": body.action_type,
            "message": "Learning signal captured",
        }

    except Exception as e:
        logger.error(f"Failed to log email action: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/actions/stats")
async def get_action_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365),
):
    """
    Get learning signal statistics.

    Returns counts of user actions for monitoring personalization data.
    """
    try:
        db_pool = request.app.state.db_pool

        async with db_pool.acquire() as conn:
            # Get action counts by type
            rows = await conn.fetch("""
                SELECT action_type, COUNT(*) as count
                FROM email_actions
                WHERE action_at > NOW() - INTERVAL '1 day' * $1
                GROUP BY action_type
                ORDER BY count DESC
            """, days)

            # Get total unprocessed signals
            unprocessed = await conn.fetchval("""
                SELECT COUNT(*) FROM email_actions
                WHERE is_processed_for_learning = FALSE
            """)

            # Get top senders by interaction
            top_senders = await conn.fetch("""
                SELECT sender_email, COUNT(*) as interaction_count
                FROM email_actions
                WHERE action_at > NOW() - INTERVAL '1 day' * $1
                AND action_type IN ('open_in_gmail', 'star', 'reply', 'create_task')
                GROUP BY sender_email
                ORDER BY interaction_count DESC
                LIMIT 10
            """, days)

        return {
            "period_days": days,
            "action_counts": {row["action_type"]: row["count"] for row in rows},
            "total_signals": sum(row["count"] for row in rows),
            "unprocessed_signals": unprocessed,
            "top_engaged_senders": [
                {"email": row["sender_email"], "interactions": row["interaction_count"]}
                for row in top_senders
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get action stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# INTELLIGENCE ENDPOINTS (AI-Powered)
# ==========================================

@router.get("/insights")
async def get_inbox_insights(
    request: Request,
    limit: int = Query(50, ge=10, le=200),
):
    """
    Get AI-generated inbox insights.

    Analyzes email patterns and returns:
    - Unread/priority counts
    - Top senders
    - Actionable insights
    """
    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient
        from src.integrations.gmail.client import GmailClient
        from src.integrations.gmail.sender_model import SenderImportanceModel
        from src.integrations.gmail.intelligence import GmailIntelligence

        db_pool = request.app.state.db_pool
        oauth = GoogleOAuthClient(db_pool=db_pool)

        # Get user email
        tokens = await oauth._load_tokens("default")
        user_email = tokens.email if tokens else ""

        # Get emails
        async with GmailClient(oauth) as gmail:
            result = await gmail.list_messages(max_results=limit, label_ids=["INBOX"])

            emails = []
            for msg in result.get("messages", [])[:limit]:
                try:
                    detail = await gmail.get_message(
                        msg["id"],
                        format="metadata",
                        metadata_headers=["From", "Subject", "Date"],
                    )
                    headers = {
                        h["name"].lower(): h["value"]
                        for h in detail.get("payload", {}).get("headers", [])
                    }
                    from_header = headers.get("from", "")
                    sender_email = GmailClient._parse_email_address(from_header)

                    emails.append({
                        "message_id": detail["id"],
                        "subject": headers.get("subject", ""),
                        "from": from_header,
                        "sender_email": sender_email,
                        "is_read": "UNREAD" not in detail.get("labelIds", []),
                        "is_priority": False,  # Will be set below
                    })
                except Exception:
                    continue

        # Score emails for priority
        if emails and user_email:
            sender_model = SenderImportanceModel(db_pool=db_pool)
            emails = await sender_model.score_emails_batch(emails, user_email)

        # Generate insights
        intelligence = GmailIntelligence(db_pool=db_pool)
        insights = await intelligence.generate_inbox_insights(emails, user_email)

        return insights

    except Exception as e:
        logger.error(f"Failed to get inbox insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/daily-brief")
async def get_daily_brief(
    request: Request,
    limit: int = Query(50, ge=10, le=200),
):
    """
    Get AI-generated daily email brief.

    Returns executive summary:
    - Headline with priority status
    - Stats (total, unread, priority)
    - Priority email preview
    - Action items
    """
    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient
        from src.integrations.gmail.client import GmailClient
        from src.integrations.gmail.sender_model import SenderImportanceModel
        from src.integrations.gmail.intelligence import GmailIntelligence

        db_pool = request.app.state.db_pool
        oauth = GoogleOAuthClient(db_pool=db_pool)

        tokens = await oauth._load_tokens("default")
        user_email = tokens.email if tokens else ""

        async with GmailClient(oauth) as gmail:
            # Get today's emails
            result = await gmail.list_messages(
                max_results=limit,
                label_ids=["INBOX"],
                query="newer_than:1d",  # Today only
            )

            emails = []
            for msg in result.get("messages", [])[:limit]:
                try:
                    detail = await gmail.get_message(
                        msg["id"],
                        format="metadata",
                        metadata_headers=["From", "Subject", "Date"],
                    )
                    headers = {
                        h["name"].lower(): h["value"]
                        for h in detail.get("payload", {}).get("headers", [])
                    }
                    from_header = headers.get("from", "")
                    sender_email = GmailClient._parse_email_address(from_header)

                    emails.append({
                        "message_id": detail["id"],
                        "subject": headers.get("subject", ""),
                        "from": from_header,
                        "sender_email": sender_email,
                        "is_read": "UNREAD" not in detail.get("labelIds", []),
                        "is_priority": False,
                    })
                except Exception:
                    continue

        # Score for priority
        if emails and user_email:
            sender_model = SenderImportanceModel(db_pool=db_pool)
            emails = await sender_model.score_emails_batch(emails, user_email)

        # Generate daily brief
        intelligence = GmailIntelligence(db_pool=db_pool)
        brief = await intelligence.get_daily_brief(emails, user_email)

        return brief

    except Exception as e:
        logger.error(f"Failed to get daily brief: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/emails/{message_id}/summarize")
async def summarize_email(request: Request, message_id: str):
    """
    Get AI summary for a specific email.

    Uses Gemini 2.0 Flash to generate:
    - Brief summary
    - Action needed (yes/no)
    - Urgency level
    - Suggested action
    - Key points
    """
    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient
        from src.integrations.gmail.client import GmailClient
        from src.integrations.gmail.intelligence import GmailIntelligence

        db_pool = request.app.state.db_pool
        oauth = GoogleOAuthClient(db_pool=db_pool)

        # Get email content
        async with GmailClient(oauth) as gmail:
            detail = await gmail.get_message_detail(message_id)

        email_data = {
            "message_id": detail.gmail_message_id,
            "subject": detail.subject,
            "from": detail.sender_name or detail.sender_email,
            "sender_email": detail.sender_email,
            "body_text": detail.body_text,
            "snippet": detail.snippet,
        }

        # Generate AI summary
        intelligence = GmailIntelligence(db_pool=db_pool)
        summary = await intelligence.summarize_email(email_data)

        return {
            "message_id": message_id,
            "ai_summary": summary,
        }

    except Exception as e:
        logger.error(f"Failed to summarize email {message_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/emails/priority-summaries")
async def get_priority_summaries(
    request: Request,
    max_summaries: int = Query(5, ge=1, le=10),
):
    """
    Get AI summaries for top priority emails.

    Fetches priority emails and generates AI summaries for each.
    Cost-controlled via max_summaries parameter.
    """
    try:
        from src.integrations.gmail.oauth import GoogleOAuthClient
        from src.integrations.gmail.client import GmailClient
        from src.integrations.gmail.sender_model import SenderImportanceModel
        from src.integrations.gmail.intelligence import GmailIntelligence

        db_pool = request.app.state.db_pool
        oauth = GoogleOAuthClient(db_pool=db_pool)

        tokens = await oauth._load_tokens("default")
        user_email = tokens.email if tokens else ""

        async with GmailClient(oauth) as gmail:
            result = await gmail.list_messages(
                max_results=50,
                label_ids=["INBOX", "UNREAD"],  # Unread inbox only
            )

            emails = []
            for msg in result.get("messages", [])[:50]:
                try:
                    detail = await gmail.get_message_detail(msg["id"])
                    emails.append({
                        "message_id": detail.gmail_message_id,
                        "thread_id": detail.gmail_thread_id,
                        "subject": detail.subject,
                        "from": detail.sender_name or detail.sender_email,
                        "sender_email": detail.sender_email,
                        "snippet": detail.snippet,
                        "body_text": detail.body_text[:2000],  # Limit for AI
                        "is_read": detail.is_read,
                        "is_starred": detail.is_starred,
                    })
                except Exception:
                    continue

        # Score for priority
        if emails and user_email:
            sender_model = SenderImportanceModel(db_pool=db_pool)
            emails = await sender_model.score_emails_batch(emails, user_email)

        # Generate AI summaries for priority emails
        intelligence = GmailIntelligence(db_pool=db_pool)
        emails = await intelligence.summarize_priority_emails(emails, max_summaries)

        # Return only priority emails with summaries
        priority_with_summaries = [
            e for e in emails
            if e.get("is_priority") and e.get("ai_summary")
        ]

        return {
            "priority_emails": priority_with_summaries,
            "count": len(priority_with_summaries),
            "max_summaries": max_summaries,
        }

    except Exception as e:
        logger.error(f"Failed to get priority summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))
