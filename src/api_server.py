"""
ACMS FastAPI Server for Desktop App

Provides REST API endpoints for the desktop application to interact with ACMS.
Endpoints: health, memories (CRUD), search, stats.
"""

import sys
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import uuid4
from enum import Enum
import logging

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel, Field
import json
import time

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("acms.api")

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.memory_crud import MemoryCRUD
from src.storage.conversation_crud import ConversationCRUD
from src.storage.database import get_db_pool
from src.storage.models import User
from src.generation.claude_generator import ClaudeGenerator
from src.auth.simple_auth import SimpleAuth, TokenPair, UserContext, AuthError, get_auth_service
from src.auth.middleware import get_current_user, require_auth, require_admin, optional_auth
from src.cache.query_cache import QueryCache
from src.cache.semantic_cache import get_semantic_cache
from src.gateway.orchestrator import get_gateway_orchestrator
from src.gateway.models import GatewayRequest, AgentType, ThreadContext
from src.gateway.conversation_memory import get_conversation_memory_manager
from src.privacy.pii_detector import PIIScanner
from src.intelligence.pattern_detector import PatternDetector
from src.intelligence.insight_generator import InsightGenerator
from src.services.quality_validator import QualityValidator  # Week 5 Task 1: Pollution Prevention
from src.jobs.scheduler import start_scheduler, shutdown_scheduler, get_job_status
from src.audit.endpoints import router as audit_router
from src.api.gmail_endpoints import router as gmail_router
from src.api.plaid_endpoints import router as plaid_router
from src.api.active_brain_endpoints import router as active_brain_router  # Active Second Brain (Jan 2026)
from src.api.clusters_endpoints import router as clusters_router  # Sprint 2: Memory Clustering
from src.api.knowledge_v2_endpoints import router as knowledge_v2_router  # Sprint 3: Knowledge Consolidation
from src.api.constitution_endpoints import router as constitution_router  # Sprint 4: Financial Constitution
from src.api.reports_endpoints import router as reports_router  # Sprint 5: Reports & Insights
from src.api.cognitive_endpoints import router as cognitive_router  # Cognitive Architecture (Feb 2026)
from src.audit.logger import init_audit_logger, get_audit_logger
from sqlalchemy import select

# Initialize FastAPI app
app = FastAPI(
    title="ACMS API",
    description="Adaptive Context Memory System REST API",
    version="1.0.0"
)

# CORS middleware - Environment-based configuration
# SECURITY: Restrict CORS to specific origins to prevent unauthorized access
environment = os.getenv("ENVIRONMENT", "development")

if environment == "production":
    # PRODUCTION: Only allow Electron app (null origin from file://)
    # DO NOT add web origins unless explicitly needed
    allowed_origins = ["null"]  # Electron file:// protocol
    logger.info("[CORS] Production mode - Strict origins: ['null' (Electron)]")
else:
    # DEVELOPMENT: Allow localhost for testing
    # Still blocks external domains like evil.com
    allowed_origins = [
        "null",                       # Electron file:// protocol
        "http://localhost:8080",      # Desktop app API server
        "http://localhost:3000",      # React/Next.js dev server
        "http://127.0.0.1:8080",      # Alternative localhost
        "http://127.0.0.1:3000",      # Alternative localhost
    ]
    logger.info(f"[CORS] Development mode - Allowed origins: {allowed_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,  # Specific origins only - NO wildcard!
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # Explicit methods
    allow_headers=["Content-Type", "Authorization"],  # Explicit headers
)

# Include audit router (Phase 0: Data Flow Audit)
app.include_router(audit_router)

# Include Gmail router (Phase 1: Gmail Integration)
app.include_router(gmail_router)

# Include Plaid router (Phase 2: Financial Constitution)
app.include_router(plaid_router)

# Include Active Second Brain router (Jan 2026)
app.include_router(active_brain_router)

# Include Memory Clusters router (Sprint 2: Memory Clustering)
app.include_router(clusters_router)

# Sprint 3: Knowledge Consolidation
app.include_router(knowledge_v2_router)

# Sprint 4: Financial Constitution
app.include_router(constitution_router)

# Sprint 5: Reports & Insights
app.include_router(reports_router)

# Cognitive Architecture (Feb 2026)
app.include_router(cognitive_router)

# Initialize MemoryCRUD, Claude generator, Query Cache, Semantic Cache, and Gateway Orchestrator
crud = MemoryCRUD()
claude = ClaudeGenerator()
query_cache = QueryCache()
semantic_cache = get_semantic_cache()
gateway = get_gateway_orchestrator()

# Initialize Quality Validator (Week 5 Task 1: Pollution Prevention)
quality_validator = QualityValidator()

# Initialize Auto-Tuner (self-improving AI)
from src.auto_tuner import get_auto_tuner
auto_tuner = get_auto_tuner()

# Default user ID (for now, single-user system)
DEFAULT_USER_ID = None


# Background task: Auto-tuning
import asyncio

async def auto_tuning_loop():
    """
    Background task that runs auto-tuning every hour.

    Analyzes user feedback to automatically optimize:
    - Semantic cache (disable if ratings < 3.0)
    - Model routing (switch to best-performing model)
    - Context limits (adjust based on feedback)
    """
    await asyncio.sleep(10)  # Wait 10 seconds on startup

    logger.info("[AutoTuner] Background task started (runs every hour)")

    while True:
        try:
            # Analyze feedback
            decision = await auto_tuner.analyze_feedback()

            if decision:
                # Apply tuning decision
                await auto_tuner.apply_tuning(decision)
                logger.info(f"[AutoTuner] ✅ Applied: {decision.action} - {decision.reason}")
            else:
                logger.debug("[AutoTuner] No tuning actions needed")

        except Exception as e:
            logger.error(f"[AutoTuner] Error in tuning loop: {e}")

        # Run every hour
        await asyncio.sleep(3600)


# Start background task on startup
@app.on_event("startup")
async def startup_event():
    """Start background tasks on server startup"""
    logger.info("[API] Starting ACMS API server...")

    # Initialize auto-tuner
    await auto_tuner.initialize()

    # Start auto-tuning background task
    asyncio.create_task(auto_tuning_loop())

    # Start job scheduler (per Arch-review: integrate into API lifecycle)
    # Jobs: decay (daily 3AM), dedup (Sun 4AM), cleanup (Sun 5AM)
    scheduler_enabled = os.getenv("ACMS_JOBS_ENABLED", "true").lower() == "true"
    if scheduler_enabled:
        scheduler = start_scheduler()
        if scheduler:
            logger.info("[API] ✅ Job scheduler started")
            status = get_job_status()
            for job in status.get("jobs", []):
                logger.info(f"[Scheduler] Job registered: {job['name']} -> next: {job['next_run']}")
        else:
            logger.warning("[API] ⚠️ Job scheduler not available (APScheduler not installed)")
    else:
        logger.info("[API] Job scheduler disabled via ACMS_JOBS_ENABLED=false")

    # Initialize Audit Logger (Phase 0: Data Flow Audit)
    try:
        db_pool = await get_db_pool()
        await init_audit_logger(db_pool)
        logger.info("[API] ✅ Audit logger initialized")

        # Store db_pool in app.state for Gmail integration (Phase 1)
        app.state.db_pool = db_pool
        logger.info("[API] ✅ Database pool stored in app.state")
    except Exception as e:
        logger.warning(f"[API] ⚠️ Audit logger not initialized: {e}")
        app.state.db_pool = None

    logger.info("[API] ✅ Background tasks started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on server shutdown"""
    logger.info("[API] Shutting down ACMS API server...")

    # Stop job scheduler gracefully
    shutdown_scheduler()
    logger.info("[API] ✅ Job scheduler stopped")

    logger.info("[API] Shutdown complete")


async def get_or_create_default_user():
    """Get or create the default user - use the MCP user with most memories."""
    global DEFAULT_USER_ID

    if DEFAULT_USER_ID:
        return DEFAULT_USER_ID

    from src.storage.database import get_session
    from src.storage.models import MemoryItem
    from sqlalchemy import func

    async with get_session() as session:
        # Find user with most memories (should be the main user from MCP)
        stmt = (
            select(User.user_id, func.count(MemoryItem.memory_id).label('count'))
            .outerjoin(MemoryItem, User.user_id == MemoryItem.user_id)
            .group_by(User.user_id)
            .order_by(func.count(MemoryItem.memory_id).desc())
            .limit(1)
        )
        result = await session.execute(stmt)
        user_row = result.first()

        if user_row:
            DEFAULT_USER_ID = str(user_row[0])
            print(f"Using user with {user_row[1]} memories: {DEFAULT_USER_ID}")
        else:
            # No users exist, create default MCP user
            from uuid import UUID
            default_user = User(
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                email="default@acms.local",
                username="default_mcp_user",
            )
            session.add(default_user)
            await session.commit()
            DEFAULT_USER_ID = str(default_user.user_id)
            print(f"Created new default user: {DEFAULT_USER_ID}")

        return DEFAULT_USER_ID


# Helper functions for query_history table
async def store_query_in_history(user_id: str, question: str, context_limit: int) -> str:
    """Store query in query_history table and return query_id.

    This replaces storing queries in memory_items to prevent query pollution.
    """
    from src.storage.database import get_session
    from sqlalchemy import text

    query_id = str(uuid4())

    async with get_session() as session:
        await session.execute(
            text("""
                INSERT INTO query_history (
                    query_id, user_id, question, response_source, context_limit, created_at
                )
                VALUES (:query_id, :user_id, :question, 'pending', :context_limit, NOW())
            """),
            {
                "query_id": query_id,
                "user_id": user_id,
                "question": question,
                "context_limit": context_limit
            }
        )
        await session.commit()

    return query_id


async def update_query_history(
    query_id: str,
    answer: str,
    response_source: str,
    confidence: float,
    analytics
):
    """Update query_history with response and analytics after generation."""
    from src.storage.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        await session.execute(
            text("""
                UPDATE query_history
                SET
                    answer = :answer,
                    response_source = :response_source,
                    confidence = :confidence,
                    memories_searched = :memories_searched,
                    memories_filtered = :memories_filtered,
                    memories_used = :memories_used,
                    total_latency_ms = :total_latency_ms,
                    search_latency_ms = :search_latency_ms,
                    llm_latency_ms = :llm_latency_ms,
                    input_tokens = :input_tokens,
                    output_tokens = :output_tokens,
                    est_cost_usd = :est_cost_usd
                WHERE query_id = :query_id
            """),
            {
                "query_id": query_id,
                "answer": answer,
                "response_source": response_source,
                "confidence": confidence,
                "memories_searched": analytics.memories_searched,
                "memories_filtered": analytics.memories_filtered,
                "memories_used": analytics.memories_used,
                "total_latency_ms": analytics.total_latency_ms,
                "search_latency_ms": analytics.search_latency_ms,
                "llm_latency_ms": analytics.llm_latency_ms,
                "input_tokens": analytics.input_tokens,
                "output_tokens": analytics.output_tokens,
                "est_cost_usd": analytics.est_cost_usd
            }
        )
        await session.commit()


# Pydantic models
class MemoryCreate(BaseModel):
    content: str = Field(..., min_length=1, description="Memory content")
    tags: Optional[List[str]] = Field(default=[], description="Memory tags")
    tier: str = Field(default="SHORT", description="Memory tier (SHORT/MID/LONG)")
    phase: Optional[str] = Field(default=None, description="Phase/context")
    privacy_level: Optional[str] = Field(default=None, description="Privacy level (PUBLIC/INTERNAL/CONFIDENTIAL/LOCAL_ONLY). If None, auto-detected.")
    auto_detect_privacy: bool = Field(default=True, description="Auto-detect privacy level from content/tags")
    metadata: Optional[dict] = Field(default={}, description="Additional metadata")


class MemoryUpdate(BaseModel):
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    tier: Optional[str] = None
    phase: Optional[str] = None
    privacy_level: Optional[str] = None
    crs_score: Optional[float] = None
    metadata: Optional[dict] = None


# ═══════════════════════════════════════════════════════════════════════════════
# V2 API Models - Typed Memories with Quality Gate (Dec 2025)
# ═══════════════════════════════════════════════════════════════════════════════

class MemoryTypeEnum(str, Enum):
    """Memory types for proper categorization (Dec 2025 - Updated)."""
    SEMANTIC = "SEMANTIC"      # Facts, preferences, knowledge (→ ACMS_Knowledge_v2)
    EPISODIC = "EPISODIC"      # Conversations, events (→ ACMS_Raw_v1)
    CACHE_ENTRY = "CACHE_ENTRY"  # Q&A cache (→ ACMS_Raw_v1, cache merged)
    DOCUMENT = "DOCUMENT"      # External docs (→ ACMS_Raw_v1, unified)


class MemoryCreateV2(BaseModel):
    """V2 memory creation with explicit typing and quality gate."""
    content: str = Field(..., min_length=1, description="Memory content")
    memory_type: MemoryTypeEnum = Field(
        default=MemoryTypeEnum.SEMANTIC,
        description="Memory type: SEMANTIC (facts), EPISODIC (events), CACHE_ENTRY (Q&A)"
    )
    tags: Optional[List[str]] = Field(default=[], description="Memory tags")
    privacy_level: str = Field(default="INTERNAL", description="Privacy level")
    source: Optional[str] = Field(default="user_stated", description="Source of memory")
    skip_quality_gate: bool = Field(
        default=False,
        description="Skip quality gate validation (use with caution)"
    )
    metadata: Optional[dict] = Field(default={}, description="Additional metadata")


class MemoryCreateV2Response(BaseModel):
    """V2 memory creation response."""
    memory_id: Optional[str] = None
    status: str  # "created", "rejected", "warning"
    message: str
    quality_score: Optional[float] = None
    suggested_type: Optional[str] = None
    stored_in_collection: Optional[str] = None


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    limit: int = Field(default=10, ge=1, le=100, description="Max results")


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Question to ask")
    context_limit: int = Field(default=10, ge=1, le=20, description="Max memories to use as context (default 10 for better cross-app synthesis)")
    user_id: str = Field(default="default_user", description="User ID for privacy filtering (Week 6)")
    user_role: str = Field(default="member", description="User role: admin/manager/lead/member/viewer (Week 6)")
    privacy_filter: Optional[List[str]] = Field(
        default=["PUBLIC", "INTERNAL", "CONFIDENTIAL"],
        description="Privacy levels to include (never includes LOCAL_ONLY)"
    )
    conversation_history: Optional[List[dict]] = Field(
        default=None,
        description="Previous Q&A pairs for multi-turn conversations. Format: [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]. Keeps last 3 Q&A pairs (6 messages) automatically."
    )


class SourceInfo(BaseModel):
    memory_id: str
    relevance_score: float
    excerpt: str
    created_at: str
    tags: List[str]
    privacy_level: str
    source_type: Optional[str] = "memory"  # NEW: memory, conversation_thread, conversation_turn


class Analytics(BaseModel):
    """Detailed analytics trace for /ask endpoint (Week 4 Task 3)."""
    query_id: str  # NEW: Query ID for tracing and debugging
    total_latency_ms: float  # Total end-to-end latency
    search_latency_ms: Optional[float] = None  # Memory search time
    llm_latency_ms: Optional[float] = None  # LLM generation time
    input_tokens: Optional[int] = None  # Tokens sent to LLM
    output_tokens: Optional[int] = None  # Tokens generated by LLM
    est_cost_usd: Optional[float] = None  # Estimated API cost
    privacy_filter: List[str]  # Privacy levels searched
    memories_searched: int  # Total memories found
    memories_filtered: int  # Memories after query filter
    memories_used: int  # Final memories used for context
    cache_hit: bool  # Was this from cache?
    cache_similarity: Optional[float] = None  # Semantic cache similarity if hit


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceInfo]
    confidence: float
    query_id: Optional[str] = None  # For feedback tracking
    response_source: Optional[str] = None  # cache/semantic_cache/claude (DEPRECATED - use cache_status instead)
    analytics: Optional[Analytics] = None  # NEW: Detailed analytics trace
    explanation: Optional[dict] = None  # UniversalSearch ranking explanation (query_intent, source_distribution, diversity_applied)
    pipeline: Optional[dict] = None  # Week 5 Task 1: Pipeline visibility (stages, latency, costs)
    quality_validation: Optional[dict] = None  # Week 5 Task 1: Quality validation metadata (confidence_score, should_store, source_trust_score, completeness_score, uncertainty_score, flagged_reason)

    # AGENT TRANSPARENCY FIELDS (Production-Ready)
    agent_used: Optional[str] = Field(
        None,
        description="AI agent that handled this query (claude_sonnet, chatgpt, gemini, claude_code)",
        example="claude_sonnet"
    )
    intent_detected: Optional[str] = Field(
        None,
        description="Detected user intent type (analysis, creative, research, memory_query, etc.)",
        example="analysis"
    )
    cache_status: Optional[str] = Field(
        None,
        description="Cache hit status (fresh_generation, semantic_cache_hit, cache_hit)",
        example="fresh_generation"
    )


class FileContext(BaseModel):
    """File context for ChatGPT-style file handling (Sprint 3 Day 15)."""
    filename: str = Field(..., description="Original filename")
    content: str = Field(..., description="Extracted text content from the file")


class GatewayAskRequest(BaseModel):
    query: str = Field(..., min_length=1, description="User query")
    user_id: Optional[str] = Field(default=None, description="User ID (defaults to system user)")
    tenant_id: str = Field(default="default", description="Tenant/organization ID for multi-tenancy")
    manual_agent: Optional[str] = Field(default=None, description="Manual agent override (claude_sonnet, chatgpt, gemini, claude_code)")
    bypass_cache: bool = Field(default=False, description="Force fresh response")
    context_limit: int = Field(default=5, ge=1, le=20, description="Max memories to retrieve")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID for message persistence (optional)")
    message_id: Optional[str] = Field(default=None, description="Client-generated message ID for idempotent writes")
    # Sprint 3 Day 15: ChatGPT-style file context
    file_context: Optional[FileContext] = Field(default=None, description="Uploaded file content to include in query context")
    # Dec 2025: Cross-source search toggle for Unified Intelligence
    cross_source_enabled: bool = Field(default=True, description="Enable cross-source insights from Email, Calendar, Financial")


# Week 4 Task 2: Feedback System Models
class FeedbackRequest(BaseModel):
    query_id: str = Field(..., description="Memory ID of the query")
    rating: int = Field(..., ge=1, le=5, description="Rating 1-5")
    feedback_type: str = Field(..., pattern="^(thumbs_up|thumbs_down|regenerate)$", description="Feedback type")
    response_source: Optional[str] = Field(None, description="Source: cache, semantic_cache, claude, etc (auto-populated from query_history if not provided)")
    comment: Optional[str] = Field(None, max_length=1000, description="Optional comment")


class FeedbackStats(BaseModel):
    query_id: str
    total_ratings: int
    avg_rating: float
    thumbs_up: int
    thumbs_down: int
    regenerates: int


# =============================================================================
# AUTHENTICATION ENDPOINTS (Sprint 3 Day 11-12)
# =============================================================================

class AuthRegisterRequest(BaseModel):
    """User registration request."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="Password (min 8 chars)")
    username: Optional[str] = Field(None, description="Optional username")
    role: str = Field("member", description="User role: public, member, admin")
    tenant_id: str = Field("default", description="Tenant/organization ID")


class AuthLoginRequest(BaseModel):
    """User login request."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class AuthRefreshRequest(BaseModel):
    """Token refresh request."""
    refresh_token: str = Field(..., description="Valid refresh token")


