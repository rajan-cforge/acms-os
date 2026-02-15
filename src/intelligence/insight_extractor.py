"""Base Insight Extractor - Common interface for cross-source insight extraction.

Provides a unified interface for extracting insights from different data sources:
- EmailInsightExtractor: Action items, deadlines, sender importance
- FinanceInsightExtractor: Spending patterns, category trends (Phase 2)
- CalendarInsightExtractor: Meeting prep, schedule patterns (Phase 3)
- ChatInsightExtractor: Knowledge facts, topics (existing KnowledgeExtractor)

All extractors produce InsightEntry objects that can be stored in:
- PostgreSQL: unified_insights table
- Weaviate: ACMS_Insights_v1 collection

Usage:
    extractor = EmailInsightExtractor()
    insights = await extractor.extract_batch(email_ids=[...])
    for insight in insights:
        await insight.save()  # Saves to both PostgreSQL and Weaviate
"""

import os
import json
import logging
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


# ============================================================================
# Enums and Constants
# ============================================================================

class InsightSource(str, Enum):
    """Data source types for insights."""
    CHAT = "chat"
    EMAIL = "email"
    FINANCIAL = "financial"
    CALENDAR = "calendar"


class InsightType(str, Enum):
    """Types of insights that can be extracted."""
    ACTION_ITEM = "action_item"      # Something to do
    DEADLINE = "deadline"            # Time-sensitive date
    TOPIC = "topic"                  # Subject/theme
    PATTERN = "pattern"              # Recurring behavior
    FACT = "fact"                    # Learned fact
    RELATIONSHIP = "relationship"    # Person/entity relationship
    SUMMARY = "summary"              # Content summary
    DECISION = "decision"            # Decision made
    QUESTION = "question"            # Open question


