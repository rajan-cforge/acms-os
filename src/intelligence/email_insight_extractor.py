"""Email Insight Extractor - Extract insights from Gmail emails.

Extracts actionable insights from emails:
- Action items ("Please review...", "Can you send...", "Need by Friday")
- Deadlines ("Due by", "Deadline:", specific dates)
- Key topics (project names, subjects discussed)
- Sender relationships (who you interact with most)

Uses Gemini Flash for cost-effective AI extraction when patterns aren't clear.

Usage:
    extractor = EmailInsightExtractor()
    insights = await extractor.extract_batch(limit=50)
    for insight in insights:
        print(f"{insight.insight_type}: {insight.insight_summary}")
"""

import os
import re
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass

from .insight_extractor import (
    BaseInsightExtractor,
    InsightEntry,
    InsightSource,
    InsightType,
    PrivacyLevel,
    ExtractionResult,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Patterns for Rule-Based Extraction
# ============================================================================

ACTION_PATTERNS = [
    # Direct requests
    (r'\b(?:please|pls|kindly)\s+(?:review|check|look at|send|provide|share|confirm|approve|sign|complete)\b', 0.9),
    (r'\bcan you\s+(?:review|check|send|provide|share|confirm|approve|help|update)\b', 0.85),
    (r'\bcould you\s+(?:review|check|send|provide|share|confirm|approve|help)\b', 0.85),
    (r'\bwould you\s+(?:mind|be able to)\b', 0.8),
    (r'\bneed\s+(?:you to|your)\b', 0.85),
    (r'\brequesting\s+(?:you|your)\b', 0.8),

    # Action words at start of sentence
    (r'^(?:review|check|send|confirm|approve|sign|complete|update|submit)\s+', 0.8),

    # FYI/For your review patterns
    (r'\bfor your (?:review|approval|signature|action|attention)\b', 0.9),
    (r'\baction required\b', 0.95),
    (r'\bresponse needed\b', 0.9),
    (r'\bfyi\b', 0.5),
]

DEADLINE_PATTERNS = [
    # Explicit deadlines with dates
    (r'\b(?:due|deadline)\s*(?:by|:)?\s*(\d{4}-\d{2}-\d{2})', 0.95),  # ISO date
    (r'\b(?:due|deadline|by)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', 0.95),  # MM/DD/YYYY
    (r'\b(?:due|deadline|by)\s+(?:end of day|eod|cob|close of business)\b', 0.9),
    (r'\b(?:due|deadline|by)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b', 0.9),
    (r'\b(?:due|deadline|by)\s+(?:tomorrow|today|this week|next week)\b', 0.9),

    # Date mentions with urgency
    (r'\basap\b', 0.85),
    (r'\burgent(?:ly)?\b', 0.85),
    (r'\btime.?sensitive\b', 0.9),
    (r'\bimmediately\b', 0.8),
]

TOPIC_PATTERNS = [
    # Project/subject patterns
    (r'\bre:\s*(.{10,60})\b', 'subject'),
    (r'\bproject\s*:?\s*(\w+(?:\s+\w+){0,3})\b', 'project'),
    (r'\bregarding\s+(.{10,50})\b', 'topic'),
    (r'\babout\s+(?:the\s+)?(.{10,50})\b', 'topic'),
]


@dataclass
class EmailItem:
    """Represents an email for insight extraction."""
    id: str
    gmail_message_id: str
    sender_email: str
    sender_name: Optional[str]
    subject: str
    snippet: str
    body_text: Optional[str]
    received_at: datetime
    is_read: bool
    is_starred: bool
    labels: List[str]


class EmailInsightExtractor(BaseInsightExtractor):
    """Extracts insights from Gmail emails.

    Uses rule-based pattern matching first (free), then falls back
    to Gemini Flash for complex cases (cost-effective).
    """

    def __init__(self, use_llm_fallback: bool = True, llm_budget_per_hour: float = 0.05):
        super().__init__(InsightSource.EMAIL)
        self.use_llm_fallback = use_llm_fallback
        self.llm_budget = llm_budget_per_hour
        self._llm_cost_this_hour = 0.0
        self._hour_start = datetime.now(timezone.utc)

    async def get_unprocessed_items(self, limit: int = 50) -> List[EmailItem]:
        """Get emails that haven't had insights extracted.

        Queries email_metadata table for recent emails not yet processed.
        """
        from src.storage.database import get_db_connection

        async with get_db_connection() as conn:
            rows = await conn.fetch("""
                SELECT
                    em.id, em.gmail_message_id, em.sender_email, em.sender_name,
                    em.subject, em.snippet, em.received_at, em.is_read, em.is_starred,
                    em.labels
                FROM email_metadata em
                LEFT JOIN unified_insights ui ON (
                    ui.source = 'email'
                    AND ui.source_id = em.gmail_message_id::text
                )
                WHERE ui.id IS NULL  -- Not yet processed
                AND em.received_at > NOW() - INTERVAL '90 days'
                ORDER BY em.received_at DESC
                LIMIT $1
            """, limit)

        items = []
        for row in rows:
            items.append(EmailItem(
                id=str(row["id"]),
                gmail_message_id=row["gmail_message_id"],
                sender_email=row["sender_email"],
                sender_name=row["sender_name"],
                subject=row["subject"] or "",
                snippet=row["snippet"] or "",
                body_text=None,  # Don't fetch body by default
                received_at=row["received_at"],
                is_read=row["is_read"],
                is_starred=row["is_starred"],
                labels=row["labels"] or [],
            ))

        return items

    async def extract_from_item(self, item: EmailItem) -> List[InsightEntry]:
        """Extract insights from a single email.

        Uses rule-based extraction first, then LLM fallback if needed.
        """
        insights: List[InsightEntry] = []
        text = f"{item.subject}\n{item.snippet}"

        # 1. Extract action items
        action_insights = self._extract_action_items(item, text)
        insights.extend(action_insights)

        # 2. Extract deadlines
        deadline_insights = self._extract_deadlines(item, text)
        insights.extend(deadline_insights)

        # 3. Extract topics
        topic_insights = self._extract_topics(item, text)
        insights.extend(topic_insights)

        # 4. Extract sender relationship insight
        sender_insight = self._extract_sender_insight(item)
        if sender_insight:
            insights.append(sender_insight)

        # 5. LLM fallback if no insights found and email seems important
        if not insights and self._should_use_llm(item):
            llm_insights = await self._extract_with_llm(item, text)
            insights.extend(llm_insights)

        self.logger.debug(f"Extracted {len(insights)} insights from email {item.gmail_message_id}")
        return insights

    def _extract_action_items(self, item: EmailItem, text: str) -> List[InsightEntry]:
        """Extract action items using pattern matching."""
        insights = []
        text_lower = text.lower()

        for pattern, confidence in ACTION_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
            if matches:
                # Found an action pattern
                insight = InsightEntry(
                    source=InsightSource.EMAIL,
                    source_id=item.gmail_message_id,
                    source_timestamp=item.received_at,
                    insight_type=InsightType.ACTION_ITEM,
                    insight_text=f"Action requested in email from {item.sender_email}: {item.subject}",
                    insight_summary=f"Action from {item.sender_name or item.sender_email}: {item.subject[:100]}",
                    entities=self._build_entities(item),
                    privacy_level=PrivacyLevel.INTERNAL,
                    confidence_score=confidence,
                )
                insights.append(insight)
                break  # One action item per email

        return insights

    def _extract_deadlines(self, item: EmailItem, text: str) -> List[InsightEntry]:
        """Extract deadline mentions."""
        insights = []
        text_lower = text.lower()

        for pattern, confidence in DEADLINE_PATTERNS:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                # Extract the deadline text
                deadline_text = matches[0] if isinstance(matches[0], str) else str(matches[0])

                insight = InsightEntry(
                    source=InsightSource.EMAIL,
                    source_id=item.gmail_message_id,
                    source_timestamp=item.received_at,
                    insight_type=InsightType.DEADLINE,
                    insight_text=f"Deadline mentioned in email from {item.sender_email}: {deadline_text}",
                    insight_summary=f"Deadline: {deadline_text} - {item.subject[:80]}",
                    entities=self._build_entities(item, dates=[deadline_text]),
                    privacy_level=PrivacyLevel.INTERNAL,
                    confidence_score=confidence,
                )
                insights.append(insight)
                break  # One deadline per email

        return insights

    def _extract_topics(self, item: EmailItem, text: str) -> List[InsightEntry]:
        """Extract topic/subject insights."""
        insights = []

        # Always create a topic insight for the email subject
        if item.subject and len(item.subject) > 5:
            insight = InsightEntry(
                source=InsightSource.EMAIL,
                source_id=item.gmail_message_id,
                source_timestamp=item.received_at,
                insight_type=InsightType.TOPIC,
                insight_text=f"Email discussion: {item.subject}",
                insight_summary=f"Topic: {item.subject[:100]}",
                entities=self._build_entities(item, topics=[item.subject]),
                privacy_level=PrivacyLevel.INTERNAL,
                confidence_score=0.7,
            )
            insights.append(insight)

        return insights

    def _extract_sender_insight(self, item: EmailItem) -> Optional[InsightEntry]:
        """Create insight about sender relationship if starred/important."""
        if item.is_starred or "IMPORTANT" in item.labels:
            return InsightEntry(
                source=InsightSource.EMAIL,
                source_id=item.gmail_message_id,
                source_timestamp=item.received_at,
                insight_type=InsightType.RELATIONSHIP,
                insight_text=f"Important email from {item.sender_name or item.sender_email}",
                insight_summary=f"Important sender: {item.sender_name or item.sender_email}",
                entities=self._build_entities(item),
                privacy_level=PrivacyLevel.INTERNAL,
                confidence_score=0.85 if item.is_starred else 0.75,
            )
        return None

    def _build_entities(
        self,
        item: EmailItem,
        topics: Optional[List[str]] = None,
        dates: Optional[List[str]] = None,
    ) -> Dict[str, List[str]]:
        """Build entity dictionary from email item."""
        entities = {
            "people": [item.sender_email],
            "topics": topics or [],
            "dates": dates or [],
            "organizations": [],
        }

        # Extract domain as organization
        if "@" in item.sender_email:
            domain = item.sender_email.split("@")[1]
            if domain not in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]:
                entities["organizations"] = [domain]

        return entities

    def _should_use_llm(self, item: EmailItem) -> bool:
        """Determine if we should use LLM for this email."""
        if not self.use_llm_fallback:
            return False

        # Reset budget if new hour
        now = datetime.now(timezone.utc)
        if (now - self._hour_start).total_seconds() > 3600:
            self._llm_cost_this_hour = 0.0
            self._hour_start = now

        # Check budget
        if self._llm_cost_this_hour >= self.llm_budget:
            return False

        # Use LLM for important emails
        return item.is_starred or "IMPORTANT" in item.labels or not item.is_read

    async def _extract_with_llm(self, item: EmailItem, text: str) -> List[InsightEntry]:
        """Use Gemini Flash to extract insights from complex emails."""
        try:
            import google.generativeai as genai

            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            model = genai.GenerativeModel("gemini-2.0-flash-exp")

            prompt = f"""Analyze this email and extract key insights. Return JSON only.

Email from: {item.sender_email}
Subject: {item.subject}
Content: {text[:1000]}

Return a JSON array of insights, each with:
- type: "action_item", "deadline", "topic", or "decision"
- summary: brief description (max 100 chars)
- confidence: 0.0-1.0

Example: [{{"type": "action_item", "summary": "Review Q4 budget proposal", "confidence": 0.9}}]

JSON only, no markdown:"""

            response = model.generate_content(prompt)
            result_text = response.text.strip()

            # Clean up response
            if result_text.startswith("```"):
                result_text = re.sub(r'^```\w*\n?', '', result_text)
                result_text = re.sub(r'\n?```$', '', result_text)

            insights_data = json.loads(result_text)
            self._llm_cost_this_hour += 0.001  # Approximate Gemini Flash cost

            insights = []
            for data in insights_data[:3]:  # Max 3 insights per email
                insight_type = InsightType.FACT
                if data.get("type") == "action_item":
                    insight_type = InsightType.ACTION_ITEM
                elif data.get("type") == "deadline":
                    insight_type = InsightType.DEADLINE
                elif data.get("type") == "topic":
                    insight_type = InsightType.TOPIC
                elif data.get("type") == "decision":
                    insight_type = InsightType.DECISION

                insight = InsightEntry(
                    source=InsightSource.EMAIL,
                    source_id=item.gmail_message_id,
                    source_timestamp=item.received_at,
                    insight_type=insight_type,
                    insight_text=f"From {item.sender_email}: {data.get('summary', item.subject)}",
                    insight_summary=data.get("summary", item.subject)[:100],
                    entities=self._build_entities(item),
                    privacy_level=PrivacyLevel.INTERNAL,
                    confidence_score=float(data.get("confidence", 0.7)),
                    extraction_method="llm",  # Mark as LLM-extracted
                )
                insights.append(insight)

            return insights

        except Exception as e:
            self.logger.warning(f"LLM extraction failed: {e}")
            return []


# ============================================================================
# Convenience Functions
# ============================================================================

async def extract_email_insights(limit: int = 50, use_llm: bool = True) -> ExtractionResult:
    """Extract insights from unprocessed emails.

    Args:
        limit: Max emails to process
        use_llm: Whether to use LLM for complex cases

    Returns:
        ExtractionResult with insights and stats
    """
    extractor = EmailInsightExtractor(use_llm_fallback=use_llm)
    return await extractor.extract_batch(limit=limit)


async def run_email_insight_job():
    """Run as a scheduled job to extract email insights."""
    logger.info("Starting email insight extraction job")

    try:
        result = await extract_email_insights(limit=50)

        logger.info(
            f"Email insight job complete: "
            f"{result.total_processed} processed, "
            f"{result.insights_created} insights, "
            f"{result.errors} errors, "
            f"{result.duration_ms}ms"
        )

        # Save insights
        from .insight_extractor import InsightStorage
        storage = InsightStorage()
        saved = await storage.save_batch(result.insights)
        logger.info(f"Saved {saved} insights to database")

        return result

    except Exception as e:
        logger.error(f"Email insight job failed: {e}")
        raise
