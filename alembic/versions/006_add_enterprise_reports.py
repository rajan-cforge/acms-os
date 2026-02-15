"""Add enterprise_reports table

Revision ID: 006_add_enterprise_reports
Revises: 005_add_pii_detection_log
Create Date: 2025-10-23

Weekly enterprise intelligence reports storage.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006_add_enterprise_reports'
down_revision = '005_add_pii_detection_log'
branch_labels = None
depends_on = None


def upgrade():
    # Create enterprise_reports table
    op.execute("""
        CREATE TABLE IF NOT EXISTS enterprise_reports (
            report_id VARCHAR(100) PRIMARY KEY,
            generated_at TIMESTAMP NOT NULL DEFAULT NOW(),
            week_start DATE NOT NULL,
            week_end DATE NOT NULL,
            executive_summary TEXT NOT NULL,
            report_data JSONB NOT NULL,
            total_impact_usd FLOAT NOT NULL DEFAULT 0,
            patterns_detected INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)

    # Create indexes
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_week_start
        ON enterprise_reports(week_start DESC);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_generated_at
        ON enterprise_reports(generated_at DESC);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_impact
        ON enterprise_reports(total_impact_usd DESC);
    """)

    # Create GIN index for JSONB data
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_reports_data
        ON enterprise_reports USING GIN (report_data);
    """)

    print("✅ Created enterprise_reports table with 4 indexes")


def downgrade():
    op.execute("DROP TABLE IF EXISTS enterprise_reports CASCADE;")
    print("✅ Dropped enterprise_reports table")
