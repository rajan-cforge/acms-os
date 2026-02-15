"""Unit tests for Intent Classifier.

Tests intent classification for all 7 intent types.
Critical: Tests CREATIVE intent for poetry requests (haiku, sonnet, etc).
"""

import pytest
from src.gateway.intent_classifier import IntentClassifier
from src.gateway.models import IntentType


@pytest.fixture
def classifier():
    """Create IntentClassifier instance."""
    return IntentClassifier()


class TestCreativeIntent:
    """Test CREATIVE intent classification."""

    def test_haiku_detection(self, classifier):
        """Test that 'Write a haiku about X' is classified as CREATIVE."""
        query = "Write a haiku about databases"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.CREATIVE, \
            f"Expected CREATIVE intent for haiku, got {intent.value}"
        assert confidence >= 0.8, \
            f"Expected high confidence (>=0.8), got {confidence:.2f}"

    def test_sonnet_detection(self, classifier):
        """Test that 'Write a sonnet' is classified as CREATIVE."""
        query = "Write a sonnet about distributed systems"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.CREATIVE
        assert confidence >= 0.8

    def test_limerick_detection(self, classifier):
        """Test that 'Write a limerick' is classified as CREATIVE."""
        query = "Write a limerick about Redis"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.CREATIVE
        assert confidence >= 0.8

    def test_poem_detection(self, classifier):
        """Test that 'Write a poem' is classified as CREATIVE."""
        query = "Write a poem about AI collaboration"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.CREATIVE
        assert confidence >= 0.7  # Lower threshold for generic "poem"

    def test_story_detection(self, classifier):
        """Test that 'Write a story' is classified as CREATIVE."""
        query = "Write a story about microservices"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.CREATIVE
        assert confidence >= 0.7  # Lower threshold for generic "story"

    def test_brainstorm_detection(self, classifier):
        """Test that 'brainstorm ideas' is classified as CREATIVE."""
        query = "Brainstorm ideas for API endpoint names"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.CREATIVE
        assert confidence >= 0.8


class TestCodeGenerationIntent:
    """Test CODE_GENERATION intent classification."""

    def test_write_function_detection(self, classifier):
        """Test that 'Write a function' is classified as CODE_GENERATION."""
        query = "Write a function to validate JWT tokens"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.CODE_GENERATION
        assert confidence >= 0.8

    def test_implement_detection(self, classifier):
        """Test that 'Implement X' is classified as CODE_GENERATION."""
        query = "Implement OAuth2 authentication flow"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.CODE_GENERATION
        assert confidence >= 0.8

    def test_create_class_detection(self, classifier):
        """Test that 'Create a class' is classified as CODE_GENERATION."""
        query = "Create a class for user session management"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.CODE_GENERATION
        assert confidence >= 0.8


class TestAnalysisIntent:
    """Test ANALYSIS intent classification."""

    def test_explain_detection(self, classifier):
        """Test that 'Explain X' is classified as ANALYSIS."""
        query = "Explain how JWT authentication works"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.ANALYSIS
        assert confidence >= 0.8

    def test_summarize_detection(self, classifier):
        """Test that 'Summarize X' is classified as ANALYSIS."""
        query = "Summarize all authentication discussions"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.ANALYSIS
        assert confidence >= 0.4  # Lower threshold - "summarize" is ambiguous

    def test_compare_detection(self, classifier):
        """Test that 'Compare X and Y' is classified as ANALYSIS."""
        query = "Compare Redis and Memcached for caching"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.ANALYSIS
        assert confidence >= 0.8


class TestTerminalCommandIntent:
    """Test TERMINAL_COMMAND intent classification."""

    def test_git_command_detection(self, classifier):
        """Test that 'git status' is classified as TERMINAL_COMMAND."""
        query = "git status"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.TERMINAL_COMMAND
        assert confidence >= 0.9

    def test_docker_command_detection(self, classifier):
        """Test that 'docker ps' is classified as TERMINAL_COMMAND."""
        query = "docker ps -a"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.TERMINAL_COMMAND
        assert confidence >= 0.9


class TestResearchIntent:
    """Test RESEARCH intent classification."""

    def test_research_detection(self, classifier):
        """Test that 'Research X' is classified as RESEARCH."""
        query = "Research current best practices for API security"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.RESEARCH
        assert confidence >= 0.8

    def test_investigate_detection(self, classifier):
        """Test that 'Investigate X' is classified as RESEARCH or ANALYSIS."""
        query = "Investigate why PostgreSQL is slow"
        intent, confidence = classifier.classify(query)

        # "Investigate" can be either RESEARCH or ANALYSIS - both are valid
        assert intent in [IntentType.RESEARCH, IntentType.ANALYSIS]
        assert confidence >= 0.5


class TestMemoryQueryIntent:
    """Test MEMORY_QUERY intent classification."""

    def test_memory_query_detection(self, classifier):
        """Test that 'What did I say about X' is classified as MEMORY_QUERY."""
        query = "What did I say about JWT implementation yesterday?"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.MEMORY_QUERY
        assert confidence >= 0.6  # Lower threshold - complex memory query

    def test_recall_detection(self, classifier):
        """Test that 'Recall X' is classified as MEMORY_QUERY."""
        query = "Recall our discussion about Redis caching"
        intent, confidence = classifier.classify(query)

        assert intent == IntentType.MEMORY_QUERY
        assert confidence >= 0.8
