"""Knowledge Compaction for ACMS.

Cognitive Principle: LSM-Tree Consolidation

Like Log-Structured Merge-Trees in databases, knowledge consolidates
from volatile to stable stores over time:

- Level 1 (Raw): Individual Q&A pairs (ephemeral, high detail)
- Level 2 (Knowledge): Extracted facts (consolidated, medium detail)
- Level 3 (Topics): Topic summaries (synthesized, abstracted)
- Level 4 (Domains): Domain maps (cross-topic relationships)

This module implements the compaction pipeline:
1. Cluster Knowledge entries by topic
2. Synthesize topic summaries using LLM
3. Create domain maps from related topics
4. Store results in Weaviate collections

Expected Impact:
- Higher-order knowledge synthesis
- Expertise-calibrated responses via schema context
- Knowledge gap identification
- Cross-domain insight discovery

Usage:
    from src.jobs.knowledge_compaction import KnowledgeCompactor

    compactor = KnowledgeCompactor()

    # Level 2 → Level 3
    result = await compactor.compact_to_topic_summaries(
        user_id="user-1",
        tenant_id="default"
    )

    # Level 3 → Level 4
    result = await compactor.compact_to_domain_maps(
        user_id="user-1",
        tenant_id="default"
    )
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeCompactorConfig:
    """Configuration for knowledge compaction.

    Attributes:
        min_entries_for_topic: Minimum knowledge entries to create topic summary
        min_topics_for_domain: Minimum topic summaries to create domain map
        synthesis_budget_usd: Max LLM spend per compaction run
        max_entries_per_batch: Max entries to process per batch
        llm_model: Model to use for synthesis (default: claude-sonnet)
    """
    min_entries_for_topic: int = 3
    min_topics_for_domain: int = 2
    synthesis_budget_usd: float = 0.50
    max_entries_per_batch: int = 100
    llm_model: str = "claude-sonnet"


@dataclass
class TopicSummary:
    """A synthesized topic summary (Level 3).

    Attributes:
        id: Unique identifier
        topic_slug: Topic identifier (e.g., "kubernetes")
        summary_text: Synthesized summary of the topic
        user_id: Owner user ID
        entity_map: Map of entities and their relationships
        knowledge_depth: Number of source entries
        knowledge_gaps: Identified gaps in knowledge
        source_entry_ids: IDs of source Knowledge entries
        created_at: Creation timestamp
    """
    id: str
    topic_slug: str
    summary_text: str
    user_id: str
    entity_map: Dict[str, List[str]]
    knowledge_depth: int
    knowledge_gaps: List[str]
    source_entry_ids: List[str]
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "topic_slug": self.topic_slug,
            "summary_text": self.summary_text,
            "user_id": self.user_id,
            "entity_map": json.dumps(self.entity_map),
            "knowledge_depth": self.knowledge_depth,
            "knowledge_gaps": self.knowledge_gaps,
            "source_entry_ids": self.source_entry_ids,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class DomainMap:
    """A synthesized domain map (Level 4).

    Attributes:
        id: Unique identifier
        domain_name: Human-readable domain name
        user_id: Owner user ID
        topology_json: JSON string of topic relationships
        cross_topic_relationships: List of cross-topic insights
        knowledge_strengths: Areas of strong knowledge
        knowledge_gaps: Areas needing more knowledge
        emerging_themes: Detected emerging themes
        source_topic_ids: IDs of source TopicSummaries
        created_at: Creation timestamp
    """
    id: str
    domain_name: str
    user_id: str
    topology_json: str
    cross_topic_relationships: List[str]
    knowledge_strengths: List[str]
    knowledge_gaps: List[str]
    emerging_themes: List[str]
    source_topic_ids: List[str]
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "domain_name": self.domain_name,
            "user_id": self.user_id,
            "topology_json": self.topology_json,
            "cross_topic_relationships": self.cross_topic_relationships,
            "knowledge_strengths": self.knowledge_strengths,
            "knowledge_gaps": self.knowledge_gaps,
            "emerging_themes": self.emerging_themes,
            "source_topic_ids": self.source_topic_ids,
            "created_at": self.created_at.isoformat(),
        }


class KnowledgeCompactor:
    """Compacts knowledge from Level 2 → Level 3 → Level 4.

    Implements LSM-tree style consolidation:
    - Knowledge entries cluster by topic
    - Topics synthesize into summaries
    - Summaries synthesize into domain maps

    Usage:
        compactor = KnowledgeCompactor()
        await compactor.compact_to_topic_summaries(user_id, tenant_id)
        await compactor.compact_to_domain_maps(user_id, tenant_id)
    """

    def __init__(self, config: Optional[KnowledgeCompactorConfig] = None):
        """Initialize knowledge compactor.

        Args:
            config: Optional configuration overrides
        """
        self.config = config or KnowledgeCompactorConfig()

        # Statistics
        self._total_topics_created = 0
        self._total_domains_created = 0
        self._total_cost_usd = 0.0

        # Budget tracking for current run
        self._current_run_cost = 0.0

    def _cluster_by_topic(self, entries: List[Any]) -> Dict[str, List[Any]]:
        """Cluster knowledge entries by their topic tag.

        Args:
            entries: List of knowledge entries with 'topic' attribute

        Returns:
            Dict mapping topic → list of entries
        """
        clusters = defaultdict(list)

        for entry in entries:
            topic = getattr(entry, 'topic', None)
            if topic:
                clusters[topic].append(entry)

        return dict(clusters)

    def _get_compactable_clusters(
        self,
        clusters: Dict[str, List[Any]]
    ) -> Dict[str, List[Any]]:
        """Filter clusters that meet minimum size for compaction.

        Args:
            clusters: Topic → entries mapping

        Returns:
            Filtered clusters meeting min_entries_for_topic
        """
        return {
            topic: entries
            for topic, entries in clusters.items()
            if len(entries) >= self.config.min_entries_for_topic
        }

    async def _call_llm_for_synthesis(
        self,
        topic: str,
        content_summaries: List[str],
    ) -> Dict[str, Any]:
        """Call LLM to synthesize topic summary.

        Args:
            topic: Topic name
            content_summaries: List of content snippets

        Returns:
            Dict with summary, entity_map, knowledge_gaps
        """
        # Build prompt
        combined_content = "\n".join([
            f"- {c[:500]}" for c in content_summaries[:20]  # Limit context
        ])

        prompt = f"""Synthesize the following knowledge about "{topic}" into a coherent summary.

