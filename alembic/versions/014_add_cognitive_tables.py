"""Add cognitive architecture tables.

Creates tables for:
- topic_extractions: Per-query topic assignments
- cross_domain_discoveries: Cross-domain insight bridges
- coretrieval_edges: Co-retrieval association graph
- topic_summaries: Cached topic detail pages
- knowledge_review_queue: Items flagged for review
- scheduled_job_runs: Background job execution log

Revision ID: 014_cognitive_tables
Revises: 013_add_tenant_state
Create Date: 2026-03-07
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '014_cognitive_tables'
down_revision = '013_add_tenant_state'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create cognitive architecture tables (idempotent)."""

    op.execute("""
        CREATE TABLE IF NOT EXISTS topic_extractions (
            extraction_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            query_id UUID,
            user_id UUID,
            primary_topic VARCHAR(200),
            secondary_topics VARCHAR[] DEFAULT '{}',
            confidence FLOAT DEFAULT 0.0,
            source_type VARCHAR(50),
            source_id UUID,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_topic_extractions_topic ON topic_extractions(primary_topic)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_topic_extractions_user ON topic_extractions(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_topic_extractions_created ON topic_extractions(created_at)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS cross_domain_discoveries (
            discovery_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            bridge VARCHAR(200) NOT NULL,
            domain_a VARCHAR(100) NOT NULL,
            domain_b VARCHAR(100) NOT NULL,
            session_count INTEGER DEFAULT 1,
            topics_involved VARCHAR[] DEFAULT '{}',
            insight TEXT,
            creativity_score FLOAT DEFAULT 0.0,
            status VARCHAR(50) DEFAULT 'active',
            user_id UUID,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_cross_domain_bridge ON cross_domain_discoveries(bridge)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_cross_domain_domains ON cross_domain_discoveries(domain_a, domain_b)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS coretrieval_edges (
            edge_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            item_a_id VARCHAR(200) NOT NULL,
            item_b_id VARCHAR(200) NOT NULL,
            strength FLOAT DEFAULT 1.0,
            co_retrieval_count INTEGER DEFAULT 1,
            last_co_retrieved TIMESTAMPTZ DEFAULT NOW(),
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_coretrieval_a ON coretrieval_edges(item_a_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_coretrieval_b ON coretrieval_edges(item_b_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_coretrieval_pair ON coretrieval_edges(item_a_id, item_b_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS topic_summaries (
            summary_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            topic_slug VARCHAR(200) NOT NULL UNIQUE,
            knowledge_depth INTEGER DEFAULT 0,
            expertise_level VARCHAR(50) DEFAULT 'beginner',
            key_concepts VARCHAR[] DEFAULT '{}',
            sample_questions VARCHAR[] DEFAULT '{}',
            knowledge_gaps VARCHAR[] DEFAULT '{}',
            first_interaction TIMESTAMPTZ,
            last_interaction TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_topic_summaries_slug ON topic_summaries(topic_slug)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_review_queue (
            review_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            source_type VARCHAR(50) NOT NULL,
            source_id UUID,
            reason TEXT,
            status VARCHAR(50) DEFAULT 'pending',
            reviewed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_review_queue_status ON knowledge_review_queue(status)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_job_runs (
            job_run_id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
            job_name VARCHAR(200) NOT NULL,
            status VARCHAR(50) DEFAULT 'running',
            started_at TIMESTAMPTZ DEFAULT NOW(),
            completed_at TIMESTAMPTZ,
            result_json JSONB DEFAULT '{}',
            error_message TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_job_runs_name ON scheduled_job_runs(job_name)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_job_runs_status ON scheduled_job_runs(status)")


def downgrade() -> None:
    """Drop cognitive architecture tables."""
    op.execute("DROP TABLE IF EXISTS scheduled_job_runs")
    op.execute("DROP TABLE IF EXISTS knowledge_review_queue")
    op.execute("DROP TABLE IF EXISTS topic_summaries")
    op.execute("DROP TABLE IF EXISTS coretrieval_edges")
    op.execute("DROP TABLE IF EXISTS cross_domain_discoveries")
    op.execute("DROP TABLE IF EXISTS topic_extractions")
