"""Pydantic models for MCP tool input validation."""
from pydantic import BaseModel, validator, Field
from typing import Optional, List
from enum import Enum


class MemoryTier(str, Enum):
    """Valid memory tier values."""
    SHORT = "SHORT"
    MID = "MID"
    LONG = "LONG"


class StoreMemoryInput(BaseModel):
    """Input validation for acms_store_memory tool."""
    content: str = Field(..., min_length=1, max_length=10000, description="Memory content")
    tags: Optional[List[str]] = Field(default=None, description="Optional categorization tags")
    tier: str = Field(default="SHORT", description="Memory tier (SHORT/MID/LONG)")
    phase: Optional[str] = Field(default=None, description="Optional phase/context")

    @validator('tier')
    def validate_tier(cls, v):
        """Ensure tier is valid."""
        if v not in ["SHORT", "MID", "LONG"]:
            raise ValueError(f"Invalid tier: {v}. Must be SHORT, MID, or LONG")
        return v

    @validator('tags')
    def validate_tags(cls, v):
        """Ensure tags are non-empty strings."""
        if v is not None:
            if not all(isinstance(tag, str) and tag.strip() for tag in v):
                raise ValueError("All tags must be non-empty strings")
            return [tag.strip() for tag in v]
        return v


class SearchMemoriesInput(BaseModel):
    """Input validation for acms_search_memories tool."""
    query: str = Field(..., min_length=1, max_length=1000, description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Max results (1-100)")
    user_id: Optional[str] = Field(default="default", description="User filter")


class GetMemoryInput(BaseModel):
    """Input validation for acms_get_memory tool."""
    memory_id: str = Field(..., description="Memory UUID")


class UpdateMemoryInput(BaseModel):
    """Input validation for acms_update_memory tool."""
    memory_id: str = Field(..., description="Memory UUID")
    content: str = Field(..., min_length=1, max_length=10000, description="Updated content")
    tags: Optional[List[str]] = Field(default=None, description="Updated tags")


class DeleteMemoryInput(BaseModel):
    """Input validation for acms_delete_memory tool."""
    memory_id: str = Field(..., description="Memory UUID")


class ListMemoriesInput(BaseModel):
    """Input validation for acms_list_memories tool."""
    user_id: Optional[str] = Field(default="default", description="Filter by user")
    tag: Optional[str] = Field(default=None, description="Filter by tag")
    tier: Optional[str] = Field(default=None, description="Filter by tier")
    limit: int = Field(default=20, ge=1, le=100, description="Max results")

    @validator('tier')
    def validate_tier(cls, v):
        """Ensure tier is valid if provided."""
        if v is not None and v not in ["SHORT", "MID", "LONG"]:
            raise ValueError(f"Invalid tier: {v}. Must be SHORT, MID, or LONG")
        return v


class SearchByTagInput(BaseModel):
    """Input validation for acms_search_by_tag tool."""
    tag: str = Field(..., min_length=1, description="Tag to search for")
    limit: int = Field(default=10, ge=1, le=100, description="Max results")


class GetConversationContextInput(BaseModel):
    """Input validation for acms_get_conversation_context tool."""
    query: str = Field(..., min_length=1, max_length=1000, description="Context query")
    limit: int = Field(default=10, ge=1, le=50, description="Max memories to retrieve")


class StoreConversationTurnInput(BaseModel):
    """Input validation for acms_store_conversation_turn tool."""
    role: str = Field(..., description="Role (user/assistant)")
    content: str = Field(..., min_length=1, description="Turn content")
    context: Optional[str] = Field(default=None, description="Additional context")

    @validator('role')
    def validate_role(cls, v):
        """Ensure role is valid."""
        if v not in ["user", "assistant"]:
            raise ValueError(f"Invalid role: {v}. Must be 'user' or 'assistant'")
        return v


class TierTransitionInput(BaseModel):
    """Input validation for acms_tier_transition tool."""
    memory_id: str = Field(..., description="Memory UUID")
    new_tier: str = Field(..., description="Target tier")

    @validator('new_tier')
    def validate_tier(cls, v):
        """Ensure tier is valid."""
        if v not in ["SHORT", "MID", "LONG"]:
            raise ValueError(f"Invalid tier: {v}. Must be SHORT, MID, or LONG")
        return v


class SemanticSearchInput(BaseModel):
    """Input validation for acms_semantic_search tool."""
    query: str = Field(..., min_length=1, max_length=1000, description="Semantic search query")
    filters: Optional[dict] = Field(default=None, description="Additional filters")
    limit: int = Field(default=10, ge=1, le=100, description="Max results")