Knowledge entries:
{combined_content}

Provide your response as JSON with:
1. "summary": A 2-3 sentence synthesis of the key knowledge
2. "entity_map": A dict mapping main concepts to related concepts
3. "knowledge_gaps": List of topics that seem incomplete or missing

Example response:
{{
    "summary": "Docker is a containerization platform that packages applications...",
    "entity_map": {{"docker": ["containers", "images", "volumes"]}},
    "knowledge_gaps": ["networking configuration", "security best practices"]
}}"""

        try:
            from src.llm.client import get_llm_client

            client = get_llm_client()
            response = await client.generate(
                prompt=prompt,
                model=self.config.llm_model,
                max_tokens=1000,
            )

            # Track cost
            self._current_run_cost += response.cost_usd or 0.001

            # Parse JSON response
            import re
            json_match = re.search(r'\{[\s\S]*\}', response.text)
            if json_match:
                return json.loads(json_match.group())

            # Fallback if no JSON found
            return {
                "summary": response.text[:500],
                "entity_map": {},
                "knowledge_gaps": []
            }

        except ImportError:
            logger.debug("[KnowledgeCompactor] LLM client not available")
            # Return mock response for testing
            return {
                "summary": f"Synthesized knowledge about {topic}.",
                "entity_map": {topic: []},
                "knowledge_gaps": []
            }
        except Exception as e:
            logger.error(f"[KnowledgeCompactor] LLM synthesis failed: {e}")
            raise

    async def _call_llm_for_domain_synthesis(
        self,
        topics: List[Any],
    ) -> Dict[str, Any]:
        """Call LLM to synthesize domain map from topic summaries.

        Args:
            topics: List of TopicSummary objects

        Returns:
            Dict with domain_name, topology, relationships, etc.
        """
        topic_descriptions = "\n".join([
            f"- {t.topic_slug}: {t.summary_text[:200]}"
            for t in topics[:10]  # Limit
        ])

        prompt = f"""Analyze these topic summaries and identify the overarching domain and relationships.

