"""Add knowledge extraction tables.

Creates tables for:
- topic_clusters: Dynamic topic hierarchy
- knowledge_entities: Named entities from content
- entity_relations: Relationships between entities

Revision ID: 011_knowledge_tables
Revises: 010_add_from_cache_to_query_history
Create Date: 2025-12-16
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '011_knowledge_tables'
down_revision = '010_add_from_cache'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create knowledge extraction tables."""

    # Topic Clusters - Dynamic topic hierarchy (model discovers topics)
    op.create_table(
        'topic_clusters',
        sa.Column('cluster_id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(100), nullable=False, unique=True),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('parent_cluster_id', UUID(as_uuid=True),
                  sa.ForeignKey('topic_clusters.cluster_id'), nullable=True),
        sa.Column('query_count', sa.Integer, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
    )

    # Index for fast lookup by name
    op.create_index('idx_topic_clusters_name', 'topic_clusters', ['name'])

    # Knowledge Entities - Named entities extracted from content
    op.create_table(
        'knowledge_entities',
        sa.Column('entity_id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('canonical_name', sa.String(200), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('entity_type', sa.String(50), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('aliases', JSONB, server_default='[]'),  # Alternative names
        sa.Column('mention_count', sa.Integer, server_default='1'),
        sa.Column('user_id', UUID(as_uuid=True), nullable=True),  # Null = global entity
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
    )

    # Unique constraint on canonical name per user (or global)
    op.create_index(
        'idx_knowledge_entities_canonical_user',
        'knowledge_entities',
        ['canonical_name', 'user_id'],
        unique=True
    )
    op.create_index('idx_knowledge_entities_type', 'knowledge_entities', ['entity_type'])

    # Entity Relations - Relationships between entities
    op.create_table(
        'entity_relations',
        sa.Column('relation_id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('from_entity_id', UUID(as_uuid=True),
                  sa.ForeignKey('knowledge_entities.entity_id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('to_entity_id', UUID(as_uuid=True),
                  sa.ForeignKey('knowledge_entities.entity_id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('relation_type', sa.String(50), nullable=False),
        sa.Column('strength', sa.Float, server_default='1.0'),
        sa.Column('occurrence_count', sa.Integer, server_default='1'),
        sa.Column('user_id', UUID(as_uuid=True), nullable=True),  # Null = global relation
        sa.Column('source_query_id', UUID(as_uuid=True), nullable=True),  # First query that created this
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
    )

    # Unique constraint on relation per user
    op.create_index(
        'idx_entity_relations_unique',
        'entity_relations',
        ['from_entity_id', 'to_entity_id', 'relation_type', 'user_id'],
        unique=True
    )
    op.create_index('idx_entity_relations_from', 'entity_relations', ['from_entity_id'])
    op.create_index('idx_entity_relations_to', 'entity_relations', ['to_entity_id'])

    # Knowledge Extraction Log - Track what's been extracted
    op.create_table(
        'knowledge_extraction_log',
        sa.Column('extraction_id', UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('source_type', sa.String(50), nullable=False),  # query_history, memory_items
        sa.Column('source_id', UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), nullable=False),
        sa.Column('weaviate_id', sa.String(100), nullable=True),  # ID in ACMS_Knowledge_v2
        sa.Column('extraction_model', sa.String(50), nullable=False),
        sa.Column('extraction_confidence', sa.Float, nullable=True),
        sa.Column('topic_cluster', sa.String(100), nullable=True),
        sa.Column('entity_count', sa.Integer, server_default='0'),
        sa.Column('fact_count', sa.Integer, server_default='0'),
        sa.Column('tokens_used', sa.Integer, server_default='0'),
        sa.Column('cost_usd', sa.Float, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()')),
    )

    # Prevent duplicate extractions
    op.create_index(
        'idx_extraction_log_source',
        'knowledge_extraction_log',
        ['source_type', 'source_id'],
        unique=True
    )
    op.create_index('idx_extraction_log_user', 'knowledge_extraction_log', ['user_id'])
    op.create_index('idx_extraction_log_topic', 'knowledge_extraction_log', ['topic_cluster'])


def downgrade() -> None:
    """Drop knowledge extraction tables."""
    op.drop_table('knowledge_extraction_log')
    op.drop_table('entity_relations')
    op.drop_table('knowledge_entities')
    op.drop_table('topic_clusters')
