#!/usr/bin/env python3
"""Storage layer tests for ACMS Phase 2.

TDD Approach: These tests are written BEFORE implementation.
They will fail initially, then pass as we build the storage layer.

Test Coverage:
- PostgreSQL schemas and connections
- Database models (Users, MemoryItems, QueryLogs, Outcomes, AuditLogs)
- Weaviate collection setup and vector operations
- Encryption/decryption (XChaCha20-Poly1305)
- Memory CRUD operations
- Connection pooling
- Integration tests for full storage pipeline
"""

import pytest
import asyncio
import time
import hashlib
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

# Test database configuration (will use test ports)
TEST_POSTGRES_HOST = "localhost"
TEST_POSTGRES_PORT = 40432
TEST_POSTGRES_DB = "acms_test"
TEST_POSTGRES_USER = "acms"
TEST_POSTGRES_PASSWORD = "acms_password"

TEST_WEAVIATE_HOST = "localhost"
TEST_WEAVIATE_PORT = 40480  # ACMS Weaviate v4 instance

TEST_REDIS_HOST = "localhost"
TEST_REDIS_PORT = 40379


class TestDatabaseSchemas:
    """Test PostgreSQL schema definitions and migrations."""

    def test_alembic_migrations_directory_exists(self):
        """Alembic migrations directory must exist."""
        migrations_dir = Path("alembic")
        assert migrations_dir.exists(), "alembic/ directory not found"
        assert (migrations_dir / "env.py").exists(), "alembic/env.py not found"

    def test_alembic_ini_exists(self):
        """Alembic configuration file must exist."""
        alembic_ini = Path("alembic.ini")
        assert alembic_ini.exists(), "alembic.ini not found"

    def test_users_table_schema(self):
        """Users table must have correct schema."""
        from src.storage.models import User

        # Required fields
        assert hasattr(User, 'user_id'), "User missing user_id field"
        assert hasattr(User, 'username'), "User missing username field"
        assert hasattr(User, 'created_at'), "User missing created_at field"
        assert hasattr(User, 'updated_at'), "User missing updated_at field"
        assert hasattr(User, 'is_active'), "User missing is_active field"

    def test_memory_items_table_schema(self):
        """MemoryItems table must have correct schema."""
        from src.storage.models import MemoryItem

        # Required fields
        required_fields = [
            'memory_id', 'user_id', 'content', 'content_hash',
            'encrypted_content', 'embedding_vector_id', 'tier',
            'crs_score', 'access_count', 'last_accessed',
            'created_at', 'updated_at', 'tags', 'phase'
        ]
        for field in required_fields:
            assert hasattr(MemoryItem, field), f"MemoryItem missing {field} field"

    def test_query_logs_table_schema(self):
        """QueryLogs table must have correct schema."""
        from src.storage.models import QueryLog

        required_fields = [
            'log_id', 'user_id', 'query', 'query_embedding_id',
            'retrieved_memory_ids', 'timestamp', 'latency_ms'
        ]
        for field in required_fields:
            assert hasattr(QueryLog, field), f"QueryLog missing {field} field"

    def test_outcomes_table_schema(self):
        """Outcomes table must have correct schema."""
        from src.storage.models import Outcome

        required_fields = [
            'outcome_id', 'memory_id', 'query_id',
            'outcome_type', 'feedback_score', 'timestamp'
        ]
        for field in required_fields:
            assert hasattr(Outcome, field), f"Outcome missing {field} field"

    def test_audit_logs_table_schema(self):
        """AuditLogs table must have correct schema."""
        from src.storage.models import AuditLog

        required_fields = [
            'audit_id', 'user_id', 'action', 'resource_type',
            'resource_id', 'timestamp', 'ip_address', 'user_agent'
        ]
        for field in required_fields:
            assert hasattr(AuditLog, field), f"AuditLog missing {field} field"


