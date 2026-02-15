"""Creative Recombination for Cross-Domain Discovery.

Cognitive Principle: REM Sleep Creative Discovery

During REM sleep, the brain replays and recombines memories from different
contexts, leading to novel insights and creative problem-solving. The
prefrontal cortex is less active during REM, allowing unusual associations
to form that wouldn't occur during focused waking thought.

The CreativeRecombinator mimics this by:
1. Finding shared entities across distant topic clusters
2. Detecting structural analogies (A:B :: C:D patterns)
3. Identifying bridging queries that connect domains

This enables ACMS to surface creative insights like:
- "Your knowledge of network optimization in DevOps may apply to ML pipelines"
- "The 'feedback loop' pattern appears in both cooking (taste-adjust) and ML (train-eval)"
- "You've been asking questions that connect biology and computer science"

Run as scheduled job: Sunday 3:00 AM
"""

import math
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from collections import defaultdict


logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION
# ============================================================

@dataclass
class RecombinatorConfig:
    """Configuration for CreativeRecombinator."""

    # Minimum semantic distance between domains for discovery to count
    min_domain_distance: float = 0.5

    # Minimum novelty score for a discovery to be surfaced
    min_novelty_score: float = 0.4

    # Maximum discoveries to surface per run (avoid overwhelming)
    max_discoveries_per_run: int = 5

    # Minimum topics sharing an entity to count as discovery
    min_topics_for_shared_entity: int = 2

    # Weight factors for creativity scoring
    distance_weight: float = 0.6
    novelty_weight: float = 0.4

    # Domain similarity thresholds
    same_domain_threshold: float = 0.3
    related_domain_threshold: float = 0.7


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class Discovery:
    """A cross-domain discovery."""
    discovery_type: str  # "cross_domain_entity", "structural_analogy", "bridging_query"
    entity: Optional[str] = None
    topics: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    pattern: Optional[str] = None
    examples: List[Tuple[str, str]] = field(default_factory=list)
    query: Optional[str] = None
    description: str = ""
    insight_text: str = ""
    novelty: float = 0.0
    distance: float = 0.0
    creativity_score: float = 0.0
    strength: float = 0.0
    score: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TopicSummary:
    """Topic summary with entity map."""
    id: str
    topic_slug: str
    summary_text: str
    user_id: str
    entity_map: Dict[str, List[str]]
    knowledge_depth: int
    created_at: datetime


# ============================================================
# DOMAIN TAXONOMY
# ============================================================

# Simple domain taxonomy for computing semantic distance
DOMAIN_TAXONOMY = {
    # Technology domains
    "python": "programming",
    "python-django": "programming",
    "python-flask": "programming",
    "javascript": "programming",
    "rust": "programming",
    "golang": "programming",
    "kubernetes": "devops",
    "docker": "devops",
    "helm": "devops",
    "terraform": "devops",
    "machine-learning": "data-science",
    "deep-learning": "data-science",
    "statistics": "data-science",
    "databases": "data-engineering",
    "sql": "data-engineering",
    "postgresql": "data-engineering",

    # Science domains
    "biology": "life-science",
    "neuroscience": "life-science",
    "ecology": "life-science",
    "chemistry": "physical-science",
    "physics": "physical-science",
    "astronomy": "physical-science",

    # Other domains
    "cooking": "lifestyle",
    "fitness": "lifestyle",
    "music": "arts",
    "art": "arts",
    "supply-chain": "business",
    "logistics": "business",
    "urban-planning": "urban",
    "architecture": "urban",
}

# Parent domain groupings
DOMAIN_GROUPS = {
    "programming": "technology",
    "devops": "technology",
    "data-science": "technology",
    "data-engineering": "technology",
    "life-science": "science",
    "physical-science": "science",
    "lifestyle": "personal",
    "arts": "personal",
    "business": "professional",
    "urban": "professional",
}


