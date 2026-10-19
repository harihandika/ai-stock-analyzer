"""Index the per-stock session reads; no data or column changes.

Revision ID: r3_read_paths
Revises: r2_product
"""

from alembic import op

revision = "r3_read_paths"
down_revision = "r2_product"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_daily_prices_stock_date", "daily_prices", ["stock_ticker", "trading_date"])
    op.create_index(
        "ix_technical_indicators_stock_date",
        "technical_indicators",
        ["stock_ticker", "trading_date"],
    )


def downgrade():
    op.drop_index("ix_technical_indicators_stock_date", table_name="technical_indicators")
    op.drop_index("ix_daily_prices_stock_date", table_name="daily_prices")