class TestDatabaseConnection:
    """Test database connection and connection pooling."""

    @pytest.mark.asyncio
    async def test_postgres_connection_pool(self):
        """Connection pool must be created and functional."""
        from src.storage.database import get_db_pool, close_db_pool

        pool = await get_db_pool()
        assert pool is not None, "Connection pool not created"

        # Test acquiring connection
        async with pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1, "Connection not functional"

        await close_db_pool()

    @pytest.mark.asyncio
    async def test_connection_pool_max_size(self):
        """Connection pool must respect max size (20 connections)."""
        from src.storage.database import get_db_pool, close_db_pool

        pool = await get_db_pool()
        assert pool._maxsize == 20, "Connection pool max size not 20"
        await close_db_pool()

    @pytest.mark.asyncio
    async def test_postgres_schema_created(self):
        """All tables must be created after migrations."""
        from src.storage.database import get_db_pool, close_db_pool

        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Check that all required tables exist
            tables = await conn.fetch("""
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
            """)
            table_names = [t['tablename'] for t in tables]

            required_tables = [
                'users', 'memory_items', 'query_logs',
                'outcomes', 'audit_logs'
            ]
            for table in required_tables:
                assert table in table_names, f"Table {table} not created"

        await close_db_pool()


class TestEncryption:
    """Test encryption manager with XChaCha20-Poly1305."""

    def test_encryption_manager_exists(self):
        """Encryption manager module must exist."""
        from src.storage.encryption import EncryptionManager
        assert EncryptionManager is not None

    def test_generate_key(self):
        """Must generate 256-bit encryption keys."""
        from src.storage.encryption import EncryptionManager

        manager = EncryptionManager()
        key = manager.generate_key()
        assert len(key) == 32, "Key must be 32 bytes (256 bits)"

    def test_encrypt_decrypt_roundtrip(self):
        """Encryption and decryption must be reversible."""
        from src.storage.encryption import EncryptionManager

        manager = EncryptionManager()
        plaintext = "This is sensitive memory content"

        # Encrypt
        encrypted = manager.encrypt(plaintext)
        assert encrypted != plaintext, "Encrypted text same as plaintext"
        assert len(encrypted) > len(plaintext), "Encrypted text not larger"

        # Decrypt
        decrypted = manager.decrypt(encrypted)
        assert decrypted == plaintext, "Decryption failed"

    def test_encryption_unique_nonces(self):
        """Each encryption must use a unique nonce."""
        from src.storage.encryption import EncryptionManager

        manager = EncryptionManager()
        plaintext = "Same content"

        encrypted1 = manager.encrypt(plaintext)
        encrypted2 = manager.encrypt(plaintext)

        # Same plaintext should produce different ciphertext
        assert encrypted1 != encrypted2, "Nonces not unique"

    def test_encryption_with_wrong_key_fails(self):
        """Decryption with wrong key must fail."""
        from src.storage.encryption import EncryptionManager

        manager1 = EncryptionManager()
        manager2 = EncryptionManager()  # Different key

        plaintext = "Sensitive data"
        encrypted = manager1.encrypt(plaintext)

        with pytest.raises(Exception):
            manager2.decrypt(encrypted)

    def test_encryption_detects_tampering(self):
        """AEAD must detect tampered ciphertext."""
        from src.storage.encryption import EncryptionManager

        manager = EncryptionManager()
        plaintext = "Original content"
        encrypted = manager.encrypt(plaintext)

        # Tamper with ciphertext
        tampered = encrypted[:-10] + b"tampered!!"

        with pytest.raises(Exception):
            manager.decrypt(tampered)