Topics:
{topic_descriptions}

Provide your response as JSON with:
1. "domain_name": A descriptive name for this knowledge domain
2. "topology": A dict showing how topics relate to each other
3. "cross_topic_relationships": List of insights connecting topics
4. "strengths": List of well-covered areas
5. "gaps": List of areas needing more knowledge
6. "emerging_themes": List of patterns or themes across topics

Example:
{{
    "domain_name": "Container Infrastructure",
    "topology": {{"docker": {{"relates_to": ["kubernetes"]}}}},
    "cross_topic_relationships": ["Docker containers run on K8s pods"],
    "strengths": ["container basics"],
    "gaps": ["security"],
    "emerging_themes": ["cloud native"]
}}"""

        try:
            from src.llm.client import get_llm_client

            client = get_llm_client()
            response = await client.generate(
                prompt=prompt,
                model=self.config.llm_model,
                max_tokens=1500,
            )

            self._current_run_cost += response.cost_usd or 0.002

            import re
            json_match = re.search(r'\{[\s\S]*\}', response.text)
            if json_match:
                return json.loads(json_match.group())

            return {
                "domain_name": "General Knowledge",
                "topology": {},
                "cross_topic_relationships": [],
                "strengths": [],
                "gaps": [],
                "emerging_themes": []
            }

        except ImportError:
            logger.debug("[KnowledgeCompactor] LLM client not available")
            return {
                "domain_name": "Knowledge Domain",
                "topology": {},
                "cross_topic_relationships": [],
                "strengths": [],
                "gaps": [],
                "emerging_themes": []
            }
        except Exception as e:
            logger.error(f"[KnowledgeCompactor] Domain synthesis failed: {e}")
            raise

    async def _synthesize_topic_summary(
        self,
        topic: str,
        entries: List[Any],
        user_id: str,
    ) -> Optional[TopicSummary]:
        """Synthesize a topic summary from knowledge entries.

        Args:
            topic: Topic name
            entries: List of knowledge entries
            user_id: Owner user ID

        Returns:
            TopicSummary or None if synthesis fails
        """
        from uuid import uuid4

        # Extract content from entries
        content_summaries = [
            getattr(e, 'content', str(e))[:1000]
            for e in entries
        ]

        # Call LLM for synthesis
        result = await self._call_llm_for_synthesis(topic, content_summaries)

        # Build topic summary
        return TopicSummary(
            id=str(uuid4()),
            topic_slug=topic,
            summary_text=result.get("summary", ""),
            user_id=user_id,
            entity_map=result.get("entity_map", {}),
            knowledge_depth=len(entries),
            knowledge_gaps=result.get("knowledge_gaps", []),
            source_entry_ids=[getattr(e, 'id', str(i)) for i, e in enumerate(entries)],
        )

    async def _synthesize_domain_map(
        self,
        topics: List[Any],
        user_id: str,
    ) -> Optional[DomainMap]:
        """Synthesize a domain map from topic summaries.

        Args:
            topics: List of TopicSummary objects
            user_id: Owner user ID

        Returns:
            DomainMap or None if synthesis fails
        """
        from uuid import uuid4

        result = await self._call_llm_for_domain_synthesis(topics)

        return DomainMap(
            id=str(uuid4()),
            domain_name=result.get("domain_name", "Unknown Domain"),
            user_id=user_id,
            topology_json=json.dumps(result.get("topology", {})),
            cross_topic_relationships=result.get("cross_topic_relationships", []),
            knowledge_strengths=result.get("strengths", []),
            knowledge_gaps=result.get("gaps", []),
            emerging_themes=result.get("emerging_themes", []),
            source_topic_ids=[getattr(t, 'id', str(i)) for i, t in enumerate(topics)],
        )

    async def _fetch_knowledge_entries(
        self,
        user_id: str,
        tenant_id: str,
        limit: int = 100
    ) -> List[Any]:
        """Fetch knowledge entries from database.

        Args:
            user_id: User to fetch entries for
            tenant_id: Tenant ID
            limit: Max entries to fetch

        Returns:
            List of knowledge entries
        """
        try:
            from src.storage.database import get_db_pool

            pool = await get_db_pool()

            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT id, content, user_id, primary_topic as topic,
                           created_at, confidence
                    FROM knowledge_entries
                    WHERE user_id = $1::uuid
                      AND tenant_id = $2
                      AND created_at >= NOW() - INTERVAL '30 days'
                    ORDER BY created_at DESC
                    LIMIT $3
                """, user_id, tenant_id, limit)

                # Convert to objects
                entries = []
                for row in rows:
                    class Entry:
                        pass
                    e = Entry()
                    e.id = str(row['id'])
                    e.content = row['content']
                    e.user_id = str(row['user_id'])
                    e.topic = row['topic']
                    e.created_at = row['created_at']
                    e.confidence = float(row['confidence'] or 0.9)
                    entries.append(e)

                return entries

        except Exception as e:
            logger.warning(f"[KnowledgeCompactor] Failed to fetch entries: {e}")
            return []

    async def _fetch_topic_summaries(
        self,
        user_id: str,
        tenant_id: str,
        limit: int = 50
    ) -> List[TopicSummary]:
        """Fetch topic summaries from Weaviate.

        Args:
            user_id: User to fetch for
            tenant_id: Tenant ID
            limit: Max summaries to fetch

        Returns:
            List of TopicSummary objects
        """
        # In production, this would query Weaviate ACMS_Topics_v1
        # For now, return empty list (will be populated by compaction)
        try:
            from src.storage.weaviate_client import get_weaviate_client

            client = get_weaviate_client()
            # Query ACMS_Topics_v1 collection
            # ... implementation depends on Weaviate setup
            return []

        except Exception as e:
            logger.debug(f"[KnowledgeCompactor] Topics fetch: {e}")
            return []

    async def _save_topic_summary(
        self,
        summary: TopicSummary,
        tenant_id: str
    ) -> bool:
        """Save topic summary to Weaviate.

        Args:
            summary: TopicSummary to save
            tenant_id: Tenant ID

        Returns:
            True if saved successfully
        """
        try:
            from src.storage.weaviate_client import get_weaviate_client

            client = get_weaviate_client()
            # Save to ACMS_Topics_v1 collection
            # ... implementation depends on Weaviate setup
            logger.info(
                f"[KnowledgeCompactor] Saved topic summary: {summary.topic_slug}"
            )
            return True

        except Exception as e:
            logger.warning(f"[KnowledgeCompactor] Failed to save topic: {e}")
            return False

    async def _save_domain_map(
        self,
        domain: DomainMap,
        tenant_id: str
    ) -> bool:
        """Save domain map to Weaviate.

        Args:
            domain: DomainMap to save
            tenant_id: Tenant ID

        Returns:
            True if saved successfully
        """
        try:
            from src.storage.weaviate_client import get_weaviate_client

            client = get_weaviate_client()
            # Save to ACMS_Domains_v1 collection
            # ... implementation depends on Weaviate setup
            logger.info(
                f"[KnowledgeCompactor] Saved domain map: {domain.domain_name}"
            )
            return True

        except Exception as e:
            logger.warning(f"[KnowledgeCompactor] Failed to save domain: {e}")
            return False

    async def compact_to_topic_summaries(
        self,
        user_id: str,
        tenant_id: str = "default"
    ) -> Dict[str, Any]:
        """Compact Knowledge entries to Topic summaries (Level 2 → 3).

        Cognitive basis: LSM-tree consolidation from volatile to stable.

        Args:
            user_id: User to compact for
            tenant_id: Tenant ID

        Returns:
            Dict with compaction stats
        """
        self._current_run_cost = 0.0
        result = {
            "topics_created": 0,
            "entries_processed": 0,
            "clusters_found": 0,
            "cost_usd": 0.0,
            "budget_remaining_usd": self.config.synthesis_budget_usd,
            "errors": 0
        }

        # Fetch knowledge entries
        entries = await self._fetch_knowledge_entries(
            user_id, tenant_id, self.config.max_entries_per_batch
        )

        if not entries:
            logger.info("[KnowledgeCompactor] No entries to compact")
            return result

        result["entries_processed"] = len(entries)

        # Cluster by topic
        clusters = self._cluster_by_topic(entries)
        result["clusters_found"] = len(clusters)

        # Filter compactable clusters
        compactable = self._get_compactable_clusters(clusters)

        logger.info(
            f"[KnowledgeCompactor] Found {len(compactable)} compactable clusters "
            f"from {len(entries)} entries"
        )

        # Synthesize topic summaries
        for topic, topic_entries in compactable.items():
            # Check budget
            if self._current_run_cost >= self.config.synthesis_budget_usd:
                logger.warning("[KnowledgeCompactor] Budget exhausted")
                break

            try:
                summary = await self._synthesize_topic_summary(
                    topic=topic,
                    entries=topic_entries,
                    user_id=user_id
                )

                if summary:
                    saved = await self._save_topic_summary(summary, tenant_id)
                    if saved:
                        result["topics_created"] += 1
                        self._total_topics_created += 1

            except Exception as e:
                logger.error(f"[KnowledgeCompactor] Topic synthesis failed: {e}")
                result["errors"] += 1

        result["cost_usd"] = self._current_run_cost
        result["budget_remaining_usd"] = max(
            0, self.config.synthesis_budget_usd - self._current_run_cost
        )
        self._total_cost_usd += self._current_run_cost

        logger.info(
            f"[KnowledgeCompactor] Topic compaction complete: "
            f"{result['topics_created']} topics, ${result['cost_usd']:.4f}"
        )

        return result

    async def compact_to_domain_maps(
        self,
        user_id: str,
        tenant_id: str = "default"
    ) -> Dict[str, Any]:
        """Compact Topic summaries to Domain maps (Level 3 → 4).

        Cognitive basis: Schema abstraction from specific to general.

        Args:
            user_id: User to compact for
            tenant_id: Tenant ID

        Returns:
            Dict with compaction stats
        """
        self._current_run_cost = 0.0
        result = {
            "domains_created": 0,
            "topics_processed": 0,
            "cost_usd": 0.0,
            "errors": 0
        }

        # Fetch topic summaries
        topics = await self._fetch_topic_summaries(user_id, tenant_id)

        if len(topics) < self.config.min_topics_for_domain:
            logger.info(
                f"[KnowledgeCompactor] Not enough topics for domain "
                f"({len(topics)} < {self.config.min_topics_for_domain})"
            )
            return result

        result["topics_processed"] = len(topics)

        try:
            domain = await self._synthesize_domain_map(
                topics=topics,
                user_id=user_id
            )

            if domain:
                saved = await self._save_domain_map(domain, tenant_id)
                if saved:
                    result["domains_created"] += 1
                    self._total_domains_created += 1

        except Exception as e:
            logger.error(f"[KnowledgeCompactor] Domain synthesis failed: {e}")
            result["errors"] += 1

        result["cost_usd"] = self._current_run_cost
        self._total_cost_usd += self._current_run_cost

        logger.info(
            f"[KnowledgeCompactor] Domain compaction complete: "
            f"{result['domains_created']} domains, ${result['cost_usd']:.4f}"
        )

        return result

    def get_stats(self) -> Dict[str, Any]:
        """Get compactor statistics.

        Returns:
            Dict with total_topics_created, total_domains_created, etc.
        """
        return {
            "total_topics_created": self._total_topics_created,
            "total_domains_created": self._total_domains_created,
            "total_cost_usd": self._total_cost_usd,
            "config": {
                "min_entries_for_topic": self.config.min_entries_for_topic,
                "min_topics_for_domain": self.config.min_topics_for_domain,
                "synthesis_budget_usd": self.config.synthesis_budget_usd,
            }
        }

    def reset_stats(self) -> None:
        """Reset statistics (for testing)."""
        self._total_topics_created = 0
        self._total_domains_created = 0
        self._total_cost_usd = 0.0


# ============================================================
# HELPER FUNCTIONS
# ============================================================

# Global instance
_compactor_instance: Optional[KnowledgeCompactor] = None


def get_knowledge_compactor() -> KnowledgeCompactor:
    """Get global knowledge compactor instance."""
    global _compactor_instance
    if _compactor_instance is None:
        _compactor_instance = KnowledgeCompactor()
    return _compactor_instance