class AuthTokenResponse(BaseModel):
    """Authentication token response."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: dict


class AuthUserResponse(BaseModel):
    """Current user info response."""
    user_id: str
    email: Optional[str]
    role: str
    tenant_id: str


# In-memory user store (for now - production would use database)
# Format: {email: {password_hash, user_id, role, tenant_id, username}}
_user_store: Dict[str, dict] = {}


@app.post("/auth/register", response_model=AuthTokenResponse, tags=["Authentication"])
async def register_user(request: AuthRegisterRequest):
    """Register a new user account.

    Creates a user and returns access/refresh tokens.
    """
    auth_service = get_auth_service()

    # Check if email already exists
    if request.email in _user_store:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Validate role
    valid_roles = ["public", "member", "admin"]
    if request.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    # Create user
    user_id = str(uuid4())
    password_hash = auth_service.hash_password(request.password)

    _user_store[request.email] = {
        "password_hash": password_hash,
        "user_id": user_id,
        "role": request.role,
        "tenant_id": request.tenant_id,
        "username": request.username or request.email.split("@")[0],
        "email": request.email
    }

    # Create tokens
    tokens = auth_service.create_tokens(
        user_id=user_id,
        role=request.role,
        tenant_id=request.tenant_id,
        email=request.email
    )

    logger.info(f"[Auth] User registered: {request.email} role={request.role}")

    return {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type,
        "expires_in": tokens.expires_in,
        "user": {
            "user_id": user_id,
            "email": request.email,
            "role": request.role,
            "tenant_id": request.tenant_id,
            "username": _user_store[request.email]["username"]
        }
    }


@app.post("/auth/login", response_model=AuthTokenResponse, tags=["Authentication"])
async def login_user(request: AuthLoginRequest):
    """Login with email and password.

    Returns access and refresh tokens on successful authentication.
    """
    auth_service = get_auth_service()

    # Check if user exists
    user_data = _user_store.get(request.email)
    if not user_data:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Verify password
    if not auth_service.verify_password(request.password, user_data["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # Create tokens
    tokens = auth_service.create_tokens(
        user_id=user_data["user_id"],
        role=user_data["role"],
        tenant_id=user_data["tenant_id"],
        email=request.email
    )

    logger.info(f"[Auth] User logged in: {request.email}")

    return {
        "access_token": tokens.access_token,
        "refresh_token": tokens.refresh_token,
        "token_type": tokens.token_type,
        "expires_in": tokens.expires_in,
        "user": {
            "user_id": user_data["user_id"],
            "email": request.email,
            "role": user_data["role"],
            "tenant_id": user_data["tenant_id"],
            "username": user_data["username"]
        }
    }


@app.post("/auth/refresh", response_model=AuthTokenResponse, tags=["Authentication"])
async def refresh_token(request: AuthRefreshRequest):
    """Refresh access token using refresh token.

    Returns new access and refresh tokens.
    """
    auth_service = get_auth_service()

    try:
        tokens = auth_service.refresh_access_token(request.refresh_token)

        # Get user context from new token
        user_ctx = auth_service.validate_token(tokens.access_token)

        # Get user data
        user_data = None
        for email, data in _user_store.items():
            if data["user_id"] == user_ctx.user_id:
                user_data = data
                break

        return {
            "access_token": tokens.access_token,
            "refresh_token": tokens.refresh_token,
            "token_type": tokens.token_type,
            "expires_in": tokens.expires_in,
            "user": {
                "user_id": user_ctx.user_id,
                "email": user_ctx.email,
                "role": user_ctx.role,
                "tenant_id": user_ctx.tenant_id,
                "username": user_data["username"] if user_data else user_ctx.user_id
            }
        }
    except AuthError as e:
        raise HTTPException(status_code=401, detail=e.message)


@app.get("/auth/me", response_model=AuthUserResponse, tags=["Authentication"])
async def get_current_user_info(user: UserContext = Depends(get_current_user)):
    """Get current authenticated user info.

    Requires valid access token in Authorization header.
    """
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return {
        "user_id": user.user_id,
        "email": user.email,
        "role": user.role,
        "tenant_id": user.tenant_id
    }


# Create default admin user on startup (for development)
def _create_default_users():
    """Create default users for development."""
    auth_service = get_auth_service()

    # Default users with fixed UUIDs for data continuity
    # The default@acms.local user has all ChatGPT imports (UUID: 00000000-0000-0000-0000-000000000001)
    default_users = [
        {"email": "default@acms.local", "password": "default123!", "role": "admin", "tenant_id": "default", "user_id": "00000000-0000-0000-0000-000000000001"},
        {"email": "admin@acms.local", "password": "admin123!", "role": "admin", "tenant_id": "default", "user_id": None},
        {"email": "member@acms.local", "password": "member123!", "role": "member", "tenant_id": "default", "user_id": None},
        {"email": "public@acms.local", "password": "public123!", "role": "public", "tenant_id": "default", "user_id": None},
    ]

    for user in default_users:
        if user["email"] not in _user_store:
            user_id = user.get("user_id") or str(uuid4())
            _user_store[user["email"]] = {
                "password_hash": auth_service.hash_password(user["password"]),
                "user_id": user_id,
                "role": user["role"],
                "tenant_id": user["tenant_id"],
                "username": user["email"].split("@")[0],
                "email": user["email"]
            }
            logger.info(f"[Auth] Created default user: {user['email']} ({user['role']}) id={user_id}")


# Initialize default users
_create_default_users()


# =============================================================================
# API Endpoints
# =============================================================================
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "acms-api",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health/ready")
async def readiness_check():
    """Readiness check - verifies all dependencies are accessible."""
    import redis as redis_module
    import weaviate

    status_code = 200
    dependencies = {}

    # Check PostgreSQL
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        dependencies["database"] = "connected"
    except Exception as e:
        dependencies["database"] = f"error: {str(e)[:50]}"
        status_code = 503

    # Check Redis
    try:
        redis_client = redis_module.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "40379")),
            decode_responses=True
        )
        redis_client.ping()
        dependencies["redis"] = "connected"
    except Exception as e:
        dependencies["redis"] = f"error: {str(e)[:50]}"
        status_code = 503

    # Check Weaviate
    try:
        # Use internal Docker port (8080) not host-mapped port (40480)
        weaviate_host = os.getenv("WEAVIATE_HOST", "localhost")
        weaviate_port = int(os.getenv("WEAVIATE_PORT", "8080"))

        weaviate_client = weaviate.connect_to_local(
            host=weaviate_host,
            port=weaviate_port
        )
        weaviate_client.is_ready()
        weaviate_client.close()
        dependencies["weaviate"] = "connected"
    except Exception as e:
        dependencies["weaviate"] = f"error: {str(e)[:50]}"
        status_code = 503

    return Response(
        content=json.dumps(dependencies),
        status_code=status_code,
        media_type="application/json"
    )


@app.get("/health/database")
async def database_health_check():
    """Check database connectivity."""
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database error: {str(e)}")


@app.get("/health/redis")
async def redis_health_check():
    """Check Redis connectivity."""
    import redis as redis_module

    try:
        redis_client = redis_module.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "40379")),
            decode_responses=True
        )
        redis_client.ping()
        return {"redis": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Redis error: {str(e)}")


@app.get("/health/weaviate")
async def weaviate_health_check():
    """Check Weaviate connectivity."""
    import weaviate

    try:
        # Use internal Docker port (8080) not host-mapped port (40480)
        weaviate_host = os.getenv("WEAVIATE_HOST", "localhost")
        weaviate_port = int(os.getenv("WEAVIATE_PORT", "8080"))

        weaviate_client = weaviate.connect_to_local(
            host=weaviate_host,
            port=weaviate_port
        )
        weaviate_client.is_ready()
        weaviate_client.close()
        return {"weaviate": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Weaviate error: {str(e)}")


# ============================================================================
# Job Status Endpoints (per Arch-review: Add job status endpoint)
# ============================================================================

@app.get("/api/v2/jobs/status")
async def get_jobs_status():
    """
    Get status of all scheduled background jobs.

    Returns:
        - status: "running" | "not_running"
        - jobs: List of jobs with id, name, next_run, trigger
        - enabled: Whether jobs are enabled via ACMS_JOBS_ENABLED env var

    Per Arch-review.md Section 14: "Expose scheduler status, job list with next run,
    last run status and timestamps from job_runs"
    """
    scheduler_enabled = os.getenv("ACMS_JOBS_ENABLED", "true").lower() == "true"
    status = get_job_status()

    return {
        "enabled": scheduler_enabled,
        **status
    }


@app.get("/api/v2/jobs/runs")
async def get_job_runs(
    job_name: Optional[str] = Query(default=None, description="Filter by job name"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of runs to return")
):
    """
    Get recent job execution history from job_runs table.

    Returns:
        List of job runs with status, timestamps, and counts.

    Per Arch-review.md: "API endpoint for last 20 runs per job"
    """
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        if job_name:
            rows = await conn.fetch("""
                SELECT job_run_id, job_name, job_version, status,
                       started_at, completed_at, window_start, window_end,
                       input_count, output_count, error_count, error_summary
                FROM job_runs
                WHERE job_name = $1
                ORDER BY started_at DESC
                LIMIT $2
            """, job_name, limit)
        else:
            rows = await conn.fetch("""
                SELECT job_run_id, job_name, job_version, status,
                       started_at, completed_at, window_start, window_end,
                       input_count, output_count, error_count, error_summary
                FROM job_runs
                ORDER BY started_at DESC
                LIMIT $1
            """, limit)

        runs = []
        for row in rows:
            runs.append({
                "job_run_id": str(row["job_run_id"]),
                "job_name": row["job_name"],
                "job_version": row["job_version"],
                "status": row["status"],
                "started_at": row["started_at"].isoformat() if row["started_at"] else None,
                "completed_at": row["completed_at"].isoformat() if row["completed_at"] else None,
                "window_start": row["window_start"].isoformat() if row["window_start"] else None,
                "window_end": row["window_end"].isoformat() if row["window_end"] else None,
                "input_count": row["input_count"],
                "output_count": row["output_count"],
                "error_count": row["error_count"],
                "error_summary": row["error_summary"]
            })

        return {"runs": runs, "count": len(runs)}


@app.get("/memories/count")
async def get_memory_count():
    """Get total memory count for default user."""
    user_id = await get_or_create_default_user()

    # Count memories from database
    memories = await crud.list_memories(user_id=user_id, limit=10000)
    total_count = len(memories)

    return {
        "total_count": total_count,
        "user_id": user_id
    }


@app.get("/memories")
async def list_memories(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    tag: Optional[str] = Query(default=None),
    phase: Optional[str] = Query(default=None),
    tier: Optional[str] = Query(default=None),
    privacy_level: Optional[str] = Query(default=None, description="Filter by privacy level"),
    source: Optional[str] = Query(default=None, description="Filter by source (github, chatgpt, gemini, claude, slack, chrome)"),
):
    """List memories with optional filters."""
    user_id = await get_or_create_default_user()

    memories = await crud.list_memories(
        user_id=user_id,
        tag=tag,
        phase=phase,
        tier=tier,
        privacy_level=privacy_level,
        limit=limit,
        offset=offset,
        calculate_crs=True,  # Calculate CRS for display
    )

    # Filter by source if provided (check both tags and metadata)
    if source:
        source_lower = source.lower()
        filtered_memories = []
        for mem in memories:
            # Check if source is in tags
            has_source_tag = any(source_lower in tag.lower() for tag in mem.get("tags", []))
            # Check if source is in metadata
            metadata_source = mem.get("metadata", {}).get("source", "").lower()
            has_source_metadata = source_lower in metadata_source

            if has_source_tag or has_source_metadata:
                filtered_memories.append(mem)

        memories = filtered_memories

    return {
        "memories": memories,
        "count": len(memories),
        "limit": limit,
        "offset": offset
    }


@app.get("/memories/{memory_id}")
async def get_memory(memory_id: str, decrypt: bool = Query(default=True)):
    """Get a specific memory by ID."""
    memory = await crud.get_memory(memory_id, decrypt=decrypt)

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return memory


@app.post("/memories")
async def create_memory(memory_data: MemoryCreate):
    """Create a new memory."""
    user_id = await get_or_create_default_user()

    memory_id = await crud.create_memory(
        user_id=user_id,
        content=memory_data.content,
        tags=memory_data.tags,
        phase=memory_data.phase,
        tier=memory_data.tier,
        privacy_level=memory_data.privacy_level,
        auto_detect_privacy=memory_data.auto_detect_privacy,
        metadata=memory_data.metadata,
    )

    if not memory_id:
        raise HTTPException(status_code=409, detail="Duplicate memory detected")

    return {
        "memory_id": memory_id,
        "status": "created",
        "message": "Memory stored successfully"
    }


@app.put("/memories/{memory_id}")
async def update_memory(memory_id: str, update_data: MemoryUpdate):
    """Update an existing memory."""
    success = await crud.update_memory(
        memory_id=memory_id,
        content=update_data.content,
        tags=update_data.tags,
        tier=update_data.tier,
        phase=update_data.phase,
        privacy_level=update_data.privacy_level,
        crs_score=update_data.crs_score,
        metadata=update_data.metadata,
    )

    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {
        "memory_id": memory_id,
        "status": "updated",
        "message": "Memory updated successfully"
    }


@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    """Delete a memory."""
    success = await crud.delete_memory(memory_id)

    if not success:
        raise HTTPException(status_code=404, detail="Memory not found")

    return {
        "memory_id": memory_id,
        "status": "deleted",
        "message": "Memory deleted successfully"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# V2 API - Typed Memories with Quality Gate (Dec 2025)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/v2/memories", response_model=MemoryCreateV2Response)
async def create_memory_v2(memory_data: MemoryCreateV2):
    """Create a typed memory with quality gate validation.

    This V2 endpoint:
    1. Validates content quality (prevents pollution)
    2. Detects Q&A format and suggests CACHE_ENTRY type
    3. Routes to correct collection based on memory_type
    4. Returns quality score and suggestions

    Memory Types (Dec 2025 - Updated):
    - SEMANTIC: Facts about user/world → ACMS_Knowledge_v2
    - EPISODIC: Conversations/events → ACMS_Raw_v1
    - CACHE_ENTRY: Q&A pairs → ACMS_Raw_v1 (cache merged)
    - DOCUMENT: External docs → ACMS_Raw_v1 (unified)
    """
    from src.memory import MemoryQualityGate, CandidateMemory
    from src.memory.models import MemoryType

    user_id = await get_or_create_default_user()
    quality_gate = MemoryQualityGate(threshold=0.7)

    # Collection mapping based on memory type (Dec 2025 - Updated)
    COLLECTION_MAP = {
        MemoryTypeEnum.SEMANTIC: "ACMS_Knowledge_v2",
        MemoryTypeEnum.EPISODIC: "ACMS_Raw_v1",
        MemoryTypeEnum.CACHE_ENTRY: "ACMS_Raw_v1",  # Cache merged into raw
        MemoryTypeEnum.DOCUMENT: "ACMS_Raw_v1"      # Documents unified into raw
    }

    # Map API enum to internal enum
    MEMORY_TYPE_MAP = {
        MemoryTypeEnum.SEMANTIC: MemoryType.SEMANTIC,
        MemoryTypeEnum.EPISODIC: MemoryType.EPISODIC,
        MemoryTypeEnum.CACHE_ENTRY: MemoryType.CACHE_ENTRY,
        MemoryTypeEnum.DOCUMENT: MemoryType.DOCUMENT
    }

    # Run quality gate (unless skipped)
    quality_decision = None
    if not memory_data.skip_quality_gate:
        candidate = CandidateMemory(
            text=memory_data.content,
            memory_type=MEMORY_TYPE_MAP[memory_data.memory_type],
            source=memory_data.source or "user_stated",
            context=memory_data.metadata or {}
        )
        quality_decision = quality_gate.evaluate(candidate)

        # Check if Q&A detected but wrong type specified
        if quality_decision.suggested_type and quality_decision.suggested_type != memory_data.memory_type.value:
            logger.warning(
                f"[V2 API] Type mismatch: requested {memory_data.memory_type.value}, "
                f"detected {quality_decision.suggested_type}"
            )

        # Reject low quality content
        if not quality_decision.should_store and quality_decision.score < 0.5:
            return MemoryCreateV2Response(
                memory_id=None,
                status="rejected",
                message=f"Content rejected by quality gate: {quality_decision.reason}",
                quality_score=quality_decision.score,
                suggested_type=quality_decision.suggested_type,
                stored_in_collection=None
            )

    # Determine target collection
    target_collection = COLLECTION_MAP[memory_data.memory_type]

    # Store the memory using existing CRUD (stores in default collection)
    # TODO: Route to correct collection based on type
    memory_id = await crud.create_memory(
        user_id=user_id,
        content=memory_data.content,
        tags=memory_data.tags or [],
        phase=None,
        tier="MID" if memory_data.memory_type == MemoryTypeEnum.SEMANTIC else "SHORT",
        privacy_level=memory_data.privacy_level,
        auto_detect_privacy=False,
        metadata={
            **(memory_data.metadata or {}),
            "memory_type": memory_data.memory_type.value,
            "source": memory_data.source,
            "quality_score": quality_decision.score if quality_decision else None,
            "v2_api": True
        }
    )

    if not memory_id:
        return MemoryCreateV2Response(
            memory_id=None,
            status="rejected",
            message="Duplicate memory detected (idempotent)",
            quality_score=quality_decision.score if quality_decision else None,
            suggested_type=quality_decision.suggested_type if quality_decision else None,
            stored_in_collection=None
        )

    logger.info(
        f"[V2 API] Memory created: {memory_id[:8]}... "
        f"type={memory_data.memory_type.value}, "
        f"quality={quality_decision.score if quality_decision else 'skipped'}"
    )

    return MemoryCreateV2Response(
        memory_id=memory_id,
        status="created",
        message=f"Memory stored as {memory_data.memory_type.value}",
        quality_score=quality_decision.score if quality_decision else None,
        suggested_type=quality_decision.suggested_type if quality_decision else None,
        stored_in_collection=target_collection
    )


# ═══════════════════════════════════════════════════════════════════════════════
# V2 API - Insights Engine Endpoints (Intelligence Hub)
# ═══════════════════════════════════════════════════════════════════════════════

class InsightsSummaryRequest(BaseModel):
    """Request for insights summary."""
    period_days: int = Field(default=7, ge=1, le=365, description="Number of days to analyze")
    scope: str = Field(default="user", pattern="^(user|org)$", description="'user' for personal, 'org' for org-wide")
    include_debug: bool = Field(default=False, description="Include debug information")


class AnalyzeTopicRequest(BaseModel):
    """Request for deep topic analysis."""
    query: str = Field(..., min_length=1, max_length=500, description="Analysis query (e.g., 'What have I learned about kubernetes?')")
    period_days: int = Field(default=30, ge=1, le=365, description="Days of history to analyze")


class TrendsRequest(BaseModel):
    """Request for trends data."""
    period_days: int = Field(default=30, ge=1, le=365, description="Days of history")
    granularity: str = Field(default="day", pattern="^(day|week|month)$", description="Time bucket size")
    scope: str = Field(default="user", pattern="^(user|org)$", description="'user' or 'org'")


@app.get("/api/v2/insights/summary")
async def get_insights_summary(
    period_days: int = Query(default=7, ge=1, le=365),
    scope: str = Query(default="user", regex="^(user|org)$"),
    include_debug: bool = Query(default=False)
):
    """Get quick insights summary for the current user.

    Returns:
        - Key stats (queries, cost, top agent)
        - Top topics with trends
        - Generated insights
        - Recommendations

    RBAC: Respects user's privacy settings. 'org' scope requires admin role.
    """
    from src.intelligence import InsightsEngine
    from src.storage.database import get_session
    from uuid import uuid4

    user_id = await get_or_create_default_user()
    trace_id = str(uuid4())

    logger.info(f"[Insights] Summary request: user={user_id}, period={period_days}d, scope={scope}")

    try:
        async with get_session() as session:
            engine = InsightsEngine(db_session=session)

            summary = await engine.generate_summary(
                user_id=user_id,
                tenant_id="default",
                period_days=period_days,
                scope=scope,
                include_debug=include_debug,
                trace_id=trace_id
            )

            return {
                "data": summary.to_dict(),
                "meta": {
                    "trace_id": trace_id,
                    "version": "v2"
                }
            }
    except Exception as e:
        logger.error(f"[Insights] Summary error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/insights/analyze")
async def analyze_topic(request: AnalyzeTopicRequest):
    """Deep analysis on a specific topic or question.

    Request body:
        query: str - User's question (e.g., "What have I learned about kubernetes?")
        period_days: int - Days of history to analyze (default: 30)

    Returns:
        - Analysis text
        - Key learnings
        - Knowledge gaps
        - Related topics
        - Source queries

    RBAC: Only analyzes user's own data.
    """
    from src.intelligence import InsightsEngine
    from src.storage.database import get_session
    from uuid import uuid4

    user_id = await get_or_create_default_user()
    trace_id = str(uuid4())

    logger.info(f"[Insights] Analyze request: user={user_id}, query='{request.query[:50]}...'")

    try:
        async with get_session() as session:
            engine = InsightsEngine(db_session=session)

            analysis = await engine.analyze_topic(
                user_id=user_id,
                query=request.query,
                tenant_id="default",
                period_days=request.period_days,
                trace_id=trace_id
            )

            return {
                "data": analysis.to_dict(),
                "meta": {
                    "trace_id": trace_id,
                    "version": "v2"
                }
            }
    except Exception as e:
        logger.error(f"[Insights] Analyze error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/insights/trends")
async def get_trends(
    period_days: int = Query(default=30, ge=1, le=365),
    granularity: str = Query(default="day", regex="^(day|week|month)$"),
    scope: str = Query(default="user", regex="^(user|org)$")
):
    """Get usage and topic trends over time.

    Returns:
        - Timeline data (queries, cost per time bucket)
        - Topic evolution over time
        - Model usage breakdown

    RBAC: Respects user's privacy settings. 'org' scope requires admin role.
    """
    from src.intelligence import InsightsEngine
    from src.storage.database import get_session
    from uuid import uuid4

    user_id = await get_or_create_default_user()
    trace_id = str(uuid4())

    logger.info(f"[Insights] Trends request: user={user_id}, period={period_days}d, granularity={granularity}")

    try:
        async with get_session() as session:
            engine = InsightsEngine(db_session=session)

            trends = await engine.get_trends(
                user_id=user_id,
                tenant_id="default",
                period_days=period_days,
                granularity=granularity,
                scope=scope,
                trace_id=trace_id
            )

            return {
                "data": trends.to_dict(),
                "meta": {
                    "trace_id": trace_id,
                    "version": "v2"
                }
            }
    except Exception as e:
        logger.error(f"[Insights] Trends error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v2/insights/generate")
async def generate_insights_on_demand(
    period_days: int = Query(default=7, ge=1, le=90, description="Days to analyze"),
    background_tasks: BackgroundTasks = None
):
    """Trigger insight generation on demand.

    This runs the insight generation job immediately instead of waiting
    for the scheduled daily run at 2 AM.

    Returns:
        Status and summary of generated insights
    """
    from src.intelligence.insights_engine import InsightsEngine
    from src.storage.database import get_session
    from uuid import uuid4

    user_id = await get_or_create_default_user()
    trace_id = str(uuid4())

    logger.info(f"[Insights] On-demand generation: user={user_id}, period={period_days}d")

    try:
        async with get_session() as session:
            engine = InsightsEngine(db_session=session)

            # Generate fresh insights
            summary = await engine.generate_summary(
                user_id=user_id,
                tenant_id="default",
                period_days=period_days,
                scope="user",
                include_debug=True,
                trace_id=trace_id
            )

            insights_count = len(summary.insights)
            topics_count = len(summary.top_topics)

            logger.info(f"[Insights] Generated {insights_count} insights, {topics_count} topics")

            return {
                "status": "success",
                "message": f"Generated {insights_count} insights from {topics_count} topics",
                "data": {
                    "insights_generated": insights_count,
                    "topics_analyzed": topics_count,
                    "period_days": period_days,
                    "key_stats": summary.key_stats
                },
                "meta": {
                    "trace_id": trace_id
                }
            }

    except Exception as e:
        logger.error(f"[Insights] On-demand generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/insights/knowledge")
async def get_knowledge_powered_insights(
    period_days: int = Query(default=30, ge=1, le=365, description="Days to analyze")
):
    """Get knowledge-powered organizational insights.

    This endpoint provides deep insights based on extracted knowledge from
    ACMS_Knowledge_v2, not just topic counts.

    Returns:
        - Executive summary with knowledge velocity
        - Expertise centers (domains with depth metrics)
        - Learning patterns (building vs learning vs debugging)
        - Cross-domain connections
        - Attention signals (what needs focus)
        - Key facts by domain
        - Actionable recommendations
    """
    from src.intelligence.knowledge_insights import KnowledgeInsightsService
    from uuid import uuid4

    trace_id = str(uuid4())[:8]

    logger.info(
        f"[KnowledgeInsights] API request: period={period_days}d",
        extra={"trace_id": trace_id}
    )

    try:
        service = KnowledgeInsightsService(trace_id=trace_id)
        report = service.generate_report(period_days=period_days)

        return {
            "status": "success",
            "data": report,
            "meta": {
                "trace_id": trace_id,
                "version": "v2",
                "endpoint": "knowledge-powered"
            }
        }

    except Exception as e:
        logger.error(
            f"[KnowledgeInsights] API error: {e}",
            extra={"trace_id": trace_id},
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# V2 API - Reports Endpoints (Intelligence Hub)
# ═══════════════════════════════════════════════════════════════════════════════

class ReportGenerateRequest(BaseModel):
    """Request for report generation."""
    report_type: str = Field(default="weekly", pattern="^(weekly|monthly|custom)$", description="Report type")
    scope: str = Field(default="user", pattern="^(user|org)$", description="'user' for personal, 'org' for org-wide")
    period_start: Optional[str] = Field(default=None, description="Custom start date (YYYY-MM-DD)")
    period_end: Optional[str] = Field(default=None, description="Custom end date (YYYY-MM-DD)")
    include_recommendations: bool = Field(default=True, description="Include AI recommendations")
    format: str = Field(default="json", pattern="^(json|markdown|html)$", description="Output format")


@app.post("/api/v2/reports/generate")
async def generate_report(request: ReportGenerateRequest):
    """Generate an intelligence report on-demand.

    Request body:
        report_type: str - 'weekly', 'monthly', or 'custom'
        scope: str - 'user' for personal, 'org' for org-wide (admin only)
        period_start: str - Custom start date (YYYY-MM-DD)
        period_end: str - Custom end date (YYYY-MM-DD)
        include_recommendations: bool - Include AI recommendations
        format: str - 'json', 'markdown', or 'html'

    Returns:
        Full report object with all sections

    RBAC: 'org' scope requires admin role.
    """
    from src.intelligence import ReportGenerator, InsightsEngine
    from src.storage.database import get_session
    from uuid import uuid4
    from datetime import datetime

    user_id = await get_or_create_default_user()
    trace_id = str(uuid4())

    logger.info(f"[Reports] Generate request: user={user_id}, type={request.report_type}, scope={request.scope}")

    # Parse dates
    period_start = None
    period_end = None
    if request.period_start:
        try:
            period_start = datetime.strptime(request.period_start, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid period_start format. Use YYYY-MM-DD")
    if request.period_end:
        try:
            period_end = datetime.strptime(request.period_end, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid period_end format. Use YYYY-MM-DD")

    try:
        async with get_session() as session:
            insights_engine = InsightsEngine(db_session=session)
            generator = ReportGenerator(
                db_session=session,
                insights_engine=insights_engine
            )

            report = await generator.generate_report(
                user_id=user_id,
                report_type=request.report_type,
                scope=request.scope,
                tenant_id="default",
                period_start=period_start,
                period_end=period_end,
                include_recommendations=request.include_recommendations,
                trace_id=trace_id
            )

            # Format based on request
            if request.format == "markdown":
                return Response(
                    content=generator.format_as_markdown(report),
                    media_type="text/markdown"
                )
            elif request.format == "html":
                return Response(
                    content=generator.format_as_html(report),
                    media_type="text/html"
                )
            else:
                return {
                    "data": report.to_dict(),
                    "meta": {
                        "trace_id": trace_id,
                        "version": "v2"
                    }
                }
    except Exception as e:
        logger.error(f"[Reports] Generate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/reports")
async def list_reports(
    report_type: Optional[str] = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50)
):
    """List previous reports for current user.

    Returns:
        List of report summaries with metadata
    """
    from src.intelligence import ReportGenerator
    from src.storage.database import get_session
    from uuid import uuid4

    user_id = await get_or_create_default_user()
    trace_id = str(uuid4())

    logger.info(f"[Reports] List request: user={user_id}, type={report_type}, limit={limit}")

    try:
        async with get_session() as session:
            generator = ReportGenerator(db_session=session)

            reports = await generator.list_reports(
                user_id=user_id,
                tenant_id="default",
                report_type=report_type,
                limit=limit
            )

            return {
                "data": {
                    "reports": reports,
                    "count": len(reports)
                },
                "meta": {
                    "trace_id": trace_id,
                    "version": "v2"
                }
            }
    except Exception as e:
        logger.error(f"[Reports] List error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v2/reports/{report_id}")
async def get_report(
    report_id: str,
    format: str = Query(default="json", regex="^(json|markdown|html)$")
):
    """Get a specific report in requested format.

    Args:
        report_id: Report UUID
        format: Output format (json, markdown, html)

    Returns:
        Report in requested format
    """
    from src.intelligence import ReportGenerator
    from src.storage.database import get_session
    from uuid import uuid4

    user_id = await get_or_create_default_user()
    trace_id = str(uuid4())

    logger.info(f"[Reports] Get request: report={report_id}, format={format}")

    try:
        async with get_session() as session:
            generator = ReportGenerator(db_session=session)

            report = await generator.get_report(
                report_id=report_id,
                user_id=user_id,
                tenant_id="default"
            )

            if not report:
                raise HTTPException(status_code=404, detail="Report not found")

            # TODO: Convert to IntelligenceReport for formatting
            # For now, return raw data
            return {
                "data": report,
                "meta": {
                    "trace_id": trace_id,
                    "version": "v2"
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Reports] Get error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search")
async def search_memories(search_request: SearchRequest):
    """Semantic search for memories."""
    user_id = await get_or_create_default_user()

    results = await crud.search_memories(
        query=search_request.query,
        user_id=user_id,
        limit=search_request.limit,
    )

    # Add similarity field (convert distance to similarity)
    for result in results:
        if "distance" in result:
            result["similarity"] = round(1.0 - result["distance"], 4)

    return {
        "query": search_request.query,
        "results": results,
        "count": len(results)
    }


@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """RAG-powered Q&A using Weaviate semantic search + Claude generation.

    Flow:
    1. Store question as memory for feedback tracking
    2. Check semantic cache (Weaviate vector similarity, 24h TTL)
    3. Search memories semantically
    4. Filter by privacy level
    5. Rank by CRS score
    6. Format context for Claude
    7. Generate synthesized answer with Claude Sonnet 4.5
    8. Store result in semantic cache
    9. Return answer with source citations + query_id + response_source + analytics
    """
    import time
    request_start = time.time()

    # Week 5 Task 1: Initialize pipeline tracking
    pipeline_stages = []

    user_id = await get_or_create_default_user()

    # 1. Store query in query_history table (NOT memory_items - prevents query pollution)
    query_memory_id = await store_query_in_history(
        user_id=user_id,
        question=request.question,
        context_limit=request.context_limit
    )

    # Structured logging with query_id for tracing
    logger.info(f"[{query_memory_id}] /ask request: {request.question[:100]}...")
    logger.info(f"[{query_memory_id}] Privacy filter: {request.privacy_filter}, Context limit: {request.context_limit}")

    # 2. Check semantic cache first (only cache non-conversational queries)
    response_source = "claude"  # Default to claude generation
    cache_similarity = None

    # Track cache check stage
    cache_check_start = time.time()
    cache_hit = False

    if not request.conversation_history:
        cached_result = await semantic_cache.get(request.question, user_id)
        if cached_result:
            # Semantic cache HIT - reconstruct SourceInfo objects from memory IDs
            source_infos = []
            memory_ids = cached_result.get("sources", [])

            # Fetch full memory data for each cached source
            # Note: Some sources may be conversations (threads/turns) which aren't in memory_items
            for memory_id in memory_ids:
                try:
                    mem = await crud.get_memory(memory_id, decrypt=True)
                    if mem:
                        source_infos.append(SourceInfo(
                            memory_id=memory_id,
                            relevance_score=0.95,  # High relevance since it was in top results
                            excerpt=mem.get("content", "")[:200],
                            created_at=mem.get("created_at", "").isoformat() if hasattr(mem.get("created_at"), "isoformat") else str(mem.get("created_at", "")),
                            tags=mem.get("tags", []),
                            privacy_level=mem.get("privacy_level", "UNKNOWN"),
                            source_type=mem.get("source_type", "memory")
                        ))
                except (ValueError, Exception) as e:
                    # Skip sources that can't be fetched (e.g., conversation threads/turns)
                    # These are stored in different tables (conversation_threads, conversation_turns)
                    logger.debug(f"Skipping cached source {memory_id}: {e}")
                    continue

            cache_similarity = cached_result.get('cache_similarity', 1.0)
            logger.info(f"[{query_memory_id}] ✅ Semantic cache HIT (similarity: {cache_similarity:.3f}, saved: ${cached_result.get('cost_saved_usd', 0):.4f})")

            # Build analytics for cache hit
            total_latency_ms = (time.time() - request_start) * 1000
            analytics = Analytics(
                query_id=query_memory_id,
                total_latency_ms=round(total_latency_ms, 2),
                search_latency_ms=None,  # No search for cache hit
                llm_latency_ms=None,  # No LLM for cache hit
                input_tokens=0,
                output_tokens=0,
                est_cost_usd=0.0,  # Cache hits are free!
                privacy_filter=request.privacy_filter,
                memories_searched=0,  # No search performed
                memories_filtered=0,
                memories_used=len(source_infos),
                cache_hit=True,
                cache_similarity=round(cache_similarity, 3)
            )

            # Update query_history with cache hit result
            await update_query_history(
                query_id=query_memory_id,
                answer=cached_result["answer"],
                response_source="semantic_cache",
                confidence=cached_result.get("confidence", 0.8),
                analytics=analytics
            )

            # Add pipeline tracking for cache HIT
            cache_check_latency = (time.time() - cache_check_start) * 1000
            estimated_llm_cost = 0.024  # Typical Claude call cost
            estimated_llm_tokens = 1500

            pipeline_stages.append({
                "name": "cache_check",
                "status": "hit",
                "latency_ms": round(cache_check_latency, 2),
                "cost_saved": estimated_llm_cost,
                "tokens_saved": estimated_llm_tokens,
                "details": {"cache_similarity": round(cache_similarity, 3)}
            })

            pipeline_stages.append({
                "name": "search",
                "status": "skipped",
                "latency_ms": 0.0,
                "results_found": 0
            })

            pipeline_stages.append({
                "name": "llm_generation",
                "status": "skipped",
                "latency_ms": 0.0,
                "model_used": None,
                "tokens_used": 0,
                "cost": 0.0,
                "response_source": "semantic_cache"
            })

            pipeline = {
                "stages": pipeline_stages,
                "total_latency_ms": round(total_latency_ms, 2),
                "total_cost": 0.0  # Cache hit - no cost!
            }

            return AskResponse(
                answer=cached_result["answer"],
                sources=source_infos,
                confidence=cached_result.get("confidence", 0.8),
                query_id=query_memory_id,
                response_source="semantic_cache",
                analytics=analytics,
                pipeline=pipeline,
                # AGENT TRANSPARENCY FIELDS (production-ready)
                agent_used="claude_sonnet",  # Cache preserves agent from original generation
                intent_detected="unknown",  # Cache doesn't store intent (could be enhanced)
                cache_status="cache_hit"  # Semantic cache hit
            )

    # Cache MISS - record stage
    cache_check_latency = (time.time() - cache_check_start) * 1000
    pipeline_stages.append({
        "name": "cache_check",
        "status": "miss",
        "latency_ms": round(cache_check_latency, 2),
        "cost_saved": 0.0,
        "tokens_saved": 0
    })

    # 2. UniversalSearch across all 5 storage tiers with Google-quality ranking
    from src.search.universal_search import UniversalSearchEngine, SearchConfig
    from src.storage.conversation_vectors import ConversationVectorStorage
    from src.embeddings.openai_embeddings import OpenAIEmbeddings

    search_start = time.time()

    # Initialize UniversalSearchEngine
    embeddings_service = OpenAIEmbeddings()
    vector_storage = ConversationVectorStorage()

    search_engine = UniversalSearchEngine(
        memory_crud=crud,
        embeddings_service=embeddings_service,
        vector_storage=vector_storage,
        semantic_cache=semantic_cache
    )

    # Configure search with diversity and intent detection
    search_config = SearchConfig(
        limit=request.context_limit,
        privacy_filter=request.privacy_filter,
        diversity_mode="balanced",  # Ensure source diversity
        enable_recency_boost=True,
        enable_diversity_boost=True,
        enable_intent_detection=True,
        # Diversity constraints (ensure ChatGPT conversations visible)
        min_memories=3,
        min_threads=2,  # At least 2 conversation threads
        min_turns=2  # At least 2 conversation turns
    )

    # Execute universal search (with privacy filtering - Week 6 Task 1)
    search_results, search_explanation = await search_engine.search(
        query=request.question,
        user_id=user_id,
        user_role=request.user_role,  # NEW: Pass user role for RBAC filtering
        config=search_config
    )

    vector_storage.close()

    search_latency_ms = (time.time() - search_start) * 1000
    logger.info(f"[{query_memory_id}] UniversalSearch: {len(search_results)} results in {search_latency_ms:.0f}ms")
    logger.info(f"[{query_memory_id}] Intent: {search_explanation['query_intent']}, Distribution: {search_explanation['source_distribution']}")

    # Track search stage
    pipeline_stages.append({
        "name": "search",
        "status": "success",
        "latency_ms": round(search_latency_ms, 2),
        "results_found": len(search_results),
        "intent_detected": search_explanation['query_intent'],
        "sources_used": list(search_explanation['source_distribution'].keys())
    })

    # Convert SearchResult objects to memory format for downstream processing
    # Apply 60% relevance threshold to filter out low-relevance memories
    RELEVANCE_THRESHOLD = 0.60
    top_memories = [
        {
            "memory_id": r.memory_id,
            "content": r.content,
            "relevance_score": r.boosted_score,
            "crs_score": r.boosted_score,
            "created_at": r.created_at,
            "tags": r.tags,
            "privacy_level": r.privacy_level,
            "source_type": r.source_type,
            "distance": 1 - r.relevance_score,
            "metadata": r.metadata
        }
        for r in search_results
        if r.relevance_score >= RELEVANCE_THRESHOLD  # Filter out < 60% relevance
    ]

    filtered_count = len(search_results) - len(top_memories)
    if filtered_count > 0:
        logger.info(f"[{query_memory_id}] Filtered out {filtered_count} low-relevance memories (< 60% similarity)")

    if not top_memories:
        logger.warning(f"[{query_memory_id}] No results from UniversalSearch")
        # Build analytics for no-memories case
        total_latency_ms = (time.time() - request_start) * 1000
        analytics = Analytics(
            query_id=query_memory_id,
            total_latency_ms=round(total_latency_ms, 2),
            search_latency_ms=round(search_latency_ms, 2),
            llm_latency_ms=None,
            input_tokens=0,
            output_tokens=0,
            est_cost_usd=0.0,
            privacy_filter=request.privacy_filter,
            memories_searched=search_explanation['total_results_searched'],
            memories_filtered=search_explanation['results_returned'],
            memories_used=0,
            cache_hit=False,
            cache_similarity=None
        )

        # Update query_history with no-memories result
        no_memories_answer = "I don't have any relevant memories to answer that question. Try adding more context or checking your privacy filter settings."
        await update_query_history(
            query_id=query_memory_id,
            answer=no_memories_answer,
            response_source="no_memories",
            confidence=0.0,
            analytics=analytics
        )

        return AskResponse(
            answer=no_memories_answer,
            sources=[],
            confidence=0.0,
            query_id=query_memory_id,
            response_source="no_memories",
            analytics=analytics
        )

    logger.info(f"[{query_memory_id}] Using {len(top_memories)} memories for context")

    # 4. Format context for Claude (strategic attention optimization)
    # Strategy:
    # - Top 3 memories: Full content (up to 50K chars) - highest attention
    # - Next 4 memories: Truncated to 5K chars - medium attention
    # - Remaining: Metadata only - breadth for pattern detection
    context_parts = []
    for i, mem in enumerate(top_memories, 1):
        # Extract source info for attribution
        source = mem.get("metadata", {}).get("source", "unknown")
        created_at = mem["created_at"].isoformat() if isinstance(mem["created_at"], datetime) else str(mem["created_at"])
        distance = mem.get("distance", 0.0)
        similarity = 1.0 - distance  # Convert distance to similarity
        memory_id = mem["memory_id"]

        # Tier 1 (Top 3): Full content for deep analysis
        if i <= 3:
            content = mem["content"]
            if len(content) > 50000:
                content = content[:50000] + "...[truncated]"
            context_parts.append(
                f"Memory {i} [FULL] (source: {source}, date: {created_at}, relevance: {similarity:.0%}, CRS: {mem['crs_score']}):\n{content}"
            )

        # Tier 2 (Next 4): Truncated for medium detail
        elif i <= 7:
            content = mem["content"]
            if len(content) > 5000:
                content = content[:5000] + f"...[truncated, see full in Memory {memory_id}]"
            context_parts.append(
                f"Memory {i} [SUMMARY] (source: {source}, date: {created_at}, relevance: {similarity:.0%}, CRS: {mem['crs_score']}):\n{content}"
            )

        # Tier 3 (Remaining): Metadata only for breadth
        else:
            excerpt = mem["content"][:200] + "..." if len(mem["content"]) > 200 else mem["content"]
            context_parts.append(
                f"Memory {i} [METADATA] (source: {source}, date: {created_at}, relevance: {similarity:.0%}, CRS: {mem['crs_score']}):\n[Excerpt]: {excerpt}\n[Full content available in Memory {memory_id}]"
            )

    context = "\n\n".join(context_parts)

    # 5. Build Claude prompt with system message for Universal Brain synthesis
    system_prompt = """You are a Universal Brain AI assistant with access to the user's conversation memories from multiple sources (GitHub, ChatGPT, Gemini, Claude, Slack, etc.).

