"""Online SQLite backup/restore into a NEW file; never overwrite a database.

For PostgreSQL use pg_dump/pg_restore in the operator runbook. Snapshot files
contain account data and must remain in private operator storage, never Git.
"""

import argparse
import os
import sqlite3
from contextlib import closing
from pathlib import Path

from sqlalchemy.engine import make_url


def copy_snapshot(source, target):
    source, target = Path(source).resolve(), Path(target).resolve()
    if source == target or not source.is_file():
        raise ValueError("Snapshot source must be an existing separate database")
    # O_EXCL refuses replacement, including a symlink at the destination.
    descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
            with closing(sqlite3.connect(target)) as restored:
                original.backup(restored)
                if restored.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise ValueError("Snapshot integrity check failed")
                revision = restored.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        return {"status": "verified", "database": "sqlite", "revision": revision}
    except BaseException:
        target.unlink(missing_ok=True)
        raise


def main():
    import json

    from app.core.config import settings

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["backup", "restore"])
    parser.add_argument("--source", help="Required for restore; optional for backup")
    parser.add_argument(
        "--target", required=True, help="A new file in an existing private directory"
    )
    args = parser.parse_args()
    current = make_url(settings.SYNC_DATABASE_URL)
    if current.get_backend_name() != "sqlite":
        raise SystemExit("Use the PostgreSQL pg_dump/pg_restore runbook for this database")
    if args.operation == "restore" and not args.source:
        raise SystemExit("Restore requires an explicit snapshot source and a new target")
    if Path(args.target).resolve() == Path(current.database).resolve():
        raise SystemExit("Restore/backup target must not be the configured database")
    try:
        print(json.dumps(copy_snapshot(args.source or current.database, args.target)))
    except Exception:
        raise SystemExit("SNAPSHOT_FAILED: verify source and choose a new private target") from None


if __name__ == "__main__":
    main()
