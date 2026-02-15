"""Adaptive Threshold Resolver for ACMS Retrieval Pipeline.

Cognitive Principle: Pattern Separation vs Pattern Completion.

The hippocampus uses different neural circuits for different retrieval tasks:
- Dentate Gyrus (Pattern Separation): Distinguishes similar memories
  → Use HIGH thresholds for exact recall queries
- CA3 (Pattern Completion): Recalls full memory from partial cues
  → Use LOWER thresholds for exploratory queries

This module implements adaptive similarity thresholds based on query intent,
replacing the fixed thresholds (0.95/0.85/0.60) with context-aware values.

Usage:
    from src.retrieval.threshold_resolver import ThresholdResolver

    resolver = ThresholdResolver()
    thresholds = resolver.resolve("What was the exact command I used?")

    # thresholds.cache  → 0.96 (high for exact recall)
    # thresholds.raw    → 0.90
    # thresholds.knowledge → 0.80

    thresholds = resolver.resolve("What do I know about Kubernetes?")

    # thresholds.cache  → 0.92 (lower for exploration)
    # thresholds.raw    → 0.75
    # thresholds.knowledge → 0.55
"""

import re
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class RetrievalMode(Enum):
    """Retrieval modes based on query intent.

    Cognitive basis:
    - EXACT_RECALL: Pattern separation (Dentate Gyrus)
    - CONCEPTUAL_EXPLORE: Pattern completion (CA3)
    - TROUBLESHOOT: Balanced recall (both circuits)
    - COMPARE: Diverse recall (multiple memory traces)
    - DEFAULT: Standard retrieval
    """
    EXACT_RECALL = "exact"          # "What was the command..."
    CONCEPTUAL_EXPLORE = "explore"  # "What do I know about..."
    TROUBLESHOOT = "troubleshoot"   # "Why is X failing..."
    COMPARE = "compare"             # "Difference between X and Y"
    DEFAULT = "default"             # Standard queries


