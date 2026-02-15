"""Add PII detection log table

Revision ID: 005_add_pii_detection_log
Revises: 004_add_privacy_levels
Create Date: 2025-10-23

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_pii_detection_log'
down_revision = '004_add_privacy_levels'
branch_labels = None
depends_on = None


def upgrade():
    """Create PII detection log table"""
    # Use raw SQL with IF NOT EXISTS for idempotency
    op.execute("""
        CREATE TABLE IF NOT EXISTS pii_detection_log (
            id SERIAL PRIMARY KEY,
            table_name VARCHAR(100) NOT NULL,
            record_id VARCHAR(255) NOT NULL,
            pii_type VARCHAR(50) NOT NULL,
            field_name VARCHAR(100) NOT NULL,
            confidence FLOAT NOT NULL,
            detected_at TIMESTAMP NOT NULL DEFAULT NOW(),
            created_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)

    # Create indexes for efficient querying
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pii_log_table_record
        ON pii_detection_log(table_name, record_id);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pii_log_type
        ON pii_detection_log(pii_type);
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_pii_log_detected_at
        ON pii_detection_log(detected_at DESC);
    """)


def downgrade():
    """Drop PII detection log table"""
    op.execute("DROP TABLE IF EXISTS pii_detection_log;")
