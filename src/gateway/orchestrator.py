"""Gateway orchestrator - Main 7-step pipeline.

Coordinates all gateway components:
1. Intent Detection → IntentClassifier
2. Cache Check → QueryResultCache
3. Agent Selection → AgentSelector
4. Context Assembly → ContextAssembler
5. Compliance Check → ComplianceChecker
6. Agent Execution → Agent wrappers
7. Feedback Storage → MemoryCRUD

Workflow:
    Request → Orchestrator → 7 steps → Response (streaming)
    Each step emits status updates for real-time progress tracking.
"""

import logging
import time
import hashlib
import json
import os
from typing import AsyncIterator, Optional, Dict, Any, List
from datetime import datetime

from src.gateway.models import (
    GatewayRequest,
    GatewayResponse,
    AgentType,
    IntentType,
    ComplianceResult,
    GatewayStage
)
from src.gateway.intent_classifier import get_intent_classifier
from src.gateway.agent_selector import get_agent_selector
from src.gateway.context_assembler import get_context_assembler
from src.gateway.compliance_checker import get_compliance_checker
from src.gateway.preflight_gate import get_preflight_gate  # NEW: Security gate BEFORE external calls
from src.gateway.tracing import generate_trace_id, set_trace_id, get_trace_id, TraceContext  # NEW: Request tracing
from src.gateway.context_sanitizer import get_context_sanitizer  # NEW: Neutralize injection in retrieved context
from src.gateway.rate_limiter import get_rate_limiter  # NEW: Rate limit security-blocked requests
from src.gateway.agents.claude_sonnet import ClaudeSonnetAgent
from src.gateway.agents.chatgpt import ChatGPTAgent
from src.gateway.agents.gemini import GeminiAgent
from src.gateway.agents.claude_code import ClaudeCodeAgent
from src.gateway.agents.ollama import OllamaAgent
# from src.cache.semantic_cache import get_semantic_cache  # DISABLED Nov 14, 2025
from src.storage.memory_crud import MemoryCRUD
from src.storage.dual_memory import DualMemoryService  # WEEK 6 DAY 3: Dual memory integration
from src.storage.database import get_db_pool  # Phase 2: Schema context database access
from src.gateway.query_augmentation import QueryAugmenter
from src.storage.query_history_crud import save_query_to_history_async
from src.gateway.search_detector import SearchDetector
from src.gateway.web_search import web_search_service

# PHASE 0: Audit Logging (Dec 2025) - Data Flow Tracking
from src.audit.logger import get_audit_logger
from src.audit.models import DataClassification

# NEW: Phase 2 Retrieval Pipeline (Dec 2025)
from src.retrieval import Retriever, Ranker, ContextBuilder
from src.memory import MemoryQualityGate

# NEW: Knowledge Extraction (Dec 2025) - Replaces old FactExtractor
# Extracts intent, entities, topics, and facts using Claude Sonnet 4
from src.intelligence.knowledge_extractor import (
    KnowledgeExtractor,
    KnowledgeEntry,
    get_knowledge_extractor,
)

# NEW: Cross-Source Intelligence (Dec 2025) - Query Router for unified insights
from src.intelligence.query_router import QueryRouter

# NEW: Knowledge Preflight (Feb 2026) - Cognitive "Feeling of Knowing"
# Skip expensive retrieval when knowledge is unlikely to exist
from src.retrieval.knowledge_preflight import (
    KnowledgePreflight,
    KnowledgeSignal,
    get_preflight_instance,
)

logger = logging.getLogger(__name__)


