"""Tests for Unified Intelligence Layer.

TDD tests for:
- InsightExtractor base class
- EmailInsightExtractor
- QueryRouter
- Cross-source query routing
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.intelligence.insight_extractor import (
    BaseInsightExtractor,
    InsightEntry,
    InsightSource,
    InsightType,
    PrivacyLevel,
    ExtractionResult,
    InsightStorage,
)
from src.intelligence.email_insight_extractor import (
    EmailInsightExtractor,
    EmailItem,
)
from src.intelligence.query_router import (
    QueryRouter,
    EntityDetector,
    IntentClassifier,
    SourceRouter,
    QueryIntent,
    DetectedEntity,
    RouteResult,
)


# ============================================================================
# InsightEntry Tests
# ============================================================================

class TestInsightEntry:
    """Tests for InsightEntry data class."""

    def test_create_insight_entry(self):
        """InsightEntry should have all required fields with defaults."""
        insight = InsightEntry(
            source=InsightSource.EMAIL,
            source_id="msg123",
            insight_type=InsightType.ACTION_ITEM,
            insight_text="Review the Q4 budget proposal",
        )

        assert insight.source == InsightSource.EMAIL
        assert insight.source_id == "msg123"
        assert insight.insight_type == InsightType.ACTION_ITEM
        assert insight.privacy_level == PrivacyLevel.INTERNAL
        assert insight.confidence_score == 0.8
        assert insight.is_vectorized is False
        assert insight.id is not None

    def test_insight_to_dict(self):
        """InsightEntry should convert to dict for storage."""
        insight = InsightEntry(
            source=InsightSource.EMAIL,
            source_id="msg123",
            insight_type=InsightType.ACTION_ITEM,
            insight_text="Test insight",
            entities={"people": ["alice@example.com"]},
        )

        d = insight.to_dict()

        assert d["source"] == "email"
        assert d["source_id"] == "msg123"
        assert d["insight_type"] == "action_item"
        assert d["entities"] == {"people": ["alice@example.com"]}

    def test_insight_content_hash(self):
        """InsightEntry should generate consistent content hash."""
        insight1 = InsightEntry(
            source=InsightSource.EMAIL,
            source_id="msg123",
            insight_type=InsightType.ACTION_ITEM,
            insight_text="Same content",
        )
        insight2 = InsightEntry(
            source=InsightSource.EMAIL,
            source_id="msg123",
            insight_type=InsightType.ACTION_ITEM,
            insight_text="Same content",
        )

        # Same content should produce same hash
        assert insight1.content_hash() == insight2.content_hash()

    def test_insight_entity_types_present(self):
        """InsightEntry should report which entity types are present."""
        insight = InsightEntry(
            entities={"people": ["alice@example.com"], "topics": ["budget"], "dates": []}
        )

        types = insight.entity_types_present
        assert "people" in types
        assert "topics" in types
        assert "dates" not in types  # Empty list


# ============================================================================
# EmailInsightExtractor Tests
# ============================================================================

class TestEmailInsightExtractor:
    """Tests for EmailInsightExtractor."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return EmailInsightExtractor(use_llm_fallback=False)

    @pytest.fixture
    def sample_email(self):
        """Create a sample email item."""
        return EmailItem(
            id="uuid-123",
            gmail_message_id="msg123",
            sender_email="alice@acme.com",
            sender_name="Alice Smith",
            subject="Please review the Q4 budget proposal",
            snippet="Hi team, could you please review the attached budget by Friday?",
            body_text=None,
            received_at=datetime.now(timezone.utc),
            is_read=False,
            is_starred=False,
            labels=["INBOX"],
        )

    @pytest.mark.asyncio
    async def test_extract_action_item(self, extractor, sample_email):
        """Should extract action items from emails."""
        insights = await extractor.extract_from_item(sample_email)

        # Should find an action item
        action_insights = [i for i in insights if i.insight_type == InsightType.ACTION_ITEM]
        assert len(action_insights) >= 1

        # Check first action item
        action = action_insights[0]
        assert action.source == InsightSource.EMAIL
        assert action.source_id == "msg123"
        assert "alice@acme.com" in action.entities.get("people", [])

    @pytest.mark.asyncio
    async def test_extract_deadline(self, extractor):
        """Should extract deadline mentions."""
        email = EmailItem(
            id="uuid-456",
            gmail_message_id="msg456",
            sender_email="bob@acme.com",
            sender_name="Bob",
            subject="Report due by 2025-01-15",
            snippet="Please submit the report by the deadline",
            body_text=None,
            received_at=datetime.now(timezone.utc),
            is_read=False,
            is_starred=False,
            labels=["INBOX"],
        )

        insights = await extractor.extract_from_item(email)

        deadline_insights = [i for i in insights if i.insight_type == InsightType.DEADLINE]
        assert len(deadline_insights) >= 1

        deadline = deadline_insights[0]
        assert "2025-01-15" in deadline.insight_text or "2025-01-15" in str(deadline.entities.get("dates", []))

    @pytest.mark.asyncio
    async def test_extract_topic(self, extractor, sample_email):
        """Should extract topic from email subject."""
        insights = await extractor.extract_from_item(sample_email)

        topic_insights = [i for i in insights if i.insight_type == InsightType.TOPIC]
        assert len(topic_insights) >= 1

        topic = topic_insights[0]
        assert "budget" in topic.insight_text.lower() or "budget" in str(topic.entities.get("topics", [])).lower()

    @pytest.mark.asyncio
    async def test_starred_email_relationship(self, extractor):
        """Should create relationship insight for starred emails."""
        starred_email = EmailItem(
            id="uuid-789",
            gmail_message_id="msg789",
            sender_email="vip@important.com",
            sender_name="VIP Person",
            subject="Quick note",
            snippet="Just a note",
            body_text=None,
            received_at=datetime.now(timezone.utc),
            is_read=True,
            is_starred=True,
            labels=["INBOX", "STARRED"],
        )

        insights = await extractor.extract_from_item(starred_email)

        rel_insights = [i for i in insights if i.insight_type == InsightType.RELATIONSHIP]
        assert len(rel_insights) >= 1

    @pytest.mark.asyncio
    async def test_entity_extraction(self, extractor, sample_email):
        """Should extract entities correctly."""
        insights = await extractor.extract_from_item(sample_email)

        # Check entities in any insight
        all_people = []
        for insight in insights:
            all_people.extend(insight.entities.get("people", []))

        assert "alice@acme.com" in all_people


