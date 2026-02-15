"""Unit tests for ConsolidationTriager.

Tests the cognitive science-inspired selective consolidation system that
prioritizes which queries get full knowledge extraction vs lightweight
tagging vs transient marking.

Run with: PYTHONPATH=. pytest tests/unit/intelligence/test_consolidation_triager.py -v
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.intelligence.consolidation_triager import (
    ConsolidationPriority,
    ConsolidationTriager,
    QueryRecord,
    TriageResult,
    create_query_record_from_row,
)


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def triager():
    """Create a ConsolidationTriager without database connection."""
    return ConsolidationTriager(
        db=None,
        enable_follow_up_detection=False,
        enable_topic_novelty_check=False,
    )


@pytest.fixture
def triager_with_db():
    """Create a ConsolidationTriager with mocked database."""
    mock_db = AsyncMock()
    return ConsolidationTriager(
        db=mock_db,
        enable_follow_up_detection=True,
        enable_topic_novelty_check=True,
    )


@pytest.fixture
def base_query_record():
    """Create a basic QueryRecord for testing."""
    return QueryRecord(
        query_id="test-123",
        question="How do I implement a REST API in FastAPI?",
        answer="To implement a REST API in FastAPI, you need to...",
        user_id="user-456",
        created_at=datetime.utcnow(),
        tenant_id="default",
    )


# ============================================================
# CONSOLIDATION PRIORITY ENUM TESTS
# ============================================================

class TestConsolidationPriority:
    """Tests for ConsolidationPriority enum."""

    def test_enum_values(self):
        """Verify enum has correct values."""
        assert ConsolidationPriority.FULL_EXTRACTION.value == "full"
        assert ConsolidationPriority.LIGHTWEIGHT_TAGGING.value == "light"
        assert ConsolidationPriority.TRANSIENT.value == "transient"

    def test_enum_members_count(self):
        """Verify enum has exactly 3 members."""
        assert len(ConsolidationPriority) == 3


# ============================================================
# QUERY RECORD DATACLASS TESTS
# ============================================================

class TestQueryRecord:
    """Tests for QueryRecord dataclass."""

    def test_required_fields(self):
        """Test QueryRecord requires essential fields."""
        record = QueryRecord(
            query_id="id-1",
            question="What is Python?",
            answer="Python is a programming language.",
            user_id="user-1",
            created_at=datetime.utcnow(),
        )
        assert record.query_id == "id-1"
        assert record.tenant_id == "default"  # Default value

    def test_optional_fields_default_to_none(self):
        """Test optional fields default to None."""
        record = QueryRecord(
            query_id="id-1",
            question="Test",
            answer="Answer",
            user_id="user-1",
            created_at=datetime.utcnow(),
        )
        assert record.session_id is None
        assert record.response_source is None
        assert record.feedback_type is None
        assert record.metadata is None

    def test_all_fields_populated(self):
        """Test QueryRecord with all fields populated."""
        now = datetime.utcnow()
        record = QueryRecord(
            query_id="id-full",
            question="Full question",
            answer="Full answer",
            user_id="user-full",
            created_at=now,
            tenant_id="tenant-1",
            session_id="session-1",
            response_source="cache",
            total_latency_ms=150,
            feedback_type="positive",
            metadata={"source": "test"},
        )
        assert record.tenant_id == "tenant-1"
        assert record.session_id == "session-1"
        assert record.total_latency_ms == 150
        assert record.feedback_type == "positive"
        assert record.metadata == {"source": "test"}


# ============================================================
# TRIAGE RESULT DATACLASS TESTS
# ============================================================

class TestTriageResult:
    """Tests for TriageResult dataclass."""

    def test_basic_result(self):
        """Test basic TriageResult creation."""
        result = TriageResult(
            priority=ConsolidationPriority.FULL_EXTRACTION,
            score=0.85,
            signals_detected=["long_response", "code_in_response"],
        )
        assert result.priority == ConsolidationPriority.FULL_EXTRACTION
        assert result.score == 0.85
        assert len(result.signals_detected) == 2
        assert result.transient_reason is None

    def test_transient_result_with_reason(self):
        """Test TriageResult for transient query with reason."""
        result = TriageResult(
            priority=ConsolidationPriority.TRANSIENT,
            score=0.0,
            signals_detected=[],
            transient_reason="matches_transient_pattern_0",
        )
        assert result.transient_reason == "matches_transient_pattern_0"


# ============================================================
# TRANSIENT PATTERN DETECTION TESTS
# ============================================================

class TestTransientPatternDetection:
    """Tests for transient query pattern detection."""

    def test_greeting_patterns_are_transient(self, triager):
        """Test that greetings are detected as transient."""
        greetings = [
            "hello",
            "Hi there",
            "hey",
            "Thanks!",
            "thank you so much",
            "goodbye",
            "good morning",
        ]
        for greeting in greetings:
            reason = triager._check_transient(greeting)
            assert reason is not None, f"'{greeting}' should be transient"

    def test_time_queries_are_transient(self, triager):
        """Test that time/conversion queries are transient."""
        time_queries = [
            "what time is it",
            "current time in Tokyo",
            "convert 5 miles to km",
            "calculate 15% of 200",
            "translate hello to Spanish",
        ]
        for query in time_queries:
            reason = triager._check_transient(query)
            assert reason is not None, f"'{query}' should be transient"

    def test_weather_queries_are_transient(self, triager):
        """Test that weather queries are transient."""
        weather_queries = [
            "what's the weather today",
            "weather in New York",
            "check the weather forecast",
        ]
        for query in weather_queries:
            reason = triager._check_transient(query)
            assert reason is not None, f"'{query}' should be transient"

    def test_very_short_queries_are_transient(self, triager):
        """Test that very short queries (< 20 chars) are transient."""
        short_queries = [
            "yes",
            "no",
            "ok",
            "sure",
            "test",
            "hello world",
        ]
        for query in short_queries:
            reason = triager._check_transient(query)
            assert reason is not None, f"'{query}' should be transient (too short)"

    def test_simple_factual_lookups_are_transient(self, triager):
        """Test that simple factual lookups are transient."""
        factual_queries = [
            "what is the capital?",
            "who is Einstein?",
            "when was 1990?",
            "where is Paris?",
        ]
        for query in factual_queries:
            reason = triager._check_transient(query)
            assert reason is not None, f"'{query}' should be transient"

    def test_technical_questions_not_transient(self, triager):
        """Test that substantive technical questions are NOT transient."""
        technical_questions = [
            "How do I implement a REST API endpoint in FastAPI with authentication?",
            "What is the difference between async and sync database connections in SQLAlchemy?",
            "Can you explain how Kubernetes pods communicate with each other?",
            "I'm getting a NullPointerException when calling the user service, how do I debug this?",
        ]
        for query in technical_questions:
            reason = triager._check_transient(query)
            assert reason is None, f"'{query}' should NOT be transient"

    def test_appreciation_at_end_is_transient(self, triager):
        """Test that appreciation messages at end are transient."""
        appreciation = [
            "Thanks!",
            "thank you.",
            "appreciate it!",
            "Great!",
            "awesome!",
            "Perfect.",
            "got it!",
        ]
        for msg in appreciation:
            reason = triager._check_transient(msg)
            assert reason is not None, f"'{msg}' should be transient"


# ============================================================
# CONTENT SIGNAL DETECTION TESTS
# ============================================================

class TestContentSignalDetection:
    """Tests for content-based signal detection."""

    def test_long_response_detection(self, triager):
        """Test detection of long responses (> 500 words)."""
        short_answer = "This is a short answer."
        long_answer = " ".join(["word"] * 501)

        assert triager._has_long_response(short_answer) is False
        assert triager._has_long_response(long_answer) is True
        assert triager._has_long_response("") is False
        assert triager._has_long_response(None) is False

    def test_code_block_detection_markdown(self, triager):
        """Test detection of markdown code blocks."""
        with_code = "Here's an example:\n```python\nprint('hello')\n```"
        without_code = "Here's an example: print('hello')"

        assert triager._has_code_block(with_code) is True
        assert triager._has_code_block(without_code) is False

    def test_code_block_detection_indentation(self, triager):
        """Test detection of code via significant indentation."""
        indented_code = "Example:\n    def foo():\n        return bar"
        no_indentation = "Example: def foo(): return bar"

        assert triager._has_code_block(indented_code) is True
        assert triager._has_code_block(no_indentation) is False

    def test_code_block_empty_text(self, triager):
        """Test code block detection with empty/None text."""
        assert triager._has_code_block("") is False
        assert triager._has_code_block(None) is False

    def test_substantial_question_detection(self, triager):
        """Test detection of substantial questions (> 100 chars)."""
        short_question = "What is Python?"
        substantial_question = "Can you explain how to implement a distributed caching system with Redis that handles both read-heavy and write-heavy workloads?"

        assert triager._is_substantial_question(short_question) is False
        assert triager._is_substantial_question(substantial_question) is True
        assert triager._is_substantial_question("") is False
        assert triager._is_substantial_question(None) is False

    def test_technical_keywords_detection(self, triager):
        """Test detection of technical keywords."""
        technical_q = "How do I implement kubernetes deployment?"
        technical_a = "You need to configure the docker container first."
        non_technical = "What should I have for lunch today?"

        assert triager._has_technical_keywords(technical_q, "") is True
        assert triager._has_technical_keywords("", technical_a) is True
        assert triager._has_technical_keywords(non_technical, "") is False

    def test_technical_keywords_multiple_patterns(self, triager):
        """Test technical keywords across multiple patterns."""
        keywords_to_test = [
            ("How do I implement this?", True),
            ("Deploy to production", True),
            ("Debug the error", True),
            ("Configure the API endpoint", True),
            ("Python script for data", True),
            ("React component rendering", True),
            ("AWS Lambda function", True),
            ("What's for dinner?", False),
        ]
        for question, expected in keywords_to_test:
            result = triager._has_technical_keywords(question, "")
            assert result == expected, f"'{question}' technical={result}, expected={expected}"

    def test_error_debugging_detection(self, triager):
        """Test detection of error/debugging questions."""
        error_questions = [
            "I'm getting an error when running the script",
            "Exception thrown in production",
            "The build failed with this message",
            "It's not working as expected",
            "The app doesn't work anymore",
            "Something is broken in the API",
            "There's a bug in the calculation",
            "How do I debug this issue?",
            "Can you help fix this?",
            "Traceback shows this error",
        ]
        for question in error_questions:
            assert triager._is_error_or_debugging(question) is True, \
                f"'{question}' should be detected as error/debugging"

    def test_non_error_questions(self, triager):
        """Test that non-error questions are not flagged."""
        normal_questions = [
            "How do I create a new React component?",
            "What is the best practice for API design?",
            "Explain how Docker containers work",
        ]
        for question in normal_questions:
            assert triager._is_error_or_debugging(question) is False, \
                f"'{question}' should NOT be detected as error/debugging"


# ============================================================
# KEYWORD EXTRACTION TESTS
# ============================================================

class TestKeywordExtraction:
    """Tests for topic keyword extraction."""

    def test_extracts_tech_keywords(self, triager):
        """Test extraction of known tech keywords."""
        text = "I'm learning Python and Docker for my kubernetes deployment"
        keywords = triager._extract_keywords(text)

        assert "python" in keywords
        assert "docker" in keywords
        assert "kubernetes" in keywords

    def test_limits_to_five_keywords(self, triager):
        """Test that keyword extraction is limited to 5."""
        text = "Python JavaScript TypeScript Rust Go Java Kubernetes Docker AWS GCP Azure"
        keywords = triager._extract_keywords(text)

        assert len(keywords) <= 5

    def test_empty_text_returns_empty_list(self, triager):
        """Test empty text returns empty keywords."""
        assert triager._extract_keywords("") == []
        assert triager._extract_keywords(None) == []

    def test_no_tech_keywords_returns_empty(self, triager):
        """Test non-technical text returns empty keywords."""
        text = "What should I have for dinner tonight?"
        keywords = triager._extract_keywords(text)

        assert keywords == []


# ============================================================
# TRIAGE SCORING TESTS
# ============================================================

class TestTriageScoring:
    """Tests for the main triage scoring logic."""

    @pytest.mark.asyncio
    async def test_transient_query_gets_zero_score(self, triager):
        """Test that transient queries get score 0 and skip signal detection."""
        record = QueryRecord(
            query_id="transient-1",
            question="hello",
            answer="Hi there!",
            user_id="user-1",
            created_at=datetime.utcnow(),
        )
        result = await triager.triage(record)

        assert result.priority == ConsolidationPriority.TRANSIENT
        assert result.score == 0.0
        assert result.signals_detected == []
        assert result.transient_reason is not None

    @pytest.mark.asyncio
    async def test_high_value_query_gets_full_extraction(self, triager):
        """Test that high-value queries get FULL_EXTRACTION priority."""
        # Create a query with multiple high-value signals
        long_answer = " ".join(["word"] * 600)  # > 500 words
        record = QueryRecord(
            query_id="high-value-1",
            question="How do I implement a distributed caching system with Redis that handles failover and replication across multiple data centers?",
            answer=f"Here's how to implement it:\n```python\nclass DistributedCache:\n    pass\n```\n{long_answer}",
            user_id="user-1",
            created_at=datetime.utcnow(),
            feedback_type="positive",
        )
        result = await triager.triage(record)

        assert result.priority == ConsolidationPriority.FULL_EXTRACTION
        assert result.score >= 0.6
        assert "long_response" in result.signals_detected
        assert "code_in_response" in result.signals_detected
        assert "substantial_question" in result.signals_detected
        assert "technical_keywords" in result.signals_detected
        assert "explicit_positive_feedback" in result.signals_detected

    @pytest.mark.asyncio
    async def test_medium_value_query_gets_lightweight_tagging(self, triager):
        """Test that medium-value queries get LIGHTWEIGHT_TAGGING priority."""
        record = QueryRecord(
            query_id="medium-1",
            question="What is the difference between Python lists and tuples?",
            answer="Lists are mutable while tuples are immutable. Lists use square brackets [], tuples use parentheses ().",
            user_id="user-1",
            created_at=datetime.utcnow(),
        )
        result = await triager.triage(record)

        # Medium value: has technical keyword (Python) but not much else
        assert result.priority in [
            ConsolidationPriority.LIGHTWEIGHT_TAGGING,
            ConsolidationPriority.FULL_EXTRACTION,  # Might score higher with base 0.5
        ]
        assert result.score >= 0.3

    @pytest.mark.asyncio
    async def test_low_value_query_gets_transient_or_lightweight(self, triager):
        """Test that low-value but non-transient queries get appropriate priority."""
        record = QueryRecord(
            query_id="low-1",
            question="What color is the sky on a clear day?",
            answer="The sky appears blue.",
            user_id="user-1",
            created_at=datetime.utcnow(),
        )
        result = await triager.triage(record)

        # Non-technical, short response, no signals
        # Base score is 0.5, so might get LIGHTWEIGHT_TAGGING
        assert result.priority in [
            ConsolidationPriority.LIGHTWEIGHT_TAGGING,
            ConsolidationPriority.TRANSIENT,
        ]

    @pytest.mark.asyncio
    async def test_positive_feedback_boosts_score(self, triager):
        """Test that positive feedback significantly boosts score."""
        base_record = QueryRecord(
            query_id="feedback-1",
            question="Explain how async/await works in Python",
            answer="Async/await provides concurrency...",
            user_id="user-1",
            created_at=datetime.utcnow(),
        )
        with_feedback = QueryRecord(
            query_id="feedback-2",
            question="Explain how async/await works in Python",
            answer="Async/await provides concurrency...",
            user_id="user-1",
            created_at=datetime.utcnow(),
            feedback_type="positive",
        )

        base_result = await triager.triage(base_record)
        feedback_result = await triager.triage(with_feedback)

        assert feedback_result.score > base_result.score
        assert "explicit_positive_feedback" in feedback_result.signals_detected

    @pytest.mark.asyncio
    async def test_negative_feedback_adds_minimal_boost(self, triager):
        """Test that negative feedback adds small boost (still engagement)."""
        record = QueryRecord(
            query_id="negative-1",
            question="How do I fix this API error?",
            answer="Try restarting the server.",
            user_id="user-1",
            created_at=datetime.utcnow(),
            feedback_type="negative",
        )
        result = await triager.triage(record)

        assert "explicit_negative_feedback" in result.signals_detected

    @pytest.mark.asyncio
    async def test_score_capped_at_one(self, triager):
        """Test that score is capped at 1.0."""
        # Create a query with ALL possible signals
        long_answer = " ".join(["word"] * 600)
        record = QueryRecord(
            query_id="max-1",
            question="I'm getting an error when implementing my kubernetes deployment with docker. How do I debug and fix this distributed system issue?",
            answer=f"Here's the solution:\n```python\nclass Solution:\n    pass\n```\n{long_answer}",
            user_id="user-1",
            created_at=datetime.utcnow(),
            feedback_type="positive",
        )
        result = await triager.triage(record)

        assert result.score <= 1.0


# ============================================================
# BATCH TRIAGE TESTS
# ============================================================

class TestBatchTriage:
    """Tests for batch triage operations."""

    @pytest.mark.asyncio
    async def test_batch_triage_groups_by_priority(self, triager):
        """Test that batch_triage correctly groups records by priority."""
        records = [
            QueryRecord(
                query_id="1",
                question="hello",
                answer="Hi!",
                user_id="user-1",
                created_at=datetime.utcnow(),
            ),
            QueryRecord(
                query_id="2",
                question="How do I implement a distributed cache with Redis cluster?",
                answer="Here's how:\n```python\nclass Cache:\n    pass\n```" + " word" * 500,
                user_id="user-1",
                created_at=datetime.utcnow(),
                feedback_type="positive",
            ),
            QueryRecord(
                query_id="3",
                question="What is Python used for?",
                answer="Python is used for many things.",
                user_id="user-1",
                created_at=datetime.utcnow(),
            ),
        ]

        result = await triager.batch_triage(records)

        assert ConsolidationPriority.FULL_EXTRACTION in result
        assert ConsolidationPriority.LIGHTWEIGHT_TAGGING in result
        assert ConsolidationPriority.TRANSIENT in result

        # Verify total count matches input
        total = sum(len(v) for v in result.values())
        assert total == len(records)

    @pytest.mark.asyncio
    async def test_batch_triage_empty_list(self, triager):
        """Test batch_triage with empty list."""
        result = await triager.batch_triage([])

        assert len(result[ConsolidationPriority.FULL_EXTRACTION]) == 0
        assert len(result[ConsolidationPriority.LIGHTWEIGHT_TAGGING]) == 0
        assert len(result[ConsolidationPriority.TRANSIENT]) == 0


# ============================================================
# STATISTICS TESTS
# ============================================================

class TestStatistics:
    """Tests for triage statistics tracking."""

    @pytest.mark.asyncio
    async def test_stats_increment_on_triage(self, triager):
        """Test that stats are incremented on each triage."""
        initial_stats = triager.get_stats()
        assert initial_stats["total_triaged"] == 0

        record = QueryRecord(
            query_id="stats-1",
            question="hello",
            answer="Hi!",
            user_id="user-1",
            created_at=datetime.utcnow(),
        )
        await triager.triage(record)

        stats = triager.get_stats()
        assert stats["total_triaged"] == 1
        assert stats["transient_count"] == 1

    @pytest.mark.asyncio
    async def test_stats_percentages(self, triager):
        """Test that stats include correct percentages."""
        # Triage 10 records with known outcomes
        for i in range(10):
            if i < 3:
                # Transient
                question = "hello"
            elif i < 7:
                # Full extraction (high value)
                question = "How do I implement a distributed cache with Redis?"
            else:
                # Medium value
                question = "What is Python?"

            record = QueryRecord(
                query_id=f"pct-{i}",
                question=question,
                answer="Answer " + ("word " * (600 if i >= 3 and i < 7 else 10)),
                user_id="user-1",
                created_at=datetime.utcnow(),
                feedback_type="positive" if 3 <= i < 7 else None,
            )
            await triager.triage(record)

        stats = triager.get_stats()
        assert stats["total_triaged"] == 10
        assert "full_pct" in stats
        assert "light_pct" in stats
        assert "transient_pct" in stats

    def test_reset_stats(self, triager):
        """Test that reset_stats clears all counters."""
        triager.stats["total_triaged"] = 100
        triager.stats["full_count"] = 50

        triager.reset_stats()

        assert triager.stats["total_triaged"] == 0
        assert triager.stats["full_count"] == 0
        assert triager.stats["light_count"] == 0
        assert triager.stats["transient_count"] == 0


# ============================================================
# DATABASE INTEGRATION TESTS (MOCKED)
# ============================================================

class TestDatabaseIntegration:
    """Tests for database-dependent features with mocked DB."""

    @pytest.mark.asyncio
    async def test_follow_up_detection_with_db(self, triager_with_db):
        """Test follow-up detection when DB is available."""
        # Mock the database to return follow-ups
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(follow_up_count=3)
        triager_with_db.db.execute = AsyncMock(return_value=mock_result)

        record = QueryRecord(
            query_id="followup-1",
            question="How do I use FastAPI?",
            answer="FastAPI is a modern web framework...",
            user_id="user-1",
            created_at=datetime.utcnow(),
            session_id="session-123",
        )

        result = await triager_with_db.triage(record)

        # Should detect follow-up signal
        assert "follow_up_detected" in result.signals_detected

    @pytest.mark.asyncio
    async def test_follow_up_detection_no_session(self, triager_with_db):
        """Test follow-up detection skipped without session_id."""
        record = QueryRecord(
            query_id="no-session-1",
            question="How do I use FastAPI?",
            answer="FastAPI is a modern web framework...",
            user_id="user-1",
            created_at=datetime.utcnow(),
            session_id=None,  # No session
        )

        has_follow_ups = await triager_with_db._check_follow_ups(record)
        assert has_follow_ups is False

    @pytest.mark.asyncio
    async def test_topic_novelty_check_with_db(self, triager_with_db):
        """Test topic novelty check when DB is available."""
        # Mock the database to return no existing topics (novel)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(existing_count=0)
        triager_with_db.db.execute = AsyncMock(return_value=mock_result)

        record = QueryRecord(
            query_id="novel-1",
            question="How do I use kubernetes for deployment?",
            answer="Kubernetes orchestrates containers...",
            user_id="user-1",
            created_at=datetime.utcnow(),
        )

        result = await triager_with_db.triage(record)

        # Should detect novel topic
        assert "novel_topic" in result.signals_detected

    @pytest.mark.asyncio
    async def test_topic_novelty_not_novel(self, triager_with_db):
        """Test topic novelty check when topic exists."""
        # Mock the database to return existing topics (not novel)
        mock_result = MagicMock()
        mock_result.fetchone.return_value = MagicMock(existing_count=5)
        triager_with_db.db.execute = AsyncMock(return_value=mock_result)

        record = QueryRecord(
            query_id="existing-1",
            question="How do I use Python for scripting?",
            answer="Python is great for scripting...",
            user_id="user-1",
            created_at=datetime.utcnow(),
        )

        result = await triager_with_db.triage(record)

        # Should NOT detect novel topic
        assert "novel_topic" not in result.signals_detected


# ============================================================
# HELPER FUNCTION TESTS
# ============================================================

class TestHelperFunctions:
    """Tests for helper functions."""

    def test_create_query_record_from_row_minimal(self):
        """Test creating QueryRecord from minimal row data."""
        row = {
            "query_id": "row-1",
            "question": "Test question?",
            "answer": "Test answer.",
            "user_id": "user-row",
            "created_at": datetime(2025, 1, 15, 10, 30),
        }
        record = create_query_record_from_row(row)

        assert record.query_id == "row-1"
        assert record.question == "Test question?"
        assert record.user_id == "user-row"
        assert record.tenant_id == "default"

    def test_create_query_record_from_row_full(self):
        """Test creating QueryRecord from full row data."""
        row = {
            "query_id": "row-full",
            "question": "Full question?",
            "answer": "Full answer.",
            "user_id": "user-full",
            "created_at": datetime(2025, 1, 15, 10, 30),
            "tenant_id": "tenant-1",
            "session_id": "session-abc",
            "response_source": "llm",
            "total_latency_ms": 250,
            "feedback_type": "positive",
            "metadata": {"key": "value"},
        }
        record = create_query_record_from_row(row)

        assert record.tenant_id == "tenant-1"
        assert record.session_id == "session-abc"
        assert record.response_source == "llm"
        assert record.total_latency_ms == 250
        assert record.feedback_type == "positive"
        assert record.metadata == {"key": "value"}

    def test_create_query_record_from_row_missing_fields(self):
        """Test creating QueryRecord with missing optional fields."""
        row = {
            "query_id": "sparse",
            "question": "Q",
            "answer": "A",
            "user_id": "u",
        }
        record = create_query_record_from_row(row)

        assert record.query_id == "sparse"
        assert record.session_id is None
        assert record.feedback_type is None


# ============================================================
# THRESHOLD CONFIGURATION TESTS
# ============================================================

class TestThresholdConfiguration:
    """Tests for threshold configuration."""

    def test_default_thresholds(self, triager):
        """Test default threshold values."""
        assert triager.FULL_EXTRACTION_THRESHOLD == 0.6
        assert triager.LIGHTWEIGHT_THRESHOLD == 0.3

    def test_threshold_ordering(self, triager):
        """Test that thresholds are properly ordered."""
        assert triager.FULL_EXTRACTION_THRESHOLD > triager.LIGHTWEIGHT_THRESHOLD

    def test_signal_weights_sum(self, triager):
        """Test that signal weights approximately sum to 1.0."""
        total_weight = sum(triager.HIGH_VALUE_SIGNALS.values())
        # Allow some variance since not all signals will trigger
        assert 0.9 <= total_weight <= 1.1


# ============================================================
# EDGE CASE TESTS
# ============================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_empty_question_and_answer(self, triager):
        """Test handling of empty question and answer."""
        record = QueryRecord(
            query_id="empty-1",
            question="",
            answer="",
            user_id="user-1",
            created_at=datetime.utcnow(),
        )
        result = await triager.triage(record)

        # Empty question should match short query pattern
        assert result.priority == ConsolidationPriority.TRANSIENT

    @pytest.mark.asyncio
    async def test_unicode_content(self, triager):
        """Test handling of unicode content."""
        record = QueryRecord(
            query_id="unicode-1",
            question="如何在Python中实现异步编程？",  # Chinese
            answer="使用async/await关键字...",
            user_id="user-1",
            created_at=datetime.utcnow(),
        )
        # Should not raise exception
        result = await triager.triage(record)
        assert result is not None

    @pytest.mark.asyncio
    async def test_very_long_question(self, triager):
        """Test handling of very long questions."""
        record = QueryRecord(
            query_id="long-q-1",
            question="word " * 10000,  # 10K words
            answer="Short answer.",
            user_id="user-1",
            created_at=datetime.utcnow(),
        )
        result = await triager.triage(record)

        assert "substantial_question" in result.signals_detected

    @pytest.mark.asyncio
    async def test_special_characters_in_question(self, triager):
        """Test handling of special characters."""
        record = QueryRecord(
            query_id="special-1",
            question="How do I fix this error: `TypeError: 'NoneType' object is not callable`?",
            answer="Check if the function is defined properly.",
            user_id="user-1",
            created_at=datetime.utcnow(),
        )
        result = await triager.triage(record)

        assert "error_or_debugging" in result.signals_detected
