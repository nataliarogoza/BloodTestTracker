""" SQLite connection setup, schema migrations and backups """
import re
import sqlite3
from datetime import datetime
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
MIGRATION_NAME = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$") # e.g. 001_initial.sql
KEEP_STARTUP_BACKUPS = 30 # Older automatic backups are deleted; manual and pre-upgrade ones never are


def connect(db_path) -> sqlite3.Connection:
    """ Open the database with the settings every connection needs """
    # check_same_thread=False: FastAPI may open a connection on one thread and use it on
    # another. That's safe here because each web request gets its own connection.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row # Rows can be read by column name: row["value"]
    conn.execute("PRAGMA foreign_keys = ON") # SQLite ignores foreign keys unless told otherwise
    return conn


def migrate(conn: sqlite3.Connection, migrations_dir: Path = MIGRATIONS_DIR,
            backup_dir: Path | None = None) -> list[str]:
    """ Apply migrations that haven't run yet, in filename order. Each one runs
        all-or-nothing: if it fails halfway, none of its changes are kept.
        With backup_dir, an existing database is backed up before any change.
        Returns the names of the migrations applied this time. """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))")
    already_applied = {row["name"] for row in conn.execute("SELECT name FROM schema_migrations")}

    pending = [p for p in sorted(migrations_dir.glob("*.sql")) if p.name not in already_applied]
    for path in pending:
        if not MIGRATION_NAME.match(path.name):
            raise ValueError(f"Migration file name must look like 001_description.sql, got {path.name}")
    if pending and already_applied and backup_dir is not None:
        # An existing database is about to change shape: keep a copy of how it was.
        # (A brand-new database has nothing worth backing up.)
        backup_database(conn, backup_dir, reason=f"before-{pending[0].stem}")

    applied_now = []
    for path in pending:
        # executescript() can't be wrapped in a Python transaction, so BEGIN/COMMIT go in the script itself
        script = (f"BEGIN;\n{path.read_text()}\n"
                  f"INSERT INTO schema_migrations (name) VALUES ('{path.name}');\nCOMMIT;")
        try:
            conn.executescript(script)
        except sqlite3.Error:
            conn.rollback()
            raise
        applied_now.append(path.name)
    return applied_now


def backup_database(conn: sqlite3.Connection, backup_dir: Path, reason: str = "manual") -> Path:
    """ Save a complete copy of the database, e.g. tracker_2026-10-23_18-05-12_manual.db.
        Uses SQLite's backup feature rather than copying the file: a plain file copy taken
        while the app is writing could catch it half-updated, this is always consistent. """
    backup_dir.mkdir(parents=True, exist_ok=True)
    stem = f"tracker_{datetime.now():%Y-%m-%d_%H-%M-%S}_{reason}"
    path, n = backup_dir / f"{stem}.db", 2
    while path.exists(): # Two backups within the same second
        path, n = backup_dir / f"{stem}_{n}.db", n + 1
    target = sqlite3.connect(path)
    try:
        conn.backup(target)
    finally:
        target.close()
    return path


def list_backups(backup_dir: Path) -> list[Path]:
    """ Database backups in the folder, newest first """
    if not backup_dir.is_dir():
        return []
    return sorted(backup_dir.glob("tracker_*.db"), key=lambda p: p.stat().st_mtime, reverse=True)


def backup_on_startup(conn: sqlite3.Connection, db_path: Path, backup_dir: Path,
                      keep: int = KEEP_STARTUP_BACKUPS) -> Path | None:
    """ The automatic backup made every time the app starts - but only if the database
        changed since the newest backup, so just opening the app doesn't pile up copies.
        Keeps the newest `keep` automatic backups. Returns the new backup, or None if skipped. """
    backups = list_backups(backup_dir)
    if backups and backups[0].stat().st_mtime >= db_path.stat().st_mtime:
        return None # Nothing was saved to the database since the last backup
    path = backup_database(conn, backup_dir, reason="startup")
    for old in [p for p in list_backups(backup_dir) if "_startup" in p.name][keep:]:
        old.unlink()
    return path
