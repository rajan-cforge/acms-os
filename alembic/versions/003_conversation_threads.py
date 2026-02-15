"""Add conversation threads and turns tables

Revision ID: 003_conversation_threads
Revises: 002_add_privacy_level
Create Date: 2025-10-21

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision = '003_conversation_threads'
down_revision = '002_add_privacy_level'
branch_labels = None
depends_on = None


def upgrade():
    # Create conversation_threads table
    op.create_table(
        'conversation_threads',
        sa.Column('thread_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.user_id'), nullable=False),
        sa.Column('source', sa.String(50), nullable=False, comment='chatgpt, claude, gemini'),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('original_thread_id', sa.Text(), nullable=True, comment='Original ID from source platform'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('imported_at', sa.TIMESTAMP(), server_default=sa.func.now()),
        sa.Column('turn_count', sa.Integer(), server_default='0'),
        sa.Column('embedding_vector_id', sa.String(255), nullable=True, comment='Weaviate vector ID for full conversation'),
        sa.Column('metadata_json', JSONB, nullable=True)
    )

    # Create indexes for conversation_threads
    op.create_index('idx_threads_user_source', 'conversation_threads', ['user_id', 'source'])
    op.create_index('idx_threads_imported', 'conversation_threads', ['imported_at'], postgresql_using='btree')

    # Create unique constraint for preventing duplicate imports
    op.create_unique_constraint(
        'uq_conversation_threads_user_source_original',
        'conversation_threads',
        ['user_id', 'source', 'original_thread_id']
    )

    # Create conversation_turns table
    op.create_table(
        'conversation_turns',
        sa.Column('turn_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('thread_id', UUID(as_uuid=True), sa.ForeignKey('conversation_threads.thread_id', ondelete='CASCADE'), nullable=False),
        sa.Column('turn_number', sa.Integer(), nullable=False, comment='Order within conversation (1, 2, 3...)'),
        sa.Column('role', sa.String(20), nullable=False, comment='user or assistant'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('original_message_id', sa.Text(), nullable=True, comment='Original message ID from source'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('embedding_vector_id', sa.String(255), nullable=True, comment='Weaviate vector ID for this turn'),
        sa.Column('metadata_json', JSONB, nullable=True)
    )

    # Create indexes for conversation_turns
    op.create_index('idx_turns_thread', 'conversation_turns', ['thread_id', 'turn_number'], postgresql_using='btree')

    # Create unique constraint for turn ordering
    op.create_unique_constraint(
        'uq_conversation_turns_thread_turn',
        'conversation_turns',
        ['thread_id', 'turn_number']
    )


def downgrade():
    # Drop tables in reverse order (conversation_turns first due to foreign key)
    op.drop_table('conversation_turns')
    op.drop_table('conversation_threads')