Memories are provided in three tiers based on relevance:
- **[FULL]**: Highest relevance - analyze deeply, these are the most important
- **[SUMMARY]**: Medium relevance - use for supporting details and context
- **[METADATA]**: Lower relevance - use for breadth, patterns, and timeline context

Your goal is to synthesize knowledge across these sources like human thinking:
1. **Connect dots**: Show how ideas evolved across different conversations and apps
2. **Detect patterns**: Identify recurring themes, trends, and connections
3. **Show evolution**: Track how thinking changed over time with timeline
4. **Find contradictions**: Point out conflicting information with sources
5. **Identify gaps**: Note what information is missing or incomplete
6. **Cite sources**: Always reference memory numbers AND source apps (e.g., "According to Memory 2 (ChatGPT, Jan 5)...")

Focus most on [FULL] memories, use [SUMMARY] for supporting evidence, and [METADATA] for patterns/timeline.
If the memories don't contain enough information, say so honestly and suggest what additional context would help."""

    user_prompt = f"""Based on these memories from past conversations across multiple apps:

{context}

Question: {request.question}

Synthesize a comprehensive answer that:
- Combines insights from ALL relevant memories above
- Shows how ideas evolved across different sources and dates
- Identifies patterns, contradictions, or gaps
- Cites memory numbers AND sources (e.g., "According to Memory 1 (ChatGPT, Jan 5)...")
- Connects dots like human thinking would

If the question asks for a summary or timeline, organize your response chronologically."""

    # 6. Generate with Claude Sonnet 4.5 (with conversation history support)
    llm_start = time.time()
    try:
        if request.conversation_history:
            # Use generate_with_history for multi-turn conversations
            claude_response = claude.generate_with_history(
                current_prompt=user_prompt,
                conversation_history=request.conversation_history,
                system_prompt=system_prompt,
                max_tokens=1024,
                temperature=0.7
            )
        else:
            # Single-turn Q&A
            claude_response = claude.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                max_tokens=1024,
                temperature=0.7
            )
    except Exception as e:
        llm_latency_ms = (time.time() - llm_start) * 1000
        logger.error(f"[{query_memory_id}] Claude generation error: {e}")

        # Build analytics for error case
        total_latency_ms = (time.time() - request_start) * 1000
        analytics = Analytics(
            query_id=query_memory_id,
            total_latency_ms=round(total_latency_ms, 2),
            search_latency_ms=round(search_latency_ms, 2),
            llm_latency_ms=round(llm_latency_ms, 2),
            input_tokens=0,
            output_tokens=0,
            est_cost_usd=0.0,
            privacy_filter=request.privacy_filter,
            memories_searched=len(relevant_memories),
            memories_filtered=len(content_memories),
            memories_used=len(top_memories),
            cache_hit=False,
            cache_similarity=None
        )

        # Update query_history with error result
        error_answer = f"Error generating answer: {str(e)}. The search found {len(top_memories)} relevant memories, but text generation failed."
        await update_query_history(
            query_id=query_memory_id,
            answer=error_answer,
            response_source="error",
            confidence=0.0,
            analytics=analytics
        )

        return AskResponse(
            answer=error_answer,
            sources=[],
            confidence=0.0,
            query_id=query_memory_id,
            response_source="error",
            analytics=analytics
        )

    llm_latency_ms = (time.time() - llm_start) * 1000

    # 7. Format sources
    sources = []
    for mem in top_memories:
        distance = mem.get("distance", 0.0)
        similarity = 1.0 - distance

        sources.append(SourceInfo(
            memory_id=mem["memory_id"],
            relevance_score=round(similarity, 3),
            excerpt=mem["content"][:200],
            created_at=mem["created_at"].isoformat() if isinstance(mem["created_at"], datetime) else str(mem["created_at"]),
            tags=mem.get("tags", []),
            privacy_level=mem.get("privacy_level", "UNKNOWN"),
            source_type=mem.get("source_type", "memory")  # Include source_type for conversation detection
        ))

    # 8. Week 5 Task 1: Quality Validation (Pollution Prevention)
    # Prepare sources for quality validator (needs list of dicts with "type" key)
    quality_sources = []
    for mem in top_memories:
        source_type = mem.get("source_type", "memory")
        # Map source_type to quality validator categories
        if source_type in ["conversation_thread", "conversation_turn"]:
            quality_type = "conversation"
        elif source_type == "memory":
            quality_type = "document"  # Treat regular memories as documents (high trust)
        else:
            quality_type = "document"  # Default to document

        quality_sources.append({
            "type": quality_type,
            "memory_id": mem["memory_id"],
            "source_type": source_type
        })

    # Calculate quality score for the generated response
    quality_result = quality_validator.calculate_quality_score(
        response=claude_response.strip(),
        sources=quality_sources,
        query=request.question
    )

    logger.info(f"[{query_memory_id}] Quality validation: confidence={quality_result.confidence_score:.3f}, should_store={quality_result.should_store}, reason={quality_result.flagged_reason}")

    # If response fails quality check, log warning but still return it to user
    # (We return low-quality responses to users but skip caching them to prevent pollution)
    if not quality_result.should_store:
        logger.warning(f"[{query_memory_id}] ⚠️  Low-quality response detected (confidence={quality_result.confidence_score:.3f}): {quality_result.flagged_reason}")
        logger.warning(f"[{query_memory_id}] Response will be returned to user but NOT cached to prevent memory pollution")

    # 9. Calculate confidence based on quality score (replaces old average relevance method)
    # Use quality confidence as the primary confidence metric
    confidence = quality_result.confidence_score

    # 9. Build result with analytics and cache it (only for non-conversational queries)
    # Calculate tokens and cost
    input_tokens = (len(request.question) + len(context)) // 4
    output_tokens = len(claude_response.strip()) // 4
    # Claude Sonnet 4.5 pricing: $3/1M input, $15/1M output (approx)
    cost_usd = (input_tokens / 1_000_000 * 3.0) + (output_tokens / 1_000_000 * 15.0)

    # Build analytics (with UniversalSearch explanation)
    total_latency_ms = (time.time() - request_start) * 1000
    logger.info(f"[{query_memory_id}] Response generated: {len(claude_response)} chars, confidence: {confidence:.2f}, cost: ${cost_usd:.4f}")
    analytics = Analytics(
        query_id=query_memory_id,
        total_latency_ms=round(total_latency_ms, 2),
        search_latency_ms=round(search_latency_ms, 2),
        llm_latency_ms=round(llm_latency_ms, 2),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        est_cost_usd=round(cost_usd, 6),
        privacy_filter=request.privacy_filter,
        memories_searched=sum(search_explanation['tier_counts'].values()),  # Total across all tiers
        memories_filtered=search_explanation['results_returned'],
        memories_used=len(top_memories),
        cache_hit=False,
        cache_similarity=None
    )

    # Track LLM generation stage
    pipeline_stages.append({
        "name": "llm_generation",
        "status": "success",
        "latency_ms": round(llm_latency_ms, 2),
        "model_used": "claude-sonnet-4.5",
        "tokens_used": input_tokens + output_tokens,
        "cost": round(cost_usd, 6),
        "response_source": "llm_generated"
    })

    # Build complete pipeline
    pipeline = {
        "stages": pipeline_stages,
        "total_latency_ms": round(total_latency_ms, 2),
        "total_cost": round(cost_usd, 6)
    }

    result = {
        "answer": claude_response.strip(),
        "sources": [s.dict() for s in sources],
        "confidence": round(confidence, 3),
        "query_id": query_memory_id,  # Week 4 Task 2: For feedback tracking
        "response_source": response_source,  # Week 4 Task 2: claude (not from cache)
        "analytics": analytics.dict(),  # Week 4 Task 3: Detailed analytics trace
        "explanation": search_explanation,  # UniversalSearch ranking explanation (query_intent, source_distribution, diversity_applied)
        "pipeline": pipeline,  # Week 5 Task 1: Pipeline visibility (stages, latency, costs)
        "quality_validation": {  # Week 5 Task 1: Quality validation metadata
            "confidence_score": quality_result.confidence_score,
            "should_store": quality_result.should_store,
            "source_trust_score": quality_result.source_trust_score,
            "completeness_score": quality_result.completeness_score,
            "uncertainty_score": quality_result.uncertainty_score,
            "flagged_reason": quality_result.flagged_reason,
            "passed_threshold": quality_result.should_store
        },
        # AGENT TRANSPARENCY FIELDS (production-ready)
        "agent_used": "claude_sonnet",  # /ask endpoint always uses Claude Sonnet 4.5
        "intent_detected": search_explanation.get("query_intent", "unknown") if search_explanation else "unknown",  # Intent from UniversalSearch
        "cache_status": "fresh_generation"  # Fresh LLM generation (not from cache)
    }

    # Update query_history with successful result
    await update_query_history(
        query_id=query_memory_id,
        answer=result["answer"],
        response_source=response_source,
        confidence=result["confidence"],
        analytics=analytics
    )

    # Week 5 Task 1: Conditional caching based on quality score
    # Only cache high-quality responses (confidence >= 0.8) to prevent memory pollution
    if not request.conversation_history and quality_result.should_store:
        # Store in semantic cache (24h TTL, paraphrase matching)
        await semantic_cache.set(
            query=request.question,
            user_id=user_id,
            answer=result["answer"],
            sources=[s.memory_id for s in sources],  # Store memory IDs
            confidence=result["confidence"],
            cost_usd=cost_usd
        )
        logger.info(f"[{query_memory_id}] ✅ Response cached (quality_score={quality_result.confidence_score:.3f})")

        # WEEK 6 DAY 1: Q&A pollution code REMOVED
        # Old code stored Q&A pairs as LONG-tier memories, causing pollution
        # Dec 2025: Unified architecture - ACMS_Raw_v1 + ACMS_Knowledge_v2 only
        # ACMS_Enriched_v1 cache layer removed (merged into ACMS_Raw_v1)
        # KnowledgeExtractor extracts intent/entities/facts to ACMS_Knowledge_v2

    elif not request.conversation_history and not quality_result.should_store:
        logger.warning(f"[{query_memory_id}] ❌ Cache skipped due to low quality (score={quality_result.confidence_score:.3f} < 0.8)")
        logger.warning(f"[{query_memory_id}] ❌ Memory storage skipped - Quality gate protection active")

    return AskResponse(**result)


