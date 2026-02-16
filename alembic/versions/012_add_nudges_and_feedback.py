"""Add nudges table and feedback_summary column.

Revision ID: 012_add_nudges_feedback
Revises: 011_knowledge_tables
Create Date: 2026-02-16

Creates:
- nudges table for proactive notifications
- feedback_summary column on memory_items
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '012_add_nudges_feedback'
down_revision = '011_knowledge_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create nudges table and add feedback_summary column."""

    # Create nudges table
    op.execute("""
        CREATE TABLE IF NOT EXISTS nudges (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            nudge_type VARCHAR(50) NOT NULL,
            title VARCHAR(255) NOT NULL,
            message TEXT NOT NULL,
            priority VARCHAR(20) DEFAULT 'medium',
            related_id VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE,
            dismissed BOOLEAN DEFAULT FALSE,
            snoozed_until TIMESTAMP WITH TIME ZONE,

            CONSTRAINT valid_nudge_type CHECK (
                nudge_type IN ('new_learning', 'stale_knowledge', 'low_confidence',
                               'correction_suggested', 'review_reminder', 'insight_available')
            ),
            CONSTRAINT valid_priority CHECK (
                priority IN ('high', 'medium', 'low')
            )
        )
    """)

    # Create indexes for nudges
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_nudges_user_id
        ON nudges(user_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_nudges_user_active
        ON nudges(user_id, dismissed, created_at DESC)
        WHERE dismissed = FALSE
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_nudges_priority
        ON nudges(priority, created_at DESC)
    """)

    # Add feedback_summary column to memory_items
    op.execute("""
        ALTER TABLE memory_items
        ADD COLUMN IF NOT EXISTS feedback_summary JSONB DEFAULT '{}'::jsonb
    """)

    # Create index for feedback queries
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_memory_feedback
        ON memory_items USING GIN (feedback_summary)
    """)

    # Add comment
    op.execute("""
        COMMENT ON TABLE nudges IS
        'Proactive notifications for Active Second Brain (tap on shoulder feature)'
    """)

    op.execute("""
        COMMENT ON COLUMN memory_items.feedback_summary IS
        'Aggregated feedback: {total_ratings, avg_rating, thumbs_up, thumbs_down, regenerates}'
    """)


def downgrade() -> None:
    """Remove nudges table and feedback_summary column."""
    op.execute("DROP INDEX IF EXISTS idx_memory_feedback")
    op.execute("ALTER TABLE memory_items DROP COLUMN IF EXISTS feedback_summary")
    op.execute("DROP INDEX IF EXISTS idx_nudges_priority")
    op.execute("DROP INDEX IF EXISTS idx_nudges_user_active")
    op.execute("DROP INDEX IF EXISTS idx_nudges_user_id")
    op.execute("DROP TABLE IF EXISTS nudges")
