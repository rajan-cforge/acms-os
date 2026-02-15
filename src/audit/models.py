"""
Audit System Models

Pydantic models for audit events, summaries, and reports.
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class AuditEventType(str, Enum):
    """Types of audit events"""
    INGRESS = "ingress"      # Data entering the system
    TRANSFORM = "transform"  # Data being processed/transformed
    EGRESS = "egress"        # Data leaving the system
    VALIDATION = "validation"  # Privacy/security validation


class DataClassification(str, Enum):
    """Data sensitivity classification"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    LOCAL_ONLY = "local_only"


class AuditEventCreate(BaseModel):
    """Model for creating a new audit event"""
    event_type: AuditEventType
    source: str  # gmail, plaid, calendar, file, browser, llm, chat, memory
    operation: str  # fetch_emails, summarize, embed, send_to_api, etc.

    # Data info (optional)
    data_classification: Optional[DataClassification] = None
    data_hash: Optional[str] = None  # SHA-256
    data_size_bytes: Optional[int] = None
    item_count: int = 1

    # Flow tracking
    destination: Optional[str] = None  # local, weaviate, postgres, claude_api, etc.
    correlation_id: Optional[UUID] = None
    parent_event_id: Optional[UUID] = None

    # Context
    user_id: str = "default"
    session_id: Optional[UUID] = None
    request_id: Optional[str] = None

    # Details
    metadata: Dict[str, Any] = Field(default_factory=dict)
    duration_ms: Optional[int] = None
    success: bool = True
    error_message: Optional[str] = None


class AuditEvent(AuditEventCreate):
    """Full audit event with ID and timestamp"""
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True


class AuditDailySummary(BaseModel):
    """Daily summary of audit events"""
    date: date

    # Ingress counts
    gmail_emails_fetched: int = 0
    gmail_emails_read: int = 0
    calendar_events_synced: int = 0
    plaid_transactions_fetched: int = 0
    plaid_accounts_synced: int = 0
    files_uploaded: int = 0
    files_bytes_uploaded: int = 0
    browser_captures: int = 0
    chat_messages_received: int = 0

    # Transform counts
    summaries_generated: int = 0
    embeddings_created: int = 0
    learning_signals_captured: int = 0
    knowledge_facts_extracted: int = 0
    memories_created: int = 0

    # Egress counts
    llm_calls_claude: int = 0
    llm_calls_openai: int = 0
    llm_calls_gemini: int = 0
    llm_tokens_input: int = 0
    llm_tokens_output: int = 0
    llm_cost_usd: Decimal = Decimal("0.0000")
    browser_automations: int = 0
    external_api_calls: int = 0

    # Storage changes
    postgres_bytes_added: int = 0
    weaviate_vectors_added: int = 0
    files_bytes_added: int = 0

    # Privacy tracking
    confidential_items_processed: int = 0
    confidential_items_kept_local: int = 0
    confidential_items_external: int = 0  # Should always be 0!

    # Error tracking
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0

    # Timing
    total_duration_ms: int = 0
    avg_operation_ms: Decimal = Decimal("0.00")

    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

    @property
    def privacy_status(self) -> str:
        """Return privacy status: SECURE or VIOLATION"""
        return "SECURE" if self.confidential_items_external == 0 else "VIOLATION"

    @property
    def success_rate(self) -> float:
        """Calculate operation success rate"""
        if self.total_operations == 0:
            return 100.0
        return (self.successful_operations / self.total_operations) * 100


class IntegrationStatus(BaseModel):
    """Status of an external integration"""
    id: str  # gmail, calendar, plaid, browser_chatgpt, etc.

    # Connection status
    is_connected: bool = False
    connected_at: Optional[datetime] = None
    last_sync_at: Optional[datetime] = None
    next_sync_at: Optional[datetime] = None

    # OAuth info (no actual tokens, just metadata)
    oauth_expires_at: Optional[datetime] = None
    oauth_scopes: List[str] = Field(default_factory=list)

    # Sync state
    items_synced: int = 0

    # Health
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    last_error_at: Optional[datetime] = None

    # Account info
    account_email: Optional[str] = None
    account_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        from_attributes = True

    @property
    def health_status(self) -> str:
        """Return health status: healthy, degraded, or failed"""
        if not self.is_connected:
            return "disconnected"
        if self.consecutive_failures >= 5:
            return "failed"
        if self.consecutive_failures >= 2:
            return "degraded"
        return "healthy"


