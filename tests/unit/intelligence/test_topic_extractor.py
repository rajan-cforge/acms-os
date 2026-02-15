"""Unit tests for Topic Extractor.

Tests the topic extraction module including:
- Keyword extraction (deterministic)
- Method selection logic
- Idempotency key generation
- Batch processing with budget guards

Run with: pytest tests/unit/intelligence/test_topic_extractor.py -v
"""

import pytest
from src.intelligence.topic_extractor import (
    TopicExtractor,
    ExtractionMethod,
    TopicExtractionResult,
    BatchExtractionResult,
    ExtractableItem,
    EXTRACTOR_VERSION,
    BATCH_CONFIG,
    get_extractable_text,
)


class TestExtractionMethod:
    """Tests for ExtractionMethod enum."""

    def test_method_values(self):
        """ExtractionMethod has correct values."""
        assert ExtractionMethod.LLM.value == "llm"
        assert ExtractionMethod.KEYWORD.value == "keyword"
        assert ExtractionMethod.INTENT.value == "intent"


class TestTopicExtractionResult:
    """Tests for TopicExtractionResult dataclass."""

    def test_create_result(self):
        """Can create extraction result."""
        result = TopicExtractionResult(
            topics=["kubernetes", "docker"],
            primary_topic="kubernetes",
            method=ExtractionMethod.KEYWORD,
            confidence=0.8,
            tokens_used=0,
            cached=False
        )
        assert result.topics == ["kubernetes", "docker"]
        assert result.primary_topic == "kubernetes"
        assert result.method == ExtractionMethod.KEYWORD

    def test_from_db(self):
        """Can create result from database row."""
        row = {
            "topics": ["python", "fastapi"],
            "primary_topic": "python",
            "extraction_method": "keyword",
            "confidence": 0.7,
            "tokens_used": 0
        }
        result = TopicExtractionResult.from_db(row)

        assert result.topics == ["python", "fastapi"]
        assert result.method == ExtractionMethod.KEYWORD
        assert result.cached is True


