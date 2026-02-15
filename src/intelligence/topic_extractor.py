"""Topic Extractor for ACMS Intelligence Hub.

Extracts topics from Q&A pairs and memories with:
- LLM-based extraction (highest quality, highest cost)
- Keyword-based extraction (free, deterministic fallback)
- Intent-based extraction (from pre-computed query_intent)

Key Features:
- Idempotent: Same input always returns same output, no duplicates
- Cost-guarded: Budget caps prevent runaway LLM costs
- Versioned: Extraction version allows re-processing on algorithm upgrades

Usage:
    from src.intelligence import TopicExtractor

    extractor = TopicExtractor()

    # Single extraction (idempotent)
    result = await extractor.extract_topics_idempotent(
        source_type="query_history",
        source_id="uuid-123",
        text="Q: How do I deploy to Kubernetes?\\nA: You can use kubectl...",
        user_id="user-456"
    )

    # Batch extraction with budget
    batch_result = await extractor.batch_extract(items, budget_usd=0.10)
"""

import re
import hashlib
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from uuid import uuid4
import asyncio

from sqlalchemy import text

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

EXTRACTOR_VERSION = "v1"  # Bump when extraction logic changes

BATCH_CONFIG = {
    "max_batch_size": 100,              # Max items per batch
    "max_llm_calls_per_batch": 50,      # Cap LLM usage
    "max_tokens_per_batch": 10_000,     # ~$0.05 at Claude Opus rates
    "max_cost_per_batch_usd": 0.10,     # Hard cost cap
    "cooldown_seconds": 60,             # Wait between batches
}