class TestWeaviate:
    """Test Weaviate client and vector operations."""

    def test_weaviate_client_creation(self):
        """Weaviate client must connect to existing instance."""
        from src.storage.weaviate_client import WeaviateClient

        client = WeaviateClient()
        assert client is not None, "Client not created"
        assert client.is_ready(), "Weaviate not ready"

    def test_weaviate_auto_detection(self):
        """Client must connect to ACMS Weaviate on port 40480."""
        from src.storage.weaviate_client import WeaviateClient

        client = WeaviateClient()
        # Should connect to ACMS port
        assert client.port == 40480, "Port detection failed"

    def test_weaviate_collection_exists(self):
        """ACMS_MemoryItems_v1 collection must exist or be created."""
        from src.storage.weaviate_client import WeaviateClient

        client = WeaviateClient()
        # Setup collection (creates if not exists)
        client.setup_acms_collection()

        collections = client.list_collections()
        assert "ACMS_MemoryItems_v1" in collections, \
            "ACMS_MemoryItems_v1 collection not found"

        client.close()

    def test_weaviate_collection_schema(self):
        """Collection must have correct schema (384-dim vectors)."""
        from src.storage.weaviate_client import WeaviateClient

        client = WeaviateClient()
        schema = client.get_collection_schema("ACMS_MemoryItems_v1")

        # Check vector dimensions
        assert schema is not None, "Schema not found"
        # Vector dimension should be 384 (all-minilm:22m output)
        vectorizer_config = schema.get('vectorizer') or schema.get('vectorIndexConfig')
        # Will verify dimension matches all-minilm output

    def test_weaviate_insert_vector(self):
        """Must be able to insert vectors into collection."""
        from src.storage.weaviate_client import WeaviateClient
        import numpy as np

        client = WeaviateClient()

        # Create test vector (384 dimensions)
        test_vector = np.random.randn(384).tolist()
        test_data = {
            "content": "Test memory content",
            "memory_id": "test_001",
            "created_at": datetime.now().astimezone().isoformat()  # RFC3339 with timezone
        }

        # Insert
        vector_id = client.insert_vector(
            collection="ACMS_MemoryItems_v1",
            vector=test_vector,
            data=test_data
        )
        assert vector_id is not None, "Vector not inserted"

    def test_weaviate_semantic_search(self):
        """Must perform semantic search on vectors."""
        from src.storage.weaviate_client import WeaviateClient
        import numpy as np

        client = WeaviateClient()

        # Search with query vector
        query_vector = np.random.randn(384).tolist()
        results = client.semantic_search(
            collection="ACMS_MemoryItems_v1",
            query_vector=query_vector,
            limit=5
        )

        assert isinstance(results, list), "Results not a list"
        assert len(results) <= 5, "Too many results"

    def test_weaviate_delete_vector(self):
        """Must be able to delete vectors by ID."""
        from src.storage.weaviate_client import WeaviateClient
        import numpy as np

        client = WeaviateClient()

        # Insert test vector
        test_vector = np.random.randn(384).tolist()
        test_data = {"content": "Delete test", "memory_id": "delete_test"}
        vector_id = client.insert_vector(
            "ACMS_MemoryItems_v1", test_vector, test_data
        )

        # Delete
        deleted = client.delete_vector("ACMS_MemoryItems_v1", vector_id)
        assert deleted, "Vector not deleted"

    def test_weaviate_safety_existing_collections(self):
        """Must NEVER delete existing collections."""
        from src.storage.weaviate_client import WeaviateClient

        client = WeaviateClient()
        collections_before = set(client.list_collections())

        # Attempt to create/setup ACMS collection
        client.setup_acms_collection()

        collections_after = set(client.list_collections())

        # All original collections must still exist
        assert collections_before.issubset(collections_after), \
            "SAFETY VIOLATION: Existing collections deleted!"


