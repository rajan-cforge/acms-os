"""
Unit tests for Memory Categorization (Week 6 Task 1)

Tests the 5-category classification system for organizational intelligence.
"""

import pytest
from src.intelligence.categorizer import (
    MemoryCategory,
    PatternDetector,
    categorize_memory
)


class TestMemoryCategory:
    """Test the MemoryCategory enum"""

    def test_all_categories_defined(self):
        """All 5 categories should be defined"""
        categories = [e.value for e in MemoryCategory]
        assert len(categories) == 5
        assert "PRODUCTIVITY_BLOCKER" in categories
        assert "INNOVATION_IDEA" in categories
        assert "KNOWLEDGE_GAP" in categories
        assert "QUALITY_ISSUE" in categories
        assert "POSITIVE_TREND" in categories


class TestPatternDetector:
    """Test pattern detection logic"""

    def test_detect_productivity_blocker(self):
        """Should detect productivity blockers from negative feedback + keywords"""
        memory = {
            "content": "CI deployment is slow, takes 3 hours every time",
            "feedback": {"rating": 1, "feedback_type": "thumbs_down"},
            "query_count": 12
        }

        detector = PatternDetector()
        category = detector.detect_category(memory)

        assert category == MemoryCategory.PRODUCTIVITY_BLOCKER

    def test_detect_innovation_idea(self):
        """Should detect innovation ideas from positive feedback + keywords"""
        memory = {
            "content": "What if we could automate code reviews with AI?",
            "feedback": {"rating": 5, "feedback_type": "thumbs_up"},
            "query_count": 8
        }

        detector = PatternDetector()
        category = detector.detect_category(memory)

        assert category == MemoryCategory.INNOVATION_IDEA

    def test_detect_knowledge_gap(self):
        """Should detect knowledge gaps from high regenerate rate + repeated questions"""
        memory = {
            "content": "Where is the deployment documentation?",
            "feedback": {"feedback_type": "regenerate"},
            "query_count": 20,
            "regenerate_rate": 0.35  # 35% regenerate rate
        }

        detector = PatternDetector()
        category = detector.detect_category(memory)

        assert category == MemoryCategory.KNOWLEDGE_GAP

    def test_detect_quality_issue(self):
        """Should detect quality issues from negative feedback on specific topics"""
        memory = {
            "content": "Auth service returns 500 errors randomly",
            "feedback": {"rating": 1, "feedback_type": "thumbs_down"},
            "query_count": 15,
            "topic": "authentication"
        }

        detector = PatternDetector()
        category = detector.detect_category(memory)

        assert category == MemoryCategory.QUALITY_ISSUE

    def test_detect_positive_trend(self):
        """Should detect positive trends from recent positive feedback"""
        memory = {
            "content": "New dashboard is much faster and easier to use",
            "feedback": {"rating": 5, "feedback_type": "thumbs_up"},
            "query_count": 10,
            "created_at": "2025-10-22T10:00:00",  # Recent
            "positive_rate": 0.9  # 90% positive
        }

        detector = PatternDetector()
        category = detector.detect_category(memory)

        assert category == MemoryCategory.POSITIVE_TREND

    def test_no_clear_category_returns_none(self):
        """Should return None if no clear category matches"""
        memory = {
            "content": "Just a regular memory without signals",
            "query_count": 1
        }

        detector = PatternDetector()
        category = detector.detect_category(memory)

        assert category is None


class TestCategorizationKeywords:
    """Test keyword matching for each category"""

    def test_productivity_blocker_keywords(self):
        """Should match productivity blocker keywords"""
        detector = PatternDetector()

        # Positive matches
        assert detector._has_blocker_keywords("This is too slow")
        assert detector._has_blocker_keywords("The build is broken")
        assert detector._has_blocker_keywords("Error when trying to deploy")
        assert detector._has_blocker_keywords("Takes too long to complete")

        # Negative matches
        assert not detector._has_blocker_keywords("Everything works great")
        assert not detector._has_blocker_keywords("How do I configure this?")

    def test_innovation_keywords(self):
        """Should match innovation idea keywords"""
        detector = PatternDetector()

        # Positive matches
        assert detector._has_innovation_keywords("Could we automate this?")
        assert detector._has_innovation_keywords("What if we tried a different approach")
        assert detector._has_innovation_keywords("Is there a better way to do this?")

        # Negative matches
        assert not detector._has_innovation_keywords("This is broken")
        assert not detector._has_innovation_keywords("Where is the documentation?")


class TestCategorizeMemoryFunction:
    """Test the main categorize_memory function"""

    def test_categorize_with_feedback_data(self):
        """Should categorize memory using feedback data"""
        memory = {
            "id": "test-123",
            "content": "CI is slow",
            "feedback": {"rating": 1}
        }

        category = categorize_memory(memory)
        assert category == MemoryCategory.PRODUCTIVITY_BLOCKER

    def test_categorize_without_feedback(self):
        """Should handle memories without feedback"""
        memory = {
            "id": "test-456",
            "content": "What is the API endpoint for users?",
            "query_count": 15
        }

        category = categorize_memory(memory)
        assert category == MemoryCategory.KNOWLEDGE_GAP

    def test_categorize_returns_none_for_unclear(self):
        """Should return None for unclear categorization"""
        memory = {
            "id": "test-789",
            "content": "Random note",
            "query_count": 1
        }

        category = categorize_memory(memory)
        assert category is None


class TestCategorizationPriority:
    """Test priority ranking when multiple categories match"""

    def test_productivity_blocker_takes_priority(self):
        """Productivity blockers should take priority over other categories"""
        memory = {
            "content": "What if we could speed up the slow CI? It's broken.",
            "feedback": {"rating": 1, "feedback_type": "thumbs_down"},
            "query_count": 12
        }

        detector = PatternDetector()
        category = detector.detect_category(memory)

        # Should prioritize blocker over innovation
        assert category == MemoryCategory.PRODUCTIVITY_BLOCKER

    def test_quality_issue_priority(self):
        """Quality issues should be detected even with mixed signals"""
        memory = {
            "content": "Auth errors happening frequently in production",
            "feedback": {"rating": 2},
            "query_count": 10,
            "topic": "bugs"
        }

        detector = PatternDetector()
        category = detector.detect_category(memory)

        assert category == MemoryCategory.QUALITY_ISSUE