class TestTopicExtractor:
    """Tests for TopicExtractor class."""

    @pytest.fixture
    def extractor(self):
        """Create extractor without DB or LLM."""
        return TopicExtractor(db_session=None, llm_provider=None)

    # --------------------------------------------------------
    # Method Selection Tests
    # --------------------------------------------------------

    def test_select_method_short_text(self, extractor):
        """Short text uses KEYWORD method."""
        method = extractor.select_extraction_method(
            text_length=30,
            has_intent=False
        )
        assert method == ExtractionMethod.KEYWORD

    def test_select_method_long_text(self, extractor):
        """Long text uses KEYWORD method."""
        method = extractor.select_extraction_method(
            text_length=3000,
            has_intent=False
        )
        assert method == ExtractionMethod.KEYWORD

    def test_select_method_has_intent(self, extractor):
        """Pre-computed intent uses INTENT method."""
        method = extractor.select_extraction_method(
            text_length=500,
            has_intent=True
        )
        assert method == ExtractionMethod.INTENT

    def test_select_method_budget_exhausted(self, extractor):
        """Exhausted budget uses KEYWORD method."""
        method = extractor.select_extraction_method(
            text_length=500,
            has_intent=False,
            budget_remaining=0
        )
        assert method == ExtractionMethod.KEYWORD

    def test_select_method_no_llm_provider(self, extractor):
        """No LLM provider uses KEYWORD method."""
        # Extractor has no LLM provider
        method = extractor.select_extraction_method(
            text_length=500,
            has_intent=False,
            budget_remaining=1.0
        )
        # Even with budget, no LLM provider means KEYWORD
        assert method == ExtractionMethod.KEYWORD

    # --------------------------------------------------------
    # Keyword Extraction Tests
    # --------------------------------------------------------

    def test_extract_keyword_kubernetes(self, extractor):
        """Extracts kubernetes-related topics."""
        text = "How do I deploy to Kubernetes using kubectl?"
        topics = extractor.extract_topics_keyword(text)

        assert "kubernetes" in topics

    def test_extract_keyword_python(self, extractor):
        """Extracts Python-related topics."""
        text = "Write a Python FastAPI endpoint"
        topics = extractor.extract_topics_keyword(text)

        assert "python" in topics
        assert "fastapi" in topics

    def test_extract_keyword_multiple(self, extractor):
        """Extracts multiple topics from rich text."""
        text = """
        I'm building a React frontend with TypeScript that calls
        a FastAPI backend. The backend uses PostgreSQL and Redis
        for caching. How do I deploy this to Kubernetes?
        """
        topics = extractor.extract_topics_keyword(text)

        assert len(topics) >= 3
        # Should find several topics
        topic_set = set(topics)
        assert len(topic_set.intersection({
            "react", "typescript", "fastapi", "postgresql", "redis", "kubernetes"
        })) >= 3

    def test_extract_keyword_max_five(self, extractor):
        """Keyword extraction returns max 5 topics."""
        text = """
        Python JavaScript TypeScript React Vue Angular
        FastAPI Django Flask Express PostgreSQL MySQL
        MongoDB Redis Docker Kubernetes AWS GCP Azure
        """
        topics = extractor.extract_topics_keyword(text)

        assert len(topics) <= 5

    def test_extract_keyword_case_insensitive(self, extractor):
        """Keyword matching is case insensitive."""
        text1 = "How to use KUBERNETES"
        text2 = "How to use kubernetes"
        text3 = "How to use Kubernetes"

        topics1 = extractor.extract_topics_keyword(text1)
        topics2 = extractor.extract_topics_keyword(text2)
        topics3 = extractor.extract_topics_keyword(text3)

        assert topics1 == topics2 == topics3
        assert "kubernetes" in topics1

    def test_extract_keyword_no_match(self, extractor):
        """Returns empty list when no keywords match."""
        text = "What is the meaning of life?"
        topics = extractor.extract_topics_keyword(text)

        assert topics == []

    # --------------------------------------------------------
    # Intent Extraction Tests
    # --------------------------------------------------------

    def test_extract_intent_analysis(self, extractor):
        """ANALYSIS intent returns analysis topics."""
        topics = extractor.extract_topics_intent("ANALYSIS")
        assert "analysis" in topics

    def test_extract_intent_code(self, extractor):
        """CODE intent returns coding topics."""
        topics = extractor.extract_topics_intent("CODE")
        assert "coding" in topics or "programming" in topics

    def test_extract_intent_unknown(self, extractor):
        """Unknown intent returns empty list."""
        topics = extractor.extract_topics_intent("UNKNOWN")
        assert topics == []

    def test_extract_intent_none(self, extractor):
        """None intent returns empty list."""
        topics = extractor.extract_topics_intent(None)
        assert topics == []

    # --------------------------------------------------------
    # Idempotency Key Tests
    # --------------------------------------------------------

    def test_idempotency_key_consistent(self, extractor):
        """Same inputs produce same idempotency key."""
        key1 = extractor.get_idempotency_key("t1", "query_history", "id-123")
        key2 = extractor.get_idempotency_key("t1", "query_history", "id-123")

        assert key1 == key2

    def test_idempotency_key_different_source(self, extractor):
        """Different source_id produces different key."""
        key1 = extractor.get_idempotency_key("t1", "query_history", "id-123")
        key2 = extractor.get_idempotency_key("t1", "query_history", "id-456")

        assert key1 != key2

    def test_idempotency_key_different_type(self, extractor):
        """Different source_type produces different key."""
        key1 = extractor.get_idempotency_key("t1", "query_history", "id-123")
        key2 = extractor.get_idempotency_key("t1", "memory_items", "id-123")

        assert key1 != key2

    def test_idempotency_key_different_tenant(self, extractor):
        """Different tenant produces different key."""
        key1 = extractor.get_idempotency_key("t1", "query_history", "id-123")
        key2 = extractor.get_idempotency_key("t2", "query_history", "id-123")

        assert key1 != key2


class TestExtractTopicsIdempotent:
    """Tests for idempotent extraction."""

    @pytest.fixture
    def extractor(self):
        """Create extractor without DB."""
        return TopicExtractor(db_session=None, llm_provider=None)

    @pytest.mark.asyncio
    async def test_extract_returns_result(self, extractor):
        """Extraction returns valid result."""
        result = await extractor.extract_topics_idempotent(
            source_type="query_history",
            source_id="test-id",
            text="Q: How do I deploy to Kubernetes?\nA: Use kubectl apply...",
            user_id="user-123"
        )

        assert isinstance(result, TopicExtractionResult)
        assert len(result.topics) > 0
        assert result.primary_topic is not None
        assert result.method == ExtractionMethod.KEYWORD  # No LLM provider

    @pytest.mark.asyncio
    async def test_extract_with_intent(self, extractor):
        """Extraction uses intent when available."""
        result = await extractor.extract_topics_idempotent(
            source_type="query_history",
            source_id="test-id",
            text="Some text",
            user_id="user-123",
            has_intent=True,
            intent="ANALYSIS"
        )

        assert result.method == ExtractionMethod.INTENT
        assert "analysis" in result.topics

    @pytest.mark.asyncio
    async def test_extract_empty_text_returns_general(self, extractor):
        """Empty text returns 'general' topic."""
        result = await extractor.extract_topics_idempotent(
            source_type="memory_items",
            source_id="test-id",
            text="",
            user_id="user-123"
        )

        assert "general" in result.topics
        assert result.confidence < 0.5


