"""TDD Tests for KnowledgeExtractor.

These tests define the expected behavior of the KnowledgeExtractor class
BEFORE implementation. The implementation should make these tests pass.

Test Strategy:
1. Unit tests for each extraction component (intent, entities, topics, facts)
2. Integration test for full extraction pipeline
3. Edge case tests (empty input, non-English, etc.)
4. Mock LLM responses to avoid API costs during testing

Run with:
    PYTHONPATH=. pytest tests/unit/intelligence/test_knowledge_extractor.py -v
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import json


# ============================================================================
# Expected Data Models (Define contract before implementation)
# ============================================================================

class TestKnowledgeExtractionModels:
    """Test that data models are properly structured."""

    def test_intent_analysis_has_required_fields(self):
        """IntentAnalysis must have primary_intent, problem_domain, why_context."""
        from src.intelligence.knowledge_extractor import IntentAnalysis

        analysis = IntentAnalysis(
            primary_intent="Learn OAuth2 implementation",
            problem_domain="API Security",
            why_context="User is building secure API authentication for production",
            user_context_signals=["building web service", "needs authentication"],
            confidence=0.85
        )

        assert analysis.primary_intent == "Learn OAuth2 implementation"
        assert analysis.problem_domain == "API Security"
        assert analysis.why_context is not None
        assert len(analysis.user_context_signals) >= 1
        assert 0 <= analysis.confidence <= 1.0

    def test_entity_has_required_fields(self):
        """Entity must have name, canonical, type, importance."""
        from src.intelligence.knowledge_extractor import Entity

        entity = Entity(
            name="FastAPI",
            canonical="fastapi",
            entity_type="framework",
            importance="primary"
        )

        assert entity.name == "FastAPI"
        assert entity.canonical == "fastapi"
        assert entity.entity_type in ["framework", "language", "concept", "tool", "protocol", "library"]
        assert entity.importance in ["primary", "secondary", "mentioned"]

    def test_relation_has_required_fields(self):
        """Relation must have from_entity, to_entity, relation_type."""
        from src.intelligence.knowledge_extractor import Relation

        relation = Relation(
            from_entity="fastapi",
            to_entity="oauth2",
            relation_type="IMPLEMENTS"
        )

        assert relation.from_entity == "fastapi"
        assert relation.to_entity == "oauth2"
        assert relation.relation_type in [
            "USES", "IMPLEMENTS", "PART_OF", "ALTERNATIVE_TO", "REQUIRES", "PRODUCES"
        ]

    def test_knowledge_entry_has_all_fields(self):
        """KnowledgeEntry is the complete extraction result."""
        from src.intelligence.knowledge_extractor import KnowledgeEntry

        entry = KnowledgeEntry(
            canonical_query="How to implement OAuth2 in FastAPI?",
            answer_summary="Use OAuth2PasswordBearer with JWT tokens...",
            full_answer="Full answer text here...",
            intent=MagicMock(),  # IntentAnalysis
            entities=[],
            relations=[],
            topic_cluster="api-authentication",
            related_topics=["python-web-development"],
            key_facts=["OAuth2PasswordBearer is built into FastAPI"],
            user_id="user-123",
            source_query_id="query-456",
            extraction_model="claude-sonnet-4",
            extraction_confidence=0.85,
            created_at=datetime.utcnow()
        )

        assert entry.canonical_query is not None
        assert entry.answer_summary is not None
        assert entry.topic_cluster is not None
        assert entry.extraction_model == "claude-sonnet-4"


# ============================================================================
# KnowledgeExtractor Unit Tests
# ============================================================================

class TestKnowledgeExtractorInit:
    """Test KnowledgeExtractor initialization."""

    def test_init_with_default_model(self):
        """Default model should be Claude Sonnet 4."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        extractor = KnowledgeExtractor()
        assert extractor.model == "claude-sonnet-4-20250514"

    def test_init_with_custom_model(self):
        """Should allow specifying a different model."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        extractor = KnowledgeExtractor(model="claude-opus-4-5-20251101")
        assert extractor.model == "claude-opus-4-5-20251101"

    def test_init_requires_anthropic_key(self):
        """Should raise error if ANTHROPIC_API_KEY not set."""
        import os
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        # Save and remove key
        original_key = os.environ.get("ANTHROPIC_API_KEY")
        if "ANTHROPIC_API_KEY" in os.environ:
            del os.environ["ANTHROPIC_API_KEY"]

        try:
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                KnowledgeExtractor()
        finally:
            # Restore key
            if original_key:
                os.environ["ANTHROPIC_API_KEY"] = original_key


class TestIntentExtraction:
    """Test intent analysis extraction."""

    @pytest.mark.asyncio
    async def test_extract_intent_from_technical_query(self):
        """Should extract meaningful intent from technical query."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        # Mock the Anthropic client response
        mock_response = {
            "intent_analysis": {
                "primary_intent": "Learn OAuth2 implementation in FastAPI",
                "problem_domain": "API Security",
                "why_context": "User is building secure API authentication for a production web service",
                "user_context_signals": [
                    "Building production system",
                    "Needs secure authentication"
                ]
            }
        }

        with patch.object(KnowledgeExtractor, '_call_claude') as mock_call:
            mock_call.return_value = mock_response
            extractor = KnowledgeExtractor()

            intent = await extractor.extract_intent(
                query="How do I implement OAuth2 in FastAPI?",
                answer="To implement OAuth2 in FastAPI, use OAuth2PasswordBearer..."
            )

            assert intent.primary_intent == "Learn OAuth2 implementation in FastAPI"
            assert intent.problem_domain == "API Security"
            assert "production" in intent.why_context.lower()

    @pytest.mark.asyncio
    async def test_extract_intent_handles_simple_query(self):
        """Should handle simple/trivial queries gracefully."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        mock_response = {
            "intent_analysis": {
                "primary_intent": "Basic greeting",
                "problem_domain": "General",
                "why_context": "User initiated conversation",
                "user_context_signals": []
            }
        }

        with patch.object(KnowledgeExtractor, '_call_claude') as mock_call:
            mock_call.return_value = mock_response
            extractor = KnowledgeExtractor()

            intent = await extractor.extract_intent(
                query="Hello",
                answer="Hello! How can I help you today?"
            )

            assert intent.confidence <= 0.5  # Low confidence for trivial


class TestEntityExtraction:
    """Test entity and relationship extraction."""

    @pytest.mark.asyncio
    async def test_extract_entities_from_technical_content(self):
        """Should extract named entities (frameworks, languages, etc.)."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        mock_response = {
            "entities": [
                {"name": "FastAPI", "canonical": "fastapi", "type": "framework", "importance": "primary"},
                {"name": "OAuth2", "canonical": "oauth2", "type": "protocol", "importance": "primary"},
                {"name": "JWT", "canonical": "jwt", "type": "technology", "importance": "secondary"},
                {"name": "Python", "canonical": "python", "type": "language", "importance": "mentioned"}
            ],
            "relations": [
                {"from": "fastapi", "to": "oauth2", "type": "IMPLEMENTS"},
                {"from": "oauth2", "to": "jwt", "type": "USES"}
            ]
        }

        with patch.object(KnowledgeExtractor, '_call_claude') as mock_call:
            mock_call.return_value = mock_response
            extractor = KnowledgeExtractor()

            entities, relations = await extractor.extract_entities(
                "FastAPI implements OAuth2 using JWT tokens for authentication"
            )

            assert len(entities) >= 3
            assert any(e.canonical == "fastapi" for e in entities)
            assert any(e.canonical == "oauth2" for e in entities)
            assert len(relations) >= 1

    @pytest.mark.asyncio
    async def test_entities_are_normalized(self):
        """Entity names should be normalized to canonical form."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        mock_response = {
            "entities": [
                {"name": "React.js", "canonical": "react", "type": "framework", "importance": "primary"},
                {"name": "Node.JS", "canonical": "nodejs", "type": "runtime", "importance": "primary"},
            ],
            "relations": []
        }

        with patch.object(KnowledgeExtractor, '_call_claude') as mock_call:
            mock_call.return_value = mock_response
            extractor = KnowledgeExtractor()

            entities, _ = await extractor.extract_entities(
                "React.js and Node.JS are commonly used together"
            )

            # Canonical names should be lowercase, no special chars
            canonicals = [e.canonical for e in entities]
            assert all(c.islower() or c.isdigit() for c in "".join(canonicals))


class TestTopicClustering:
    """Test dynamic topic cluster assignment."""

    @pytest.mark.asyncio
    async def test_assigns_topic_cluster(self):
        """Should assign a meaningful topic cluster."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        mock_response = {
            "topic_cluster": "api-authentication",
            "related_topics": ["python-web-development", "security-best-practices"]
        }

        with patch.object(KnowledgeExtractor, '_call_claude') as mock_call:
            mock_call.return_value = mock_response
            extractor = KnowledgeExtractor()

            topic, related = await extractor.extract_topic_cluster(
                query="How to implement OAuth2?",
                entities=[]
            )

            assert topic == "api-authentication"
            assert isinstance(related, list)

    @pytest.mark.asyncio
    async def test_topic_is_slug_format(self):
        """Topic cluster should be in slug format (lowercase-with-dashes)."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        mock_response = {
            "topic_cluster": "machine-learning-basics",
            "related_topics": ["data-science", "python-ml"]
        }

        with patch.object(KnowledgeExtractor, '_call_claude') as mock_call:
            mock_call.return_value = mock_response
            extractor = KnowledgeExtractor()

            topic, _ = await extractor.extract_topic_cluster(
                query="What is machine learning?",
                entities=[]
            )

            # Should be valid slug
            assert topic == topic.lower()
            assert " " not in topic
            assert all(c.isalnum() or c == "-" for c in topic)


class TestFactExtraction:
    """Test atomic fact extraction."""

    @pytest.mark.asyncio
    async def test_extracts_key_facts(self):
        """Should extract 0-5 key facts from answer."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        mock_response = {
            "key_facts": [
                "OAuth2PasswordBearer is FastAPI's built-in OAuth2 class",
                "JWT tokens should use RS256 algorithm for production",
                "Access tokens typically expire after 15-30 minutes"
            ]
        }

        with patch.object(KnowledgeExtractor, '_call_claude') as mock_call:
            mock_call.return_value = mock_response
            extractor = KnowledgeExtractor()

            facts = await extractor.extract_facts(
                "OAuth2PasswordBearer is built into FastAPI. Use RS256 for JWT in production. Tokens expire in 15-30 mins."
            )

            assert len(facts) >= 1
            assert len(facts) <= 5
            assert all(isinstance(f, str) for f in facts)
            assert all(len(f) > 20 for f in facts)  # No trivial facts

    @pytest.mark.asyncio
    async def test_facts_are_self_contained(self):
        """Each fact should be understandable without context."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        mock_response = {
            "key_facts": [
                "Python's asyncio library enables concurrent execution using coroutines"
            ]
        }

        with patch.object(KnowledgeExtractor, '_call_claude') as mock_call:
            mock_call.return_value = mock_response
            extractor = KnowledgeExtractor()

            facts = await extractor.extract_facts("asyncio enables concurrent execution...")

            # Facts should not reference "it", "this", "the user", etc.
            for fact in facts:
                assert not fact.lower().startswith("it ")
                assert not fact.lower().startswith("this ")
                assert "the user" not in fact.lower()


class TestFullExtraction:
    """Test the complete extraction pipeline."""

    @pytest.mark.asyncio
    async def test_extract_returns_complete_entry(self):
        """Full extraction should return KnowledgeEntry with all fields."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor, KnowledgeEntry

        # Mock the full extraction response
        mock_response = {
            "intent_analysis": {
                "primary_intent": "Learn OAuth2 implementation",
                "problem_domain": "API Security",
                "why_context": "Building secure authentication",
                "user_context_signals": ["production system"]
            },
            "entities": [
                {"name": "OAuth2", "canonical": "oauth2", "type": "protocol", "importance": "primary"}
            ],
            "relations": [],
            "topic_cluster": "api-authentication",
            "related_topics": ["security"],
            "key_facts": ["OAuth2 uses access tokens for authorization"],
            "canonical_query": "How to implement OAuth2 authentication?",
            "answer_summary": "Use OAuth2PasswordBearer with JWT tokens"
        }

        with patch.object(KnowledgeExtractor, '_call_claude') as mock_call:
            mock_call.return_value = mock_response
            extractor = KnowledgeExtractor()

            entry = await extractor.extract(
                query="How do I implement OAuth2?",
                answer="To implement OAuth2...",
                user_id="user-123",
                source_query_id="query-456"
            )

            assert isinstance(entry, KnowledgeEntry)
            assert entry.canonical_query is not None
            assert entry.intent is not None
            assert entry.topic_cluster is not None
            assert entry.user_id == "user-123"
            assert entry.extraction_model.startswith("claude")

    @pytest.mark.asyncio
    async def test_extract_handles_llm_errors(self):
        """Should handle LLM API errors gracefully."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        with patch.object(KnowledgeExtractor, '_call_claude') as mock_call:
            mock_call.side_effect = Exception("API rate limit exceeded")
            extractor = KnowledgeExtractor()

            # Should return None or raise appropriate exception
            with pytest.raises(Exception):
                await extractor.extract(
                    query="test",
                    answer="test answer",
                    user_id="user-123"
                )


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_query_returns_minimal_extraction(self):
        """Empty or very short queries should return minimal extraction."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        mock_response = {
            "intent_analysis": {
                "primary_intent": "Unknown",
                "problem_domain": "General",
                "why_context": "Insufficient context to determine intent",
                "user_context_signals": []
            },
            "entities": [],
            "relations": [],
            "topic_cluster": "general",
            "related_topics": [],
            "key_facts": [],
            "canonical_query": "",
            "answer_summary": ""
        }

        with patch.object(KnowledgeExtractor, '_call_claude') as mock_call:
            mock_call.return_value = mock_response
            extractor = KnowledgeExtractor()

            entry = await extractor.extract(
                query="",
                answer="",
                user_id="user-123"
            )

            assert entry.extraction_confidence < 0.3  # Very low confidence

    @pytest.mark.asyncio
    async def test_very_long_content_is_truncated(self):
        """Very long content should be truncated before sending to LLM."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        mock_response = {
            "intent_analysis": {"primary_intent": "Test", "problem_domain": "Test", "why_context": "Test", "user_context_signals": []},
            "entities": [], "relations": [], "topic_cluster": "test", "related_topics": [],
            "key_facts": [], "canonical_query": "Test", "answer_summary": "Test"
        }

        with patch.object(KnowledgeExtractor, '_call_claude') as mock_call:
            mock_call.return_value = mock_response
            extractor = KnowledgeExtractor()

            long_query = "test " * 10000  # Very long query
            long_answer = "answer " * 10000  # Very long answer

            await extractor.extract(
                query=long_query,
                answer=long_answer,
                user_id="user-123"
            )

            # Verify the call was made with truncated content
            call_args = mock_call.call_args
            # Content should be truncated to reasonable length
            assert len(str(call_args)) < 100000  # Not sending full 10K words

    @pytest.mark.asyncio
    async def test_non_english_content_handled(self):
        """Should handle non-English content gracefully."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        mock_response = {
            "intent_analysis": {
                "primary_intent": "Learn Python basics",
                "problem_domain": "Programming",
                "why_context": "User is learning Python programming",
                "user_context_signals": ["beginner"]
            },
            "entities": [{"name": "Python", "canonical": "python", "type": "language", "importance": "primary"}],
            "relations": [],
            "topic_cluster": "python-basics",
            "related_topics": ["programming-fundamentals"],
            "key_facts": ["Python is a high-level programming language"],
            "canonical_query": "How to learn Python?",
            "answer_summary": "Python is a beginner-friendly language..."
        }

        with patch.object(KnowledgeExtractor, '_call_claude') as mock_call:
            mock_call.return_value = mock_response
            extractor = KnowledgeExtractor()

            # Mixed English/Unicode content
            entry = await extractor.extract(
                query="Python はどうやって学べますか？",  # Japanese
                answer="Python is a great language...",
                user_id="user-123"
            )

            assert entry is not None
            assert entry.topic_cluster is not None