# Week 4 Task 2: Feedback System Endpoints
@app.post("/feedback", response_model=dict)
async def submit_feedback(request: FeedbackRequest):
    """Submit user feedback on answer quality (Week 4 Task 2).

    This is CRITICAL for enterprise intelligence:
    - Negative feedback → productivity_blocker signal
    - Regenerate → cache quality issue
    - Positive feedback (rating ≥4) → promote Q&A to knowledge base

    NEW (Query History Separation):
    - Verifies query exists in query_history table (not memory_items)
    - Promotes high-quality Q&As (rating ≥4 + thumbs_up) to knowledge base as memory_type='qa_pair'
    """
    user_id = await get_or_create_default_user()

    from src.storage.database import get_session
    from src.storage.models import QueryFeedback
    from sqlalchemy import text

    async with get_session() as session:
        # 1. Verify query exists in query_history table AND belongs to current user
        result = await session.execute(
            text("SELECT question, answer, confidence, response_source FROM query_history WHERE query_id = :query_id AND user_id = :user_id"),
            {"query_id": request.query_id, "user_id": user_id}
        )
        query_row = result.fetchone()

        if not query_row:
            raise HTTPException(status_code=404, detail="Query not found or access denied")

        question, answer, confidence, db_response_source = query_row[0], query_row[1], query_row[2], query_row[3]

        # Use response_source from query_history if not provided in request
        response_source = request.response_source if request.response_source else db_response_source

        # 2. Insert feedback
        feedback = QueryFeedback(
            query_id=request.query_id,
            user_id=user_id,
            rating=request.rating,
            feedback_type=request.feedback_type,
            response_source=response_source,
            comment=request.comment
        )
        session.add(feedback)
        await session.flush()

        # 3. Promotion logic: thumbs_up with rating ≥4 promotes to knowledge base
        promoted = False
        if request.feedback_type == "thumbs_up" and request.rating >= 4:
            # Check if already promoted (user_id already verified above)
            check_result = await session.execute(
                text("SELECT promoted_to_kb FROM query_history WHERE query_id = :query_id AND user_id = :user_id"),
                {"query_id": request.query_id, "user_id": user_id}
            )
            already_promoted = check_result.fetchone()[0]

            if not already_promoted:
                # Promote to knowledge base as memory_type='qa_pair'
                # Use crud.create_memory() to properly handle vector embeddings
                qa_content = f"Q: {question}\n\nA: {answer}"

                # Close current session before calling crud (it manages its own session)
                await session.commit()

                # Create memory using CRUD (handles embeddings, deduplication, etc.)
                promoted_memory_id = await crud.create_memory(
                    user_id=user_id,
                    content=qa_content,
                    tags=["promoted_qa", "high_quality"],
                    tier="SHORT",
                    phase="promoted_qa",
                    privacy_level="PUBLIC",
                    metadata={
                        "source": "query_history_promotion",
                        "original_query_id": request.query_id,
                        "rating": request.rating,
                        "confidence": confidence,
                        "promoted_at": datetime.utcnow().isoformat(),
                        "memory_type": "qa_pair"  # Store in metadata since we can't override model field
                    }
                )

                if promoted_memory_id:
                    # Update memory_type to qa_pair (requires separate update after creation)
                    async with get_session() as update_session:
                        await update_session.execute(
                            text("UPDATE memory_items SET memory_type = 'qa_pair' WHERE memory_id = :memory_id"),
                            {"memory_id": promoted_memory_id}
                        )

                        # Mark query as promoted in query_history
                        await update_session.execute(
                            text("""
                                UPDATE query_history
                                SET promoted_to_kb = TRUE, promoted_at = NOW()
                                WHERE query_id = :query_id
                            """),
                            {"query_id": request.query_id}
                        )

                        await update_session.commit()

                    promoted = True
                    logger.info(f"✅ Promoted Q&A to knowledge base: {request.query_id} → {promoted_memory_id}")
                else:
                    logger.warning(f"⚠️ Promotion failed (duplicate or error): {request.query_id}")

        await session.commit()

    feedback_msg = f"✅ Feedback recorded: {request.feedback_type} (rating: {request.rating}) for query {request.query_id}"
    if promoted:
        feedback_msg += " + PROMOTED to knowledge base 🎉"

    print(feedback_msg)

    return {
        "status": "success",
        "feedback_id": str(feedback.feedback_id),
        "promoted": promoted,
        "message": "High-quality Q&A promoted to knowledge base!" if promoted else "Feedback recorded"
    }


@app.get("/feedback/summary/{query_id}", response_model=FeedbackStats)
async def get_feedback_summary(query_id: str):
    """Get aggregated feedback statistics for a query from query_history."""
    user_id = await get_or_create_default_user()

    from src.storage.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        # Verify query exists in query_history AND belongs to current user
        check_result = await session.execute(
            text("SELECT query_id FROM query_history WHERE query_id = :query_id AND user_id = :user_id"),
            {"query_id": query_id, "user_id": user_id}
        )

        if not check_result.fetchone():
            raise HTTPException(status_code=404, detail="Query not found or access denied")

        # Calculate feedback statistics from query_feedback table
        result = await session.execute(
            text("""
                SELECT
                    COUNT(*) as total,
                    AVG(rating) as avg_rating,
                    SUM(CASE WHEN feedback_type = 'thumbs_up' THEN 1 ELSE 0 END) as thumbs_up,
                    SUM(CASE WHEN feedback_type = 'thumbs_down' THEN 1 ELSE 0 END) as thumbs_down,
                    SUM(CASE WHEN feedback_type = 'regenerate' THEN 1 ELSE 0 END) as regenerates
                FROM query_feedback
                WHERE query_id = :query_id
            """),
            {"query_id": query_id}
        )

        row = result.fetchone()

        if not row or row[0] == 0:
            return FeedbackStats(
                query_id=query_id,
                total_ratings=0,
                avg_rating=0.0,
                thumbs_up=0,
                thumbs_down=0,
                regenerates=0
            )

        # Unpack columns from SELECT query
        total, avg_rating, thumbs_up, thumbs_down, regenerates = row

        return FeedbackStats(
            query_id=query_id,
            total_ratings=total,
            avg_rating=float(avg_rating) if avg_rating else 0.0,
            thumbs_up=thumbs_up if thumbs_up else 0,
            thumbs_down=thumbs_down if thumbs_down else 0,
            regenerates=regenerates if regenerates else 0
        )


@app.get("/feedback/user/{user_id}")
async def get_user_feedback_stats(user_id: str, days: int = Query(default=30, ge=1, le=365)):
    """Get user's feedback statistics by response source (for auto-tuning).

    Returns breakdown by response source:
    - Cache vs Claude ratings
    - Regenerate rate
    - Used by auto-tuner to adjust behavior
    """
    # Handle 'default' user_id by resolving to actual UUID
    if user_id == "default":
        user_id = await get_or_create_default_user()

    from src.storage.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text(f"""
                SELECT
                    response_source,
                    AVG(rating) as avg_rating,
                    COUNT(*) as count,
                    SUM(CASE WHEN feedback_type = 'regenerate' THEN 1 ELSE 0 END) as regenerates
                FROM query_feedback
                WHERE user_id = :user_id
                    AND created_at > NOW() - INTERVAL '{days} days'
                GROUP BY response_source
            """),
            {"user_id": user_id}
        )

        stats = []
        for row in result:
            stats.append({
                "response_source": row[0],
                "avg_rating": float(row[1]) if row[1] else 0.0,
                "count": row[2],
                "regenerates": row[3]
            })

        return {
            "user_id": user_id,
            "time_period_days": days,
            "sources": stats
        }