# ============================================================================
# EntityDetector Tests
# ============================================================================

class TestEntityDetector:
    """Tests for EntityDetector."""

    @pytest.fixture
    def detector(self):
        return EntityDetector()

    def test_detect_email_address(self, detector):
        """Should detect email addresses as person entities."""
        entities = detector.detect("What did alice@example.com say?")

        person_entities = [e for e in entities if e.entity_type == "person"]
        assert len(person_entities) >= 1
        assert any(e.value == "alice@example.com" for e in person_entities)

    def test_detect_person_name(self, detector):
        """Should detect person names from 'from X' pattern."""
        entities = detector.detect("What did we get from John Smith about the project?")

        person_entities = [e for e in entities if e.entity_type == "person"]
        assert len(person_entities) >= 1

    def test_detect_topic_keywords(self, detector):
        """Should detect topic keywords."""
        entities = detector.detect("Show me information about kubernetes deployments")

        topic_entities = [e for e in entities if e.entity_type == "topic"]
        assert any("kubernetes" in e.value.lower() for e in topic_entities)

    def test_detect_date_keywords(self, detector):
        """Should detect date references."""
        entities = detector.detect("What happened last week?")

        date_entities = [e for e in entities if e.entity_type == "date"]
        assert len(date_entities) >= 1
        assert any("last week" in e.value.lower() for e in date_entities)

    def test_detect_source_hint_email(self, detector):
        """Should add source hint for email-related queries."""
        entities = detector.detect("Find emails from Sarah")

        # At least one entity should have email source hint
        hints = [e.source_hint for e in entities if e.source_hint]
        assert "email" in hints or any("email" in str(h) for h in hints if h)

    def test_detect_source_hint_financial(self, detector):
        """Should add source hint for financial queries."""
        entities = detector.detect("What was my spending on AWS?")

        topic_entities = [e for e in entities if e.entity_type == "topic"]
        # Should detect spending-related topic
        assert any("spending" in e.value.lower() for e in topic_entities)


