"""
Knowledge Corrector - User corrections to extracted facts.

Allows users to:
- Edit any extracted fact (Fix Button)
- Preserve original in audit trail
- Update search vectors for corrected content
- Mark content as verified

Part of Active Second Brain implementation (Jan 2026).
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List

from src.storage.weaviate_client import WeaviateClient
from src.embeddings.openai_embeddings import OpenAIEmbeddings
from src.storage.database import get_session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class CorrectionType(Enum):
    """Types of corrections users can make."""
    FACTUAL_ERROR = "factual_error"     # Fact is wrong
    OUTDATED = "outdated"               # Information is old
    INCOMPLETE = "incomplete"           # Missing key details
    WRONG_CONTEXT = "wrong_context"     # Applied to wrong situation
    TYPO = "typo"                       # Spelling/grammar
    CLARIFICATION = "clarification"     # Needs better wording


@dataclass
class Correction:
    """
    Represents a user correction to knowledge.

    Stores both original and corrected content for audit trail.
    """
    id: str
    knowledge_id: str
    original_content: str
    corrected_content: str
    correction_type: CorrectionType
    corrected_by: str
    corrected_at: datetime
    reason: Optional[str] = None


class KnowledgeCorrector:
    """
    Handles user corrections to extracted knowledge.

    Features:
    - Apply corrections with audit trail
    - Re-vectorize corrected content
    - Mark knowledge as verified
    - Track correction history
    - Find items needing review
    """

    KNOWLEDGE_COLLECTION = "ACMS_Knowledge_v2"

    def __init__(self):
        """Initialize KnowledgeCorrector with dependencies."""
        self.weaviate_client = WeaviateClient()
        self.embeddings = OpenAIEmbeddings()
        logger.info("KnowledgeCorrector initialized")

    async def apply_correction(
        self,
        knowledge_id: str,
        corrected_content: str,
        user_id: str,
        correction_type: CorrectionType,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Apply a user correction to a knowledge item.

        Args:
            knowledge_id: ID of the knowledge item to correct
            corrected_content: New corrected content
            user_id: ID of user making correction
            correction_type: Type of correction
            reason: Optional reason for correction

        Returns:
            Dict with success, correction_id, error
        """
        result = {
            "success": False,
            "correction_id": None,
            "error": None
        }

        try:
            # Get existing knowledge item
            existing = self.weaviate_client.get_by_id(
                self.KNOWLEDGE_COLLECTION,
                knowledge_id
            )

            if not existing:
                result["error"] = f"Knowledge item not found: {knowledge_id}"
                return result

            original_content = existing.get("content", "")
            correction_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)

            # Store correction in audit trail (PostgreSQL)
            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO knowledge_corrections
                        (id, knowledge_id, original_content, corrected_content,
                         correction_type, corrected_by, corrected_at, reason)
                        VALUES (:id, :knowledge_id, :original_content, :corrected_content,
                                :correction_type, :corrected_by, :corrected_at, :reason)
                    """),
                    {
                        "id": correction_id,
                        "knowledge_id": knowledge_id,
                        "original_content": original_content,
                        "corrected_content": corrected_content,
                        "correction_type": correction_type.value,
                        "corrected_by": user_id,
                        "corrected_at": now,
                        "reason": reason
                    }
                )
                await session.commit()

            # Generate new embedding for corrected content
            new_vector = self.embeddings.generate_embedding(corrected_content)

            # Update Weaviate with corrected content and verified status
            self.weaviate_client.update_properties(
                self.KNOWLEDGE_COLLECTION,
                knowledge_id,
                {
                    "content": corrected_content,
                    "user_verified": True,
                    "confidence": 1.0,
                    "last_corrected_at": now.isoformat(),
                    "corrected_by": user_id
                }
            )

            # Update vector for search
            self.weaviate_client.update_vector(
                self.KNOWLEDGE_COLLECTION,
                knowledge_id,
                new_vector
            )

            result["success"] = True
            result["correction_id"] = correction_id
            logger.info(f"Applied correction {correction_id} to {knowledge_id}")

        except Exception as e:
            logger.error(f"Failed to apply correction: {e}", exc_info=True)
            result["error"] = str(e)

        return result

    async def get_correction_history(
        self,
        knowledge_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all corrections made to a knowledge item.

        Args:
            knowledge_id: ID of the knowledge item

        Returns:
            List of correction records, newest first
        """
        try:
            async with get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT id, original_content, corrected_content,
                               correction_type, corrected_by, corrected_at, reason
                        FROM knowledge_corrections
                        WHERE knowledge_id = :knowledge_id
                        ORDER BY corrected_at DESC
                    """),
                    {"knowledge_id": knowledge_id}
                )
                rows = result.fetchall()

                history = []
                for row in rows:
                    history.append({
                        "id": row.id,
                        "original_content": row.original_content,
                        "corrected_content": row.corrected_content,
                        "correction_type": row.correction_type,
                        "corrected_by": row.corrected_by,
                        "corrected_at": row.corrected_at,
                        "reason": getattr(row, 'reason', None)
                    })

                return history

        except Exception as e:
            logger.error(f"Failed to get correction history: {e}", exc_info=True)
            return []

    async def get_items_needing_review(
        self,
        user_id: str,
        limit: int = 10,
        confidence_threshold: float = 0.8
    ) -> List[Dict[str, Any]]:
        """
        Get knowledge items that need user review.

        Criteria:
        - user_verified = False
        - confidence < threshold (default 0.8)

        Args:
            user_id: User ID for filtering
            limit: Maximum items to return
            confidence_threshold: Items below this need review

        Returns:
            List of knowledge items needing review
        """
        try:
            # Query Weaviate for unverified, low-confidence items
            items = self.weaviate_client.query_collection(
                self.KNOWLEDGE_COLLECTION,
                filters={
                    "user_verified": False,
                    "confidence_lt": confidence_threshold,
                    "user_id": user_id
                },
                limit=limit
            )

            return items

        except Exception as e:
            logger.error(f"Failed to get items needing review: {e}", exc_info=True)
            return []

    async def verify_knowledge(
        self,
        knowledge_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Mark knowledge as verified without changing content.

        Use when user confirms existing content is correct.

        Args:
            knowledge_id: ID of the knowledge item
            user_id: ID of user verifying

        Returns:
            Dict with success status
        """
        result = {"success": False}

        try:
            # Verify item exists
            existing = self.weaviate_client.get_by_id(
                self.KNOWLEDGE_COLLECTION,
                knowledge_id
            )

            if not existing:
                result["error"] = f"Knowledge item not found: {knowledge_id}"
                return result

            # Update verified status and confidence
            self.weaviate_client.update_properties(
                self.KNOWLEDGE_COLLECTION,
                knowledge_id,
                {
                    "user_verified": True,
                    "confidence": 1.0,
                    "verified_by": user_id,
                    "verified_at": datetime.now(timezone.utc).isoformat()
                }
            )

            # Log verification in audit table
            async with get_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO knowledge_verifications
                        (id, knowledge_id, verified_by, verified_at)
                        VALUES (:id, :knowledge_id, :verified_by, :verified_at)
                    """),
                    {
                        "id": str(uuid.uuid4()),
                        "knowledge_id": knowledge_id,
                        "verified_by": user_id,
                        "verified_at": datetime.now(timezone.utc)
                    }
                )
                await session.commit()

            result["success"] = True
            logger.info(f"Verified knowledge {knowledge_id} by {user_id}")

        except Exception as e:
            logger.error(f"Failed to verify knowledge: {e}", exc_info=True)
            result["error"] = str(e)

        return result


# Global instance
_corrector_instance: Optional[KnowledgeCorrector] = None


def get_knowledge_corrector() -> KnowledgeCorrector:
    """Get global KnowledgeCorrector instance."""
    global _corrector_instance
    if _corrector_instance is None:
        _corrector_instance = KnowledgeCorrector()
    return _corrector_instance
