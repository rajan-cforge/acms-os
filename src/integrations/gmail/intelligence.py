# src/integrations/gmail/intelligence.py
"""
Gmail Intelligence Service

AI-powered email intelligence:
- Priority email summaries
- Action suggestions (reply, schedule, delegate)
- Email insights and patterns
- Smart categorization

Uses Gemini 3 Flash for fast, efficient email analysis.
All LLM calls are audit-logged for compliance and cost tracking.
"""

import os
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

import google.generativeai as genai

logger = logging.getLogger(__name__)

# Gemini 3 Flash pricing (Dec 2025)
GEMINI_COST_PER_1M_INPUT = 0.10
GEMINI_COST_PER_1M_OUTPUT = 0.40


class GmailIntelligence:
    """
    AI-powered email intelligence service.
    Uses Gemini 3 Flash for fast email analysis.
    """

    def __init__(self, db_pool=None, model: str = "gemini-3-flash-preview"):
        """
        Initialize Gmail Intelligence.

        Args:
            db_pool: AsyncPG database pool
            model: Gemini model to use (default: gemini-3-flash-preview)
                   Options: gemini-3-flash-preview, gemini-3-pro-preview, gemini-2.5-flash
        """
        self.db_pool = db_pool
        self.model_name = model

        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model)
            logger.info(f"GmailIntelligence initialized with {model}")
        else:
            self.model = None
            logger.warning("GEMINI_API_KEY not set - AI summaries will be unavailable")

    async def summarize_email(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate AI summary for an email using Gemini 3 Flash.

        Args:
            email: Email dict with subject, snippet, body_text

        Returns:
            Dict with summary, action_needed, suggested_action

        Note:
            All LLM calls are audit-logged for compliance tracking.
        """
        if not self.model:
            return {
                "summary": "AI summary unavailable (API key not configured)",
                "action_needed": False,
                "urgency": "none",
                "suggested_action": "none",
                "key_points": [],
                "error": "GEMINI_API_KEY not set",
            }

        start_time = time.time()
        email_id = email.get("gmail_message_id", email.get("id", "unknown"))

        try:
            # Build prompt
            subject = email.get("subject", "")
            snippet = email.get("snippet", "")
            body = email.get("body_text", snippet)[:2000]  # Limit body size
            sender = email.get("from", email.get("sender_email", ""))

            prompt = f"""Analyze this email and provide a brief intelligence summary.

From: {sender}
Subject: {subject}

Content:
{body[:1500]}

Respond in this exact JSON format:
{{
    "summary": "1-2 sentence summary of what this email is about",
    "action_needed": true/false,
    "urgency": "high/medium/low/none",
    "suggested_action": "reply/schedule/delegate/archive/read_later/none",
    "key_points": ["point 1", "point 2"]
}}

Be concise. Focus on actionable intelligence."""

            # Estimate tokens (rough: 4 chars = 1 token)
            input_tokens = len(prompt) // 4

            # Call Gemini directly (no orchestrator overhead)
            response = await self.model.generate_content_async(prompt)
            answer = response.text if response.text else "{}"

            # Calculate metrics
            duration_ms = int((time.time() - start_time) * 1000)
            output_tokens = len(answer) // 4
            est_cost = self._estimate_cost(input_tokens, output_tokens)

            # Parse JSON response
            import json

            # Try to extract JSON from the response
            try:
                # Look for JSON block
                if "```json" in answer:
                    json_str = answer.split("```json")[1].split("```")[0]
                elif "```" in answer:
                    json_str = answer.split("```")[1].split("```")[0]
                elif "{" in answer:
                    start = answer.index("{")
                    end = answer.rindex("}") + 1
                    json_str = answer[start:end]
                else:
                    json_str = answer

                result = json.loads(json_str)
            except (json.JSONDecodeError, ValueError):
                # Fallback if JSON parsing fails
                result = {
                    "summary": answer[:200] if answer else "Unable to summarize",
                    "action_needed": False,
                    "urgency": "none",
                    "suggested_action": "none",
                    "key_points": [],
                }

            # Audit log: Track LLM egress for compliance
            await self._log_llm_call(
                operation="email_summarization",
                email_id=email_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                duration_ms=duration_ms,
                est_cost=est_cost,
                success=True,
                prompt_size_chars=len(prompt),
                sender_domain=sender.split("@")[1] if "@" in sender else "unknown",
            )

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Email summary failed: {e}")

            # Audit log: Track failed LLM call
            await self._log_llm_call(
                operation="email_summarization",
                email_id=email_id,
                input_tokens=0,
                output_tokens=0,
                duration_ms=duration_ms,
                est_cost=0.0,
                success=False,
                error_message=str(e),
            )

            return {
                "summary": "Unable to generate summary",
                "action_needed": False,
                "urgency": "none",
                "suggested_action": "none",
                "key_points": [],
                "error": str(e),
            }

    def _estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for Gemini 3 Flash API call."""
        input_cost = (input_tokens / 1_000_000) * GEMINI_COST_PER_1M_INPUT
        output_cost = (output_tokens / 1_000_000) * GEMINI_COST_PER_1M_OUTPUT
        return round(input_cost + output_cost, 6)

    async def _log_llm_call(
        self,
        operation: str,
        email_id: str,
        input_tokens: int,
        output_tokens: int,
        duration_ms: int,
        est_cost: float,
        success: bool,
        error_message: Optional[str] = None,
        **extra_metadata
    ):
        """
        Log LLM API call to audit system for compliance tracking.

        Tracks:
        - What operation was performed
        - Tokens sent/received
        - Cost estimate
        - Success/failure
        - Email context (ID, sender domain - no PII)
        """
        try:
            from src.audit.logger import get_audit_logger
            from src.audit.models import DataClassification

            audit = get_audit_logger()
            await audit.log_egress(
                source="gmail_intelligence",
                operation=operation,
                destination="gemini_api",
                item_count=1,
                data_classification=DataClassification.INTERNAL,  # Email content is internal
                duration_ms=duration_ms,
                success=success,
                error_message=error_message,
                metadata={
                    "model": self.model_name,
                    "email_id": email_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "est_cost_usd": est_cost,
                    **extra_metadata,
                }
            )
            logger.debug(
                f"[Audit] Gmail LLM call: {operation} - "
                f"{input_tokens}in/{output_tokens}out tokens, "
                f"${est_cost:.6f}, {duration_ms}ms"
            )
        except Exception as e:
            # Don't fail email summarization if audit logging fails
            logger.warning(f"Audit log failed for Gmail LLM call: {e}")

    async def summarize_priority_emails(
        self,
        emails: List[Dict[str, Any]],
        max_to_summarize: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Summarize top priority emails.

        Args:
            emails: List of emails (already sorted by priority)
            max_to_summarize: Max emails to summarize (LLM cost control)

        Returns:
            List of emails with added ai_summary field
        """
        priority_emails = [e for e in emails if e.get("is_priority")][:max_to_summarize]

        for email in priority_emails:
            summary = await self.summarize_email(email)
            email["ai_summary"] = summary

        return emails

    async def generate_inbox_insights(
        self,
        emails: List[Dict[str, Any]],
        user_email: str,
    ) -> Dict[str, Any]:
        """
        Generate inbox insights from email patterns.

        Args:
            emails: List of recent emails
            user_email: User's email for domain analysis

        Returns:
            Dict with insights
        """
        if not emails:
            return {"total_emails": 0, "insights": []}

        # Analyze patterns
        total = len(emails)
        unread = sum(1 for e in emails if not e.get("is_read"))
        priority = sum(1 for e in emails if e.get("is_priority"))

        # Sender frequency
        sender_counts = {}
        for e in emails:
            sender = e.get("sender_email", "unknown")
            sender_counts[sender] = sender_counts.get(sender, 0) + 1

        top_senders = sorted(
            sender_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # Domain analysis
        user_domain = user_email.split("@")[1] if "@" in user_email else ""
        internal = sum(
            1 for e in emails
            if user_domain and e.get("sender_email", "").endswith(user_domain)
        )

        # Generate insights
        insights = []

        if unread > total * 0.5:
            insights.append({
                "type": "unread_backlog",
                "message": f"You have {unread} unread emails ({int(unread/total*100)}%)",
                "severity": "medium",
            })

        if priority > 0:
            insights.append({
                "type": "priority_waiting",
                "message": f"{priority} priority emails need attention",
                "severity": "high",
            })

        if top_senders:
            top_sender_name = top_senders[0][0].split("@")[0]
            insights.append({
                "type": "top_sender",
                "message": f"Most emails from: {top_sender_name} ({top_senders[0][1]} emails)",
                "severity": "info",
            })

        return {
            "total_emails": total,
            "unread_count": unread,
            "priority_count": priority,
            "internal_count": internal,
            "external_count": total - internal,
            "top_senders": [{"email": s[0], "count": s[1]} for s in top_senders],
            "insights": insights,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_daily_brief(
        self,
        emails: List[Dict[str, Any]],
        user_email: str,
    ) -> Dict[str, Any]:
        """
        Generate a daily email brief - executive summary.

        Args:
            emails: Today's emails
            user_email: User's email

        Returns:
            Dict with daily brief
        """
        insights = await self.generate_inbox_insights(emails, user_email)

        # Get priority emails for summary
        priority_emails = [e for e in emails if e.get("is_priority")][:3]

        brief = {
            "date": datetime.now(timezone.utc).strftime("%A, %B %d"),
            "headline": self._generate_headline(insights),
            "stats": {
                "total": insights["total_emails"],
                "unread": insights["unread_count"],
                "priority": insights["priority_count"],
            },
            "priority_preview": [
                {
                    "from": e.get("from", "")[:30],
                    "subject": e.get("subject", "")[:50],
                    "score": e.get("importance_score", 0),
                }
                for e in priority_emails
            ],
            "action_items": [],
            "insights": insights["insights"],
        }

        # Add action items based on priority emails
        if priority_emails:
            brief["action_items"].append(
                f"Review {len(priority_emails)} priority emails"
            )

        if insights["unread_count"] > 10:
            brief["action_items"].append(
                f"Clear inbox backlog ({insights['unread_count']} unread)"
            )

        return brief

    def _generate_headline(self, insights: Dict[str, Any]) -> str:
        """Generate a headline for the daily brief."""
        priority = insights.get("priority_count", 0)
        unread = insights.get("unread_count", 0)

        if priority > 5:
            return f"🔥 {priority} priority emails need attention"
        elif priority > 0:
            return f"⭐ {priority} priority emails today"
        elif unread > 20:
            return f"📬 {unread} unread emails waiting"
        elif unread > 0:
            return f"✉️ {unread} new emails"
        else:
            return "✨ Inbox clear!"


# ============================================================================
# Email Category Detection
# ============================================================================

# Category patterns for rule-based detection
EMAIL_CATEGORY_PATTERNS = {
    "bills": {
        "subjects": [
            "invoice", "bill", "payment due", "statement", "amount due",
            "pay now", "balance due", "payment reminder", "overdue",
            "autopay", "billing", "monthly statement"
        ],
        "senders": [
            "billing", "invoice", "payments", "accounts", "finance",
            "noreply@", "donotreply@"
        ],
        "domains": [
            "xfinity.com", "att.com", "verizon.com", "tmobile.com",
            "pge.com", "edison.com", "utilities", "insurance",
            "chase.com", "bankofamerica.com", "wellsfargo.com",
            "capitalone.com", "discover.com", "amex.com"
        ]
    },
    "shipments": {
        "subjects": [
            "tracking", "shipped", "delivered", "on its way", "out for delivery",
            "in transit", "shipment", "package", "order shipped",
            "delivery update", "your order has shipped", "arriving"
        ],
        "senders": [
            "shipping", "delivery", "tracking", "orders"
        ],
        "domains": [
            "ups.com", "fedex.com", "usps.com", "dhl.com",
            "amazon.com", "ship-notify", "shipstation.com"
        ]
    },
    "purchases": {
        "subjects": [
            "order confirmation", "receipt", "purchase", "thank you for your order",
            "order #", "your order", "order received", "order placed",
            "payment received", "transaction", "bought"
        ],
        "senders": [
            "orders", "order-confirm", "receipts", "noreply", "confirmation"
        ],
        "domains": [
            "amazon.com", "ebay.com", "walmart.com", "target.com",
            "bestbuy.com", "apple.com", "paypal.com", "venmo.com",
            "squareup.com", "stripe.com", "shopify.com"
        ]
    },
    "promotions": {
        "subjects": [
            "sale", "% off", "discount", "deal", "offer", "save",
            "limited time", "exclusive", "flash sale", "clearance",
            "free shipping", "coupon", "promo"
        ],
        "senders": [
            "marketing", "promo", "deals", "offers", "newsletter"
        ],
        "domains": []  # Many domains send promotions
    },
    "social": {
        "subjects": [
            "mentioned you", "tagged you", "new follower", "friend request",
            "new message", "commented", "liked", "shared"
        ],
        "senders": [],
        "domains": [
            "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
            "tiktok.com", "snapchat.com", "pinterest.com", "reddit.com"
        ]
    },
}


def detect_email_category(
    subject: str,
    sender_email: str,
    snippet: str = "",
) -> tuple[str, float]:
    """
    Detect email category using rule-based pattern matching.

    Args:
        subject: Email subject line
        sender_email: Sender's email address
        snippet: Email snippet/preview

    Returns:
        Tuple of (category, confidence)
        Categories: bills, shipments, purchases, promotions, social, other
    """
    subject_lower = subject.lower()
    sender_lower = sender_email.lower()
    snippet_lower = snippet.lower()

    # Extract domain from sender
    sender_domain = ""
    if "@" in sender_lower:
        sender_domain = sender_lower.split("@")[1]

    scores = {}

    for category, patterns in EMAIL_CATEGORY_PATTERNS.items():
        score = 0.0

        # Check subject patterns (highest weight)
        for pattern in patterns["subjects"]:
            if pattern in subject_lower:
                score += 0.4
            if pattern in snippet_lower:
                score += 0.1

        # Check sender patterns
        for pattern in patterns["senders"]:
            if pattern in sender_lower:
                score += 0.2

        # Check domain patterns (strong signal)
        for domain in patterns["domains"]:
            if domain in sender_domain:
                score += 0.3

        if score > 0:
            scores[category] = min(score, 1.0)  # Cap at 1.0

    if not scores:
        return ("other", 0.0)

    # Return highest scoring category
    best_category = max(scores, key=scores.get)
    return (best_category, scores[best_category])


def categorize_emails_batch(emails: list[dict]) -> tuple[list[dict], dict]:
    """
    Categorize a batch of emails and return category counts.

    Args:
        emails: List of email dicts with subject, sender_email, snippet

    Returns:
        Tuple of (emails with category added, category_counts dict)
    """
    category_counts = {}

    for email in emails:
        category, confidence = detect_email_category(
            subject=email.get("subject", ""),
            sender_email=email.get("sender_email", ""),
            snippet=email.get("snippet", ""),
        )

        email["category"] = category
        email["category_confidence"] = confidence

        if category != "other":
            category_counts[category] = category_counts.get(category, 0) + 1

    return emails, category_counts


# Factory
def create_intelligence(db_pool=None) -> GmailIntelligence:
    """Create GmailIntelligence instance."""
    return GmailIntelligence(db_pool)
