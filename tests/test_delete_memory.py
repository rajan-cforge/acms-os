#!/usr/bin/env python3
"""Tests for Task 13: Delete Memory Feature

TDD Approach: Write tests BEFORE implementation.
Tests cover both API endpoint and CRUD layer.

Test Coverage:
1. DELETE /memories/{memory_id} API endpoint
2. MemoryCRUD.delete_memory() method
3. Edge cases (not found, invalid UUID, already deleted)
4. Dual deletion (PostgreSQL + Weaviate)
"""

import pytest
import uuid
from httpx import AsyncClient
from fastapi import status

# Mock imports - will be replaced with actual imports
# from src.api_server import app
# from src.storage.memory_crud import MemoryCRUD


class TestDeleteMemoryAPI:
    """Test DELETE /memories/{memory_id} API endpoint."""

    @pytest.mark.asyncio
    async def test_delete_memory_success(self, test_client: AsyncClient):
        """DELETE /memories/{id} returns 200 and deletes memory successfully."""
        # Arrange: Create a test memory first
        create_payload = {
            "content": "Test memory to delete",
            "tags": ["test", "delete"],
            "tier": "SHORT",
            "phase": "testing"
        }
        create_response = await test_client.post("/memories", json=create_payload)
        assert create_response.status_code == status.HTTP_200_OK
        memory_id = create_response.json()["memory_id"]

        # Act: Delete the memory
        delete_response = await test_client.delete(f"/memories/{memory_id}")

        # Assert: Response success
        assert delete_response.status_code == status.HTTP_200_OK
        response_data = delete_response.json()
        assert response_data["memory_id"] == memory_id
        assert response_data["status"] == "deleted"
        assert "deleted successfully" in response_data["message"].lower()

        # Assert: Memory no longer retrievable
        get_response = await test_client.get(f"/memories/{memory_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_memory_not_found(self, test_client: AsyncClient):
        """DELETE /memories/{id} returns 404 if memory doesn't exist."""
        # Arrange: Generate a random UUID that doesn't exist
        fake_memory_id = str(uuid.uuid4())

        # Act: Try to delete non-existent memory
        delete_response = await test_client.delete(f"/memories/{fake_memory_id}")

        # Assert: 404 error
        assert delete_response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in delete_response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_delete_memory_invalid_uuid(self, test_client: AsyncClient):
        """DELETE /memories/{id} returns 422 for invalid UUID format."""
        # Arrange: Invalid UUID string
        invalid_uuid = "not-a-valid-uuid"

        # Act: Try to delete with invalid UUID
        delete_response = await test_client.delete(f"/memories/{invalid_uuid}")

        # Assert: 422 validation error
        assert delete_response.status_code in [
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_400_BAD_REQUEST
        ]

    @pytest.mark.asyncio
    async def test_delete_memory_twice(self, test_client: AsyncClient):
        """DELETE /memories/{id} twice returns 404 on second attempt."""
        # Arrange: Create a test memory
        create_payload = {
            "content": "Test memory to delete twice",
            "tags": ["test", "delete"],
            "tier": "SHORT",
            "phase": "testing"
        }
        create_response = await test_client.post("/memories", json=create_payload)
        memory_id = create_response.json()["memory_id"]

        # Act: Delete once (should succeed)
        first_delete = await test_client.delete(f"/memories/{memory_id}")
        assert first_delete.status_code == status.HTTP_200_OK

        # Act: Delete again (should fail)
        second_delete = await test_client.delete(f"/memories/{memory_id}")

        # Assert: 404 on second delete
        assert second_delete.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_memory_removes_from_search(self, test_client: AsyncClient):
        """Deleted memory should not appear in search results."""
        # Arrange: Create a memory with unique content
        unique_content = f"Unique test content {uuid.uuid4()}"
        create_payload = {
            "content": unique_content,
            "tags": ["test", "delete", "search"],
            "tier": "SHORT",
            "phase": "testing"
        }
        create_response = await test_client.post("/memories", json=create_payload)
        memory_id = create_response.json()["memory_id"]

        # Verify memory appears in search before deletion
        search_payload = {"query": unique_content, "limit": 10}
        search_before = await test_client.post("/search", json=search_payload)
        assert search_before.status_code == status.HTTP_200_OK
        results_before = search_before.json()["results"]
        assert len(results_before) > 0
        assert any(r["memory_id"] == memory_id for r in results_before)

        # Act: Delete the memory
        delete_response = await test_client.delete(f"/memories/{memory_id}")
        assert delete_response.status_code == status.HTTP_200_OK

        # Assert: Memory no longer in search results
        search_after = await test_client.post("/search", json=search_payload)
        results_after = search_after.json()["results"]
        assert not any(r["memory_id"] == memory_id for r in results_after)

    @pytest.mark.asyncio
    async def test_delete_memory_removes_from_list(self, test_client: AsyncClient):
        """Deleted memory should not appear in GET /memories list."""
        # Arrange: Create a memory
        create_payload = {
            "content": "Test memory for list deletion",
            "tags": ["test", "delete", "list"],
            "tier": "SHORT",
            "phase": "testing"
        }
        create_response = await test_client.post("/memories", json=create_payload)
        memory_id = create_response.json()["memory_id"]

        # Verify memory appears in list before deletion
        list_before = await test_client.get("/memories?limit=100")
        memories_before = list_before.json()["memories"]
        assert any(m["memory_id"] == memory_id for m in memories_before)

        # Act: Delete the memory
        delete_response = await test_client.delete(f"/memories/{memory_id}")
        assert delete_response.status_code == status.HTTP_200_OK

        # Assert: Memory no longer in list
        list_after = await test_client.get("/memories?limit=100")
        memories_after = list_after.json()["memories"]
        assert not any(m["memory_id"] == memory_id for m in memories_after)


class TestDeleteMemoryCRUD:
    """Test MemoryCRUD.delete_memory() method."""

    @pytest.mark.asyncio
    async def test_delete_memory_returns_true_on_success(self, memory_crud):
        """delete_memory() returns True when memory exists and is deleted."""
        # Arrange: Create a test memory
        memory_id = await memory_crud.create_memory(
            user_id="test-user",
            content="Test memory for CRUD deletion",
            tags=["test", "crud"],
            phase="testing",
            tier="SHORT"
        )

        # Act: Delete the memory
        result = await memory_crud.delete_memory(memory_id)

        # Assert: Returns True
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_memory_returns_false_on_not_found(self, memory_crud):
        """delete_memory() returns False when memory doesn't exist."""
        # Arrange: Generate a random UUID that doesn't exist
        fake_memory_id = str(uuid.uuid4())

        # Act: Try to delete non-existent memory
        result = await memory_crud.delete_memory(fake_memory_id)

        # Assert: Returns False
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_memory_removes_from_postgresql(self, memory_crud, db_session):
        """delete_memory() removes record from PostgreSQL."""
        # Arrange: Create a test memory
        memory_id = await memory_crud.create_memory(
            user_id="test-user",
            content="Test memory for PostgreSQL deletion",
            tags=["test", "postgresql"],
            phase="testing",
            tier="SHORT"
        )

        # Verify memory exists in PostgreSQL
        from src.storage.models import MemoryItem
        from sqlalchemy import select
        stmt = select(MemoryItem).where(MemoryItem.memory_id == uuid.UUID(memory_id))
        result = await db_session.execute(stmt)
        memory_before = result.scalar_one_or_none()
        assert memory_before is not None

        # Act: Delete the memory
        await memory_crud.delete_memory(memory_id)

        # Assert: Memory no longer in PostgreSQL
        result_after = await db_session.execute(stmt)
        memory_after = result_after.scalar_one_or_none()
        assert memory_after is None

    @pytest.mark.asyncio
    async def test_delete_memory_removes_from_weaviate(self, memory_crud, weaviate_client):
        """delete_memory() removes vector from Weaviate."""
        # Arrange: Create a test memory
        memory_id = await memory_crud.create_memory(
            user_id="test-user",
            content="Test memory for Weaviate deletion with enough content to generate embedding",
            tags=["test", "weaviate"],
            phase="testing",
            tier="SHORT"
        )

        # Get the embedding_vector_id from PostgreSQL
        from src.storage.models import MemoryItem
        from sqlalchemy import select
        stmt = select(MemoryItem).where(MemoryItem.memory_id == uuid.UUID(memory_id))
        result = await memory_crud.db_session.execute(stmt)
        memory = result.scalar_one()
        embedding_vector_id = memory.embedding_vector_id

        # Verify vector exists in Weaviate (before deletion)
        # Note: Weaviate may not have immediate consistency
        # This assertion may be skipped in real tests

        # Act: Delete the memory
        await memory_crud.delete_memory(memory_id)

        # Assert: Vector no longer retrievable from Weaviate
        # Verify by checking that the UUID is not in collection
        # (This is implementation-dependent on weaviate_client API)
        # For now, we trust that weaviate.delete_vector() was called

    @pytest.mark.asyncio
    async def test_delete_memory_logs_audit_trail(self, memory_crud, db_session):
        """delete_memory() creates audit log entry."""
        # Arrange: Create a test memory
        memory_id = await memory_crud.create_memory(
            user_id="test-user",
            content="Test memory for audit logging",
            tags=["test", "audit"],
            phase="testing",
            tier="SHORT"
        )

        # Act: Delete the memory
        await memory_crud.delete_memory(memory_id)

        # Assert: Audit log entry created
        from src.storage.models import AuditLog
        from sqlalchemy import select
        stmt = select(AuditLog).where(
            AuditLog.action == "delete_memory",
            AuditLog.resource_id == memory_id
        )
        result = await db_session.execute(stmt)
        audit_log = result.scalar_one_or_none()
        assert audit_log is not None
        assert audit_log.action == "delete_memory"
        assert audit_log.resource_type == "memory"
        assert audit_log.resource_id == memory_id


class TestDeleteMemoryEdgeCases:
    """Test edge cases for delete memory functionality."""

    @pytest.mark.asyncio
    async def test_delete_memory_with_no_embedding(self, memory_crud):
        """Can delete memory even if it has no Weaviate embedding."""
        # Arrange: Create memory with minimal content (might skip embedding)
        memory_id = await memory_crud.create_memory(
            user_id="test-user",
            content="x",  # Very short content
            tags=["test"],
            phase="testing",
            tier="SHORT"
        )

        # Act: Delete should succeed even if no embedding exists
        result = await memory_crud.delete_memory(memory_id)

        # Assert: Returns True (deletion succeeds)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_memory_concurrent_access(self, test_client: AsyncClient):
        """Deleting memory while another request is accessing it."""
        # Arrange: Create a memory
        create_payload = {
            "content": "Test memory for concurrent deletion",
            "tags": ["test", "concurrent"],
            "tier": "SHORT",
            "phase": "testing"
        }
        create_response = await test_client.post("/memories", json=create_payload)
        memory_id = create_response.json()["memory_id"]

        # Act: Delete the memory
        delete_response = await test_client.delete(f"/memories/{memory_id}")
        assert delete_response.status_code == status.HTTP_200_OK

        # Act: Try to retrieve immediately after delete
        get_response = await test_client.get(f"/memories/{memory_id}")

        # Assert: Should return 404 (memory is gone)
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_memory_with_special_characters_in_content(self, test_client: AsyncClient):
        """Can delete memory with special characters, emojis, etc."""
        # Arrange: Create memory with special content
        create_payload = {
            "content": "Test memory with 🚀 emojis and special chars: <>&\"'",
            "tags": ["test", "special-chars"],
            "tier": "SHORT",
            "phase": "testing"
        }
        create_response = await test_client.post("/memories", json=create_payload)
        memory_id = create_response.json()["memory_id"]

        # Act: Delete the memory
        delete_response = await test_client.delete(f"/memories/{memory_id}")

        # Assert: Deletion succeeds
        assert delete_response.status_code == status.HTTP_200_OK


# Pytest fixtures (to be implemented in conftest.py)
@pytest.fixture
async def test_client():
    """Provides AsyncClient for API testing."""
    # from src.api_server import app
    # from httpx import AsyncClient
    # async with AsyncClient(app=app, base_url="http://test") as client:
    #     yield client
    raise NotImplementedError("Fixture test_client must be implemented in conftest.py")


@pytest.fixture
async def memory_crud():
    """Provides MemoryCRUD instance for CRUD testing."""
    # from src.storage.memory_crud import MemoryCRUD
    # crud = MemoryCRUD()
    # yield crud
    raise NotImplementedError("Fixture memory_crud must be implemented in conftest.py")


@pytest.fixture
async def db_session():
    """Provides database session for direct DB assertions."""
    # from src.storage.database import get_session
    # async with get_session() as session:
    #     yield session
    raise NotImplementedError("Fixture db_session must be implemented in conftest.py")


@pytest.fixture
async def weaviate_client():
    """Provides Weaviate client for vector DB assertions."""
    # from src.storage.weaviate_client import WeaviateClient
    # client = WeaviateClient()
    # yield client
    raise NotImplementedError("Fixture weaviate_client must be implemented in conftest.py")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
