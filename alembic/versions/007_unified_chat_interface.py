"""Add unified chat interface tables (conversations and conversation_messages)

Revision ID: 007_unified_chat_interface
Revises: 006_add_enterprise_reports
Create Date: 2025-10-24

Purpose: Phase 1 - Unified Chat Interface Foundation
- conversations table: Stores live chat conversations (NOT imports from other platforms)
- conversation_messages table: Stores individual messages (user and assistant)

Note: This is separate from conversation_threads/turns (003) which are for imported conversations.
      These new tables are for LIVE conversations happening in the unified ACMS interface.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '007_unified_chat_interface'
down_revision = '006_add_enterprise_reports'
branch_labels = None
depends_on = None


def upgrade():
    """Create conversations and conversation_messages tables for unified chat interface"""

    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('conversation_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('title', sa.String(200), nullable=True, comment='Auto-generated from first message or user-set'),
        sa.Column('agent', sa.String(50), nullable=False, index=True, comment='claude, gpt, gemini, claude-code'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        comment='Live conversations in unified chat interface (Phase 1)'
    )

    # Create indexes for conversations
    op.create_index(
        'idx_conversation_user_created',
        'conversations',
        ['user_id', 'created_at'],
        postgresql_using='btree'
    )
    op.create_index(
        'idx_conversation_agent',
        'conversations',
        ['agent', 'created_at'],
        postgresql_using='btree'
    )

    # Create conversation_messages table
    op.create_table(
        'conversation_messages',
        sa.Column('message_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('conversation_id', UUID(as_uuid=True), sa.ForeignKey('conversations.conversation_id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('role', sa.String(20), nullable=False, comment='user or assistant'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_metadata', JSONB, nullable=False, server_default='{}', comment='costs, tokens, model, compliance results'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=func.now(), nullable=False, index=True),
        comment='Individual messages within live conversations'
    )

    # Create indexes for conversation_messages
    op.create_index(
        'idx_message_conversation_created',
        'conversation_messages',
        ['conversation_id', 'created_at'],
        postgresql_using='btree'
    )
    op.create_index(
        'idx_message_role',
        'conversation_messages',
        ['role'],
        postgresql_using='btree'
    )


def downgrade():
    """Drop unified chat interface tables"""

    # Drop tables in reverse order (conversation_messages first due to foreign key)
    op.drop_table('conversation_messages')
    op.drop_table('conversations')