class PrivacyLevel(str, Enum):
    """Privacy classification for insights."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    LOCAL_ONLY = "local_only"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class ExtractedEntity:
    """An entity extracted from source content."""
    value: str              # The entity value (e.g., "sarah@acme.com")
    entity_type: str        # Type: person, topic, date, amount, organization
    display_name: str       # Human-readable name (e.g., "Sarah")
    confidence: float = 0.9


@dataclass
class InsightEntry:
    """A single insight extracted from a data source.

    This is the common format for all sources. Each extractor produces
    InsightEntry objects that get stored in unified_insights table
    and vectorized into ACMS_Insights_v1.
    """
    # Core identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: InsightSource = InsightSource.CHAT
    source_id: str = ""                     # Reference to source record
    source_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Insight content
    insight_type: InsightType = InsightType.FACT
    insight_text: str = ""                  # Full insight text
    insight_summary: str = ""               # Short summary (max 500 chars)

    # Entities for cross-source linking
    entities: Dict[str, List[str]] = field(default_factory=dict)
    # Example: {"people": ["sarah@acme.com"], "topics": ["budget", "Q4"], "dates": ["2025-01-15"]}

    # Entity references (IDs for privacy)
    entity_refs: Dict[str, List[str]] = field(default_factory=dict)

    # Classification
    privacy_level: PrivacyLevel = PrivacyLevel.INTERNAL
    confidence_score: float = 0.8

    # Extraction metadata
    extraction_method: str = "rule_based"  # 'rule_based', 'llm', 'hybrid'

    # Vectorization state
    weaviate_id: Optional[str] = None
    is_vectorized: bool = False

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        return {
            "id": self.id,
            "source": self.source.value,
            "source_id": self.source_id,
            "source_timestamp": self.source_timestamp.isoformat(),
            "insight_type": self.insight_type.value,
            "insight_text": self.insight_text,
            "insight_summary": self.insight_summary,
            "entities": self.entities,
            "entity_refs": self.entity_refs,
            "privacy_level": self.privacy_level.value,
            "confidence_score": self.confidence_score,
            "extraction_method": self.extraction_method,
            "weaviate_id": self.weaviate_id,
            "is_vectorized": self.is_vectorized,
            "created_at": self.created_at.isoformat(),
        }

    def content_hash(self) -> str:
        """Generate hash for deduplication."""
        content = f"{self.source.value}:{self.source_id}:{self.insight_type.value}:{self.insight_text}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    @property
    def entity_types_present(self) -> List[str]:
        """Get list of entity types present in this insight."""
        return [k for k, v in self.entities.items() if v]


@dataclass
class ExtractionResult:
    """Result of a batch extraction job."""
    source: InsightSource
    total_processed: int = 0
    insights_created: int = 0
    errors: int = 0
    insights: List[InsightEntry] = field(default_factory=list)
    error_messages: List[str] = field(default_factory=list)
    duration_ms: int = 0


# ============================================================================
# Base Extractor
# ============================================================================

class BaseInsightExtractor(ABC):
    """Abstract base class for insight extractors.

    Each data source (email, financial, calendar) implements this interface
    to extract insights in a common format.
    """

    def __init__(self, source: InsightSource):
        self.source = source
        self.logger = logging.getLogger(f"{__name__}.{source.value}")

    @abstractmethod
    async def extract_from_item(self, item: Any) -> List[InsightEntry]:
        """Extract insights from a single source item.

        Args:
            item: Source-specific item (email, transaction, event, etc.)

        Returns:
            List of InsightEntry objects extracted from the item
        """
        pass

    @abstractmethod
    async def get_unprocessed_items(self, limit: int = 50) -> List[Any]:
        """Get items that haven't been processed for insights yet.

        Args:
            limit: Maximum number of items to return

        Returns:
            List of source-specific items to process
        """
        pass

    async def extract_batch(
        self,
        item_ids: Optional[List[str]] = None,
        limit: int = 50,
    ) -> ExtractionResult:
        """Extract insights from multiple items.

        Args:
            item_ids: Specific IDs to process (optional)
            limit: Max items to process if item_ids not provided

        Returns:
            ExtractionResult with all insights and stats
        """
        import time
        start_time = time.time()

        result = ExtractionResult(source=self.source)

        try:
            # Get items to process
            if item_ids:
                items = await self.get_items_by_ids(item_ids)
            else:
                items = await self.get_unprocessed_items(limit=limit)

            result.total_processed = len(items)

            # Process each item
            for item in items:
                try:
                    insights = await self.extract_from_item(item)
                    result.insights.extend(insights)
                    result.insights_created += len(insights)
                except Exception as e:
                    result.errors += 1
                    result.error_messages.append(str(e))
                    self.logger.error(f"Error extracting from item: {e}")

        except Exception as e:
            result.error_messages.append(f"Batch extraction failed: {e}")
            self.logger.error(f"Batch extraction failed: {e}")

        result.duration_ms = int((time.time() - start_time) * 1000)
        return result

    async def get_items_by_ids(self, item_ids: List[str]) -> List[Any]:
        """Get specific items by their IDs.

        Override this in subclasses if needed.
        Default implementation calls get_unprocessed_items.
        """
        return await self.get_unprocessed_items(limit=len(item_ids))

    def classify_privacy(self, content: str, entities: Dict[str, List[str]]) -> PrivacyLevel:
        """Classify privacy level based on content and entities.

        Override in subclasses for source-specific rules.
        """
        # Financial amounts -> confidential
        if "amounts" in entities and entities["amounts"]:
            return PrivacyLevel.CONFIDENTIAL

        # Default to internal
        return PrivacyLevel.INTERNAL

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text using pattern matching.

        Override in subclasses for more sophisticated extraction.
        """
        import re

        entities: Dict[str, List[str]] = {
            "people": [],
            "topics": [],
            "dates": [],
            "organizations": [],
        }

        # Email patterns
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities["people"] = list(set(re.findall(email_pattern, text.lower())))

        # Date patterns (simple)
        date_pattern = r'\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b'
        entities["dates"] = list(set(re.findall(date_pattern, text)))

        return entities


# ============================================================================
# Insight Storage
# ============================================================================

