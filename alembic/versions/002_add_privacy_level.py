"""Add privacy_level column to memory_items

Revision ID: 002_add_privacy_level
Revises: 001_initial_schema
Create Date: 2025-10-14 02:30:00

Adds privacy_level column to memory_items table with four levels:
- PUBLIC: Safe to inject anywhere (docs, general knowledge)
- INTERNAL: Your tools only - DEFAULT (conversations, notes)
- CONFIDENTIAL: Manual review required (sensitive data)
- LOCAL_ONLY: Never leaves ACMS (credentials, API keys, PII)

Also updates all existing memories to INTERNAL (safe default).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002_add_privacy_level'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add privacy_level column to memory_items table."""

    # Add privacy_level column with default value 'INTERNAL'
    op.add_column(
        'memory_items',
        sa.Column(
            'privacy_level',
            sa.String(length=20),
            nullable=False,
            server_default='INTERNAL'
        )
    )

    # Add index on privacy_level for filtering
    op.create_index(
        op.f('ix_memory_items_privacy_level'),
        'memory_items',
        ['privacy_level'],
        unique=False
    )

    # Add composite index on (user_id, privacy_level) for user-scoped privacy queries
    op.create_index(
        'idx_memory_user_privacy',
        'memory_items',
        ['user_id', 'privacy_level'],
        unique=False
    )

    # Update all existing memories to have privacy_level = 'INTERNAL'
    # This is the safe default - user's tools only, not public
    op.execute(
        "UPDATE memory_items SET privacy_level = 'INTERNAL' WHERE privacy_level IS NULL"
    )

    print("✅ Added privacy_level column to memory_items")
    print("✅ Created indexes on privacy_level")
    print("✅ Updated existing memories to INTERNAL")


def downgrade() -> None:
    """Remove privacy_level column from memory_items table."""

    # Drop indexes first
    op.drop_index('idx_memory_user_privacy', table_name='memory_items')
    op.drop_index(op.f('ix_memory_items_privacy_level'), table_name='memory_items')

    # Drop column
    op.drop_column('memory_items', 'privacy_level')

    print("✅ Removed privacy_level column and indexes")
