"""Memory Cluster Discovery Job for ACMS.

Sprint 2: Memory Clustering for UX Improvements

This job discovers and manages memory clusters by:
1. Fetching unassigned memories
2. Getting embeddings from Weaviate
3. Running DBSCAN clustering
4. Generating cluster names via LLM
5. Creating/updating cluster records
6. Assigning memories to clusters

Run weekly or on-demand to keep clusters up-to-date.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, List, Tuple
from uuid import uuid4

import numpy as np
from sklearn.cluster import DBSCAN

from src.jobs.job_runner import run_job_with_tracking
from src.storage.database import get_db_pool

logger = logging.getLogger(__name__)


class ClusterDiscoveryJob:
    """
    Discovers and maintains memory clusters using DBSCAN clustering.

    Algorithm:
    1. Fetch all unassigned memories from the database
    2. Get embeddings from Weaviate
    3. Run DBSCAN clustering (eps=0.15, min_samples=3)
    4. For each cluster:
       - Generate display name via LLM
       - Compute centroid embedding
       - Create/update memory_clusters record
    5. Assign memories to clusters with similarity scores
    """

    def __init__(
        self,
        db_pool=None,
        weaviate_client=None,
        eps: float = 0.15,
        min_samples: int = 3,
        max_clusters_per_run: int = 50,
        tenant_id: str = "default"
    ):
        """Initialize the cluster discovery job.

        Args:
            db_pool: Database connection pool
            weaviate_client: Weaviate client for embeddings
            eps: DBSCAN epsilon (max distance between samples)
            min_samples: DBSCAN minimum samples per cluster
            max_clusters_per_run: Maximum new clusters to create per run
            tenant_id: Tenant identifier
        """
        self.db_pool = db_pool
        self.weaviate_client = weaviate_client
        self.eps = eps
        self.min_samples = min_samples
        self.max_clusters_per_run = max_clusters_per_run
        self.tenant_id = tenant_id

    async def run(self) -> Dict[str, Any]:
        """Execute the cluster discovery job.

        Returns:
            Dict with job statistics
        """
        stats = {
            "input_count": 0,
            "clusters_created": 0,
            "clusters_updated": 0,
            "memories_assigned": 0,
            "errors": 0,
            "error_summary": None
        }

        try:
            # Step 1: Fetch unassigned memories
            logger.info("[ClusterDiscovery] Fetching unassigned memories...")
            memory_ids = await self._fetch_unassigned_memories()
            stats["input_count"] = len(memory_ids)

            if not memory_ids:
                logger.info("[ClusterDiscovery] No unassigned memories found")
                return stats

            logger.info(f"[ClusterDiscovery] Found {len(memory_ids)} unassigned memories")

            # Step 2: Get embeddings from Weaviate
            logger.info("[ClusterDiscovery] Fetching embeddings from Weaviate...")
            embeddings, memory_contents = await self._get_embeddings(memory_ids)

            if len(embeddings) < self.min_samples:
                logger.info(f"[ClusterDiscovery] Not enough memories ({len(embeddings)}) for clustering")
                return stats

            # Step 3: Run DBSCAN clustering
            logger.info("[ClusterDiscovery] Running DBSCAN clustering...")
            clusters = self._cluster_embeddings(embeddings)

            if not clusters:
                logger.info("[ClusterDiscovery] No clusters found")
                return stats

            logger.info(f"[ClusterDiscovery] Found {len(clusters)} clusters")

            # Step 4: Process each cluster
            for cluster_indices in clusters[:self.max_clusters_per_run]:
                try:
                    # Get sample contents for cluster naming
                    sample_contents = [
                        memory_contents[i] for i in cluster_indices[:5]
                        if i < len(memory_contents)
                    ]

                    # Generate cluster name
                    display_name = await self._generate_cluster_name(sample_contents)
                    canonical_topic = self._slugify(display_name)

                    # Compute centroid
                    centroid = self._compute_centroid(embeddings, cluster_indices)

                    # Create cluster record
                    cluster_id = await self._create_cluster(
                        canonical_topic=canonical_topic,
                        display_name=display_name,
                        description=f"Cluster of {len(cluster_indices)} related memories",
                        member_count=len(cluster_indices)
                    )

                    stats["clusters_created"] += 1

                    # Assign memories to cluster
                    for idx in cluster_indices:
                        memory_id = memory_ids[idx]
                        similarity = self._compute_similarity(embeddings[idx], centroid)
                        is_canonical = (idx == cluster_indices[0])  # First member is canonical

                        await self._assign_to_cluster(
                            memory_id=memory_id,
                            cluster_id=cluster_id,
                            similarity=similarity,
                            is_canonical=is_canonical
                        )
                        stats["memories_assigned"] += 1

                except Exception as e:
                    logger.error(f"[ClusterDiscovery] Error processing cluster: {e}")
                    stats["errors"] += 1

            logger.info(
                f"[ClusterDiscovery] Complete: {stats['clusters_created']} clusters, "
                f"{stats['memories_assigned']} memories assigned"
            )

        except Exception as e:
            logger.error(f"[ClusterDiscovery] Job failed: {e}")
            stats["errors"] += 1
            stats["error_summary"] = str(e)[:500]

        return stats

    async def _fetch_unassigned_memories(self) -> List[str]:
        """Fetch memory IDs not yet assigned to any cluster.

        Returns:
            List of memory IDs
        """
        pool = self.db_pool or await get_db_pool()

        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT qh.query_id as memory_id
                FROM query_history qh
                LEFT JOIN memory_cluster_members mcm ON mcm.memory_id = qh.query_id
                WHERE mcm.cluster_id IS NULL
                  AND qh.question IS NOT NULL
                  AND qh.answer IS NOT NULL
                ORDER BY qh.created_at DESC
                LIMIT 1000
            """)

            return [str(row['memory_id']) for row in rows]

    async def _get_embeddings(
        self,
        memory_ids: List[str]
    ) -> Tuple[np.ndarray, List[str]]:
        """Get embeddings for memories from Weaviate.

        Args:
            memory_ids: List of memory IDs to fetch embeddings for

        Returns:
            Tuple of (embeddings array, content list)
        """
        embeddings = []
        contents = []

        if self.weaviate_client:
            # Fetch from Weaviate
            try:
                collection = self.weaviate_client.collections.get("ACMS_Raw_v1")

                for memory_id in memory_ids:
                    try:
                        result = collection.query.fetch_object_by_id(
                            memory_id,
                            include_vector=True
                        )
                        if result and result.vector:
                            embeddings.append(result.vector)
                            contents.append(result.properties.get('content', '')[:500])
                    except Exception as e:
                        logger.debug(f"Could not fetch embedding for {memory_id}: {e}")

            except Exception as e:
                logger.error(f"Weaviate fetch error: {e}")

        # Fallback: generate random embeddings for testing
        if not embeddings:
            logger.warning("[ClusterDiscovery] Using mock embeddings (Weaviate unavailable)")
            pool = self.db_pool or await get_db_pool()

            async with pool.acquire() as conn:
                for memory_id in memory_ids[:100]:  # Limit for mock
                    row = await conn.fetchrow("""
                        SELECT question, answer FROM query_history
                        WHERE query_id = $1
                    """, memory_id)

                    if row:
                        content = f"{row['question']} {row['answer']}"[:500]
                        contents.append(content)
                        # Mock embedding (would use real embeddings in production)
                        np.random.seed(hash(memory_id) % 2**32)
                        embeddings.append(np.random.randn(1536).astype(np.float32))

        return np.array(embeddings) if embeddings else np.array([]), contents

    def _cluster_embeddings(
        self,
        embeddings: np.ndarray,
        eps: float = None,
        min_samples: int = None
    ) -> List[List[int]]:
        """Run DBSCAN clustering on embeddings.

        Args:
            embeddings: Numpy array of embeddings
            eps: DBSCAN epsilon (default: self.eps)
            min_samples: Minimum samples per cluster (default: self.min_samples)

        Returns:
            List of clusters, where each cluster is a list of indices
        """
        if len(embeddings) == 0:
            return []

        eps = eps or self.eps
        min_samples = min_samples or self.min_samples

        # Normalize embeddings for cosine distance
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        normalized = embeddings / norms

        # DBSCAN with cosine distance (using 1 - cosine_similarity)
        # For normalized vectors: cosine_distance = 1 - dot_product
        # We use precomputed distance matrix for cosine
        similarity_matrix = np.dot(normalized, normalized.T)
        distance_matrix = 1 - similarity_matrix
        np.fill_diagonal(distance_matrix, 0)  # Self-distance is 0

        clustering = DBSCAN(
            eps=eps,
            min_samples=min_samples,
            metric='precomputed'
        ).fit(distance_matrix)

        # Group indices by cluster label
        labels = clustering.labels_
        clusters = {}
        for idx, label in enumerate(labels):
            if label >= 0:  # Ignore noise (label = -1)
                if label not in clusters:
                    clusters[label] = []
                clusters[label].append(idx)

        return list(clusters.values())

    async def _generate_cluster_name(self, sample_contents: List[str]) -> str:
        """Generate a display name for a cluster using LLM.

        Args:
            sample_contents: Sample text content from cluster members

        Returns:
            Generated cluster display name
        """
        try:
            return await self._call_llm_for_name(sample_contents)
        except Exception as e:
            logger.warning(f"LLM name generation failed: {e}")
            # Fallback name
            return f"Topic Cluster {datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"

    async def _call_llm_for_name(self, sample_contents: List[str]) -> str:
        """Call LLM to generate cluster name.

        Args:
            sample_contents: Sample text content from cluster members

        Returns:
            Generated cluster name
        """
        # Use Claude or another LLM to generate name
        # For now, use a simple heuristic
        import os

        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            # Fallback: extract key words
            all_text = " ".join(sample_contents).lower()
            words = all_text.split()
            # Simple frequency-based naming
            word_freq = {}
            for word in words:
                if len(word) > 4:  # Skip short words
                    word_freq[word] = word_freq.get(word, 0) + 1

            top_words = sorted(word_freq.items(), key=lambda x: -x[1])[:3]
            if top_words:
                return " & ".join(w[0].title() for w in top_words)
            return f"Topic {datetime.now(timezone.utc).strftime('%H%M')}"

        # Call Claude API
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)

            prompt = f"""Given these sample conversations from a memory cluster, generate a short, descriptive topic name (2-4 words max):

Samples:
{chr(10).join(f'- {c[:200]}' for c in sample_contents[:5])}

Respond with ONLY the topic name, nothing else."""

            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}]
            )

            name = response.content[0].text.strip()
            return name[:50]  # Limit length

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    def _compute_centroid(
        self,
        embeddings: np.ndarray,
        member_indices: List[int]
    ) -> np.ndarray:
        """Compute the centroid (mean) of cluster embeddings.

        Args:
            embeddings: Full embeddings array
            member_indices: Indices of cluster members

        Returns:
            Normalized centroid vector
        """
        member_embeddings = embeddings[member_indices]
        centroid = np.mean(member_embeddings, axis=0)

        # Normalize for cosine similarity
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm

        return centroid

    def _compute_similarity(
        self,
        embedding: np.ndarray,
        centroid: np.ndarray
    ) -> float:
        """Compute cosine similarity between embedding and centroid.

        Args:
            embedding: Single embedding vector
            centroid: Centroid vector

        Returns:
            Cosine similarity (0-1)
        """
        # Normalize embedding
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        # Cosine similarity = dot product of unit vectors
        similarity = float(np.dot(embedding, centroid))
        return max(0.0, min(1.0, similarity))  # Clamp to [0, 1]

    async def _get_connection(self):
        """Get a database connection."""
        pool = self.db_pool or await get_db_pool()
        return pool.acquire()

    async def _create_cluster(
        self,
        canonical_topic: str,
        display_name: str,
        description: str,
        member_count: int
    ) -> str:
        """Create a new cluster record in the database.

        Args:
            canonical_topic: Machine-readable topic slug
            display_name: Human-readable name
            description: Cluster description
            member_count: Initial member count

        Returns:
            New cluster ID
        """
        pool = self.db_pool or await get_db_pool()

        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO memory_clusters (
                    canonical_topic,
                    display_name,
                    description,
                    member_count,
                    first_memory_at,
                    last_memory_at
                ) VALUES ($1, $2, $3, $4, NOW(), NOW())
                RETURNING cluster_id
            """, canonical_topic, display_name, description, member_count)

            return str(row['cluster_id'])

    async def _assign_to_cluster(
        self,
        memory_id: str,
        cluster_id: str,
        similarity: float,
        is_canonical: bool = False
    ) -> None:
        """Assign a memory to a cluster.

        Args:
            memory_id: Memory ID to assign
            cluster_id: Cluster to assign to
            similarity: Similarity score (0-1)
            is_canonical: Whether this is the canonical member
        """
        pool = self.db_pool or await get_db_pool()

        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO memory_cluster_members (
                    cluster_id,
                    memory_id,
                    similarity_score,
                    is_canonical
                ) VALUES ($1, $2, $3, $4)
                ON CONFLICT (cluster_id, memory_id) DO UPDATE
                SET similarity_score = EXCLUDED.similarity_score,
                    is_canonical = EXCLUDED.is_canonical
            """, cluster_id, memory_id, similarity, is_canonical)

    def _slugify(self, text: str) -> str:
        """Convert text to a URL-safe slug.

        Args:
            text: Input text

        Returns:
            Slugified text
        """
        import re
        slug = text.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s-]+', '_', slug)
        return slug[:50]


# ============================================================================
# JOB ENTRY POINT
# ============================================================================

async def cluster_discovery_job(
    eps: float = 0.15,
    min_samples: int = 3,
    tenant_id: str = "default"
) -> Dict[str, Any]:
    """Entry point for cluster discovery job.

    Args:
        eps: DBSCAN epsilon parameter
        min_samples: DBSCAN minimum samples
        tenant_id: Tenant to process

    Returns:
        Job statistics
    """
    job = ClusterDiscoveryJob(
        eps=eps,
        min_samples=min_samples,
        tenant_id=tenant_id
    )
    return await job.run()


# Wrapper for job_runner
async def run_cluster_discovery():
    """Run cluster discovery with job tracking."""
    return await run_job_with_tracking(
        job_name="cluster_discovery",
        job_func=cluster_discovery_job,
        tenant_id="default"
    )