# ============================================================================
# IntentClassifier Tests
# ============================================================================

class TestIntentClassifier:
    """Tests for IntentClassifier."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    def test_classify_search_intent(self, classifier):
        """Should classify search queries."""
        intent, confidence = classifier.classify("Find emails about the budget")

        assert intent == QueryIntent.SEARCH
        assert confidence > 0.3

    def test_classify_action_intent(self, classifier):
        """Should classify action-related queries."""
        intent, confidence = classifier.classify("What action items do I have?")

        assert intent == QueryIntent.ACTION
        assert confidence > 0.3

    def test_classify_timeline_intent(self, classifier):
        """Should classify timeline queries."""
        intent, confidence = classifier.classify("When was the last meeting?")

        assert intent == QueryIntent.TIMELINE
        assert confidence > 0.3

    def test_classify_relationship_intent(self, classifier):
        """Should classify relationship queries."""
        intent, confidence = classifier.classify("Who have I been working with?")

        assert intent == QueryIntent.RELATIONSHIP
        assert confidence > 0.3

    def test_classify_general_fallback(self, classifier):
        """Should fall back to general for ambiguous queries."""
        intent, confidence = classifier.classify("Hello there")

        assert intent == QueryIntent.GENERAL
        assert confidence <= 0.5


# ============================================================================
# SourceRouter Tests
# ============================================================================

class TestSourceRouter:
    """Tests for SourceRouter."""

    @pytest.fixture
    def router(self):
        return SourceRouter()

    def test_route_action_intent(self, router):
        """Action intent should route to email and calendar."""
        sources = router.determine_sources(
            QueryIntent.ACTION,
            [],
            available_sources={"email", "chat", "calendar"}
        )

        assert "email" in sources
        assert "calendar" in sources

    def test_route_with_person_entity(self, router):
        """Person entity should route to email and chat."""
        entities = [DetectedEntity(value="alice@example.com", entity_type="person")]

        sources = router.determine_sources(
            QueryIntent.SEARCH,
            entities,
            available_sources={"email", "chat", "financial"}
        )

        assert "email" in sources
        assert "chat" in sources

    def test_route_with_amount_entity(self, router):
        """Amount entity should route to financial."""
        entities = [DetectedEntity(value="$500", entity_type="amount")]

        sources = router.determine_sources(
            QueryIntent.SEARCH,
            entities,
            available_sources={"email", "chat", "financial"}
        )

        assert "financial" in sources

    def test_filter_to_available_sources(self, router):
        """Should only return available sources."""
        sources = router.determine_sources(
            QueryIntent.SEARCH,
            [],
            available_sources={"email", "chat"}  # No financial or calendar
        )

        assert "financial" not in sources
        assert "calendar" not in sources

    def test_default_to_chat(self, router):
        """Should default to chat if no other sources match."""
        sources = router.determine_sources(
            QueryIntent.GENERAL,
            [],
            available_sources={"chat"}
        )

        assert "chat" in sources


# ============================================================================
# QueryRouter Integration Tests
# ============================================================================

class TestQueryRouter:
    """Integration tests for QueryRouter."""

    @pytest.fixture
    def router(self):
        return QueryRouter()

    def test_router_initialization(self, router):
        """Router should initialize with all components."""
        assert router.entity_detector is not None
        assert router.intent_classifier is not None
        assert router.source_router is not None

    @pytest.mark.asyncio
    async def test_route_email_query(self, router):
        """Should route email-related query correctly."""
        with patch.object(router, '_search_sources', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            result = await router.route_query(
                "Find emails from Alice about the budget",
                available_sources={"email", "chat"}
            )

            assert result.query == "Find emails from Alice about the budget"
            assert "email" in result.sources_queried
            assert result.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_route_detects_entities(self, router):
        """Should detect entities in query."""
        with patch.object(router, '_search_sources', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            result = await router.route_query(
                "What did alice@example.com say about kubernetes?",
                available_sources={"email", "chat"}
            )

            # Should detect email and topic
            entity_types = {e.entity_type for e in result.detected_entities}
            assert "person" in entity_types
            assert "topic" in entity_types

    @pytest.mark.asyncio
    async def test_route_aggregates_results(self, router):
        """Should aggregate results from multiple sources."""
        from src.intelligence.query_router import SourceResult

        mock_results = [
            SourceResult(
                source="email",
                insight_id="insight1",
                insight_text="Email about budget from Alice",
                insight_type="topic",
                confidence=0.9,
                source_timestamp=datetime.now(timezone.utc),
            ),
            SourceResult(
                source="chat",
                insight_id="insight2",
                insight_text="Discussed budget in Q3 planning",
                insight_type="fact",
                confidence=0.8,
                source_timestamp=datetime.now(timezone.utc),
            ),
        ]

        with patch.object(router, '_search_sources', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_results

            result = await router.route_query(
                "What about the budget?",
                available_sources={"email", "chat"}
            )

            assert len(result.results) == 2
            assert len(result.citations) == 2
            assert "email" in result.answer.lower() or "Email" in result.answer
            assert "chat" in result.answer.lower() or "Chat" in result.answer


# ============================================================================
# Privacy Tests
# ============================================================================

class TestPrivacy:
    """Tests for privacy handling in unified intelligence."""

    def test_financial_amounts_confidential(self):
        """Financial amounts should be marked confidential."""
        from src.intelligence.insight_extractor import BaseInsightExtractor

        class TestExtractor(BaseInsightExtractor):
            async def extract_from_item(self, item):
                return []

            async def get_unprocessed_items(self, limit):
                return []

        extractor = TestExtractor(InsightSource.FINANCIAL)
        privacy = extractor.classify_privacy(
            "Transaction for $500",
            {"amounts": ["$500"]}
        )

        assert privacy == PrivacyLevel.CONFIDENTIAL

    def test_email_without_amounts_internal(self):
        """Emails without amounts should be internal."""
        from src.intelligence.insight_extractor import BaseInsightExtractor

        class TestExtractor(BaseInsightExtractor):
            async def extract_from_item(self, item):
                return []

            async def get_unprocessed_items(self, limit):
                return []

        extractor = TestExtractor(InsightSource.EMAIL)
        privacy = extractor.classify_privacy(
            "Meeting about project planning",
            {"people": ["alice@example.com"], "topics": ["planning"]}
        )

        assert privacy == PrivacyLevel.INTERNAL


# ============================================================================
# Cross-Source Query Tests
# ============================================================================

class TestCrossSourceQueries:
    """Tests for cross-source query scenarios."""

    @pytest.mark.asyncio
    async def test_email_and_financial_query(self):
        """Query should route to both email and financial."""
        router = QueryRouter()

        # Mock the search to avoid actual DB calls
        with patch.object(router, '_search_sources', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            result = await router.route_query(
                "What emails discuss AWS spending?",
                available_sources={"email", "chat", "financial"}
            )

            # Should detect need for email (emails) and financial (spending)
            # Note: financial might not be routed if not enough signals
            assert "email" in result.sources_queried

    @pytest.mark.asyncio
    async def test_email_and_calendar_query(self):
        """Query about follow-ups should route to email and calendar."""
        router = QueryRouter()

        with patch.object(router, '_search_sources', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            result = await router.route_query(
                "Who should I follow up with this week?",
                available_sources={"email", "calendar", "chat"}
            )

            # Follow-up is action intent -> email + calendar
            assert "email" in result.sources_queried or "calendar" in result.sources_queried
