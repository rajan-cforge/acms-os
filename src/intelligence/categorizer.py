"""
Memory Categorization for Enterprise Intelligence (Week 6 Task 1)

Automatically categorizes memories into 5 types for organizational insights:
1. Productivity Blockers - Negative feedback + repeated issues
2. Innovation Ideas - Positive feedback + suggestion patterns
3. Knowledge Gaps - High regenerate rate + repeated questions
4. Quality Issues - Negative feedback on specific topics
5. Positive Trends - Recent positive feedback clusters
"""

import re
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class MemoryCategory(Enum):
    """5 categories for enterprise intelligence"""
    PRODUCTIVITY_BLOCKER = "PRODUCTIVITY_BLOCKER"
    INNOVATION_IDEA = "INNOVATION_IDEA"
    KNOWLEDGE_GAP = "KNOWLEDGE_GAP"
    QUALITY_ISSUE = "QUALITY_ISSUE"
    POSITIVE_TREND = "POSITIVE_TREND"


class PatternDetector:
    """
    Detects patterns in memory content and feedback to categorize memories

    Uses keyword matching + feedback signals for classification.
    """

    # Keyword patterns for each category
    BLOCKER_KEYWORDS = [
        'slow', 'broken', 'error', 'failed', 'failure', 'takes too long',
        'doesn\'t work', 'not working', 'issue', 'problem', 'bug'
    ]

    INNOVATION_KEYWORDS = [
        'could we', 'what if', 'better way', 'automate', 'improve',
        'suggestion', 'idea', 'propose', 'consider', 'alternative'
    ]

    KNOWLEDGE_GAP_KEYWORDS = [
        'where is', 'how do i', 'what is', 'documentation', 'docs',
        'can\'t find', 'unable to find', 'don\'t know', 'help with'
    ]

    QUALITY_ISSUE_KEYWORDS = [
        'auth', 'security', 'production', 'crash', 'timeout',
        'performance', 'memory leak', 'race condition', 'bug'
    ]

    POSITIVE_KEYWORDS = [
        'great', 'excellent', 'love', 'fast', 'easy', 'better',
        'improved', 'works well', 'helpful', 'useful'
    ]

    def __init__(self):
        """Initialize pattern detector"""
        pass

    def detect_category(self, memory: Dict[str, Any]) -> Optional[MemoryCategory]:
        """
        Detect category for a given memory

        Args:
            memory: Dict with content, feedback, query_count, etc.

        Returns:
            MemoryCategory or None if unclear

        Priority order:
            1. Quality Issue (most specific - takes precedence when quality keywords present)
            2. Productivity Blocker (general negative feedback)
            3. Knowledge Gap
            4. Innovation Idea
            5. Positive Trend
        """
        content = memory.get('content', '').lower()
        feedback = memory.get('feedback', {})
        query_count = memory.get('query_count', 0)
        regenerate_rate = memory.get('regenerate_rate', 0)
        positive_rate = memory.get('positive_rate', 0)

        # Extract feedback signals
        rating = feedback.get('rating')
        feedback_type = feedback.get('feedback_type', '')

        # 1. Quality Issue (most specific - check first)
        if self._is_quality_issue(content, rating, query_count):
            return MemoryCategory.QUALITY_ISSUE

        # 2. Productivity Blocker (general blockers)
        if self._is_productivity_blocker(content, rating, feedback_type, query_count):
            return MemoryCategory.PRODUCTIVITY_BLOCKER

        # 3. Knowledge Gap
        if self._is_knowledge_gap(content, regenerate_rate, query_count):
            return MemoryCategory.KNOWLEDGE_GAP

        # 4. Innovation Idea
        if self._is_innovation_idea(content, rating, feedback_type):
            return MemoryCategory.INNOVATION_IDEA

        # 5. Positive Trend
        if self._is_positive_trend(content, rating, positive_rate, query_count):
            return MemoryCategory.POSITIVE_TREND

        return None

    def _is_productivity_blocker(
        self,
        content: str,
        rating: Optional[int],
        feedback_type: str,
        query_count: int
    ) -> bool:
        """Check if memory is a productivity blocker"""
        has_negative_feedback = (
            (rating is not None and rating <= 2) or
            feedback_type == 'thumbs_down'
        )
        has_blocker_keywords = self._has_blocker_keywords(content)
        is_repeated = query_count >= 5

        # Need negative feedback + (keywords OR repetition)
        return has_negative_feedback and (has_blocker_keywords or is_repeated)

    def _is_innovation_idea(
        self,
        content: str,
        rating: Optional[int],
        feedback_type: str
    ) -> bool:
        """Check if memory is an innovation idea"""
        has_positive_feedback = (
            (rating is not None and rating >= 4) or
            feedback_type == 'thumbs_up'
        )
        has_innovation_keywords = self._has_innovation_keywords(content)

        return has_positive_feedback and has_innovation_keywords

    def _is_knowledge_gap(
        self,
        content: str,
        regenerate_rate: float,
        query_count: int
    ) -> bool:
        """Check if memory reveals a knowledge gap"""
        has_high_regenerate = regenerate_rate > 0.2  # >20% regenerate
        has_gap_keywords = self._has_knowledge_gap_keywords(content)
        is_repeated = query_count >= 10

        # High regenerate OR (keywords AND repetition)
        return has_high_regenerate or (has_gap_keywords and is_repeated)

    def _is_quality_issue(
        self,
        content: str,
        rating: Optional[int],
        query_count: int
    ) -> bool:
        """Check if memory is a quality issue"""
        has_negative_feedback = rating is not None and rating <= 2
        has_quality_keywords = self._has_quality_keywords(content)
        is_repeated = query_count >= 5  # Lowered to match blocker threshold

        return has_negative_feedback and has_quality_keywords and is_repeated

    def _is_positive_trend(
        self,
        content: str,
        rating: Optional[int],
        positive_rate: float,
        query_count: int
    ) -> bool:
        """Check if memory is a positive trend"""
        has_positive_feedback = rating is not None and rating >= 4
        has_positive_keywords = self._has_positive_keywords(content)
        has_high_positive_rate = positive_rate >= 0.8  # 80%+ positive
        is_mentioned = query_count >= 5

        return (
            has_positive_feedback and
            has_positive_keywords and
            (has_high_positive_rate or is_mentioned)
        )

    def _has_blocker_keywords(self, content: str) -> bool:
        """Check if content contains blocker keywords"""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in self.BLOCKER_KEYWORDS)

    def _has_innovation_keywords(self, content: str) -> bool:
        """Check if content contains innovation keywords"""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in self.INNOVATION_KEYWORDS)

    def _has_knowledge_gap_keywords(self, content: str) -> bool:
        """Check if content contains knowledge gap keywords"""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in self.KNOWLEDGE_GAP_KEYWORDS)

    def _has_quality_keywords(self, content: str) -> bool:
        """Check if content contains quality issue keywords"""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in self.QUALITY_ISSUE_KEYWORDS)

    def _has_positive_keywords(self, content: str) -> bool:
        """Check if content contains positive keywords"""
        content_lower = content.lower()
        return any(keyword in content_lower for keyword in self.POSITIVE_KEYWORDS)


def categorize_memory(memory: Dict[str, Any]) -> Optional[MemoryCategory]:
    """
    Convenience function to categorize a memory

    Args:
        memory: Memory dict with content, feedback, etc.

    Returns:
        MemoryCategory or None

    Example:
        >>> memory = {
        ...     "content": "CI is slow",
        ...     "feedback": {"rating": 1},
        ...     "query_count": 12
        ... }
        >>> category = categorize_memory(memory)
        >>> category == MemoryCategory.PRODUCTIVITY_BLOCKER
        True
    """
    detector = PatternDetector()
    return detector.detect_category(memory)
