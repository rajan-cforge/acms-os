"""add user_feedback table

Revision ID: 008_add_user_feedback
Revises: 007_unified_chat_interface
Create Date: 2025-10-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '008_add_user_feedback'
down_revision = '007_unified_chat_interface'
branch_labels = None
depends_on = None


def upgrade():
    """
    Create user_feedback table for tracking user satisfaction with AI responses.

    This table supports:
    - Thumbs up/down feedback
    - Detailed comments
    - Source tracking (semantic_cache, memory, api_call)
    - Query association for improving quality
    """

    # Create user_feedback table
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_feedback (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            query_id UUID NOT NULL,
            user_id UUID NOT NULL,
            rating INTEGER CHECK (rating >= 1 AND rating <= 5),
            comment TEXT,
            feedback_type VARCHAR(50) NOT NULL DEFAULT 'general',
            source_info JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

            -- Constraints
            CONSTRAINT valid_feedback_type CHECK (
                feedback_type IN ('general', 'cache_quality', 'memory_relevance', 'compliance_issue', 'incorrect_info', 'other')
            )
        )
    """)

    # Create indexes one by one
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_feedback_query_id
        ON user_feedback(query_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_feedback_user_id
        ON user_feedback(user_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_feedback_created_at
        ON user_feedback(created_at DESC)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_feedback_source_info
        ON user_feedback USING GIN (source_info)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_user_feedback_type_rating
        ON user_feedback(feedback_type, rating)
        WHERE rating IS NOT NULL
    """)

    # Create trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION update_user_feedback_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER trigger_user_feedback_updated_at
        BEFORE UPDATE ON user_feedback
        FOR EACH ROW
        EXECUTE FUNCTION update_user_feedback_updated_at()
    """)

    # Add table comment
    op.execute("""
        COMMENT ON TABLE user_feedback IS
        'User feedback on AI responses for quality improvement and AutoTuner optimization'
    """)

    # Add column comments
    op.execute("""
        COMMENT ON COLUMN user_feedback.query_id IS
        'Foreign key to query/response that was rated'
    """)

    op.execute("""
        COMMENT ON COLUMN user_feedback.user_id IS
        'User who provided feedback'
    """)

    op.execute("""
        COMMENT ON COLUMN user_feedback.rating IS
        'Rating from 1-5 stars (optional, can use feedback_type for thumbs up/down)'
    """)

    op.execute("""
        COMMENT ON COLUMN user_feedback.feedback_type IS
        'Type of feedback: general, cache_quality, memory_relevance, compliance_issue, incorrect_info, other'
    """)

    op.execute("""
        COMMENT ON COLUMN user_feedback.source_info IS
        'JSONB field storing metadata about the source (e.g., {\"source\": \"semantic_cache\", \"hit_rate\": 0.85})'
    """)


def downgrade():
    """
    Remove user_feedback table and associated objects.
    """
    # Drop trigger first
    op.execute("DROP TRIGGER IF EXISTS trigger_user_feedback_updated_at ON user_feedback")

    # Drop function
    op.execute("DROP FUNCTION IF EXISTS update_user_feedback_updated_at()")

    # Drop indexes (will be automatically dropped with table, but explicit for clarity)
    op.execute("DROP INDEX IF EXISTS idx_user_feedback_query_id")
    op.execute("DROP INDEX IF EXISTS idx_user_feedback_user_id")
    op.execute("DROP INDEX IF EXISTS idx_user_feedback_created_at")
    op.execute("DROP INDEX IF EXISTS idx_user_feedback_source_info")
    op.execute("DROP INDEX IF EXISTS idx_user_feedback_type_rating")

    # Drop table
    op.execute("DROP TABLE IF EXISTS user_feedback")
