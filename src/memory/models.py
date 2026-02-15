"""Memory type models - Phase 1: Typed Memory System.

Blueprint Section 3.1: Explicit memory classification.

Memory Types:
- EPISODIC: Conversation turns, queries, events (links to conversation)
- SEMANTIC: Stable facts, user preferences (standalone knowledge)
- DOCUMENT: External docs, long content (imported material)
- CACHE_ENTRY: Semantic cached Q&A (enriched responses)

Each type maps to a specific Weaviate collection (Dec 2025 - Updated):
- EPISODIC → ACMS_Raw_v1 (unified Q&A collection, 101K records)
- SEMANTIC → ACMS_Knowledge_v2 (structured knowledge with intent, entities, facts)
- CACHE_ENTRY → ACMS_Raw_v1 (cache layer removed, uses raw collection)
- DOCUMENT → ACMS_Raw_v1 (unified into raw collection)

NOTE: Dec 2025 cleanup removed old collections:
- ACMS_Knowledge_v1 → replaced by ACMS_Knowledge_v2
- ACMS_Enriched_v1 → merged into ACMS_Raw_v1
- ACMS_MemoryItems_v1 → merged into ACMS_Raw_v1
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict
from uuid import UUID, uuid4
from datetime import datetime, timezone


class MemoryType(str, Enum):
    """Explicit memory type classification (Dec 2025 - Updated).

    EPISODIC: Conversation turns, Q&A pairs, temporal events
        - Requires conversation_id
        - Short retention (30 days default)
        - Stored in ACMS_Raw_v1

    SEMANTIC: Stable facts, user preferences, knowledge
        - Standalone (no conversation link required)
        - Long retention (permanent if quality > 0.8)
        - Stored in ACMS_Knowledge_v2 (structured knowledge)

    DOCUMENT: External documents, imported content
        - Large content support
        - Variable retention
        - Stored in ACMS_Raw_v1 (unified)

    CACHE_ENTRY: Enriched Q&A for semantic cache
        - Links to original raw entry
        - High quality threshold
        - Stored in ACMS_Raw_v1 (cache layer merged)
    """
    EPISODIC = "EPISODIC"
    SEMANTIC = "SEMANTIC"
    DOCUMENT = "DOCUMENT"
    CACHE_ENTRY = "CACHE_ENTRY"


class MemoryTier(str, Enum):
    """Memory retention tier.

    SHORT: 30 days - ephemeral conversations, cache entries
    MID: 90 days - important but not permanent
    LONG: Permanent - validated knowledge, user facts
    """
    SHORT = "SHORT"
    MID = "MID"
    LONG = "LONG"


class PrivacyLevel(str, Enum):
    """Privacy classification for memory access control.

    PUBLIC: Can be shared across users/contexts
    INTERNAL: User-specific but can be sent to AI providers
    CONFIDENTIAL: User-specific, limited AI provider access
    LOCAL_ONLY: Never sent to external APIs
    """
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    LOCAL_ONLY = "LOCAL_ONLY"


class MemoryItem(BaseModel):
    """Typed memory item model.

    Core model for all memory storage operations.
    Enforces type-specific validation rules.

    Example:
        # SEMANTIC memory (user fact)
        memory = MemoryItem(
            user_id=uuid4(),
            content="User prefers Python 3.11+",
            memory_type=MemoryType.SEMANTIC,
            tier=MemoryTier.LONG
        )

        # EPISODIC memory (conversation turn)
        memory = MemoryItem(
            user_id=uuid4(),
            content="User asked about deployment",
            memory_type=MemoryType.EPISODIC,
            conversation_id=uuid4()  # Required for EPISODIC!
        )
    """
    # Identity
    memory_id: UUID = Field(default_factory=uuid4, description="Unique memory identifier")
    user_id: UUID = Field(..., description="Owner user ID")

    # Content
    content: str = Field(..., min_length=1, description="Memory content text")
    content_hash: Optional[str] = Field(default=None, description="SHA256 hash for deduplication")

    # Classification
    memory_type: MemoryType = Field(..., description="Memory type classification")
    tier: MemoryTier = Field(default=MemoryTier.SHORT, description="Retention tier")
    privacy_level: PrivacyLevel = Field(default=PrivacyLevel.INTERNAL, description="Privacy classification")

    # Relationships
    conversation_id: Optional[UUID] = Field(default=None, description="Linked conversation (required for EPISODIC)")
    source_memory_id: Optional[UUID] = Field(default=None, description="Parent memory (for CACHE_ENTRY)")

    # Metadata
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Quality/confidence score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Last update timestamp")

    # Vector storage reference
    embedding_vector_id: Optional[str] = Field(default=None, description="Weaviate vector UUID")

    @model_validator(mode='after')
    def validate_type_requirements(self) -> 'MemoryItem':
        """Validate type-specific requirements.

        Rules:
        - EPISODIC requires conversation_id
        - CACHE_ENTRY should have source_memory_id (warning if not)
        """
        if self.memory_type == MemoryType.EPISODIC and self.conversation_id is None:
            raise ValueError("EPISODIC memories require conversation_id")

        return self

    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_range(cls, v: float) -> float:
        """Ensure confidence is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence_score must be between 0 and 1, got {v}")
        return v

    def get_collection_name(self) -> str:
        """Get the Weaviate collection name for this memory type (Dec 2025 - Updated)."""
        mapping = {
            MemoryType.EPISODIC: "ACMS_Raw_v1",
            MemoryType.SEMANTIC: "ACMS_Knowledge_v2",
            MemoryType.CACHE_ENTRY: "ACMS_Raw_v1",  # Cache merged into raw
            MemoryType.DOCUMENT: "ACMS_Raw_v1"      # Documents merged into raw
        }
        return mapping[self.memory_type]

    def to_weaviate_data(self) -> Dict[str, Any]:
        """Convert to Weaviate-compatible data format."""
        return {
            "memory_id": str(self.memory_id),
            "user_id": str(self.user_id),
            "content": self.content,
            "memory_type": self.memory_type.value,
            "tier": self.tier.value,
            "privacy_level": self.privacy_level.value,
            "tags": self.tags,
            "confidence_score": self.confidence_score,
            "conversation_id": str(self.conversation_id) if self.conversation_id else None,
            "created_at": self.created_at.isoformat() + "Z",
        }

    model_config = ConfigDict(
        use_enum_values=False,  # Keep enums as enum types
    )


class CandidateMemory(BaseModel):
    """Candidate memory for quality validation before storage.

    Used by QualityValidator to assess if content should be stored.

    Example:
        candidate = CandidateMemory(
            text="User prefers dark mode",
            memory_type=MemoryType.SEMANTIC,
            source="extracted"
        )

        if quality_validator.should_store(candidate):
            # Convert to MemoryItem and store
            pass
    """
    text: str = Field(..., min_length=1, description="Candidate content")
    memory_type: MemoryType = Field(..., description="Proposed memory type")
    source: str = Field(..., description="Source: 'user', 'ai', 'extracted', 'imported'")
    context: Dict[str, Any] = Field(default_factory=dict, description="Extraction context")

    def to_memory_item(self, user_id: UUID, **kwargs) -> MemoryItem:
        """Convert validated candidate to MemoryItem.

        Args:
            user_id: User who owns this memory
            **kwargs: Additional MemoryItem fields

        Returns:
            MemoryItem ready for storage
        """
        return MemoryItem(
            user_id=user_id,
            content=self.text,
            memory_type=self.memory_type,
            metadata={"source": self.source, **self.context},
            **kwargs
        )
