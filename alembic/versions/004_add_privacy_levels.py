"""Add owner tracking and privacy to conversations

Revision ID: 004_add_privacy_levels
Revises: 003_conversation_threads
Create Date: 2025-10-22

Adds:
- owner_id column to memory_items (privacy_level already exists from migration 002)
- privacy_level and owner_id to query_logs
- privacy_level and owner_id to conversation_threads
- privacy_level and owner_id to conversation_turns
- Audit log table for compliance tracking
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision = '004_add_privacy_levels'
down_revision = '003_conversation_threads'
branch_labels = None
depends_on = None


def upgrade():
    """Add privacy level and owner columns to all memory tables"""

    # Add owner_id to memory_items (privacy_level already exists from migration 002)
    op.add_column('memory_items',
        sa.Column('owner_id', UUID(as_uuid=True), nullable=True)
    )
    op.create_index('idx_memory_owner', 'memory_items', ['owner_id'])

    # Add privacy_level and owner_id to query_logs
    op.add_column('query_logs',
        sa.Column('privacy_level', sa.String(20), nullable=False, server_default='PUBLIC')
    )
    op.add_column('query_logs',
        sa.Column('owner_id', UUID(as_uuid=True), nullable=True)
    )
    op.create_index('idx_query_privacy', 'query_logs', ['privacy_level'])
    op.create_index('idx_query_owner', 'query_logs', ['owner_id'])

    # Add privacy_level and owner_id to conversation_threads
    op.add_column('conversation_threads',
        sa.Column('privacy_level', sa.String(20), nullable=False, server_default='PUBLIC')
    )
    op.add_column('conversation_threads',
        sa.Column('owner_id', UUID(as_uuid=True), nullable=True)
    )
    op.create_index('idx_threads_privacy', 'conversation_threads', ['privacy_level'])
    op.create_index('idx_threads_owner', 'conversation_threads', ['owner_id'])

    # Add privacy_level and owner_id to conversation_turns
    op.add_column('conversation_turns',
        sa.Column('privacy_level', sa.String(20), nullable=False, server_default='PUBLIC')
    )
    op.add_column('conversation_turns',
        sa.Column('owner_id', UUID(as_uuid=True), nullable=True)
    )
    op.create_index('idx_turns_privacy', 'conversation_turns', ['privacy_level'])
    op.create_index('idx_turns_owner', 'conversation_turns', ['owner_id'])

    # Create privacy audit log table (if not exists)
    # Note: Use raw SQL with IF NOT EXISTS to avoid conflicts
    op.execute("""
        CREATE TABLE IF NOT EXISTS privacy_audit_log (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ DEFAULT NOW() NOT NULL,
            user_id TEXT NOT NULL,
            user_role TEXT NOT NULL,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            privacy_level TEXT NOT NULL,
            success BOOLEAN NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            details TEXT
        )
    """)

    # Create indexes if they don't exist
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_user ON privacy_audit_log(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON privacy_audit_log(timestamp)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON privacy_audit_log(action)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_resource ON privacy_audit_log(resource_type, resource_id)")


def downgrade():
    """Remove privacy level and owner columns"""

    # Drop audit log table
    op.drop_index('idx_audit_resource', table_name='privacy_audit_log')
    op.drop_index('idx_audit_action', table_name='privacy_audit_log')
    op.drop_index('idx_audit_timestamp', table_name='privacy_audit_log')
    op.drop_index('idx_audit_user', table_name='privacy_audit_log')
    op.drop_table('privacy_audit_log')

    # Remove from conversation_turns
    op.drop_index('idx_turns_owner', table_name='conversation_turns')
    op.drop_index('idx_turns_privacy', table_name='conversation_turns')
    op.drop_column('conversation_turns', 'owner_id')
    op.drop_column('conversation_turns', 'privacy_level')

    # Remove from conversation_threads
    op.drop_index('idx_threads_owner', table_name='conversation_threads')
    op.drop_index('idx_threads_privacy', table_name='conversation_threads')
    op.drop_column('conversation_threads', 'owner_id')
    op.drop_column('conversation_threads', 'privacy_level')

    # Remove from query_logs
    op.drop_index('idx_query_owner', table_name='query_logs')
    op.drop_index('idx_query_privacy', table_name='query_logs')
    op.drop_column('query_logs', 'owner_id')
    op.drop_column('query_logs', 'privacy_level')

    # Remove owner_id from memory_items (keep privacy_level - it's from migration 002)
    op.drop_index('idx_memory_owner', table_name='memory_items')
    op.drop_column('memory_items', 'owner_id')
