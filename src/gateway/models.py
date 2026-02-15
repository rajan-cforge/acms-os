"""Gateway data models for AI Gateway Foundation.

Defines request/response models, intent types, agent types, and pipeline stages.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum
from uuid import UUID


class IntentType(str, Enum):
    """Query intent categories"""
    TERMINAL_COMMAND = "terminal_command"
    CODE_GENERATION = "code_generation"
    FILE_OPERATION = "file_operation"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    RESEARCH = "research"
    MEMORY_QUERY = "memory_query"
    EMAIL = "email"  # Email queries: inbox, insights, senders, actions
    FINANCE = "finance"  # Financial queries: portfolio, transactions, holdings


class AgentType(str, Enum):
    """Available AI agents"""
    CLAUDE_CODE = "claude_code"
    CLAUDE_SONNET = "claude_sonnet"
    CHATGPT = "chatgpt"
    GEMINI = "gemini"
    OLLAMA = "ollama"  # Local LLM via Ollama


class ThreadContext(BaseModel):
    """Thread context for conversation continuity."""
    conversation_id: str
    tenant_id: str
    summary: str = ""  # Rolling conversation summary
    entities: Dict[str, Any] = Field(default_factory=dict)  # Entity disambiguation state
    topic_stack: List[str] = Field(default_factory=list)  # Current topics
    recent_turns: List[Dict[str, Any]] = Field(default_factory=list)  # Last N turns
    turn_count: int = 0


class FileContextModel(BaseModel):
    """File context for ChatGPT-style file handling (Sprint 3 Day 15).

    When a user uploads a file, its content is included in the query context
    so the AI can analyze, summarize, or answer questions about the file.
    """
    filename: str = Field(..., description="Original filename")
    content: str = Field(..., description="Extracted text content from the file")


class GatewayRequest(BaseModel):
    """Request to Gateway"""
    query: str = Field(..., min_length=1, max_length=50000)
    user_id: str
    tenant_id: str = "default"  # Multi-tenancy support
    manual_agent: Optional[AgentType] = None
    bypass_cache: bool = False
    context_limit: int = Field(default=10, ge=1, le=20)  # Increased from 5 to 10 for better context
    conversation_id: Optional[str] = None  # For message persistence tracking
    thread_context: Optional[ThreadContext] = None  # For conversation continuity
    # Sprint 3 Day 15: ChatGPT-style file context
    file_context: Optional[FileContextModel] = None  # Uploaded file content
    # Dec 2025: Cross-source search toggle for Unified Intelligence
    cross_source_enabled: bool = True  # Enable cross-source insights by default

    @validator('query')
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError('Query cannot be empty')
        return v.strip()


class GatewayStage(str, Enum):
    """Pipeline stages for status updates"""
    PREFLIGHT_GATE = "preflight_gate"  # NEW: Security check BEFORE any external calls
    INTENT_DETECTION = "intent_detection"
    CACHE_CHECK = "cache_check"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    AGENT_SELECTION = "agent_selection"
    WEB_SEARCH = "web_search"  # Added for observability
    QUERY_AUGMENTATION = "query_augmentation"  # Added for observability
    CONTEXT_ASSEMBLY = "context_assembly"
    COMPLIANCE_CHECK = "compliance_check"
    EXECUTING = "executing"
    COMPLETE = "complete"
    ERROR = "error"


class ComplianceIssue(BaseModel):
    """Compliance violation"""
    severity: Literal["low", "medium", "high"]
    type: str
    message: str


class ComplianceResult(BaseModel):
    """Compliance check result"""
    approved: bool
    issues: List[ComplianceIssue] = Field(default_factory=list)


class GatewayResponse(BaseModel):
    """Final response from gateway"""
    query_id: Optional[UUID] = None  # NEW: For feedback support
    query: str
    answer: str
    agent_used: AgentType
    from_cache: bool
    intent_detected: IntentType
    cost_usd: float
    latency_ms: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