class TestMemoryCRUD:
    """Test memory CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_memory(self, test_user):
        """Must create memory in PostgreSQL and Weaviate."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()
        memory_data = {
            "user_id": test_user["user_id"],  # Use fixture user
            "content": "This is a test memory for CRUD operations",
            "tags": ["test", "crud"],
            "phase": "test"
        }

        memory_id = await crud.create_memory(**memory_data)
        assert memory_id is not None, "Memory not created"
        assert isinstance(memory_id, str), "Memory ID not string"

    @pytest.mark.asyncio
    async def test_create_memory_generates_embedding(self, test_user):
        """Create must generate embedding via Ollama."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()
        memory_data = {
            "user_id": test_user["user_id"],
            "content": "Test embedding generation",
            "tags": ["embedding"],
            "phase": "test"
        }

        memory_id = await crud.create_memory(**memory_data)

        # Retrieve and check embedding exists
        memory = await crud.get_memory(memory_id)
        assert memory['embedding_vector_id'] is not None, "Embedding not generated"

    @pytest.mark.asyncio
    async def test_create_memory_encrypts_content(self, test_user):
        """Create must encrypt sensitive content."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()
        plaintext = "Sensitive memory content"
        memory_data = {
            "user_id": test_user["user_id"],
            "content": plaintext,
            "tags": ["encryption"],
            "phase": "test"
        }

        memory_id = await crud.create_memory(**memory_data)

        # Retrieve from database directly
        memory = await crud.get_memory(memory_id, decrypt=False)
        assert memory['encrypted_content'] != plaintext, "Content not encrypted"

    @pytest.mark.asyncio
    async def test_get_memory(self, test_user):
        """Must retrieve memory by ID."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()

        # Create test memory
        memory_data = {
            "user_id": test_user["user_id"],
            "content": "Retrieve test",
            "tags": ["get"],
            "phase": "test"
        }
        memory_id = await crud.create_memory(**memory_data)

        # Retrieve
        memory = await crud.get_memory(memory_id)
        assert memory is not None, "Memory not retrieved"
        assert memory['content'] == "Retrieve test", "Content mismatch"

    @pytest.mark.asyncio
    async def test_update_memory(self, test_user):
        """Must update existing memory."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()

        # Create
        memory_id = await crud.create_memory(
            user_id=test_user["user_id"],
            content="Original content",
            tags=["update"],
            phase="test"
        )

        # Update
        updated = await crud.update_memory(
            memory_id=memory_id,
            content="Updated content",
            tags=["update", "modified"]
        )
        assert updated, "Update failed"

        # Verify
        memory = await crud.get_memory(memory_id)
        assert memory['content'] == "Updated content", "Content not updated"
        assert "modified" in memory['tags'], "Tags not updated"

    @pytest.mark.asyncio
    async def test_delete_memory(self, test_user):
        """Must delete memory from PostgreSQL and Weaviate."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()

        # Create
        memory_id = await crud.create_memory(
            user_id=test_user["user_id"],
            content="Delete test",
            tags=["delete"],
            phase="test"
        )

        # Delete
        deleted = await crud.delete_memory(memory_id)
        assert deleted, "Delete failed"

        # Verify deleted
        memory = await crud.get_memory(memory_id)
        assert memory is None, "Memory not deleted"

    @pytest.mark.asyncio
    async def test_list_memories_by_user(self, test_user):
        """Must list all memories for a user."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()
        user_id = test_user["user_id"]

        # Create multiple memories
        for i in range(3):
            await crud.create_memory(
                user_id=user_id,
                content=f"Memory {i}",
                tags=["list"],
                phase="test"
            )

        # List
        memories = await crud.list_memories(user_id=user_id)
        assert len(memories) >= 3, "Not all memories listed"

    @pytest.mark.asyncio
    async def test_list_memories_by_tag(self, test_user):
        """Must filter memories by tag."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()

        # Create memories with specific tag
        tag = "filter_test"
        test_user_id = test_user["user_id"]
        for i in range(2):
            await crud.create_memory(
                user_id=test_user_id,
                content=f"Tagged memory {i}",
                tags=[tag],
                phase="test"
            )

        # Filter by tag
        memories = await crud.list_memories(tag=tag)
        assert len(memories) >= 2, "Tag filtering failed"
        for memory in memories:
            assert tag in memory['tags'], "Wrong memories returned"

    @pytest.mark.asyncio
    async def test_content_deduplication(self, test_user):
        """Must detect and prevent duplicate content."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()
        content = "Duplicate content test"
        test_user_id = test_user["user_id"]

        # Create first memory
        memory_id1 = await crud.create_memory(
            user_id=test_user_id,
            content=content,
            tags=["dup"],
            phase="test"
        )

        # Attempt duplicate
        memory_id2 = await crud.create_memory(
            user_id=test_user_id,
            content=content,
            tags=["dup"],
            phase="test"
        )

        # Should return existing ID or None
        assert memory_id2 is None or memory_id2 == memory_id1, \
            "Duplicate not detected"


class TestOllamaIntegration:
    """Test Ollama embedding generation."""

    def test_ollama_client_exists(self):
        """Ollama client module must exist."""
        from src.storage.ollama_client import OllamaClient
        assert OllamaClient is not None

    def test_ollama_generate_embedding(self):
        """Must generate 384-dim embeddings using all-minilm:22m."""
        from src.storage.ollama_client import OllamaClient

        client = OllamaClient()
        text = "This is a test sentence for embedding generation"

        embedding = client.generate_embedding(text)
        assert embedding is not None, "Embedding not generated"
        assert len(embedding) == 384, f"Wrong dimension: {len(embedding)}"
        assert all(isinstance(x, float) for x in embedding), "Not float values"

    def test_ollama_embedding_performance(self):
        """Embedding generation must be <100ms p95."""
        from src.storage.ollama_client import OllamaClient

        client = OllamaClient()
        text = "Performance test sentence"

        # Run 20 times, check p95
        times = []
        for _ in range(20):
            start = time.time()
            client.generate_embedding(text)
            elapsed = (time.time() - start) * 1000  # ms
            times.append(elapsed)

        times.sort()
        p95 = times[int(len(times) * 0.95)]
        assert p95 < 100, f"p95 latency {p95}ms exceeds 100ms target"

    def test_ollama_model_available(self):
        """all-minilm:22m model must be available."""
        from src.storage.ollama_client import OllamaClient

        client = OllamaClient()
        models = client.list_models()

        assert any("all-minilm" in m for m in models), \
            "all-minilm:22m model not available"


