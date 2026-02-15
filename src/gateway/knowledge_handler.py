"""
Knowledge Data Handler

Handles direct queries about conversation topics and knowledge
stored in ACMS_Knowledge_v2.
"""

import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class KnowledgeDataHandler:
    """Handler for knowledge-related queries.

    Fetches data directly from ACMS_Knowledge_v2 via internal API
    to provide accurate topic summaries.
    """

    def __init__(self):
        self.api_base = "http://localhost:40080"

    async def format_topic_summary(self, user_id: str) -> str:
        """Format a summary of all topics discussed.

        Fetches from /knowledge/stats and /knowledge endpoints
        to build a comprehensive topic summary.

        Args:
            user_id: User identifier

        Returns:
            Formatted markdown summary of topics
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch knowledge stats
                stats_response = await client.get(f"{self.api_base}/knowledge/stats")
                stats = stats_response.json() if stats_response.status_code == 200 else {}

                # Fetch recent knowledge entries
                knowledge_response = await client.get(
                    f"{self.api_base}/knowledge",
                    params={"limit": 30}
                )
                knowledge = knowledge_response.json() if knowledge_response.status_code == 200 else {}

            return self._format_response(stats, knowledge)

        except Exception as e:
            logger.error(f"Error fetching knowledge: {e}")
            return self._format_error_response(str(e))

    def _format_response(self, stats: Dict[str, Any], knowledge: Dict[str, Any]) -> str:
        """Format the knowledge data into a readable summary."""
        total = stats.get("total_knowledge", 0)
        top_topics = stats.get("top_topics", [])
        top_domains = stats.get("top_domains", [])
        entries = knowledge.get("knowledge", [])

        # Build response
        lines = [
            "# Topics We've Discussed",
            "",
            f"Based on **{total}** knowledge entries stored in ACMS, here are the main topics:",
            "",
        ]

        # Top topic clusters
        if top_topics:
            lines.append("## Top Topic Clusters")
            lines.append("")
            for i, topic in enumerate(top_topics[:10], 1):
                topic_name = topic.get("topic", "").replace("-", " ").title()
                count = topic.get("count", 0)
                lines.append(f"{i}. **{topic_name}** ({count} discussions)")
            lines.append("")

        # Domain areas
        if top_domains:
            lines.append("## Knowledge Domains")
            lines.append("")
            for domain in top_domains[:8]:
                domain_name = domain.get("domain", "").replace("-", " ").title()
                count = domain.get("count", 0)
                lines.append(f"- {domain_name}: {count} entries")
            lines.append("")

        # Sample recent discussions
        if entries:
            lines.append("## Sample Recent Discussions")
            lines.append("")
            seen_topics = set()
            for entry in entries[:15]:
                topic = entry.get("topic_cluster", "general")
                if topic not in seen_topics:
                    seen_topics.add(topic)
                    query = entry.get("canonical_query", "")[:80]
                    topic_display = topic.replace("-", " ").title()
                    lines.append(f"- **{topic_display}**: {query}...")
            lines.append("")

        # Summary stats
        lines.append("---")
        lines.append("")
        lines.append("*This is a summary from your ACMS Knowledge Base (ACMS_Knowledge_v2).*")
        lines.append("*Ask about any specific topic to dive deeper!*")

        return "\n".join(lines)

    def _format_error_response(self, error: str) -> str:
        """Format error response."""
        return f"""# Knowledge Summary Unavailable

I encountered an error while fetching your knowledge base:
```
{error}
```

Please try again or check the ACMS API status.
"""
