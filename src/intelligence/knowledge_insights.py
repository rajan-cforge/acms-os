"""Knowledge-Powered Insights Service.

Generates organizational intelligence from extracted knowledge in ACMS_Knowledge_v2.

This replaces shallow topic-count insights with deep knowledge-based analysis:
- Expertise Centers: Where organizational knowledge lives
- Learning Patterns: How users learn (building vs learning vs debugging)
- Cross-Domain Connections: Knowledge that spans multiple areas
- Attention Signals: What needs focus vs. what's well-documented
- Key Facts: Actual knowledge extracted, not just counts

Enterprise Features:
- Structured logging with trace IDs
- Performance metrics
- Error handling with graceful degradation
"""

import logging
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from uuid import uuid4

logger = logging.getLogger("acms.intelligence.knowledge_insights")


# ============================================================================
# CONFIGURATION
# ============================================================================

DEPTH_THRESHOLDS = {
    "deep": 20,      # >20 facts = deep expertise
    "growing": 5,    # 5-20 facts = growing
    "shallow": 0     # <5 facts = shallow
}

INTENT_CATEGORIES = {
    "building": ["building", "creating", "implementing", "developing"],
    "learning": ["learning", "understanding", "researching", "exploring"],
    "debugging": ["debugging", "fixing", "troubleshooting", "resolving"],
    "configuring": ["configuring", "setting", "installing", "deploying"],
    "investing": ["investing", "analyzing", "evaluating"]
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def calculate_depth_level(fact_count: int) -> str:
    """Calculate expertise depth level based on fact count.

    Args:
        fact_count: Number of facts in a domain/topic

    Returns:
        Depth level: 'deep', 'growing', or 'shallow'
    """
    if fact_count > DEPTH_THRESHOLDS["deep"]:
        return "deep"
    elif fact_count >= DEPTH_THRESHOLDS["growing"]:
        return "growing"
    else:
        return "shallow"


def categorize_intent(intent_text: str) -> str:
    """Categorize a primary_intent string into standard categories.

    Args:
        intent_text: Raw intent text from knowledge extraction

    Returns:
        Standardized intent category
    """
    if not intent_text:
        return "unknown"

    intent_lower = intent_text.lower()

    for category, keywords in INTENT_CATEGORIES.items():
        for keyword in keywords:
            if keyword in intent_lower:
                return category

    # Default to first word if no match
    words = intent_lower.split()
    first_word = words[0] if words else "unknown"

    # Skip articles
    if first_word in ["the", "a", "to", "for"]:
        return words[1] if len(words) > 1 else "unknown"

    return first_word


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ExpertiseCenter:
    """Represents an area of organizational expertise."""
    domain: str
    item_count: int
    fact_count: int
    depth_level: str
    topics: List[str]
    sample_insight: str
    related_domains: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "item_count": self.item_count,
            "fact_count": self.fact_count,
            "depth_level": self.depth_level,
            "topics": self.topics,
            "sample_insight": self.sample_insight,
            "related_domains": self.related_domains
        }


@dataclass
class LearningPattern:
    """Represents a learning behavior pattern."""
    category: str
    count: int
    percentage: float
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category,
            "count": self.count,
            "percentage": self.percentage,
            "description": self.description
        }


@dataclass
class AttentionSignal:
    """Represents something that needs attention or is well-handled."""
    signal_type: str  # 'deep_expertise', 'needs_attention', 'growing_areas'
    domain: str
    topic: Optional[str]
    reason: str
    priority: str  # 'high', 'medium', 'low'

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_type": self.signal_type,
            "domain": self.domain,
            "topic": self.topic,
            "reason": self.reason,
            "priority": self.priority
        }


@dataclass
class Recommendation:
    """Actionable recommendation based on knowledge analysis."""
    priority: str
    action: str
    context: str
    domain: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "priority": self.priority,
            "action": self.action,
            "context": self.context,
            "domain": self.domain
        }


# ============================================================================
# MAIN SERVICE CLASS
# ============================================================================