class InsightStorage:
    """Handles storing insights in PostgreSQL and Weaviate."""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.storage")

    async def save_insight(self, insight: InsightEntry) -> str:
        """Save insight to PostgreSQL and queue for vectorization.

        Args:
            insight: InsightEntry to save

        Returns:
            The insight ID
        """
        from src.storage.database import get_db_connection

        async with get_db_connection() as conn:
            await conn.execute("""
                INSERT INTO unified_insights (
                    id, source, source_id, source_timestamp,
                    insight_type, insight_text, insight_summary,
                    entities, entity_refs, privacy_level, confidence_score,
                    extraction_method, weaviate_id, is_vectorized, created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
                )
                ON CONFLICT (id) DO UPDATE SET
                    insight_text = EXCLUDED.insight_text,
                    insight_summary = EXCLUDED.insight_summary,
                    entities = EXCLUDED.entities,
                    extraction_method = EXCLUDED.extraction_method,
                    updated_at = NOW()
            """,
                insight.id,
                insight.source.value,
                insight.source_id,
                insight.source_timestamp,
                insight.insight_type.value,
                insight.insight_text,
                insight.insight_summary,
                json.dumps(insight.entities),
                json.dumps(insight.entity_refs),
                insight.privacy_level.value,
                insight.confidence_score,
                insight.extraction_method,
                insight.weaviate_id,
                insight.is_vectorized,
                insight.created_at,
            )

        self.logger.info(f"Saved insight {insight.id} from {insight.source.value}")
        return insight.id

    async def save_batch(self, insights: List[InsightEntry]) -> int:
        """Save multiple insights.

        Args:
            insights: List of InsightEntry objects

        Returns:
            Number of insights saved
        """
        count = 0
        for insight in insights:
            try:
                await self.save_insight(insight)
                count += 1
            except Exception as e:
                self.logger.error(f"Failed to save insight {insight.id}: {e}")
        return count

    async def vectorize_pending(self, limit: int = 50) -> int:
        """Vectorize insights that haven't been vectorized yet.

        Args:
            limit: Max insights to vectorize

        Returns:
            Number of insights vectorized
        """
        from src.storage.database import get_db_connection
        from src.embeddings.openai_embeddings import OpenAIEmbeddings
        from src.storage.weaviate_client import WeaviateClient

        embedder = OpenAIEmbeddings()

        async with get_db_connection() as conn:
            rows = await conn.fetch("""
                SELECT id, source, insight_type, insight_text, insight_summary,
                       entities, privacy_level, confidence_score, source_timestamp, created_at
                FROM unified_insights
                WHERE is_vectorized = FALSE
                ORDER BY created_at DESC
                LIMIT $1
            """, limit)

        if not rows:
            return 0

        client = WeaviateClient()
        count = 0

        try:
            for row in rows:
                try:
                    # Generate embedding for insight text
                    vector = embedder.generate_embedding(row["insight_text"])

                    # Prepare Weaviate data
                    entities = json.loads(row["entities"]) if isinstance(row["entities"], str) else row["entities"]

                    data = {
                        "insight_id": str(row["id"]),
                        "source": row["source"],
                        "insight_type": row["insight_type"],
                        "insight_text": row["insight_text"],
                        "insight_summary": row["insight_summary"] or "",
                        "source_tags": [row["source"]],
                        "entity_types": list(entities.keys()) if entities else [],
                        "privacy_level": row["privacy_level"],
                        "confidence_score": float(row["confidence_score"]) if row["confidence_score"] else 0.8,
                        "source_timestamp": row["source_timestamp"].isoformat() if row["source_timestamp"] else None,
                        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                    }

                    # Insert into Weaviate
                    weaviate_id = client.insert_vector(
                        collection="ACMS_Insights_v1",
                        vector=vector,
                        data=data,
                    )

                    # Update PostgreSQL with Weaviate ID
                    async with get_db_connection() as conn:
                        await conn.execute("""
                            UPDATE unified_insights
                            SET weaviate_id = $1, is_vectorized = TRUE, updated_at = NOW()
                            WHERE id = $2
                        """, weaviate_id, row["id"])

                    count += 1

                except Exception as e:
                    self.logger.error(f"Failed to vectorize insight {row['id']}: {e}")

        finally:
            client.close()

        self.logger.info(f"Vectorized {count} insights")
        return count