# Common tech topics for keyword extraction
KEYWORD_PATTERNS = {
    # Programming languages
    "python": r"\bpython\b",
    "javascript": r"\bjavascript\b|\bjs\b|\bnode\.js\b|\bnodejs\b",
    "typescript": r"\btypescript\b|\bts\b",
    "rust": r"\brust\b",
    "go": r"\bgolang\b|\bgo\b",
    "java": r"\bjava\b",
    "c++": r"\bc\+\+\b|\bcpp\b",
    "swift": r"\bswift\b",
    "kotlin": r"\bkotlin\b",
    "ruby": r"\bruby\b",
    "php": r"\bphp\b",
    "shell": r"\bbash\b|\bshell\b|\bzsh\b",

    # Frameworks
    "react": r"\breact\b|\breactjs\b",
    "vue": r"\bvue\b|\bvuejs\b",
    "angular": r"\bangular\b",
    "fastapi": r"\bfastapi\b",
    "django": r"\bdjango\b",
    "flask": r"\bflask\b",
    "express": r"\bexpress\b|\bexpressjs\b",
    "electron": r"\belectron\b",
    "nextjs": r"\bnext\.js\b|\bnextjs\b",

    # Infrastructure
    "kubernetes": r"\bkubernetes\b|\bk8s\b",
    "docker": r"\bdocker\b|\bcontainer\b",
    "aws": r"\baws\b|\bamazon web services\b|\bs3\b|\bec2\b|\blambda\b",
    "gcp": r"\bgcp\b|\bgoogle cloud\b",
    "azure": r"\bazure\b|\bmicrosoft azure\b",
    "terraform": r"\bterraform\b",
    "linux": r"\blinux\b|\bubuntu\b|\bdebian\b|\bcentos\b",

    # Databases
    "postgresql": r"\bpostgresql\b|\bpostgres\b|\bpsql\b",
    "mysql": r"\bmysql\b",
    "mongodb": r"\bmongodb\b|\bmongo\b",
    "redis": r"\bredis\b",
    "elasticsearch": r"\belasticsearch\b|\belastic\b",
    "weaviate": r"\bweaviate\b",

    # AI/ML
    "machine-learning": r"\bmachine learning\b|\bml\b",
    "deep-learning": r"\bdeep learning\b|\bneural network\b",
    "llm": r"\bllm\b|\blarge language model\b|\blanguage model\b",
    "claude": r"\bclaude\b|\banthropic\b",
    "openai": r"\bopenai\b|\bgpt\b|\bchatgpt\b",
    "gemini": r"\bgemini\b",
    "embeddings": r"\bembedding\b|\bvector\b",
    "rag": r"\brag\b|\bretrieval augmented\b",
    "ai-agents": r"\bagent\b|\bmulti-agent\b|\bagentic\b",

    # Security
    "security": r"\bsecurity\b|\bauth\b|\bauthentication\b|\bauthorization\b",
    "rbac": r"\brbac\b|\brole.based\b",
    "encryption": r"\bencrypt\b|\bcrypto\b",
    "oauth": r"\boauth\b|\bjwt\b|\btoken\b",

    # DevOps
    "ci-cd": r"\bci/cd\b|\bcicd\b|\bcontinuous integration\b|\bcontinuous deployment\b",
    "git": r"\bgit\b|\bgithub\b|\bgitlab\b",
    "monitoring": r"\bmonitoring\b|\bobservability\b|\bmetrics\b|\blogging\b",

    # API
    "api-design": r"\bapi\b|\brest\b|\bgraphql\b|\bgrpc\b",
    "http": r"\bhttp\b|\bhttps\b|\brendpoint\b",

    # Testing
    "testing": r"\btest\b|\btesting\b|\bunit test\b|\bintegration test\b|\bpytest\b",

    # Data
    "data-engineering": r"\bdata engineering\b|\betl\b|\bdata pipeline\b",
    "sql": r"\bsql\b|\bquery\b",

    # Finance/Investing (common in ChatGPT imports)
    "finance": r"\bstock\b|\bportfolio\b|\byield\b|\bdividend\b|\binvest\b|\btrading\b|\bshares\b|\bmarket\b|\betf\b|\bequity\b|\bvaluation\b",
    "stocks": r"\bnvda\b|\bamd\b|\baapl\b|\bgoog\b|\btsla\b|\bspy\b|\bqqq\b|\boklo\b|\bionq\b|\brigetti\b",

    # Automotive/EV
    "automotive": r"\bcar\b|\bvehicle\b|\bautomotive\b|\bself.driving\b|\bautonomous\b|\bev\b|\btesla\b",

    # Architecture/Review
    "architecture": r"\barchitecture\b|\brefactor\b|\bdesign pattern\b|\bmicroservice\b|\bmonolith\b",
    "code-review": r"\breview\b|\bfeedback\b|\bcode quality\b",

    # Business/Product
    "business": r"\bstartup\b|\bcompany\b|\bproduct\b|\bbusiness\b|\benterprise\b",
    "project-mgmt": r"\bproject\b|\bteam\b|\bchecklist\b|\bplanning\b|\broadmap\b|\bsprint\b",

    # Writing/Documentation
    "writing": r"\bdocument\b|\bwrite\b|\barticle\b|\bblog\b|\bpdf\b|\breport\b",

    # Weather/Geography
    "weather": r"\bweather\b|\btemperature\b|\bclimate\b|\brain\b|\bsnow\b",
}

# LLM prompt for topic extraction
TOPIC_EXTRACTION_PROMPT = """Extract 1-5 topic tags from this Q&A pair.

Rules:
- Use lowercase, hyphenated tags (e.g., "kubernetes", "api-design")
- Be specific (not "programming" but "python-fastapi")
- Focus on the main subject, not incidental mentions
- Return only the tags, comma-separated, no other text

Q: {question}
A: {answer}

Topics:"""


# ============================================================
# DATA CLASSES
# ============================================================

class ExtractionMethod(str, Enum):
    """Methods for topic extraction."""
    LLM = "llm"           # Claude/GPT - highest quality, highest cost
    KEYWORD = "keyword"   # Regex/NLP - free, deterministic
    INTENT = "intent"     # From query_metrics.query_intent - free, pre-computed


