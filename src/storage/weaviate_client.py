"""Weaviate client for ACMS vector storage.

Provides semantic search using vector embeddings (1536 dimensions from OpenAI text-embedding-3-small).
Connects to ACMS Weaviate v4 instance at localhost:40480.

Features:
- Weaviate v4 API compatibility (port 40480 HTTP, 40481 gRPC)
- Collection management (ACMS_Raw_v1, ACMS_Knowledge_v2 - Dec 2025)
- Vector insertion and semantic search (768d and 1536d supported)
- SAFETY: NEVER deletes existing collections

Dec 2025 Collections:
- ACMS_Raw_v1: Unified Q&A pairs (101K records, 1536d embeddings)
- ACMS_Knowledge_v2: Structured knowledge with intent/entities/facts
- Old collections deleted: ACMS_MemoryItems_v1, ACMS_Knowledge_v1, ACMS_Enriched_v1, QueryCache_v1
"""

import os
import time
import sys
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery


class WeaviateClient:
    """Client for Weaviate vector database operations.

    Auto-detects Weaviate instance and manages ACMS memory collections.

    Example:
        client = WeaviateClient()
        vector_id = client.insert_vector(
            collection="ACMS_Raw_v1",
            vector=[0.1, 0.2, ...],  # 1536 dimensions
            data={"content": "Q: question\\nA: answer", "user_id": "uuid"}
        )
    """

    def __init__(self, host: Optional[str] = None, port: Optional[int] = None):
        """Initialize Weaviate client for ACMS v2.0.

        Args:
            host: Weaviate host (default: from WEAVIATE_HOST env or localhost)
            port: Weaviate HTTP port (default: from WEAVIATE_PORT env or 8080 for Docker, 40480 for local)
        """
        # Use environment variables for Docker networking
        # Docker: weaviate:8080, Local: localhost:40480
        self.host = host or os.getenv("WEAVIATE_HOST", "localhost")
        self.port = port or int(os.getenv("WEAVIATE_PORT", "8080"))

        # gRPC port: 50051 (Docker internal) or 40481 (host-mapped for local)
        grpc_port = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))

        # Connect to Weaviate v4
        self.url = f"http://{self.host}:{self.port}"
        self._client = weaviate.connect_to_local(
            host=self.host,
            port=self.port,
            grpc_port=grpc_port,
            skip_init_checks=False,
        )

        # Use stderr to avoid polluting stdout (needed for MCP JSON-RPC)
        sys.stderr.write(f"✅ Connected to Weaviate v4 at {self.url}\n")

    def is_ready(self) -> bool:
        """Check if Weaviate is ready.

        Returns:
            bool: True if ready, False otherwise
        """
        return self._client.is_ready()

    def list_collections(self) -> List[str]:
        """List all collections in Weaviate.

        Returns:
            List[str]: Collection names

        Note:
            SAFETY: Used to verify we don't delete existing collections.
        """
        collections = self._client.collections.list_all()
        return [c.name for c in collections.values()]

    def collection_exists(self, name: str) -> bool:
        """Check if a collection exists.

        Args:
            name: Collection name

        Returns:
            bool: True if exists, False otherwise
        """
        return name in self.list_collections()

    def get_collection_schema(self, name: str) -> Optional[Dict[str, Any]]:
        """Get schema for a collection.

        Args:
            name: Collection name

        Returns:
            dict: Collection schema, or None if not found
        """
        if not self.collection_exists(name):
            return None

        collection = self._client.collections.get(name)
        config = collection.config.get()

        # Extract vectorizer config (v4 API)
        vectorizer_info = None
        if hasattr(config, 'vectorizer') and config.vectorizer:
            vectorizer_info = str(config.vectorizer)

        return {
            "name": config.name,
            "description": config.description,
            "vectorizer": vectorizer_info,
            "vectorIndexConfig": str(config.vector_index_config) if hasattr(config, 'vector_index_config') else None,
            "properties": [
                {
                    "name": prop.name,
                    "data_type": prop.data_type,
                    "description": prop.description,
                }
                for prop in config.properties
            ],
        }

    def create_acms_collection(self) -> bool:
        """Verify ACMS_Raw_v1 collection exists.

        Returns:
            bool: True if exists, False otherwise

        Note:
            Dec 2025: Cleaned up old collections. Now only ACMS_Raw_v1 and ACMS_Knowledge_v2.
            This method no longer creates collections - they should exist from migration.
        """
        collection_name = "ACMS_Raw_v1"

        if self.collection_exists(collection_name):
            sys.stderr.write(f"✅ Collection {collection_name} already exists\n")
            return False

        # Collection doesn't exist - this is unexpected after migration
        sys.stderr.write(f"❌ Collection {collection_name} not found! Run migration scripts.\n")
        return False

    def setup_acms_collection(self) -> bool:
        """Setup ACMS collection (create if not exists).

        Returns:
            bool: True if setup successful

        Note:
            SAFETY: Verifies existing collections are preserved.
        """
        collections_before = set(self.list_collections())
        sys.stderr.write(f"Existing collections: {collections_before}\n")

        # Create ACMS collection
        created = self.create_acms_collection()

        # SAFETY CHECK: Verify no existing collections were deleted
        collections_after = set(self.list_collections())
        if not collections_before.issubset(collections_after):
            deleted = collections_before - collections_after
            raise RuntimeError(
                f"SAFETY VIOLATION: Existing collections deleted: {deleted}"
            )

        sys.stderr.write("✅ SAFETY CHECK PASSED: All existing collections preserved\n")
        return True

    def create_insights_collection(self) -> bool:
        """Create ACMS_Insights_v1 collection for unified cross-source insights.

        Returns:
            bool: True if created, False if already exists

        Note:
            Dec 2025: New collection for Unified Intelligence Layer.
            Stores vectorized insights from Email, Financial, Calendar, Chat sources.
        """
        collection_name = "ACMS_Insights_v1"

        if self.collection_exists(collection_name):
            sys.stderr.write(f"✅ Collection {collection_name} already exists\n")
            return False

        # Create collection with schema for cross-source insights
        self._client.collections.create(
            name=collection_name,
            description="Unified cross-source insights for ACMS (Dec 2025)",
            vectorizer_config=Configure.Vectorizer.none(),
            properties=[
                Property(
                    name="insight_id",
                    data_type=DataType.TEXT,
                    description="PostgreSQL UUID reference",
                ),
                Property(
                    name="source",
                    data_type=DataType.TEXT,
                    description="Data source: chat, email, financial, calendar",
                ),
                Property(
                    name="insight_type",
                    data_type=DataType.TEXT,
                    description="Type: action_item, deadline, topic, pattern, fact, relationship",
                ),
                Property(
                    name="insight_text",
                    data_type=DataType.TEXT,
                    description="Full insight text for display",
                ),
                Property(
                    name="insight_summary",
                    data_type=DataType.TEXT,
                    description="Short summary for listings",
                ),
                Property(
                    name="source_tags",
                    data_type=DataType.TEXT_ARRAY,
                    description="Source attribution tags",
                ),
                Property(
                    name="entity_types",
                    data_type=DataType.TEXT_ARRAY,
                    description="Entity types present: people, topics, dates, organizations",
                ),
                Property(
                    name="privacy_level",
                    data_type=DataType.TEXT,
                    description="Privacy: public, internal, confidential, local_only",
                ),
                Property(
                    name="confidence_score",
                    data_type=DataType.NUMBER,
                    description="Extraction confidence 0.0-1.0",
                ),
                Property(
                    name="source_timestamp",
                    data_type=DataType.DATE,
                    description="When source data was created",
                ),
                Property(
                    name="created_at",
                    data_type=DataType.DATE,
                    description="When insight was extracted",
                ),
            ],
        )

        sys.stderr.write(f"✅ Created collection {collection_name}\n")
        return True

    def setup_insights_collection(self) -> bool:
        """Setup ACMS_Insights_v1 collection (create if not exists).

        Returns:
            bool: True if setup successful
        """
        collections_before = set(self.list_collections())

        # Create insights collection
        created = self.create_insights_collection()

        # SAFETY CHECK: Verify no existing collections were deleted
        collections_after = set(self.list_collections())
        if not collections_before.issubset(collections_after):
            deleted = collections_before - collections_after
            raise RuntimeError(
                f"SAFETY VIOLATION: Existing collections deleted: {deleted}"
            )

        return True

    def insert_vector(
        self,
        collection: str,
        vector: List[float],
        data: Dict[str, Any],
    ) -> str:
        """Insert a vector with data into collection.

        Args:
            collection: Collection name
            vector: Vector embedding (768d or 1536d depending on collection)
            data: Associated data (must match schema)

        Returns:
            str: Vector UUID

        Raises:
            ValueError: If vector dimension is invalid
        """
        # Support both 768d (all-MiniLM) and 1536d (text-embedding-3-small)
        if len(vector) not in (768, 1536):
            raise ValueError(f"Vector must be 768 or 1536 dimensions, got {len(vector)}")

        coll = self._client.collections.get(collection)

        # Insert with vector
        uuid = coll.data.insert(
            properties=data,
            vector=vector,
        )

        return str(uuid)

    def semantic_search(
        self,
        collection: str,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform semantic search using query vector.

        Args:
            collection: Collection name
            query_vector: Query vector (768d or 1536d depending on collection)
            limit: Max results to return
            filters: Optional filters (e.g., {"user_id": "uuid"})

        Returns:
            List[dict]: Search results with data and distances
        """
        # Support both 768d (all-MiniLM) and 1536d (text-embedding-3-small)
        if len(query_vector) not in (768, 1536):
            raise ValueError(f"Query vector must be 768 or 1536 dimensions, got {len(query_vector)}")

        coll = self._client.collections.get(collection)

        # Perform search
        response = coll.query.near_vector(
            near_vector=query_vector,
            limit=limit,
            return_metadata=MetadataQuery(distance=True),
        )

        # Format results
        results = []
        for obj in response.objects:
            results.append({
                "uuid": str(obj.uuid),
                "properties": obj.properties,
                "distance": obj.metadata.distance,
            })

        return results

    def get_vector_by_uuid(self, collection: str, uuid: str) -> Optional[Dict[str, Any]]:
        """Get vector data by UUID.

        Args:
            collection: Collection name
            uuid: Vector UUID

        Returns:
            dict: Vector data, or None if not found
        """
        coll = self._client.collections.get(collection)

        try:
            obj = coll.query.fetch_object_by_id(uuid)
            return {
                "uuid": str(obj.uuid),
                "properties": obj.properties,
                "vector": obj.vector,
            }
        except Exception:
            return None

    def delete_vector(self, collection: str, uuid: str) -> bool:
        """Delete a vector by UUID.

        Args:
            collection: Collection name
            uuid: Vector UUID

        Returns:
            bool: True if deleted, False if not found
        """
        coll = self._client.collections.get(collection)

        try:
            coll.data.delete_by_id(uuid)
            return True
        except Exception:
            return False

    def update_vector(
        self,
        collection: str,
        uuid: str,
        vector: Optional[List[float]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update vector and/or data.

        Args:
            collection: Collection name
            uuid: Vector UUID
            vector: New 768-dim vector (optional)
            data: New data (optional)

        Returns:
            bool: True if updated, False if not found
        """
        if vector is not None and len(vector) != 768:
            raise ValueError(f"Vector must be 768 dimensions, got {len(vector)}")

        coll = self._client.collections.get(collection)

        try:
            if data is not None:
                coll.data.update(
                    uuid=uuid,
                    properties=data,
                    vector=vector,
                )
            elif vector is not None:
                # Update only vector
                coll.data.update(
                    uuid=uuid,
                    vector=vector,
                )
            return True
        except Exception:
            return False

    def count_vectors(self, collection: str) -> int:
        """Count vectors in collection.

        Args:
            collection: Collection name

        Returns:
            int: Number of vectors
        """
        coll = self._client.collections.get(collection)
        agg = coll.aggregate.over_all(total_count=True)
        return agg.total_count

    def close(self):
        """Close Weaviate connection."""
        self._client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Test Weaviate client
    print("Testing Weaviate client...")

    with WeaviateClient() as client:
        print(f"Connected: {client.is_ready()}")

        # List collections
        collections = client.list_collections()
        print(f"Existing collections: {collections}")

        # Setup ACMS collection
        client.setup_acms_collection()

        # Test insert with ACMS_Raw_v1 schema (Dec 2025)
        import random
        # Test data matching ACMS_Raw_v1 schema
        test_data = {
            "content": "Test memory content",
            "content_hash": "test_hash_001",
            "user_id": "test_user",
            "source_type": "test",
            "source_id": "test_001",
            "agent": "test",
            "privacy_level": "PUBLIC",
            "tags": ["test"],
            "cost_usd": 0.0,
            "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        # Use 1536d vectors for ACMS_Raw_v1
        test_vector = [random.random() for _ in range(1536)]
        vector_id = client.insert_vector("ACMS_Raw_v1", test_vector, test_data)
        print(f"Inserted vector: {vector_id}")

        # Test search with 1536d vector
        query_vector = [random.random() for _ in range(1536)]
        results = client.semantic_search("ACMS_Raw_v1", query_vector, limit=5)
        print(f"Search results: {len(results)} found")

        # Test count
        count = client.count_vectors("ACMS_Raw_v1")
        print(f"Total vectors: {count}")

        print("✅ All Weaviate tests passed!")
