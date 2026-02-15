"""Tests for ACMS MCP Server."""
import pytest
import sys
from pathlib import Path
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mcp.server import (
    acms_store_memory,
    acms_search_memories,
    acms_get_memory,
    acms_update_memory,
    acms_delete_memory,
    acms_list_memories,
    acms_search_by_tag,
    acms_get_conversation_context,
    acms_store_conversation_turn,
    acms_get_memory_stats,
    acms_tier_transition,
    acms_semantic_search,
)
from src.storage.memory_crud import MemoryCRUD


class TestMCPTools:
    """Test MCP tool functionality."""

    @pytest.mark.asyncio
    async def test_acms_store_memory_success(self):
        """Test storing memory via MCP tool - success case."""
        unique_id = str(uuid.uuid4())[:8]
        content = f"Test memory content for MCP {unique_id}"

        result = await acms_store_memory(
            content=content,
            tags=["test", "mcp"],
            tier="SHORT"
        )

        assert result["success"] is True
        assert "memory_id" in result["data"]
        assert result["data"]["content"] == content
        assert result["data"]["tags"] == ["test", "mcp"]
        assert result["data"]["tier"] == "SHORT"

    @pytest.mark.asyncio
    async def test_acms_store_memory_validation_error(self):
        """Test storing memory with invalid tier - should return error."""
        result = await acms_store_memory(
            content="Test content",
            tier="INVALID_TIER"
        )

        assert result["success"] is False
        assert "invalid" in result["error"].lower()
        assert "details" in result
        assert "validation_error" in result["details"]

    @pytest.mark.asyncio
    async def test_acms_store_memory_empty_content(self):
        """Test storing memory with empty content - should return error."""
        result = await acms_store_memory(
            content=""
        )

        assert result["success"] is False
        assert "details" in result or "error" in result

    @pytest.mark.asyncio
    async def test_acms_search_memories_success(self):
        """Test searching memories via MCP tool - success case."""
        # First store a memory with unique content
        unique_id = str(uuid.uuid4())[:8]
        content = f"Python programming best practices {unique_id}"

        store_result = await acms_store_memory(
            content=content,
            tags=["programming", "python"]
        )
        assert store_result["success"] is True

        # Then search for it
        search_result = await acms_search_memories(
            query="Python programming",
            limit=5
        )

        assert search_result["success"] is True
        assert isinstance(search_result["data"], list)
        assert len(search_result["data"]) > 0

        # Verify first result has expected fields
        first_result = search_result["data"][0]
        assert "memory_id" in first_result
        assert "content" in first_result
        assert "similarity_score" in first_result

    @pytest.mark.asyncio
    async def test_acms_search_memories_no_results(self):
        """Test searching with query that has no matches."""
        result = await acms_search_memories(
            query="xyzabc123uniquequery456",
            limit=10
        )

        assert result["success"] is True
        assert isinstance(result["data"], list)
        # May return empty list or low-relevance results

    @pytest.mark.asyncio
    async def test_acms_search_memories_limit(self):
        """Test search respects limit parameter."""
        result = await acms_search_memories(
            query="test",
            limit=3
        )

        assert result["success"] is True
        assert len(result["data"]) <= 3

    # ========================================================================
    # Tool 3: acms_get_memory
    # ========================================================================

    @pytest.mark.asyncio
    async def test_acms_get_memory_success(self):
        """Test retrieving memory by ID - success case."""
        # First store a memory
        unique_id = str(uuid.uuid4())[:8]
        content = f"Test get memory content {unique_id}"

        store_result = await acms_store_memory(
            content=content,
            tags=["test", "get"]
        )
        assert store_result["success"] is True
        memory_id = store_result["data"]["memory_id"]

        # Get it
        result = await acms_get_memory(memory_id=memory_id)

        assert result["success"] is True
        assert result["data"]["memory_id"] == memory_id
        assert result["data"]["content"] == content
        assert "test" in result["data"]["tags"]
        assert "access_count" in result["data"]
        assert "created_at" in result["data"]

    @pytest.mark.asyncio
    async def test_acms_get_memory_not_found(self):
        """Test retrieving non-existent memory."""
        result = await acms_get_memory(
            memory_id="00000000-0000-0000-0000-000000000000"
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    # ========================================================================
    # Tool 4: acms_update_memory
    # ========================================================================

    @pytest.mark.asyncio
    async def test_acms_update_memory_success(self):
        """Test updating memory content and tags."""
        # Store original memory
        unique_id = str(uuid.uuid4())[:8]
        original_content = f"Original content {unique_id}"

        store_result = await acms_store_memory(
            content=original_content,
            tags=["original"]
        )
        memory_id = store_result["data"]["memory_id"]

        # Update it
        updated_content = f"Updated content {unique_id}"
        result = await acms_update_memory(
            memory_id=memory_id,
            content=updated_content,
            tags=["updated", "modified"]
        )

        assert result["success"] is True
        assert result["data"]["memory_id"] == memory_id
        assert result["data"]["content"] == updated_content
        assert result["data"]["tags"] == ["updated", "modified"]

    @pytest.mark.asyncio
    async def test_acms_update_memory_not_found(self):
        """Test updating non-existent memory."""
        result = await acms_update_memory(
            memory_id="00000000-0000-0000-0000-000000000000",
            content="Updated content"
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    # ========================================================================
    # Tool 5: acms_delete_memory
    # ========================================================================

    @pytest.mark.asyncio
    async def test_acms_delete_memory_success(self):
        """Test deleting a memory."""
        # Store a memory
        unique_id = str(uuid.uuid4())[:8]
        content = f"Memory to delete {unique_id}"

        store_result = await acms_store_memory(content=content)
        memory_id = store_result["data"]["memory_id"]

        # Delete it
        result = await acms_delete_memory(memory_id=memory_id)

        assert result["success"] is True
        assert result["data"]["deleted"] is True
        assert result["data"]["memory_id"] == memory_id

        # Verify it's gone
        get_result = await acms_get_memory(memory_id=memory_id)
        assert get_result["success"] is False

    @pytest.mark.asyncio
    async def test_acms_delete_memory_not_found(self):
        """Test deleting non-existent memory."""
        result = await acms_delete_memory(
            memory_id="00000000-0000-0000-0000-000000000000"
        )

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    # ========================================================================
    # Tool 6: acms_list_memories
    # ========================================================================

    @pytest.mark.asyncio
    async def test_acms_list_memories_success(self):
        """Test listing memories with filters."""
        # Store a memory with specific tag
        unique_id = str(uuid.uuid4())[:8]
        content = f"List test memory {unique_id}"

        await acms_store_memory(
            content=content,
            tags=["list_test", unique_id],
            tier="MID"
        )

        # List with tag filter
        result = await acms_list_memories(tag="list_test", limit=10)

        assert result["success"] is True
        assert isinstance(result["data"], list)
        assert len(result["data"]) > 0

        # Verify first result has expected structure
        first = result["data"][0]
        assert "memory_id" in first
        assert "content" in first
        assert "tags" in first
        assert "created_at" in first

    @pytest.mark.asyncio
    async def test_acms_list_memories_tier_filter(self):
        """Test listing memories with tier filter."""
        result = await acms_list_memories(tier="SHORT", limit=5)

        assert result["success"] is True
        assert isinstance(result["data"], list)
        # All results should be SHORT tier
        for mem in result["data"]:
            assert mem.get("tier") == "SHORT"

    # ========================================================================
    # Tool 7: acms_search_by_tag
    # ========================================================================

    @pytest.mark.asyncio
    async def test_acms_search_by_tag_success(self):
        """Test searching memories by tag."""
        # Store memory with unique tag
        unique_tag = f"tag_{uuid.uuid4().hex[:8]}"
        unique_id = str(uuid.uuid4())[:8]

        await acms_store_memory(
            content=f"Tag search test {unique_id}",
            tags=[unique_tag, "search_test"]
        )

        # Search by tag
        result = await acms_search_by_tag(tag=unique_tag, limit=10)

        assert result["success"] is True
        assert isinstance(result["data"], list)
        assert len(result["data"]) > 0

        # Verify the tag is in results
        found = False
        for mem in result["data"]:
            if unique_tag in mem.get("tags", []):
                found = True
                break
        assert found, f"Tag {unique_tag} not found in results"

    # ========================================================================
    # Tool 8: acms_get_conversation_context
    # ========================================================================

    @pytest.mark.asyncio
    async def test_acms_get_conversation_context_success(self):
        """Test retrieving conversation context."""
        # Store a conversation-related memory
        unique_id = str(uuid.uuid4())[:8]
        content = f"User asked about Python decorators {unique_id}"

        await acms_store_memory(
            content=content,
            tags=["conversation", "python"]
        )

        # Get context
        result = await acms_get_conversation_context(
            query="Python decorators discussion",
            limit=5
        )

        assert result["success"] is True
        assert "data" in result
        assert "query" in result["data"]
        assert "context_memories" in result["data"]
        assert isinstance(result["data"]["context_memories"], list)
        assert "total_retrieved" in result["data"]

    # ========================================================================
    # Tool 9: acms_store_conversation_turn
    # ========================================================================

    @pytest.mark.asyncio
    async def test_acms_store_conversation_turn_user(self):
        """Test storing a user conversation turn."""
        unique_id = str(uuid.uuid4())[:8]
        content = f"How do I use async/await in Python? {unique_id}"

        result = await acms_store_conversation_turn(
            role="user",
            content=content,
            context="Python programming question"
        )

        assert result["success"] is True
        assert result["data"]["role"] == "user"
        assert result["data"]["content"] == content
        assert "conversation" in result["data"]["tags"]
        assert "user_turn" in result["data"]["tags"]
        assert result["data"]["tier"] == "SHORT"

    @pytest.mark.asyncio
    async def test_acms_store_conversation_turn_assistant(self):
        """Test storing an assistant conversation turn."""
        unique_id = str(uuid.uuid4())[:8]
        content = f"Async/await allows non-blocking code execution {unique_id}"

        result = await acms_store_conversation_turn(
            role="assistant",
            content=content
        )

        assert result["success"] is True
        assert result["data"]["role"] == "assistant"
        assert "assistant_turn" in result["data"]["tags"]

    @pytest.mark.asyncio
    async def test_acms_store_conversation_turn_invalid_role(self):
        """Test storing conversation turn with invalid role."""
        result = await acms_store_conversation_turn(
            role="invalid_role",
            content="Test content"
        )

        assert result["success"] is False
        assert "validation_error" in result.get("details", {})

    # ========================================================================
    # Tool 10: acms_get_memory_stats
    # ========================================================================

    @pytest.mark.asyncio
    async def test_acms_get_memory_stats_success(self):
        """Test retrieving memory statistics."""
        result = await acms_get_memory_stats()

        assert result["success"] is True
        assert "data" in result

        data = result["data"]
        assert "total_memories" in data
        assert "by_tier" in data
        assert "SHORT" in data["by_tier"]
        assert "MID" in data["by_tier"]
        assert "LONG" in data["by_tier"]
        assert "by_phase" in data
        assert "top_tags" in data
        assert isinstance(data["top_tags"], list)
        assert "total_access_count" in data

    # ========================================================================
    # Tool 11: acms_tier_transition
    # ========================================================================

    @pytest.mark.asyncio
    async def test_acms_tier_transition_success(self):
        """Test transitioning memory between tiers."""
        # Store a SHORT tier memory
        unique_id = str(uuid.uuid4())[:8]
        content = f"Memory for tier transition {unique_id}"

        store_result = await acms_store_memory(
            content=content,
            tier="SHORT"
        )
        memory_id = store_result["data"]["memory_id"]

        # Transition to LONG
        result = await acms_tier_transition(
            memory_id=memory_id,
            new_tier="LONG"
        )

        assert result["success"] is True
        assert result["data"]["old_tier"] == "SHORT"
        assert result["data"]["new_tier"] == "LONG"
        assert result["data"]["memory_id"] == memory_id

        # Verify it was updated
        get_result = await acms_get_memory(memory_id=memory_id)
        assert get_result["data"]["tier"] == "LONG"

    @pytest.mark.asyncio
    async def test_acms_tier_transition_same_tier(self):
        """Test transitioning memory to same tier."""
        # Store a memory
        unique_id = str(uuid.uuid4())[:8]
        store_result = await acms_store_memory(
            content=f"Same tier test {unique_id}",
            tier="MID"
        )
        memory_id = store_result["data"]["memory_id"]

        # Try to transition to same tier
        result = await acms_tier_transition(
            memory_id=memory_id,
            new_tier="MID"
        )

        assert result["success"] is True
        assert "already at target tier" in result["data"].get("message", "").lower()

    @pytest.mark.asyncio
    async def test_acms_tier_transition_invalid_tier(self):
        """Test transitioning to invalid tier."""
        # Store a memory
        unique_id = str(uuid.uuid4())[:8]
        store_result = await acms_store_memory(
            content=f"Invalid tier test {unique_id}"
        )
        memory_id = store_result["data"]["memory_id"]

        # Try invalid tier
        result = await acms_tier_transition(
            memory_id=memory_id,
            new_tier="INVALID"
        )

        assert result["success"] is False
        assert "validation_error" in result.get("details", {})

    # ========================================================================
    # Tool 12: acms_semantic_search
    # ========================================================================

    @pytest.mark.asyncio
    async def test_acms_semantic_search_success(self):
        """Test semantic search without filters."""
        unique_id = str(uuid.uuid4())[:8]
        await acms_store_memory(
            content=f"Python async programming tutorial {unique_id}",
            tags=["python", "async"]
        )

        result = await acms_semantic_search(
            query="Python async",
            limit=5
        )

        assert result["success"] is True
        assert "data" in result
        assert "query" in result["data"]
        assert "results" in result["data"]
        assert "total_results" in result["data"]
        assert isinstance(result["data"]["results"], list)

    @pytest.mark.asyncio
    async def test_acms_semantic_search_with_filters(self):
        """Test semantic search with tier and tag filters."""
        unique_id = str(uuid.uuid4())[:8]
        unique_tag = f"semantic_{uuid.uuid4().hex[:8]}"

        await acms_store_memory(
            content=f"Filtered semantic search test {unique_id}",
            tags=[unique_tag, "test"],
            tier="LONG"
        )

        result = await acms_semantic_search(
            query="semantic search",
            filters={"tier": "LONG", "tag": unique_tag},
            limit=10
        )

        assert result["success"] is True
        assert "filters_applied" in result["data"]
        assert result["data"]["filters_applied"]["tier"] == "LONG"
        assert result["data"]["filters_applied"]["tag"] == unique_tag

        # All results should match filters
        for mem in result["data"]["results"]:
            assert mem.get("tier") == "LONG"
            assert unique_tag in mem.get("tags", [])


class TestMCPIntegration:
    """Test MCP server integration."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_workflow(self):
        """Test complete workflow: store → search → verify."""
        # Store memory with unique content
        unique_id = str(uuid.uuid4())[:8]
        unique_content = f"MCP integration test - unique content {unique_id}"

        store_result = await acms_store_memory(
            content=unique_content,
            tags=["integration", "test"]
        )

        assert store_result["success"] is True
        memory_id = store_result["data"]["memory_id"]

        # Search for it
        search_result = await acms_search_memories(
            query=f"MCP integration test {unique_id}",
            limit=5
        )

        assert search_result["success"] is True

        # Verify our memory is in results
        found = False
        for memory in search_result["data"]:
            if memory["memory_id"] == memory_id:
                found = True
                assert memory["content"] == unique_content
                assert "integration" in memory["tags"]
                break

        assert found, "Stored memory not found in search results"

    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test MCP server initialization and configuration."""
        # Verify server configuration is loaded correctly
        from src.mcp.config import MCPConfig

        # Check database configuration
        assert MCPConfig.POSTGRES_PORT == 40432
        assert MCPConfig.POSTGRES_DB == "acms"
        assert MCPConfig.POSTGRES_USER == "acms"

        # Check Weaviate configuration
        assert MCPConfig.WEAVIATE_PORT == 40480
        assert MCPConfig.WEAVIATE_GRPC_PORT == 40481

        # Check Ollama configuration
        assert MCPConfig.OLLAMA_PORT == 40434
        assert MCPConfig.OLLAMA_MODEL == "all-minilm:22m"

        # Verify default user ID is set
        assert MCPConfig.DEFAULT_USER_ID == "00000000-0000-0000-0000-000000000001"

    @pytest.mark.asyncio
    async def test_tool_discovery(self):
        """Test that all 12 MCP tools are registered."""
        # Import the server module
        import src.mcp.server as server_module

        # Expected tools
        expected_tools = [
            "acms_store_memory",
            "acms_search_memories",
            "acms_get_memory",
            "acms_update_memory",
            "acms_delete_memory",
            "acms_list_memories",
            "acms_search_by_tag",
            "acms_get_conversation_context",
            "acms_store_conversation_turn",
            "acms_get_memory_stats",
            "acms_tier_transition",
            "acms_semantic_search",
        ]

        # Verify each tool exists and is callable
        for tool_name in expected_tools:
            assert hasattr(server_module, tool_name), f"Tool {tool_name} not found"
            tool_func = getattr(server_module, tool_name)
            assert callable(tool_func), f"Tool {tool_name} is not callable"

    @pytest.mark.asyncio
    async def test_end_to_end_workflow(self):
        """Complete end-to-end workflow testing all 12 tools."""
        # Step 1: Store 3 memories with different tiers
        unique_id = str(uuid.uuid4())[:8]

        # Store SHORT tier memory
        short_result = await acms_store_memory(
            content=f"E2E test SHORT tier memory {unique_id}",
            tags=["e2e_test", "short"],
            tier="SHORT"
        )
        assert short_result["success"] is True
        short_id = short_result["data"]["memory_id"]

        # Store MID tier memory
        mid_result = await acms_store_memory(
            content=f"E2E test MID tier memory {unique_id}",
            tags=["e2e_test", "mid"],
            tier="MID"
        )
        assert mid_result["success"] is True
        mid_id = mid_result["data"]["memory_id"]

        # Store LONG tier memory
        long_result = await acms_store_memory(
            content=f"E2E test LONG tier memory {unique_id}",
            tags=["e2e_test", "long"],
            tier="LONG"
        )
        assert long_result["success"] is True
        long_id = long_result["data"]["memory_id"]

        # Step 2: Search and verify retrieval
        search_result = await acms_search_memories(
            query=f"E2E test {unique_id}",
            limit=10
        )
        assert search_result["success"] is True
        assert len(search_result["data"]) >= 3

        # Step 3: Update memory
        update_result = await acms_update_memory(
            memory_id=short_id,
            content=f"UPDATED E2E test SHORT tier {unique_id}",
            tags=["e2e_test", "short", "updated"]
        )
        assert update_result["success"] is True
        assert "updated" in update_result["data"]["tags"]

        # Step 4: Get by ID
        get_result = await acms_get_memory(memory_id=mid_id)
        assert get_result["success"] is True
        assert get_result["data"]["tier"] == "MID"
        assert "e2e_test" in get_result["data"]["tags"]

        # Step 5: List with filters
        list_result = await acms_list_memories(
            tag="e2e_test",
            limit=20
        )
        assert list_result["success"] is True
        assert len(list_result["data"]) >= 3

        # Step 6: Search by tag
        tag_result = await acms_search_by_tag(
            tag="e2e_test",
            limit=10
        )
        assert tag_result["success"] is True
        assert len(tag_result["data"]) >= 3

        # Step 7: Get conversation context
        context_result = await acms_get_conversation_context(
            query=f"E2E test memories {unique_id}",
            limit=5
        )
        assert context_result["success"] is True
        assert context_result["data"]["total_retrieved"] > 0

        # Step 8: Store conversation turn
        turn_result = await acms_store_conversation_turn(
            role="user",
            content=f"E2E workflow test conversation {unique_id}",
            context="Integration testing"
        )
        assert turn_result["success"] is True
        assert turn_result["data"]["role"] == "user"
        turn_id = turn_result["data"]["memory_id"]

        # Step 9: Get statistics
        stats_result = await acms_get_memory_stats()
        assert stats_result["success"] is True
        assert stats_result["data"]["total_memories"] >= 4
        assert all(tier in stats_result["data"]["by_tier"] for tier in ["SHORT", "MID", "LONG"])

        # Step 10: Tier transition
        transition_result = await acms_tier_transition(
            memory_id=mid_id,
            new_tier="LONG"
        )
        assert transition_result["success"] is True
        assert transition_result["data"]["old_tier"] == "MID"
        assert transition_result["data"]["new_tier"] == "LONG"

        # Verify transition took effect
        verify_result = await acms_get_memory(memory_id=mid_id)
        assert verify_result["data"]["tier"] == "LONG"

        # Step 11: Advanced semantic search with filters
        semantic_result = await acms_semantic_search(
            query=f"E2E test {unique_id}",
            filters={"tier": "LONG", "tag": "e2e_test"},
            limit=10
        )
        assert semantic_result["success"] is True
        # Should find at least 2 LONG tier memories (original long + transitioned mid)
        assert semantic_result["data"]["total_results"] >= 2

        # Step 12: Delete memory and verify
        delete_result = await acms_delete_memory(memory_id=turn_id)
        assert delete_result["success"] is True
        assert delete_result["data"]["deleted"] is True

        # Verify deletion
        verify_delete = await acms_get_memory(memory_id=turn_id)
        assert verify_delete["success"] is False
        assert "not found" in verify_delete["error"].lower()

        # Clean up remaining test memories
        await acms_delete_memory(memory_id=short_id)
        await acms_delete_memory(memory_id=mid_id)
        await acms_delete_memory(memory_id=long_id)


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