@dataclass
class TopicExtractionResult:
    """Result of a single topic extraction."""
    topics: List[str]
    primary_topic: Optional[str]
    method: ExtractionMethod
    confidence: float
    tokens_used: int = 0
    cached: bool = False

    @classmethod
    def from_db(cls, row: Dict[str, Any]) -> "TopicExtractionResult":
        """Create result from database row."""
        return cls(
            topics=row.get("topics", []),
            primary_topic=row.get("primary_topic"),
            method=ExtractionMethod(row.get("extraction_method", "keyword")),
            confidence=row.get("confidence", 0.0),
            tokens_used=row.get("tokens_used", 0),
            cached=True
        )


@dataclass
class BatchExtractionResult:
    """Result of batch topic extraction."""
    results: List[TopicExtractionResult]
    items_processed: int
    total_tokens: int
    total_cost_usd: float
    budget_exhausted: bool
    errors: List[str] = field(default_factory=list)


@dataclass
class ExtractableItem:
    """Item to extract topics from."""
    source_type: Literal["query_history", "memory_items"]
    source_id: str
    text: str
    user_id: str
    tenant_id: str = "default"
    has_intent: bool = False
    intent: Optional[str] = None
    source_created_at: Optional[datetime] = None  # Original record timestamp


# ============================================================
# TOPIC EXTRACTOR CLASS
# ============================================================

