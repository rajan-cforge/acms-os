# src/gateway/email_handler.py
"""Email Data Handler for EMAIL intent queries.

Provides structured access to email data for the orchestrator when
EMAIL intent is detected. Returns real data from email_metadata and
unified_insights tables.

Per 3.0 Plan use cases:
- "How many unread emails do I have?" → inbox stats
- "Show me important unread emails" → priority list
- "Summarize emails from John" → filtered + summarized
- "Show me email insights" → action items, deadlines, topics
"""

import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EmailDataHandler:
    """Handles EMAIL intent queries by fetching real data from database."""

    def __init__(self, db_pool=None):
        """Initialize with database pool."""
        self._db_pool = db_pool

    async def _get_pool(self):
        """Get database pool, initializing if needed."""
        if self._db_pool is None:
            from src.storage.database import get_db_pool
            self._db_pool = await get_db_pool()
        return self._db_pool

    @property
    def db_pool(self):
        return self._db_pool

    async def get_inbox_stats(self) -> Dict[str, Any]:
        """Get inbox statistics (unread count, priority count, etc.)."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Total and unread counts
                stats = await conn.fetchrow("""
                    SELECT
                        COUNT(*) as total_emails,
                        COUNT(*) FILTER (WHERE is_read = false) as unread_count,
                        COUNT(*) FILTER (WHERE is_starred = true) as starred_count,
                        COUNT(*) FILTER (WHERE is_important = true) as important_count,
                        COUNT(DISTINCT sender_email) as unique_senders
                    FROM email_metadata
                    WHERE is_archived = false
                """)

                # Priority emails (importance_score > 60)
                priority = await conn.fetchval("""
                    SELECT COUNT(*) FROM email_metadata
                    WHERE is_read = false AND importance_score >= 60
                """)

                return {
                    "total_emails": stats["total_emails"] or 0,
                    "unread_count": stats["unread_count"] or 0,
                    "starred_count": stats["starred_count"] or 0,
                    "important_count": stats["important_count"] or 0,
                    "unique_senders": stats["unique_senders"] or 0,
                    "priority_unread": priority or 0
                }
        except Exception as e:
            logger.error(f"Failed to get inbox stats: {e}")
            return {"error": str(e)}

    async def get_top_senders(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top email senders by volume."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT
                        sender_email,
                        sender_name,
                        COUNT(*) as email_count,
                        MAX(received_at) as last_email
                    FROM email_metadata
                    GROUP BY sender_email, sender_name
                    ORDER BY email_count DESC
                    LIMIT $1
                """, limit)

                return [
                    {
                        "email": row["sender_email"],
                        "name": row["sender_name"],
                        "count": row["email_count"],
                        "last_email": row["last_email"].isoformat() if row["last_email"] else None
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get top senders: {e}")
            return []

    async def get_email_insights(
        self,
        insight_types: Optional[List[str]] = None,
        limit: int = 20
    ) -> Dict[str, Any]:
        """Get email insights (action items, deadlines, topics, relationships)."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Get insight counts by type
                type_counts = await conn.fetch("""
                    SELECT insight_type, COUNT(*) as count
                    FROM unified_insights
                    WHERE source = 'email' AND is_active = true
                    GROUP BY insight_type
                    ORDER BY count DESC
                """)

                # Build type filter
                if insight_types:
                    type_filter = "AND insight_type = ANY($2)"
                    params = ['email', insight_types, limit]
                else:
                    type_filter = ""
                    params = ['email', limit]

                # Get recent insights
                query = f"""
                    SELECT
                        id, insight_type, insight_summary,
                        entities, confidence_score, source_timestamp,
                        COALESCE(extraction_method, 'rule_based') as extraction_method
                    FROM unified_insights
                    WHERE source = $1 AND is_active = true {type_filter}
                    ORDER BY source_timestamp DESC
                    LIMIT ${len(params)}
                """

                insights = await conn.fetch(query, *params)

                # Count by extraction method
                method_counts = await conn.fetch("""
                    SELECT COALESCE(extraction_method, 'rule_based') as method, COUNT(*) as count
                    FROM unified_insights
                    WHERE source = 'email' AND is_active = true
                    GROUP BY extraction_method
                """)

                return {
                    "summary": {t["insight_type"]: t["count"] for t in type_counts},
                    "extraction_methods": {m["method"]: m["count"] for m in method_counts},
                    "total_insights": sum(t["count"] for t in type_counts),
                    "insights": [
                        {
                            "type": row["insight_type"],
                            "summary": row["insight_summary"],
                            "entities": row["entities"],
                            "confidence": float(row["confidence_score"]) if row["confidence_score"] else 0.8,
                            "date": row["source_timestamp"].isoformat() if row["source_timestamp"] else None,
                            "extraction_method": row["extraction_method"]
                        }
                        for row in insights
                    ]
                }
        except Exception as e:
            logger.error(f"Failed to get email insights: {e}")
            return {"error": str(e)}

    async def get_action_items(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get action items extracted from emails."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT
                        insight_summary, entities,
                        confidence_score, source_timestamp
                    FROM unified_insights
                    WHERE source = 'email'
                      AND insight_type = 'action_item'
                      AND is_active = true
                    ORDER BY source_timestamp DESC
                    LIMIT $1
                """, limit)

                return [
                    {
                        "action": row["insight_summary"],
                        "from": row["entities"].get("people", [None])[0] if row["entities"] else None,
                        "confidence": float(row["confidence_score"]) if row["confidence_score"] else 0.8,
                        "date": row["source_timestamp"].isoformat() if row["source_timestamp"] else None
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get action items: {e}")
            return []

    async def get_deadlines(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get deadlines extracted from emails."""
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT
                        insight_summary, entities,
                        confidence_score, source_timestamp
                    FROM unified_insights
                    WHERE source = 'email'
                      AND insight_type = 'deadline'
                      AND is_active = true
                    ORDER BY source_timestamp DESC
                    LIMIT $1
                """, limit)

                return [
                    {
                        "deadline": row["insight_summary"],
                        "dates": row["entities"].get("dates", []) if row["entities"] else [],
                        "confidence": float(row["confidence_score"]) if row["confidence_score"] else 0.8,
                        "source_date": row["source_timestamp"].isoformat() if row["source_timestamp"] else None
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to get deadlines: {e}")
            return []

    async def get_unread_by_priority(self, limit: int = 30) -> Dict[str, Any]:
        """Get unread emails grouped by priority tier using sender_scores.

        Priority tiers:
        - High (60+): Important senders, frequent replies
        - Medium (30-59): Regular contacts
        - Low (0-29): Newsletters, bulk mail
        - Unscored: New senders, not yet scored
        """
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                # Get unread emails with sender scores
                rows = await conn.fetch("""
                    SELECT
                        em.gmail_message_id,
                        em.subject,
                        em.sender_email,
                        em.sender_name,
                        em.snippet,
                        em.received_at,
                        em.is_starred,
                        COALESCE(ss.importance_score, -1) as priority_score
                    FROM email_metadata em
                    LEFT JOIN sender_scores ss ON LOWER(em.sender_email) = ss.sender_email
                    WHERE em.is_read = false AND em.is_archived = false
                    ORDER BY COALESCE(ss.importance_score, -1) DESC, em.received_at DESC
                    LIMIT $1
                """, limit)

                # Group by priority tier
                high = []  # 60+
                medium = []  # 30-59
                low = []  # 0-29
                unscored = []  # -1 (no score)

                for row in rows:
                    email_data = {
                        "id": row["gmail_message_id"],
                        "subject": row["subject"][:80] if row["subject"] else "(no subject)",
                        "from": row["sender_name"] or row["sender_email"].split("@")[0],
                        "sender_email": row["sender_email"],
                        "snippet": row["snippet"][:100] if row["snippet"] else "",
                        "date": row["received_at"].strftime("%b %d") if row["received_at"] else "",
                        "is_starred": row["is_starred"],
                        "score": row["priority_score"]
                    }

                    score = row["priority_score"]
                    if score >= 60:
                        high.append(email_data)
                    elif score >= 30:
                        medium.append(email_data)
                    elif score >= 0:
                        low.append(email_data)
                    else:
                        unscored.append(email_data)

                return {
                    "high_priority": high,
                    "medium_priority": medium,
                    "low_priority": low,
                    "unscored": unscored,
                    "total_unread": len(rows),
                    "counts": {
                        "high": len(high),
                        "medium": len(medium),
                        "low": len(low),
                        "unscored": len(unscored)
                    }
                }
        except Exception as e:
            logger.error(f"Failed to get unread by priority: {e}")
            return {"error": str(e)}

    async def search_emails(
        self,
        sender: Optional[str] = None,
        subject_contains: Optional[str] = None,
        unread_only: bool = False,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Search emails by sender, subject, or read status."""
        try:
            conditions = ["is_archived = false"]
            params = []
            param_idx = 1

            if sender:
                conditions.append(f"(sender_email ILIKE ${param_idx} OR sender_name ILIKE ${param_idx})")
                params.append(f"%{sender}%")
                param_idx += 1

            if subject_contains:
                conditions.append(f"subject ILIKE ${param_idx}")
                params.append(f"%{subject_contains}%")
                param_idx += 1

            if unread_only:
                conditions.append("is_read = false")

            params.append(limit)
            where_clause = " AND ".join(conditions)

            pool = await self._get_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch(f"""
                    SELECT
                        gmail_message_id, subject, sender_email, sender_name,
                        snippet, received_at, is_read, is_starred, importance_score
                    FROM email_metadata
                    WHERE {where_clause}
                    ORDER BY received_at DESC
                    LIMIT ${param_idx}
                """, *params)

                return [
                    {
                        "id": row["gmail_message_id"],
                        "subject": row["subject"],
                        "from": row["sender_name"] or row["sender_email"],
                        "sender_email": row["sender_email"],
                        "snippet": row["snippet"],
                        "date": row["received_at"].isoformat() if row["received_at"] else None,
                        "is_read": row["is_read"],
                        "is_starred": row["is_starred"],
                        "importance": row["importance_score"]
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            return []

    def _extract_search_terms(self, query: str) -> List[str]:
        """Extract meaningful search terms from a query.

        Filters out common words and extracts what the user is actually looking for.
        e.g., "from my emails find subscriptions" → ["subscription", "recurring"]
        """
        # Remove common phrases
        cleaned = re.sub(r'\b(from|my|the|in|find|search|show|get|list|can|you|figure|out|what|all|emails?|inbox|mail)\b', '', query.lower())

        # Extract remaining meaningful words
        words = [w.strip() for w in cleaned.split() if len(w.strip()) > 2]

        # Map common queries to search terms
        term_expansions = {
            'subscription': ['subscription', 'recurring', 'monthly', 'yearly', 'renew', 'billing'],
            'newsletter': ['newsletter', 'digest', 'weekly', 'daily', 'update'],
            'receipt': ['receipt', 'invoice', 'payment', 'order', 'confirmation'],
            'meeting': ['meeting', 'invite', 'calendar', 'schedule', 'appointment'],
        }

        expanded_terms = []
        for word in words:
            if word in term_expansions:
                expanded_terms.extend(term_expansions[word])
            else:
                expanded_terms.append(word)

        return list(set(expanded_terms)) if expanded_terms else []

    async def _search_subscriptions(self, query: str) -> str:
        """Search for subscription-related emails.

        Looks for recurring billing, subscription confirmations, etc.
        """
        search_terms = ['subscription', 'recurring', 'monthly', 'yearly', 'renew', 'billing', 'auto-pay']

        results = []
        for term in search_terms[:3]:  # Limit to avoid too many queries
            emails = await self.search_emails(subject_contains=term, limit=5)
            results.extend(emails)

        # Deduplicate by email ID
        seen_ids = set()
        unique_results = []
        for email in results:
            if email['id'] not in seen_ids:
                seen_ids.add(email['id'])
                unique_results.append(email)

        if unique_results:
            response = f"## Subscription-Related Emails\n\n"
            response += f"Found **{len(unique_results)}** emails related to subscriptions:\n\n"
            for e in unique_results[:15]:
                status = "📭" if e['is_read'] else "📬"
                date_str = e['date'][:10] if e['date'] else 'unknown'
                sender = e.get('from', e.get('sender_email', 'Unknown'))[:30]
                response += f"- {status} **{e['subject'][:50]}** - {sender} ({date_str})\n"
            return response

        return "No subscription-related emails found. Try searching for specific services like 'Netflix' or 'Spotify'."

    async def _semantic_email_search(self, search_terms: List[str], original_query: str) -> str:
        """Perform semantic search across email subjects and content.

        Args:
            search_terms: List of terms to search for
            original_query: The original user query for context
        """
        results = []

        # Search by subject for each term
        for term in search_terms[:5]:  # Limit terms
            emails = await self.search_emails(subject_contains=term, limit=5)
            results.extend(emails)

        # Deduplicate
        seen_ids = set()
        unique_results = []
        for email in results:
            if email['id'] not in seen_ids:
                seen_ids.add(email['id'])
                unique_results.append(email)

        if unique_results:
            response = f"## Email Search Results\n\n"
            response += f"Searching for: **{', '.join(search_terms[:3])}**\n"
            response += f"Found **{len(unique_results)}** relevant emails:\n\n"
            for e in unique_results[:15]:
                status = "📭" if e['is_read'] else "📬"
                date_str = e['date'][:10] if e['date'] else 'unknown'
                sender = e.get('from', e.get('sender_email', 'Unknown'))[:30]
                response += f"- {status} **{e['subject'][:50]}** - {sender} ({date_str})\n"
            return response

        return f"No emails found matching: {', '.join(search_terms[:3])}. Try different search terms."

    async def format_response_for_query(self, query: str) -> str:
        """
        Analyze email query and return formatted response with real data.

        This is the main entry point called by the orchestrator for EMAIL intent.
        """
        query_lower = query.lower()

        # Determine what data to fetch based on query
        # Priority grouping: "unread emails by priority", "group unread by importance"
        if ("priority" in query_lower or "group" in query_lower or "order" in query_lower) and "unread" in query_lower:
            priority_data = await self.get_unread_by_priority(limit=30)
            if "error" in priority_data:
                return f"Unable to access email data: {priority_data['error']}"

            counts = priority_data["counts"]
            response = f"""## Unread Emails by Priority

**Total unread**: {priority_data['total_unread']}

| Priority | Count | Description |
|----------|-------|-------------|
| 🔴 High | {counts['high']} | Important senders, frequent replies |
| 🟡 Medium | {counts['medium']} | Regular contacts |
| 🟢 Low | {counts['low']} | Newsletters, bulk mail |
| ⚪ Unscored | {counts['unscored']} | New senders |

"""
            # Show high priority emails
            if priority_data["high_priority"]:
                response += "### 🔴 High Priority\n"
                for e in priority_data["high_priority"][:5]:
                    star = "⭐" if e["is_starred"] else ""
                    response += f"- {star}**{e['subject']}** - {e['from']} ({e['date']})\n"

            # Show medium priority
            if priority_data["medium_priority"]:
                response += "\n### 🟡 Medium Priority\n"
                for e in priority_data["medium_priority"][:5]:
                    star = "⭐" if e["is_starred"] else ""
                    response += f"- {star}**{e['subject']}** - {e['from']} ({e['date']})\n"

            # Show low priority count only
            if priority_data["low_priority"]:
                response += f"\n### 🟢 Low Priority\n*{counts['low']} newsletters and bulk emails*\n"

            # Show unscored
            if priority_data["unscored"]:
                response += f"\n### ⚪ Unscored (New Senders)\n"
                for e in priority_data["unscored"][:3]:
                    response += f"- **{e['subject']}** - {e['from']} ({e['date']})\n"

            return response

        elif "unread" in query_lower and ("how many" in query_lower or "count" in query_lower):
            stats = await self.get_inbox_stats()
            if "error" in stats:
                return f"Unable to access email data: {stats['error']}"

            return f"""## Inbox Stats

- **Unread emails**: {stats['unread_count']}
- **Priority unread** (from important senders): {stats['priority_unread']}
- **Total emails**: {stats['total_emails']}
- **Starred**: {stats['starred_count']}"""

        elif "insight" in query_lower or "action item" in query_lower or "deadline" in query_lower:
            insights = await self.get_email_insights(limit=15)
            if "error" in insights:
                return f"Unable to access email insights: {insights['error']}"

            # Format insights summary
            summary = insights.get("summary", {})
            response = f"""## Email Insights Summary

**Total insights extracted**: {insights['total_insights']}

| Type | Count |
|------|-------|
"""
            for itype, count in summary.items():
                response += f"| {itype.replace('_', ' ').title()} | {count} |\n"

            # Show recent action items if requested or available
            if "action" in query_lower or summary.get("action_item", 0) > 0:
                actions = await self.get_action_items(limit=5)
                if actions:
                    response += "\n### Recent Action Items\n"
                    for a in actions:
                        response += f"- {a['action']}\n"

            # Show deadlines if requested
            if "deadline" in query_lower or summary.get("deadline", 0) > 0:
                deadlines = await self.get_deadlines(limit=5)
                if deadlines:
                    response += "\n### Upcoming Deadlines\n"
                    for d in deadlines:
                        response += f"- {d['deadline']}\n"

            return response

        elif "sender" in query_lower or "who" in query_lower:
            senders = await self.get_top_senders(limit=10)
            if not senders:
                return "No sender data available."

            response = "## Top Email Senders\n\n| Sender | Emails |\n|--------|--------|\n"
            for s in senders:
                name = s['name'] or s['email'].split('@')[0]
                response += f"| {name} | {s['count']} |\n"
            return response

        elif "subscription" in query_lower or "recurring" in query_lower:
            # Handle subscription/recurring queries - search email content and subjects
            return await self._search_subscriptions(query_lower)

        elif "from" in query_lower:
            # Parse "from" carefully - distinguish between:
            # 1. "from my emails, find X" → search IN emails for X
            # 2. "emails from John" → search emails FROM sender John

            # Pattern 1: "from my emails" or "from emails" → search IN emails
            if re.search(r'from\s+(my\s+)?(emails?|inbox|mail)\b', query_lower):
                # Extract what they're searching for
                # e.g., "from my emails, find subscriptions" → search for subscription-related
                search_terms = self._extract_search_terms(query_lower)
                if search_terms:
                    return await self._semantic_email_search(search_terms, query_lower)
                # Fall through to general overview if no specific search terms

            # Pattern 2: "emails from John" → search by sender
            match = re.search(r'(?:emails?\s+)?from\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)', query)
            if match:
                sender = match.group(1)
                # Don't treat common words as sender names
                if sender.lower() not in ['my', 'the', 'all', 'any', 'some', 'your']:
                    emails = await self.search_emails(sender=sender, limit=10)
                    if emails:
                        response = f"## Emails from '{sender}'\n\n"
                        for e in emails:
                            status = "📭" if e['is_read'] else "📬"
                            response += f"- {status} **{e['subject'][:60]}** ({e['date'][:10] if e['date'] else 'unknown'})\n"
                        return response
                    return f"No emails found from '{sender}'."

        else:
            # General email query - show overview
            stats = await self.get_inbox_stats()
            insights = await self.get_email_insights(limit=5)
            senders = await self.get_top_senders(limit=5)

            response = f"""## Email Overview

### Inbox Stats
- **Unread**: {stats.get('unread_count', 0)} emails
- **Priority**: {stats.get('priority_unread', 0)} need attention
- **Total**: {stats.get('total_emails', 0)} emails from {stats.get('unique_senders', 0)} senders

### Recent Insights ({insights.get('total_insights', 0)} total)
"""
            for insight in insights.get('insights', [])[:5]:
                response += f"- **{insight['type']}**: {insight['summary'][:80]}...\n"

            response += "\n### Top Senders\n"
            for s in senders[:5]:
                name = s['name'] or s['email'].split('@')[0]
                response += f"- {name}: {s['count']} emails\n"

            return response


# Global instance
_email_handler = None


async def get_email_handler(db_pool=None) -> EmailDataHandler:
    """Get global email handler instance."""
    global _email_handler
    if _email_handler is None or db_pool is not None:
        _email_handler = EmailDataHandler(db_pool=db_pool)
    return _email_handler
