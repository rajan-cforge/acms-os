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
    Add from_cache column to query_history table to support feedback on cached responses.

    This migration supports Week 5 Day 3: Enable feedback on cached responses
    by adding:
    - from_cache: Boolean indicating if response came from semantic cache
    - Index for analytics queries on cached vs fresh responses

    Backfills existing data based on response_source:
    - response_source = 'semantic_cache' → from_cache = TRUE
    - All other values → from_cache = FALSE
    """

    # Add from_cache column (default FALSE for fresh responses)
    op.execute("""
        ALTER TABLE query_history
        ADD COLUMN from_cache BOOLEAN DEFAULT FALSE NOT NULL
    """)

    # Backfill existing data: Mark semantic_cache entries as from_cache=TRUE
    op.execute("""
        UPDATE query_history
        SET from_cache = TRUE
        WHERE response_source = 'semantic_cache'
    """)

    # Create index for analytics on cached responses
    # Simple index without time filter (PostgreSQL requires IMMUTABLE functions in WHERE)
    op.execute("""
        CREATE INDEX idx_query_history_cache_status
        ON query_history(from_cache, created_at DESC)
    """)

    # Create index for feedback analysis on cached responses
    op.execute("""
        CREATE INDEX idx_query_history_cached_with_feedback
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
