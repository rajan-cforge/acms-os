"""Salience Scorer for ACMS Intelligence Pipeline.

Cognitive Principle: Emotional Priority Queue

The brain prioritizes emotionally significant memories for consolidation.
Emotionally charged events (frustration, excitement, breakthrough moments)
create stronger memory traces than neutral experiences.

This module scores queries based on engagement and emotional signals
to prioritize which Q&A pairs deserve full knowledge extraction:

1. Engagement signals (follow-ups, session duration, return visits)
2. Content signals (response length, code presence)
3. Feedback signals (positive/negative)
4. Emotional markers (frustration/excitement keywords)
5. Context window (flashbulb memory effect)

Expected Impact: 20-30% improvement in knowledge extraction quality
by focusing extraction effort on high-value memories.

Usage:
    from src.intelligence.salience_scorer import SalienceScorer

    scorer = SalienceScorer()
    result = await scorer.score(query_context)
    if result.is_high():
        # Prioritize for full extraction
        pass
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Any, Protocol

logger = logging.getLogger(__name__)


class SalienceSignal(Enum):
    """Salience signals that contribute to score.

    Each signal represents a type of engagement or emotional marker
    that indicates memory importance.
    """
    FOLLOW_UP = "follow_up"           # User asked follow-up questions
    POSITIVE_FEEDBACK = "positive_feedback"  # Explicit positive feedback
    LONG_SESSION = "long_session"     # Extended session duration
    LONG_RESPONSE = "long_response"   # Detailed response content
    CODE_PRESENT = "code_present"     # Code in response (technical value)
    RETURN_VISIT = "return_visit"     # Returned to same topic later
    EMOTIONAL_MARKER = "emotional_marker"  # Emotional language detected


# Signal weights - how much each signal contributes to total score
SIGNAL_WEIGHTS: Dict[SalienceSignal, float] = {
    SalienceSignal.FOLLOW_UP: 0.15,
    SalienceSignal.POSITIVE_FEEDBACK: 0.20,
    SalienceSignal.LONG_SESSION: 0.10,
    SalienceSignal.LONG_RESPONSE: 0.10,
    SalienceSignal.CODE_PRESENT: 0.10,
    SalienceSignal.RETURN_VISIT: 0.15,
    SalienceSignal.EMOTIONAL_MARKER: 0.10,
}


@dataclass
class SalienceConfig:
    """Configuration for salience scoring.

    Attributes:
        high_threshold: Score threshold for "high salience" classification
        long_session_threshold_seconds: Minimum seconds for "long session"
        long_response_threshold_words: Minimum words for "long response"
        context_window_minutes: Minutes to look back for context window
        follow_up_weight_decay: How much to decay weight for each follow-up
    """
    high_threshold: float = 0.6
    long_session_threshold_seconds: int = 300  # 5 minutes
    long_response_threshold_words: int = 200
    context_window_minutes: int = 10
    follow_up_weight_decay: float = 0.8  # Each follow-up worth 80% of previous


@dataclass
class SalienceScore:
    """Result of salience scoring.

    Attributes:
        score: Overall salience score (0.0 - 1.0)
        signals_detected: List of signal names that contributed
        signal_contributions: Dict mapping signal to its contribution
        context_window_boost: Additional boost from emotional context
        timestamp: When the score was computed
    """
    score: float
    signals_detected: List[str]
    signal_contributions: Dict[str, float]
    context_window_boost: float
    timestamp: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "score": self.score,
            "signals_detected": self.signals_detected,
            "signal_contributions": self.signal_contributions,
            "context_window_boost": self.context_window_boost,
            "timestamp": self.timestamp.isoformat(),
        }

    def is_high(self, threshold: float = 0.6) -> bool:
        """Check if score exceeds high-salience threshold."""
        return self.score >= threshold


class QueryContext(Protocol):
    """Protocol for query context objects."""
    query_id: str
    user_id: str
    question: str
    answer: str
    created_at: datetime
    session_id: Optional[str]
    session_duration_seconds: Optional[int]
    feedback_type: Optional[str]
    follow_up_count: int
    return_visits: int
    emotional_markers: List[str]


# Emotional marker patterns (frustration, excitement, breakthrough)
EMOTIONAL_PATTERNS = {
    "frustration": [
        r"\b(frustrat|annoying|hate|stupid|awful|terrible|broken|impossible)\w*\b",
        r"\b(why (won\'t|doesn\'t|isn\'t))\b",
        r"\b(keep (getting|seeing|having))\b",
        r"(!{2,})",
    ],
    "excitement": [
        r"\b(amazing|awesome|brilliant|perfect|excellent|fantastic|incredible)\b",
        r"\b(finally|breakthrough|eureka|solved|works?|success)\b",
        r"\b(love|great|thank)\w*\b",
        r"(!{2,})",
    ],
    "urgency": [
        r"\b(urgent|critical|asap|emergency|deadline|production)\b",
        r"\b(broken|down|crashed|failed|error)\b",
    ],
}


class SalienceScorer:
    """Scores queries based on engagement and emotional signals.

    Implements cognitive "Emotional Priority Queue" principle:
    emotionally significant memories get prioritized for consolidation.

    Usage:
        scorer = SalienceScorer()
        result = await scorer.score(query_context)
        if result.is_high():
            # Prioritize for full extraction
            pass
    """

    def __init__(self, config: Optional[SalienceConfig] = None):
        """Initialize salience scorer.

        Args:
            config: Optional configuration overrides
        """
        self.config = config or SalienceConfig()

        # Statistics tracking
        self._total_scored = 0
        self._total_score_sum = 0.0
        self._high_salience_count = 0

        # Context window tracking (session_id -> recent scores)
        self._context_windows: Dict[str, List[float]] = {}

        # Compile emotional patterns for efficiency
        self._emotional_patterns = {}
        for category, patterns in EMOTIONAL_PATTERNS.items():
            self._emotional_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    async def score(self, context: Any) -> SalienceScore:
        """Score a query context for salience.

        Cognitive basis: Emotional Priority Queue
        High-engagement and emotionally significant queries
        are prioritized for memory consolidation.

        Args:
            context: Query context with engagement signals

        Returns:
            SalienceScore with overall score and signal breakdown
        """
        signals_detected: List[str] = []
        signal_contributions: Dict[str, float] = {}
        total_score = 0.0

        # Extract context fields safely
        question = getattr(context, 'question', '') or ''
        answer = getattr(context, 'answer', '') or ''
        feedback_type = getattr(context, 'feedback_type', None)
        follow_up_count = getattr(context, 'follow_up_count', 0) or 0
        return_visits = getattr(context, 'return_visits', 0) or 0
        session_duration = getattr(context, 'session_duration_seconds', None)
        session_id = getattr(context, 'session_id', None)

        # Signal 1: Positive Feedback
        if feedback_type == "positive":
            weight = SIGNAL_WEIGHTS[SalienceSignal.POSITIVE_FEEDBACK]
            signals_detected.append("positive_feedback")
            signal_contributions["positive_feedback"] = weight
            total_score += weight

        # Signal 2: Follow-up Questions
        if follow_up_count > 0:
            # Diminishing returns for each follow-up
            weight = SIGNAL_WEIGHTS[SalienceSignal.FOLLOW_UP]
            contribution = weight * min(follow_up_count, 5) / 5  # Cap at 5
            signals_detected.append("follow_up")
            signal_contributions["follow_up"] = contribution
            total_score += contribution

        # Signal 3: Long Session
        if session_duration and session_duration >= self.config.long_session_threshold_seconds:
            weight = SIGNAL_WEIGHTS[SalienceSignal.LONG_SESSION]
            # Scale by session length (up to 1 hour = full weight)
            duration_factor = min(session_duration / 3600, 1.0)
            contribution = weight * (0.5 + 0.5 * duration_factor)
            signals_detected.append("long_session")
            signal_contributions["long_session"] = contribution
            total_score += contribution

        # Signal 4: Long Response
        if self._is_long_response(answer):
            weight = SIGNAL_WEIGHTS[SalienceSignal.LONG_RESPONSE]
            signals_detected.append("long_response")
            signal_contributions["long_response"] = weight
            total_score += weight

        # Signal 5: Code Present
        if self._has_code(answer):
            weight = SIGNAL_WEIGHTS[SalienceSignal.CODE_PRESENT]
            signals_detected.append("code_present")
            signal_contributions["code_present"] = weight
            total_score += weight

        # Signal 6: Return Visits
        if return_visits > 0:
            weight = SIGNAL_WEIGHTS[SalienceSignal.RETURN_VISIT]
            contribution = weight * min(return_visits, 3) / 3  # Cap at 3
            signals_detected.append("return_visit")
            signal_contributions["return_visit"] = contribution
            total_score += contribution

        # Signal 7: Emotional Markers
        combined_text = f"{question} {answer}"
        emotional_markers = self._detect_emotional_markers(combined_text)
        if emotional_markers:
            weight = SIGNAL_WEIGHTS[SalienceSignal.EMOTIONAL_MARKER]
            # More markers = higher contribution
            contribution = weight * min(len(emotional_markers), 3) / 3
            signals_detected.append("emotional_marker")
            signal_contributions["emotional_marker"] = contribution
            total_score += contribution

        # Context Window Boost (Flashbulb Memory)
        context_boost = 0.0
        if session_id and session_id in self._context_windows:
            recent_scores = self._context_windows[session_id]
            if recent_scores:
                # Boost based on average of recent high scores
                avg_recent = sum(recent_scores) / len(recent_scores)
                if avg_recent > 0.5:
                    context_boost = 0.1 * (avg_recent - 0.5)

        # Apply context boost
        total_score += context_boost

        # Clamp score to [0.0, 1.0]
        total_score = min(max(total_score, 0.0), 1.0)

        # Update context window for this session
        if session_id:
            if session_id not in self._context_windows:
                self._context_windows[session_id] = []
            self._context_windows[session_id].append(total_score)
            # Keep only last 5 scores per session
            self._context_windows[session_id] = self._context_windows[session_id][-5:]

        # Update statistics
        self._total_scored += 1
        self._total_score_sum += total_score
        if total_score >= self.config.high_threshold:
            self._high_salience_count += 1

        return SalienceScore(
            score=total_score,
            signals_detected=signals_detected,
            signal_contributions=signal_contributions,
            context_window_boost=context_boost,
            timestamp=datetime.now(timezone.utc),
        )

    def _has_code(self, text: str) -> bool:
        """Detect if text contains code.

        Args:
            text: Text to check for code patterns

        Returns:
            True if code patterns detected
        """
        if not text:
            return False

        # Check for code blocks
        if "```" in text:
            return True

        # Check for inline code
        if "`" in text:
            return True

        # Check for common code patterns
        code_patterns = [
            r"^\s*def\s+\w+\s*\(",  # Python function
            r"^\s*class\s+\w+",     # Class definition
            r"^\s*import\s+\w+",    # Import statement
            r"^\s*from\s+\w+",      # From import
            r"function\s+\w+\s*\(", # JavaScript function
            r"const\s+\w+\s*=",     # JavaScript const
            r"let\s+\w+\s*=",       # JavaScript let
        ]

        for pattern in code_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return True

        return False

    def _is_long_response(self, text: str) -> bool:
        """Check if response is long (high content value).

        Args:
            text: Response text

        Returns:
            True if word count exceeds threshold
        """
        if not text:
            return False

        word_count = len(text.split())
        return word_count >= self.config.long_response_threshold_words

    def _detect_emotional_markers(self, text: str) -> List[str]:
        """Detect emotional markers in text.

        Cognitive basis: Emotional memories are prioritized.

        Args:
            text: Text to analyze for emotional content

        Returns:
            List of detected emotion categories
        """
        if not text:
            return []

        detected = []
        for category, patterns in self._emotional_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    if category not in detected:
                        detected.append(category)
                    break

        return detected

    def get_stats(self) -> Dict[str, Any]:
        """Get scoring statistics.

        Returns:
            Dict with total_scored, avg_score, high_salience_pct
        """
        avg_score = (
            self._total_score_sum / self._total_scored
            if self._total_scored > 0 else 0.0
        )
        high_pct = (
            self._high_salience_count / self._total_scored * 100
            if self._total_scored > 0 else 0.0
        )

        return {
            "total_scored": self._total_scored,
            "avg_score": round(avg_score, 3),
            "high_salience_pct": round(high_pct, 1),
            "high_threshold": self.config.high_threshold,
            "active_sessions": len(self._context_windows),
        }

    def reset_stats(self) -> None:
        """Reset statistics (for testing)."""
        self._total_scored = 0
        self._total_score_sum = 0.0
        self._high_salience_count = 0
        self._context_windows = {}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

# Global instance
_scorer_instance: Optional[SalienceScorer] = None


def get_salience_scorer() -> SalienceScorer:
    """Get global salience scorer instance."""
    global _scorer_instance
    if _scorer_instance is None:
        _scorer_instance = SalienceScorer()
    return _scorer_instance