@dataclass(frozen=True)
class ThresholdSet:
    """Similarity thresholds for different memory stores.

    Attributes:
        cache: QualityCache (semantic dedup) threshold
        raw: ACMS_Raw_v1 (verbatim Q&A) threshold
        knowledge: ACMS_Knowledge_v2 (extracted facts) threshold
    """
    cache: float
    raw: float
    knowledge: float

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary for serialization."""
        return {
            "cache": self.cache,
            "raw": self.raw,
            "knowledge": self.knowledge,
        }


# ============================================================
# THRESHOLD CONFIGURATION
# ============================================================

# Threshold map based on retrieval mode
# Higher thresholds = more precision, fewer results
# Lower thresholds = more recall, more results

THRESHOLD_MAP: Dict[RetrievalMode, ThresholdSet] = {
    # EXACT RECALL: Pattern separation
    # User wants to retrieve a specific memory exactly as stored
    # High thresholds to avoid returning similar but wrong memories
    RetrievalMode.EXACT_RECALL: ThresholdSet(
        cache=0.96,      # Very high - only near-exact matches
        raw=0.90,        # High - close semantic match
        knowledge=0.80,  # Moderately high - relevant knowledge
    ),

    # CONCEPTUAL EXPLORE: Pattern completion
    # User wants to explore what they know about a topic
    # Lower thresholds to allow associative recall
    RetrievalMode.CONCEPTUAL_EXPLORE: ThresholdSet(
        cache=0.92,      # Allow related cached queries
        raw=0.75,        # Allow topically related Q&As
        knowledge=0.55,  # Allow broad knowledge matching
    ),

    # TROUBLESHOOT: Balanced recall
    # User needs both exact errors AND related context
    # Moderate thresholds for balanced retrieval
    RetrievalMode.TROUBLESHOOT: ThresholdSet(
        cache=0.90,      # Allow recent similar issues
        raw=0.80,        # Match error-related Q&As
        knowledge=0.60,  # Include troubleshooting knowledge
    ),

    # COMPARE: Diverse recall
    # User needs information about multiple distinct topics
    # Lower knowledge threshold to gather diverse sources
    RetrievalMode.COMPARE: ThresholdSet(
        cache=0.94,      # Allow queries about either topic
        raw=0.82,        # Match Q&As about both topics
        knowledge=0.55,  # Low threshold to get both topics
    ),

    # DEFAULT: Standard retrieval
    # Balanced thresholds for general queries
    RetrievalMode.DEFAULT: ThresholdSet(
        cache=0.95,      # Standard cache matching
        raw=0.85,        # Standard raw matching
        knowledge=0.60,  # Standard knowledge matching
    ),
}


# ============================================================
# INTENT DETECTION PATTERNS
# ============================================================

# Patterns for detecting exact recall intent
EXACT_RECALL_PATTERNS = [
    r"\bwhat was the exact\b",
    r"\bwhat were the\b",
    r"\bshow me the exact\b",
    r"\bwhat (?:was (?:the )?)?command\b",
    r"\bwhat (?:was (?:the )?)?configuration\b",
    r"\bwhat (?:was (?:the )?)?credentials?\b",
    r"\bexact error\b",
    r"\bexact message\b",
    r"\bspecific\s+(?:command|config|error|value)\b",
    r"\bconfiguration value\b",
]

# Patterns for detecting conceptual exploration intent
CONCEPTUAL_EXPLORE_PATTERNS = [
    r"\bwhat do i know about\b",
    r"\btell me everything about\b",
    r"\bwhat have i learned about\b",
    r"\bsummarize (?:my|our) knowledge\b",
    r"\bwhat topics\b",
    r"\bwhat have we discussed\b",
    r"\boverview of\b",
]

# Patterns for detecting troubleshooting intent
TROUBLESHOOT_PATTERNS = [
    r"\bwhy is\b.*\b(?:fail|error|not work|broken|crash)\b",
    r"\bdebug\b",
    r"\bfix\b.*\b(?:error|issue|problem)\b",
    r"\btroubleshoot\b",
    r"\bdiagnose\b",
    r"\bwhat'?s? causing\b",
    r"\bnot working\b",
    r"\bfailing\b",
    r"\bcrash\b",
]

# Patterns for detecting comparison intent
COMPARE_PATTERNS = [
    r"\bdifference between\b",
    r"\bcompare\b",
    r"\bvs\.?\b",
    r"\bversus\b",
    r"\bhow does .+ compare\b",
    r"\bwhich is better\b",
    r"\b(?:what|how) .+ different\b",
]


def resolve_retrieval_mode(
    query: str,
    intent_hint: Optional[str] = None
) -> RetrievalMode:
    """Detect retrieval mode from query text and optional intent hint.

    Args:
        query: The user's query text
        intent_hint: Optional explicit intent from UI/API ("exact", "explore", etc.)

    Returns:
        RetrievalMode enum value
    """
    # Explicit intent hint takes precedence
    if intent_hint:
        hint_lower = intent_hint.lower()
        if hint_lower in ("exact", "exact_recall"):
            return RetrievalMode.EXACT_RECALL
        elif hint_lower in ("explore", "conceptual", "conceptual_explore"):
            return RetrievalMode.CONCEPTUAL_EXPLORE
        elif hint_lower in ("troubleshoot", "debug", "fix"):
            return RetrievalMode.TROUBLESHOOT
        elif hint_lower in ("compare", "diff", "difference"):
            return RetrievalMode.COMPARE

    if not query:
        return RetrievalMode.DEFAULT

    query_lower = query.lower()

    # Check patterns in order of specificity

    # Exact recall patterns (most specific)
    for pattern in EXACT_RECALL_PATTERNS:
        if re.search(pattern, query_lower):
            return RetrievalMode.EXACT_RECALL

    # Troubleshoot patterns
    for pattern in TROUBLESHOOT_PATTERNS:
        if re.search(pattern, query_lower):
            return RetrievalMode.TROUBLESHOOT

    # Compare patterns
    for pattern in COMPARE_PATTERNS:
        if re.search(pattern, query_lower):
            return RetrievalMode.COMPARE

    # Conceptual explore patterns
    for pattern in CONCEPTUAL_EXPLORE_PATTERNS:
        if re.search(pattern, query_lower):
            return RetrievalMode.CONCEPTUAL_EXPLORE

    # Default for ambiguous queries
    return RetrievalMode.DEFAULT


class ThresholdResolver:
    """Resolves adaptive similarity thresholds based on query intent.

    Implements cognitive-inspired threshold adaptation:
    - Pattern separation for exact recall (high thresholds)
    - Pattern completion for exploration (low thresholds)
    - Balanced retrieval for troubleshooting (moderate thresholds)
    """

    def __init__(self):
        """Initialize the threshold resolver."""
        # Pre-compile patterns for efficiency
        self._exact_patterns = [
            re.compile(p, re.IGNORECASE) for p in EXACT_RECALL_PATTERNS
        ]
        self._explore_patterns = [
            re.compile(p, re.IGNORECASE) for p in CONCEPTUAL_EXPLORE_PATTERNS
        ]
        self._troubleshoot_patterns = [
            re.compile(p, re.IGNORECASE) for p in TROUBLESHOOT_PATTERNS
        ]
        self._compare_patterns = [
            re.compile(p, re.IGNORECASE) for p in COMPARE_PATTERNS
        ]

    def resolve(
        self,
        query: str,
        mode: Optional[RetrievalMode] = None,
        intent_hint: Optional[str] = None,
    ) -> ThresholdSet:
        """Resolve thresholds for a query.

        Args:
            query: The query text
            mode: Optional explicit mode (overrides detection)
            intent_hint: Optional intent hint string

        Returns:
            ThresholdSet with cache, raw, and knowledge thresholds
        """
        if mode is None:
            mode = self.get_mode(query, intent_hint)

        # Return a copy of the threshold set
        original = THRESHOLD_MAP[mode]
        return ThresholdSet(
            cache=original.cache,
            raw=original.raw,
            knowledge=original.knowledge,
        )

    def get_mode(
        self,
        query: str,
        intent_hint: Optional[str] = None
    ) -> RetrievalMode:
        """Get the retrieval mode for a query without resolving thresholds.

        Args:
            query: The query text
            intent_hint: Optional intent hint string

        Returns:
            RetrievalMode enum value
        """
        return resolve_retrieval_mode(query, intent_hint)

    def get_thresholds_for_mode(self, mode: RetrievalMode) -> ThresholdSet:
        """Get thresholds for a specific mode.

        Args:
            mode: The retrieval mode

        Returns:
            ThresholdSet for the mode
        """
        original = THRESHOLD_MAP[mode]
        return ThresholdSet(
            cache=original.cache,
            raw=original.raw,
            knowledge=original.knowledge,
        )


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_default_thresholds() -> ThresholdSet:
    """Get the default threshold set.

    Returns:
        ThresholdSet with default values (0.95/0.85/0.60)
    """
    return ThresholdSet(
        cache=THRESHOLD_MAP[RetrievalMode.DEFAULT].cache,
        raw=THRESHOLD_MAP[RetrievalMode.DEFAULT].raw,
        knowledge=THRESHOLD_MAP[RetrievalMode.DEFAULT].knowledge,
    )


def get_thresholds_for_intent(intent: str) -> ThresholdSet:
    """Get thresholds from an intent string.

    Args:
        intent: Intent string like "exact", "explore", etc.

    Returns:
        ThresholdSet for the intent
    """
    resolver = ThresholdResolver()
    return resolver.resolve("", intent_hint=intent)
