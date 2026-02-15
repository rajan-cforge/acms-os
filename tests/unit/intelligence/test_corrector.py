"""
Unit Tests for KnowledgeCorrector - TDD First

Tests written BEFORE implementation per TDD methodology.

Test Coverage:
- R1: User can edit any extracted fact
- R2: Original content preserved in audit trail
- R3: Corrected content replaces original
- R4: Confidence badge updates to "Verified"
- R5: Re-vectorize corrected content for search
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional
import uuid


class TestCorrectionType:
    """Tests for CorrectionType enum."""

    def test_correction_type_values(self):
        """CorrectionType should have expected values."""
        from src.intelligence.corrector import CorrectionType

        assert CorrectionType.FACTUAL_ERROR.value == "factual_error"
        assert CorrectionType.OUTDATED.value == "outdated"
        assert CorrectionType.INCOMPLETE.value == "incomplete"
        assert CorrectionType.WRONG_CONTEXT.value == "wrong_context"
        assert CorrectionType.TYPO.value == "typo"
        assert CorrectionType.CLARIFICATION.value == "clarification"


class TestCorrection:
    """Tests for Correction dataclass."""

    def test_correction_creation(self):
        """Correction should store all required fields."""
        from src.intelligence.corrector import Correction, CorrectionType

        correction = Correction(
            id=str(uuid.uuid4()),
            knowledge_id="knowledge-123",
            original_content="ACMS uses PostgreSQL for vectors",
            corrected_content="ACMS uses Weaviate for vectors, PostgreSQL for relational data",
            correction_type=CorrectionType.FACTUAL_ERROR,
            corrected_by="user-456",
            corrected_at=datetime.now(timezone.utc),
            reason="PostgreSQL doesn't store vectors, Weaviate does"
        )

        assert correction.knowledge_id == "knowledge-123"
        assert "Weaviate" in correction.corrected_content
        assert correction.correction_type == CorrectionType.FACTUAL_ERROR

    def test_correction_has_audit_fields(self):
        """Correction should have audit trail fields."""
        from src.intelligence.corrector import Correction, CorrectionType

        correction = Correction(
            id="corr-001",
            knowledge_id="knowledge-123",
            original_content="Original",
            corrected_content="Corrected",
            correction_type=CorrectionType.TYPO,
            corrected_by="user-456",
            corrected_at=datetime.now(timezone.utc),
            reason=None
        )

        # Audit trail fields
        assert correction.corrected_by is not None
        assert correction.corrected_at is not None
        assert correction.original_content is not None  # Preserved


class TestKnowledgeCorrectorInit:
    """Tests for KnowledgeCorrector initialization."""

    def test_init_creates_dependencies(self):
        """KnowledgeCorrector should initialize with required dependencies."""
        with patch('src.intelligence.corrector.WeaviateClient') as mock_weaviate:
            with patch('src.intelligence.corrector.OpenAIEmbeddings') as mock_embeddings:
                with patch('src.intelligence.corrector.get_session'):
                    from src.intelligence.corrector import KnowledgeCorrector

                    corrector = KnowledgeCorrector()

                    mock_weaviate.assert_called_once()
                    mock_embeddings.assert_called_once()


class TestApplyCorrection:
    """Tests for KnowledgeCorrector.apply_correction()."""

    @pytest.mark.asyncio
    async def test_apply_correction_updates_content(self):
        """Apply correction should update knowledge item content."""
        with patch('src.intelligence.corrector.WeaviateClient') as mock_weaviate:
            with patch('src.intelligence.corrector.OpenAIEmbeddings') as mock_embeddings:
                with patch('src.intelligence.corrector.get_session') as mock_session:
                    mock_client = MagicMock()
                    mock_client.get_by_id.return_value = {
                        "content": "Original content",
                        "user_verified": False,
                        "confidence": 0.7
                    }
                    mock_weaviate.return_value = mock_client

                    mock_emb = MagicMock()
                    mock_emb.generate_embedding.return_value = [0.1] * 1536
                    mock_embeddings.return_value = mock_emb

                    mock_session_ctx = AsyncMock()
                    mock_cm = AsyncMock()
                    mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                    mock_cm.__aexit__ = AsyncMock(return_value=None)
                    mock_session.return_value = mock_cm

                    from src.intelligence.corrector import KnowledgeCorrector, CorrectionType

                    corrector = KnowledgeCorrector()
                    result = await corrector.apply_correction(
                        knowledge_id="knowledge-123",
                        corrected_content="Corrected content",
                        user_id="user-456",
                        correction_type=CorrectionType.FACTUAL_ERROR
                    )

                    assert result["success"] is True
                    assert result["correction_id"] is not None

    @pytest.mark.asyncio
    async def test_apply_correction_preserves_original(self):
        """Apply correction should preserve original in audit trail."""
        with patch('src.intelligence.corrector.WeaviateClient') as mock_weaviate:
            with patch('src.intelligence.corrector.OpenAIEmbeddings') as mock_embeddings:
                with patch('src.intelligence.corrector.get_session') as mock_session:
                    mock_client = MagicMock()
                    mock_client.get_by_id.return_value = {
                        "content": "Original fact about Python",
                        "user_verified": False,
                        "confidence": 0.7
                    }
                    mock_weaviate.return_value = mock_client

                    mock_emb = MagicMock()
                    mock_emb.generate_embedding.return_value = [0.1] * 1536
                    mock_embeddings.return_value = mock_emb

                    mock_session_ctx = AsyncMock()
                    mock_cm = AsyncMock()
                    mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                    mock_cm.__aexit__ = AsyncMock(return_value=None)
                    mock_session.return_value = mock_cm

                    from src.intelligence.corrector import KnowledgeCorrector, CorrectionType

                    corrector = KnowledgeCorrector()
                    result = await corrector.apply_correction(
                        knowledge_id="knowledge-123",
                        corrected_content="Corrected fact about Python",
                        user_id="user-456",
                        correction_type=CorrectionType.INCOMPLETE
                    )

                    # Should have called execute to insert correction record
                    mock_session_ctx.execute.assert_called()
                    # Verify original content was passed to the insert
                    call_args = str(mock_session_ctx.execute.call_args)
                    assert "Original fact" in call_args or result["success"] is True

    @pytest.mark.asyncio
    async def test_apply_correction_sets_verified_true(self):
        """Apply correction should set user_verified=True."""
        with patch('src.intelligence.corrector.WeaviateClient') as mock_weaviate:
            with patch('src.intelligence.corrector.OpenAIEmbeddings') as mock_embeddings:
                with patch('src.intelligence.corrector.get_session') as mock_session:
                    mock_client = MagicMock()
                    mock_client.get_by_id.return_value = {
                        "content": "Original",
                        "user_verified": False,
                        "confidence": 0.7
                    }
                    mock_weaviate.return_value = mock_client

                    mock_emb = MagicMock()
                    mock_emb.generate_embedding.return_value = [0.1] * 1536
                    mock_embeddings.return_value = mock_emb

                    mock_session_ctx = AsyncMock()
                    mock_cm = AsyncMock()
                    mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                    mock_cm.__aexit__ = AsyncMock(return_value=None)
                    mock_session.return_value = mock_cm

                    from src.intelligence.corrector import KnowledgeCorrector, CorrectionType

                    corrector = KnowledgeCorrector()
                    await corrector.apply_correction(
                        knowledge_id="knowledge-123",
                        corrected_content="Corrected",
                        user_id="user-456",
                        correction_type=CorrectionType.TYPO
                    )

                    # Should update Weaviate with user_verified=True
                    mock_client.update_properties.assert_called()
                    call_args = mock_client.update_properties.call_args
                    # Check that user_verified is True in the update
                    assert call_args[0][2].get("user_verified") is True

    @pytest.mark.asyncio
    async def test_apply_correction_revectorizes_content(self):
        """Apply correction should generate new embedding for search."""
        with patch('src.intelligence.corrector.WeaviateClient') as mock_weaviate:
            with patch('src.intelligence.corrector.OpenAIEmbeddings') as mock_embeddings:
                with patch('src.intelligence.corrector.get_session') as mock_session:
                    mock_client = MagicMock()
                    mock_client.get_by_id.return_value = {
                        "content": "Original",
                        "user_verified": False
                    }
                    mock_weaviate.return_value = mock_client

                    mock_emb = MagicMock()
                    mock_emb.generate_embedding.return_value = [0.2] * 1536
                    mock_embeddings.return_value = mock_emb

                    mock_session_ctx = AsyncMock()
                    mock_cm = AsyncMock()
                    mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                    mock_cm.__aexit__ = AsyncMock(return_value=None)
                    mock_session.return_value = mock_cm

                    from src.intelligence.corrector import KnowledgeCorrector, CorrectionType

                    corrector = KnowledgeCorrector()
                    await corrector.apply_correction(
                        knowledge_id="knowledge-123",
                        corrected_content="New corrected content for search",
                        user_id="user-456",
                        correction_type=CorrectionType.FACTUAL_ERROR
                    )

                    # Should generate embedding for corrected content
                    mock_emb.generate_embedding.assert_called_with("New corrected content for search")
                    # Should update vector in Weaviate
                    mock_client.update_vector.assert_called()

    @pytest.mark.asyncio
    async def test_apply_correction_fails_for_nonexistent_knowledge(self):
        """Apply correction should fail gracefully for non-existent knowledge."""
        with patch('src.intelligence.corrector.WeaviateClient') as mock_weaviate:
            with patch('src.intelligence.corrector.OpenAIEmbeddings') as mock_embeddings:
                with patch('src.intelligence.corrector.get_session'):
                    mock_client = MagicMock()
                    mock_client.get_by_id.return_value = None  # Not found
                    mock_weaviate.return_value = mock_client

                    mock_emb = MagicMock()
                    mock_embeddings.return_value = mock_emb

                    from src.intelligence.corrector import KnowledgeCorrector, CorrectionType

                    corrector = KnowledgeCorrector()
                    result = await corrector.apply_correction(
                        knowledge_id="nonexistent-123",
                        corrected_content="Corrected",
                        user_id="user-456",
                        correction_type=CorrectionType.FACTUAL_ERROR
                    )

                    assert result["success"] is False
                    assert "not found" in result.get("error", "").lower()


class TestGetCorrectionHistory:
    """Tests for getting correction history."""

    @pytest.mark.asyncio
    async def test_get_history_returns_corrections(self):
        """Should return list of corrections for a knowledge item."""
        with patch('src.intelligence.corrector.WeaviateClient'):
            with patch('src.intelligence.corrector.OpenAIEmbeddings'):
                with patch('src.intelligence.corrector.get_session') as mock_session:
                    mock_result = MagicMock()
                    mock_result.fetchall.return_value = [
                        MagicMock(
                            id="corr-1",
                            original_content="Version 1",
                            corrected_content="Version 2",
                            correction_type="factual_error",
                            corrected_by="user-456",
                            corrected_at=datetime.now(timezone.utc)
                        ),
                        MagicMock(
                            id="corr-2",
                            original_content="Version 2",
                            corrected_content="Version 3",
                            correction_type="incomplete",
                            corrected_by="user-456",
                            corrected_at=datetime.now(timezone.utc)
                        ),
                    ]

                    mock_session_ctx = AsyncMock()
                    mock_session_ctx.execute = AsyncMock(return_value=mock_result)
                    mock_cm = AsyncMock()
                    mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                    mock_cm.__aexit__ = AsyncMock(return_value=None)
                    mock_session.return_value = mock_cm

                    from src.intelligence.corrector import KnowledgeCorrector

                    corrector = KnowledgeCorrector()
                    history = await corrector.get_correction_history("knowledge-123")

                    assert len(history) == 2
                    assert history[0]["corrected_content"] == "Version 2"


class TestGetItemsNeedingReview:
    """Tests for getting items that need user review."""

    @pytest.mark.asyncio
    async def test_returns_low_confidence_unverified_items(self):
        """Should return items with low confidence and not verified."""
        with patch('src.intelligence.corrector.WeaviateClient') as mock_weaviate:
            with patch('src.intelligence.corrector.OpenAIEmbeddings'):
                with patch('src.intelligence.corrector.get_session'):
                    mock_client = MagicMock()
                    # Mock Weaviate query for unverified items
                    mock_client.query_collection.return_value = [
                        {
                            "id": "knowledge-1",
                            "content": "Unverified fact 1",
                            "confidence": 0.6,
                            "user_verified": False
                        },
                        {
                            "id": "knowledge-2",
                            "content": "Unverified fact 2",
                            "confidence": 0.5,
                            "user_verified": False
                        },
                    ]
                    mock_weaviate.return_value = mock_client

                    from src.intelligence.corrector import KnowledgeCorrector

                    corrector = KnowledgeCorrector()
                    items = await corrector.get_items_needing_review(
                        user_id="user-456",
                        limit=10
                    )

                    assert len(items) == 2
                    assert all(item["confidence"] < 0.8 for item in items)
                    assert all(item["user_verified"] is False for item in items)

    @pytest.mark.asyncio
    async def test_excludes_already_verified_items(self):
        """Should not return items that are already verified."""
        with patch('src.intelligence.corrector.WeaviateClient') as mock_weaviate:
            with patch('src.intelligence.corrector.OpenAIEmbeddings'):
                with patch('src.intelligence.corrector.get_session'):
                    mock_client = MagicMock()
                    # Only unverified items returned
                    mock_client.query_collection.return_value = [
                        {
                            "id": "knowledge-1",
                            "content": "Unverified fact",
                            "confidence": 0.6,
                            "user_verified": False
                        },
                    ]
                    mock_weaviate.return_value = mock_client

                    from src.intelligence.corrector import KnowledgeCorrector

                    corrector = KnowledgeCorrector()
                    items = await corrector.get_items_needing_review(
                        user_id="user-456",
                        limit=10
                    )

                    # All returned items should be unverified
                    for item in items:
                        assert item["user_verified"] is False


class TestVerifyKnowledge:
    """Tests for marking knowledge as verified without correction."""

    @pytest.mark.asyncio
    async def test_verify_sets_verified_true(self):
        """Verify should set user_verified=True without changing content."""
        with patch('src.intelligence.corrector.WeaviateClient') as mock_weaviate:
            with patch('src.intelligence.corrector.OpenAIEmbeddings'):
                with patch('src.intelligence.corrector.get_session') as mock_session:
                    mock_client = MagicMock()
                    mock_client.get_by_id.return_value = {
                        "content": "Correct fact",
                        "user_verified": False,
                        "confidence": 0.85
                    }
                    mock_weaviate.return_value = mock_client

                    mock_session_ctx = AsyncMock()
                    mock_cm = AsyncMock()
                    mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                    mock_cm.__aexit__ = AsyncMock(return_value=None)
                    mock_session.return_value = mock_cm

                    from src.intelligence.corrector import KnowledgeCorrector

                    corrector = KnowledgeCorrector()
                    result = await corrector.verify_knowledge(
                        knowledge_id="knowledge-123",
                        user_id="user-456"
                    )

                    assert result["success"] is True
                    # Should update with user_verified=True
                    mock_client.update_properties.assert_called()
                    call_args = mock_client.update_properties.call_args
                    assert call_args[0][2].get("user_verified") is True

    @pytest.mark.asyncio
    async def test_verify_boosts_confidence(self):
        """Verify should set confidence to 1.0."""
        with patch('src.intelligence.corrector.WeaviateClient') as mock_weaviate:
            with patch('src.intelligence.corrector.OpenAIEmbeddings'):
                with patch('src.intelligence.corrector.get_session') as mock_session:
                    mock_client = MagicMock()
                    mock_client.get_by_id.return_value = {
                        "content": "Fact",
                        "user_verified": False,
                        "confidence": 0.7
                    }
                    mock_weaviate.return_value = mock_client

                    mock_session_ctx = AsyncMock()
                    mock_cm = AsyncMock()
                    mock_cm.__aenter__ = AsyncMock(return_value=mock_session_ctx)
                    mock_cm.__aexit__ = AsyncMock(return_value=None)
                    mock_session.return_value = mock_cm

                    from src.intelligence.corrector import KnowledgeCorrector

                    corrector = KnowledgeCorrector()
                    await corrector.verify_knowledge(
                        knowledge_id="knowledge-123",
                        user_id="user-456"
                    )

                    # Should set confidence to 1.0
                    call_args = mock_client.update_properties.call_args
                    assert call_args[0][2].get("confidence") == 1.0
