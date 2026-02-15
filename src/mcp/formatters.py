"""Response formatting utilities for MCP tools."""
from typing import Any, Dict, List, Optional
from datetime import datetime


def format_success_response(data: Any, message: Optional[str] = None) -> Dict[str, Any]:
    """
    Format successful MCP tool response.

    Args:
        data: Response data (can be any JSON-serializable type)
        message: Optional success message

    Returns:
        dict: Formatted response with success=True
    """
    response = {
        "success": True,
        "data": data
    }
    if message:
        response["message"] = message
    return response


def format_error_response(error: str, details: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Format error MCP tool response.

    Args:
        error: Error message
        details: Optional additional error details

    Returns:
        dict: Formatted response with success=False
    """
    response = {
        "success": False,
        "error": error
    }
    if details:
        response["details"] = details
    return response


def format_memory_response(memory) -> Dict[str, Any]:
    """
    Format memory object for MCP response.

    Args:
        memory: Memory object from storage layer

    Returns:
        dict: Formatted memory data
    """
    return {
        "memory_id": str(memory.memory_id),
        "user_id": memory.user_id,
        "content": memory.content,
        "tags": memory.tags or [],
        "tier": memory.tier,
        "created_at": memory.created_at.isoformat() if isinstance(memory.created_at, datetime) else memory.created_at,
        "updated_at": memory.updated_at.isoformat() if isinstance(memory.updated_at, datetime) else memory.updated_at
    }


def format_search_results(memories: List, include_score: bool = True) -> List[Dict[str, Any]]:
    """
    Format list of memory search results.

    Args:
        memories: List of memory objects with optional distance/score
        include_score: Whether to include similarity scores

    Returns:
        list: Formatted memory results
    """
    results = []
    for item in memories:
        # Handle both (memory, distance) tuples and plain memory objects
        if isinstance(item, tuple):
            memory, distance = item
            formatted = format_memory_response(memory)
            if include_score:
                formatted["similarity_score"] = 1 - distance  # Convert distance to similarity
        else:
            memory = item
            formatted = format_memory_response(memory)

        results.append(formatted)

    return results


def format_stats_response(stats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format memory statistics for response.

    Args:
        stats: Statistics dictionary

    Returns:
        dict: Formatted stats
    """
    return {
        "total_memories": stats.get("total", 0),
        "by_tier": {
            "SHORT": stats.get("short", 0),
            "MID": stats.get("mid", 0),
            "LONG": stats.get("long", 0)
        },
        "by_source": stats.get("by_source", {}),
        "oldest": stats.get("oldest"),
        "newest": stats.get("newest")
    }