class PrivacyViolation(BaseModel):
    """Record of a privacy violation attempt"""
    id: UUID = Field(default_factory=uuid4)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    data_classification: DataClassification
    attempted_destination: str
    operation: str

    user_id: Optional[str] = None
    correlation_id: Optional[UUID] = None

    blocked: bool = True  # Should always be True
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class EndOfDayReport(BaseModel):
    """End of Day comprehensive report"""
    date: date
    generated_at: datetime = Field(default_factory=datetime.utcnow)

    # Summary
    summary: AuditDailySummary

    # Integrations status
    integrations: List[IntegrationStatus] = Field(default_factory=list)

    # Privacy
    privacy_status: str  # SECURE or VIOLATION
    privacy_violations: List[PrivacyViolation] = Field(default_factory=list)

    # Top activity
    top_sources: List[Dict[str, Any]] = Field(default_factory=list)
    top_operations: List[Dict[str, Any]] = Field(default_factory=list)

    # Errors
    errors_today: int = 0
    error_summary: List[Dict[str, Any]] = Field(default_factory=list)

    # Storage
    storage_summary: Dict[str, Any] = Field(default_factory=dict)

    def to_text(self) -> str:
        """Generate text report for display"""
        s = self.summary
        lines = [
            "=" * 60,
            f"           ACMS DATA FLOW REPORT",
            f"           {self.date.strftime('%B %d, %Y')}",
            "=" * 60,
            "",
            "DATA INGRESS",
            f"  Gmail: {s.gmail_emails_fetched} emails fetched",
            f"  Calendar: {s.calendar_events_synced} events synced",
            f"  Plaid: {s.plaid_transactions_fetched} transactions fetched",
            f"  Files: {s.files_uploaded} files uploaded",
            f"  Chat: {s.chat_messages_received} messages received",
            "",
            "TRANSFORMATIONS",
            f"  Summaries generated: {s.summaries_generated}",
            f"  Embeddings created: {s.embeddings_created}",
            f"  Learning signals: {s.learning_signals_captured}",
            f"  Knowledge extracted: {s.knowledge_facts_extracted}",
            f"  Memories created: {s.memories_created}",
            "",
            "DATA EGRESS",
            f"  LLM API calls: {s.llm_calls_claude + s.llm_calls_openai + s.llm_calls_gemini}",
            f"    Claude: {s.llm_calls_claude} calls",
            f"    OpenAI: {s.llm_calls_openai} calls",
            f"    Gemini: {s.llm_calls_gemini} calls",
            f"  Total tokens: {s.llm_tokens_input + s.llm_tokens_output:,}",
            f"  Estimated cost: ${s.llm_cost_usd:.4f}",
            f"  Browser automations: {s.browser_automations}",
            "",
            "PRIVACY STATUS",
            f"  Status: {self.privacy_status}",
            f"  Confidential items processed: {s.confidential_items_processed}",
            f"  Kept local: {s.confidential_items_kept_local}",
            f"  Sent external: {s.confidential_items_external}",
            "",
            "OPERATIONS",
            f"  Total: {s.total_operations}",
            f"  Successful: {s.successful_operations} ({s.success_rate:.1f}%)",
            f"  Failed: {s.failed_operations}",
            f"  Avg duration: {s.avg_operation_ms:.1f}ms",
            "",
            "=" * 60,
        ]
        return "\n".join(lines)


class AuditEventFilter(BaseModel):
    """Filter for querying audit events"""
    event_type: Optional[AuditEventType] = None
    source: Optional[str] = None
    destination: Optional[str] = None
    data_classification: Optional[DataClassification] = None
    success: Optional[bool] = None
    correlation_id: Optional[UUID] = None
    user_id: Optional[str] = None

    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    limit: int = 100
    offset: int = 0


class AuditEventList(BaseModel):
    """Paginated list of audit events"""
    events: List[AuditEvent]
    total_count: int
    limit: int
    offset: int
    has_more: bool
