"""add from_cache column to query_history for feedback on cached responses

Revision ID: 010_add_from_cache
Revises: 009_add_quality_tracking
Create Date: 2025-11-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010_add_from_cache'
down_revision = '009_add_quality_tracking'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create query_history table and add from_cache column.

    This migration supports Week 5 Day 3: Enable feedback on cached responses
    by adding:
    - query_history table for tracking queries
    - from_cache: Boolean indicating if response came from semantic cache
    - Index for analytics queries on cached vs fresh responses
    """

    # Create query_history table first (if not exists)
    op.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            query_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            query_text TEXT NOT NULL,
            response_text TEXT,
            response_source VARCHAR(50) DEFAULT 'fresh',
            confidence_score FLOAT DEFAULT 0.0,
            latency_ms FLOAT DEFAULT 0.0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            metadata JSONB DEFAULT '{}'::jsonb
        )
    """)

    # Create indexes for query_history
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_query_history_user_id
        ON query_history(user_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_query_history_created_at
        ON query_history(created_at DESC)
    """)

    # Add from_cache column (default FALSE for fresh responses)
    op.execute("""
        ALTER TABLE query_history
        ADD COLUMN IF NOT EXISTS from_cache BOOLEAN DEFAULT FALSE NOT NULL
    """)

    # Backfill existing data: Mark semantic_cache entries as from_cache=TRUE
    op.execute("""
        UPDATE query_history
        SET from_cache = TRUE
        WHERE response_source = 'semantic_cache'
    """)

    # Create index for analytics on cached responses
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_query_history_cache_status
        ON query_history(from_cache, created_at DESC)
    """)

    # Create index for feedback analysis on cached responses
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_query_history_cached_with_feedback
        ON query_history(query_id, from_cache)
        WHERE from_cache = TRUE
    """)

    # Add table comment for documentation
    op.execute("""
        COMMENT ON COLUMN query_history.from_cache IS
        'Boolean indicating if response came from semantic cache (TRUE) or fresh generation (FALSE). Used for feedback availability and cache quality analytics.'
    """)


def downgrade():
    """
    Remove from_cache column from query_history table.
    """
    # Drop indexes first
    op.execute("DROP INDEX IF EXISTS idx_query_history_cached_with_feedback")
    op.execute("DROP INDEX IF EXISTS idx_query_history_cache_status")

    # Drop column
    op.execute("ALTER TABLE query_history DROP COLUMN IF EXISTS from_cache")