# ============================================================================
# Integration Tests (require actual API - marked for skip in CI)
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(
    "ANTHROPIC_API_KEY" not in __import__("os").environ,
    reason="Requires ANTHROPIC_API_KEY"
)
class TestKnowledgeExtractorIntegration:
    """Integration tests that call real LLM API."""

    @pytest.mark.asyncio
    async def test_real_extraction(self):
        """Test with real API call (run manually, not in CI)."""
        from src.intelligence.knowledge_extractor import KnowledgeExtractor

        extractor = KnowledgeExtractor()

        entry = await extractor.extract(
            query="What is the difference between REST and GraphQL?",
            answer="""
            REST and GraphQL are both API architectures. REST uses multiple endpoints
            with fixed data structures, while GraphQL uses a single endpoint where
            clients specify exactly what data they need. GraphQL reduces over-fetching
            but has a steeper learning curve. REST is simpler but may require multiple
            round trips for complex data needs.
            """,
            user_id="test-user"
        )

        print(f"\n{'='*60}")
        print(f"Canonical Query: {entry.canonical_query}")
        print(f"Topic: {entry.topic_cluster}")
        print(f"Why: {entry.intent.why_context}")
        print(f"Entities: {[e.canonical for e in entry.entities]}")
        print(f"Facts: {entry.key_facts}")
        print(f"Confidence: {entry.extraction_confidence}")
        print(f"{'='*60}\n")

        assert entry.topic_cluster is not None
        assert len(entry.entities) >= 2  # Should find REST and GraphQL at minimum
        assert entry.extraction_confidence > 0.5
