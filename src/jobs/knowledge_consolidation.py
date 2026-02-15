"""Knowledge Consolidation Job for ACMS.

Sprint 3: Knowledge Consolidation for UX Improvements

This job consolidates similar knowledge items by:
1. Fetching new knowledge items (last 24h)
2. Finding similar existing consolidated_knowledge (similarity > 0.9)
3. Either merging with existing or creating new record
4. Creating provenance records for source attribution
5. Updating domain counts

Run daily to keep knowledge base clean and authoritative.
"""

import asyncio
import hashlib
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
from uuid import uuid4

from src.jobs.job_runner import run_job_with_tracking
from src.storage.database import get_db_pool

logger = logging.getLogger(__name__)


def get_confidence_indicator(confidence: float) -> Tuple[str, str]:
    """Get visual indicator and color for confidence level.

    Args:
        confidence: Confidence score (0.0 to 1.0)

    Returns:
        Tuple of (dots string, color name)
    """
    if confidence >= 0.8:
        return ('●●●●○', 'green')
    elif confidence >= 0.6:
        return ('●●●○○', 'blue')
    elif confidence >= 0.4:
        return ('●●○○○', 'yellow')
    elif confidence >= 0.2:
        return ('●○○○○', 'orange')
    else:
        return ('○○○○○', 'red')


