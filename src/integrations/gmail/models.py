# src/integrations/gmail/models.py
"""
Gmail Integration Data Models

Pydantic models for email data structures.
"""

from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass


@dataclass
class EmailMetadata:
    """Basic email metadata for list views."""
    gmail_message_id: str
    gmail_thread_id: str
    sender_email: str
    sender_name: Optional[str]
    subject: str
    snippet: str
    received_at: datetime
    is_read: bool
    is_starred: bool
    labels: List[str]


@dataclass
class EmailDetail(EmailMetadata):
    """Full email details including body."""
    body_text: str = ""
    body_html: Optional[str] = None
    importance_score: Optional[float] = None
    ai_summary: Optional[str] = None
