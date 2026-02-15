"""ACMS MCP Server - Exposes memory operations as MCP tools."""
import sys
import os
import warnings
from pathlib import Path
from io import StringIO

# Add project root to path FIRST (before any imports)
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Load .env file for local development (Claude Desktop passes env vars directly)
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Suppress ALL output during initialization (MCP protocol uses stdio)
_original_stdout = sys.stdout
_original_stderr = sys.stderr
sys.stdout = StringIO()
sys.stderr = StringIO()

# Suppress warnings
warnings.filterwarnings("ignore")

# Disable logging during import
import logging
logging.disable(logging.CRITICAL)

from mcp.server.fastmcp import FastMCP
from typing import Optional, List, Dict, Any
import asyncio
from uuid import UUID

# Import ACMS components (from Phase 2A)
from src.storage.memory_crud import MemoryCRUD
from src.storage.database import get_session
from src.mcp.config import MCPConfig
from src.storage.models import MemoryItem
from src.mcp.validators import (
    StoreMemoryInput,
    SearchMemoriesInput,
    GetMemoryInput,
    UpdateMemoryInput,
    DeleteMemoryInput,
    ListMemoriesInput,
    SearchByTagInput,
    GetConversationContextInput,
    StoreConversationTurnInput,
    TierTransitionInput,
    SemanticSearchInput,
)
from src.mcp.formatters import (
    format_success_response,
    format_error_response,
)
from src.mcp.logging_utils import log_mcp_call, logger

# Initialize FastMCP server
mcp_server = FastMCP(MCPConfig.SERVER_NAME)

# Initialize storage layer (from Phase 2A) - keep stderr suppressed
memory_crud = MemoryCRUD()

# Restore stdout/stderr and logging after ALL initialization
sys.stdout = _original_stdout
sys.stderr = _original_stderr
logging.disable(logging.NOTSET)
logging.getLogger().setLevel(logging.ERROR)


