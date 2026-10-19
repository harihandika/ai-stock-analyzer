"""Both a fresh install and a populated legacy database must survive upgrades."""

import uuid

import pytest
from sqlalchemy import create_engine, inspect, text

from alembic import command
from alembic.config import Config
from app.core.config import settings


@pytest.mark.parametrize("legacy", [False, True])
def test_schema_upgrade_preserves_user_and_watchlist(tmp_path, monkeypatch, legacy):
    url = "sqlite:///" + str(tmp_path / "migration.db")
    monkeypatch.setattr(settings, "SYNC_DATABASE_URL", url)
    config = Config("alembic.ini")
    engine = create_engine(url)
    if legacy:
        command.upgrade(config, "ijkl5678mnop")
        with engine.begin() as connection:
            user_id, item_id = uuid.uuid4().hex, uuid.uuid4().hex
            connection.execute(
                text(
                    "INSERT INTO users (id,email,password_hash,full_name,subscription_tier,analysis_quota_used,is_active)"
                    " VALUES (:id,'legacy@example.com','hashed','Legacy','free',2,1)"
                ),
                {"id": user_id},
            )
            connection.execute(
                text(
                    "INSERT INTO stocks (ticker,company_name,is_active) VALUES ('BBCA.JK','Legacy stock',1)"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO watchlists (id,user_id,stock_ticker,notes)"
                    " VALUES (:id,:user,'BBCA.JK','Keep this note')"
                ),
                {"id": item_id, "user": user_id},
            )
    command.upgrade(config, "head")
    inspector = inspect(engine)
    assert "analysis_requests" in inspector.get_table_names()
    assert "analysis_quota_reserved" in {c["name"] for c in inspector.get_columns("users")}
    assert "provenance" in {c["name"] for c in inspector.get_columns("ai_analyses")}
    with engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "r3_read_paths"
        if legacy:
            assert connection.scalar(text("SELECT analysis_quota_used FROM users")) == 2
            assert connection.scalar(text("SELECT notes FROM watchlists")) == "Keep this note"
    engine.dispose()
