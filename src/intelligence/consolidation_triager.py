"""Consolidation Triager for ACMS Intelligence Pipeline.

Cognitive Principle: The hippocampus selectively replays experiences during
sleep consolidation, prioritizing novel, emotionally significant, and
goal-relevant memories. Not everything gets consolidated.

This module implements the same principle for ACMS: triage queries into
different consolidation priority levels to optimize LLM extraction costs
while maintaining knowledge quality.

Expected Impact: 40-60% reduction in LLM extraction costs.

Usage:
    from src.intelligence.consolidation_triager import ConsolidationTriager

    triager = ConsolidationTriager()
    priority = await triager.triage(query_record)

    if priority == ConsolidationPriority.FULL_EXTRACTION:
        await full_knowledge_extraction(query)
    elif priority == ConsolidationPriority.LIGHTWEIGHT_TAGGING:
        await keyword_only_extraction(query)
    else:
        await mark_as_transient(query)
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import UUID

logger = logging.getLogger(__name__)


class ConsolidationPriority(Enum):
    """Priority levels for knowledge consolidation.

    Analogous to hippocampal replay priority during sleep:
    - FULL: Novel, emotionally significant, goal-relevant experiences
    - LIGHT: Routine but potentially useful information
    - TRANSIENT: Ephemeral, throwaway interactions
    """
    FULL_EXTRACTION = "full"        # Full knowledge extraction with Claude
    LIGHTWEIGHT_TAGGING = "light"   # Keyword-only topic tagging, no LLM
    TRANSIENT = "transient"         # Mark for TTL expiration, skip extraction


@dataclass
class QueryRecord:
    """Query record for triage analysis.

    Can be constructed from query_history row or other sources.
    """
    query_id: str
    question: str
    answer: str
    user_id: str
    created_at: datetime
    tenant_id: str = "default"

    # Optional engagement signals
    session_id: Optional[str] = None
    response_source: Optional[str] = None
    total_latency_ms: Optional[int] = None

    # Optional feedback signals
    feedback_type: Optional[str] = None  # "positive", "negative", None

    # Optional context
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TriageResult:
    """Result of triage operation with explanation."""
    priority: ConsolidationPriority
    score: float
    signals_detected: List[str]
    transient_reason: Optional[str] = None


class ConsolidationTriager:
    """Determines consolidation priority for query records.

    Implements value-based triage to optimize LLM extraction costs:
    - High-value interactions get full knowledge extraction
    - Medium-value get lightweight keyword tagging
    - Transient queries are skipped (natural TTL decay)

    Cognitive basis: Hippocampal replay selectivity during sleep.
    """

    # Signals indicating high consolidation value (weights sum to ~1.0)
    HIGH_VALUE_SIGNALS: Dict[str, float] = {
        "follow_up_detected": 0.15,     # User asked follow-ups (engagement)
        "long_response": 0.10,           # Response > 500 words (depth)
        "code_in_response": 0.10,        # Contains code blocks (actionable)
        "explicit_positive_feedback": 0.20,  # Thumbs up (validation)
        "session_duration_gt_5min": 0.10,    # Extended engagement
        "novel_topic": 0.15,             # Topic not in existing clusters
        "code_in_question": 0.05,        # User shared code (context)
        "substantial_question": 0.05,    # Question > 100 chars
        "technical_keywords": 0.05,      # Contains technical terms
        "error_or_debugging": 0.05,      # Problem-solving interaction
    }

    # Patterns indicating transient/throwaway queries
    TRANSIENT_PATTERNS: List[str] = [
        # Time/conversion queries
        r"\b(what time|current time|time in|convert|calculate|translate)\b",
        # Greetings/pleasantries
        r"^(hello|hi|hey|thanks|thank you|goodbye|bye|good morning|good night)\b",
        r"(thanks|thank you|appreciate|great|awesome|perfect|got it)\s*[!.]*$",
        # Very short queries (< 20 chars)
        r"^.{0,20}$",
        # Weather
        r"\bweather\b",
        # Simple factual lookups
        r"^(what is the|who is|when was|where is)\s+\w+\s*\??$",
    ]

    # Technical keywords that suggest valuable content
    TECHNICAL_KEYWORDS: List[str] = [
        r"\b(implement|deploy|configure|debug|optimize|refactor)\b",
        r"\b(error|exception|bug|issue|problem|fix)\b",
        r"\b(api|endpoint|database|server|client)\b",
        r"\b(kubernetes|docker|aws|gcp|azure)\b",
        r"\b(python|javascript|typescript|rust|go)\b",
        r"\b(react|vue|angular|fastapi|django)\b",
    ]

    # Thresholds for priority classification
    FULL_EXTRACTION_THRESHOLD = 0.6
    LIGHTWEIGHT_THRESHOLD = 0.3

    def __init__(
        self,
        db=None,
        enable_follow_up_detection: bool = True,
        enable_topic_novelty_check: bool = True,
        enable_salience_scoring: bool = True,
    ):
        """Initialize the triager.

        Args:
            db: Optional database session for follow-up/novelty checks
            enable_follow_up_detection: Check for follow-up queries
            enable_topic_novelty_check: Check if topic is novel
            enable_salience_scoring: Use salience scorer for engagement signals (Sprint 2)
        """
        self.db = db
        self.enable_follow_up_detection = enable_follow_up_detection
        self.enable_topic_novelty_check = enable_topic_novelty_check
        self.enable_salience_scoring = enable_salience_scoring
        self._compiled_transient = [
            re.compile(p, re.IGNORECASE) for p in self.TRANSIENT_PATTERNS
        ]
        self._compiled_technical = [
            re.compile(p, re.IGNORECASE) for p in self.TECHNICAL_KEYWORDS
        ]

        # Sprint 2: Salience Scorer for engagement signals
        self._salience_scorer = None
        if enable_salience_scoring:
            try:
                from src.intelligence.salience_scorer import get_salience_scorer
                self._salience_scorer = get_salience_scorer()
                logger.info("[ConsolidationTriager] Salience scoring enabled")
            except Exception as e:
                logger.warning(f"[ConsolidationTriager] Salience scoring disabled: {e}")
                self.enable_salience_scoring = False

        # Statistics for monitoring
        self.stats = {
            "total_triaged": 0,
            "full_count": 0,
            "light_count": 0,
            "transient_count": 0,
            "salience_boost_count": 0,  # Sprint 2: Track salience boosts
        }

    async def triage(self, record: QueryRecord) -> TriageResult:
        """Determine consolidation priority for a query record.

        Args:
            record: QueryRecord to analyze

        Returns:
            TriageResult with priority, score, and explanation
        """
        # Fast path: Check for transient patterns first
        transient_reason = self._check_transient(record.question)
        if transient_reason:
            self.stats["total_triaged"] += 1
            self.stats["transient_count"] += 1
            return TriageResult(
                priority=ConsolidationPriority.TRANSIENT,
                score=0.0,
                signals_detected=[],
                transient_reason=transient_reason
            )

        # Calculate consolidation score from signals
        score = 0.5  # Base score
        signals_detected = []

        # Content-based signals (sync, no DB needed)
        if self._has_long_response(record.answer):
            score += self.HIGH_VALUE_SIGNALS["long_response"]
            signals_detected.append("long_response")

        if self._has_code_block(record.answer):
            score += self.HIGH_VALUE_SIGNALS["code_in_response"]
            signals_detected.append("code_in_response")

        if self._has_code_block(record.question):
            score += self.HIGH_VALUE_SIGNALS["code_in_question"]
            signals_detected.append("code_in_question")

        if self._is_substantial_question(record.question):
            score += self.HIGH_VALUE_SIGNALS["substantial_question"]
            signals_detected.append("substantial_question")

        if self._has_technical_keywords(record.question, record.answer):
            score += self.HIGH_VALUE_SIGNALS["technical_keywords"]
            signals_detected.append("technical_keywords")

        if self._is_error_or_debugging(record.question):
            score += self.HIGH_VALUE_SIGNALS["error_or_debugging"]
            signals_detected.append("error_or_debugging")

        # Feedback signal
        if record.feedback_type == "positive":
            score += self.HIGH_VALUE_SIGNALS["explicit_positive_feedback"]
            signals_detected.append("explicit_positive_feedback")
        elif record.feedback_type == "negative":
            # Negative feedback still indicates engagement, but less priority
            score += 0.05
            signals_detected.append("explicit_negative_feedback")

        # Async signals (require DB)
        if self.db and self.enable_follow_up_detection:
            has_follow_ups = await self._check_follow_ups(record)
            if has_follow_ups:
                score += self.HIGH_VALUE_SIGNALS["follow_up_detected"]
                signals_detected.append("follow_up_detected")

        if self.db and self.enable_topic_novelty_check:
            is_novel = await self._check_topic_novelty(record)
            if is_novel:
                score += self.HIGH_VALUE_SIGNALS["novel_topic"]
                signals_detected.append("novel_topic")

        # Sprint 2: Salience Scoring (Emotional Priority Queue)
        # Use engagement signals to boost consolidation priority
        if self.enable_salience_scoring and self._salience_scorer:
            try:
                salience_result = await self._salience_scorer.score(record)
                if salience_result.is_high(threshold=0.5):
                    # Boost score based on salience (max +0.15)
                    salience_boost = min(salience_result.score * 0.15, 0.15)
                    score += salience_boost
                    signals_detected.append("high_salience")
                    self.stats["salience_boost_count"] += 1
                    logger.debug(
                        f"[ConsolidationTriager] Salience boost applied: "
                        f"+{salience_boost:.2f} (salience={salience_result.score:.2f})"
                    )
            except Exception as e:
                logger.warning(f"[ConsolidationTriager] Salience scoring failed: {e}")

        # Determine priority from score
        score = min(score, 1.0)

        if score >= self.FULL_EXTRACTION_THRESHOLD:
            priority = ConsolidationPriority.FULL_EXTRACTION
            self.stats["full_count"] += 1
        elif score >= self.LIGHTWEIGHT_THRESHOLD:
            priority = ConsolidationPriority.LIGHTWEIGHT_TAGGING
            self.stats["light_count"] += 1
        else:
            priority = ConsolidationPriority.TRANSIENT
            self.stats["transient_count"] += 1

        self.stats["total_triaged"] += 1

        return TriageResult(
            priority=priority,
            score=score,
            signals_detected=signals_detected
        )

    async def batch_triage(
        self,
        records: List[QueryRecord]
    ) -> Dict[ConsolidationPriority, List[QueryRecord]]:
        """Triage a batch of records and group by priority.

        Args:
            records: List of QueryRecord to triage

        Returns:
            Dict mapping priority to list of records
        """
        result = {
            ConsolidationPriority.FULL_EXTRACTION: [],
            ConsolidationPriority.LIGHTWEIGHT_TAGGING: [],
            ConsolidationPriority.TRANSIENT: [],
        }

        for record in records:
            triage_result = await self.triage(record)
            result[triage_result.priority].append(record)

        logger.info(
            f"[ConsolidationTriager] Batch triage: "
            f"{len(result[ConsolidationPriority.FULL_EXTRACTION])} full, "
            f"{len(result[ConsolidationPriority.LIGHTWEIGHT_TAGGING])} light, "
            f"{len(result[ConsolidationPriority.TRANSIENT])} transient"
        )

        return result

    def _check_transient(self, question: str) -> Optional[str]:
        """Check if query matches transient patterns.

        Returns:
            Reason string if transient, None otherwise
        """
        question_lower = question.strip().lower()

        for i, pattern in enumerate(self._compiled_transient):
            if pattern.search(question_lower):
                return f"matches_transient_pattern_{i}"

        return None

    def _has_long_response(self, answer: str, min_words: int = 500) -> bool:
        """Check if response is substantial (> 500 words)."""
        if not answer:
            return False
        return len(answer.split()) > min_words

    def _has_code_block(self, text: str) -> bool:
        """Check if text contains code blocks."""
        if not text:
            return False
        # Markdown code blocks or significant indentation patterns
        return "```" in text or bool(re.search(r'\n\s{4,}\S', text))

    def _is_substantial_question(self, question: str, min_chars: int = 100) -> bool:
        """Check if question is substantial (> 100 chars)."""
        if not question:
            return False
        return len(question.strip()) > min_chars

    def _has_technical_keywords(self, question: str, answer: str) -> bool:
        """Check if content contains technical keywords."""
        combined = f"{question or ''} {answer or ''}".lower()
        return any(p.search(combined) for p in self._compiled_technical)

    def _is_error_or_debugging(self, question: str) -> bool:
        """Check if question is about error/debugging."""
        if not question:
            return False
        error_patterns = [
            r"\berror\b",
            r"\bexception\b",
            r"\bfailed\b",
            r"\bnot working\b",
            r"\bdoesn't work\b",
            r"\bbroken\b",
            r"\bbug\b",
            r"\bdebug\b",
            r"\bfix\b",
            r"\btraceback\b",
        ]
        question_lower = question.lower()
        return any(re.search(p, question_lower) for p in error_patterns)

    async def _check_follow_ups(self, record: QueryRecord) -> bool:
        """Check if this query had follow-up questions.

        Looks for queries from the same session within 30 minutes after this one.
        """
        if not self.db or not record.session_id:
            return False

        try:
            from sqlalchemy import text

            result = await self.db.execute(text("""
                SELECT COUNT(*) as follow_up_count
                FROM query_history
                WHERE session_id = :session_id
                  AND user_id = :user_id
                  AND created_at > :created_at
                  AND created_at < :created_at + INTERVAL '30 minutes'
            """), {
                "session_id": record.session_id,
                "user_id": record.user_id,
                "created_at": record.created_at,
            })

            row = result.fetchone()
            return row and row.follow_up_count >= 2

        except Exception as e:
            logger.warning(f"[ConsolidationTriager] Follow-up check failed: {e}")
            return False

    async def _check_topic_novelty(self, record: QueryRecord) -> bool:
        """Check if this query introduces a novel topic.

        A topic is novel if it doesn't appear in the user's existing
        topic_extractions with confidence > 0.5.
        """
        if not self.db:
            return False

        try:
            from sqlalchemy import text

            # Extract keywords from question (simple approach)
            keywords = self._extract_keywords(record.question)
            if not keywords:
                return False

            # Check if any keywords are already in user's topics
            placeholders = ", ".join([f":kw{i}" for i in range(len(keywords))])
            params = {f"kw{i}": kw for i, kw in enumerate(keywords)}
            params["user_id"] = record.user_id

            result = await self.db.execute(text(f"""
                SELECT COUNT(*) as existing_count
                FROM topic_extractions
                WHERE user_id = :user_id
                  AND confidence > 0.5
                  AND primary_topic IN ({placeholders})
            """), params)

            row = result.fetchone()
            # Novel if no existing high-confidence topics match
            return row and row.existing_count == 0

        except Exception as e:
            logger.warning(f"[ConsolidationTriager] Topic novelty check failed: {e}")
            return False

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract potential topic keywords from text.

        Simple approach: look for matches against known tech keywords.
        """
        if not text:
            return []

        keywords = []
        text_lower = text.lower()

        # Common tech topics
        tech_keywords = [
            "python", "javascript", "typescript", "rust", "go", "java",
            "kubernetes", "docker", "aws", "gcp", "azure",
            "react", "vue", "angular", "fastapi", "django",
            "postgresql", "mongodb", "redis", "elasticsearch",
            "machine-learning", "deep-learning", "llm", "embeddings",
            "security", "authentication", "oauth", "rbac",
            "api", "graphql", "rest", "grpc",
        ]

        for kw in tech_keywords:
            if kw in text_lower:
                keywords.append(kw)

        return keywords[:5]  # Limit to top 5

    def get_stats(self) -> Dict[str, Any]:
        """Get triage statistics."""
        total = self.stats["total_triaged"]
        if total == 0:
            return {**self.stats, "full_pct": 0, "light_pct": 0, "transient_pct": 0}

        return {
            **self.stats,
            "full_pct": round(self.stats["full_count"] / total * 100, 1),
            "light_pct": round(self.stats["light_count"] / total * 100, 1),
            "transient_pct": round(self.stats["transient_count"] / total * 100, 1),
        }

    def reset_stats(self):
        """Reset statistics."""
        self.stats = {
            "total_triaged": 0,
            "full_count": 0,
            "light_count": 0,
            "transient_count": 0,
        }


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def create_query_record_from_row(row: Dict[str, Any]) -> QueryRecord:
    """Create QueryRecord from database row.

    Args:
        row: Dict from query_history table

    Returns:
        QueryRecord instance
    """
    return QueryRecord(
        query_id=str(row.get('query_id', '')),
        question=row.get('question', ''),
        answer=row.get('answer', ''),
        user_id=str(row.get('user_id', '')),
        created_at=row.get('created_at', datetime.utcnow()),
        tenant_id=row.get('tenant_id', 'default'),
        session_id=row.get('session_id'),
        response_source=row.get('response_source'),
        total_latency_ms=row.get('total_latency_ms'),
        feedback_type=row.get('feedback_type'),
        metadata=row.get('metadata'),
    )