# Week 4 Task 3: Individual Metrics Dashboard Analytics
@app.get("/analytics/dashboard")
async def get_analytics_dashboard(
    user_id: str = Query(..., description="User ID to get analytics for"),
    days: int = Query(default=30, ge=1, le=365, description="Time period in days"),
    recent_limit: int = Query(default=20, ge=1, le=100, description="Number of recent queries to return")
):
    """Comprehensive analytics dashboard endpoint (Week 4 Task 3).

    Aggregates metrics for Individual Metrics Dashboard:
    - Cache performance (hit rate, cost savings)
    - Source performance (Claude vs ChatGPT vs Gemini)
    - User satisfaction (avg rating, thumbs up/down percentages)
    - Recent queries with feedback

    Used by desktop app dashboard UI.
    """
    # Handle 'default' user_id by resolving to actual UUID
    if user_id == "default":
        user_id = await get_or_create_default_user()

    from src.storage.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        # ============================================================
        # 1. CACHE PERFORMANCE METRICS
        # ============================================================
        cache_result = await session.execute(
            text(f"""
                SELECT
                    COUNT(*) as total_queries,
                    SUM(CASE WHEN response_source = 'cache' THEN 1 ELSE 0 END) as exact_cache_hits,
                    SUM(CASE WHEN response_source = 'semantic_cache' THEN 1 ELSE 0 END) as semantic_cache_hits,
                    AVG(CASE WHEN response_source IN ('cache', 'semantic_cache') THEN total_latency_ms ELSE NULL END) as avg_latency_cache_hit,
                    AVG(CASE WHEN response_source NOT IN ('cache', 'semantic_cache') THEN total_latency_ms ELSE NULL END) as avg_latency_cache_miss
                FROM query_history
                WHERE user_id = :user_id
                    AND created_at > NOW() - INTERVAL '{days} days'
            """),
            {"user_id": user_id}
        )
        cache_row = cache_result.fetchone()

        total_queries = cache_row[0] if cache_row[0] else 0
        exact_cache_hits = cache_row[1] if cache_row[1] else 0
        semantic_cache_hits = cache_row[2] if cache_row[2] else 0
        avg_latency_cache_hit = cache_row[3] if cache_row[3] else 0
        avg_latency_cache_miss = cache_row[4] if cache_row[4] else 0

        # Calculate hit rates
        if total_queries > 0:
            exact_hit_rate = (exact_cache_hits / total_queries)
            semantic_hit_rate = (semantic_cache_hits / total_queries)
            total_hit_rate = ((exact_cache_hits + semantic_cache_hits) / total_queries)
        else:
            exact_hit_rate = 0.0
            semantic_hit_rate = 0.0
            total_hit_rate = 0.0

        # Estimate cost savings (assuming $0.015 per Claude Sonnet 4.5 call)
        # Cache hits save the cost of an external API call
        cost_per_call = 0.015
        estimated_cost_savings = (exact_cache_hits + semantic_cache_hits) * cost_per_call

        cache_performance = {
            "total_queries": total_queries,
            "exact_cache_hits": exact_cache_hits,
            "semantic_cache_hits": semantic_cache_hits,
            "cache_hits": exact_cache_hits + semantic_cache_hits,  # For backward compatibility
            "exact_hit_rate": round(exact_hit_rate, 4),
            "semantic_hit_rate": round(semantic_hit_rate, 4),
            "total_hit_rate": round(total_hit_rate, 4),
            "cache_hit_rate": round(total_hit_rate * 100, 2),  # Percentage for backward compatibility
            "avg_latency_cache_hit_ms": round(float(avg_latency_cache_hit) if avg_latency_cache_hit else 0.0, 2),
            "avg_latency_cache_miss_ms": round(float(avg_latency_cache_miss) if avg_latency_cache_miss else 0.0, 2),
            "estimated_cost_savings_usd": round(estimated_cost_savings, 2)
        }

        # ============================================================
        # 2. SOURCE PERFORMANCE (AI Model Comparison)
        # ============================================================
        source_result = await session.execute(
            text(f"""
                SELECT
                    qf.response_source,
                    AVG(qf.rating) as avg_rating,
                    COUNT(qf.feedback_id) as total_feedback,
                    SUM(CASE WHEN qf.feedback_type = 'thumbs_up' THEN 1 ELSE 0 END) as thumbs_up,
                    SUM(CASE WHEN qf.feedback_type = 'thumbs_down' THEN 1 ELSE 0 END) as thumbs_down,
                    SUM(CASE WHEN qf.feedback_type = 'regenerate' THEN 1 ELSE 0 END) as regenerates
                FROM query_feedback qf
                JOIN query_history qh ON qf.query_id = qh.query_id
                WHERE qh.user_id = :user_id
                    AND qf.created_at > NOW() - INTERVAL '{days} days'
                GROUP BY qf.response_source
                ORDER BY avg_rating DESC
            """),
            {"user_id": user_id}
        )

        source_performance = []
        for row in source_result:
            source_name, avg_rating, total_feedback, thumbs_up, thumbs_down, regenerates = row
            regenerate_rate = (regenerates / total_feedback * 100) if total_feedback > 0 else 0.0

            source_performance.append({
                "source_name": source_name,
                "avg_rating": round(float(avg_rating) if avg_rating else 0.0, 2),
                "total_queries": total_feedback,
                "thumbs_up": thumbs_up if thumbs_up else 0,
                "thumbs_down": thumbs_down if thumbs_down else 0,
                "regenerate_rate": round(regenerate_rate, 2)
            })

        # ============================================================
        # 3. USER SATISFACTION (Overall Metrics)
        # ============================================================
        satisfaction_result = await session.execute(
            text(f"""
                SELECT
                    COUNT(qf.feedback_id) as total_feedback,
                    AVG(qf.rating) as avg_rating,
                    SUM(CASE WHEN qf.feedback_type = 'thumbs_up' THEN 1 ELSE 0 END) as thumbs_up,
                    SUM(CASE WHEN qf.feedback_type = 'thumbs_down' THEN 1 ELSE 0 END) as thumbs_down,
                    SUM(CASE WHEN qf.feedback_type = 'regenerate' THEN 1 ELSE 0 END) as regenerates
                FROM query_feedback qf
                JOIN query_history qh ON qf.query_id = qh.query_id
                WHERE qh.user_id = :user_id
                    AND qf.created_at > NOW() - INTERVAL '{days} days'
            """),
            {"user_id": user_id}
        )

        sat_row = satisfaction_result.fetchone()
        total_feedback = sat_row[0] if sat_row[0] else 0
        avg_rating = sat_row[1] if sat_row[1] else 0.0
        thumbs_up = sat_row[2] if sat_row[2] else 0
        thumbs_down = sat_row[3] if sat_row[3] else 0
        regenerates = sat_row[4] if sat_row[4] else 0

        # Calculate percentages
        thumbs_up_pct = (thumbs_up / total_feedback * 100) if total_feedback > 0 else 0.0
        thumbs_down_pct = (thumbs_down / total_feedback * 100) if total_feedback > 0 else 0.0
        regenerate_pct = (regenerates / total_feedback * 100) if total_feedback > 0 else 0.0

        user_satisfaction = {
            "total_feedback": total_feedback,
            "avg_rating": round(float(avg_rating), 2),
            "thumbs_up_percentage": round(thumbs_up_pct, 2),
            "thumbs_down_percentage": round(thumbs_down_pct, 2),
            "regenerate_percentage": round(regenerate_pct, 2)
        }

        # ============================================================
        # 4. RECENT QUERIES WITH FEEDBACK
        # ============================================================
        recent_result = await session.execute(
            text(f"""
                SELECT
                    qh.query_id,
                    qh.question,
                    qh.response_source,
                    qh.created_at,
                    qf.feedback_type,
                    qf.rating
                FROM query_history qh
                LEFT JOIN query_feedback qf ON qh.query_id = qf.query_id
                WHERE qh.user_id = :user_id
                    AND qh.created_at > NOW() - INTERVAL '{days} days'
                ORDER BY qh.created_at DESC
                LIMIT :limit
            """),
            {"user_id": user_id, "limit": recent_limit}
        )

        recent_queries = []
        for row in recent_result:
            query_id, question, response_source, created_at, feedback_type, rating = row
            recent_queries.append({
                "query_id": str(query_id),
                "question": question[:100] + "..." if len(question) > 100 else question,
                "response_source": response_source,
                "created_at": created_at.isoformat() if created_at else None,
                "feedback_type": feedback_type,
                "rating": rating
            })

        # ============================================================
        # RETURN COMPLETE DASHBOARD ANALYTICS
        # ============================================================
        return {
            "cache_performance": cache_performance,
            "source_performance": source_performance,
            "user_satisfaction": user_satisfaction,
            "recent_queries": recent_queries,
            "time_period_days": days
        }


@app.post("/gateway/ask")
async def gateway_ask(request: GatewayAskRequest):
    """AI Gateway endpoint with multi-agent routing, caching, and compliance.

    Workflow:
    1. Load Thread Context → Get conversation summary + recent turns (if conversation_id)
    2. Intent Detection → Classify query intent
    3. Cache Check → Redis query cache (1-hour TTL)
    4. Agent Selection → Cost-optimized routing
    5. Context Assembly → Retrieve relevant memories + thread context
    6. Compliance Check → Block sensitive data, warn dangerous commands
    7. Agent Execution → Stream response from selected agent
    8. Feedback Storage → Store query + response in conversation

    Returns:
        StreamingResponse: Server-Sent Events (SSE) stream
            - event: status (step updates)
            - event: chunk (response text chunks)
            - event: done (final GatewayResponse with conversation_id, turn_ids)
            - event: error (if failure)
    """
    from uuid import UUID

    # Use default user if not provided
    user_id = request.user_id
    if not user_id:
        user_id = await get_or_create_default_user()

    # Parse manual_agent if provided
    manual_agent_enum = None
    if request.manual_agent:
        try:
            manual_agent_enum = AgentType(request.manual_agent.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent: {request.manual_agent}. Must be one of: claude_sonnet, chatgpt, gemini, claude_code, ollama"
            )

    # Get ConversationMemoryManager
    conv_memory = get_conversation_memory_manager()
    tenant_id = request.tenant_id or "default"
    thread_context = None
    conversation_id = None

    # Load thread context if conversation_id provided
    if request.conversation_id:
        try:
            conv_uuid = UUID(request.conversation_id)
            ctx = await conv_memory.load_thread_context(tenant_id, conv_uuid)
            if ctx:
                conversation_id = conv_uuid
                thread_context = ThreadContext(
                    conversation_id=str(ctx.conversation_id),
                    tenant_id=ctx.tenant_id,
                    summary=ctx.summary,
                    entities=ctx.entities,
                    topic_stack=ctx.topic_stack,
                    recent_turns=ctx.recent_turns,
                    turn_count=ctx.turn_count
                )
                logger.info(f"[Gateway] Loaded thread context: {ctx.turn_count} turns, summary_len={len(ctx.summary)}")
        except Exception as ctx_error:
            logger.warning(f"[Gateway] Failed to load thread context: {ctx_error}")

    # Sprint 3 Day 15: Convert FileContext to FileContextModel if provided
    from src.gateway.models import FileContextModel
    file_context_model = None
    if request.file_context:
        file_context_model = FileContextModel(
            filename=request.file_context.filename,
            content=request.file_context.content
        )
        logger.info(f"[Gateway] File context included: {request.file_context.filename}")

    # Build GatewayRequest with thread context and file context
    gateway_request = GatewayRequest(
        query=request.query,
        user_id=user_id,
        tenant_id=tenant_id,
        manual_agent=manual_agent_enum,
        bypass_cache=request.bypass_cache,
        context_limit=request.context_limit,
        conversation_id=request.conversation_id,
        thread_context=thread_context,
        file_context=file_context_model,
        cross_source_enabled=request.cross_source_enabled
    )

    # Stream response using Server-Sent Events
    async def event_stream():
        """Generate SSE stream from gateway execution."""
        # Variables to capture response for conversation persistence
        full_text = ""
        final_response = None
        user_turn_id = None
        assistant_turn_id = None

        try:
            async for update in gateway.execute(gateway_request):
                event_type = update.get("type")

                if event_type == "status":
                    # Status update: {"step": "...", "message": "..."}
                    yield f"event: status\ndata: {json.dumps(update)}\n\n"

                elif event_type == "chunk":
                    # Response chunk: {"text": "..."}
                    # Capture text for conversation persistence
                    chunk_text = update.get("text", "")
                    full_text += chunk_text
                    yield f"event: chunk\ndata: {json.dumps(update)}\n\n"

                elif event_type == "done":
                    # Final response: {"response": GatewayResponse}
                    final_response = update.get("response", {})

                    # Save to conversation using ConversationMemoryManager
                    if conversation_id and final_response:
                        try:
                            # Generate client_message_id for idempotency
                            user_client_id = request.message_id
                            assistant_client_id = f"{request.message_id}_assistant" if request.message_id else None

                            # Save user turn (idempotent)
                            user_turn_id = await conv_memory.append_turn(
                                tenant_id=tenant_id,
                                conversation_id=conversation_id,
                                role="user",
                                content=request.query,
                                client_message_id=user_client_id,
                                metadata={}
                            )

                            # Save assistant turn (idempotent)
                            assistant_turn_id = await conv_memory.append_turn(
                                tenant_id=tenant_id,
                                conversation_id=conversation_id,
                                role="assistant",
                                content=full_text or final_response.get("answer", ""),
                                client_message_id=assistant_client_id,
                                metadata={
                                    "agent": final_response.get("agent_used", "unknown"),
                                    "from_cache": final_response.get("from_cache", False),
                                    "cost_usd": final_response.get("cost_usd", 0.0),
                                    "query_id": str(final_response.get("query_id", "")),
                                    "confidence": final_response.get("confidence", 0.0),
                                    "latency_ms": final_response.get("latency_ms", 0)
                                }
                            )

                            # Update summary if threshold reached
                            await conv_memory.update_summary_if_needed(tenant_id, conversation_id)

                            logger.info(
                                f"[Gateway] Saved turns to conversation {conversation_id}: "
                                f"user={user_turn_id}, assistant={assistant_turn_id}"
                            )

                        except Exception as save_error:
                            # Don't fail the request if save fails
                            logger.error(f"[Gateway] Failed to save turns to conversation: {save_error}")

                    # Add turn_ids to response
                    if user_turn_id or assistant_turn_id:
                        final_response["user_turn_id"] = str(user_turn_id) if user_turn_id else None
                        final_response["assistant_turn_id"] = str(assistant_turn_id) if assistant_turn_id else None
                    if conversation_id:
                        final_response["conversation_id"] = str(conversation_id)

                    yield f"event: done\ndata: {json.dumps(update)}\n\n"

                elif event_type == "error":
                    # Error: {"step": "...", "message": "...", "approved": false, "issues": [...]}
                    yield f"event: error\ndata: {json.dumps(update)}\n\n"

        except Exception as e:
            # Unexpected error
            error_data = {
                "type": "error",
                "message": f"Gateway error: {str(e)}",
                "step": "unknown"
            }
            yield f"event: error\ndata: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
    )


@app.post("/gateway/ask-sync")
async def gateway_ask_sync(request: GatewayAskRequest):
    """Synchronous JSON version of /gateway/ask for simple clients and testing.

    Same workflow as /gateway/ask but returns complete JSON response instead of SSE stream.
    Includes conversation continuity support (thread context, turn persistence).

    Returns:
        JSON response with agent transparency fields:
        - agent_used: Which AI agent handled the query
        - intent_detected: Detected query intent type
        - cache_status: Whether response was cached or freshly generated
        - conversation_id: ID of the conversation (if provided)
        - user_turn_id, assistant_turn_id: IDs of saved turns
    """
    from uuid import UUID

    # Use default user if not provided
    user_id = request.user_id
    if not user_id:
        user_id = await get_or_create_default_user()

    # Parse manual_agent if provided
    manual_agent_enum = None
    if request.manual_agent:
        try:
            manual_agent_enum = AgentType(request.manual_agent.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid agent: {request.manual_agent}. Must be one of: claude_sonnet, chatgpt, gemini, claude_code, ollama"
            )

    # Get ConversationMemoryManager for continuity
    conv_memory = get_conversation_memory_manager()
    tenant_id = request.tenant_id or "default"
    thread_context = None
    conversation_id = None

    # Load thread context if conversation_id provided
    if request.conversation_id:
        try:
            conv_uuid = UUID(request.conversation_id)
            ctx = await conv_memory.load_thread_context(tenant_id, conv_uuid)
            if ctx:
                conversation_id = conv_uuid
                thread_context = ThreadContext(
                    conversation_id=str(ctx.conversation_id),
                    tenant_id=ctx.tenant_id,
                    summary=ctx.summary,
                    entities=ctx.entities,
                    topic_stack=ctx.topic_stack,
                    recent_turns=ctx.recent_turns,
                    turn_count=ctx.turn_count
                )
                logger.info(f"[Gateway-Sync] Loaded thread context: {ctx.turn_count} turns")
        except Exception as ctx_error:
            logger.warning(f"[Gateway-Sync] Failed to load thread context: {ctx_error}")

    # Sprint 3 Day 15: Convert FileContext to FileContextModel if provided
    from src.gateway.models import FileContextModel
    file_context_model = None
    if request.file_context:
        file_context_model = FileContextModel(
            filename=request.file_context.filename,
            content=request.file_context.content
        )
        logger.info(f"[Gateway-Sync] File context included: {request.file_context.filename}")

    # Build GatewayRequest with thread context and file context
    gateway_request = GatewayRequest(
        query=request.query,
        user_id=user_id,
        tenant_id=tenant_id,
        manual_agent=manual_agent_enum,
        bypass_cache=request.bypass_cache,
        context_limit=request.context_limit,
        conversation_id=request.conversation_id,
        thread_context=thread_context,
        file_context=file_context_model,
        cross_source_enabled=request.cross_source_enabled
    )

    # Execute gateway and collect stream
    answer_chunks = []
    gateway_response = None
    error_message = None
    user_turn_id = None
    assistant_turn_id = None

    try:
        async for update in gateway.execute(gateway_request):
            event_type = update.get("type")

            if event_type == "chunk":
                # Collect response chunks
                answer_chunks.append(update.get("text", ""))

            elif event_type == "done":
                # Extract final GatewayResponse
                gateway_response = update.get("response")

            elif event_type == "error":
                # Gateway error (e.g., compliance rejection)
                error_message = update.get("message", "Gateway execution failed")
                break

        # Handle errors
        if error_message:
            raise HTTPException(status_code=400, detail=error_message)

        if not gateway_response:
            raise HTTPException(status_code=500, detail="No response from gateway")

        full_answer = "".join(answer_chunks)

        # Save turns to conversation using ConversationMemoryManager
        if conversation_id and gateway_response:
            try:
                user_client_id = request.message_id
                assistant_client_id = f"{request.message_id}_assistant" if request.message_id else None

                user_turn_id = await conv_memory.append_turn(
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    role="user",
                    content=request.query,
                    client_message_id=user_client_id,
                    metadata={}
                )

                assistant_turn_id = await conv_memory.append_turn(
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_answer,
                    client_message_id=assistant_client_id,
                    metadata={
                        "agent": gateway_response.get("agent_used", "unknown"),
                        "from_cache": gateway_response.get("from_cache", False),
                        "cost_usd": gateway_response.get("cost_usd", 0.0),
                        "confidence": gateway_response.get("confidence", 0.0)
                    }
                )

                await conv_memory.update_summary_if_needed(tenant_id, conversation_id)

                logger.info(
                    f"[Gateway-Sync] Saved turns to conversation {conversation_id}: "
                    f"user={user_turn_id}, assistant={assistant_turn_id}"
                )
            except Exception as save_error:
                logger.error(f"[Gateway-Sync] Failed to save turns: {save_error}")

        # Build JSON response with transparency fields
        response = {
            "answer": full_answer,
            "query_id": str(uuid4()),
            "sources": gateway_response.get("sources", []),
            "cross_source_citations": gateway_response.get("cross_source_citations", []),  # Phase 1.5 citations
            "confidence": gateway_response.get("confidence", 0.9),

            # AGENT TRANSPARENCY FIELDS
            "agent_used": gateway_response["agent_used"],
            "intent_detected": gateway_response["intent_detected"],
            "cache_status": "cache_hit" if gateway_response.get("from_cache", False) else "fresh_generation",

            # Cache metrics
            "from_cache": gateway_response.get("from_cache", False),
            "cache_similarity": gateway_response.get("cache_similarity"),

            # Performance metrics
            "cost_usd": gateway_response.get("cost_usd", 0.0),
            "latency_ms": gateway_response.get("latency_ms", 0)
        }

        # Add conversation continuity fields if applicable
        if conversation_id:
            response["conversation_id"] = str(conversation_id)
        if user_turn_id:
            response["user_turn_id"] = str(user_turn_id)
        if assistant_turn_id:
            response["assistant_turn_id"] = str(assistant_turn_id)

        return response

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Unexpected error
        logger.error(f"[GATEWAY-SYNC] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Gateway error: {str(e)}")


# =============================================================================
# FILE UPLOAD ENDPOINT (Sprint 3 Day 13)
# =============================================================================

# Import file upload utilities from gateway module
from src.gateway.file_upload import (
    ALLOWED_FILE_TYPES,
    MAX_FILE_SIZE,
    extract_text_from_file,
    validate_file_type,
    validate_file_size,
    get_invalid_type_error,
    get_file_too_large_error,
)


class FileUploadResponse(BaseModel):
    """Response for file upload."""
    success: bool
    memory_id: Optional[str] = None
    filename: str
    content_type: str
    size_bytes: int
    extracted_text: Optional[str] = None
    message: str


@app.post("/gateway/upload", response_model=FileUploadResponse, tags=["Gateway"])
async def upload_file(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    privacy_level: str = Form("INTERNAL"),
    save_to_memory: bool = Form(True),
    conversation_id: Optional[str] = Form(None)
):
    """Upload a file and optionally store it as a memory.

    Sprint 3 Day 13: File Upload capability

    Supports:
    - Text files (.txt, .md)
    - PDF files (.pdf)
    - Images (.png, .jpg, .gif, .webp)
    - JSON files (.json)

    Args:
        file: File to upload
        user_id: User ID (optional, uses default if not provided)
        privacy_level: Privacy level for stored memory (PUBLIC, INTERNAL, CONFIDENTIAL, LOCAL_ONLY)
        save_to_memory: Whether to save extracted content as memory
        conversation_id: Optional conversation to associate with

    Returns:
        Upload result with memory ID if saved
    """
    # Validate content type
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_FILE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed types: {list(ALLOWED_FILE_TYPES.keys())}"
        )

    # Read file content
    content = await file.read()
    size_bytes = len(content)

    # Check file size
    if size_bytes > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )

    filename = file.filename or "unnamed_file"
    logger.info(f"[UPLOAD] Received file: {filename} ({content_type}, {size_bytes} bytes)")

    # Extract text content
    extracted_text = await extract_text_from_file(content, content_type, filename)

    memory_id = None

    # Save to memory if requested
    if save_to_memory and extracted_text:
        try:
            # Get user ID - always resolve to UUID
            # user_id from API could be email, "default", or UUID - resolve to actual UUID
            resolved_user_id = await get_or_create_default_user()

            # Create memory content
            memory_content = f"[Uploaded File: {filename}]\n\n{extracted_text}"

            # Store as memory
            from uuid import uuid4
            memory_id = str(uuid4())

            # Use memory CRUD to store
            result = await crud.create_memory(
                user_id=resolved_user_id,
                content=memory_content[:10000],  # Limit content length
                source="file_upload",
                privacy_level=privacy_level,
                tags=[f"file:{filename}", f"type:{content_type}"],
                auto_detect_privacy=False,  # Already specified
            )

            if result:
                memory_id = result  # create_memory returns string UUID directly

            logger.info(f"[UPLOAD] Saved to memory: {memory_id}")

        except Exception as e:
            logger.error(f"[UPLOAD] Failed to save to memory: {e}")
            # Continue - file was uploaded successfully even if memory save failed

    # Sprint 3 Day 15: Return full extracted text for ChatGPT-style file context
    # Cap at 100KB to prevent excessively large payloads
    MAX_EXTRACTED_TEXT = 100_000
    truncated = False
    if extracted_text and len(extracted_text) > MAX_EXTRACTED_TEXT:
        extracted_text = extracted_text[:MAX_EXTRACTED_TEXT]
        truncated = True
        logger.warning(f"[UPLOAD] Extracted text truncated from {size_bytes} to {MAX_EXTRACTED_TEXT} chars")

    # ──────────────────────────────────────────────────────────
    # AUDIT: Log file upload (INGRESS)
    # ──────────────────────────────────────────────────────────
    try:
        from src.audit.models import DataClassification
        audit = get_audit_logger()

        # Map privacy level string to DataClassification
        data_class_map = {
            "PUBLIC": DataClassification.PUBLIC,
            "INTERNAL": DataClassification.INTERNAL,
            "CONFIDENTIAL": DataClassification.CONFIDENTIAL,
            "LOCAL_ONLY": DataClassification.LOCAL_ONLY,
        }
        data_classification = data_class_map.get(privacy_level.upper(), DataClassification.INTERNAL)

        await audit.log_ingress(
            source="file",
            operation="upload",
            item_count=1,
            data_classification=data_classification,
            metadata={
                "filename": filename,
                "content_type": content_type,
                "size_bytes": size_bytes,
                "memory_id": memory_id,
                "extracted_chars": len(extracted_text) if extracted_text else 0,
                "truncated": truncated,
                "user_id": user_id
            }
        )
        logger.debug(f"[Audit] Logged file upload ingress: {filename}")
    except Exception as audit_error:
        # Don't fail the upload if audit logging fails
        logger.warning(f"[Audit] Failed to log file upload: {audit_error}")

    return FileUploadResponse(
        success=True,
        memory_id=memory_id,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        extracted_text=extracted_text,  # Full content for ChatGPT-style context
        message=f"File uploaded successfully{' and saved to memory' if memory_id else ''}{' (content truncated)' if truncated else ''}"
    )