# ============================================================================
# TOOL 1: acms_store_memory
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_store_memory(
    content: str,
    tags: Optional[List[str]] = None,
    tier: str = "SHORT",
    phase: Optional[str] = None
) -> Dict[str, Any]:
    """
    Store a new memory in ACMS.

    This tool encrypts and stores content with optional tags and tier classification.
    Memories are searchable via semantic search and can be organized by tiers:
    - SHORT: Recent context (hours to days)
    - MID: Medium-term knowledge (days to weeks)
    - LONG: Long-term important information (weeks to months)

    Args:
        content: The memory content to store (1-10000 characters)
        tags: Optional list of categorization tags
        tier: Memory tier - SHORT (default), MID, or LONG
        phase: Optional phase/context identifier

    Returns:
        dict: Success response with memory_id, or error response

    Example:
        {
            "success": true,
            "data": {
                "memory_id": "550e8400-e29b-41d4-a716-446655440000",
                "content": "...",
                "tags": ["coding", "python"],
                "tier": "SHORT",
                "created_at": "2025-10-13T22:00:00Z"
            }
        }
    """
    try:
        # Validate input
        validated_input = StoreMemoryInput(
            content=content,
            tags=tags,
            tier=tier,
            phase=phase
        )

        # Store memory using Phase 2A storage layer
        memory_id = await memory_crud.create_memory(
            user_id=MCPConfig.DEFAULT_USER_ID,
            content=validated_input.content,
            tags=validated_input.tags,
            tier=validated_input.tier,
            phase=validated_input.phase
        )

        if memory_id is None:
            return format_error_response(
                error="Duplicate memory detected",
                details={"reason": "Memory with identical content already exists"}
            )

        # Fetch the created memory to return full details
        memory_data = await memory_crud.get_memory(memory_id, decrypt=False)

        # Format response
        return format_success_response(
            data={
                "memory_id": memory_data["memory_id"],
                "user_id": memory_data["user_id"],
                "content": memory_data["content"],
                "tags": memory_data["tags"],
                "tier": memory_data["tier"],
                "phase": memory_data["phase"],
                "created_at": memory_data["created_at"].isoformat() if hasattr(memory_data["created_at"], "isoformat") else str(memory_data["created_at"])
            },
            message="Memory stored successfully"
        )

    except ValueError as e:
        logger.warning(f"Validation error in acms_store_memory: {e}")
        return format_error_response(
            error="Invalid input",
            details={"validation_error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error in acms_store_memory: {e}", exc_info=True)
        return format_error_response(
            error="Failed to store memory",
            details={"exception": str(e)}
        )


# ============================================================================
# TOOL 2: acms_search_memories
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_search_memories(
    query: str,
    limit: int = 10,
    user_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Semantic search across stored memories.

    Uses Weaviate vector search with OpenAI embeddings to find semantically
    similar memories. Returns results ranked by relevance.

    Args:
        query: Natural language search query (1-1000 characters)
        limit: Maximum number of results to return (1-100, default 10)
        user_id: Optional user filter (defaults to 'default')

    Returns:
        dict: Success response with list of matching memories, or error response

    Example:
        {
            "success": true,
            "data": [
                {
                    "memory_id": "...",
                    "content": "...",
                    "tags": [...],
                    "similarity_score": 0.85,
                    "created_at": "..."
                },
                ...
            ]
        }
    """
    try:
        # Validate input
        validated_input = SearchMemoriesInput(
            query=query,
            limit=limit,
            user_id=user_id or MCPConfig.DEFAULT_USER_ID
        )

        # Search using Phase 2A storage layer
        # This uses Weaviate vector search with OpenAI embeddings
        results = await memory_crud.search_memories(
            query=validated_input.query,
            user_id=validated_input.user_id,
            limit=validated_input.limit
        )

        # Format results with similarity scores
        formatted_results = []
        for result in results:
            formatted = {
                "memory_id": result["memory_id"],
                "content": result["content"],
                "tags": result.get("tags", []),
                "tier": result.get("tier"),
                "phase": result.get("phase"),
                "similarity_score": 1 - result.get("semantic_distance", 0.0),  # Convert distance to score
                "created_at": result["created_at"].isoformat() if hasattr(result["created_at"], "isoformat") else str(result["created_at"])
            }
            formatted_results.append(formatted)

        # Format response
        return format_success_response(
            data=formatted_results,
            message=f"Found {len(formatted_results)} matching memories"
        )

    except ValueError as e:
        logger.warning(f"Validation error in acms_search_memories: {e}")
        return format_error_response(
            error="Invalid input",
            details={"validation_error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error in acms_search_memories: {e}", exc_info=True)
        return format_error_response(
            error="Failed to search memories",
            details={"exception": str(e)}
        )


# ============================================================================
# TOOL 3: acms_get_memory
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_get_memory(memory_id: str) -> Dict[str, Any]:
    """
    Retrieve a specific memory by its ID.

    Gets complete memory details including content, metadata, tags, tier,
    access count, and timestamps.

    Args:
        memory_id: UUID of the memory to retrieve

    Returns:
        dict: Success response with memory data, or error response

    Example:
        {
            "success": true,
            "data": {
                "memory_id": "...",
                "user_id": "...",
                "content": "...",
                "tags": [...],
                "tier": "SHORT",
                "access_count": 5,
                "created_at": "...",
                "updated_at": "..."
            }
        }
    """
    try:
        # Validate input
        validated_input = GetMemoryInput(memory_id=memory_id)

        # Get memory from storage layer
        memory_data = await memory_crud.get_memory(
            memory_id=validated_input.memory_id,
            decrypt=False  # Don't include encrypted content in response
        )

        if memory_data is None:
            return format_error_response(
                error="Memory not found",
                details={"memory_id": memory_id}
            )

        # Format response
        formatted_memory = {
            "memory_id": memory_data["memory_id"],
            "user_id": memory_data["user_id"],
            "content": memory_data["content"],
            "tags": memory_data.get("tags", []),
            "tier": memory_data.get("tier"),
            "phase": memory_data.get("phase"),
            "crs_score": memory_data.get("crs_score"),
            "access_count": memory_data.get("access_count", 0),
            "created_at": memory_data["created_at"].isoformat() if hasattr(memory_data["created_at"], "isoformat") else str(memory_data["created_at"]),
            "updated_at": memory_data["updated_at"].isoformat() if hasattr(memory_data["updated_at"], "isoformat") else str(memory_data["updated_at"]),
            "last_accessed": memory_data.get("last_accessed").isoformat() if memory_data.get("last_accessed") and hasattr(memory_data.get("last_accessed"), "isoformat") else None
        }

        return format_success_response(
            data=formatted_memory,
            message="Memory retrieved successfully"
        )

    except ValueError as e:
        logger.warning(f"Validation error in acms_get_memory: {e}")
        return format_error_response(
            error="Invalid input",
            details={"validation_error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error in acms_get_memory: {e}", exc_info=True)
        return format_error_response(
            error="Failed to retrieve memory",
            details={"exception": str(e)}
        )


# ============================================================================
# TOOL 4: acms_update_memory
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_update_memory(
    memory_id: str,
    content: str,
    tags: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Update an existing memory's content and/or tags.

    Args:
        memory_id: UUID of the memory to update
        content: New content for the memory
        tags: Optional new tags (replaces existing tags)

    Returns:
        dict: Success response with updated memory data, or error response
    """
    try:
        # Validate input
        validated_input = UpdateMemoryInput(
            memory_id=memory_id,
            content=content,
            tags=tags
        )

        # Update memory
        success = await memory_crud.update_memory(
            memory_id=validated_input.memory_id,
            content=validated_input.content,
            tags=validated_input.tags
        )

        if not success:
            return format_error_response(
                error="Memory not found",
                details={"memory_id": memory_id}
            )

        # Fetch updated memory
        updated_memory = await memory_crud.get_memory(memory_id, decrypt=False)

        formatted_memory = {
            "memory_id": updated_memory["memory_id"],
            "content": updated_memory["content"],
            "tags": updated_memory.get("tags", []),
            "updated_at": updated_memory["updated_at"].isoformat() if hasattr(updated_memory["updated_at"], "isoformat") else str(updated_memory["updated_at"])
        }

        return format_success_response(
            data=formatted_memory,
            message="Memory updated successfully"
        )

    except ValueError as e:
        logger.warning(f"Validation error in acms_update_memory: {e}")
        return format_error_response(
            error="Invalid input",
            details={"validation_error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error in acms_update_memory: {e}", exc_info=True)
        return format_error_response(
            error="Failed to update memory",
            details={"exception": str(e)}
        )


# ============================================================================
# TOOL 5: acms_delete_memory
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_delete_memory(memory_id: str) -> Dict[str, Any]:
    """
    Delete a memory from storage.

    Removes memory from both PostgreSQL and Weaviate.

    Args:
        memory_id: UUID of the memory to delete

    Returns:
        dict: Success response or error response
    """
    try:
        # Validate input
        validated_input = DeleteMemoryInput(memory_id=memory_id)

        # Delete memory
        success = await memory_crud.delete_memory(validated_input.memory_id)

        if not success:
            return format_error_response(
                error="Memory not found",
                details={"memory_id": memory_id}
            )

        return format_success_response(
            data={"memory_id": memory_id, "deleted": True},
            message="Memory deleted successfully"
        )

    except ValueError as e:
        logger.warning(f"Validation error in acms_delete_memory: {e}")
        return format_error_response(
            error="Invalid input",
            details={"validation_error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error in acms_delete_memory: {e}", exc_info=True)
        return format_error_response(
            error="Failed to delete memory",
            details={"exception": str(e)}
        )


# ============================================================================
# TOOL 6: acms_list_memories
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_list_memories(
    user_id: Optional[str] = None,
    tag: Optional[str] = None,
    tier: Optional[str] = None,
    limit: int = 20
) -> Dict[str, Any]:
    """
    List memories with optional filters.

    Args:
        user_id: Optional user filter (defaults to default user)
        tag: Optional tag filter
        tier: Optional tier filter (SHORT/MID/LONG)
        limit: Maximum number of results (1-100, default 20)

    Returns:
        dict: Success response with list of memories, or error response
    """
    try:
        # Validate input
        validated_input = ListMemoriesInput(
            user_id=user_id or MCPConfig.DEFAULT_USER_ID,
            tag=tag,
            tier=tier,
            limit=limit
        )

        # List memories
        memories = await memory_crud.list_memories(
            user_id=validated_input.user_id,
            tag=validated_input.tag,
            tier=validated_input.tier,
            limit=validated_input.limit
        )

        # Format results
        formatted_memories = []
        for mem in memories:
            formatted = {
                "memory_id": mem["memory_id"],
                "content": mem["content"],  # Already truncated by list_memories
                "tags": mem.get("tags", []),
                "tier": mem.get("tier"),
                "phase": mem.get("phase"),
                "access_count": mem.get("access_count", 0),
                "created_at": mem["created_at"].isoformat() if hasattr(mem["created_at"], "isoformat") else str(mem["created_at"])
            }
            formatted_memories.append(formatted)

        return format_success_response(
            data=formatted_memories,
            message=f"Found {len(formatted_memories)} memories"
        )

    except ValueError as e:
        logger.warning(f"Validation error in acms_list_memories: {e}")
        return format_error_response(
            error="Invalid input",
            details={"validation_error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error in acms_list_memories: {e}", exc_info=True)
        return format_error_response(
            error="Failed to list memories",
            details={"exception": str(e)}
        )


# ============================================================================
# TOOL 7: acms_search_by_tag
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_search_by_tag(
    tag: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search memories by tag.

    Retrieves all memories that contain the specified tag. This is a simple
    tag-based filter (not semantic search). For semantic/similarity search,
    use acms_search_memories or acms_semantic_search.

    Args:
        tag: Tag to search for (exact match, case-sensitive)
        limit: Maximum number of results (1-100, default 10)

    Returns:
        dict: Success response with list of memories, or error response

    Example:
        {
            "success": true,
            "data": [
                {
                    "memory_id": "...",
                    "content": "...",
                    "tags": ["python", "coding"],
                    "tier": "SHORT",
                    "created_at": "..."
                },
                ...
            ]
        }
    """
    try:
        # Validate input
        validated_input = SearchByTagInput(
            tag=tag,
            limit=limit
        )

        # Use list_memories with tag filter
        memories = await memory_crud.list_memories(
            user_id=MCPConfig.DEFAULT_USER_ID,
            tag=validated_input.tag,
            limit=validated_input.limit
        )

        # Format results
        formatted_memories = []
        for mem in memories:
            formatted = {
                "memory_id": mem["memory_id"],
                "content": mem["content"],
                "tags": mem.get("tags", []),
                "tier": mem.get("tier"),
                "phase": mem.get("phase"),
                "access_count": mem.get("access_count", 0),
                "created_at": mem["created_at"].isoformat() if hasattr(mem["created_at"], "isoformat") else str(mem["created_at"])
            }
            formatted_memories.append(formatted)

        return format_success_response(
            data=formatted_memories,
            message=f"Found {len(formatted_memories)} memories with tag '{tag}'"
        )

    except ValueError as e:
        logger.warning(f"Validation error in acms_search_by_tag: {e}")
        return format_error_response(
            error="Invalid input",
            details={"validation_error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error in acms_search_by_tag: {e}", exc_info=True)
        return format_error_response(
            error="Failed to search by tag",
            details={"exception": str(e)}
        )


# ============================================================================
# TOOL 8: acms_get_conversation_context
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_get_conversation_context(
    query: str,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Retrieve relevant conversation context based on query.

    Uses semantic search to find memories relevant to the current conversation
    context. This is useful for retrieving past conversation turns, user
    preferences, or related discussion topics.

    Args:
        query: Query describing the context needed (1-1000 characters)
        limit: Maximum memories to retrieve (1-50, default 10)

    Returns:
        dict: Success response with contextually relevant memories

    Example:
        {
            "success": true,
            "data": {
                "query": "previous discussion about Python",
                "context_memories": [
                    {
                        "memory_id": "...",
                        "content": "...",
                        "tags": [...],
                        "similarity_score": 0.87,
                        "created_at": "..."
                    },
                    ...
                ],
                "total_retrieved": 5
            }
        }
    """
    try:
        # Validate input
        validated_input = GetConversationContextInput(
            query=query,
            limit=limit
        )

        # Use semantic search to find relevant context
        results = await memory_crud.search_memories(
            query=validated_input.query,
            user_id=MCPConfig.DEFAULT_USER_ID,
            limit=validated_input.limit
        )

        # Format results with similarity scores
        context_memories = []
        for result in results:
            formatted = {
                "memory_id": result["memory_id"],
                "content": result["content"],
                "tags": result.get("tags", []),
                "tier": result.get("tier"),
                "phase": result.get("phase"),
                "similarity_score": 1 - result.get("semantic_distance", 0.0),
                "created_at": result["created_at"].isoformat() if hasattr(result["created_at"], "isoformat") else str(result["created_at"])
            }
            context_memories.append(formatted)

        # Return structured context response
        return format_success_response(
            data={
                "query": validated_input.query,
                "context_memories": context_memories,
                "total_retrieved": len(context_memories)
            },
            message=f"Retrieved {len(context_memories)} contextually relevant memories"
        )

    except ValueError as e:
        logger.warning(f"Validation error in acms_get_conversation_context: {e}")
        return format_error_response(
            error="Invalid input",
            details={"validation_error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error in acms_get_conversation_context: {e}", exc_info=True)
        return format_error_response(
            error="Failed to retrieve conversation context",
            details={"exception": str(e)}
        )


# ============================================================================
# TOOL 9: acms_store_conversation_turn
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_store_conversation_turn(
    role: str,
    content: str,
    context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Store a conversation turn (user or assistant message).

    Stores conversation turns as memories with special tagging for retrieval.
    Useful for building conversation history and context awareness.

    Args:
        role: Role of the speaker ('user' or 'assistant')
        content: The conversation turn content
        context: Optional additional context or metadata

    Returns:
        dict: Success response with stored memory details

    Example:
        {
            "success": true,
            "data": {
                "memory_id": "...",
                "role": "user",
                "content": "...",
                "tags": ["conversation", "user_turn"],
                "tier": "SHORT",
                "created_at": "..."
            }
        }
    """
    try:
        # Validate input
        validated_input = StoreConversationTurnInput(
            role=role,
            content=content,
            context=context
        )

        # Create tags for conversation turn
        tags = ["conversation", f"{validated_input.role}_turn"]
        if validated_input.context:
            tags.append("with_context")

        # Build full content with role prefix
        full_content = f"[{validated_input.role.upper()}]: {validated_input.content}"
        if validated_input.context:
            full_content += f"\n[CONTEXT]: {validated_input.context}"

        # Store as SHORT tier memory (conversation turns are recent context)
        memory_id = await memory_crud.create_memory(
            user_id=MCPConfig.DEFAULT_USER_ID,
            content=full_content,
            tags=tags,
            tier="SHORT",
            phase="conversation"
        )

        if memory_id is None:
            return format_error_response(
                error="Duplicate conversation turn detected",
                details={"reason": "Memory with identical content already exists"}
            )

        # Fetch the created memory
        memory_data = await memory_crud.get_memory(memory_id, decrypt=False)

        # Format response
        return format_success_response(
            data={
                "memory_id": memory_data["memory_id"],
                "role": validated_input.role,
                "content": validated_input.content,
                "context": validated_input.context,
                "tags": memory_data["tags"],
                "tier": memory_data["tier"],
                "phase": memory_data["phase"],
                "created_at": memory_data["created_at"].isoformat() if hasattr(memory_data["created_at"], "isoformat") else str(memory_data["created_at"])
            },
            message=f"Conversation turn stored successfully"
        )

    except ValueError as e:
        logger.warning(f"Validation error in acms_store_conversation_turn: {e}")
        return format_error_response(
            error="Invalid input",
            details={"validation_error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error in acms_store_conversation_turn: {e}", exc_info=True)
        return format_error_response(
            error="Failed to store conversation turn",
            details={"exception": str(e)}
        )


# ============================================================================
# TOOL 10: acms_get_memory_stats
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_get_memory_stats() -> Dict[str, Any]:
    """
    Get statistics about stored memories.

    Returns aggregate statistics including total count, breakdown by tier,
    breakdown by tags, oldest/newest memories, and access patterns.

    Args:
        None

    Returns:
        dict: Success response with memory statistics

    Example:
        {
            "success": true,
            "data": {
                "total_memories": 150,
                "by_tier": {
                    "SHORT": 80,
                    "MID": 45,
                    "LONG": 25
                },
                "by_phase": {
                    "conversation": 60,
                    "knowledge": 90
                },
                "top_tags": [
                    {"tag": "python", "count": 35},
                    {"tag": "coding", "count": 28}
                ],
                "oldest_memory": "2025-01-15T10:30:00Z",
                "newest_memory": "2025-10-13T22:00:00Z",
                "total_access_count": 450
            }
        }
    """
    try:
        user_id = MCPConfig.DEFAULT_USER_ID

        # Get all memories for this user (large limit to get accurate count)
        all_memories = await memory_crud.list_memories(
            user_id=user_id,
            limit=1000  # Large limit to get most memories
        )

        # Calculate stats from the list
        total = len(all_memories)
        by_tier = {"SHORT": 0, "MID": 0, "LONG": 0}
        by_phase = {}
        tag_counts = {}
        total_accesses = 0
        oldest = None
        newest = None

        for mem in all_memories:
            # Count by tier
            tier = mem.get("tier", "SHORT")
            by_tier[tier] = by_tier.get(tier, 0) + 1

            # Count by phase
            phase = mem.get("phase")
            if phase:
                by_phase[phase] = by_phase.get(phase, 0) + 1

            # Count tags
            for tag in mem.get("tags", []):
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

            # Sum access counts
            total_accesses += mem.get("access_count", 0)

            # Track oldest/newest
            created = mem.get("created_at")
            if created:
                if oldest is None or created < oldest:
                    oldest = created
                if newest is None or created > newest:
                    newest = created

        # Format top tags
        top_tags = [
            {"tag": tag, "count": count}
            for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        stats_data = {
            "total_memories": total,
            "by_tier": by_tier,
            "by_phase": by_phase,
            "top_tags": top_tags,
            "oldest_memory": oldest.isoformat() if oldest and hasattr(oldest, "isoformat") else None,
            "newest_memory": newest.isoformat() if newest and hasattr(newest, "isoformat") else None,
            "total_access_count": total_accesses
        }

        return format_success_response(
            data=stats_data,
            message="Memory statistics retrieved successfully"
        )

    except Exception as e:
        logger.error(f"Error in acms_get_memory_stats: {e}", exc_info=True)
        return format_error_response(
            error="Failed to retrieve memory statistics",
            details={"exception": str(e)}
        )


# ============================================================================
# TOOL 11: acms_tier_transition
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_tier_transition(
    memory_id: str,
    new_tier: str
) -> Dict[str, Any]:
    """
    Transition a memory to a different tier.

    Moves memory between SHORT/MID/LONG tiers based on importance and
    retention needs. This is useful for promoting important short-term
    memories to long-term storage.

    Args:
        memory_id: UUID of the memory to transition
        new_tier: Target tier (SHORT/MID/LONG)

    Returns:
        dict: Success response with updated memory details

    Example:
        {
            "success": true,
            "data": {
                "memory_id": "...",
                "old_tier": "SHORT",
                "new_tier": "LONG",
                "transitioned_at": "2025-10-13T22:00:00Z"
            }
        }
    """
    try:
        # Validate input
        validated_input = TierTransitionInput(
            memory_id=memory_id,
            new_tier=new_tier
        )

        # Get current memory to check if it exists and get old tier
        current_memory = await memory_crud.get_memory(
            memory_id=validated_input.memory_id,
            decrypt=False
        )

        if current_memory is None:
            return format_error_response(
                error="Memory not found",
                details={"memory_id": memory_id}
            )

        old_tier = current_memory.get("tier")

        # Check if already at target tier
        if old_tier == validated_input.new_tier:
            return format_success_response(
                data={
                    "memory_id": memory_id,
                    "old_tier": old_tier,
                    "new_tier": validated_input.new_tier,
                    "message": "Memory is already at target tier"
                },
                message="No transition needed"
            )

        # Update tier using SQLAlchemy session
        async with get_session() as session:
            memory_obj = await session.get(MemoryItem, UUID(validated_input.memory_id))
            if memory_obj:
                memory_obj.tier = validated_input.new_tier
                await session.commit()

        # Get updated memory
        updated_memory = await memory_crud.get_memory(memory_id, decrypt=False)

        return format_success_response(
            data={
                "memory_id": memory_id,
                "old_tier": old_tier,
                "new_tier": validated_input.new_tier,
                "transitioned_at": updated_memory["updated_at"].isoformat() if hasattr(updated_memory["updated_at"], "isoformat") else str(updated_memory["updated_at"])
            },
            message=f"Memory transitioned from {old_tier} to {validated_input.new_tier}"
        )

    except ValueError as e:
        logger.warning(f"Validation error in acms_tier_transition: {e}")
        return format_error_response(
            error="Invalid input",
            details={"validation_error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error in acms_tier_transition: {e}", exc_info=True)
        return format_error_response(
            error="Failed to transition memory tier",
            details={"exception": str(e)}
        )


# ============================================================================
# TOOL 12: acms_semantic_search
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_semantic_search(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Advanced semantic search with optional filters.

    Uses Weaviate vector search with OpenAI embeddings, supporting additional
    filters like tier, tags, and date ranges. This is more powerful than
    acms_search_memories as it supports filtering.

    Args:
        query: Natural language search query (1-1000 characters)
        filters: Optional filters dict with keys: tier, tag, min_score
        limit: Maximum results (1-100, default 10)

    Returns:
        dict: Success response with filtered search results

    Example:
        {
            "success": true,
            "data": {
                "query": "Python best practices",
                "filters_applied": {"tier": "LONG", "tag": "coding"},
                "results": [
                    {
                        "memory_id": "...",
                        "content": "...",
                        "similarity_score": 0.92,
                        "tier": "LONG",
                        "tags": ["python", "coding"]
                    },
                    ...
                ],
                "total_results": 5
            }
        }
    """
    try:
        # Validate input
        validated_input = SemanticSearchInput(
            query=query,
            filters=filters,
            limit=limit
        )

        # First do semantic search
        results = await memory_crud.search_memories(
            query=validated_input.query,
            user_id=MCPConfig.DEFAULT_USER_ID,
            limit=validated_input.limit * 2  # Get more results for filtering
        )

        # Apply filters if provided
        filtered_results = []
        filters_applied = validated_input.filters or {}

        for result in results:
            # Check tier filter
            if filters_applied.get("tier"):
                if result.get("tier") != filters_applied["tier"]:
                    continue

            # Check tag filter
            if filters_applied.get("tag"):
                if filters_applied["tag"] not in result.get("tags", []):
                    continue

            # Check min_score filter
            similarity_score = 1 - result.get("semantic_distance", 0.0)
            if filters_applied.get("min_score"):
                if similarity_score < filters_applied["min_score"]:
                    continue

            # Format and add to results
            formatted = {
                "memory_id": result["memory_id"],
                "content": result["content"],
                "tags": result.get("tags", []),
                "tier": result.get("tier"),
                "phase": result.get("phase"),
                "similarity_score": similarity_score,
                "created_at": result["created_at"].isoformat() if hasattr(result["created_at"], "isoformat") else str(result["created_at"])
            }
            filtered_results.append(formatted)

            # Stop if we have enough results
            if len(filtered_results) >= validated_input.limit:
                break

        # Return structured response
        return format_success_response(
            data={
                "query": validated_input.query,
                "filters_applied": filters_applied,
                "results": filtered_results,
                "total_results": len(filtered_results)
            },
            message=f"Found {len(filtered_results)} matching memories"
        )

    except ValueError as e:
        logger.warning(f"Validation error in acms_semantic_search: {e}")
        return format_error_response(
            error="Invalid input",
            details={"validation_error": str(e)}
        )
    except Exception as e:
        logger.error(f"Error in acms_semantic_search: {e}", exc_info=True)
        return format_error_response(
            error="Failed to perform semantic search",
            details={"exception": str(e)}
        )


# ============================================================================
# TOOL 13: acms_get_qa_batch (Knowledge Extraction Support)
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_get_qa_batch(
    batch_size: int = 10,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get a batch of Q&A pairs from query_history for knowledge extraction.

    Use this to get Q&A pairs that need knowledge extraction. Claude Desktop
    can process these and extract structured knowledge (intent, entities,
    topics, facts) then store via acms_store_knowledge.

    Args:
        batch_size: Number of Q&A pairs to return (1-50, default 10)
        offset: Skip first N records (for pagination)

    Returns:
        dict: Batch of Q&A pairs with query_id, question, answer

    Example:
        {
            "success": true,
            "data": {
                "batch": [
                    {
                        "query_id": "uuid",
                        "question": "How do I optimize SQL?",
                        "answer": "There are several strategies..."
                    }
                ],
                "total_remaining": 3800,
                "batch_size": 10,
                "offset": 0
            }
        }
    """
    from sqlalchemy import text

    try:
        # Validate batch_size
        if batch_size < 1:
            batch_size = 1
        elif batch_size > 50:
            batch_size = 50

        async with get_session() as session:
            # Get Q&A pairs that don't have knowledge extracted yet
            # Check by looking for matching source_query_id in ACMS_Knowledge_v2
            result = await session.execute(text("""
                SELECT query_id, question, answer, user_id, created_at
                FROM query_history
                WHERE answer IS NOT NULL
                  AND LENGTH(answer) > 100
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """), {"limit": batch_size, "offset": offset})

            rows = result.fetchall()

            # Get total count
            count_result = await session.execute(text("""
                SELECT COUNT(*) FROM query_history
                WHERE answer IS NOT NULL AND LENGTH(answer) > 100
            """))
            total_count = count_result.scalar()

            batch = []
            for row in rows:
                batch.append({
                    "query_id": str(row.query_id),
                    "question": row.question[:2000] if row.question else "",
                    "answer": row.answer[:10000] if row.answer else "",
                    "user_id": str(row.user_id),
                    "created_at": row.created_at.isoformat() if row.created_at else None
                })

            return format_success_response(
                data={
                    "batch": batch,
                    "batch_size": len(batch),
                    "offset": offset,
                    "total_remaining": max(0, total_count - offset - len(batch)),
                    "total_records": total_count
                },
                message=f"Retrieved {len(batch)} Q&A pairs for knowledge extraction"
            )

    except Exception as e:
        logger.error(f"Error in acms_get_qa_batch: {e}", exc_info=True)
        return format_error_response(
            error="Failed to get Q&A batch",
            details={"exception": str(e)}
        )


# ============================================================================
# TOOL 14: acms_store_knowledge (Knowledge Extraction Support)
# ============================================================================

@log_mcp_call
@mcp_server.tool()
async def acms_store_knowledge(
    query_id: str,
    canonical_query: str,
    answer_summary: str,
    primary_intent: str,
    problem_domain: str,
    why_context: str,
    topic_cluster: str,
    related_topics: List[str],
    key_facts: List[str],
    entities: Optional[List[Dict[str, Any]]] = None,
    relations: Optional[List[Dict[str, Any]]] = None,
    user_context_signals: Optional[List[str]] = None,
    extraction_confidence: float = 0.85
) -> Dict[str, Any]:
    """
    Store extracted knowledge to ACMS_Knowledge_v2.

    After Claude Desktop processes Q&A pairs and extracts structured knowledge,
    use this tool to store the results. This enables semantic search over
    user's accumulated knowledge with intent/entity understanding.

    Args:
        query_id: Source query_history ID (for traceability)
        canonical_query: Normalized/cleaned version of the question
        answer_summary: Concise summary of the answer (1-3 sentences)
        primary_intent: Why the user asked this (e.g., "learning", "debugging")
        problem_domain: Category (e.g., "python-programming", "sql-optimization")
        why_context: Deeper context about user's motivation
        topic_cluster: Main topic cluster (e.g., "python-concurrency")
        related_topics: List of related topic tags
        key_facts: List of key facts extracted from the answer
        entities: Optional list of entities [{name, type, canonical, importance}]
        relations: Optional list of relations [{from_entity, to_entity, relation_type}]
        user_context_signals: Optional signals about user context
        extraction_confidence: Confidence score 0-1 (default 0.85)

    Returns:
        dict: Success with weaviate_id, or error

    Example:
        {
            "success": true,
            "data": {
                "weaviate_id": "uuid",
                "topic_cluster": "python-concurrency",
                "facts_count": 5
            }
        }
    """
    from src.storage.weaviate_client import WeaviateClient
    from src.embeddings.openai_embeddings import OpenAIEmbeddings
    import json
    from datetime import datetime

    try:
        # Initialize clients
        weaviate = WeaviateClient()
        embeddings = OpenAIEmbeddings()

        # Generate embedding for the canonical query
        embedding = embeddings.generate_embedding(canonical_query[:8000])

        # Prepare entities and relations as JSON
        entities_json = json.dumps(entities or [])
        relations_json = json.dumps(relations or [])

        # Prepare properties matching ACMS_Knowledge_v2 schema
        properties = {
            "canonical_query": canonical_query[:2000],
            "answer_summary": answer_summary[:5000],
            "full_answer": answer_summary,  # Could be fuller version
            "primary_intent": primary_intent[:200],
            "problem_domain": problem_domain[:200],
            "why_context": why_context[:1000],
            "user_context_signals": user_context_signals or [],
            "entities_json": entities_json,
            "relations_json": relations_json,
            "topic_cluster": topic_cluster[:200],
            "related_topics": related_topics[:20] if related_topics else [],
            "key_facts": key_facts[:50] if key_facts else [],
            "user_id": MCPConfig.DEFAULT_USER_ID,
            "source_query_id": query_id,
            "extraction_model": "claude-desktop-mcp",
            "extraction_confidence": min(1.0, max(0.0, extraction_confidence)),
            "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "usage_count": 0,
            "feedback_score": 0.0
        }

        # Store to ACMS_Knowledge_v2
        weaviate_id = weaviate.insert_vector(
            collection="ACMS_Knowledge_v2",
            vector=embedding,
            data=properties
        )

        weaviate.close()

        logger.info(f"Stored knowledge: {weaviate_id[:8]}... topic={topic_cluster}")

        return format_success_response(
            data={
                "weaviate_id": weaviate_id,
                "source_query_id": query_id,
                "topic_cluster": topic_cluster,
                "facts_count": len(key_facts) if key_facts else 0,
                "entities_count": len(entities) if entities else 0
            },
            message=f"Knowledge stored successfully to ACMS_Knowledge_v2"
        )

    except Exception as e:
        logger.error(f"Error in acms_store_knowledge: {e}", exc_info=True)
        return format_error_response(
            error="Failed to store knowledge",
            details={"exception": str(e)}
        )


# ============================================================================
# SERVER ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Don't log to stderr - MCP protocol uses stdio
    # logger.info(f"Starting {MCPConfig.SERVER_NAME} v{MCPConfig.SERVER_VERSION}")

    # Run FastMCP server
    mcp_server.run()
