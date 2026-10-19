"""Add provenance and durable quota reservations without rewriting existing data."""

import sqlalchemy as sa

from alembic import op

revision = "r1_integrity"
down_revision = "ijkl5678mnop"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column("analysis_quota_reserved", sa.Integer(), nullable=False, server_default="0"),
    )
    for col in [
        sa.Column("currency", sa.String(3)),
        sa.Column("market_source", sa.String(50)),
        sa.Column("data_revision", sa.String(64)),
        sa.Column("data_fetched_at", sa.DateTime(timezone=True)),
    ]:
        op.add_column("stocks", col)
    for col in [
        sa.Column("provenance", sa.String(20), nullable=False, server_default="unknown"),
        sa.Column("model_name", sa.String(100)),
        sa.Column("prompt_version", sa.String(50)),
        sa.Column("data_revision", sa.String(64)),
        sa.Column("details", sa.JSON()),
    ]:
        op.add_column("ai_analyses", col)
    op.create_table(
        "analysis_requests",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("request_key", sa.String(64), nullable=False),
        sa.Column("input_revision", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("quota_day", sa.Date(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("result_id", sa.Uuid(), sa.ForeignKey("ai_analyses.id")),
        sa.UniqueConstraint("user_id", "request_key", name="uq_analysis_request_key"),
    )
    op.create_index("ix_analysis_requests_user_id", "analysis_requests", ["user_id"])


def downgrade():
    op.drop_table("analysis_requests")
    for col in ["details", "data_revision", "prompt_version", "model_name", "provenance"]:
        op.drop_column("ai_analyses", col)
    for col in ["data_fetched_at", "data_revision", "market_source", "currency"]:
        op.drop_column("stocks", col)
    op.drop_column("users", "analysis_quota_reserved")
