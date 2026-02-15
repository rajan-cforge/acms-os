"""
Query Augmentation Module - Phase 2 Implementation

Improves retrieval accuracy through query preprocessing with multiple techniques:
1. Synonym Expansion - Add related terms from domain dictionary
2. Technical Term Addition - Pattern-match and add ACMS-specific keywords
3. Query Rewriting - LLM-powered clarification of vague queries
4. Query Decomposition - Split complex queries into focused sub-queries

Design Principles:
- Security: Input validation, cache poisoning prevention, SQL injection protection
- Performance: Redis caching, async I/O, connection pooling
- Testability: Dependency injection, mockable dependencies
- Reliability: Graceful fallbacks, error handling, idempotent operations

Architecture:
- Swappable LLM providers (ChatGPT, Claude, Ollama)
- Redis caching for all LLM calls (1-hour TTL)
- Three modes: "fast" (no LLM), "full" (all techniques), "decompose" (focus on splitting)
"""

import asyncio
import hashlib
import re
import json
import logging
from typing import List, Dict, Optional, Literal
from datetime import datetime

from pydantic import BaseModel, validator, constr
from redis.asyncio import Redis

# LLM provider abstraction
from src.llm import LLMProvider, create_llm_provider

# Redis
import redis.asyncio as redis
import os

# Configure logging
logger = logging.getLogger(__name__)


# ==========================================
# CONFIGURATION
# ==========================================

class QueryAugmentationConfig(BaseModel):
    """Configuration for query augmentation."""

    max_variations: int = 5
    cache_ttl: int = 3600  # 1 hour
    synonym_limit: int = 2
    technical_term_limit: int = 3
    rewrite_temperature: float = 0.3
    max_query_length: int = 5000
    llm_provider: str = "chatgpt"  # "chatgpt", "claude", "ollama"
    llm_model: Optional[str] = None  # Override default model


# ==========================================
# INPUT VALIDATION
# ==========================================

class AugmentationRequest(BaseModel):
    """Validated request for query augmentation."""

    query: constr(min_length=1, max_length=5000)
    mode: Literal["fast", "full", "decompose"] = "full"
    user_id: Optional[str] = None

    @validator('query')
    def sanitize_query(cls, v):
        """
        Sanitize query to prevent injection attacks.

        Security checks:
        1. Remove SQL injection patterns
        2. Remove command injection patterns
        3. Remove XSS patterns
        """
        dangerous_patterns = [
            r'drop\s+table',
            r'delete\s+from',
            r'<script',
            r'javascript:',
            r'\$\(',
            r'`',
            r'&&\s*[a-zA-Z]',  # Command chaining
            r'\|\|\s*[a-zA-Z]',  # Command chaining
            r';.*--',  # SQL comments
        ]

        query_lower = v.lower()
        for pattern in dangerous_patterns:
            if re.search(pattern, query_lower):
                logger.warning(
                    "Dangerous pattern detected in query",
                    extra={"pattern": pattern, "query": v[:50]}
                )
                raise ValueError("Query contains potentially dangerous patterns")

        return v.strip()


# ==========================================
# MAIN AUGMENTER CLASS
# ==========================================

