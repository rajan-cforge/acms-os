"""add quality tracking columns for pollution prevention

Revision ID: 009_add_quality_tracking
Revises: 008_add_user_feedback
Create Date: 2025-10-27 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009_add_quality_tracking'
down_revision = '008_add_user_feedback'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add quality tracking columns to memory_items table for pollution prevention.

    This migration supports Week 5 Task 1: Memory Pollution Prevention
    by adding columns to track:
    - confidence_score: Quality confidence score (0.0 - 1.0)
    - flagged: Boolean indicating if memory is flagged for review
    - flagged_reason: Reason why memory was flagged (pollution, low quality, etc.)
    """

    # Add confidence_score column (default 1.0 for existing memories,
    # assuming they passed manual review)
    op.execute("""
        ALTER TABLE memory_items
        ADD COLUMN confidence_score FLOAT DEFAULT 1.0
    """)

    # Add constraint to ensure confidence_score is between 0.0 and 1.0
    op.execute("""
        ALTER TABLE memory_items
        ADD CONSTRAINT check_confidence_score_range
        CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0)
    """)

    # Add flagged column (default FALSE for existing memories)
    op.execute("""
        ALTER TABLE memory_items
        ADD COLUMN flagged BOOLEAN DEFAULT FALSE NOT NULL
    """)

    # Add flagged_reason column (NULL for non-flagged memories)
    op.execute("""
        ALTER TABLE memory_items
        ADD COLUMN flagged_reason TEXT DEFAULT NULL
    """)

    # Create index on confidence_score for efficient querying of low-quality memories
    op.execute("""
        CREATE INDEX idx_memory_confidence_score
        ON memory_items(confidence_score)
        WHERE confidence_score < 0.8
    """)

    # Create index on flagged for efficient querying of flagged memories
    op.execute("""
        CREATE INDEX idx_memory_flagged
        ON memory_items(flagged)
        WHERE flagged = TRUE
    """)

    # Create composite index for quality audit queries
    op.execute("""
        CREATE INDEX idx_memory_quality_audit
        ON memory_items(flagged, confidence_score, created_at DESC)
    """)

    # Add table comments
    op.execute("""
        COMMENT ON COLUMN memory_items.confidence_score IS
        'Quality confidence score (0.0-1.0) calculated by QualityValidator. Threshold: 0.8 for storage.'
    """)

    op.execute("""
        COMMENT ON COLUMN memory_items.flagged IS
        'Boolean flag indicating memory needs review (pollution, speculation, low quality)'
    """)

    op.execute("""
        COMMENT ON COLUMN memory_items.flagged_reason IS
        'Human-readable reason why memory was flagged: e.g., "speculation_no_sources", "low_confidence", "uncertainty_detected"'
    """)


def downgrade():
    """
    Remove quality tracking columns from memory_items table.
    """
    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_memory_quality_audit")
    op.execute("DROP INDEX IF EXISTS idx_memory_flagged")
    op.execute("DROP INDEX IF EXISTS idx_memory_confidence_score")

    # Drop columns
    op.execute("ALTER TABLE memory_items DROP COLUMN IF EXISTS flagged_reason")
    op.execute("ALTER TABLE memory_items DROP COLUMN IF EXISTS flagged")
    op.execute("ALTER TABLE memory_items DROP CONSTRAINT IF EXISTS check_confidence_score_range")
    op.execute("ALTER TABLE memory_items DROP COLUMN IF EXISTS confidence_score")