def create_step_event(step: str, message: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a detailed thinking step event for UI visualization.

    Args:
        step: Step identifier (intent_detection, agent_selection, etc.)
        message: Human-readable status message
        details: Optional dict with input/output data for debugging

    Returns:
        Dict with type, step, message, and optional details
    """
    event = {
        "type": "status",
        "step": step,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    if details:
        event["details"] = details
    return event


class GatewayOrchestrator:
    """Orchestrates all gateway components in 7-step pipeline."""

    def __init__(self):
        """Initialize gateway orchestrator."""
        # Components
        self.intent_classifier = get_intent_classifier()
        self.agent_selector = get_agent_selector()
        self.context_assembler = get_context_assembler()
        self.compliance_checker = get_compliance_checker()
        self.preflight_gate = get_preflight_gate()  # NEW: Security gate BEFORE external calls
        self.context_sanitizer = get_context_sanitizer()  # NEW: Neutralize injection in retrieved context
        self.rate_limiter = get_rate_limiter()  # NEW: Rate limit security-blocked requests
        self.query_router = QueryRouter()  # NEW: Cross-source intelligence routing

        # Semantic cache DISABLED (Nov 14, 2025) - prevents cache pollution
        # self.semantic_cache = get_semantic_cache()

        # WEEK 6 DAY 3: Dual memory system (new) + old system (fallback)
        self.memory_crud = MemoryCRUD()  # Keep as fallback
        self.dual_memory = DualMemoryService()  # NEW: Cache + Knowledge search

        # NEW: Phase 2 Retrieval Pipeline (Dec 2025)
        # Feature flag: ENABLE_NEW_RETRIEVAL=true to use new 3-stage pipeline
        self.enable_new_retrieval = os.getenv("ENABLE_NEW_RETRIEVAL", "true").lower() == "true"
        if self.enable_new_retrieval:
            self.retriever = Retriever()
            self.ranker = Ranker()
            self.context_builder = ContextBuilder(max_tokens=4000)
            self.quality_gate = MemoryQualityGate(threshold=0.8)
            logger.info("✅ NEW Retrieval Pipeline ENABLED (Retriever → Ranker → ContextBuilder)")
        else:
            self.retriever = None
            self.ranker = None
            self.context_builder = None
            self.quality_gate = None
            logger.info("⚠️ New Retrieval Pipeline DISABLED (using legacy)")

        # Query Augmentation (Phase 2 - Feature flagged)
        self.enable_query_augmentation = os.getenv("ENABLE_QUERY_AUGMENTATION", "false").lower() == "true"
        if self.enable_query_augmentation:
            try:
                self.query_augmenter = QueryAugmenter()
                logger.info("Query Augmentation enabled (Phase 2)")
            except Exception as e:
                logger.warning(f"Failed to initialize QueryAugmenter: {e}. Query augmentation disabled.")
                self.query_augmenter = None
                self.enable_query_augmentation = False
        else:
            self.query_augmenter = None
            logger.info("Query Augmentation disabled (set ENABLE_QUERY_AUGMENTATION=true to enable)")

        # Knowledge Preflight (Feb 2026 - Cognitive Architecture Sprint 2)
        # Implements "Feeling of Knowing" to skip retrieval when knowledge unlikely
        self.enable_preflight = os.getenv("ENABLE_KNOWLEDGE_PREFLIGHT", "true").lower() == "true"
        if self.enable_preflight:
            try:
                self.knowledge_preflight = get_preflight_instance()
                logger.info("✅ Knowledge Preflight enabled (FOK cognitive pattern)")
            except Exception as e:
                logger.warning(f"Failed to initialize KnowledgePreflight: {e}. Preflight disabled.")
                self.knowledge_preflight = None
                self.enable_preflight = False
        else:
            self.knowledge_preflight = None
            logger.info("⚠️ Knowledge Preflight disabled (set ENABLE_KNOWLEDGE_PREFLIGHT=true to enable)")

        # Agent pool - agents are optional based on API key availability
        self.agents = {}

        # Initialize each agent with graceful fallback
        agent_configs = [
            (AgentType.CLAUDE_SONNET, ClaudeSonnetAgent, "ANTHROPIC_API_KEY"),
            (AgentType.CHATGPT, ChatGPTAgent, "OPENAI_API_KEY"),
            (AgentType.GEMINI, GeminiAgent, "GEMINI_API_KEY"),
            (AgentType.CLAUDE_CODE, ClaudeCodeAgent, "ANTHROPIC_API_KEY"),
            (AgentType.OLLAMA, OllamaAgent, None),  # Ollama doesn't need API key
        ]

        for agent_type, agent_class, required_key in agent_configs:
            try:
                if required_key and not os.getenv(required_key):
                    logger.info(f"⚠️ {agent_type.value} agent not available ({required_key} not set)")
                    continue
                self.agents[agent_type] = agent_class()
                logger.info(f"✅ {agent_type.value} agent initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize {agent_type.value}: {e}")

        # NEW: Knowledge Extractor (Dec 2025) - Replaces old FactExtractor
        # Extracts intent, entities, topics, and facts using Claude Sonnet 4
        self.enable_knowledge_extraction = os.getenv("ENABLE_KNOWLEDGE_EXTRACTION", "true").lower() == "true"
        if self.enable_knowledge_extraction:
            try:
                self.knowledge_extractor = get_knowledge_extractor()
                logger.info("✅ Knowledge Extraction ENABLED (Claude Sonnet 4)")
            except Exception as e:
                logger.warning(f"Failed to initialize KnowledgeExtractor: {e}. Extraction disabled.")
                self.knowledge_extractor = None
                self.enable_knowledge_extraction = False
        else:
            self.knowledge_extractor = None
            logger.info("⚠️ Knowledge Extraction DISABLED (set ENABLE_KNOWLEDGE_EXTRACTION=true to enable)")

        logger.info("GatewayOrchestrator initialized with 4 agents")

    async def execute(
        self,
        request: GatewayRequest
    ) -> AsyncIterator[Dict[str, Any]]:
        """Execute full 7-step gateway pipeline.

        Args:
            request: GatewayRequest with query, user_id, options

        Yields:
            dict: Status updates and response chunks
                {"type": "status", "step": "intent_detection", "message": "..."}
                {"type": "chunk", "text": "..."}
                {"type": "done", "response": GatewayResponse}

        7-Step Pipeline:
            1. Intent Detection (IntentClassifier)
            2. Cache Check (Redis DB 2)
            3. Agent Selection (AgentSelector)
            4. Context Assembly (ContextAssembler)
            5. Compliance Check (ComplianceChecker)
            6. Agent Execution (streaming)
            7. Feedback Storage (PostgreSQL + Weaviate)
        """
        start_time = time.time()
        query = request.query
        user_id = request.user_id

        # NEW: Generate trace_id for this request (for observability)
        trace_id = generate_trace_id()
        set_trace_id(trace_id)

        logger.info(f"[{trace_id}] Gateway executing: {query[:50]}... (user: {user_id})")

        # ──────────────────────────────────────────────────────────
        # AUDIT: Log user query ingress
        # ──────────────────────────────────────────────────────────
        try:
            audit = get_audit_logger()
            await audit.log_ingress(
                source="gateway",
                operation="user_query",
                item_count=1,
                metadata={
                    "query_length": len(query),
                    "has_file_context": request.file_context is not None,
                    "has_thread_context": request.thread_context is not None,
                    "conversation_id": request.conversation_id,
                    "trace_id": trace_id,
                    "user_id": user_id
                }
            )
            logger.debug(f"[Audit] Logged user query ingress: {trace_id}")
        except Exception as audit_error:
            # Don't fail the request if audit logging fails
            logger.warning(f"[Audit] Failed to log query ingress: {audit_error}")

        # Initialize response tracking
        detected_intent = None
        selected_agent_type = None
        from_cache = False
        answer = ""
        cost_usd = 0.0

        try:
            # ──────────────────────────────────────────────────────────
            # Step 1: Intent Detection
            # ──────────────────────────────────────────────────────────
            yield create_step_event(
                "intent_detection",
                "Classifying query intent...",
                {"input": {"query": query[:100] + "..." if len(query) > 100 else query}}
            )

            detected_intent, confidence = self.intent_classifier.classify(query)
            logger.info(
                f"Intent detected: {detected_intent.value} "
                f"(confidence: {confidence:.2f})"
            )

            yield create_step_event(
                "intent_detection",
                f"Detected intent: {detected_intent.value.upper()} ({confidence:.0%})",
                {
                    "input": {"query_length": len(query)},
                    "output": {
                        "intent": detected_intent.value,
                        "confidence": round(confidence, 2)
                    }
                }
            )

            # ──────────────────────────────────────────────────────────
            # Step 1.5: PREFLIGHT GATE (Security Check)
            # CRITICAL: Must run BEFORE web search, augmentation, or any external call
            # ──────────────────────────────────────────────────────────
            yield create_step_event(
                "preflight_gate",
                "Running security checks (PII/secrets/injection)...",
                {
                    "input": {
                        "query_chars": len(query),
                        "checks": ["secrets", "pii", "injection"]
                    }
                }
            )

            user_ctx = {"user_id": user_id, "role": "member", "tenant_id": "default"}

            # Check if user is rate limited BEFORE processing
            rate_check = self.rate_limiter.check_only(user_id)
            if not rate_check.allowed:
                logger.warning(f"[{trace_id}] Rate limited: {rate_check.reason} | retry_after={rate_check.retry_after}s")
                yield {
                    "type": "error",
                    "step": "rate_limit",
                    "message": f"Too many blocked requests. Please wait {rate_check.retry_after} seconds before trying again.",
                    "trace_id": trace_id,
                    "approved": False,
                    "reason": rate_check.reason,
                    "details": {
                        "retry_after": rate_check.retry_after,
                        "window_seconds": rate_check.window_seconds
                    }
                }
                return

            preflight_result = self.preflight_gate.check(query, user_id, user_ctx)

            if not preflight_result.allowed:
                # BLOCKED - Return error immediately, BEFORE any external API call
                # Record blocked request for rate limiting
                self.rate_limiter.check_and_record(user_id, was_blocked=True)

                logger.warning(
                    f"[{trace_id}] PreflightGate BLOCKED: {preflight_result.reason}"
                )

                # Build user-friendly error message
                detection_types = [d.detection_type.value for d in preflight_result.detections]

                if "ssn" in detection_types:
                    user_message = "Your message contains a Social Security Number. Please remove it and try again - I cannot process queries containing SSNs for your protection."
                elif "credit_card" in detection_types:
                    user_message = "Your message contains a credit card number. Please remove it and try again - I cannot process queries containing payment information."
                elif "api_key" in detection_types:
                    user_message = "Your message contains an API key or secret token. Please remove it and try again - sharing API keys could compromise your accounts."
                elif "password" in detection_types:
                    user_message = "Your message contains a password. Please remove it and try again - I cannot process queries containing passwords."
                elif "email" in detection_types:
                    user_message = "Your message contains an email address. Please remove personal information and try again."
                elif "phone" in detection_types:
                    user_message = "Your message contains a phone number. Please remove personal information and try again."
                elif "sql_injection" in detection_types or "command_injection" in detection_types:
                    user_message = "Your message contains potentially harmful content that cannot be processed."
                else:
                    user_message = f"Security check failed: {preflight_result.reason}"

                yield {
                    "type": "error",
                    "step": "preflight_gate",
                    "message": user_message,
                    "trace_id": trace_id,
                    "approved": False,
                    "reason": preflight_result.reason,
                    "details": {
                        "input": {"query_chars": len(query)},
                        "output": preflight_result.to_dict()
                    }
                }
                return

            # Record successful request (not blocked)
            self.rate_limiter.check_and_record(user_id, was_blocked=False)

            # Use sanitized query for downstream operations if available
            working_query = preflight_result.sanitized_query if preflight_result.sanitized_query else query
            allow_web_search = preflight_result.allow_web_search

            if preflight_result.detections:
                yield create_step_event(
                    "preflight_gate",
                    f"Passed with {len(preflight_result.detections)} detections (sanitized)",
                    {
                        "output": {
                            "allowed": True,
                            "sanitized": working_query != query,
                            "allow_web_search": allow_web_search,
                            "detections": len(preflight_result.detections)
                        }
                    }
                )
            else:
                yield create_step_event(
                    "preflight_gate",
                    "Security check passed",
                    {
                        "output": {
                            "allowed": True,
                            "sanitized": False,
                            "allow_web_search": allow_web_search
                        }
                    }
                )

            logger.info(f"[{trace_id}] PreflightGate passed | allow_web_search={allow_web_search}")

            # ──────────────────────────────────────────────────────────
            # Step 1.7: Direct Data Handlers (EMAIL, FINANCE, KNOWLEDGE intents)
            # For structured data queries, bypass LLM and return real data
            # ──────────────────────────────────────────────────────────

            # Handle MEMORY_QUERY for topic/knowledge summary requests
            query_lower = query.lower()
            is_topic_summary_query = (
                detected_intent == IntentType.MEMORY_QUERY and
                any(kw in query_lower for kw in ["topics", "summarize", "knowledge", "discussed", "know about"])
            )

            if is_topic_summary_query:
                yield create_step_event(
                    "data_handler",
                    "Fetching conversation topics from knowledge base...",
                    {"input": {"intent": "knowledge_summary", "query": query[:50]}}
                )

                # Fetch actual topics from ACMS_Knowledge_v2
                from src.gateway.knowledge_handler import KnowledgeDataHandler
                knowledge_handler = KnowledgeDataHandler()
                knowledge_response = await knowledge_handler.format_topic_summary(user_id)

                yield create_step_event(
                    "data_handler",
                    "Knowledge topics retrieved successfully",
                    {"output": {"source": "ACMS_Knowledge_v2"}}
                )

                # Stream the response
                yield {"type": "chunk", "text": knowledge_response}

                # Complete
                latency_ms = int((time.time() - start_time) * 1000)
                response = GatewayResponse(
                    query=query,
                    answer=knowledge_response,
                    agent_used=AgentType.CLAUDE_SONNET,
                    intent_detected=detected_intent,
                    from_cache=False,
                    trace_id=trace_id,
                    cost_usd=0.0,
                    latency_ms=latency_ms
                )
                response_dict = response.model_dump(mode='json')
                response_dict["data_source"] = "knowledge_handler"
                yield {"type": "done", "response": response_dict}

                await save_query_to_history_async(
                    user_id=user_id,
                    question=query,
                    answer=knowledge_response,
                    response_source="knowledge_handler",
                    from_cache=False,
                    cost_usd=0.0,
                    latency_ms=latency_ms
                )

                logger.info(f"[{trace_id}] MEMORY_QUERY (topics) handled via knowledge handler")
                return

            if detected_intent == IntentType.EMAIL:
                yield create_step_event(
                    "data_handler",
                    "Fetching email data from database...",
                    {"input": {"intent": "email", "query": query[:50]}}
                )

                from src.gateway.email_handler import EmailDataHandler
                email_handler = EmailDataHandler(db_pool=getattr(self, 'db_pool', None))
                email_response = await email_handler.format_response_for_query(query)

                yield create_step_event(
                    "data_handler",
                    "Email data retrieved successfully",
                    {"output": {"source": "email_metadata + unified_insights"}}
                )

                # Stream the response
                yield {"type": "chunk", "text": email_response}

                # Complete the response
                latency_ms = int((time.time() - start_time) * 1000)
                response = GatewayResponse(
                    query=query,
                    answer=email_response,
                    agent_used=AgentType.GEMINI,  # Placeholder - not actually used
                    intent_detected=detected_intent,
                    from_cache=False,
                    trace_id=trace_id,
                    cost_usd=0.0,  # No LLM cost for direct data queries
                    latency_ms=latency_ms
                )
                response_dict = response.model_dump(mode='json')
                response_dict["data_source"] = "email_handler"
                yield {"type": "done", "response": response_dict}

                # Log to query history
                await save_query_to_history_async(
                    user_id=user_id,
                    question=query,
                    answer=email_response,
                    response_source="email_handler",
                    from_cache=False,
                    cost_usd=0.0,
                    latency_ms=latency_ms
                )

                logger.info(f"[{trace_id}] EMAIL intent handled via direct data query")
                return

            # ──────────────────────────────────────────────────────────
            # Step 2: Cache Check (DISABLED - Nov 14, 2025)
            # ──────────────────────────────────────────────────────────
            # Caching disabled to prevent pollution (wrong agents, stale data, quality issues)
            # All queries generate fresh responses for maximum correctness
            logger.info(f"[GATEWAY] Caching DISABLED | query='{query[:50]}...' | generating_fresh=true")

            yield create_step_event(
                "cache_check",
                "Cache check skipped (disabled for quality)",
                {
                    "input": {"query_hash": hashlib.md5(query.encode()).hexdigest()[:12]},
                    "output": {
                        "cache_hit": False,
                        "semantic_cache_enabled": False,
                        "redis_cache_enabled": False,
                        "reason": "Cache disabled Nov 2025 to prevent pollution (wrong agents, stale web data)",
                        "generating_fresh": True
                    }
                }
            )

            # ──────────────────────────────────────────────────────────
            # Step 3: Agent Selection
            # ──────────────────────────────────────────────────────────
            yield create_step_event(
                "agent_selection",
                "Selecting optimal agent...",
                {"input": {"intent": detected_intent.value, "manual_override": request.manual_agent}}
            )

            selected_agent_type = self.agent_selector.select_agent(
                intent=detected_intent,
                manual_override=request.manual_agent
            )

            agent = self.agents[selected_agent_type]
            metadata = agent.get_metadata()

            logger.info(
                f"Agent selected: {selected_agent_type.value} "
                f"(best for: {metadata['best_for']})"
            )

            if request.manual_agent:
                yield create_step_event(
                    "agent_selection",
                    f"Manual override: {selected_agent_type.value.upper()}",
                    {
                        "input": {"manual_agent": request.manual_agent},
                        "output": {"agent": selected_agent_type.value, "override": True}
                    }
                )
            else:
                yield create_step_event(
                    "agent_selection",
                    f"Selected agent: {selected_agent_type.value.upper()} (cost-optimized)",
                    {
                        "input": {"intent": detected_intent.value},
                        "output": {
                            "agent": selected_agent_type.value,
                            "best_for": metadata.get("best_for", []),
                            "cost_per_1m_tokens": metadata.get("cost_per_million", "N/A")
                        }
                    }
                )

            # ──────────────────────────────────────────────────────────
            # Step 3.25: Web Search Detection (Tavily Integration)
            # SECURITY: Only proceed if PreflightGate allows web search
            # ──────────────────────────────────────────────────────────
            search_results = []
            search_used = False
            search_query = None

            # Check if query needs web search AND PreflightGate allows it
            needs_search, search_reason = SearchDetector.needs_search(working_query)

            # SECURITY: PreflightGate can disable web search if injection detected
            if not allow_web_search:
                needs_search = False
                search_reason = "disabled by security gate"
                logger.info(f"[{trace_id}] Web search DISABLED by PreflightGate")

            if needs_search:
                yield create_step_event(
                    "web_search",
                    f"Query needs web search ({search_reason})...",
                    {"input": {"query": working_query[:80], "reason": search_reason}}
                )

                logger.info(f"[{trace_id}] 🔍 Web search triggered: {search_reason}")

                # Extract optimized search query (use sanitized working_query)
                search_query = SearchDetector.extract_search_query(working_query)

                # Perform web search
                search_results = await web_search_service.search(search_query)

                if search_results:
                    search_used = True
                    logger.info(
                        f"✅ Web search found {len(search_results)} results for: {search_query}"
                    )

                    yield create_step_event(
                        "web_search",
                        f"Found {len(search_results)} sources ({search_reason})",
                        {
                            "input": {"search_query": search_query, "trigger_reason": search_reason},
                            "output": {
                                "result_count": len(search_results),
                                "sources": [
                                    {
                                        "title": r.title[:80] if r.title else "Untitled",
                                        "url": r.url,
                                        "snippet": r.content[:150] + "..." if r.content and len(r.content) > 150 else (r.content or "")
                                    }
                                    for r in search_results[:5]
                                ]
                            }
                        }
                    )
                else:
                    logger.warning(f"⚠️ Web search returned no results for: {search_query}")
                    yield create_step_event(
                        "web_search",
                        "No search results found - using memory context",
                        {"input": {"search_query": search_query}, "output": {"result_count": 0}}
                    )
            else:
                logger.info(f"ℹ️ No web search needed: {search_reason}")

            # ──────────────────────────────────────────────────────────
            # Step 3.5: Query Augmentation (Phase 2 - Optional)
            # ──────────────────────────────────────────────────────────
            augmented_queries = [query]  # Default: just use original query

            if self.enable_query_augmentation and self.query_augmenter:
                yield create_step_event(
                    "query_augmentation",
                    "Augmenting query for better retrieval...",
                    {"input": {"query_words": len(query.split())}}
                )

                try:
                    # Determine augmentation mode based on query complexity
                    query_word_count = len(query.split())
                    if query_word_count > 15:
                        mode = "decompose"  # Complex queries → decompose
                    elif query_word_count < 5:
                        mode = "full"  # Short queries → expand with synonyms + LLM
                    else:
                        mode = "full"  # Medium queries → use all techniques

                    augmented_queries = await self.query_augmenter.augment(query, mode=mode)

                    logger.info(
                        f"Query augmented: 1 original → {len(augmented_queries)} variations "
                        f"(mode: {mode})"
                    )

                    yield create_step_event(
                        "query_augmentation",
                        f"Generated {len(augmented_queries)} query variations ({mode} mode)",
                        {
                            "input": {"original_query": query},
                            "output": {
                                "mode": mode,
                                "mode_reason": "complex query" if mode == "decompose" else ("short query" if len(query.split()) < 5 else "standard"),
                                "variation_count": len(augmented_queries),
                                "variations": augmented_queries  # Full variations, not truncated
                            }
                        }
                    )

                except Exception as e:
                    logger.warning(f"Query augmentation failed: {e}. Using original query.")
                    augmented_queries = [query]
                    yield create_step_event(
                        "query_augmentation",
                        "Augmentation failed - using original query",
                        {"error": str(e)}
                    )

            # ──────────────────────────────────────────────────────────
            # Step 4: Context Assembly (with multi-query support + Web Search)
            # ──────────────────────────────────────────────────────────
            yield create_step_event(
                "context_assembly",
                "Retrieving relevant context...",
                {
                    "input": {
                        "query_count": len(augmented_queries),
                        "queries": augmented_queries,
                        "user_id": user_id,
                        "intent": detected_intent.value,
                        "context_limit": request.context_limit,
                        "retrieval_sources": ["ACMS_Memory_v2 (Weaviate)", "PostgreSQL memory_items"]
                    }
                }
            )

            # Search with augmented queries and deduplicate results
            memory_context = await self._assemble_context_with_augmentation(
                queries=augmented_queries,
                user_id=user_id,
                intent=detected_intent,
                context_limit=request.context_limit
            )

            # Build final context: thread context + file context + web search results + memory context
            # Thread context (conversation continuity) comes first
            thread_context_str = ""
            if request.thread_context:
                thread_context_str = self.context_assembler.format_thread_context(request.thread_context)
                if thread_context_str:
                    logger.info(
                        f"[{trace_id}] Thread context: {len(thread_context_str)} chars, "
                        f"{request.thread_context.turn_count} turns"
                    )

            # Sprint 3 Day 15: Build file context string (ChatGPT-style)
            file_context_str = ""
            if request.file_context:
                file_context_str = (
                    f"# Uploaded File: {request.file_context.filename}\n"
                    f"## File Content:\n"
                    f"```\n{request.file_context.content}\n```\n"
                )
                logger.info(
                    f"[{trace_id}] File context: {len(file_context_str)} chars "
                    f"(file: {request.file_context.filename})"
                )

                # Emit status event for file context inclusion (visible in UI)
                yield create_step_event(
                    "file_context_included",
                    f"Including uploaded file: {request.file_context.filename}",
                    {
                        "input": {"filename": request.file_context.filename},
                        "output": {
                            "file_chars": len(request.file_context.content),
                            "context_chars": len(file_context_str),
                            "included_in_prompt": True
                        }
                    }
                )

            if search_used and search_results:
                # Prepend web search results to context
                search_context = web_search_service.format_results_for_llm(search_results)

                # Build full context with thread context and file context first
                context_parts = []
                if thread_context_str:
                    context_parts.append("# Conversation Context (Recent History)")
                    context_parts.append(thread_context_str)
                    context_parts.append("")

                # Sprint 3 Day 15: Include file context prominently (ChatGPT-style)
                if file_context_str:
                    context_parts.append(file_context_str)
                    context_parts.append("")

                context_parts.append(search_context)
                context_parts.append("")
                context_parts.append("# Memory Context (from your knowledge base)")
                context_parts.append(memory_context)
                context_parts.append("")
                context_parts.append("# Instructions")
                context_parts.append("Answer the user's question using:")
                if file_context_str:
                    context_parts.append("1. The Uploaded File content above - this is the primary focus")
                    context_parts.append("2. The Conversation Context for continuity with recent discussion")
                    context_parts.append("3. Web Search Results for current information")
                    context_parts.append("4. Memory Context for additional background")
                else:
                    context_parts.append("1. The Conversation Context above for continuity with recent discussion")
                    context_parts.append("2. Web Search Results for current information")
                    context_parts.append("3. Memory Context for additional background")
                context_parts.append("Always cite sources from web search. Reference earlier conversation when relevant.")

                context = "\n".join(context_parts)

                logger.info(
                    f"Context assembled: {len(thread_context_str)} chars (thread) + "
                    f"{len(search_context)} chars (web search) + "
                    f"{len(memory_context)} chars (memory)"
                )
                yield create_step_event(
                    "context_assembly",
                    f"Combined thread context + {len(search_results)} web sources + memory",
                    {
                        "output": {
                            "thread_chars": len(thread_context_str),
                            "thread_turns": request.thread_context.turn_count if request.thread_context else 0,
                            "web_sources": len(search_results),
                            "web_chars": len(search_context),
                            "memory_chars": len(memory_context),
                            "total_chars": len(context)
                        }
                    }
                )
            else:
                # Build context with thread context + file context + memory context
                context_parts = []
                if thread_context_str:
                    context_parts.append("# Conversation Context (Recent History)")
                    context_parts.append(thread_context_str)
                    context_parts.append("")

                # Sprint 3 Day 15: Include file context prominently (ChatGPT-style)
                if file_context_str:
                    context_parts.append(file_context_str)
                    context_parts.append("")
                    context_parts.append("# Instructions")
                    context_parts.append("Focus on the uploaded file content above. Answer questions about the file.")
                    if thread_context_str:
                        context_parts.append("Reference earlier conversation when relevant.")
                    context_parts.append("")
                elif thread_context_str:
                    context_parts.append("# Instructions")
                    context_parts.append("Continue the conversation naturally, referencing earlier discussion when relevant.")
                    context_parts.append("")

                if memory_context:
                    context_parts.append("# Memory Context (from your knowledge base)")
                    context_parts.append(memory_context)

                context = "\n".join(context_parts) if context_parts else memory_context

                context_size = len(context)
                if context_size > 0:
                    logger.info(
                        f"Context assembled: {context_size} chars "
                        f"(thread: {len(thread_context_str)}, memory: {len(memory_context)}, "
                        f"limit: {request.context_limit} memories)"
                    )
                    yield create_step_event(
                        "context_assembly",
                        f"Context retrieved ({context_size} chars, including thread context)",
                        {
                            "output": {
                                "thread_chars": len(thread_context_str),
                                "thread_turns": request.thread_context.turn_count if request.thread_context else 0,
                                "context_chars": context_size,
                                "memory_limit": request.context_limit,
                                "query_variations": len(augmented_queries)
                            }
                        }
                    )
                else:
                    logger.info("No context needed for this intent")
                    yield create_step_event(
                        "context_assembly",
                        "No context needed (creative/standalone task)",
                        {"output": {"context_chars": 0}}
                    )

            # ──────────────────────────────────────────────────────────
            # Step 4.25: Cross-Source Insights (Unified Intelligence)
            # Check if query involves multiple data sources (email, financial, etc.)
            # and include relevant insights from unified_insights store
            # ──────────────────────────────────────────────────────────
            cross_source_context = ""
            cross_source_citations = []
            cross_source_sources = []  # Track which sources were queried for UI badges
            # Respect both env var AND request-level toggle (request takes precedence)
            env_cross_source = os.getenv("ACMS_CROSS_SOURCE_ENABLED", "true").lower() == "true"
            use_cross_source = request.cross_source_enabled and env_cross_source

            if use_cross_source:
                try:
                    # Detect if query involves cross-source data
                    entities = self.query_router.entity_detector.detect(query)
                    source_hints = [e.source_hint for e in entities if e.source_hint]

                    # SKIP cross-source for pure MEMORY_QUERY about topics/knowledge
                    # These queries should prioritize ACMS_Knowledge_v2 data, not email insights
                    query_lower = query.lower()
                    is_knowledge_query = detected_intent == IntentType.MEMORY_QUERY and any(
                        kw in query_lower for kw in ["topics", "topic", "knowledge", "memories", "discussed", "summarize"]
                    )

                    if is_knowledge_query:
                        logger.info(f"[{trace_id}] Skipping cross-source for knowledge query - prioritizing ACMS_Knowledge_v2")
                        use_cross_source = False

                    # If we detect email/financial/calendar entities, search unified insights
                    if use_cross_source and (source_hints or any(kw in query_lower for kw in ["email", "emails", "mail", "inbox"])):
                        yield create_step_event(
                            "cross_source_insights",
                            "Searching across data sources...",
                            {
                                "input": {
                                    "entities_detected": len(entities),
                                    "source_hints": list(set(source_hints))
                                }
                            }
                        )

                        route_result = await self.query_router.route_query(
                            query,
                            available_sources={"email", "chat"},
                            max_results_per_source=3
                        )

                        if route_result.results:
                            # Format cross-source insights for context
                            cross_source_parts = ["# Cross-Source Insights"]
                            for result in route_result.results[:5]:
                                source_label = result.source.upper()
                                cross_source_parts.append(
                                    f"[{source_label}] {result.insight_text}"
                                )
                            cross_source_context = "\n".join(cross_source_parts)
                            cross_source_citations = route_result.citations
                            cross_source_sources = list(route_result.sources_queried)  # For UI badges

                            yield create_step_event(
                                "cross_source_insights",
                                f"Found {len(route_result.results)} insights across {len(route_result.sources_queried)} sources",
                                {
                                    "output": {
                                        "sources_queried": route_result.sources_queried,
                                        "results_count": len(route_result.results),
                                        "citations": cross_source_citations[:5],
                                        "latency_ms": route_result.latency_ms
                                    }
                                }
                            )

                            # Prepend cross-source context to main context
                            if cross_source_context:
                                context = f"{cross_source_context}\n\n{context}" if context else cross_source_context

                except Exception as e:
                    logger.warning(f"Cross-source search failed: {e}")
                    yield create_step_event(
                        "cross_source_insights",
                        "Cross-source search skipped (error)",
                        {"error": str(e)}
                    )

            # ──────────────────────────────────────────────────────────
            # Step 4.5: Context Sanitization
            # SECURITY: Neutralize injection attempts in retrieved content
            # Retrieved memories/web results may contain malicious content
            # ──────────────────────────────────────────────────────────
            if context:
                sanitization_result = self.context_sanitizer.sanitize(context, add_delimiters=True)

                if not sanitization_result.is_clean:
                    logger.warning(
                        f"[{trace_id}] Context sanitized: {sanitization_result.detection_count} "
                        f"injection attempts neutralized"
                    )
                    yield create_step_event(
                        "context_sanitization",
                        f"Sanitized {sanitization_result.detection_count} potential injection attempts",
                        {
                            "input": {"original_length": sanitization_result.original_length},
                            "output": {
                                "sanitized_length": sanitization_result.sanitized_length,
                                "detection_count": sanitization_result.detection_count,
                                "is_clean": sanitization_result.is_clean
                            }
                        }
                    )
                else:
                    yield create_step_event(
                        "context_sanitization",
                        "Context verified clean",
                        {
                            "output": {
                                "is_clean": True,
                                "length": len(context)
                            }
                        }
                    )

                # Use sanitized context for LLM
                context = sanitization_result.sanitized_context

            # ──────────────────────────────────────────────────────────
            # Step 5: Compliance Check
            # ──────────────────────────────────────────────────────────
            # Define rules being checked for observability
            compliance_rules = [
                "PII detection (SSN, credit cards, phone numbers)",
                "Prohibited content (violence, illegal activities)",
                "Privacy level enforcement",
                "Token limit validation"
            ]

            yield create_step_event(
                "compliance_check",
                "Checking compliance...",
                {
                    "input": {
                        "query_chars": len(query),
                        "rules_to_check": compliance_rules
                    }
                }
            )

            compliance_result = self.compliance_checker.check_compliance(query)

            if not compliance_result.approved:
                # BLOCKED - Return error immediately
                logger.warning(
                    f"Compliance BLOCKED: {len(compliance_result.issues)} issues"
                )

                yield {
                    "type": "error",
                    "step": "compliance_check",
                    "message": "Compliance check failed",
                    "approved": False,
                    "issues": [issue.dict() for issue in compliance_result.issues],
                    "details": {
                        "input": {"query_chars": len(query)},
                        "output": {
                            "approved": False,
                            "issue_count": len(compliance_result.issues),
                            "issues": [i.type for i in compliance_result.issues]
                        }
                    }
                }
                return

            elif compliance_result.issues:
                # WARNED - Continue but notify user
                logger.warning(
                    f"Compliance WARNING: {len(compliance_result.issues)} issues"
                )
                yield create_step_event(
                    "compliance_check",
                    f"Approved with {len(compliance_result.issues)} warnings",
                    {
                        "output": {
                            "approved": True,
                            "warnings": len(compliance_result.issues),
                            "warning_types": [i.type for i in compliance_result.issues]
                        }
                    }
                )
            else:
                # APPROVED - No issues
                logger.info("Compliance approved (no issues)")
                yield create_step_event(
                    "compliance_check",
                    "Approved (no issues)",
                    {
                        "output": {
                            "approved": True,
                            "issues": 0,
                            "rules_passed": compliance_rules,
                            "pii_detected": False,
                            "prohibited_content": False
                        }
                    }
                )

            # ──────────────────────────────────────────────────────────
            # Step 5.5: Schema-Driven Context (Feb 2026 - Cognitive Architecture)
            # Inject user expertise context to calibrate LLM responses
            # ──────────────────────────────────────────────────────────
            schema_context = ""
            try:
                schema_context = await self._build_expertise_context(query, user_id)
                if schema_context:
                    # Prepend schema context to existing context
                    context = f"{schema_context}\n\n{context}" if context else schema_context

                    yield create_step_event(
                        "schema_context",
                        "Expertise context applied",
                        {
                            "output": {
                                "context_injected": True,
                                "context_length": len(schema_context)
                            }
                        }
                    )
            except Exception as schema_err:
                logger.warning(f"Schema context injection failed: {schema_err}")
                # Continue without schema context - don't break the pipeline

            # ──────────────────────────────────────────────────────────
            # Step 6: Agent Execution (streaming)
            # ──────────────────────────────────────────────────────────
            yield create_step_event(
                "agent_execution",
                f"Executing {selected_agent_type.value}...",
                {
                    "input": {
                        "agent": selected_agent_type.value,
                        "query_chars": len(query),
                        "context_chars": len(context),
                        "schema_context_applied": bool(schema_context)
                    }
                }
            )

            # Stream response from agent
            full_response = ""
            async for chunk in agent.generate(query=query, context=context):
                full_response += chunk
                yield {"type": "chunk", "text": chunk}

            answer = full_response

            # Estimate cost (rough estimate based on char count)
            # 1 token ≈ 4 chars (rough approximation)
            input_tokens = (len(query) + len(context)) // 4
            output_tokens = len(answer) // 4
            cost_usd = agent.estimate_cost(input_tokens, output_tokens)

            logger.info(
                f"Agent execution complete: {len(answer)} chars, "
                f"${cost_usd:.6f} cost"
            )

            # ──────────────────────────────────────────────────────────
            # AUDIT: Log LLM API call (EGRESS)
            # ──────────────────────────────────────────────────────────
            try:
                audit = get_audit_logger()

                # Map agent type to API destination
                agent_destination_map = {
                    AgentType.CLAUDE_SONNET: "claude_api",
                    AgentType.CHATGPT: "openai_api",
                    AgentType.GEMINI: "gemini_api",
                    AgentType.CLAUDE_CODE: "claude_api",
                }
                destination = agent_destination_map.get(selected_agent_type, "unknown_api")

                await audit.log_egress(
                    source="gateway",
                    operation="llm_call",
                    destination=destination,
                    duration_ms=int((time.time() - start_time) * 1000),
                    data_classification=DataClassification.PUBLIC,  # User queries are public by default
                    metadata={
                        "agent": selected_agent_type.value,
                        "model": getattr(agent, 'model_name', 'unknown'),
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "cost_usd": round(cost_usd, 6),
                        "query_length": len(query),
                        "response_length": len(answer),
                        "trace_id": trace_id
                    }
                )
                logger.debug(f"[Audit] Logged LLM egress: {destination}")
            except Exception as audit_error:
                # Don't fail the request if audit logging fails
                logger.warning(f"[Audit] Failed to log LLM egress: {audit_error}")

            # ──────────────────────────────────────────────────────────
            # Step 7: Knowledge Extraction (Dec 2025 - New Architecture)
            # ──────────────────────────────────────────────────────────
            # Uses KnowledgeExtractor (Claude Sonnet 4) to extract:
            # - Intent analysis (the "why" behind the query)
            # - Named entities and relationships
            # - Dynamic topic clustering
            # - Atomic facts
            # Stores to ACMS_Knowledge_v2 (replaces old ACMS_Knowledge_v1)

            knowledge_entry = None
            knowledge_stored = False
            weaviate_id = None

            if self.enable_knowledge_extraction and self.knowledge_extractor and len(answer) > 100:
                yield create_step_event(
                    "knowledge_extraction",
                    "Extracting knowledge from response...",
                    {
                        "input": {
                            "response_chars": len(answer),
                            "query": query[:100]
                        }
                    }
                )

                try:
                    # Step 7a: Extract full knowledge using Claude Sonnet 4
                    knowledge_entry = await self.knowledge_extractor.extract(
                        query=query,
                        answer=answer,
                        user_id=user_id,
                        source_query_id=None  # Will be set after query_history insert
                    )

                    # Step 7b: Emit "knowledge_understanding" step with WHY context
                    # This is the key UI feature - shows users WHY they asked
                    yield create_step_event(
                        "knowledge_understanding",
                        f"Understanding context: {knowledge_entry.intent.why_context[:80]}...",
                        {
                            "output": {
                                "why_context": knowledge_entry.intent.why_context,
                                "primary_intent": knowledge_entry.intent.primary_intent,
                                "problem_domain": knowledge_entry.intent.problem_domain,
                                "topic_cluster": knowledge_entry.topic_cluster,
                                "related_topics": knowledge_entry.related_topics,
                                "entities_found": len(knowledge_entry.entities),
                                "facts_extracted": len(knowledge_entry.key_facts),
                                "confidence": knowledge_entry.extraction_confidence
                            }
                        }
                    )

                    # Step 7c: Store to ACMS_Knowledge_v2
                    weaviate_id = await self._store_knowledge_entry(
                        entry=knowledge_entry,
                        user_id=user_id
                    )
                    knowledge_stored = weaviate_id is not None

                    logger.info(
                        f"[KnowledgeExtraction] topic={knowledge_entry.topic_cluster}, "
                        f"entities={len(knowledge_entry.entities)}, "
                        f"facts={len(knowledge_entry.key_facts)}, "
                        f"confidence={knowledge_entry.extraction_confidence:.2f}"
                    )

                    yield create_step_event(
                        "knowledge_extraction",
                        f"Stored knowledge → ACMS_Knowledge_v2",
                        {
                            "output": {
                                "topic_cluster": knowledge_entry.topic_cluster,
                                "entities": [e.canonical for e in knowledge_entry.entities],
                                "key_facts": knowledge_entry.key_facts,
                                "stored": knowledge_stored,
                                "weaviate_id": weaviate_id
                            }
                        }
                    )

                except Exception as e:
                    logger.error(f"[KnowledgeExtraction] Failed: {e}", exc_info=True)
                    yield create_step_event(
                        "knowledge_extraction",
                        f"Extraction failed: {str(e)[:50]}",
                        {"error": str(e)}
                    )
            else:
                # Knowledge extraction disabled or response too short
                yield create_step_event(
                    "knowledge_extraction",
                    "Skipped (response too short or disabled)",
                    {
                        "output": {
                            "skipped": True,
                            "reason": "disabled" if not self.enable_knowledge_extraction else f"response_too_short ({len(answer)} chars < 100)",
                            "query_history": {
                                "logged": True,
                                "table": "query_history"
                            }
                        }
                    }
                )

            yield create_step_event(
                "response_complete",
                "Response generation complete",
                {
                    "output": {
                        "agent": selected_agent_type.value,
                        "response_chars": len(answer),
                        "cost_usd": round(cost_usd, 6),
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens
                    }
                }
            )

            # ──────────────────────────────────────────────────────────
            # Final Response
            # ──────────────────────────────────────────────────────────
            latency_ms = int((time.time() - start_time) * 1000)

            # Save to query_history for feedback + analytics
            query_id = await save_query_to_history_async(
                user_id=user_id,
                question=query,
                answer=answer,
                response_source=selected_agent_type.value,
                from_cache=False,
                confidence=0.9,
                cost_usd=cost_usd,
                context_limit=request.context_limit,
                latency_ms=latency_ms,
                metadata={
                    "cache_status": "miss",
                    "intent": detected_intent.value,
                    "context_size": len(context),
                    "agent": selected_agent_type.value,
                    "search_used": search_used,
                    "search_query": search_query,
                    "search_results_count": len(search_results) if search_used else 0
                }
            )

            response = GatewayResponse(
                query_id=query_id,
                query=query,
                answer=answer,
                agent_used=selected_agent_type,
                from_cache=False,
                intent_detected=detected_intent,
                cost_usd=cost_usd,
                latency_ms=latency_ms
            )

            # Add search metadata to response
            response_dict = response.model_dump(mode='json')
            response_dict["search_used"] = search_used
            if search_used:
                response_dict["search_query"] = search_query
                response_dict["search_results_count"] = len(search_results)
                response_dict["search_results"] = [r.to_dict() for r in search_results]

            # Add cross-source metadata for UI badges
            if cross_source_sources:
                response_dict["sources"] = cross_source_sources
                response_dict["cross_source_citations"] = cross_source_citations

            logger.info(
                f"Gateway complete: {latency_ms}ms, ${cost_usd:.6f}, "
                f"{selected_agent_type.value}, search={search_used}"
            )

            yield {"type": "done", "response": response_dict}

        except Exception as e:
            logger.error(f"Gateway execution error: {e}", exc_info=True)

            yield {
                "type": "error",
                "step": "agent_execution",
                "message": f"Gateway error: {str(e)}",
                "agent": selected_agent_type.value if selected_agent_type else "unknown"
            }


    async def _assemble_context_with_augmentation(
        self,
        queries: List[str],
        user_id: str,
        intent: IntentType,
        context_limit: int
    ) -> str:
        """Assemble context using multiple augmented queries with deduplication.

        Phase 2 Enhancement: Uses QueryAugmenter to generate multiple query variations,
        searches with each, and deduplicates memories for better retrieval.

        Dec 2025: NEW 3-stage pipeline (Retriever → Ranker → ContextBuilder) when enabled.

        Args:
            queries: List of query variations (original + augmented)
            user_id: User identifier
            intent: Detected intent type
            context_limit: Maximum number of unique memories to retrieve

        Returns:
            str: Formatted context from deduplicated memories

        Design:
            1. Search with each query variation
            2. Deduplicate by memory_id (same memory from different queries)
            3. Re-rank by highest similarity score
            4. Limit to context_limit memories
            5. Format using ContextAssembler's formatting logic
        """
        # Early exit for creative intent (no context needed)
        if intent == IntentType.CREATIVE:
            logger.info("Creative intent: Skipping context retrieval")
            return ""

        # ═══════════════════════════════════════════════════════════════════
        # NEW: 3-Stage Retrieval Pipeline (Dec 2025)
        # ═══════════════════════════════════════════════════════════════════
        if self.enable_new_retrieval and self.retriever:
            return await self._retrieve_with_new_pipeline(
                queries=queries,
                user_id=user_id,
                intent=intent,
                context_limit=context_limit
            )

        # If only one query (augmentation disabled), use standard path
        if len(queries) == 1:
            return await self.context_assembler.assemble_context(
                query=queries[0],
                user_id=user_id,
                intent=intent,
                context_limit=context_limit
            )

        # Multi-query search with deduplication
        logger.info(f"Searching with {len(queries)} query variations...")

        all_memories = []
        memory_ids_seen = set()

        # Adjust context limit based on intent (same logic as ContextAssembler)
        if intent == IntentType.MEMORY_QUERY:
            search_limit = min(context_limit, 20)
        elif intent == IntentType.ANALYSIS:
            search_limit = min(context_limit, 10)
        else:
            search_limit = context_limit

        # Search with each query variation
        for i, q in enumerate(queries):
            try:
                # WEEK 6 DAY 3: Use dual memory system (cache + knowledge)
                # Get embedding for this query variation
                query_vector = self.memory_crud.openai_embeddings.generate_embedding(q)

                # SPRINT 2 (Feb 2026): Knowledge Preflight Check
                # Implements cognitive "Feeling of Knowing" - quickly estimate
                # if relevant knowledge exists before expensive retrieval
                preflight_result = None
                if self.enable_preflight and self.knowledge_preflight:
                    try:
                        if self.knowledge_preflight._initialized:
                            preflight_result = await self.knowledge_preflight.check(
                                query=q,
                                embedding=query_vector,
                                user_id=user_id,
                            )
                            logger.debug(
                                f"[Preflight] Query {i+1}: signal={preflight_result.signal.value}, "
                                f"confidence={preflight_result.confidence:.2f}, "
                                f"entities={preflight_result.matched_entities[:3]}"
                            )

                            # Skip expensive retrieval if knowledge is unlikely
                            if preflight_result.signal == KnowledgeSignal.UNLIKELY:
                                logger.info(
                                    f"[Preflight] Skipping retrieval for query {i+1} - "
                                    f"signal=UNLIKELY (confidence={preflight_result.confidence:.2f})"
                                )
                                continue  # Skip to next query variation
                    except Exception as pf_err:
                        # Graceful degradation - proceed with retrieval if preflight fails
                        logger.warning(f"[Preflight] Check failed, proceeding with retrieval: {pf_err}")

                # Search dual memory (cache + knowledge) in parallel
                cache_hits, knowledge_facts = await self.dual_memory.search_dual(
                    query=q,
                    query_vector=query_vector,
                    user_id=user_id,
                    conversation_id=None,  # Will be added when we have conversation context
                    cache_limit=min(search_limit, 5),
                    knowledge_limit=min(search_limit, 10),
                    cache_threshold=0.85,  # Strict for cache hits
                    knowledge_threshold=0.60  # Lenient for facts
                )

                # Convert dual memory results to unified format
                memories = []

                # Add cache hits
                for hit in cache_hits:
                    memories.append({
                        "id": hit["id"],
                        "content": f"Q: {hit['canonical_query']}\nA: {hit['summarized_answer']}",
                        "similarity": hit["similarity"],
                        "source": "cache",
                        "metadata": {
                            "usage_count": hit.get("usage_count", 0),
                            "confidence_score": hit.get("confidence_score", 0.0)
                        }
                    })

                # Add knowledge facts
                for fact in knowledge_facts:
                    memories.append({
                        "id": fact["id"],
                        "content": fact["content"],
                        "similarity": fact["similarity"],
                        "source": "knowledge",
                        "metadata": {
                            "source_type": fact.get("source_type", ""),
                            "confidence": fact.get("confidence", 0.0)
                        }
                    })

                # STAGED ROLLOUT: Also search old system for comparison
                old_memories = await self.memory_crud.search_memories(
                    query=q,
                    user_id=user_id,
                    limit=search_limit,
                    privacy_filter=["PUBLIC", "INTERNAL", "CONFIDENTIAL"]
                )

                # Log comparison for monitoring
                logger.info(
                    f"[DualMemory] Query variation {i+1}: "
                    f"NEW ({len(cache_hits)} cache + {len(knowledge_facts)} knowledge = {len(memories)} total) "
                    f"vs OLD ({len(old_memories)} memories)"
                )

                # STAGE 1: Use NEW system, fallback to OLD if empty
                if not memories and old_memories:
                    logger.warning(f"[DualMemory] No results from dual memory, using old system fallback")
                    memories = old_memories

                # Add unique memories (deduplicate by memory_id)
                for memory in memories:
                    memory_id = memory.get("id") or memory.get("memory_id")
                    if memory_id and memory_id not in memory_ids_seen:
                        memory_ids_seen.add(memory_id)
                        all_memories.append(memory)

                logger.debug(
                    f"Query variation {i+1}/{len(queries)}: "
                    f"{len(memories)} found, {len(all_memories)} unique total"
                )

            except Exception as e:
                logger.error(f"Error searching with query variation {i+1}: {e}")
                # Fallback to old system on error
                try:
                    old_memories = await self.memory_crud.search_memories(
                        query=q,
                        user_id=user_id,
                        limit=search_limit,
                        privacy_filter=["PUBLIC", "INTERNAL", "CONFIDENTIAL"]
                    )
                    for memory in old_memories:
                        memory_id = memory.get("id") or memory.get("memory_id")
                        if memory_id and memory_id not in memory_ids_seen:
                            memory_ids_seen.add(memory_id)
                            all_memories.append(memory)
                    logger.info(f"[DualMemory] Fallback successful: {len(old_memories)} from old system")
                except Exception as fallback_error:
                    logger.error(f"[DualMemory] Fallback also failed: {fallback_error}")
                continue

        # Re-rank by similarity score (highest first)
        all_memories.sort(
            key=lambda m: m.get("similarity", 0.0),
            reverse=True
        )

        # Limit to context_limit (best matches only)
        unique_memories = all_memories[:search_limit]

        # Check maximum relevance - implement passthrough if too low
        max_similarity = max(
            (m.get("similarity", 0.0) for m in unique_memories),
            default=0.0
        )

        # Passthrough threshold: Skip memory augmentation if relevance < 0.6
        PASSTHROUGH_THRESHOLD = 0.6

        if max_similarity < PASSTHROUGH_THRESHOLD:
            logger.info(
                f"[PASSTHROUGH] Max relevance {max_similarity:.3f} < {PASSTHROUGH_THRESHOLD} → "
                f"Skipping memory augmentation, using AI general knowledge"
            )
            return ""  # Empty context = passthrough to AI agent

        logger.info(
            f"Multi-query search complete: {len(queries)} queries → "
            f"{len(all_memories)} total → {len(unique_memories)} unique memories "
            f"(max_relevance: {max_similarity:.3f})"
        )

        # Format context using ContextAssembler's formatting logic
        return self.context_assembler._format_context(unique_memories, intent)

    async def _retrieve_with_new_pipeline(
        self,
        queries: List[str],
        user_id: str,
        intent: IntentType,
        context_limit: int
    ) -> str:
        """NEW: 3-Stage Retrieval Pipeline (Dec 2025).

        Uses the new modular pipeline:
        1. Retriever → RawResults (vector search)
        2. Ranker → ScoredResults (CRS scoring)
        3. ContextBuilder → formatted string (token-budgeted)

        Args:
            queries: Query variations from augmentation
            user_id: User identifier
            intent: Detected intent for context adjustment
            context_limit: Maximum memories to retrieve

        Returns:
            Formatted context string ready for LLM
        """
        from datetime import timezone
        from src.embeddings.openai_embeddings import OpenAIEmbeddings
        from src.retrieval import RawResult

        # Use existing embeddings client from memory_crud
        embeddings = self.memory_crud.openai_embeddings

        logger.info(f"[NEW PIPELINE] Starting 3-stage retrieval for {len(queries)} queries")

        # Adjust limits based on intent
        if intent == IntentType.MEMORY_QUERY:
            search_limit = min(context_limit, 20)
        elif intent == IntentType.ANALYSIS:
            search_limit = min(context_limit, 10)
        else:
            search_limit = context_limit

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 1: Retriever - Get raw results from all query variations
        # ═══════════════════════════════════════════════════════════════════
        all_raw_results: List[RawResult] = []
        seen_uuids = set()

        for i, query in enumerate(queries):
            try:
                # Get embedding for this query (synchronous call)
                query_embedding = embeddings.generate_embedding(query)

                # SPRINT 2 (Feb 2026): Knowledge Preflight Check
                # Implements cognitive "Feeling of Knowing" - skip retrieval if unlikely
                if self.enable_preflight and self.knowledge_preflight:
                    try:
                        if self.knowledge_preflight._initialized:
                            preflight_result = await self.knowledge_preflight.check(
                                query=query,
                                embedding=query_embedding,
                                user_id=user_id,
                            )
                            if preflight_result.signal == KnowledgeSignal.UNLIKELY:
                                logger.info(
                                    f"[NEW PIPELINE] Skipping query {i+1} - "
                                    f"preflight=UNLIKELY (confidence={preflight_result.confidence:.2f})"
                                )
                                continue
                    except Exception as pf_err:
                        logger.warning(f"[NEW PIPELINE] Preflight failed: {pf_err}")

                # Retrieve from Weaviate
                # NOTE: user_id filter disabled for development (desktop uses different ID than imported memories)
                # TODO: Re-enable user filtering when user management is implemented
                raw_results = await self.retriever.retrieve(
                    query_embedding=query_embedding,
                    text_query=query,
                    filters={
                        # "user_id": user_id,  # Disabled: desktop uses 0000...0001, memories use other IDs
                        "privacy_level": ["PUBLIC", "INTERNAL", "CONFIDENTIAL"]
                    },
                    limit=search_limit,
                    sources=["raw", "knowledge"]  # raw=ACMS_Raw_v1 (101K), knowledge=ACMS_Knowledge_v2
                )

                # Deduplicate by UUID
                for result in raw_results:
                    if result.uuid not in seen_uuids:
                        seen_uuids.add(result.uuid)
                        all_raw_results.append(result)

                logger.debug(
                    f"[NEW PIPELINE] Query {i+1}/{len(queries)}: "
                    f"{len(raw_results)} results, {len(all_raw_results)} unique total"
                )

            except Exception as e:
                logger.error(f"[NEW PIPELINE] Error in retrieval for query {i+1}: {e}")
                continue

        if not all_raw_results:
            logger.info("[NEW PIPELINE] No results found, returning empty context")
            return ""

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 2: Ranker - Score with CRS algorithm
        # ═══════════════════════════════════════════════════════════════════
        now = datetime.now(timezone.utc)
        scored_results = self.ranker.score(all_raw_results, now=now)

        # Check if top result meets relevance threshold
        # NOTE: Lowered from 0.6 to 0.5 for testing (more lenient)
        PASSTHROUGH_THRESHOLD = 0.5
        max_similarity = scored_results[0].breakdown["similarity"] if scored_results else 0.0

        if max_similarity < PASSTHROUGH_THRESHOLD:
            logger.info(
                f"[NEW PIPELINE] Max relevance {max_similarity:.3f} < {PASSTHROUGH_THRESHOLD} → "
                f"Skipping memory augmentation (passthrough to AI)"
            )
            return ""

        logger.info(
            f"[NEW PIPELINE] Ranked {len(scored_results)} results, "
            f"top score: {scored_results[0].score:.3f} "
            f"(sim: {scored_results[0].breakdown['similarity']:.3f})"
        )

        # ═══════════════════════════════════════════════════════════════════
        # STAGE 3: ContextBuilder - Token-budgeted assembly
        # ═══════════════════════════════════════════════════════════════════
        context = self.context_builder.build(scored_results[:search_limit])

        logger.info(
            f"[NEW PIPELINE] Built context: {len(context)} chars, "
            f"{len(scored_results[:search_limit])} memories"
        )

        return context

    async def _store_to_raw_collection(
        self,
        query: str,
        answer: str,
        user_id: str,
        agent: str,
        cost_usd: float = 0.0,
        latency_ms: int = 0
    ) -> Optional[str]:
        """Store raw Q&A to ACMS_Raw_v1 collection.

        Args:
            query: User's original query
            answer: Agent's response
            user_id: User identifier
            agent: Agent that generated the response
            cost_usd: Cost of API call
            latency_ms: Response latency

        Returns:
            UUID of stored entry, or None if failed
        """
        try:
            from src.storage.weaviate_client import WeaviateClient
            import hashlib

            weaviate = WeaviateClient()

            # Generate embedding from query (for cache lookup)
            embedding = self.memory_crud.openai_embeddings.generate_embedding(query[:8000])

            # Generate query hash
            query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]

            # Store to ACMS_Raw_v1 - matching actual schema
            # Schema: content, content_hash, user_id, source_type, source_id, agent, privacy_level, tags, cost_usd, created_at
            content = f"Q: {query[:10000]}\nA: {answer[:40000]}"  # Combined Q&A format
            properties = {
                "content": content,
                "content_hash": query_hash,  # Query hash for deduplication
                "user_id": user_id,
                "source_type": "desktop_chat",  # Distinguish from imports
                "source_id": query_hash,  # Use hash as unique ID
                "agent": agent.upper(),  # e.g., CLAUDE_SONNET
                "privacy_level": "PUBLIC",  # Default privacy
                "tags": [],  # No tags initially
                "cost_usd": cost_usd,
                "created_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
            }

            raw_id = weaviate.insert_vector(
                collection="ACMS_Raw_v1",
                vector=embedding,
                data=properties
            )

            logger.info(f"[RawStorage] Stored Q&A to ACMS_Raw_v1: {raw_id[:8]}...")
            return raw_id

        except Exception as e:
            logger.error(f"[RawStorage] Failed to store to ACMS_Raw_v1: {e}")
            return None

    # NOTE: _store_facts_to_knowledge method REMOVED (Dec 2025)
    # Replaced by _store_knowledge_entry which uses ACMS_Knowledge_v2
    # The old method stored individual facts to ACMS_Knowledge_v1 (now deleted)
    # The new method stores full KnowledgeEntry with intent, entities, topics, facts

    async def _store_knowledge_entry(
        self,
        entry: KnowledgeEntry,
        user_id: str
    ) -> Optional[str]:
        """Store extracted knowledge to ACMS_Knowledge_v2 collection.

        Args:
            entry: KnowledgeEntry from KnowledgeExtractor
            user_id: User identifier

        Returns:
            Weaviate UUID of stored entry, or None if failed
        """
        try:
            from src.storage.weaviate_client import WeaviateClient
            import json

            weaviate = WeaviateClient()

            # Generate embedding from canonical query (for similarity search)
            embedding = self.memory_crud.openai_embeddings.generate_embedding(
                entry.canonical_query[:8000]
            )

            # Serialize entities and relations to JSON
            entities_json = json.dumps([
                {"name": e.name, "canonical": e.canonical, "type": e.entity_type, "importance": e.importance}
                for e in entry.entities
            ])
            relations_json = json.dumps([
                {"from": r.from_entity, "to": r.to_entity, "type": r.relation_type}
                for r in entry.relations
            ])

            # Build properties matching ACMS_Knowledge_v2 schema
            properties = {
                "canonical_query": entry.canonical_query,
                "answer_summary": entry.answer_summary,
                "full_answer": entry.full_answer[:50000],  # Truncate very long answers
                "primary_intent": entry.intent.primary_intent,
                "problem_domain": entry.intent.problem_domain,
                "why_context": entry.intent.why_context,
                "user_context_signals": entry.intent.user_context_signals,
                "entities_json": entities_json,
                "relations_json": relations_json,
                "topic_cluster": entry.topic_cluster,
                "related_topics": entry.related_topics,
                "key_facts": entry.key_facts,
                "user_id": user_id,
                "source_query_id": entry.source_query_id or "",
                "extraction_model": entry.extraction_model,
                "extraction_confidence": entry.extraction_confidence,
                "created_at": entry.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "usage_count": 0,
                "feedback_score": 0.0
            }

            weaviate_id = weaviate.insert_vector(
                collection="ACMS_Knowledge_v2",
                vector=embedding,
                data=properties
            )

            logger.info(
                f"[KnowledgeStorage] Stored to ACMS_Knowledge_v2: {weaviate_id[:8]}... "
                f"(topic={entry.topic_cluster})"
            )
            return weaviate_id

        except Exception as e:
            logger.error(f"[KnowledgeStorage] Failed to store knowledge: {e}")
            return None

    # ──────────────────────────────────────────────────────────────────────────
    # PHASE 2: Schema-Driven Context (Feb 2026)
    # Cognitive Architecture Integration - Expertise calibration for LLM prompts
    # ──────────────────────────────────────────────────────────────────────────

    async def _build_expertise_context(self, query: str, user_id: str) -> str:
        """Build schema context from the user's actual topic history.

        Queries PostgreSQL topic_extractions to determine expertise level,
        then builds calibration instructions for the LLM prompt.

        Args:
            query: User's query
            user_id: User identifier

        Returns:
            Schema context string to prepend to system prompt, or empty string
        """
        try:
            # Get topic counts from real data
            topic_counts = await self._get_topic_counts(user_id)
            if not topic_counts:
                return ""

            total = sum(topic_counts.values())

            # Detect which topic this query is about
            detected_topic = self._detect_query_topic(query, list(topic_counts.keys()))
            if not detected_topic or detected_topic not in topic_counts:
                return ""

            # Build topic summaries for expertise calculation
            from dataclasses import dataclass

            @dataclass
            class TopicSummary:
                topic_slug: str
                knowledge_depth: int

            summaries = [
                TopicSummary(topic_slug=t, knowledge_depth=c)
                for t, c in topic_counts.items()
            ]

            # Determine expertise level using the calibrated algorithm
            depth = topic_counts.get(detected_topic, 0)
            level = self.context_assembler._determine_expertise_level(
                detected_topic,
                summaries,
                total_query_count=total
            )

            # Build the calibration instruction
            calibration = self.context_assembler._get_calibration_instructions(level)

            # Get related topics the user knows about (top 5 excluding current)
            related = [
                t for t, c in sorted(topic_counts.items(), key=lambda x: -x[1])[:6]
                if t != detected_topic
            ][:5]

            # Build schema context
            schema_context = f"""USER EXPERTISE CONTEXT:
- Topic: {detected_topic}
- User depth: {depth} past interactions ({level})
- {calibration}
- User's other strong areas: {', '.join(related) if related else 'None identified'}
- Connect to user's existing knowledge where relevant.
"""
            logger.info(
                f"[SchemaContext] Injected for topic={detected_topic}, "
                f"level={level}, depth={depth}"
            )
            return schema_context

        except Exception as e:
            # Never let schema context break the pipeline
            logger.warning(f"Schema context failed: {e}")
            return ""

    async def _get_topic_counts(self, user_id: str = None) -> dict:
        """Query actual topic_extractions table for topic counts.

        Args:
            user_id: Optional user filter (not used currently - single user system)

        Returns:
            Dict mapping topic_slug -> count
        """
        try:
            pool = await get_db_pool()
            async with pool.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT primary_topic, COUNT(*) as count
                    FROM topic_extractions
                    WHERE primary_topic IS NOT NULL
                      AND primary_topic NOT IN ('transient', '', 'general')
                    GROUP BY primary_topic
                    ORDER BY count DESC
                """)
                return {row['primary_topic']: row['count'] for row in rows}
        except Exception as e:
            logger.warning(f"Failed to get topic counts: {e}")
            return {}

    def _detect_query_topic(self, query: str, known_topics: list = None) -> str:
        """Lightweight topic detection from query text.

        Uses keyword matching first against known topics, then falls back
        to general topic keywords.

        Args:
            query: User's query
            known_topics: List of topic slugs from database

        Returns:
            Detected topic slug or None
        """
        query_lower = query.lower()

        # First, try exact match against known topics from database
        if known_topics:
            for topic in known_topics:
                # Check if topic name appears in query
                if topic.lower() in query_lower:
                    return topic

        # General topic keyword mapping for common terms
        TOPIC_KEYWORDS = {
            "llm": ["llm", "language model", "gpt", "transformer", "attention", "prompt", "token"],
            "python": ["python", "pip", "pytest", "django", "flask", "pydantic", "venv"],
            "go": ["golang", "goroutine", "channel", "go module", "go build"],
            "kubernetes": ["kubernetes", "k8s", "kubectl", "pod", "deployment", "helm"],
            "docker": ["docker", "container", "dockerfile", "compose", "image"],
            "security": ["security", "auth", "oauth", "rbac", "encryption", "vulnerability", "exploit"],
            "finance": ["stock", "portfolio", "investment", "market", "etf", "dividend", "trading"],
            "weaviate": ["weaviate", "vector", "embedding", "semantic search", "vectordb"],
            "claude": ["claude", "anthropic", "sonnet", "haiku", "opus"],
            "fastapi": ["fastapi", "fast api", "uvicorn", "starlette"],
            "testing": ["test", "pytest", "unittest", "mock", "coverage", "assertion"],
            "aws": ["aws", "lambda", "s3", "ec2", "cloudformation", "iam"],
            "monitoring": ["monitoring", "prometheus", "grafana", "alert", "metric", "observability"],
            "writing": ["writing", "blog", "article", "document", "report", "essay"],
            "business": ["business", "strategy", "product", "market", "revenue", "startup"],
            "http": ["http", "api", "rest", "endpoint", "request", "response"],
            "database": ["database", "sql", "postgres", "query", "table", "index"],
            "git": ["git", "commit", "branch", "merge", "rebase", "pull request"],
        }

        best_match = None
        best_score = 0

        for topic, keywords in TOPIC_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in query_lower)
            if score > best_score:
                best_score = score
                best_match = topic

        # Also check against known topics from database using keyword approach
        if known_topics and best_match is None:
            for topic in known_topics:
                # Split topic slug into words for matching
                topic_words = topic.lower().replace("-", " ").replace("_", " ").split()
                score = sum(1 for word in topic_words if word in query_lower)
                if score > 0 and score > best_score:
                    best_score = score
                    best_match = topic

        return best_match if best_score > 0 else None


# Global instance
_orchestrator_instance = None


def get_gateway_orchestrator() -> GatewayOrchestrator:
    """Get global gateway orchestrator instance.

    Returns:
        GatewayOrchestrator: Global instance
    """
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = GatewayOrchestrator()
    return _orchestrator_instance
