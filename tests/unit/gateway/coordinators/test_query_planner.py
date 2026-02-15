"""Unit tests for QueryPlanner coordinator.

Tests verify that:
1. Intent classification is called correctly
2. Web search decision respects preflight result
3. Query augmentation produces variations
4. QueryPlan contains all required fields
5. Events are generated for UI

TDD spec from ACMS_Combined_Code_Review_Refactor_TDD_Spec.md
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from src.gateway.coordinators.query_planner import QueryPlanner, QueryPlan
from src.gateway.preflight_gate import PreflightResult, PreflightDecision


@pytest.fixture
def mock_intent_classifier():
    """Mock intent classifier."""
    classifier = Mock()
    classifier.classify = Mock(return_value=(Mock(value="general"), 0.85))
    return classifier


@pytest.fixture
def mock_search_detector():
    """Mock search detector."""
    detector = Mock()
    detector.should_search = Mock(return_value=(True, "current events query"))
    return detector


@pytest.fixture
def mock_query_augmenter():
    """Mock query augmenter."""
    augmenter = Mock()
    augmenter.augment = AsyncMock(return_value=[
        "original query",
        "variation 1",
        "variation 2"
    ])
    return augmenter


@pytest.fixture
def preflight_allowed():
    """Preflight result that allows everything."""
    return PreflightResult(
        decision=PreflightDecision.ALLOW,
        original_query="test query",
        sanitized_query="test query",
        allow_web_search=True
    )


@pytest.fixture
def preflight_blocked_search():
    """Preflight result that blocks web search."""
    return PreflightResult(
        decision=PreflightDecision.ALLOW,
        original_query="test query",
        sanitized_query="test query",
        allow_web_search=False
    )


@pytest.fixture
def planner(mock_intent_classifier, mock_search_detector, mock_query_augmenter):
    """Get QueryPlanner with mocks."""
    return QueryPlanner(
        intent_classifier=mock_intent_classifier,
        search_detector=mock_search_detector,
        query_augmenter=mock_query_augmenter,
        enable_augmentation=True,
        enable_web_search=True
    )


class TestQueryPlannerBasic:
    """Test basic QueryPlanner functionality."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_query_plan(self, planner, preflight_allowed):
        """plan() should return QueryPlan."""
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        assert isinstance(plan, QueryPlan)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_plan_has_original_query(self, planner, preflight_allowed):
        """QueryPlan should have original query."""
        plan = await planner.plan(
            query="my original query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        assert plan.original_query == "my original query"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_plan_has_sanitized_query(self, planner, preflight_allowed):
        """QueryPlan should have sanitized query from preflight."""
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        assert plan.sanitized_query == "test query"


class TestIntentClassification:
    """Test intent classification."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_calls_intent_classifier(self, planner, preflight_allowed, mock_intent_classifier):
        """Should call intent classifier."""
        await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        mock_intent_classifier.classify.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_stores_intent_in_plan(self, planner, preflight_allowed):
        """QueryPlan should have intent."""
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        assert plan.intent == "general"
        assert plan.intent_confidence == 0.85

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_handles_classifier_failure(self, preflight_allowed):
        """Should handle classifier failure gracefully."""
        failing_classifier = Mock()
        failing_classifier.classify = Mock(side_effect=Exception("classifier error"))

        planner = QueryPlanner(intent_classifier=failing_classifier)
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )

        assert plan.intent == "general"
        assert plan.intent_confidence == 0.5


class TestWebSearchDecision:
    """Test web search decision."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_search_when_allowed(self, planner, preflight_allowed):
        """Should enable web search when allowed."""
        plan = await planner.plan(
            query="current events",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        assert plan.allow_web_search is True
        assert plan.needs_web_search is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_web_search_when_blocked(self, planner, preflight_blocked_search):
        """Should disable web search when blocked by preflight."""
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_blocked_search,
            user_id="user1"
        )
        assert plan.allow_web_search is False
        assert plan.needs_web_search is False

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_search_reason_captured(self, planner, preflight_allowed):
        """Should capture web search reason."""
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        assert plan.web_search_reason is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_search_disabled_by_config(self, preflight_allowed, mock_intent_classifier):
        """Should respect enable_web_search config."""
        planner = QueryPlanner(
            intent_classifier=mock_intent_classifier,
            enable_web_search=False
        )
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        assert plan.allow_web_search is False


class TestQueryAugmentation:
    """Test query augmentation."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_augments_query(self, planner, preflight_allowed, mock_query_augmenter):
        """Should call query augmenter."""
        await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        mock_query_augmenter.augment.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_plan_has_augmented_queries(self, planner, preflight_allowed):
        """QueryPlan should have augmented queries."""
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        assert len(plan.augmented_queries) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_includes_original_in_augmented(self, planner, preflight_allowed):
        """Augmented queries should include original."""
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        assert plan.sanitized_query in plan.augmented_queries or plan.augmented_queries[0] == plan.sanitized_query

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_no_augmentation_when_disabled(self, preflight_allowed, mock_intent_classifier):
        """Should skip augmentation when disabled."""
        planner = QueryPlanner(
            intent_classifier=mock_intent_classifier,
            enable_augmentation=False
        )
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        assert len(plan.augmented_queries) == 1


class TestEventGeneration:
    """Test UI event generation."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_creates_events(self, planner, preflight_allowed):
        """Should create events for UI."""
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        events = planner.create_events(plan)
        assert len(events) > 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_intent_event_created(self, planner, preflight_allowed):
        """Should create intent detection event."""
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        events = planner.create_events(plan)

        intent_events = [e for e in events if e["step"] == "intent_detection"]
        assert len(intent_events) == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_web_search_event_when_needed(self, planner, preflight_allowed):
        """Should create web search event when needed."""
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        events = planner.create_events(plan)

        search_events = [e for e in events if e["step"] == "web_search_decision"]
        assert len(search_events) == 1


class TestQueryPlanSerialization:
    """Test QueryPlan serialization."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_to_dict(self, planner, preflight_allowed):
        """QueryPlan should serialize to dict."""
        plan = await planner.plan(
            query="test query",
            preflight_result=preflight_allowed,
            user_id="user1"
        )
        d = plan.to_dict()

        assert "intent" in d
        assert "intent_confidence" in d
        assert "query_count" in d
        assert "allow_web_search" in d

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_to_dict_truncates_long_query(self, planner, preflight_allowed):
        """to_dict should truncate long queries."""
        long_query = "x" * 100
        preflight = PreflightResult(
            decision=PreflightDecision.ALLOW,
            original_query=long_query,
            sanitized_query=long_query,
            allow_web_search=True
        )
        plan = await planner.plan(
            query=long_query,
            preflight_result=preflight,
            user_id="user1"
        )
        d = plan.to_dict()

        assert len(d["original_query"]) <= 53  # 50 + "..."