@app.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics - caching currently disabled."""
    import os

    enable_semantic = os.getenv("ENABLE_SEMANTIC_CACHE", "false").lower() == "true"
    enable_redis = os.getenv("ENABLE_REDIS_CACHE", "false").lower() == "true"

    return {
        "caching_enabled": False,
        "semantic_cache": {
            "enabled": enable_semantic,
            "status": "Disabled to prevent cache pollution (wrong agents, stale data, quality issues)" if not enable_semantic else "Enabled"
        },
        "redis_cache": {
            "enabled": enable_redis,
            "status": "Disabled to prevent quality pollution (bad responses cached)" if not enable_redis else "Enabled"
        },
        "note": "All queries generate fresh responses for maximum correctness. Conversation history preserved in conversation_messages table."
    }


@app.post("/cache/clear")
async def clear_all_caches():
    """Clear both Redis query cache and Weaviate semantic cache.

    Use with caution - this clears ALL cached queries for ALL users.
    Requires manual invocation for safety.

    Returns:
        dict: Number of entries cleared from each cache
    """
    try:
        # Clear Redis query cache
        redis_cleared = query_cache.clear_all()

        # Clear semantic cache (Weaviate)
        # We'll need to add a method to semantic cache for this
        from src.storage.weaviate_client import WeaviateClient
        weaviate = WeaviateClient()

        # Count entries before deletion
        semantic_count_before = weaviate.count_vectors("QueryCache_v1")

        # Delete entire collection and recreate
        if weaviate.collection_exists("QueryCache_v1"):
            weaviate._client.collections.delete("QueryCache_v1")
            logger.warning("[CACHE] Deleted QueryCache_v1 collection")

        # Recreate collection (semantic_cache will auto-create on next use)
        semantic_cache._ensure_collection()

        logger.warning(
            f"[CACHE] Cleared all caches: "
            f"Redis={redis_cleared}, Semantic={semantic_count_before}"
        )

        return {
            "status": "success",
            "redis_entries_cleared": redis_cleared,
            "semantic_entries_cleared": semantic_count_before,
            "message": "All caches cleared successfully"
        }

    except Exception as e:
        logger.error(f"[CACHE] Error clearing caches: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear caches: {str(e)}")


@app.post("/cache/clear/semantic")
async def clear_semantic_cache():
    """Clear only the Weaviate semantic cache.

    This is useful when cache pollution occurs (wrong responses cached).
    Redis query cache remains intact.

    Returns:
        dict: Number of entries cleared
    """
    try:
        from src.storage.weaviate_client import WeaviateClient
        weaviate = WeaviateClient()

        # Count entries before deletion
        count_before = weaviate.count_vectors("QueryCache_v1")

        # Delete and recreate collection
        if weaviate.collection_exists("QueryCache_v1"):
            weaviate._client.collections.delete("QueryCache_v1")
            logger.warning("[CACHE] Deleted QueryCache_v1 collection")

        # Recreate collection
        semantic_cache._ensure_collection()

        logger.warning(f"[CACHE] Cleared semantic cache: {count_before} entries")

        return {
            "status": "success",
            "entries_cleared": count_before,
            "message": "Semantic cache cleared successfully"
        }

    except Exception as e:
        logger.error(f"[CACHE] Error clearing semantic cache: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to clear semantic cache: {str(e)}")


@app.get("/stats")
async def get_stats():
    """Get system statistics using efficient SQL aggregation."""
    from sqlalchemy import text
    from src.storage.database import get_session

    user_id = await get_or_create_default_user()

    stats = {
        "total": 0,
        "by_tier": {},
        "by_phase": {},
        "by_tag": {},
        "by_privacy": {},
        "by_source": {},
    }

    try:
        async with get_session() as session:
            # Total count
            result = await session.execute(text("""
                SELECT COUNT(*) FROM memory_items WHERE user_id = :user_id
            """), {"user_id": user_id})
            stats["total"] = result.scalar() or 0

            # By tier (using content_length_tier)
            result = await session.execute(text("""
                SELECT content_length_tier, COUNT(*) as count
                FROM memory_items
                WHERE user_id = :user_id
                GROUP BY content_length_tier
            """), {"user_id": user_id})
            for row in result.fetchall():
                tier = row[0] or "UNKNOWN"
                stats["by_tier"][tier] = row[1]

            # By phase
            result = await session.execute(text("""
                SELECT phase, COUNT(*) as count
                FROM memory_items
                WHERE user_id = :user_id
                GROUP BY phase
            """), {"user_id": user_id})
            for row in result.fetchall():
                phase = row[0] or "None"
                stats["by_phase"][phase] = row[1]

            # By privacy level
            result = await session.execute(text("""
                SELECT privacy_level, COUNT(*) as count
                FROM memory_items
                WHERE user_id = :user_id
                GROUP BY privacy_level
            """), {"user_id": user_id})
            for row in result.fetchall():
                privacy = row[0] or "UNKNOWN"
                stats["by_privacy"][privacy] = row[1]

            # By source (from metadata_json->>'source')
            result = await session.execute(text("""
                SELECT
                    COALESCE(metadata_json->>'source', 'unknown') as source,
                    COUNT(*) as count
                FROM memory_items
                WHERE user_id = :user_id
                GROUP BY metadata_json->>'source'
            """), {"user_id": user_id})
            for row in result.fetchall():
                source = row[0] or "unknown"
                stats["by_source"][source] = row[1]

            # Top tags (unnest tags array and count)
            result = await session.execute(text("""
                SELECT tag, COUNT(*) as count
                FROM memory_items, unnest(tags) as tag
                WHERE user_id = :user_id
                GROUP BY tag
                ORDER BY count DESC
                LIMIT 10
            """), {"user_id": user_id})
            stats["top_tags"] = [{"tag": row[0], "count": row[1]} for row in result.fetchall()]

            # Build by_tag from top_tags for backward compatibility
            for item in stats["top_tags"]:
                stats["by_tag"][item["tag"]] = item["count"]

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        # Fall back to memory-based approach with higher limit
        all_memories = await crud.list_memories(user_id=user_id, limit=100000)
        stats["total"] = len(all_memories)

        for memory in all_memories:
            tier = memory.get("tier", "UNKNOWN")
            stats["by_tier"][tier] = stats["by_tier"].get(tier, 0) + 1

            phase = memory.get("phase") or "None"
            stats["by_phase"][phase] = stats["by_phase"].get(phase, 0) + 1

            privacy = memory.get("privacy_level", "UNKNOWN")
            stats["by_privacy"][privacy] = stats["by_privacy"].get(privacy, 0) + 1

            source = memory.get("metadata", {}).get("source", "unknown")
            stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

            for tag in memory.get("tags", []):
                stats["by_tag"][tag] = stats["by_tag"].get(tag, 0) + 1

        top_tags = sorted(stats["by_tag"].items(), key=lambda x: x[1], reverse=True)[:10]
        stats["top_tags"] = [{"tag": tag, "count": count} for tag, count in top_tags]

    return stats


# ============================================================================
# Conversation Thread Endpoints (ChatGPT/Claude/Gemini Import Support)
# ============================================================================

class ConversationTurnResponse(BaseModel):
    """Individual turn in a conversation."""
    turn_id: str
    turn_number: int
    role: str
    content: str
    created_at: str
    metadata: Optional[dict] = None


class ConversationThreadResponse(BaseModel):
    """Conversation thread with optional turns."""
    thread_id: str
    source: str
    title: str
    original_thread_id: Optional[str] = None
    created_at: str
    imported_at: str
    turn_count: int
    turns: Optional[List[ConversationTurnResponse]] = None
    metadata: Optional[dict] = None


class ChatGPTImportRequest(BaseModel):
    """Request to import ChatGPT conversations from file."""
    file_content: str = Field(..., description="JSON content of ChatGPT export file")


@app.get("/conversations", response_model=List[ConversationThreadResponse])
async def list_conversation_threads(
    source: Optional[str] = Query(default=None, description="Filter by source (chatgpt, claude, gemini)"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    include_turns: bool = Query(default=False, description="Include all turns in response")
):
    """List imported conversation threads with optional filtering.

    Args:
        source: Filter by source platform (chatgpt, claude, gemini)
        limit: Maximum number of threads to return
        offset: Number of threads to skip
        include_turns: If true, include all turns for each thread

    Returns:
        List of conversation threads with metadata
    """
    user_id = await get_or_create_default_user()

    from src.storage.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        # Build query with optional source filter
        query = """
            SELECT
                thread_id, source, title, original_thread_id,
                created_at, imported_at, turn_count, metadata_json
            FROM conversation_threads
            WHERE user_id = :user_id
        """
        params = {"user_id": user_id, "limit": limit, "offset": offset}

        if source:
            query += " AND source = :source"
            params["source"] = source

        query += " ORDER BY imported_at DESC LIMIT :limit OFFSET :offset"

        result = await session.execute(text(query), params)
        threads = result.fetchall()

        response_threads = []
        for thread in threads:
            # metadata_json is already a dict (parsed by SQLAlchemy JSONB)
            metadata = thread[7] if isinstance(thread[7], dict) else (json.loads(thread[7]) if thread[7] else None)

            thread_data = ConversationThreadResponse(
                thread_id=str(thread[0]),
                source=thread[1],
                title=thread[2],
                original_thread_id=thread[3],
                created_at=thread[4].isoformat() if thread[4] else None,
                imported_at=thread[5].isoformat() if thread[5] else None,
                turn_count=thread[6],
                metadata=metadata
            )

            # Optionally fetch turns
            if include_turns:
                turns_result = await session.execute(
                    text("""
                        SELECT turn_id, turn_number, role, content, created_at, metadata_json
                        FROM conversation_turns
                        WHERE thread_id = :thread_id
                        ORDER BY turn_number
                    """),
                    {"thread_id": str(thread[0])}
                )
                turns = turns_result.fetchall()

                thread_data.turns = [
                    ConversationTurnResponse(
                        turn_id=str(turn[0]),
                        turn_number=turn[1],
                        role=turn[2],
                        content=turn[3],
                        created_at=turn[4].isoformat() if turn[4] else None,
                        metadata=turn[5] if isinstance(turn[5], dict) else (json.loads(turn[5]) if turn[5] else None)
                    )
                    for turn in turns
                ]

            response_threads.append(thread_data)

    return response_threads


@app.get("/conversations/{thread_id}", response_model=ConversationThreadResponse)
async def get_conversation_thread(thread_id: str):
    """Get a specific conversation thread with all turns.

    Args:
        thread_id: UUID of the conversation thread

    Returns:
        Conversation thread with all turns included
    """
    user_id = await get_or_create_default_user()

    from src.storage.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        # Get thread
        thread_result = await session.execute(
            text("""
                SELECT
                    thread_id, source, title, original_thread_id,
                    created_at, imported_at, turn_count, metadata_json
                FROM conversation_threads
                WHERE thread_id = :thread_id AND user_id = :user_id
            """),
            {"thread_id": thread_id, "user_id": user_id}
        )
        thread = thread_result.fetchone()

        if not thread:
            raise HTTPException(status_code=404, detail="Conversation thread not found")

        # Get turns
        turns_result = await session.execute(
            text("""
                SELECT turn_id, turn_number, role, content, created_at, metadata_json
                FROM conversation_turns
                WHERE thread_id = :thread_id
                ORDER BY turn_number
            """),
            {"thread_id": thread_id}
        )
        turns = turns_result.fetchall()

        # metadata_json is already a dict (parsed by SQLAlchemy JSONB)
        thread_metadata = thread[7] if isinstance(thread[7], dict) else (json.loads(thread[7]) if thread[7] else None)

        return ConversationThreadResponse(
            thread_id=str(thread[0]),
            source=thread[1],
            title=thread[2],
            original_thread_id=thread[3],
            created_at=thread[4].isoformat() if thread[4] else None,
            imported_at=thread[5].isoformat() if thread[5] else None,
            turn_count=thread[6],
            metadata=thread_metadata,
            turns=[
                ConversationTurnResponse(
                    turn_id=str(turn[0]),
                    turn_number=turn[1],
                    role=turn[2],
                    content=turn[3],
                    created_at=turn[4].isoformat() if turn[4] else None,
                    metadata=turn[5] if isinstance(turn[5], dict) else (json.loads(turn[5]) if turn[5] else None)
                )
                for turn in turns
            ]
        )


@app.post("/import/chatgpt")
async def import_chatgpt_conversations(request: ChatGPTImportRequest):
    """Import ChatGPT conversations from JSON export.

    Args:
        request: Contains JSON content of ChatGPT export file

    Returns:
        Import statistics (conversations_imported, turns_created, errors)
    """
    user_id = await get_or_create_default_user()

    import tempfile
    import os
    from src.importers.chatgpt_importer import ChatGPTImporter

    # Write JSON content to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        f.write(request.file_content)
        temp_path = f.name

    try:
        # Initialize and run importer
        importer = ChatGPTImporter()
        await importer.initialize()

        result = await importer.import_conversations(temp_path, user_id=user_id)

        return {
            "status": "success",
            "conversations_imported": result["conversations_imported"],
            "turns_created": result["turns_created"],
            "errors": result["errors"]
        }

    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    finally:
        # Cleanup temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


# ============================================================================
# PII DETECTION & COMPLIANCE ENDPOINTS (WEEK 6 TASK 2)
# ============================================================================

@app.post("/compliance/scan/memories")
async def scan_memories_for_pii(limit: Optional[int] = Query(None, description="Max items to scan (None = all)")):
    """
    Scan memory_items table for PII

    Returns scan statistics and PII breakdown by type.
    """
    try:
        db_pool = await get_db_pool()
        scanner = PIIScanner(db_pool)

        result = await scanner.scan_memory_items(limit=limit)

        return {
            "status": "success",
            "scan_results": result
        }

    except Exception as e:
        logger.error(f"PII scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@app.post("/compliance/scan/queries")
async def scan_queries_for_pii(limit: Optional[int] = Query(None, description="Max queries to scan (None = all)")):
    """
    Scan query_logs table for PII

    Returns scan statistics and PII breakdown by type.
    """
    try:
        db_pool = await get_db_pool()
        scanner = PIIScanner(db_pool)

        result = await scanner.scan_query_logs(limit=limit)

        return {
            "status": "success",
            "scan_results": result
        }

    except Exception as e:
        logger.error(f"PII scan failed: {e}")
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@app.get("/compliance/pii/summary")
async def get_pii_summary():
    """
    Get summary of PII detections across all tables

    Returns breakdown by PII type and table.
    """
    try:
        db_pool = await get_db_pool()

        async with db_pool.acquire() as conn:
            # Get counts by PII type
            type_counts = await conn.fetch("""
                SELECT pii_type, COUNT(*) as count
                FROM pii_detection_log
                GROUP BY pii_type
                ORDER BY count DESC
            """)

            # Get counts by table
            table_counts = await conn.fetch("""
                SELECT table_name, COUNT(*) as count
                FROM pii_detection_log
                GROUP BY table_name
                ORDER BY count DESC
            """)

            # Get recent detections
            recent = await conn.fetch("""
                SELECT table_name, pii_type, detected_at
                FROM pii_detection_log
                ORDER BY detected_at DESC
                LIMIT 10
            """)

            return {
                "status": "success",
                "summary": {
                    "by_type": [dict(row) for row in type_counts],
                    "by_table": [dict(row) for row in table_counts],
                    "recent_detections": [
                        {
                            "table": row["table_name"],
                            "pii_type": row["pii_type"],
                            "detected_at": row["detected_at"].isoformat()
                        }
                        for row in recent
                    ]
                }
            }

    except Exception as e:
        logger.error(f"PII summary failed: {e}")
        raise HTTPException(status_code=500, detail=f"Summary failed: {str(e)}")


# ============================================================================
# PATTERN DETECTION & INTELLIGENCE ENDPOINTS (WEEK 6 TASK 3)
# ============================================================================

@app.post("/intelligence/patterns/detect")
async def detect_organizational_patterns(
    lookback_days: int = Query(30, description="Days to analyze"),
    min_mentions: int = Query(5, description="Minimum frequency")
):
    """
    Detect recurring organizational patterns

    Uses TF-IDF + DBSCAN clustering to find:
    - Productivity blockers (mentioned multiple times with negative feedback)
    - Knowledge gaps (repeated questions)
    - Quality issues (recurring bugs/errors)
    - Innovation ideas (positive suggestions)

    Returns patterns sorted by priority with insights.
    """
    try:
        db_pool = await get_db_pool()
        detector = PatternDetector(db_pool)

        patterns = await detector.detect_patterns(
            lookback_days=lookback_days,
            min_mentions=min_mentions
        )

        # Generate insights for top patterns
        insight_generator = InsightGenerator()
        results = []

        for pattern in patterns[:10]:  # Top 10 patterns
            # Convert pattern to dict for insight generation
            pattern_dict = {
                'category': pattern.category.value,
                'description': pattern.description,
                'mentions': pattern.mentions,
                'negative_feedback_rate': pattern.negative_feedback_rate,
                'trend_30day': pattern.trend_30day,
                'estimated_impact': pattern.estimated_impact,
                'priority_score': pattern.priority_score,
                'memories': []  # Insight generator doesn't need full memories
            }

            insight = insight_generator.generate_insight(pattern_dict)

            results.append({
                'pattern': {
                    'id': pattern.pattern_id,
                    'category': pattern.category.value,
                    'description': pattern.description,
                    'mentions': pattern.mentions,
                    'memory_ids': pattern.memory_ids,
                    'negative_feedback_rate': pattern.negative_feedback_rate,
                    'trend_30day': pattern.trend_30day,
                    'priority_score': pattern.priority_score
                },
                'insight': insight
            })

        return {
            'status': 'success',
            'patterns_detected': len(patterns),
            'lookback_days': lookback_days,
            'results': results
        }

    except Exception as e:
        logger.error(f"Pattern detection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@app.get("/intelligence/patterns/summary")
async def get_pattern_summary():
    """
    Get summary of detected patterns

    Returns quick overview without full detection (cached from last run).
    """
    try:
        db_pool = await get_db_pool()

        # Get recent pattern counts by category (simplified version)
        async with db_pool.acquire() as conn:
            # Count memories with negative feedback
            blockers = await conn.fetchval("""
                SELECT COUNT(*)
                FROM memory_items
                WHERE created_at >= NOW() - INTERVAL '30 days'
                  AND (feedback_summary->>'thumbs_down')::int > 0
            """)

            # Count question-like memories
            gaps = await conn.fetchval("""
                SELECT COUNT(*)
                FROM memory_items
                WHERE created_at >= NOW() - INTERVAL '30 days'
                  AND content ILIKE '%?%'
            """)

            total_memories = await conn.fetchval("""
                SELECT COUNT(*)
                FROM memory_items
                WHERE created_at >= NOW() - INTERVAL '30 days'
            """)

            return {
                'status': 'success',
                'summary': {
                    'total_memories_analyzed': total_memories,
                    'potential_blockers': blockers,
                    'potential_knowledge_gaps': gaps,
                    'lookback_days': 30
                }
            }

    except Exception as e:
        logger.error(f"Pattern summary failed: {e}")
        raise HTTPException(status_code=500, detail=f"Summary failed: {str(e)}")


# ============================================================================
# WEEKLY REPORTING ENDPOINTS (WEEK 7 TASK 1)
# ============================================================================

@app.post("/reports/weekly/generate")
async def generate_weekly_report_endpoint(
    week_start: Optional[str] = Query(None, description="Week start date (YYYY-MM-DD), defaults to last Monday"),
    format: str = Query("json", description="Response format: json, html, or text")
):
    """
    Generate weekly enterprise intelligence report

    Generates comprehensive report with:
    - Executive summary with top patterns
    - Categorized insights (blockers, gaps, quality, ideas)
    - Performance metrics (cache hits, cost savings)
    - Week-over-week trend analysis
    - Actionable recommendations

    Returns report in JSON, HTML, or plain text format.
    """
    try:
        from datetime import datetime
        from src.reporting.weekly_report import WeeklyReportGenerator

        db_pool = await get_db_pool()
        generator = WeeklyReportGenerator(db_pool)

        # Parse week_start if provided
        week_start_date = None
        if week_start:
            try:
                week_start_date = datetime.strptime(week_start, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use YYYY-MM-DD (e.g., 2025-10-16)"
                )

        # Generate report
        report = await generator.generate_report(week_start=week_start_date)

        # Return in requested format
        if format == "html":
            html_content = generator.to_html(report)
            return Response(content=html_content, media_type="text/html")
        elif format == "text":
            text_content = generator.to_text(report)
            return Response(content=text_content, media_type="text/plain")
        else:  # json (default)
            return {
                "status": "success",
                "report": generator.to_dict(report)
            }

    except Exception as e:
        logger.error(f"Weekly report generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")


@app.get("/reports/weekly/latest")
async def get_latest_weekly_report(
    format: str = Query("json", description="Response format: json, html, or text")
):
    """
    Get most recent weekly report from database

    Returns the latest generated report without regenerating.
    Useful for quickly accessing the most recent insights.
    """
    try:
        db_pool = await get_db_pool()

        async with db_pool.acquire() as conn:
            # Get most recent report
            row = await conn.fetchrow("""
                SELECT report_id, generated_at, week_start, week_end,
                       executive_summary, report_data, total_impact_usd,
                       patterns_detected
                FROM enterprise_reports
                ORDER BY generated_at DESC
                LIMIT 1
            """)

            if not row:
                raise HTTPException(
                    status_code=404,
                    detail="No reports found. Generate a report first using /reports/weekly/generate"
                )

            # Return in requested format
            if format == "html":
                from src.reporting.weekly_report import WeeklyReport, WeeklyReportGenerator
                import json
                from dataclasses import asdict

                # Reconstruct report from stored data
                report_data = json.loads(row['report_data'])

                # Simple HTML response with key info
                html = f"""
                <html>
                <head><title>Latest Weekly Report</title></head>
                <body style="font-family: Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px;">
                    <h1>Latest Weekly Report</h1>
                    <p><strong>Week:</strong> {row['week_start']} to {row['week_end']}</p>
                    <p><strong>Generated:</strong> {row['generated_at']}</p>
                    <p><strong>Total Impact:</strong> ${row['total_impact_usd']:,.0f}/month</p>
                    <p><strong>Patterns Detected:</strong> {row['patterns_detected']}</p>
                    <hr>
                    <h2>Executive Summary</h2>
                    <pre style="white-space: pre-wrap;">{row['executive_summary']}</pre>
                    <hr>
                    <p><em>For full report, use format=json</em></p>
                </body>
                </html>
                """
                return Response(content=html, media_type="text/html")

            elif format == "text":
                text = f"""
