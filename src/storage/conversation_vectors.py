"""
Conversation Vector Storage - Weaviate Integration for Conversations

Handles vector storage for conversation threads and turns using Weaviate v4.
Provides semantic search across imported conversations from ChatGPT, Claude, Gemini.
"""

import sys
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.storage.weaviate_client import WeaviateClient
from weaviate.classes.config import Configure, Property, DataType, VectorDistances


class ConversationVectorStorage:
    """
    Manages vector storage for conversation threads and turns.

    Collections:
    - ACMS_ConversationThreads: Full conversation embeddings
    - ACMS_ConversationTurns: Individual turn embeddings
    """

    THREAD_COLLECTION = "ACMS_ConversationThreads"
    TURN_COLLECTION = "ACMS_ConversationTurns"

    def __init__(self, weaviate_client: Optional[WeaviateClient] = None):
        """
        Initialize conversation vector storage.

        Args:
            weaviate_client: Existing WeaviateClient instance (or create new one)
        """
        self.client = weaviate_client or WeaviateClient()

    def setup_collections(self) -> bool:
        """
        Create conversation collections if they don't exist.

        Returns:
            bool: True if setup successful
        """
        # Create thread collection
        self._create_thread_collection()

        # Create turn collection
        self._create_turn_collection()

        sys.stderr.write("✅ Conversation vector collections setup complete\n")
        return True

    def _create_thread_collection(self) -> bool:
        """Create ACMS_ConversationThreads collection."""
        if self.client.collection_exists(self.THREAD_COLLECTION):
            sys.stderr.write(f"✅ Collection {self.THREAD_COLLECTION} already exists\n")
            return False

        self.client._client.collections.create(
            name=self.THREAD_COLLECTION,
            description="Conversation thread embeddings (full conversations)",
            vectorizer_config=None,  # Manual vectors from OpenAI
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE
            ),
            properties=[
                Property(
                    name="content",
                    data_type=DataType.TEXT,
                    description="Full conversation text",
                ),
                Property(
                    name="thread_id",
                    data_type=DataType.TEXT,
                    description="PostgreSQL thread UUID",
                    skip_vectorization=True,
                ),
                Property(
                    name="user_id",
                    data_type=DataType.TEXT,
                    description="User UUID",
                    skip_vectorization=True,
                ),
                Property(
                    name="source",
                    data_type=DataType.TEXT,
                    description="Conversation source (chatgpt, claude, gemini)",
                    skip_vectorization=True,
                ),
                Property(
                    name="title",
                    data_type=DataType.TEXT,
                    description="Conversation title",
                ),
                Property(
                    name="turn_count",
                    data_type=DataType.INT,
                    description="Number of turns in conversation",
                    skip_vectorization=True,
                ),
                Property(
                    name="created_at",
                    data_type=DataType.DATE,
                    description="Original conversation creation timestamp",
                    skip_vectorization=True,
                ),
                Property(
                    name="imported_at",
                    data_type=DataType.DATE,
                    description="Import timestamp",
                    skip_vectorization=True,
                ),
            ],
        )

        sys.stderr.write(f"✅ Created collection {self.THREAD_COLLECTION}\n")
        return True

    def _create_turn_collection(self) -> bool:
        """Create ACMS_ConversationTurns collection."""
        if self.client.collection_exists(self.TURN_COLLECTION):
            sys.stderr.write(f"✅ Collection {self.TURN_COLLECTION} already exists\n")
            return False

        self.client._client.collections.create(
            name=self.TURN_COLLECTION,
            description="Individual conversation turn embeddings",
            vectorizer_config=None,  # Manual vectors from OpenAI
            vector_index_config=Configure.VectorIndex.hnsw(
                distance_metric=VectorDistances.COSINE
            ),
            properties=[
                Property(
                    name="content",
                    data_type=DataType.TEXT,
                    description="Turn content (message text)",
                ),
                Property(
                    name="turn_id",
                    data_type=DataType.TEXT,
                    description="PostgreSQL turn UUID",
                    skip_vectorization=True,
                ),
                Property(
                    name="thread_id",
                    data_type=DataType.TEXT,
                    description="Parent thread UUID",
                    skip_vectorization=True,
                ),
                Property(
                    name="user_id",
                    data_type=DataType.TEXT,
                    description="User UUID",
                    skip_vectorization=True,
                ),
                Property(
                    name="role",
                    data_type=DataType.TEXT,
                    description="Message role (user, assistant)",
                    skip_vectorization=True,
                ),
                Property(
                    name="turn_number",
                    data_type=DataType.INT,
                    description="Turn order number",
                    skip_vectorization=True,
                ),
                Property(
                    name="source",
                    data_type=DataType.TEXT,
                    description="Conversation source (chatgpt, claude, gemini)",
                    skip_vectorization=True,
                ),
                Property(
                    name="created_at",
                    data_type=DataType.DATE,
                    description="Turn creation timestamp",
                    skip_vectorization=True,
                ),
            ],
        )

        sys.stderr.write(f"✅ Created collection {self.TURN_COLLECTION}\n")
        return True

    def store_thread_vector(
        self,
        embedding: List[float],
        thread_id: str,
        user_id: str,
        source: str,
        title: str,
        turn_count: int,
        content: str,
        created_at: datetime,
        imported_at: Optional[datetime] = None
    ) -> str:
        """
        Store conversation thread embedding in Weaviate.

        Args:
            embedding: 768-dimensional vector
            thread_id: PostgreSQL thread UUID
            user_id: User UUID
            source: Conversation source (chatgpt, claude, gemini)
            title: Conversation title
            turn_count: Number of turns
            content: Full conversation text
            created_at: Original conversation creation time
            imported_at: Import timestamp (defaults to now)

        Returns:
            str: Weaviate object UUID
        """
        if len(embedding) != 768:
            raise ValueError(f"Embedding must be 768 dimensions, got {len(embedding)}")

        data = {
            "content": content,
            "thread_id": thread_id,
            "user_id": user_id,
            "source": source,
            "title": title,
            "turn_count": turn_count,
            "created_at": created_at,
            "imported_at": imported_at or datetime.utcnow(),
        }

        vector_id = self.client.insert_vector(
            collection=self.THREAD_COLLECTION,
            vector=embedding,
            data=data
        )

        return vector_id

    def store_turn_vector(
        self,
        embedding: List[float],
        turn_id: str,
        thread_id: str,
        user_id: str,
        role: str,
        turn_number: int,
        source: str,
        content: str,
        created_at: datetime
    ) -> str:
        """
        Store conversation turn embedding in Weaviate.

        Args:
            embedding: 768-dimensional vector
            turn_id: PostgreSQL turn UUID
            thread_id: Parent thread UUID
            user_id: User UUID
            role: Message role (user, assistant)
            turn_number: Turn order number
            source: Conversation source
            content: Turn content
            created_at: Turn creation timestamp

        Returns:
            str: Weaviate object UUID
        """
        if len(embedding) != 768:
            raise ValueError(f"Embedding must be 768 dimensions, got {len(embedding)}")

        data = {
            "content": content,
            "turn_id": turn_id,
            "thread_id": thread_id,
            "user_id": user_id,
            "role": role,
            "turn_number": turn_number,
            "source": source,
            "created_at": created_at,
        }

        vector_id = self.client.insert_vector(
            collection=self.TURN_COLLECTION,
            vector=embedding,
            data=data
        )

        return vector_id

    def search_threads(
        self,
        query_vector: List[float],
        limit: int = 10,
        source_filter: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search across conversation threads.

        Args:
            query_vector: 768-dimensional query vector
            limit: Max results to return
            source_filter: Filter by source (chatgpt, claude, gemini)
            user_id: Filter by user

        Returns:
            List of search results with thread data and relevance scores
        """
        # TODO: Add filters once Weaviate v4 filter API is implemented
        results = self.client.semantic_search(
            collection=self.THREAD_COLLECTION,
            query_vector=query_vector,
            limit=limit
        )

        return results

    def search_turns(
        self,
        query_vector: List[float],
        limit: int = 10,
        role_filter: Optional[str] = None,
        source_filter: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search across individual conversation turns.

        Args:
            query_vector: 768-dimensional query vector
            limit: Max results to return
            role_filter: Filter by role (user, assistant)
            source_filter: Filter by source
            user_id: Filter by user

        Returns:
            List of search results with turn data and relevance scores
        """
        # TODO: Add filters once Weaviate v4 filter API is implemented
        results = self.client.semantic_search(
            collection=self.TURN_COLLECTION,
            query_vector=query_vector,
            limit=limit
        )

        return results

    def count_thread_vectors(self) -> int:
        """Count total thread vectors stored."""
        return self.client.count_vectors(self.THREAD_COLLECTION)

    def count_turn_vectors(self) -> int:
        """Count total turn vectors stored."""
        return self.client.count_vectors(self.TURN_COLLECTION)

    def close(self):
        """Close Weaviate connection."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


if __name__ == "__main__":
    # Test conversation vector storage
    print("Testing Conversation Vector Storage...")

    with ConversationVectorStorage() as storage:
        # Setup collections
        storage.setup_collections()

        # Test thread vector storage
        import random
        test_vector = [random.random() for _ in range(768)]

        thread_id = storage.store_thread_vector(
            embedding=test_vector,
            thread_id="thread_test_001",
            user_id="user_001",
            source="chatgpt",
            title="Test Conversation",
            turn_count=5,
            content="Full conversation text here...",
            created_at=datetime.utcnow()
        )
        print(f"✅ Stored thread vector: {thread_id}")

        # Test turn vector storage
        turn_id = storage.store_turn_vector(
            embedding=test_vector,
            turn_id="turn_test_001",
            thread_id="thread_test_001",
            user_id="user_001",
            role="user",
            turn_number=1,
            source="chatgpt",
            content="User message content",
            created_at=datetime.utcnow()
        )
        print(f"✅ Stored turn vector: {turn_id}")

        # Test search
        query_vector = [random.random() for _ in range(768)]
        thread_results = storage.search_threads(query_vector, limit=5)
        print(f"✅ Thread search: {len(thread_results)} results")

        turn_results = storage.search_turns(query_vector, limit=5)
        print(f"✅ Turn search: {len(turn_results)} results")

        # Test counts
        thread_count = storage.count_thread_vectors()
        turn_count = storage.count_turn_vectors()
        print(f"✅ Total threads: {thread_count}, Total turns: {turn_count}")

        print("\n✅ All conversation vector storage tests passed!")