# ============================================================
# CREATIVE RECOMBINATOR
# ============================================================

class CreativeRecombinator:
    """Discovers cross-domain connections mimicking REM sleep creativity."""

    def __init__(self, config: Optional[RecombinatorConfig] = None):
        """Initialize the recombinator.

        Args:
            config: Optional configuration
        """
        self.config = config or RecombinatorConfig()

        # Stats tracking
        self._stats = {
            "total_discoveries": 0,
            "discoveries_by_type": {
                "cross_domain_entity": 0,
                "structural_analogy": 0,
                "bridging_query": 0,
            },
            "last_run": None,
            "last_run_discoveries": 0,
        }

    # ============================================================
    # MAIN DISCOVERY PIPELINE
    # ============================================================

    async def discover_cross_domain_connections(
        self,
        user_id: str,
        tenant_id: str = "default"
    ) -> Dict[str, Any]:
        """Run full cross-domain discovery pipeline.

        Args:
            user_id: User ID
            tenant_id: Tenant ID

        Returns:
            Discovery results
        """
        logger.info(f"Starting creative recombination for user {user_id}")

        try:
            # Fetch data
            topic_summaries = await self._fetch_topic_summaries(user_id, tenant_id)
            query_history = await self._fetch_query_history(user_id)
            existing_discoveries = await self._fetch_existing_discoveries(user_id)

            all_discoveries = []

            # 1. Find shared entities across domains
            shared_entities = self._find_shared_entities(topic_summaries)
            entity_discoveries = self._create_entity_discoveries(
                shared_entities,
                topic_summaries
            )
            all_discoveries.extend(entity_discoveries)

            # 2. Find cross-domain discoveries with distance filter
            cross_domain = self._find_cross_domain_discoveries(
                topic_summaries,
                min_domain_distance=self.config.min_domain_distance
            )
            all_discoveries.extend(cross_domain)

            # 3. Find structural analogies
            # Note: Would need knowledge entries with embeddings for full implementation
            # analogies = self._find_structural_analogies(entries)
            # all_discoveries.extend(analogies)

            # 4. Find bridging queries
            bridges = await self._find_bridging_queries(
                user_id,
                min_domain_distance=self.config.min_domain_distance
            )
            all_discoveries.extend(bridges)

            # Filter and rank
            filtered = self._filter_discoveries(
                all_discoveries,
                min_novelty=self.config.min_novelty_score
            )

            # Remove duplicates with existing
            new_discoveries = self._deduplicate_discoveries(
                filtered,
                existing_discoveries
            )

            # Rank and limit
            ranked = self._rank_discoveries(new_discoveries)
            limited = self._limit_discoveries(
                ranked,
                max_per_session=self.config.max_discoveries_per_run
            )

            # Generate insight text
            for discovery in limited:
                if not discovery.insight_text:
                    discovery.insight_text = self._generate_insight_text(
                        self._discovery_to_dict(discovery)
                    )

            # Save discoveries
            if limited:
                await self._save_discoveries(limited, user_id, tenant_id)

            # Update stats
            self._stats["last_run"] = datetime.now(timezone.utc).isoformat()
            self._stats["last_run_discoveries"] = len(limited)
            self._stats["total_discoveries"] += len(limited)
            for d in limited:
                if d.discovery_type in self._stats["discoveries_by_type"]:
                    self._stats["discoveries_by_type"][d.discovery_type] += 1

            logger.info(f"Creative recombination complete: {len(limited)} discoveries")

            return {
                "discoveries": [self._discovery_to_dict(d) for d in limited],
                "discovery_count": len(limited),
                "new_discoveries": len(limited),
                "shared_entities": shared_entities,
                "user_id": user_id,
            }

        except Exception as e:
            logger.error(f"Creative recombination failed: {e}")
            return {
                "discoveries": [],
                "discovery_count": 0,
                "new_discoveries": 0,
                "error": str(e),
            }

    # ============================================================
    # SHARED ENTITY DISCOVERY
    # ============================================================

    def _find_shared_entities(
        self,
        summaries: List[Any]
    ) -> Dict[str, Set[str]]:
        """Find entities shared across multiple topics.

        Args:
            summaries: List of topic summaries with entity_map

        Returns:
            Dict mapping entity to set of topics containing it
        """
        entity_to_topics: Dict[str, Set[str]] = defaultdict(set)

        for summary in summaries:
            topic = getattr(summary, 'topic_slug', str(summary))
            entity_map = getattr(summary, 'entity_map', {})

            if isinstance(entity_map, dict):
                for entity in entity_map.keys():
                    entity_to_topics[entity].add(topic)

        # Filter to entities appearing in multiple topics
        shared = {
            entity: topics
            for entity, topics in entity_to_topics.items()
            if len(topics) >= self.config.min_topics_for_shared_entity
        }

        return shared

    def _create_entity_discoveries(
        self,
        shared_entities: Dict[str, Set[str]],
        summaries: List[Any]
    ) -> List[Discovery]:
        """Create discovery objects from shared entities.

        Args:
            shared_entities: Dict mapping entity to topics
            summaries: Topic summaries for context

        Returns:
            List of Discovery objects
        """
        discoveries = []

        for entity, topics in shared_entities.items():
            topic_list = list(topics)

            # Compute average domain distance
            distances = []
            for i, t1 in enumerate(topic_list):
                for t2 in topic_list[i+1:]:
                    d = self._compute_domain_distance(t1, t2)
                    distances.append(d)

            avg_distance = sum(distances) / len(distances) if distances else 0.0

            # Only count as discovery if domains are sufficiently distant
            if avg_distance >= self.config.min_domain_distance:
                novelty = self._compute_novelty(entity, topic_list)
                creativity = self._compute_creativity_score(entity, topic_list)

                discoveries.append(Discovery(
                    discovery_type="cross_domain_entity",
                    entity=entity,
                    topics=topic_list,
                    novelty=novelty,
                    distance=avg_distance,
                    creativity_score=creativity,
                    score=creativity,
                    description=f"'{entity}' appears in {len(topic_list)} distant domains",
                ))

        return discoveries

    def _find_cross_domain_discoveries(
        self,
        summaries: List[Any],
        min_domain_distance: float = 0.5
    ) -> List[Discovery]:
        """Find discoveries that cross domain boundaries.

        Args:
            summaries: Topic summaries
            min_domain_distance: Minimum distance for discovery

        Returns:
            List of cross-domain discoveries
        """
        # This is handled by _create_entity_discoveries with distance filtering
        # Return empty - the main discoveries come from shared entities
        return []

    # ============================================================
    # STRUCTURAL ANALOGY DISCOVERY
    # ============================================================

    def _find_structural_analogies(
        self,
        entries: List[Any]
    ) -> List[Discovery]:
        """Find structural analogies (A:B :: C:D patterns).

        Args:
            entries: Knowledge entries with content and entities

        Returns:
            List of analogy discoveries
        """
        # Group entries by relationship patterns
        # This is a simplified implementation - full version would use
        # embedding similarity to detect structural patterns

        analogies = []
        patterns: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

        for entry in entries:
            content = getattr(entry, 'content', '')
            entities = getattr(entry, 'entities', [])

            # Simple pattern detection via keyword
            if len(entities) >= 2:
                content_lower = content.lower()

                # Check for relationship keywords
                if "manages" in content_lower:
                    patterns["manages"].append((entities[0], entities[1]))
                elif "leads" in content_lower:
                    patterns["leads"].append((entities[0], entities[1]))
                elif "contains" in content_lower:
                    patterns["contains"].append((entities[0], entities[1]))

        # Create analogies from patterns with multiple examples
        for pattern, examples in patterns.items():
            if len(examples) >= 2:
                # Check if examples are from different domains
                topics = set()
                for ex in examples:
                    for ent in ex:
                        domain = self._get_domain(ent)
                        if domain:
                            topics.add(domain)

                if len(topics) >= 2:
                    analogies.append(Discovery(
                        discovery_type="structural_analogy",
                        pattern=f"X {pattern} Y",
                        examples=examples,
                        topics=list(topics),
                        novelty=0.6,
                        distance=0.5,
                        strength=len(examples) * 0.2,
                        score=len(examples) * 0.2,
                    ))

        return analogies

    # ============================================================
    # BRIDGING QUERY DISCOVERY
    # ============================================================

    async def _find_bridging_queries(
        self,
        user_id: str,
        min_domain_distance: float = 0.5
    ) -> List[Discovery]:
        """Find queries that bridge multiple domains.

        Args:
            user_id: User ID
            min_domain_distance: Minimum distance between domains

        Returns:
            List of bridging query discoveries
        """
        query_history = await self._fetch_query_history(user_id)
        bridges = []

        for query_data in query_history:
            retrieved_topics = query_data.get("retrieved_topics", [])

            if len(retrieved_topics) >= 2:
                # Compute pairwise distances
                distances = []
                for i, t1 in enumerate(retrieved_topics):
                    for t2 in retrieved_topics[i+1:]:
                        d = self._compute_domain_distance(t1, t2)
                        distances.append(d)

                max_distance = max(distances) if distances else 0.0

                if max_distance >= min_domain_distance:
                    bridges.append(Discovery(
                        discovery_type="bridging_query",
                        query=query_data.get("query", ""),
                        topics=retrieved_topics,
                        domains=retrieved_topics,
                        novelty=0.7,
                        distance=max_distance,
                        score=max_distance * 0.7,
                    ))

        return bridges

    # ============================================================
    # DOMAIN DISTANCE CALCULATION
    # ============================================================

    def _compute_domain_distance(self, topic1: str, topic2: str) -> float:
        """Compute semantic distance between two topics/domains.

        Distance is based on taxonomy:
        - Same topic: 0.0
        - Same subdomain: 0.1
        - Same domain: 0.3
        - Same group: 0.5
        - Different groups: 0.9

        Args:
            topic1: First topic
            topic2: Second topic

        Returns:
            Distance between 0.0 and 1.0
        """
        if topic1 == topic2:
            return 0.0

        # Normalize topic names
        t1 = topic1.lower().replace(" ", "-")
        t2 = topic2.lower().replace(" ", "-")

        # Get domains
        domain1 = DOMAIN_TAXONOMY.get(t1, t1)
        domain2 = DOMAIN_TAXONOMY.get(t2, t2)

        if domain1 == domain2:
            return 0.1  # Same subdomain

        # Get groups
        group1 = DOMAIN_GROUPS.get(domain1, domain1)
        group2 = DOMAIN_GROUPS.get(domain2, domain2)

        if group1 == group2:
            return 0.5  # Same parent group

        return 0.9  # Different groups

    def _get_domain(self, topic: str) -> Optional[str]:
        """Get the domain for a topic."""
        normalized = topic.lower().replace(" ", "-")
        return DOMAIN_TAXONOMY.get(normalized, normalized)

    # ============================================================
    # SCORING AND FILTERING
    # ============================================================

    def _compute_novelty(self, entity: str, topics: List[str]) -> float:
        """Compute novelty score for a discovery.

        Novelty is higher when:
        - More topics share the entity
        - Topics are more distant

        Args:
            entity: The shared entity
            topics: Topics containing the entity

        Returns:
            Novelty score between 0.0 and 1.0
        """
        if len(topics) < 2:
            return 0.0

        # More topics = more novel
        topic_factor = min(1.0, len(topics) / 5.0)

        # Compute average pairwise distance
        distances = []
        for i, t1 in enumerate(topics):
            for t2 in topics[i+1:]:
                d = self._compute_domain_distance(t1, t2)
                distances.append(d)

        avg_distance = sum(distances) / len(distances) if distances else 0.0

        return (topic_factor * 0.4) + (avg_distance * 0.6)

    def _compute_creativity_score(
        self,
        entity: str,
        topics: List[str]
    ) -> float:
        """Compute creativity score for a discovery.

        Creativity = distance * novelty (distant associations are more creative)

        Args:
            entity: The shared entity
            topics: Topics containing the entity

        Returns:
            Creativity score between 0.0 and 1.0
        """
        if len(topics) < 2:
            return 0.0

        # Compute average distance
        distances = []
        for i, t1 in enumerate(topics):
            for t2 in topics[i+1:]:
                d = self._compute_domain_distance(t1, t2)
                distances.append(d)

        avg_distance = sum(distances) / len(distances) if distances else 0.0
        novelty = self._compute_novelty(entity, topics)

        return (
            self.config.distance_weight * avg_distance +
            self.config.novelty_weight * novelty
        )

    def _filter_discoveries(
        self,
        discoveries: List[Any],
        min_novelty: float = 0.4
    ) -> List[Any]:
        """Filter discoveries by novelty threshold.

        Args:
            discoveries: All discoveries (Discovery objects or dicts)
            min_novelty: Minimum novelty score

        Returns:
            Filtered discoveries
        """
        def get_novelty(d: Any) -> float:
            if isinstance(d, dict):
                return d.get("novelty", 0.0)
            return getattr(d, 'novelty', 0.0)

        return [d for d in discoveries if get_novelty(d) >= min_novelty]

    def _rank_discoveries(
        self,
        discoveries: List[Any]
    ) -> List[Any]:
        """Rank discoveries by interestingness.

        Interestingness = novelty * distance

        Args:
            discoveries: Discoveries to rank (Discovery objects or dicts)

        Returns:
            Sorted discoveries (most interesting first)
        """
        def score(d: Any) -> float:
            if isinstance(d, dict):
                return d.get("novelty", 0.0) * d.get("distance", 0.0)
            return getattr(d, 'novelty', 0.0) * getattr(d, 'distance', 0.0)

        return sorted(discoveries, key=score, reverse=True)

    def _limit_discoveries(
        self,
        discoveries: List[Discovery],
        max_per_session: int = 5
    ) -> List[Discovery]:
        """Limit discoveries to avoid overwhelming user.

        Args:
            discoveries: Ranked discoveries
            max_per_session: Maximum to return

        Returns:
            Limited list
        """
        return discoveries[:max_per_session]

    def _deduplicate_discoveries(
        self,
        new_discoveries: List[Discovery],
        existing: List[Any]
    ) -> List[Discovery]:
        """Remove discoveries that already exist.

        Args:
            new_discoveries: New discoveries
            existing: Existing discoveries

        Returns:
            Deduplicated list
        """
        existing_keys = set()
        for e in existing:
            if isinstance(e, dict):
                key = (e.get("entity"), tuple(sorted(e.get("topics", []))))
            else:
                key = (getattr(e, 'entity', None), tuple(sorted(getattr(e, 'topics', []))))
            existing_keys.add(key)

        return [
            d for d in new_discoveries
            if (d.entity, tuple(sorted(d.topics))) not in existing_keys
        ]

    # ============================================================
    # INSIGHT GENERATION
    # ============================================================

    def _generate_insight_text(self, discovery: Dict[str, Any]) -> str:
        """Generate human-readable insight text.

        Args:
            discovery: Discovery dict

        Returns:
            Insight text string
        """
        discovery_type = discovery.get("type", discovery.get("discovery_type", ""))

        if discovery_type == "shared_entity" or discovery_type == "cross_domain_entity":
            entity = discovery.get("entity", "concept")
            topics = discovery.get("topics", [])
            topics_str = ", ".join(topics[:3])
            if len(topics) > 3:
                topics_str += f" and {len(topics) - 3} more"
            return f"The concept '{entity}' appears across distant domains: {topics_str}. This could reveal transferable patterns."

        elif discovery_type == "structural_analogy":
            pattern = discovery.get("pattern", "X relates to Y")
            examples = discovery.get("examples", [])
            examples_str = ", ".join([f"{a}:{b}" for a, b in examples[:2]])
            return f"Similar pattern detected: '{pattern}' (e.g., {examples_str}). Knowledge from one domain may apply to others."

        elif discovery_type == "bridging_query":
            query = discovery.get("query", "query")
            domains = discovery.get("domains", discovery.get("topics", []))
            domains_str = " and ".join(domains[:2])
            return f"Your question connects {domains_str}: '{query[:50]}...'. You may be developing expertise that bridges these fields."

        return "Cross-domain connection discovered."

    # ============================================================
    # DATA ACCESS (TO BE IMPLEMENTED WITH ACTUAL DB)
    # ============================================================

    async def _fetch_topic_summaries(
        self,
        user_id: str,
        tenant_id: str = "default"
    ) -> List[Any]:
        """Fetch topic summaries for user.

        Args:
            user_id: User ID
            tenant_id: Tenant ID

        Returns:
            List of topic summaries
        """
        # TODO: Implement actual database fetch
        # from src.storage.weaviate_store import WeaviateStore
        # store = WeaviateStore()
        # return await store.fetch_topic_summaries(user_id)
        return []

    async def _fetch_query_history(
        self,
        user_id: str,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """Fetch recent query history for user.

        Args:
            user_id: User ID
            days: Number of days to look back

        Returns:
            List of query records
        """
        # TODO: Implement actual database fetch
        return []

    async def _fetch_existing_discoveries(
        self,
        user_id: str
    ) -> List[Any]:
        """Fetch existing discoveries to avoid duplicates.

        Args:
            user_id: User ID

        Returns:
            List of existing discoveries
        """
        # TODO: Implement actual database fetch
        return []

    async def _save_discoveries(
        self,
        discoveries: List[Discovery],
        user_id: str,
        tenant_id: str
    ) -> bool:
        """Save discoveries to database.

        Args:
            discoveries: Discoveries to save
            user_id: User ID
            tenant_id: Tenant ID

        Returns:
            Success boolean
        """
        # TODO: Implement actual database save
        logger.info(f"Would save {len(discoveries)} discoveries for user {user_id}")
        return True

    # ============================================================
    # UTILITIES
    # ============================================================

    def _discovery_to_dict(self, discovery: Discovery) -> Dict[str, Any]:
        """Convert Discovery to dict.

        Args:
            discovery: Discovery object

        Returns:
            Dict representation
        """
        return {
            "type": discovery.discovery_type,
            "discovery_type": discovery.discovery_type,
            "entity": discovery.entity,
            "topics": discovery.topics,
            "domains": discovery.domains or discovery.topics,
            "pattern": discovery.pattern,
            "examples": discovery.examples,
            "query": discovery.query,
            "description": discovery.description,
            "insight_text": discovery.insight_text,
            "novelty": discovery.novelty,
            "distance": discovery.distance,
            "creativity_score": discovery.creativity_score,
            "score": discovery.score,
            "created_at": discovery.created_at.isoformat(),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get recombinator stats.

        Returns:
            Stats dict
        """
        return {
            "total_discoveries": self._stats["total_discoveries"],
            "discoveries_by_type": self._stats["discoveries_by_type"].copy(),
            "last_run": self._stats["last_run"],
            "last_run_discoveries": self._stats["last_run_discoveries"],
            "config": {
                "min_domain_distance": self.config.min_domain_distance,
                "min_novelty_score": self.config.min_novelty_score,
                "max_discoveries_per_run": self.config.max_discoveries_per_run,
            }
        }