LATEST WEEKLY REPORT
{'=' * 70}
Week: {row['week_start']} to {row['week_end']}
Generated: {row['generated_at']}
Total Impact: ${row['total_impact_usd']:,.0f}/month
Patterns Detected: {row['patterns_detected']}

EXECUTIVE SUMMARY
{'-' * 70}
{row['executive_summary']}
{'=' * 70}
For full report, use format=json
                """
                return Response(content=text.strip(), media_type="text/plain")

            else:  # json (default)
                import json
                return {
                    "status": "success",
                    "report": {
                        "report_id": row['report_id'],
                        "generated_at": row['generated_at'].isoformat(),
                        "week_start": row['week_start'].isoformat(),
                        "week_end": row['week_end'].isoformat(),
                        "executive_summary": row['executive_summary'],
                        "total_impact_usd": row['total_impact_usd'],
                        "patterns_detected": row['patterns_detected'],
                        "full_data": json.loads(row['report_data'])
                    }
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve latest report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve report: {str(e)}")


@app.get("/reports/weekly/list")
async def list_weekly_reports(
    limit: int = Query(10, description="Number of reports to return")
):
    """
    List all weekly reports (most recent first)

    Returns summary of all generated reports for historical analysis.
    """
    try:
        db_pool = await get_db_pool()

        async with db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT report_id, generated_at, week_start, week_end,
                       total_impact_usd, patterns_detected
                FROM enterprise_reports
                ORDER BY generated_at DESC
                LIMIT $1
            """, limit)

            reports = []
            for row in rows:
                reports.append({
                    "report_id": row['report_id'],
                    "generated_at": row['generated_at'].isoformat(),
                    "week_start": row['week_start'].isoformat(),
                    "week_end": row['week_end'].isoformat(),
                    "total_impact_usd": row['total_impact_usd'],
                    "patterns_detected": row['patterns_detected']
                })

            return {
                "status": "success",
                "count": len(reports),
                "reports": reports
            }

    except Exception as e:
        logger.error(f"Failed to list reports: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list reports: {str(e)}")


# ============================================================================
# Unified Chat Interface Endpoints (Phase 1, Task 1.2)
# ============================================================================
# These endpoints are for LIVE conversations happening in the unified ACMS interface.
# Separate from /conversations (imported conversation threads from ChatGPT/Claude/Gemini).

from src.storage.conversation_crud import get_conversation_crud

# Initialize conversation CRUD
conversation_crud = get_conversation_crud()


class ChatConversationCreate(BaseModel):
    """Request to create new chat conversation."""
    user_id: str = Field(..., description="User ID")
    agent: str = Field(..., description="AI agent: claude, gpt, gemini, claude-code")
    title: Optional[str] = Field(None, description="Optional title (auto-generated if None)")


class ChatConversationResponse(BaseModel):
    """Chat conversation response."""
    conversation_id: str
    user_id: str
    agent: str
    title: Optional[str]
    created_at: str
    updated_at: str
    message_count: Optional[int] = None


class ChatConversationListResponse(BaseModel):
    """List of chat conversations with grouping."""
    conversations: List[ChatConversationResponse]
    total_count: int
    groups: Optional[List[Dict[str, Any]]] = None


class ChatMessageCreate(BaseModel):
    """Request to send message in chat."""
    content: str = Field(..., min_length=1, description="Message content")
    user_id: str = Field(..., description="User ID")
    agent: Optional[str] = Field(None, description="Override agent for this message")


class ChatMessageResponse(BaseModel):
    """Chat message response."""
    message_id: str
    conversation_id: str
    role: str
    content: str
    message_metadata: Dict[str, Any]
    created_at: str


class ChatSendMessageResponse(BaseModel):
    """Response when sending a message."""
    user_message: ChatMessageResponse
    assistant_message: ChatMessageResponse
    metadata: Dict[str, Any]


@app.post("/chat/conversations", response_model=ChatConversationResponse, tags=["Unified Chat"])
async def create_chat_conversation(request: ChatConversationCreate):
    """Create new chat conversation.

    Args:
        request: ChatConversationCreate with user_id, agent, and optional title

    Returns:
        Created conversation

    Raises:
        HTTPException 404: If user not found
        HTTPException 422: If agent invalid
    """
    try:
        from uuid import UUID

        # Convert user_id string to UUID
        user_uuid = UUID(request.user_id)

        # Create conversation
        conversation = await conversation_crud.create_conversation(
            user_id=user_uuid,
            agent=request.agent,
            title=request.title
        )

        logger.info(f"[API] Created chat conversation {conversation.conversation_id} for user {user_uuid}")

        return ChatConversationResponse(
            conversation_id=str(conversation.conversation_id),
            user_id=str(conversation.user_id),
            agent=conversation.agent,
            title=conversation.title,
            created_at=conversation.created_at.isoformat(),
            updated_at=conversation.updated_at.isoformat(),
            message_count=0
        )

    except ValueError as e:
        if "User" in str(e) and "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        elif "Invalid agent" in str(e):
            raise HTTPException(status_code=422, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Failed to create chat conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {str(e)}")


@app.get("/chat/conversations", response_model=ChatConversationListResponse, tags=["Unified Chat"])
async def list_chat_conversations(
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(default=20, ge=1, le=100, description="Max conversations to return"),
    offset: int = Query(default=0, ge=0, description="Number of conversations to skip"),
    group_by_date: bool = Query(default=True, description="Group conversations by date")
):
    """List user's chat conversations with pagination and optional date grouping.

    Args:
        user_id: User ID
        limit: Max conversations to return
        offset: Number of conversations to skip
        group_by_date: If True, group conversations by Today/Yesterday/Older

    Returns:
        List of conversations with total count and optional groups
    """
    try:
        from uuid import UUID

        # Convert user_id string to UUID
        user_uuid = UUID(user_id)

        # Get conversations
        conversations, total_count = await conversation_crud.list_conversations(
            user_id=user_uuid,
            limit=limit,
            offset=offset
        )

        # Convert to response models
        conv_responses = [
            ChatConversationResponse(
                conversation_id=str(conv.conversation_id),
                user_id=str(conv.user_id),
                agent=conv.agent,
                title=conv.title,
                created_at=conv.created_at.isoformat(),
                updated_at=conv.updated_at.isoformat()
            )
            for conv in conversations
        ]

        # Group by date if requested
        groups = None
        if group_by_date:
            grouped = await conversation_crud.group_conversations_by_date(conversations)
            groups = [
                {
                    "name": group_name,
                    "count": len(group_convs),
                    "conversation_ids": [str(c.conversation_id) for c in group_convs]
                }
                for group_name, group_convs in grouped.items()
            ]

        logger.info(f"[API] Listed {len(conversations)} chat conversations for user {user_uuid}")

        return ChatConversationListResponse(
            conversations=conv_responses,
            total_count=total_count,
            groups=groups
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Failed to list chat conversations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {str(e)}")


@app.get("/chat/conversations/{conversation_id}", tags=["Unified Chat"])
async def get_chat_conversation(conversation_id: str):
    """Get chat conversation with all messages.

    Args:
        conversation_id: Conversation ID

    Returns:
        Conversation with messages

    Raises:
        HTTPException 404: If conversation not found
    """
    try:
        from uuid import UUID

        # Convert conversation_id string to UUID
        conv_uuid = UUID(conversation_id)

        # Get conversation with messages
        conversation = await conversation_crud.get_conversation(
            conversation_id=conv_uuid,
            include_messages=True
        )

        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")

        # Convert to response
        messages = [
            ChatMessageResponse(
                message_id=str(msg.message_id),
                conversation_id=str(msg.conversation_id),
                role=msg.role,
                content=msg.content,
                message_metadata=msg.message_metadata,
                created_at=msg.created_at.isoformat()
            )
            for msg in conversation.messages
        ]

        logger.info(f"[API] Retrieved chat conversation {conversation_id} with {len(messages)} messages")

        return {
            "conversation": ChatConversationResponse(
                conversation_id=str(conversation.conversation_id),
                user_id=str(conversation.user_id),
                agent=conversation.agent,
                title=conversation.title,
                created_at=conversation.created_at.isoformat(),
                updated_at=conversation.updated_at.isoformat(),
                message_count=len(messages)
            ),
            "messages": messages
        }

    except ValueError as e:
        raise HTTPException(status_code=422, detail="Invalid conversation ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to get chat conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get conversation: {str(e)}")


@app.delete("/chat/conversations/{conversation_id}", tags=["Unified Chat"])
async def delete_chat_conversation(conversation_id: str):
    """Delete chat conversation and all its messages.

    Args:
        conversation_id: Conversation ID

    Returns:
        Success message

    Raises:
        HTTPException 404: If conversation not found
        HTTPException 422: If conversation ID is invalid
    """
    try:
        from uuid import UUID

        # Convert conversation_id string to UUID
        conv_uuid = UUID(conversation_id)

        # Delete conversation (cascade deletes messages)
        deleted = await conversation_crud.delete_conversation(conversation_id=conv_uuid)

        if not deleted:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")

        logger.info(f"[API] Deleted chat conversation {conversation_id}")

        return {
            "message": f"Conversation {conversation_id} deleted successfully",
            "conversation_id": conversation_id,
            "deleted": True
        }

    except ValueError as e:
        raise HTTPException(status_code=422, detail="Invalid conversation ID format")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to delete chat conversation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")


@app.post("/chat/conversations/{conversation_id}/messages", response_model=ChatSendMessageResponse, tags=["Unified Chat"])
async def send_chat_message(conversation_id: str, request: ChatMessageCreate):
    """Send message in chat conversation and get AI response.

    This endpoint:
    1. Adds user message to conversation
    2. Calls gateway orchestrator with full conversation history
    3. Adds AI response to conversation
    4. Returns both messages with metadata

    Args:
        conversation_id: Conversation ID
        request: ChatMessageCreate with content, user_id, and optional agent override

    Returns:
        Both user message and AI response with metadata

    Raises:
        HTTPException 404: If conversation not found
        HTTPException 422: If content is empty
    """
    try:
        from uuid import UUID
        import time

        # Convert IDs to UUIDs
        conv_uuid = UUID(conversation_id)
        user_uuid = UUID(request.user_id)

        # Verify conversation exists
        conversation = await conversation_crud.get_conversation(
            conversation_id=conv_uuid,
            include_messages=True
        )

        if not conversation:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")

        # Determine which agent to use
        agent = request.agent or conversation.agent

        # Add user message
        user_message = await conversation_crud.add_message(
            conversation_id=conv_uuid,
            role="user",
            content=request.content,
            metadata={"agent_requested": agent}
        )

        logger.info(f"[API] Added user message to conversation {conversation_id}")

        # Get conversation history for context (all previous messages)
        conversation_history = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in conversation.messages
        ]

        # Add current user message
        conversation_history.append({
            "role": "user",
            "content": request.content
        })

        # Call gateway orchestrator for AI response (streaming)
        start_time = time.time()

        # Map agent string to AgentType enum for gateway
        agent_mapping = {
            "claude": AgentType.CLAUDE_SONNET,
            "gpt": AgentType.CHATGPT,
            "gemini": AgentType.GEMINI,
            "claude-code": AgentType.CLAUDE_CODE
        }

        manual_agent = agent_mapping.get(agent) if request.agent else None

        gateway_request = GatewayRequest(
            query=request.content,
            user_id=str(user_uuid),
            manual_agent=manual_agent
        )

        # Collect streaming response from gateway
        ai_content = ""
        gateway_metadata = {}
        thinking_steps = []  # Collect thinking steps for transparency

        try:
            async for chunk in gateway.execute(gateway_request):
                chunk_type = chunk.get("type")

                if chunk_type == "chunk":
                    # Accumulate streaming response text
                    ai_content += chunk.get("text", "")

                elif chunk_type == "done":
                    # Extract final metadata from GatewayResponse
                    gateway_metadata = chunk.get("response", {})

                elif chunk_type == "status":
                    # Collect thinking steps for UI transparency display
                    thinking_steps.append({
                        "step": chunk.get("step"),
                        "message": chunk.get("message")
                    })

                elif chunk_type == "error":
                    # Handle compliance blocks and other errors
                    if not chunk.get("approved", True):
                        # Compliance blocked the query
                        issues = chunk.get("issues", [])
                        raise HTTPException(
                            status_code=403,
                            detail=f"Query blocked by compliance: {len(issues)} issues detected"
                        )
                    else:
                        # Other gateway error
                        error_msg = chunk.get("message", "Gateway error occurred")
                        raise HTTPException(status_code=500, detail=error_msg)

        except HTTPException:
            # Re-raise HTTP exceptions (compliance blocks, etc.)
            raise
        except Exception as e:
            logger.error(f"[API] Gateway execution failed: {e}")
            raise HTTPException(status_code=500, detail=f"AI request failed: {str(e)}")

        llm_latency_ms = (time.time() - start_time) * 1000

        # Map gateway metadata to message metadata format
        ai_metadata = {
            "agent": gateway_metadata.get("agent_used", agent),
            "model": gateway_metadata.get("agent_used", "unknown"),
            "cost": gateway_metadata.get("cost_usd", 0.0),
            "latency_ms": gateway_metadata.get("latency_ms", int(llm_latency_ms)),
            "from_cache": gateway_metadata.get("from_cache", False),
            "intent_detected": gateway_metadata.get("intent_detected", "unknown"),
            "thinking_steps": thinking_steps  # Include thinking steps for UI transparency
        }

        # Add AI response message
        assistant_message = await conversation_crud.add_message(
            conversation_id=conv_uuid,
            role="assistant",
            content=ai_content,
            metadata=ai_metadata
        )

        logger.info(f"[API] Added AI response to conversation {conversation_id} (agent: {agent})")

        # PHASE 2 FIX: Quality validation and memory storage for /chat endpoint
        # This unifies /ask and /chat through the same quality-gated pipeline
        try:
            # Prepare sources for quality validator (conversation context as source)
            quality_sources = [{
                "type": "conversation",
                "memory_id": str(conversation.conversation_id),
                "source_type": "conversation_thread"
            }]

            # Calculate quality score for the generated response
            quality_result = quality_validator.calculate_quality_score(
                response=ai_content.strip(),
                sources=quality_sources,
                query=request.content
            )

            logger.info(f"[API] Chat quality validation: confidence={quality_result.confidence_score:.3f}, should_store={quality_result.should_store}")

            # Save high-quality Q&As to permanent memory (Universal Brain)
            if quality_result.should_store:
                memory_id = await crud.create_memory(
                    user_id=str(user_uuid),
                    content=f"Q: {request.content}\n\nA: {ai_content}",
                    tags=["validated_qa", "chat_usage", "auto_saved"],
                    tier="LONG",
                    metadata={
                        "quality_score": quality_result.confidence_score,
                        "conversation_id": str(conversation.conversation_id),
                        "source": "chat_endpoint",
                        "agent_used": agent,
                        "from_cache": ai_metadata.get("from_cache", False)
                    }
                )
                logger.info(f"[API] 💾 Chat Q&A saved to permanent memory: {memory_id} (Universal Brain growing!)")
            else:
                logger.warning(f"[API] ❌ Chat memory storage skipped - Quality gate protection active (score={quality_result.confidence_score:.3f} < 0.8)")

        except Exception as e:
            # Log error but don't fail the request - user already has their response
            logger.error(f"[API] ⚠️  Failed to validate/store chat Q&A: {e}")

        # Return both messages
        return ChatSendMessageResponse(
            user_message=ChatMessageResponse(
                message_id=str(user_message.message_id),
                conversation_id=str(user_message.conversation_id),
                role=user_message.role,
                content=user_message.content,
                message_metadata=user_message.message_metadata,
                created_at=user_message.created_at.isoformat()
            ),
            assistant_message=ChatMessageResponse(
                message_id=str(assistant_message.message_id),
                conversation_id=str(assistant_message.conversation_id),
                role=assistant_message.role,
                content=assistant_message.content,
                message_metadata=assistant_message.message_metadata,
                created_at=assistant_message.created_at.isoformat()
            ),
            metadata={
                "total_messages": len(conversation.messages) + 2,
                "agent_used": agent,
                "latency_ms": llm_latency_ms
            }
        )

    except ValueError as e:
        if "not found" in str(e):
            raise HTTPException(status_code=404, detail=str(e))
        elif "empty" in str(e).lower():
            raise HTTPException(status_code=422, detail=str(e))
        else:
            raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Failed to send chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")
# ========================================
# WebSocket Endpoint for Real-Time Chat Streaming
# ========================================

@app.websocket("/ws/chat/{conversation_id}")
async def websocket_chat_endpoint(websocket: WebSocket, conversation_id: str):
    """WebSocket endpoint for real-time chat with thinking step streaming.

    This provides real-time updates during AI processing:
    - Status events for each pipeline step (7-step gateway orchestrator)
    - Streaming text chunks as they're generated
    - Final response with full metadata

    Frontend connects to: ws://localhost:40080/ws/chat/{conversation_id}
    """
    await websocket.accept()
    logger.info(f"[WebSocket] Client connected for conversation {conversation_id}")

    try:
        # Initialize conversation CRUD (handles its own connection)
        conversation_crud = get_conversation_crud()

        # Wait for incoming message from client
        data = await websocket.receive_json()
        content = data.get("content", "")
        agent = data.get("agent", "claude")  # Default to Claude
        user_id = data.get("user_id", "default-user")

        logger.info(f"[WebSocket] Received message for conversation {conversation_id}")

        # Validate conversation belongs to user
        conversation = await conversation_crud.get_conversation(conversation_id)
        if not conversation:
            await websocket.send_json({
                "type": "error",
                "message": f"Conversation {conversation_id} not found"
            })
            await websocket.close()
            return

        # Add user message to conversation
        user_message = await conversation_crud.add_message(
            conversation_id=conversation_id,
            role="user",
            content=content
        )

        # Send user message confirmation
        await websocket.send_json({
            "type": "message_added",
            "message": {
                "message_id": str(user_message.message_id),
                "role": "user",
                "content": content
            }
        })

        # Prepare gateway request
        gateway = get_gateway_orchestrator()
        start_time = time.time()

        agent_mapping = {
            "claude": AgentType.CLAUDE_SONNET,
            "gpt": AgentType.CHATGPT,
            "gemini": AgentType.GEMINI,
            "claude-code": AgentType.CLAUDE_CODE
        }
        manual_agent = agent_mapping.get(agent) if agent else None

        gateway_request = GatewayRequest(
            query=content,
            user_id=user_id,
            manual_agent=manual_agent
        )

        # Stream gateway execution with real-time status updates
        ai_content = ""
        gateway_metadata = {}
        thinking_steps = []

        try:
            async for chunk in gateway.execute(gateway_request):
                chunk_type = chunk.get("type")

                if chunk_type == "status":
                    # REAL-TIME STATUS STREAMING - This is the key fix!
                    step_event = {
                        "type": "status",
                        "step": chunk.get("step"),
                        "message": chunk.get("message")
                    }
                    thinking_steps.append(step_event)

                    # Send to frontend immediately
                    await websocket.send_json(step_event)
                    logger.info(f"[WebSocket] Sent status: {chunk.get('step')}")

                elif chunk_type == "chunk":
                    # Stream text chunks as they arrive
                    text = chunk.get("text", "")
                    ai_content += text
                    await websocket.send_json({
                        "type": "chunk",
                        "text": text
                    })

                elif chunk_type == "done":
                    # Final metadata from gateway
                    gateway_metadata = chunk.get("response", {})

                    # FOR CACHE HITS: Extract answer from metadata if ai_content is still empty
                    # (cache hits don't stream chunks, they return full answer in "done" event)
                    if not ai_content and gateway_metadata:
                        ai_content = gateway_metadata.get("answer", "")
                        # Stream the cached answer as a single chunk so UI sees it
                        if ai_content:
                            await websocket.send_json({
                                "type": "chunk",
                                "text": ai_content
                            })

                elif chunk_type == "error":
                    # Handle errors
                    if not chunk.get("approved", True):
                        issues = chunk.get("issues", [])
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Query blocked by compliance: {len(issues)} issues"
                        })
                        await websocket.close()
                        return
                    else:
                        error_msg = chunk.get("message", "Gateway error")
                        await websocket.send_json({
                            "type": "error",
                            "message": error_msg
                        })
                        await websocket.close()
                        return

        except Exception as e:
            logger.error(f"[WebSocket] Gateway execution failed: {e}")
            await websocket.send_json({
                "type": "error",
                "message": f"AI request failed: {str(e)}"
            })
            await websocket.close()
            return

        llm_latency_ms = (time.time() - start_time) * 1000

        # Prepare AI message metadata
        ai_metadata = {
            "agent": gateway_metadata.get("agent_used", agent),
            "model": gateway_metadata.get("agent_used", "unknown"),
            "cost": gateway_metadata.get("cost_usd", 0.0),
            "latency_ms": gateway_metadata.get("latency_ms", int(llm_latency_ms)),
            "from_cache": gateway_metadata.get("from_cache", False),
            "intent_detected": gateway_metadata.get("intent_detected", "unknown"),
            "thinking_steps": thinking_steps
        }

        # Save AI response to conversation
        assistant_message = await conversation_crud.add_message(
            conversation_id=conversation_id,
            role="assistant",
            content=ai_content,
            metadata=ai_metadata
        )

        # Send final done event with full message
        await websocket.send_json({
            "type": "done",
            "message": {
                "message_id": str(assistant_message.message_id),
                "role": "assistant",
                "content": ai_content,
                "metadata": ai_metadata
            }
        })

        logger.info(f"[WebSocket] Completed message stream for conversation {conversation_id}")

    except WebSocketDisconnect:
        logger.info(f"[WebSocket] Client disconnected from conversation {conversation_id}")
    except Exception as e:
        logger.error(f"[WebSocket] Error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": f"Server error: {str(e)}"
            })
        except:
            pass  # Client may have already disconnected
    finally:
        try:
            await websocket.close()
        except:
            pass  # Already closed


