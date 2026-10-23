""" SQLite connection setup and schema migrations """
import re
import sqlite3
from pathlib import Path

MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"
MIGRATION_NAME = re.compile(r"^\d{3}_[a-z0-9_]+\.sql$") # e.g. 001_initial.sql


def connect(db_path) -> sqlite3.Connection:
    """ Open the database with the settings every connection needs """
    # check_same_thread=False: FastAPI may open a connection on one thread and use it on
    # another. That's safe here because each web request gets its own connection.
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row # Rows can be read by column name: row["value"]
    conn.execute("PRAGMA foreign_keys = ON") # SQLite ignores foreign keys unless told otherwise
    return conn


def migrate(conn: sqlite3.Connection, migrations_dir: Path = MIGRATIONS_DIR) -> list[str]:
    """ Apply migrations that haven't run yet, in filename order. Each one runs
        all-or-nothing: if it fails halfway, none of its changes are kept.
        Returns the names of the migrations applied this time. """
    conn.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT (datetime('now')))")
    already_applied = {row["name"] for row in conn.execute("SELECT name FROM schema_migrations")}

    applied_now = []
    for path in sorted(migrations_dir.glob("*.sql")):
        if path.name in already_applied:
            continue
        if not MIGRATION_NAME.match(path.name):
            raise ValueError(f"Migration file name must look like 001_description.sql, got {path.name}")
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