class TopicExtractor:
    """Extracts topics from Q&A pairs and memories.

    Features:
    - Idempotent extraction (same input = same output, no duplicates)
    - Cost-guarded batch processing
    - Versioned for re-extraction on upgrades
    """

    def __init__(
        self,
        db_session=None,
        llm_provider=None,
        version: str = EXTRACTOR_VERSION
    ):
        """Initialize topic extractor.

        Args:
            db_session: Database session for caching (optional)
            llm_provider: LLM provider for extraction (optional, falls back to keyword)
            version: Extractor version for idempotency
        """
        self.db = db_session
        self.llm = llm_provider
        self.version = version

        # Compile keyword patterns
        self._keyword_patterns = {
            topic: re.compile(pattern, re.IGNORECASE)
            for topic, pattern in KEYWORD_PATTERNS.items()
        }

        logger.info(f"TopicExtractor initialized (version={version})")

    def select_extraction_method(
        self,
        text_length: int,
        has_intent: bool,
        budget_remaining: float = 0.10
    ) -> ExtractionMethod:
        """Select extraction method based on input characteristics.

        Decision tree:
        1. If query_metrics has query_intent → use INTENT (free, already computed)
        2. If text < 50 chars → use KEYWORD (too short for LLM)
        3. If text > 2000 chars → use KEYWORD (truncation issues with LLM)
        4. If budget exhausted → use KEYWORD
        5. If no LLM provider → use KEYWORD
        6. Otherwise → use LLM (best quality)
        """
        if has_intent:
            return ExtractionMethod.INTENT

        if text_length < 50:
            logger.debug(f"Text too short ({text_length} chars), using KEYWORD")
            return ExtractionMethod.KEYWORD

        if text_length > 2000:
            logger.debug(f"Text too long ({text_length} chars), using KEYWORD")
            return ExtractionMethod.KEYWORD

        if budget_remaining <= 0:
            logger.debug("Budget exhausted, using KEYWORD")
            return ExtractionMethod.KEYWORD

        if self.llm is None:
            logger.debug("No LLM provider, using KEYWORD")
            return ExtractionMethod.KEYWORD

        return ExtractionMethod.LLM

    def extract_topics_keyword(self, text: str) -> List[str]:
        """Extract topics using keyword matching.

        Args:
            text: Text to extract topics from

        Returns:
            List of matched topic tags
        """
        text_lower = text.lower()
        matched = []

        for topic, pattern in self._keyword_patterns.items():
            if pattern.search(text_lower):
                matched.append(topic)

        # Limit to top 5 topics
        return matched[:5]

    async def extract_topics_llm(self, text: str) -> tuple[List[str], int]:
        """Extract topics using LLM.

        Args:
            text: Text to extract topics from

        Returns:
            Tuple of (topics list, tokens used)
        """
        if self.llm is None:
            logger.warning("LLM provider not available, falling back to keyword")
            return self.extract_topics_keyword(text), 0

        try:
            # Parse text into Q&A
            if text.startswith("Q:"):
                parts = text.split("\nA:", 1)
                question = parts[0].replace("Q:", "").strip()
                answer = parts[1].strip() if len(parts) > 1 else ""
            else:
                question = text[:500]
                answer = ""

            # Build prompt
            prompt = TOPIC_EXTRACTION_PROMPT.format(
                question=question[:500],
                answer=answer[:500]
            )

            # Call LLM
            response = await self.llm.generate(
                prompt=prompt,
                max_tokens=100,
                temperature=0.1  # Low temperature for consistency
            )

            # Parse response - expect comma-separated topics
            topics_raw = response.strip()
            topics = [
                t.strip().lower().replace(" ", "-")
                for t in topics_raw.split(",")
                if t.strip()
            ]

            # Estimate tokens (rough)
            tokens_used = len(prompt.split()) + len(response.split())

            return topics[:5], tokens_used

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}, falling back to keyword")
            return self.extract_topics_keyword(text), 0

    def extract_topics_intent(self, intent: str) -> List[str]:
        """Extract topics from query intent.

        Args:
            intent: Query intent from query_metrics (e.g., "ANALYSIS", "FACTUAL")

        Returns:
            List of inferred topic tags
        """
        # Map intents to general topics
        intent_map = {
            "ANALYSIS": ["analysis", "research"],
            "FACTUAL": ["reference"],
            "CREATIVE": ["creative", "brainstorming"],
            "CODE": ["coding", "programming"],
            "DEBUG": ["debugging", "troubleshooting"],
            "EXPLAIN": ["learning", "education"],
        }

        intent_upper = intent.upper() if intent else ""
        return intent_map.get(intent_upper, [])

    def get_idempotency_key(
        self,
        tenant_id: str,
        source_type: str,
        source_id: str
    ) -> str:
        """Generate idempotency key for extraction.

        Args:
            tenant_id: Tenant identifier
            source_type: Source type (query_history, memory_items)
            source_id: Source record ID

        Returns:
            SHA256 hash key
        """
        payload = f"{tenant_id}:{source_type}:{source_id}:{self.version}"
        return hashlib.sha256(payload.encode()).hexdigest()

    async def extract_topics_idempotent(
        self,
        source_type: Literal["query_history", "memory_items"],
        source_id: str,
        text: str,
        user_id: str,
        tenant_id: str = "default",
        has_intent: bool = False,
        intent: Optional[str] = None,
        force_reextract: bool = False,
        trace_id: Optional[str] = None,
        source_created_at: Optional[datetime] = None
    ) -> TopicExtractionResult:
        """Extract topics with idempotency guarantee.

        Idempotency key: (tenant_id, source_type, source_id, extractor_version)

        Behavior:
        - If extraction exists for this key → return cached result
        - If force_reextract=True → delete old, create new
        - Otherwise → extract and save

        Args:
            source_type: 'query_history' or 'memory_items'
            source_id: UUID of source record
            text: Text to extract topics from
            user_id: User who owns the data
            tenant_id: Tenant identifier
            has_intent: Whether query has pre-computed intent
            intent: Pre-computed intent value
            force_reextract: Force re-extraction even if cached
            trace_id: Request trace ID for logging

        Returns:
            TopicExtractionResult with extracted topics
        """
        logger.debug(
            f"Extracting topics: source={source_type}/{source_id}, "
            f"force={force_reextract}, trace={trace_id}"
        )

        # Check cache first (if DB available)
        if self.db is not None and not force_reextract:
            cached = await self._get_cached_extraction(
                tenant_id, source_type, source_id
            )
            if cached is not None:
                logger.debug(f"Using cached extraction for {source_id}")
                return TopicExtractionResult.from_db(cached)

        # Select extraction method
        method = self.select_extraction_method(
            text_length=len(text),
            has_intent=has_intent
        )

        # Extract topics based on method
        tokens_used = 0
        if method == ExtractionMethod.INTENT and intent:
            topics = self.extract_topics_intent(intent)
            confidence = 0.6
        elif method == ExtractionMethod.LLM:
            topics, tokens_used = await self.extract_topics_llm(text)
            confidence = 0.9
        else:
            topics = self.extract_topics_keyword(text)
            confidence = 0.7

        # Ensure at least one topic
        if not topics:
            topics = ["general"]
            confidence = 0.3

        # Create result
        result = TopicExtractionResult(
            topics=topics,
            primary_topic=topics[0] if topics else None,
            method=method,
            confidence=confidence,
            tokens_used=tokens_used,
            cached=False
        )

        # Save to cache (if DB available)
        if self.db is not None:
            await self._save_extraction(
                tenant_id=tenant_id,
                source_type=source_type,
                source_id=source_id,
                user_id=user_id,
                result=result,
                trace_id=trace_id,
                source_created_at=source_created_at
            )

        return result

    async def batch_extract(
        self,
        items: List[ExtractableItem],
        budget_usd: float = 0.10
    ) -> BatchExtractionResult:
        """Extract topics for multiple items with cost guards.

        Guarantees:
        - Never exceeds budget_usd
        - Falls back to KEYWORD if budget exhausted
        - Returns partial results on timeout

        Args:
            items: List of items to extract topics from
            budget_usd: Maximum budget for LLM calls

        Returns:
            BatchExtractionResult with all results and stats
        """
        results = []
        errors = []
        tokens_used = 0
        cost_usd = 0.0
        budget_exhausted = False

        # Limit batch size
        batch = items[:BATCH_CONFIG["max_batch_size"]]
        llm_calls = 0

        for item in batch:
            try:
                # Check budget before each item
                if cost_usd >= budget_usd:
                    budget_exhausted = True

                # Extract with budget awareness
                result = await self.extract_topics_idempotent(
                    source_type=item.source_type,
                    source_id=item.source_id,
                    text=item.text,
                    user_id=item.user_id,
                    tenant_id=item.tenant_id,
                    has_intent=item.has_intent,
                    intent=item.intent,
                    source_created_at=item.source_created_at
                )

                results.append(result)

                # Track costs for LLM calls
                if result.method == ExtractionMethod.LLM and not result.cached:
                    tokens_used += result.tokens_used
                    # Estimate cost at ~$5/1M tokens (Claude Opus input rate)
                    cost_usd += (result.tokens_used / 1_000_000) * 5.0
                    llm_calls += 1

                    # Stop LLM calls if we hit the limit
                    if llm_calls >= BATCH_CONFIG["max_llm_calls_per_batch"]:
                        logger.info(f"Hit LLM call limit ({llm_calls})")
                        budget_exhausted = True

            except Exception as e:
                logger.error(f"Error extracting topics for {item.source_id}: {e}")
                errors.append(f"{item.source_id}: {str(e)}")

        return BatchExtractionResult(
            results=results,
            items_processed=len(results),
            total_tokens=tokens_used,
            total_cost_usd=round(cost_usd, 6),
            budget_exhausted=budget_exhausted,
            errors=errors
        )

    async def _get_cached_extraction(
        self,
        tenant_id: str,
        source_type: str,
        source_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached extraction from database.

        Args:
            tenant_id: Tenant identifier
            source_type: 'query_history' or 'memory_items'
            source_id: UUID of source record

        Returns:
            Dict with extraction data if cached, None otherwise
        """
        if self.db is None:
            return None

        try:
            result = await self.db.execute(text("""
                SELECT id, topics, primary_topic, extraction_method,
                       extractor_version, confidence, tokens_used, created_at
                FROM topic_extractions
                WHERE tenant_id = :tenant_id
                  AND source_type = :source_type
                  AND source_id = :source_id
                  AND extractor_version = :version
            """), {
                "tenant_id": tenant_id,
                "source_type": source_type,
                "source_id": source_id,
                "version": self.version
            })
            row = result.fetchone()
            if row:
                logger.debug(f"Cache hit for topic extraction: {source_id}")
                return dict(row._mapping)
            return None
        except Exception as e:
            logger.error(f"Error fetching cached extraction: {e}")
            return None

    async def _save_extraction(
        self,
        tenant_id: str,
        source_type: str,
        source_id: str,
        user_id: str,
        result: TopicExtractionResult,
        trace_id: Optional[str] = None,
        source_created_at: Optional[datetime] = None
    ) -> None:
        """Save extraction to database with idempotency.

        Uses upsert to handle conflicts gracefully. Same extraction for
        same source will update existing record.

        Args:
            tenant_id: Tenant identifier
            source_type: 'query_history' or 'memory_items'
            source_id: UUID of source record
            user_id: User who owns the data
            result: TopicExtractionResult to save
            trace_id: Request trace ID for logging
            source_created_at: Original timestamp from source record (uses NOW() if None)
        """
        if self.db is None:
            return

        try:
            await self.db.execute(text("""
                INSERT INTO topic_extractions (
                    id, tenant_id, source_type, source_id, user_id,
                    topics, primary_topic, extraction_method, extractor_version,
                    confidence, tokens_used, trace_id, created_at
                ) VALUES (
                    :id, :tenant_id, :source_type, :source_id, :user_id,
                    :topics, :primary_topic, :method, :version,
                    :confidence, :tokens_used, :trace_id, COALESCE(:source_created_at, NOW())
                )
                ON CONFLICT (tenant_id, source_type, source_id, extractor_version)
                DO UPDATE SET
                    topics = EXCLUDED.topics,
                    primary_topic = EXCLUDED.primary_topic,
                    extraction_method = EXCLUDED.extraction_method,
                    confidence = EXCLUDED.confidence,
                    tokens_used = EXCLUDED.tokens_used,
                    trace_id = EXCLUDED.trace_id
            """), {
                "id": str(uuid4()),
                "tenant_id": tenant_id,
                "source_type": source_type,
                "source_id": source_id,
                "user_id": user_id,
                "topics": result.topics,
                "primary_topic": result.primary_topic,
                "method": result.method.value,
                "version": self.version,
                "confidence": result.confidence,
                "tokens_used": result.tokens_used,
                "trace_id": trace_id,
                "source_created_at": source_created_at
            })
            await self.db.commit()
            logger.debug(
                f"Saved topic extraction: {source_type}/{source_id} "
                f"topics={result.topics[:3]}... trace={trace_id}"
            )
        except Exception as e:
            logger.error(f"Error saving topic extraction: {e}")
            # Don't raise - extraction still returns valid result


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_extractable_text(
    source_type: Literal["query_history", "memory_items"],
    record: Dict[str, Any]
) -> str:
    """Get canonical text for topic extraction from a record.

    DECISION: Use question + answer together for richer context.

    Args:
        source_type: Type of source record
        record: Record data

    Returns:
        Text string for extraction
    """
    if source_type == "query_history":
        # Q&A pair - concatenate for context
        question = record.get("question", "")
        answer = record.get("answer", "")[:500]  # Truncate long answers
        return f"Q: {question}\nA: {answer}"

    elif source_type == "memory_items":
        # Memory content only
        return record.get("content", "")

    raise ValueError(f"Unknown source_type: {source_type}")