class KnowledgeConsolidationJob:
    """
    Consolidates similar knowledge items into authoritative entries.

    Algorithm:
    1. Fetch new knowledge items from recent conversations
    2. For each item, search for similar existing consolidated_knowledge
    3. If similar (>0.9): increment source_count, update source_boost
    4. If not similar: create new consolidated_knowledge
    5. Create provenance record for source attribution
    6. Update domain counts
    """

    SIMILARITY_THRESHOLD = 0.7  # Lower threshold for semantic similarity
    SOURCE_BOOST_PER_SOURCE = 0.05
    MAX_SOURCE_BOOST = 0.5
    VERIFICATION_BOOST = 0.25

    def __init__(
        self,
        db_pool=None,
        weaviate_client=None,
        window_hours: int = 24,
        tenant_id: str = "default"
    ):
        """Initialize the knowledge consolidation job.

        Args:
            db_pool: Database connection pool
            weaviate_client: Weaviate client for similarity search
            window_hours: Hours of history to process
            tenant_id: Tenant identifier
        """
        self.db_pool = db_pool
        self.weaviate_client = weaviate_client
        self.window_hours = window_hours
        self.tenant_id = tenant_id

    async def run(self) -> Dict[str, Any]:
        """Execute the knowledge consolidation job.

        Returns:
            Dict with job statistics
        """
        stats = {
            "items_processed": 0,
            "new_knowledge": 0,
            "consolidated": 0,
            "provenance_created": 0,
            "errors": 0,
            "error_summary": None
        }

        try:
            # Fetch new knowledge items
            logger.info("[KnowledgeConsolidation] Fetching new knowledge items...")
            new_items = await self._fetch_new_knowledge_items()

            if not new_items:
                logger.info("[KnowledgeConsolidation] No new knowledge items found")
                return stats

            logger.info(f"[KnowledgeConsolidation] Found {len(new_items)} items to process")

            # Process each item
            for item in new_items:
                try:
                    result = await self.consolidate_knowledge(
                        content=item.get('content', ''),
                        source_type=item.get('source_type', 'query_history'),
                        source_id=item.get('source_id'),
                        base_confidence=item.get('confidence', 0.5),
                        source_preview=item.get('preview', '')[:200]
                    )

                    if result.get('is_new'):
                        stats['new_knowledge'] += 1
                    else:
                        stats['consolidated'] += 1

                    stats['items_processed'] += 1
                    stats['provenance_created'] += 1

                except Exception as e:
                    logger.error(f"[KnowledgeConsolidation] Error processing item: {e}")
                    stats['errors'] += 1

            logger.info(
                f"[KnowledgeConsolidation] Complete: {stats['items_processed']} processed, "
                f"{stats['new_knowledge']} new, {stats['consolidated']} consolidated"
            )

        except Exception as e:
            logger.error(f"[KnowledgeConsolidation] Job failed: {e}")
            stats['errors'] += 1
            stats['error_summary'] = str(e)[:500]

        return stats

    def should_consolidate(self, content1: str, content2: str) -> bool:
        """Determine if two knowledge items should be consolidated.

        Uses normalized string similarity and word overlap.

        Args:
            content1: First content string
            content2: Second content string

        Returns:
            True if similarity > 0.9
        """
        # Normalize both contents
        norm1 = self._normalize_content(content1)
        norm2 = self._normalize_content(content2)

        # Exact match
        if norm1 == norm2:
            return True

        # Word-based Jaccard similarity
        words1 = set(norm1.split())
        words2 = set(norm2.split())

        if not words1 or not words2:
            return False

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        similarity = intersection / union if union > 0 else 0

        return similarity >= self.SIMILARITY_THRESHOLD

    def compute_content_hash(self, content: str) -> str:
        """Compute normalized hash of content for deduplication.

        Args:
            content: Content string

        Returns:
            SHA-256 hash of normalized content
        """
        normalized = self._normalize_content(content)
        return hashlib.sha256(normalized.encode()).hexdigest()

    def _normalize_content(self, content: str) -> str:
        """Normalize content for comparison.

        Lowercases, removes extra whitespace, strips punctuation.

        Args:
            content: Raw content string

        Returns:
            Normalized content
        """
        if not content:
            return ""

        # Lowercase
        normalized = content.lower()

        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)

        # Strip leading/trailing whitespace
        normalized = normalized.strip()

        return normalized

    def calculate_source_boost(self, source_count: int) -> float:
        """Calculate confidence boost from multiple sources.

        Formula: min(0.5, (source_count - 1) * 0.05)

        Args:
            source_count: Number of sources

        Returns:
            Source boost value
        """
        if source_count <= 1:
            return 0.0

        boost = (source_count - 1) * self.SOURCE_BOOST_PER_SOURCE
        return min(self.MAX_SOURCE_BOOST, boost)

    def get_verification_boost(self, is_verified: bool) -> float:
        """Get confidence boost from verification.

        Args:
            is_verified: Whether knowledge is verified

        Returns:
            Verification boost (0.25 if verified, 0.0 otherwise)
        """
        return self.VERIFICATION_BOOST if is_verified else 0.0

    def calculate_effective_confidence(
        self,
        base_confidence: float,
        source_count: int,
        is_verified: bool
    ) -> float:
        """Calculate effective confidence score.

        Formula: min(1.0, base + source_boost + verification_boost)

        Args:
            base_confidence: Initial confidence from extraction
            source_count: Number of confirming sources
            is_verified: Whether user has verified

        Returns:
            Effective confidence (0.0 to 1.0)
        """
        source_boost = self.calculate_source_boost(source_count)
        verification_boost = self.get_verification_boost(is_verified)

        effective = base_confidence + source_boost + verification_boost
        return min(1.0, max(0.0, effective))

    def extract_domain(self, content: str) -> str:
        """Extract domain path from content.

        Uses keyword matching to categorize content.

        Args:
            content: Knowledge content

        Returns:
            Domain path string (e.g., 'technology/programming')
        """
        content_lower = content.lower()

        # Domain keywords mapping
        domain_keywords = {
            'technology/programming': [
                'python', 'javascript', 'code', 'function', 'class',
                'api', 'programming', 'developer', 'software'
            ],
            'technology/databases': [
                'sql', 'database', 'postgres', 'mysql', 'mongodb',
                'query', 'table', 'index'
            ],
            'technology/devops': [
                'docker', 'kubernetes', 'deploy', 'ci/cd', 'aws',
                'cloud', 'server', 'container'
            ],
            'finance/accounts': [
                'account', 'bank', 'money', 'balance', 'transaction',
                'payment', 'credit', 'investment'
            ],
            'personal/preferences': [
                'prefer', 'like', 'favorite', 'always', 'usually',
                'i want', 'i need'
            ],
            'work/projects': [
                'project', 'task', 'deadline', 'meeting', 'team',
                'client', 'milestone'
            ]
        }

        best_domain = 'personal'
        best_score = 0

        for domain, keywords in domain_keywords.items():
            score = sum(1 for kw in keywords if kw in content_lower)
            if score > best_score:
                best_score = score
                best_domain = domain

        return best_domain

    async def consolidate_knowledge(
        self,
        content: str,
        source_type: str,
        source_id: str,
        base_confidence: float = 0.5,
        source_preview: str = ""
    ) -> Dict[str, Any]:
        """Consolidate a knowledge item.

        Finds similar existing knowledge or creates new.

        Args:
            content: Knowledge content
            source_type: Type of source (query_history, email, etc.)
            source_id: ID of source record
            base_confidence: Initial confidence score
            source_preview: Preview text from source

        Returns:
            Dict with consolidation result
        """
        pool = self.db_pool or await get_db_pool()
        content_hash = self.compute_content_hash(content)

        async with pool.acquire() as conn:
            # Check for existing knowledge with same hash
            existing = await conn.fetchrow("""
                SELECT knowledge_id, source_count, source_boost, is_verified
                FROM consolidated_knowledge
                WHERE content_hash = $1 AND is_active = TRUE
            """, content_hash)

            if existing:
                # Update existing
                new_source_count = existing['source_count'] + 1
                new_source_boost = self.calculate_source_boost(new_source_count)

                await conn.execute("""
                    UPDATE consolidated_knowledge
                    SET
                        source_count = $1,
                        source_boost = $2,
                        last_confirmed_at = NOW(),
                        updated_at = NOW()
                    WHERE knowledge_id = $3
                """, new_source_count, new_source_boost, existing['knowledge_id'])

                knowledge_id = existing['knowledge_id']
                is_new = False
            else:
                # Create new
                domain = self.extract_domain(content)
                knowledge_type = self._infer_knowledge_type(content)

                row = await conn.fetchrow("""
                    INSERT INTO consolidated_knowledge (
                        canonical_content,
                        content_hash,
                        knowledge_type,
                        domain_path,
                        base_confidence,
                        source_count,
                        first_derived_at
                    ) VALUES ($1, $2, $3, $4, $5, 1, NOW())
                    RETURNING knowledge_id
                """, content, content_hash, knowledge_type, domain, base_confidence)

                knowledge_id = row['knowledge_id']
                is_new = True

            # Create provenance record
            contribution_type = 'original' if is_new else 'confirmation'
            await conn.execute("""
                INSERT INTO knowledge_provenance (
                    knowledge_id,
                    source_type,
                    source_id,
                    source_timestamp,
                    source_preview,
                    contribution_type,
                    confidence_at_extraction
                ) VALUES ($1, $2, $3, NOW(), $4, $5, $6)
            """, knowledge_id, source_type, source_id,
                source_preview[:200], contribution_type, base_confidence)

        return {
            'knowledge_id': str(knowledge_id),
            'is_new': is_new,
            'contribution_type': contribution_type
        }

    def _infer_knowledge_type(self, content: str) -> str:
        """Infer knowledge type from content.

        Types: fact, preference, definition, procedure

        Args:
            content: Knowledge content

        Returns:
            Knowledge type string
        """
        content_lower = content.lower()

        if any(kw in content_lower for kw in ['i prefer', 'i like', 'i always', 'i usually']):
            return 'preference'
        elif any(kw in content_lower for kw in ['is defined as', 'refers to', 'means']):
            return 'definition'
        elif any(kw in content_lower for kw in ['to do', 'step', 'first', 'then', 'finally', 'how to']):
            return 'procedure'
        else:
            return 'fact'

    async def _fetch_new_knowledge_items(self) -> List[Dict[str, Any]]:
        """Fetch knowledge items from recent conversations.

        Returns:
            List of knowledge item dicts
        """
        pool = self.db_pool or await get_db_pool()
        window_start = datetime.now(timezone.utc) - timedelta(hours=self.window_hours)

        async with pool.acquire() as conn:
            # Fetch from topic_extractions table
            rows = await conn.fetch("""
                SELECT
                    te.id as source_id,
                    te.extracted_text as content,
                    te.confidence,
                    'query_history' as source_type,
                    te.source_id as original_source_id,
                    qh.question as preview
                FROM topic_extractions te
                LEFT JOIN query_history qh ON qh.query_id::text = te.source_id
                LEFT JOIN knowledge_provenance kp ON kp.source_id = te.id
                WHERE te.created_at >= $1
                  AND kp.provenance_id IS NULL
                  AND te.extracted_text IS NOT NULL
                ORDER BY te.created_at DESC
                LIMIT 500
            """, window_start)

            return [
                {
                    'source_id': str(row['source_id']),
                    'content': row['content'],
                    'confidence': row['confidence'] or 0.5,
                    'source_type': row['source_type'],
                    'preview': row['preview'] or ''
                }
                for row in rows
            ]


# ============================================================================
# JOB ENTRY POINT
# ============================================================================

async def knowledge_consolidation_job(
    window_hours: int = 24,
    tenant_id: str = "default"
) -> Dict[str, Any]:
    """Entry point for knowledge consolidation job.

    Args:
        window_hours: Hours of history to process
        tenant_id: Tenant to process

    Returns:
        Job statistics
    """
    job = KnowledgeConsolidationJob(
        window_hours=window_hours,
        tenant_id=tenant_id
    )
    return await job.run()


async def run_knowledge_consolidation():
    """Run knowledge consolidation with job tracking."""
    return await run_job_with_tracking(
        job_name="knowledge_consolidation",
        job_func=knowledge_consolidation_job,
        tenant_id="default"
    )
