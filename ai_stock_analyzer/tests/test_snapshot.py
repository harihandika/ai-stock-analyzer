import os
import sqlite3

import pytest

from scripts.sqlite_snapshot import copy_snapshot


def test_online_snapshot_restore_preserves_data_and_refuses_overwrite(tmp_path):
    source, backup, restored = (
        tmp_path / name for name in ["source.db", "backup.db", "restored.db"]
    )
    with sqlite3.connect(source) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE alembic_version (version_num TEXT)")
        db.execute("INSERT INTO alembic_version VALUES ('r4_operations')")
        db.execute("CREATE TABLE watchlists (notes TEXT)")
        db.execute("INSERT INTO watchlists VALUES ('Keep this note')")
        db.commit()
        assert copy_snapshot(source, backup)["revision"] == "r4_operations"
    assert os.stat(backup).st_mode & 0o777 == 0o600
    copy_snapshot(backup, restored)
    with sqlite3.connect(restored) as db:
        assert db.execute("SELECT notes FROM watchlists").fetchone()[0] == "Keep this note"
    with pytest.raises(FileExistsError):
        copy_snapshot(source, restored)
    with pytest.raises(ValueError):
        copy_snapshot(source, source)
    link = tmp_path / "link.db"
    link.symlink_to(restored)
    with pytest.raises(FileExistsError):
        copy_snapshot(source, link)
