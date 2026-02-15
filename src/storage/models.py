"""Database models for ACMS storage layer.

SQLAlchemy models for PostgreSQL tables:
- Users: User accounts and profiles
- MemoryItems: Core memory storage with encryption
- QueryLogs: Query history and analytics
- Outcomes: Feedback and outcome tracking
- AuditLogs: Audit trail for all operations

All models use UUIDs for primary keys and include timestamps.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime,
    Text, JSON, ForeignKey, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """User accounts and profiles."""

    __tablename__ = "users"

    # Primary key
    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # User information
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    display_name = Column(String(255), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Metadata
    metadata_json = Column(JSON, default={}, nullable=False)

    # Relationships
    memories = relationship("MemoryItem", back_populates="user", cascade="all, delete-orphan")
    query_logs = relationship("QueryLog", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(user_id={self.user_id}, username={self.username})>"


class MemoryItem(Base):
    """Core memory storage with encryption and vector embeddings."""

    __tablename__ = "memory_items"

    # Primary key
    memory_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Content (encrypted in database, decrypted in application)
    content = Column(Text, nullable=False)  # Plaintext for indexing/search
    content_hash = Column(String(64), nullable=False, index=True)  # SHA256 hash for deduplication
    encrypted_content = Column(Text, nullable=True)  # Encrypted version for sensitive data

    # Vector embedding reference (stored in Weaviate)
    embedding_vector_id = Column(String(255), nullable=True, index=True)

    # Memory classification
    tier = Column(String(20), nullable=False, default="SHORT", index=True)  # SHORT, MID, LONG
    phase = Column(String(100), nullable=True, index=True)  # Build phase or context
    tags = Column(ARRAY(String), default=[], nullable=False)  # Categorical tags
    privacy_level = Column(String(20), nullable=False, default="INTERNAL", index=True)  # PUBLIC, INTERNAL, CONFIDENTIAL, LOCAL_ONLY

    # CRS scoring
    crs_score = Column(Float, default=0.0, nullable=False, index=True)
    semantic_score = Column(Float, default=0.0, nullable=False)
    recency_score = Column(Float, default=0.0, nullable=False)
    outcome_score = Column(Float, default=0.0, nullable=False)
    frequency_score = Column(Float, default=0.0, nullable=False)
    correction_score = Column(Float, default=0.0, nullable=False)

    # Access tracking
    access_count = Column(Integer, default=0, nullable=False)
    last_accessed = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Metadata
    checkpoint = Column(Integer, nullable=True)  # Associated checkpoint
    metadata_json = Column(JSON, default={}, nullable=False)

    # Feedback summary (denormalized for fast access)
    feedback_summary = Column(JSON, default={}, nullable=False)  # {total_ratings, avg_rating, thumbs_up, thumbs_down, regenerates}

    # Quality tracking (Week 5: Pollution Prevention)
    confidence_score = Column(Float, default=1.0, nullable=True)  # Quality confidence (0.0-1.0), threshold 0.8
    flagged = Column(Boolean, default=False, nullable=False)  # Flagged for review (pollution, speculation)
    flagged_reason = Column(Text, nullable=True)  # Reason for flagging

    # Relationships
    user = relationship("User", back_populates="memories")
    outcomes = relationship("Outcome", back_populates="memory", cascade="all, delete-orphan")
    feedbacks = relationship("QueryFeedback", back_populates="query", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_memory_user_tier", "user_id", "tier"),
        Index("idx_memory_user_phase", "user_id", "phase"),
        Index("idx_memory_user_privacy", "user_id", "privacy_level"),
        Index("idx_memory_crs_score", "crs_score"),
        Index("idx_memory_created", "created_at"),
        UniqueConstraint("user_id", "content_hash", name="uq_user_content_hash"),
    )

    def __repr__(self):
        return f"<MemoryItem(memory_id={self.memory_id}, tier={self.tier}, privacy={self.privacy_level}, crs={self.crs_score:.2f})>"


class QueryLog(Base):
    """Query history and analytics."""

    __tablename__ = "query_logs"

    # Primary key
    log_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Query details
    query = Column(Text, nullable=False)
    query_hash = Column(String(64), nullable=False)  # SHA256 for deduplication
    query_embedding_id = Column(String(255), nullable=True)  # Weaviate vector ID

    # Results
    retrieved_memory_ids = Column(ARRAY(UUID(as_uuid=True)), default=[], nullable=False)
    result_count = Column(Integer, default=0, nullable=False)

    # Performance metrics
    latency_ms = Column(Float, nullable=False)
    embedding_latency_ms = Column(Float, nullable=True)
    search_latency_ms = Column(Float, nullable=True)
    crs_latency_ms = Column(Float, nullable=True)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Metadata
    metadata_json = Column(JSON, default={}, nullable=False)

    # Relationships
    user = relationship("User", back_populates="query_logs")
    outcomes = relationship("Outcome", back_populates="query_log", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_query_user_timestamp", "user_id", "timestamp"),
        Index("idx_query_latency", "latency_ms"),
    )

    def __repr__(self):
        return f"<QueryLog(log_id={self.log_id}, latency={self.latency_ms:.1f}ms)>"


class Outcome(Base):
    """Feedback and outcome tracking for memories and queries."""

    __tablename__ = "outcomes"

    # Primary key
    outcome_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign keys
    memory_id = Column(UUID(as_uuid=True), ForeignKey("memory_items.memory_id", ondelete="CASCADE"), nullable=True, index=True)
    query_id = Column(UUID(as_uuid=True), ForeignKey("query_logs.log_id", ondelete="CASCADE"), nullable=True, index=True)

    # Outcome details
    outcome_type = Column(String(50), nullable=False, index=True)  # success, failure, correction, improvement
    feedback_score = Column(Float, nullable=True)  # -1.0 to 1.0
    description = Column(Text, nullable=True)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Metadata
    metadata_json = Column(JSON, default={}, nullable=False)

    # Relationships
    memory = relationship("MemoryItem", back_populates="outcomes")
    query_log = relationship("QueryLog", back_populates="outcomes")

    # Indexes
    __table_args__ = (
        Index("idx_outcome_memory", "memory_id", "timestamp"),
        Index("idx_outcome_query", "query_id", "timestamp"),
        Index("idx_outcome_type", "outcome_type"),
    )

    def __repr__(self):
        return f"<Outcome(outcome_id={self.outcome_id}, type={self.outcome_type})>"


class QueryFeedback(Base):
    """User feedback on query responses (Week 4 Task 2)."""

    __tablename__ = "query_feedback"

    # Primary key
    feedback_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign keys
    query_id = Column(UUID(as_uuid=True), ForeignKey("memory_items.memory_id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Feedback data
    rating = Column(Integer, nullable=False)  # 1-5 stars
    feedback_type = Column(String(20), nullable=False, index=True)  # thumbs_up, thumbs_down, regenerate
    response_source = Column(String(50), nullable=False)  # cache, semantic_cache, claude, chatgpt, gemini
    comment = Column(Text, nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    query = relationship("MemoryItem", back_populates="feedbacks")
    user = relationship("User", foreign_keys=[user_id])

    # Constraints and indexes
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='ck_rating_range'),
        CheckConstraint(
            "feedback_type IN ('thumbs_up', 'thumbs_down', 'regenerate')",
            name='ck_feedback_type'
        ),
        Index("idx_query_feedback", "query_id"),
        Index("idx_user_feedback", "user_id", "created_at"),
        Index("idx_feedback_type", "feedback_type", "created_at"),
    )

    def __repr__(self):
        return f"<QueryFeedback(feedback_id={self.feedback_id}, type={self.feedback_type}, rating={self.rating})>"


class AuditLog(Base):
    """Audit trail for all operations."""

    __tablename__ = "audit_logs"

    # Primary key
    audit_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Foreign key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True, index=True)

    # Action details
    action = Column(String(100), nullable=False, index=True)  # create_memory, update_memory, delete_memory, etc.
    resource_type = Column(String(50), nullable=False, index=True)  # memory, user, query, etc.
    resource_id = Column(String(255), nullable=True, index=True)  # UUID of affected resource

    # Context
    ip_address = Column(String(45), nullable=True)  # IPv6 max length
    user_agent = Column(String(500), nullable=True)
    request_id = Column(String(255), nullable=True)

    # Result
    status = Column(String(20), nullable=False)  # success, failure, partial
    error_message = Column(Text, nullable=True)

    # Timestamp
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Metadata
    metadata_json = Column(JSON, default={}, nullable=False)

    # Relationships
    user = relationship("User", back_populates="audit_logs")

    # Indexes
    __table_args__ = (
        Index("idx_audit_user_timestamp", "user_id", "timestamp"),
        Index("idx_audit_action", "action", "timestamp"),
        Index("idx_audit_resource", "resource_type", "resource_id"),
    )

    def __repr__(self):
        return f"<AuditLog(audit_id={self.audit_id}, action={self.action}, status={self.status})>"


class Conversation(Base):
    """Unified chat conversations for Phase 1 interface."""

    __tablename__ = "conversations"

    # Primary key
    conversation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Multi-tenancy
    tenant_id = Column(String(100), nullable=False, default="default", index=True)

    # Foreign key
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    # Conversation metadata
    title = Column(String(200), nullable=True)  # Auto-generated from first message or user-set
    agent = Column(String(50), nullable=False, index=True)  # claude, gpt, gemini, claude-code

    # Conversation state for continuity (summary, entities, topic_stack, last_intent)
    state_json = Column(JSON, default={}, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ConversationMessage.created_at")

    # Indexes for performance
    __table_args__ = (
        Index("idx_conversation_user_created", "user_id", "created_at"),
        Index("idx_conversation_agent", "agent", "created_at"),
        Index("idx_conversation_tenant_user", "tenant_id", "user_id", "updated_at"),
    )

    def __repr__(self):
        return f"<Conversation(conversation_id={self.conversation_id}, agent={self.agent}, title={self.title})>"


class ConversationMessage(Base):
    """Messages within a conversation (user and assistant)."""

    __tablename__ = "conversation_messages"

    # Primary key
    message_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Multi-tenancy (denormalized for query efficiency)
    tenant_id = Column(String(100), nullable=False, default="default", index=True)

    # Foreign key
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False, index=True)

    # Idempotency key (client-generated)
    client_message_id = Column(String(100), nullable=True)

    # Message content
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Token count for context budget management
    token_count = Column(Integer, nullable=True)

    # Message metadata (costs, tokens, model, compliance results, etc.)
    # Note: Can't use 'metadata' as it's reserved by SQLAlchemy Base class
    message_metadata = Column(JSON, default={}, nullable=False)

    # Timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    # Indexes for performance
    __table_args__ = (
        Index("idx_message_conversation_created", "conversation_id", "created_at"),
        Index("idx_message_role", "role"),
        Index("idx_message_tenant_conv", "tenant_id", "conversation_id", "created_at"),
    )

    def __repr__(self):
        return f"<ConversationMessage(message_id={self.message_id}, role={self.role}, conversation_id={self.conversation_id})>"