class KnowledgeInsightsService:
    """Service for generating knowledge-powered organizational insights.

    Usage:
        service = KnowledgeInsightsService()
        report = service.generate_report(period_days=30)
    """

    def __init__(self, trace_id: Optional[str] = None):
        """Initialize the service.

        Args:
            trace_id: Optional trace ID for request tracking
        """
        self.trace_id = trace_id or str(uuid4())[:8]
        self._client = None
        self._knowledge_data: List[Dict[str, Any]] = []
        self._loaded = False

        logger.info(
            f"[KnowledgeInsights] Service initialized",
            extra={"trace_id": self.trace_id}
        )

    def _ensure_loaded(self) -> None:
        """Ensure knowledge data is loaded from Weaviate."""
        if self._loaded:
            return

        start_time = datetime.utcnow()

        try:
            from src.storage.weaviate_client import WeaviateClient

            self._client = WeaviateClient()
            collection = self._client._client.collections.get("ACMS_Knowledge_v2")

            # Fetch all knowledge items
            results = collection.query.fetch_objects(limit=1000, include_vector=False)

            self._knowledge_data = [obj.properties for obj in results.objects]
            self._loaded = True

            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(
                f"[KnowledgeInsights] Loaded {len(self._knowledge_data)} knowledge items",
                extra={
                    "trace_id": self.trace_id,
                    "item_count": len(self._knowledge_data),
                    "elapsed_ms": elapsed_ms
                }
            )

        except Exception as e:
            logger.error(
                f"[KnowledgeInsights] Failed to load knowledge data: {e}",
                extra={"trace_id": self.trace_id, "error": str(e)}
            )
            self._knowledge_data = []
            self._loaded = True  # Mark as loaded to avoid retry loops

    def close(self) -> None:
        """Close the Weaviate connection."""
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass

    def get_expertise_centers(self) -> List[Dict[str, Any]]:
        """Get expertise centers grouped by problem domain.

        Returns:
            List of expertise centers with depth metrics
        """
        self._ensure_loaded()

        logger.debug(
            f"[KnowledgeInsights] Calculating expertise centers",
            extra={"trace_id": self.trace_id}
        )

        # Group by domain
        domains: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "items": 0,
            "facts": [],
            "topics": set(),
            "related": set()
        })

        for item in self._knowledge_data:
            domain = item.get("problem_domain", "unknown")
            domains[domain]["items"] += 1
            domains[domain]["facts"].extend(item.get("key_facts", []))

            topic = item.get("topic_cluster")
            if topic:
                domains[domain]["topics"].add(topic)

            for related in item.get("related_topics", []):
                domains[domain]["related"].add(related)

        # Build expertise centers
        centers = []
        for domain, data in sorted(domains.items(), key=lambda x: -len(x[1]["facts"])):
            fact_count = len(data["facts"])

            center = ExpertiseCenter(
                domain=domain,
                item_count=data["items"],
                fact_count=fact_count,
                depth_level=calculate_depth_level(fact_count),
                topics=list(data["topics"])[:5],
                sample_insight=data["facts"][0][:150] + "..." if data["facts"] else "",
                related_domains=[]  # Will populate with cross-domain analysis
            )
            centers.append(center.to_dict())

        logger.info(
            f"[KnowledgeInsights] Found {len(centers)} expertise centers",
            extra={"trace_id": self.trace_id, "center_count": len(centers)}
        )

        return centers

    def get_learning_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Analyze learning patterns from intent distribution.

        Returns:
            Dict mapping intent category to pattern stats
        """
        self._ensure_loaded()

        logger.debug(
            f"[KnowledgeInsights] Analyzing learning patterns",
            extra={"trace_id": self.trace_id}
        )

        intent_counts = Counter()

        for item in self._knowledge_data:
            intent = item.get("primary_intent", "")
            category = categorize_intent(intent)
            intent_counts[category] += 1

        total = sum(intent_counts.values()) or 1

        # Build pattern response with standard categories
        patterns = {}

        descriptions = {
            "building": "Productive work - creating and implementing",
            "learning": "Skill building - research and exploration",
            "debugging": "Problem solving - fixing issues",
            "configuring": "Setup and deployment work",
            "investing": "Financial analysis and evaluation",
            "unknown": "Uncategorized queries"
        }

        for category in ["building", "learning", "debugging", "configuring", "investing", "unknown"]:
            count = intent_counts.get(category, 0)
            patterns[category] = LearningPattern(
                category=category,
                count=count,
                percentage=round(count / total * 100, 1),
                description=descriptions.get(category, "")
            ).to_dict()

        logger.info(
            f"[KnowledgeInsights] Learning patterns: building={intent_counts.get('building', 0)}, "
            f"learning={intent_counts.get('learning', 0)}, debugging={intent_counts.get('debugging', 0)}",
            extra={"trace_id": self.trace_id}
        )

        return patterns

    def get_cross_domain_connections(self) -> List[Dict[str, Any]]:
        """Find topics that connect multiple domains.

        Returns:
            List of cross-domain connections
        """
        self._ensure_loaded()

        logger.debug(
            f"[KnowledgeInsights] Finding cross-domain connections",
            extra={"trace_id": self.trace_id}
        )

        # Map topics to domains they appear in
        topic_domains: Dict[str, set] = defaultdict(set)

        for item in self._knowledge_data:
            domain = item.get("problem_domain", "unknown")

            for topic in item.get("related_topics", []):
                topic_domains[topic].add(domain)

        # Find cross-cutting topics (appear in 2+ domains)
        connections = []
        for topic, domains in sorted(topic_domains.items(), key=lambda x: -len(x[1])):
            if len(domains) >= 2:
                connections.append({
                    "topic": topic,
                    "domains": list(domains),
                    "connection_count": len(domains)
                })

        logger.info(
            f"[KnowledgeInsights] Found {len(connections)} cross-domain connections",
            extra={"trace_id": self.trace_id}
        )

        return connections[:10]  # Top 10 connections

    def get_attention_signals(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate attention signals for areas needing focus.

        Returns:
            Dict with signal categories and their items
        """
        self._ensure_loaded()

        logger.debug(
            f"[KnowledgeInsights] Generating attention signals",
            extra={"trace_id": self.trace_id}
        )

        # Calculate facts per domain
        domain_facts: Dict[str, int] = defaultdict(int)
        domain_items: Dict[str, int] = defaultdict(int)

        for item in self._knowledge_data:
            domain = item.get("problem_domain", "unknown")
            domain_items[domain] += 1
            domain_facts[domain] += len(item.get("key_facts", []))

        signals = {
            "deep_expertise": [],
            "needs_attention": [],
            "growing_areas": []
        }

        for domain in domain_facts:
            facts = domain_facts[domain]
            items = domain_items[domain]
            facts_per_item = facts / items if items > 0 else 0

            if facts > 20:
                signals["deep_expertise"].append(AttentionSignal(
                    signal_type="deep_expertise",
                    domain=domain,
                    topic=None,
                    reason=f"{facts} facts across {items} items - well documented",
                    priority="low"
                ).to_dict())
            elif items >= 2 and facts_per_item < 5:
                signals["needs_attention"].append(AttentionSignal(
                    signal_type="needs_attention",
                    domain=domain,
                    topic=None,
                    reason=f"Only {facts_per_item:.1f} facts/item - needs deeper extraction",
                    priority="medium"
                ).to_dict())
            elif 5 <= facts <= 20:
                signals["growing_areas"].append(AttentionSignal(
                    signal_type="growing_areas",
                    domain=domain,
                    topic=None,
                    reason=f"{facts} facts - good momentum, continue building",
                    priority="low"
                ).to_dict())

        logger.info(
            f"[KnowledgeInsights] Attention signals: deep={len(signals['deep_expertise'])}, "
            f"needs_attention={len(signals['needs_attention'])}, growing={len(signals['growing_areas'])}",
            extra={"trace_id": self.trace_id}
        )

        return signals

    def get_key_facts_summary(self, max_per_domain: int = 3) -> Dict[str, List[str]]:
        """Get key facts grouped by domain.

        Args:
            max_per_domain: Maximum facts to return per domain

        Returns:
            Dict mapping domain to list of key facts
        """
        self._ensure_loaded()

        facts_by_domain: Dict[str, List[str]] = defaultdict(list)

        for item in self._knowledge_data:
            domain = item.get("problem_domain", "unknown")
            for fact in item.get("key_facts", [])[:2]:  # Take first 2 from each item
                if len(facts_by_domain[domain]) < max_per_domain:
                    facts_by_domain[domain].append(fact)

        return dict(facts_by_domain)

    def get_knowledge_velocity(self, period_days: int = 7) -> Dict[str, Any]:
        """Calculate knowledge accumulation velocity.

        Args:
            period_days: Period to analyze

        Returns:
            Velocity metrics
        """
        self._ensure_loaded()

        total_items = len(self._knowledge_data)
        total_facts = sum(len(item.get("key_facts", [])) for item in self._knowledge_data)
        domains = set(item.get("problem_domain") for item in self._knowledge_data)

        return {
            "total_items": total_items,
            "total_facts": total_facts,
            "domains_covered": len(domains),
            "facts_per_item_avg": round(total_facts / total_items, 1) if total_items > 0 else 0,
            "period_days": period_days
        }

    def generate_recommendations(self) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on knowledge analysis.

        Returns:
            List of prioritized recommendations
        """
        self._ensure_loaded()

        logger.debug(
            f"[KnowledgeInsights] Generating recommendations",
            extra={"trace_id": self.trace_id}
        )

        recommendations = []

        # Get domain statistics
        domain_facts: Dict[str, int] = defaultdict(int)
        domain_items: Dict[str, int] = defaultdict(int)

        for item in self._knowledge_data:
            domain = item.get("problem_domain", "unknown")
            domain_items[domain] += 1
            domain_facts[domain] += len(item.get("key_facts", []))

        # Recommendation 1: Domains needing deeper extraction
        for domain, items in domain_items.items():
            facts = domain_facts[domain]
            if items >= 2 and facts / items < 5:
                recommendations.append(Recommendation(
                    priority="high",
                    action=f"Deepen knowledge extraction for {domain}",
                    context=f"{items} items but only {facts/items:.1f} facts/item average. "
                           f"Run knowledge extraction on recent Q&A in this domain.",
                    domain=domain
                ).to_dict())

        # Recommendation 2: Document top expertise areas
        top_domains = sorted(domain_facts.items(), key=lambda x: -x[1])[:3]
        for domain, facts in top_domains:
            if facts > 15:
                recommendations.append(Recommendation(
                    priority="medium",
                    action=f"Create team wiki for {domain}",
                    context=f"Strong expertise with {facts} facts. "
                           f"Consider documenting key learnings for team knowledge sharing.",
                    domain=domain
                ).to_dict())

        # Recommendation 3: Cross-domain opportunities
        connections = self.get_cross_domain_connections()
        if connections:
            top_connection = connections[0]
            recommendations.append(Recommendation(
                priority="low",
                action=f"Explore cross-domain patterns in '{top_connection['topic']}'",
                context=f"This topic connects {top_connection['connection_count']} domains: "
                       f"{', '.join(top_connection['domains'][:3])}. "
                       f"Consider unified documentation.",
                domain=None
            ).to_dict())

        logger.info(
            f"[KnowledgeInsights] Generated {len(recommendations)} recommendations",
            extra={"trace_id": self.trace_id}
        )

        return recommendations

    def generate_report(self, period_days: int = 30) -> Dict[str, Any]:
        """Generate full knowledge insights report.

        Args:
            period_days: Period to analyze

        Returns:
            Complete report dictionary
        """
        start_time = datetime.utcnow()

        logger.info(
            f"[KnowledgeInsights] Generating report for {period_days} days",
            extra={"trace_id": self.trace_id, "period_days": period_days}
        )

        try:
            velocity = self.get_knowledge_velocity(period_days)
            expertise = self.get_expertise_centers()
            patterns = self.get_learning_patterns()
            connections = self.get_cross_domain_connections()
            signals = self.get_attention_signals()
            facts = self.get_key_facts_summary()
            recommendations = self.generate_recommendations()

            # Build executive summary
            top_domain = expertise[0]["domain"] if expertise else "N/A"
            building_pct = patterns.get("building", {}).get("percentage", 0)

            executive_summary = {
                "headline": f"Knowledge captured: {velocity['total_items']} items, {velocity['total_facts']} facts",
                "top_expertise": top_domain,
                "domains_covered": velocity["domains_covered"],
                "learning_focus": f"{building_pct}% building/creating activity",
                "attention_needed": len(signals.get("needs_attention", []))
            }

            report = {
                "generated_at": datetime.utcnow().isoformat(),
                "period_days": period_days,
                "trace_id": self.trace_id,
                "executive_summary": executive_summary,
                "knowledge_velocity": velocity,
                "expertise_centers": expertise,
                "learning_patterns": patterns,
                "cross_domain_connections": connections,
                "attention_signals": signals,
                "key_facts": facts,
                "recommendations": recommendations
            }

            elapsed_ms = (datetime.utcnow() - start_time).total_seconds() * 1000

            logger.info(
                f"[KnowledgeInsights] Report generated successfully",
                extra={
                    "trace_id": self.trace_id,
                    "elapsed_ms": elapsed_ms,
                    "item_count": velocity["total_items"],
                    "fact_count": velocity["total_facts"]
                }
            )

            return report

        except Exception as e:
            logger.error(
                f"[KnowledgeInsights] Report generation failed: {e}",
                extra={"trace_id": self.trace_id, "error": str(e)},
                exc_info=True
            )
            raise
        finally:
            self.close()
