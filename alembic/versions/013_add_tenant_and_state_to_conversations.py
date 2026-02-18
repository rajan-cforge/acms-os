"""Add tenant_id and state_json to conversations table

Revision ID: 013_add_tenant_state
Revises: 012_add_nudges_and_feedback
Create Date: 2026-02-18

Purpose: Add missing columns to conversations and conversation_messages tables
to match the SQLAlchemy model definitions.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision = '013_add_tenant_state'
down_revision = '012_add_nudges_feedback'
branch_labels = None
depends_on = None


def upgrade():
    """Add tenant_id and state_json columns to conversations table"""

    # Add tenant_id to conversations
    op.execute("""
        ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(100) DEFAULT 'default' NOT NULL
    """)

    # Add state_json to conversations
    op.execute("""
        ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS state_json JSONB DEFAULT '{}'::jsonb NOT NULL
    """)

    # Add tenant_id to conversation_messages
    op.execute("""
        ALTER TABLE conversation_messages
        ADD COLUMN IF NOT EXISTS tenant_id VARCHAR(100) DEFAULT 'default' NOT NULL
    """)

    # Add client_message_id to conversation_messages
    op.execute("""
        ALTER TABLE conversation_messages
        ADD COLUMN IF NOT EXISTS client_message_id VARCHAR(100)
    """)

    # Add token_count to conversation_messages
    op.execute("""
        ALTER TABLE conversation_messages
        ADD COLUMN IF NOT EXISTS token_count INTEGER DEFAULT 0
    """)

    # Create indexes for tenant_id
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_tenant_id
        ON conversations(tenant_id)
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversation_messages_tenant_id
        ON conversation_messages(tenant_id)
    """)


def downgrade():
    """Remove added columns"""
    op.execute("DROP INDEX IF EXISTS idx_conversation_messages_tenant_id")
    op.execute("DROP INDEX IF EXISTS idx_conversations_tenant_id")
    op.execute("ALTER TABLE conversation_messages DROP COLUMN IF EXISTS token_count")
    op.execute("ALTER TABLE conversation_messages DROP COLUMN IF EXISTS client_message_id")
    op.execute("ALTER TABLE conversation_messages DROP COLUMN IF EXISTS tenant_id")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS state_json")
    op.execute("ALTER TABLE conversations DROP COLUMN IF EXISTS tenant_id")