class TestBatchExtraction:
    """Tests for batch extraction with budget."""

    @pytest.fixture
    def extractor(self):
        """Create extractor without DB."""
        return TopicExtractor(db_session=None, llm_provider=None)

    @pytest.mark.asyncio
    async def test_batch_processes_items(self, extractor):
        """Batch processes multiple items."""
        items = [
            ExtractableItem(
                source_type="query_history",
                source_id=f"id-{i}",
                text=f"Q: Question about Kubernetes #{i}\nA: Answer...",
                user_id="user-123"
            )
            for i in range(5)
        ]

        result = await extractor.batch_extract(items)

        assert isinstance(result, BatchExtractionResult)
        assert result.items_processed == 5
        assert len(result.results) == 5

    @pytest.mark.asyncio
    async def test_batch_respects_max_size(self, extractor):
        """Batch respects max batch size."""
        items = [
            ExtractableItem(
                source_type="query_history",
                source_id=f"id-{i}",
                text=f"Q: Question #{i}\nA: Answer...",
                user_id="user-123"
            )
            for i in range(200)  # More than max_batch_size
        ]

        result = await extractor.batch_extract(items)

        assert result.items_processed <= BATCH_CONFIG["max_batch_size"]

    @pytest.mark.asyncio
    async def test_batch_handles_errors(self, extractor):
        """Batch continues after errors."""
        items = [
            ExtractableItem(
                source_type="query_history",
                source_id="id-1",
                text="Q: Valid question\nA: Answer...",
                user_id="user-123"
            ),
            ExtractableItem(
                source_type="query_history",
                source_id="id-2",
                text="Q: Another question\nA: Answer...",
                user_id="user-123"
            ),
        ]

        result = await extractor.batch_extract(items)

        # Should process both items
        assert result.items_processed == 2


class TestGetExtractableText:
    """Tests for get_extractable_text helper."""

    def test_query_history_format(self):
        """Query history concatenates Q&A."""
        record = {
            "question": "How do I deploy?",
            "answer": "You can use kubectl to deploy your application."
        }
        text = get_extractable_text("query_history", record)

        assert text.startswith("Q:")
        assert "How do I deploy?" in text
        assert "A:" in text
        assert "kubectl" in text

    def test_query_history_truncates_answer(self):
        """Long answers are truncated."""
        record = {
            "question": "Short question",
            "answer": "A" * 1000  # Very long answer
        }
        text = get_extractable_text("query_history", record)

        # Answer should be truncated to 500 chars
        answer_part = text.split("A:")[1]
        assert len(answer_part) <= 510  # 500 + some whitespace

    def test_memory_items_format(self):
        """Memory items returns content directly."""
        record = {
            "content": "This is a memory about Kubernetes deployment."
        }
        text = get_extractable_text("memory_items", record)

        assert text == "This is a memory about Kubernetes deployment."

    def test_unknown_source_raises(self):
        """Unknown source type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown source_type"):
            get_extractable_text("unknown_type", {})

    def test_missing_fields_handled(self):
        """Missing fields don't cause errors."""
        record = {}  # Empty record

        # Query history with missing fields
        text = get_extractable_text("query_history", record)
        assert "Q:" in text
        assert "A:" in text

        # Memory with missing content
        text = get_extractable_text("memory_items", record)
        assert text == ""


class TestVersioning:
    """Tests for extractor versioning."""

    def test_version_constant(self):
        """Version constant is defined."""
        assert EXTRACTOR_VERSION is not None
        assert len(EXTRACTOR_VERSION) > 0

    def test_extractor_uses_version(self):
        """Extractor uses configured version."""
        extractor = TopicExtractor(version="v2")
        assert extractor.version == "v2"

        # Different version = different idempotency key
        key_v1 = TopicExtractor(version="v1").get_idempotency_key("t1", "qh", "id1")
        key_v2 = TopicExtractor(version="v2").get_idempotency_key("t1", "qh", "id1")

        assert key_v1 != key_v2