# ============================================================
# QUERY HISTORY ENDPOINT - View Raw Q&A Pairs
# ============================================================

class QueryHistoryItem(BaseModel):
    """Single Q&A pair from query history."""
    query_id: str
    question: str
    answer: Optional[str] = None
    response_source: Optional[str] = None
    topics: Optional[List[str]] = None
    primary_topic: Optional[str] = None
    created_at: str
    est_cost_usd: Optional[float] = None
    from_cache: Optional[bool] = None


class QueryHistoryResponse(BaseModel):
    """Paginated response for query history."""
    items: List[QueryHistoryItem]
    total: int
    page: int
    page_size: int
    has_more: bool


@app.get("/query-history", response_model=QueryHistoryResponse)
async def get_query_history(
    topic: Optional[str] = Query(None, description="Filter by topic (e.g., 'python', 'finance')"),
    source: Optional[str] = Query(None, description="Filter by response source (e.g., 'chatgpt', 'claude')"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=10, le=200, description="Items per page"),
    search: Optional[str] = Query(None, description="Search in question text")
):
    """
    Get raw Q&A pairs from query history with filtering and pagination.

    This endpoint allows viewing imported conversations (ChatGPT, Claude, etc.)
    and desktop queries with their extracted topics.

    Examples:
    - `/query-history?topic=python&source=chatgpt` - Python questions from ChatGPT
    - `/query-history?topic=finance&days=90` - Finance topics from last 90 days
    - `/query-history?search=kubernetes` - Search for kubernetes mentions
    """
    user_id = await get_or_create_default_user()

    from src.storage.database import get_session
    from sqlalchemy import text

    offset = (page - 1) * page_size

    async with get_session() as session:
        # Build dynamic WHERE clause
        where_clauses = ["qh.user_id = :user_id", f"qh.created_at > NOW() - INTERVAL '{days} days'"]
        params = {"user_id": user_id, "page_size": page_size, "offset": offset}

        if topic:
            where_clauses.append("te.primary_topic = :topic")
            params["topic"] = topic

        if source:
            where_clauses.append("qh.response_source = :source")
            params["source"] = source

        if search:
            where_clauses.append("qh.question ILIKE :search")
            params["search"] = f"%{search}%"

        where_sql = " AND ".join(where_clauses)

        # Get total count
        count_result = await session.execute(
            text(f"""
                SELECT COUNT(DISTINCT qh.query_id)
                FROM query_history qh
                LEFT JOIN topic_extractions te ON te.source_id = qh.query_id
                    AND te.source_type = 'query_history'
                WHERE {where_sql}
            """),
            params
        )
        total = count_result.scalar() or 0

        # Get paginated results
        result = await session.execute(
            text(f"""
                SELECT
                    qh.query_id,
                    qh.question,
                    qh.answer,
                    qh.response_source,
                    qh.created_at,
                    qh.est_cost_usd,
                    qh.from_cache,
                    te.topics,
                    te.primary_topic
                FROM query_history qh
                LEFT JOIN topic_extractions te ON te.source_id = qh.query_id
                    AND te.source_type = 'query_history'
                WHERE {where_sql}
                ORDER BY qh.created_at DESC
                LIMIT :page_size OFFSET :offset
            """),
            params
        )

        items = []
        for row in result:
            items.append(QueryHistoryItem(
                query_id=str(row[0]),
                question=row[1][:500] if row[1] else "",  # Truncate for listing
                answer=row[2][:500] if row[2] else None,   # Truncate for listing
                response_source=row[3],
                created_at=row[4].isoformat() if row[4] else "",
                est_cost_usd=float(row[5]) if row[5] else None,
                from_cache=row[6],
                topics=row[7] if row[7] else [],
                primary_topic=row[8]
            ))

        return QueryHistoryResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_more=(page * page_size) < total
        )


@app.get("/query-history/{query_id}")
async def get_query_detail(query_id: str):
    """
    Get full details of a single Q&A pair including complete question and answer.
    """
    user_id = await get_or_create_default_user()

    from src.storage.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text("""
                SELECT
                    qh.query_id,
                    qh.question,
                    qh.answer,
                    qh.response_source,
                    qh.created_at,
                    qh.est_cost_usd,
                    qh.from_cache,
                    qh.promoted_to_kb,
                    qh.conversation_id,
                    te.topics,
                    te.primary_topic,
                    te.confidence
                FROM query_history qh
                LEFT JOIN topic_extractions te ON te.source_id = qh.query_id
                    AND te.source_type = 'query_history'
                WHERE qh.query_id = :query_id AND qh.user_id = :user_id
            """),
            {"query_id": query_id, "user_id": user_id}
        )

        row = result.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Query not found")

        return {
            "query_id": str(row[0]),
            "question": row[1],
            "answer": row[2],
            "response_source": row[3],
            "created_at": row[4].isoformat() if row[4] else "",
            "est_cost_usd": float(row[5]) if row[5] else None,
            "from_cache": row[6],
            "promoted_to_kb": row[7],
            "conversation_id": str(row[8]) if row[8] else None,
            "topics": row[9] if row[9] else [],
            "primary_topic": row[10],
            "topic_confidence": float(row[11]) if row[11] else None
        }


@app.get("/query-history/topics/summary")
async def get_topic_summary(days: int = Query(30, ge=1, le=365)):
    """
    Get summary of all topics with counts for the specified time period.
    """
    user_id = await get_or_create_default_user()

    from src.storage.database import get_session
    from sqlalchemy import text

    async with get_session() as session:
        result = await session.execute(
            text(f"""
                SELECT
                    te.primary_topic,
                    COUNT(*) as count,
                    COUNT(DISTINCT qh.response_source) as source_count
                FROM topic_extractions te
                JOIN query_history qh ON qh.query_id = te.source_id
                    AND te.source_type = 'query_history'
                WHERE qh.user_id = :user_id
                    AND qh.created_at > NOW() - INTERVAL '{days} days'
                GROUP BY te.primary_topic
                ORDER BY count DESC
            """),
            {"user_id": user_id}
        )

        topics = []
        total = 0
        for row in result:
            count = row[1]
            total += count
            topics.append({
                "topic": row[0],
                "count": count,
                "sources": row[2]
            })

        return {
            "period_days": days,
            "total_queries": total,
            "topics": topics
        }


# ============================================================================
# KNOWLEDGE BASE ENDPOINTS (Dec 2025)
# ============================================================================
# View extracted knowledge from ACMS_Knowledge_v2 (via Claude Desktop MCP)

@app.get("/knowledge")
async def list_knowledge(
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    topic: Optional[str] = Query(None, description="Filter by topic cluster"),
    domain: Optional[str] = Query(None, description="Filter by problem domain"),
    search: Optional[str] = Query(None, description="Search in canonical_query")
):
    """
    List extracted knowledge from ACMS_Knowledge_v2.

    Knowledge is extracted from Q&A pairs via Claude Desktop MCP tools.
    Each item includes: intent, entities, topic cluster, related topics, key facts.
    """
    try:
        from src.storage.weaviate_client import WeaviateClient

        client = WeaviateClient()
        collection = client._client.collections.get("ACMS_Knowledge_v2")

        # Build filters
        filters = None
        if topic:
            from weaviate.classes.query import Filter
            filters = Filter.by_property("topic_cluster").equal(topic)
        elif domain:
            from weaviate.classes.query import Filter
            filters = Filter.by_property("problem_domain").equal(domain)

        # Query with filters
        if filters:
            results = collection.query.fetch_objects(
                limit=limit,
                offset=offset,
                filters=filters,
                include_vector=False
            )
        else:
            results = collection.query.fetch_objects(
                limit=limit,
                offset=offset,
                include_vector=False
            )

        # Format results
        knowledge_items = []
        for obj in results.objects:
            props = obj.properties
            item = {
                "id": str(obj.uuid),
                "canonical_query": props.get("canonical_query", ""),
                "answer_summary": props.get("answer_summary", ""),
                "primary_intent": props.get("primary_intent", ""),
                "problem_domain": props.get("problem_domain", ""),
                "topic_cluster": props.get("topic_cluster", ""),
                "related_topics": props.get("related_topics", []),
                "key_facts": props.get("key_facts", []),
                "extraction_confidence": props.get("extraction_confidence", 0),
                "created_at": props.get("created_at", ""),
                "usage_count": props.get("usage_count", 0)
            }

            # Apply search filter client-side if needed
            if search:
                if search.lower() not in item["canonical_query"].lower():
                    continue

            knowledge_items.append(item)

        # Get total count
        total_count = collection.aggregate.over_all(total_count=True).total_count

        client.close()

        return {
            "status": "success",
            "count": len(knowledge_items),
            "total": total_count,
            "offset": offset,
            "knowledge": knowledge_items
        }

    except Exception as e:
        logger.error(f"Failed to list knowledge: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list knowledge: {str(e)}")


@app.get("/knowledge/stats")
async def get_knowledge_stats():
    """
    Get statistics about extracted knowledge.
    """
    try:
        from src.storage.weaviate_client import WeaviateClient
        from collections import Counter

        client = WeaviateClient()
        collection = client._client.collections.get("ACMS_Knowledge_v2")

        # Get all items for aggregation
        results = collection.query.fetch_objects(limit=1000, include_vector=False)

        topic_counter = Counter()
        domain_counter = Counter()
        intent_counter = Counter()
        total_facts = 0

        for obj in results.objects:
            props = obj.properties
            if props.get("topic_cluster"):
                topic_counter[props["topic_cluster"]] += 1
            if props.get("problem_domain"):
                domain_counter[props["problem_domain"]] += 1
            if props.get("primary_intent"):
                # Extract just the intent type (first word or before colon)
                intent = props["primary_intent"].split()[0].lower() if props["primary_intent"] else "unknown"
                intent_counter[intent] += 1
            total_facts += len(props.get("key_facts", []))

        total_count = collection.aggregate.over_all(total_count=True).total_count

        client.close()

        return {
            "status": "success",
            "total_knowledge": total_count,
            "total_facts": total_facts,
            "top_topics": [{"topic": t, "count": c} for t, c in topic_counter.most_common(10)],
            "top_domains": [{"domain": d, "count": c} for d, c in domain_counter.most_common(10)],
            "by_intent": dict(intent_counter.most_common(10))
        }

    except Exception as e:
        logger.error(f"Failed to get knowledge stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge stats: {str(e)}")


# ============================================================
# EMAIL INSIGHTS ENDPOINTS
# ============================================================

@app.get("/email/insights")
async def get_email_insights(limit: int = 50, insight_type: str = None):
    """
    Get email insights for visualization in the UI.

    Returns:
    - Summary by insight type (action_item, deadline, topic, relationship)
    - Extraction method breakdown (rule_based vs llm)
    - Recent insights with details
    """
    try:
        from src.gateway.email_handler import EmailDataHandler

        handler = EmailDataHandler()
        insight_types = [insight_type] if insight_type else None
        data = await handler.get_email_insights(insight_types=insight_types, limit=limit)

        if "error" in data:
            raise HTTPException(status_code=500, detail=data["error"])

        return {
            "status": "success",
            **data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get email insights: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get email insights: {str(e)}")


@app.get("/email/stats")
async def get_email_stats():
    """
    Get email inbox statistics.

    Returns:
    - Total emails, unread count, starred, important
    - Priority unread count
    - Top senders
    """
    try:
        from src.gateway.email_handler import EmailDataHandler

        handler = EmailDataHandler()
        stats = await handler.get_inbox_stats()
        senders = await handler.get_top_senders(limit=10)

        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])

        return {
            "status": "success",
            "inbox_stats": stats,
            "top_senders": senders
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get email stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get email stats: {str(e)}")


@app.get("/email/priority")
async def get_emails_by_priority(limit: int = 30):
    """
    Get unread emails grouped by priority tier.

    Priority tiers:
    - High (60+): Important senders, frequent replies
    - Medium (30-59): Regular contacts
    - Low (0-29): Newsletters, bulk mail
    - Unscored: New senders
    """
    try:
        from src.gateway.email_handler import EmailDataHandler

        handler = EmailDataHandler()
        data = await handler.get_unread_by_priority(limit=limit)

        if "error" in data:
            raise HTTPException(status_code=500, detail=data["error"])

        return {
            "status": "success",
            **data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get emails by priority: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get emails by priority: {str(e)}")


@app.post("/api/gmail/sender/{sender_email}/vip")
async def mark_sender_vip(sender_email: str):
    """
    Mark a sender as VIP by boosting their importance score.

    This adds +40 points to their score, ensuring they reach "high" tier.
    Uses is_manually_prioritized flag to mark VIP status.
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Check if sender exists in sender_scores
            existing = await conn.fetchrow(
                "SELECT importance_score FROM sender_scores WHERE sender_email = $1",
                sender_email
            )

            if existing:
                # Boost existing score to VIP level (minimum 80)
                new_score = max(80, float(existing['importance_score']) + 40)
                await conn.execute(
                    """UPDATE sender_scores
                       SET importance_score = $1,
                           is_manually_prioritized = TRUE,
                           is_manually_deprioritized = FALSE,
                           updated_at = NOW()
                       WHERE sender_email = $2""",
                    new_score, sender_email
                )
            else:
                # Create new sender with VIP status
                # Extract domain from email
                domain = sender_email.split('@')[1] if '@' in sender_email else 'unknown'
                await conn.execute(
                    """INSERT INTO sender_scores
                       (sender_email, sender_domain, importance_score, is_manually_prioritized, created_at, updated_at)
                       VALUES ($1, $2, 80, TRUE, NOW(), NOW())""",
                    sender_email, domain
                )

            logger.info(f"Marked sender as VIP: {sender_email}")
            return {"status": "success", "message": f"Marked {sender_email} as VIP"}

    except Exception as e:
        logger.error(f"Failed to mark sender as VIP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to mark VIP: {str(e)}")


@app.post("/api/gmail/sender/{sender_email}/mute")
async def mute_sender(sender_email: str):
    """
    Mute a sender by setting their importance score to minimum.

    Muted senders will appear in the "low" tier.
    Uses is_manually_deprioritized flag to mark muted status.
    """
    try:
        pool = await get_db_pool()
        async with pool.acquire() as conn:
            # Check if sender exists
            existing = await conn.fetchrow(
                "SELECT importance_score FROM sender_scores WHERE sender_email = $1",
                sender_email
            )

            if existing:
                # Set score to 0 (muted)
                await conn.execute(
                    """UPDATE sender_scores
                       SET importance_score = 0,
                           is_manually_deprioritized = TRUE,
                           is_manually_prioritized = FALSE,
                           updated_at = NOW()
                       WHERE sender_email = $1""",
                    sender_email
                )
            else:
                # Create new sender as muted
                domain = sender_email.split('@')[1] if '@' in sender_email else 'unknown'
                await conn.execute(
                    """INSERT INTO sender_scores
                       (sender_email, sender_domain, importance_score, is_manually_deprioritized, created_at, updated_at)
                       VALUES ($1, $2, 0, TRUE, NOW(), NOW())""",
                    sender_email, domain
                )

            logger.info(f"Muted sender: {sender_email}")
            return {"status": "success", "message": f"Muted {sender_email}"}

    except Exception as e:
        logger.error(f"Failed to mute sender: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to mute sender: {str(e)}")


@app.get("/knowledge/{knowledge_id}")
async def get_knowledge_item(knowledge_id: str):
    """
    Get a specific knowledge item by ID.
    """
    try:
        from src.storage.weaviate_client import WeaviateClient
        from uuid import UUID

        client = WeaviateClient()
        collection = client._client.collections.get("ACMS_Knowledge_v2")

        obj = collection.query.fetch_object_by_id(UUID(knowledge_id), include_vector=False)

        if not obj:
            client.close()
            raise HTTPException(status_code=404, detail="Knowledge item not found")

        props = obj.properties
        item = {
            "id": str(obj.uuid),
            "canonical_query": props.get("canonical_query", ""),
            "answer_summary": props.get("answer_summary", ""),
            "full_answer": props.get("full_answer", ""),
            "primary_intent": props.get("primary_intent", ""),
            "problem_domain": props.get("problem_domain", ""),
            "why_context": props.get("why_context", ""),
            "topic_cluster": props.get("topic_cluster", ""),
            "related_topics": props.get("related_topics", []),
            "key_facts": props.get("key_facts", []),
            "entities_json": props.get("entities_json", "[]"),
            "relations_json": props.get("relations_json", "[]"),
            "extraction_confidence": props.get("extraction_confidence", 0),
            "extraction_model": props.get("extraction_model", ""),
            "source_query_id": props.get("source_query_id", ""),
            "created_at": props.get("created_at", ""),
            "usage_count": props.get("usage_count", 0),
            "feedback_score": props.get("feedback_score", 0)
        }

        client.close()

        return {
            "status": "success",
            "knowledge": item
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get knowledge item: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get knowledge: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting ACMS API Server...")
    print("📍 API will be available at: http://localhost:40080")
    print("📚 Docs available at: http://localhost:40080/docs")
    print("")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=40080,
        log_level="info"
    )
