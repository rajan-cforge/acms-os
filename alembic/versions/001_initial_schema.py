"""Initial ACMS schema with all tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2025-01-13 12:00:00

Creates:
- users table
- memory_items table
- query_logs table
- outcomes table
- audit_logs table

All with proper indexes, constraints, and relationships.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all ACMS tables."""

    # Create users table
    op.create_table(
        'users',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('user_id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)

    # Create memory_items table
    op.create_table(
        'memory_items',
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('encrypted_content', sa.Text(), nullable=True),
        sa.Column('embedding_vector_id', sa.String(length=255), nullable=True),
        sa.Column('tier', sa.String(length=20), nullable=False, server_default='SHORT'),
        sa.Column('phase', sa.String(length=100), nullable=True),
        sa.Column('tags', postgresql.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('crs_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('semantic_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('recency_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('outcome_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('frequency_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('correction_score', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('access_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('checkpoint', sa.Integer(), nullable=True),
        sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('memory_id'),
        sa.UniqueConstraint('user_id', 'content_hash', name='uq_user_content_hash')
    )
    op.create_index(op.f('ix_memory_items_user_id'), 'memory_items', ['user_id'], unique=False)
    op.create_index(op.f('ix_memory_items_content_hash'), 'memory_items', ['content_hash'], unique=False)
    op.create_index(op.f('ix_memory_items_embedding_vector_id'), 'memory_items', ['embedding_vector_id'], unique=False)
    op.create_index(op.f('ix_memory_items_tier'), 'memory_items', ['tier'], unique=False)
    op.create_index(op.f('ix_memory_items_phase'), 'memory_items', ['phase'], unique=False)
    op.create_index(op.f('ix_memory_items_crs_score'), 'memory_items', ['crs_score'], unique=False)
    op.create_index(op.f('ix_memory_items_created_at'), 'memory_items', ['created_at'], unique=False)
    op.create_index('idx_memory_user_tier', 'memory_items', ['user_id', 'tier'], unique=False)
    op.create_index('idx_memory_user_phase', 'memory_items', ['user_id', 'phase'], unique=False)
    op.create_index('idx_memory_crs_score', 'memory_items', ['crs_score'], unique=False)
    op.create_index('idx_memory_created', 'memory_items', ['created_at'], unique=False)

    # Create query_logs table
    op.create_table(
        'query_logs',
        sa.Column('log_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('query', sa.Text(), nullable=False),
        sa.Column('query_hash', sa.String(length=64), nullable=False),
        sa.Column('query_embedding_id', sa.String(length=255), nullable=True),
        sa.Column('retrieved_memory_ids', postgresql.ARRAY(postgresql.UUID(as_uuid=True)), nullable=False, server_default='{}'),
        sa.Column('result_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Float(), nullable=False),
        sa.Column('embedding_latency_ms', sa.Float(), nullable=True),
        sa.Column('search_latency_ms', sa.Float(), nullable=True),
        sa.Column('crs_latency_ms', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('log_id')
    )
    op.create_index(op.f('ix_query_logs_user_id'), 'query_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_query_logs_timestamp'), 'query_logs', ['timestamp'], unique=False)
    op.create_index('idx_query_user_timestamp', 'query_logs', ['user_id', 'timestamp'], unique=False)
    op.create_index('idx_query_latency', 'query_logs', ['latency_ms'], unique=False)

    # Create outcomes table
    op.create_table(
        'outcomes',
        sa.Column('outcome_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('memory_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('query_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('outcome_type', sa.String(length=50), nullable=False),
        sa.Column('feedback_score', sa.Float(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['memory_id'], ['memory_items.memory_id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['query_id'], ['query_logs.log_id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('outcome_id')
    )
    op.create_index(op.f('ix_outcomes_memory_id'), 'outcomes', ['memory_id'], unique=False)
    op.create_index(op.f('ix_outcomes_query_id'), 'outcomes', ['query_id'], unique=False)
    op.create_index(op.f('ix_outcomes_outcome_type'), 'outcomes', ['outcome_type'], unique=False)
    op.create_index(op.f('ix_outcomes_timestamp'), 'outcomes', ['timestamp'], unique=False)
    op.create_index('idx_outcome_memory', 'outcomes', ['memory_id', 'timestamp'], unique=False)
    op.create_index('idx_outcome_query', 'outcomes', ['query_id', 'timestamp'], unique=False)
    op.create_index('idx_outcome_type', 'outcomes', ['outcome_type'], unique=False)

    # Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('audit_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('request_id', sa.String(length=255), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('metadata_json', postgresql.JSON(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.ForeignKeyConstraint(['user_id'], ['users.user_id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('audit_id')
    )
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_type'), 'audit_logs', ['resource_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_resource_id'), 'audit_logs', ['resource_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_timestamp'), 'audit_logs', ['timestamp'], unique=False)
    op.create_index('idx_audit_user_timestamp', 'audit_logs', ['user_id', 'timestamp'], unique=False)
    op.create_index('idx_audit_action', 'audit_logs', ['action', 'timestamp'], unique=False)
    op.create_index('idx_audit_resource', 'audit_logs', ['resource_type', 'resource_id'], unique=False)


def downgrade() -> None:
    """Drop all ACMS tables."""

    op.drop_table('audit_logs')
    op.drop_table('outcomes')
    op.drop_table('query_logs')
    op.drop_table('memory_items')
    op.drop_table('users')