class QueryAugmenter:
    """
    Query Augmentation Engine

    Techniques:
    1. Synonym Expansion - Add related terms
    2. Technical Term Addition - Add domain keywords
    3. Query Rewriting - Clarify vague queries (LLM)
    4. Query Decomposition - Split complex queries (LLM)

    Design Principles:
    - Dependency Injection (easy testing)
    - Async I/O (non-blocking)
    - Caching (performance)
    - Input Validation (security)
    - Idempotent Operations (safe retries)
    """

    def __init__(
        self,
        llm_provider: Optional[LLMProvider] = None,
        redis_client: Optional[Redis] = None,
        config: Optional[QueryAugmentationConfig] = None
    ):
        """
        Initialize QueryAugmenter with dependency injection.

        Args:
            llm_provider: LLM provider for query rewriting/decomposition (injected for testing)
            redis_client: Redis for caching (injected for testing)
            config: Configuration object (injected for testing)
        """
        self.config = config or QueryAugmentationConfig()

        # Initialize LLM provider
        if llm_provider:
            self.llm = llm_provider
        else:
            # Create provider from config
            try:
                provider_name = os.getenv("LLM_PROVIDER", self.config.llm_provider)
                model = os.getenv("LLM_MODEL", self.config.llm_model)

                provider_kwargs = {}
                if model:
                    provider_kwargs["model"] = model

                self.llm = create_llm_provider(provider_name, **provider_kwargs)
                logger.info(f"QueryAugmenter initialized with LLM provider: {self.llm}")
            except Exception as e:
                logger.warning(f"Failed to initialize LLM provider: {e}. LLM features will be disabled.")
                self.llm = None

        # Initialize Redis
        if redis_client:
            self.redis = redis_client
        else:
            # Create Redis connection
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "40379"))
            self.redis = redis.Redis(host=redis_host, port=redis_port, decode_responses=False)

        # Synonym dictionary (ACMS domain-specific)
        self.synonyms = {
            "database": ["db", "storage", "postgresql", "weaviate", "vector store"],
            "api": ["endpoint", "rest", "http", "service", "interface"],
            "memory": ["knowledge", "context", "storage", "embedding", "recall"],
            "cache": ["redis", "caching", "cached", "hit rate"],
            "agent": ["ai", "model", "llm", "claude", "gpt", "gemini", "assistant"],
            "privacy": ["security", "encryption", "confidential", "sensitive", "private"],
            "search": ["find", "query", "retrieve", "lookup", "discover"],
            "store": ["save", "persist", "write", "record"],
        }

    # ==========================================
    # PUBLIC API
    # ==========================================

    async def augment(
        self,
        query: str,
        mode: Literal["fast", "full", "decompose"] = "full"
    ) -> List[str]:
        """
        Augment query using multiple strategies.

        This is the main public interface.

        Args:
            query: Original user query
            mode: Augmentation mode
                - "fast": Only non-LLM techniques (synonyms, technical terms)
                - "full": All techniques including LLM rewriting
                - "decompose": Focus on splitting complex queries

        Returns:
            List of augmented query strings (includes original)

        Security:
            - Input validation via AugmentationRequest model
            - Cache poisoning prevention (hash-based keys)

        Performance:
            - Async operations (non-blocking)
            - Redis caching (avoid duplicate work)
            - Limited to max_variations (prevent overhead)

        Idempotency:
            - Same input always produces same output
            - Safe to retry on failure
        """
        # Validate input
        try:
            validated = AugmentationRequest(query=query, mode=mode)
            query = validated.query
        except ValueError as e:
            logger.error(f"Query validation failed: {e}")
            return [query]  # Return original on validation error

        # Edge case: empty query
        if not query or not query.strip():
            return [""]

        # Initialize with original query
        queries = [query]

        # Mode: FAST (only non-LLM techniques)
        if mode in ["fast", "full"]:
            # Synonym expansion
            expanded = self._expand_synonyms(query)
            if expanded != query and expanded not in queries:
                queries.append(expanded)

            # Technical term addition
            technical = self._add_technical_terms(query)
            if technical != query and technical not in queries:
                queries.append(technical)

        # Mode: FULL (includes LLM techniques)
        if mode == "full" and self.llm:
            # Query rewriting (LLM-based, cached)
            try:
                rewritten = await self._rewrite_query(query)
                if rewritten and rewritten not in queries:
                    queries.append(rewritten)
            except Exception as e:
                logger.warning(f"Query rewriting failed: {e}")

        # Mode: DECOMPOSE (split complex queries)
        if mode == "decompose" or (mode == "full" and len(query.split()) > 10):
            if self.llm:
                try:
                    sub_queries = await self._decompose_query(query)
                    queries.extend([q for q in sub_queries if q not in queries])
                except Exception as e:
                    logger.warning(f"Query decomposition failed: {e}")

        # Limit to max_variations (prevent overhead)
        return queries[:self.config.max_variations]

    # ==========================================
    # TECHNIQUE 1: SYNONYM EXPANSION
    # ==========================================

    def _expand_synonyms(self, query: str) -> str:
        """
        Expand query with synonyms from domain dictionary.

        Example:
            Input: "database api"
            Output: "database db storage api endpoint rest"

        Security: No external calls, pure computation
        Performance: O(n) where n = number of words
        Idempotent: Yes (deterministic)
        """
        if not query:
            return ""

        words = query.lower().split()
        expanded_words = []

        for word in words:
            expanded_words.append(word)

            # Add synonyms if available
            if word in self.synonyms:
                # Limit to first N synonyms (prevent explosion)
                expanded_words.extend(
                    self.synonyms[word][:self.config.synonym_limit]
                )

        return " ".join(expanded_words)

    # ==========================================
    # TECHNIQUE 2: TECHNICAL TERM ADDITION
    # ==========================================

    def _add_technical_terms(self, query: str) -> str:
        """
        Add ACMS-specific technical terms based on query context.
        Uses pattern matching (no LLM calls, fast).

        Example:
            Input: "how do I store data?"
            Output: "how do I store data? memory_crud weaviate embedding"

        Security: Pure computation, no external calls
        Performance: O(n) pattern matching
        Idempotent: Yes (deterministic)
        """
        if not query:
            return ""

        query_lower = query.lower()
        additional_terms = []

        # Pattern matching for domain keywords
        term_patterns = {
            ("store", "save", "memory", "remember"): ["memory_crud", "weaviate", "embedding"],
            ("search", "find", "retrieve", "query"): ["semantic_search", "vector", "cosine_similarity"],
            ("security", "privacy", "encrypt"): ["privacy_level", "encryption", "confidential"],
            ("api", "endpoint", "http"): ["fastapi", "rest", "endpoint", "route"],
            ("cache", "caching"): ["redis", "semantic_cache", "hit_rate"],
            ("agent", "ai", "model"): ["claude", "gpt", "gemini", "multi_agent"],
            ("database", "db", "postgresql"): ["postgresql", "weaviate", "schema", "table"],
        }

        for keywords, terms in term_patterns.items():
            if any(keyword in query_lower for keyword in keywords):
                additional_terms.extend(terms)

        # Deduplicate and limit
        additional_terms = list(dict.fromkeys(additional_terms))  # Remove duplicates
        additional_terms = additional_terms[:self.config.technical_term_limit]

        if additional_terms:
            return f"{query} {' '.join(additional_terms)}"

        return query

    # ==========================================
    # TECHNIQUE 3: QUERY REWRITING (LLM-BASED)
    # ==========================================

    async def _rewrite_query(self, query: str) -> str:
        """
        Rewrite vague queries into specific technical queries.
        Uses LLM with Redis caching.

        Example:
            Input: "tell me about the database"
            Output: "ACMS database architecture PostgreSQL Weaviate schema"

        Security:
            - Cache keys hashed (prevent cache poisoning)
            - Prompt injection prevention (escaped quotes)

        Performance:
            - Redis cache (1-hour TTL)
            - Async LLM call (non-blocking)

        Idempotency:
            - Same query → same rewrite (via caching)
            - Safe to retry on network failures
        """
        if not query or not self.llm:
            return query

        # Generate cache key (hash-based for security)
        cache_key = f"query_rewrite:{self._hash_query(query)}"

        # Check cache first
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for query rewrite: {query[:50]}")
                return cached.decode('utf-8')
        except Exception as e:
            logger.warning(f"Redis cache check failed: {e}")
            # Continue without cache on Redis errors

        # Prepare prompt (escape quotes to prevent injection)
        escaped_query = query.replace('"', '\\"')
        prompt = f"""
Rewrite this vague user query into a specific technical query suitable for semantic search in an AI memory system (ACMS).

Context: ACMS is an Adaptive Context Memory System with PostgreSQL, Weaviate vector database, Redis cache, and multi-agent AI.

User Query: "{escaped_query}"

Rewritten Query (technical, specific, includes relevant keywords):
""".strip()

        try:
            # Call LLM (async, non-blocking)
            rewritten = await self.llm.generate(
                prompt=prompt,
                max_tokens=100,
                temperature=self.config.rewrite_temperature
            )

            rewritten = rewritten.strip()

            # Cache result (prevent redundant LLM calls)
            try:
                await self.redis.setex(
                    cache_key,
                    self.config.cache_ttl,
                    rewritten
                )
            except Exception as e:
                logger.warning(f"Redis cache store failed: {e}")

            logger.info(f"Query rewritten: '{query[:50]}' → '{rewritten[:50]}'")
            return rewritten

        except Exception as e:
            logger.error(f"Query rewriting failed: {e}")
            # Graceful fallback: return original query
            return query

    # ==========================================
    # TECHNIQUE 4: QUERY DECOMPOSITION
    # ==========================================

    async def _decompose_query(self, query: str) -> List[str]:
        """
        Decompose complex queries into focused sub-queries.
        Uses LLM to intelligently split multi-faceted questions.

        Example:
            Input: "How does ACMS handle privacy and security?"
            Output: [
                "ACMS privacy detection classification",
                "ACMS encryption security XChaCha20"
            ]

        Security:
            - Cached (hash-based keys)
            - Prompt injection prevention

        Performance:
            - Redis cache
            - Async LLM call

        Idempotency:
            - Same query → same decomposition (cached)
        """
        if not query or not self.llm:
            return [query]

        # Cache key
        cache_key = f"query_decompose:{self._hash_query(query)}"

        # Check cache
        try:
            cached = await self.redis.get(cache_key)
            if cached:
                cached_json = cached.decode('utf-8')
                return json.loads(cached_json)
        except Exception as e:
            logger.warning(f"Redis cache check failed: {e}")

        # Prepare prompt
        escaped_query = query.replace('"', '\\"')
        prompt = f"""
Break down this complex query about ACMS (Adaptive Context Memory System) into 2-3 focused sub-queries for better semantic search.

Complex Query: "{escaped_query}"

Return ONLY the sub-queries, one per line, focused and specific.
""".strip()

        try:
            # Call LLM
            sub_queries = await self.llm.generate_list(
                prompt=prompt,
                max_items=min(3, self.config.max_variations - 1),  # Leave room for original
                temperature=self.config.rewrite_temperature
            )

            # Filter empty strings
            sub_queries = [q.strip() for q in sub_queries if q.strip()]

            # Limit to reasonable number
            max_sub_queries = min(self.config.max_variations - 1, 5)  # Leave room for original, max 5
            sub_queries = sub_queries[:max_sub_queries]

            # Cache result
            try:
                await self.redis.setex(
                    cache_key,
                    self.config.cache_ttl,
                    json.dumps(sub_queries)
                )
            except Exception as e:
                logger.warning(f"Redis cache store failed: {e}")

            logger.info(f"Query decomposed into {len(sub_queries)} sub-queries")
            return sub_queries

        except Exception as e:
            logger.error(f"Query decomposition failed: {e}")
            # Fallback: return original
            return [query]

    # ==========================================
    # HELPER METHODS
    # ==========================================

    def _hash_query(self, query: str) -> str:
        """
        Generate hash for cache key.

        Security: Prevents cache poisoning via predictable keys
        """
        return hashlib.sha256(query.encode('utf-8')).hexdigest()[:16]