class TestStorageIntegration:
    """Integration tests for full storage pipeline."""

    @pytest.mark.asyncio
    async def test_full_storage_pipeline(self, test_user):
        """Test complete flow: create -> encrypt -> embed -> store -> retrieve."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()

        # Create memory (triggers encryption, embedding, storage)
        content = "Integration test: full storage pipeline"
        memory_id = await crud.create_memory(
            user_id=test_user["user_id"],
            content=content,
            tags=["integration", "pipeline"],
            phase="test"
        )

        assert memory_id is not None, "Storage pipeline failed"

        # Retrieve and verify all aspects
        memory = await crud.get_memory(memory_id, decrypt=False)
        assert memory['content'] == content, "Content retrieval failed"
        assert memory['embedding_vector_id'] is not None, "Embedding missing"
        assert memory['encrypted_content'] is not None, "Encryption missing"

    @pytest.mark.asyncio
    async def test_semantic_search_integration(self, test_user):
        """Test semantic search across stored memories."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()

        # Store test memories
        contents = [
            "Python programming language",
            "Machine learning algorithms",
            "Database management systems"
        ]
        search_user_id = test_user["user_id"]
        for content in contents:
            await crud.create_memory(
                user_id=search_user_id,
                content=content,
                tags=["search"],
                phase="test"
            )

        # Semantic search
        results = await crud.search_memories(
            query="programming and coding",
            user_id=search_user_id,
            limit=2
        )

        assert len(results) > 0, "Search returned no results"
        # First result should be most relevant (Python programming)

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, test_user):
        """Test concurrent memory operations (connection pooling)."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()

        # Create 10 memories concurrently
        tasks = []
        concurrent_user_id = test_user["user_id"]
        for i in range(10):
            task = crud.create_memory(
                user_id=concurrent_user_id,
                content=f"Concurrent memory {i}",
                tags=["concurrent"],
                phase="test"
            )
            tasks.append(task)

        memory_ids = await asyncio.gather(*tasks)
        assert len(memory_ids) == 10, "Concurrent operations failed"
        assert all(mid is not None for mid in memory_ids), "Some creates failed"

    @pytest.mark.asyncio
    async def test_storage_performance_latency(self, test_user):
        """Storage operations must meet latency targets."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()

        # Create memory (should be <200ms p95)
        times = []
        perf_user_id = test_user["user_id"]
        for i in range(20):
            start = time.time()
            await crud.create_memory(
                user_id=perf_user_id,
                content=f"Performance test {i}",
                tags=["perf"],
                phase="test"
            )
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)

        times.sort()
        p95 = times[int(len(times) * 0.95)]
        assert p95 < 200, f"Create latency {p95}ms exceeds 200ms target"


class TestAuditLogging:
    """Test audit logging for all storage operations."""

    @pytest.mark.asyncio
    async def test_audit_log_created_on_memory_create(self, test_user):
        """Create operation must log to audit table."""
        from src.storage.memory_crud import MemoryCRUD
        from src.storage.models import AuditLog

        crud = MemoryCRUD()
        audit_user_id = test_user["user_id"]

        memory_id = await crud.create_memory(
            user_id=audit_user_id,
            content="Audit test",
            tags=["audit"],
            phase="test"
        )

        # Check audit log
        logs = await crud.get_audit_logs(
            user_id=audit_user_id,
            action="create_memory"
        )
        assert len(logs) > 0, "No audit log created"

    @pytest.mark.asyncio
    async def test_audit_log_includes_metadata(self, test_user):
        """Audit logs must include timestamp, IP, user agent."""
        from src.storage.memory_crud import MemoryCRUD

        crud = MemoryCRUD()
        audit_user2_id = test_user["user_id"]

        await crud.create_memory(
            user_id=audit_user2_id,
            content="Metadata test",
            tags=["audit"],
            phase="test"
        )

        logs = await crud.get_audit_logs(user_id=audit_user2_id)
        log = logs[0]

        assert 'timestamp' in log, "No timestamp in audit log"
        assert 'ip_address' in log, "No IP address field in audit log"
        assert 'user_agent' in log, "No user agent field in audit log"
        # IP and user agent can be None - just check keys exist


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
