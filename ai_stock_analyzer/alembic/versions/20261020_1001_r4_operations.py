"""Persist operator ingestion evidence and independent worker liveness.

Revision ID: r4_operations
Revises: r3_read_paths
"""

import sqlalchemy as sa

from alembic import op

revision = "r4_operations"
down_revision = "r3_read_paths"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "worker_heartbeats",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("progress_at", sa.DateTime(timezone=True)),
        sa.Column("stopped_at", sa.DateTime(timezone=True)),
        sa.Column("error_code", sa.String(40)),
    )
    op.create_index("ix_worker_heartbeats_heartbeat_at", "worker_heartbeats", ["heartbeat_at"])
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("tickers", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON()),
    )
    op.create_index("ix_ingestion_runs_started_at", "ingestion_runs", ["started_at"])


def downgrade():
    op.drop_index("ix_ingestion_runs_started_at", table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
    op.drop_index("ix_worker_heartbeats_heartbeat_at", table_name="worker_heartbeats")
    op.drop_table("worker_heartbeats")
