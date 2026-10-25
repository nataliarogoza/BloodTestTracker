""" One-off copy of results from the old PostgreSQL app into the new SQLite database.

    Run once with:  python -m bloodtracker.legacy_import [--db PATH]

    PostgreSQL is opened read-only and never changed, so the old app keeps working.
    Each old test date becomes one report, and every result is checked after copying:
    if anything doesn't match, nothing is saved. """
import argparse
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path

from bloodtracker.config import DB_PATH, PROJECT_DIR
from bloodtracker.db import connect, migrate

IMPORT_NOTE = "Imported from the old app"


@dataclass(frozen=True)
class LegacyRow:
    """ One row of the old results table """
    test_name: str
    value: Decimal
    unit: str
    test_date: date


def read_postgres_rows(env_path: Path = PROJECT_DIR / ".env") -> list[LegacyRow]:
    """ Read every result from the old database, using the old app's .env credentials """
    import psycopg2 # Imported here: only needed for this one-off import (the "migrate" extra)
    from dotenv import dotenv_values

    env = dotenv_values(env_path)
    conn = psycopg2.connect(
        dbname=env.get("DB_NAME"), user=env.get("DB_USER"), password=env.get("DB_PASSWORD"),
        host=env.get("DB_HOST") or "localhost", port=env.get("DB_PORT") or "5432")
    try:
        conn.set_session(readonly=True) # Postgres itself refuses any change on this connection
        with conn.cursor() as cur:
            cur.execute("SELECT test_name, result_value, unit, test_date "
                        "FROM results_schema.results ORDER BY test_date, id")
            return [LegacyRow(*row) for row in cur.fetchall()]
    finally:
        conn.close()


def import_rows(conn: sqlite3.Connection, rows: list[LegacyRow]) -> dict:
    """ Copy the rows into an empty, migrated database and verify them, all in one
        transaction: either everything is saved and checked, or nothing is. """
    if conn.execute("SELECT count(*) FROM results").fetchone()[0]:
        raise ValueError("The new database already has results - refusing to import twice")

    try:
        test_ids = {row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM tests")}
        new_tests = sorted({r.test_name for r in rows} - set(test_ids))
        for name in new_tests: # Not in the catalog: add without a category, to sort out later
            test_ids[name] = conn.execute("INSERT INTO tests (name) VALUES (?)", (name,)).lastrowid

        report_ids = {}
        for day in sorted({r.test_date for r in rows}): # One report per lab visit (test date)
            report_ids[day] = conn.execute(
                "INSERT INTO reports (date, notes) VALUES (?, ?)", (day.isoformat(), IMPORT_NOTE)).lastrowid

        conn.executemany(
            "INSERT INTO results (report_id, test_id, value, unit) VALUES (?, ?, ?, ?)",
            [(report_ids[r.test_date], test_ids[r.test_name], float(r.value), r.unit) for r in rows])

        verify(conn, rows)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    return {"results": len(rows), "reports": len(report_ids), "new_tests": new_tests}


def verify(conn: sqlite3.Connection, rows: list[LegacyRow]):
    """ Raise if the copied results don't match the source exactly """
    expected = Counter((r.test_date.isoformat(), r.test_name, r.value, r.unit) for r in rows)
    copied = Counter(
        (row["date"], row["name"], Decimal(repr(row["value"])), row["unit"]) # repr() gives the shortest exact form, e.g. 13.45
        for row in conn.execute("SELECT rp.date, t.name, rs.value, rs.unit FROM results rs "
                                "JOIN reports rp ON rp.id = rs.report_id JOIN tests t ON t.id = rs.test_id"))
    if copied != expected:
        missing, extra = expected - copied, copied - expected
        raise ValueError(f"Copied data doesn't match the source. Missing: {list(missing)[:5]} Unexpected: {list(extra)[:5]}")


def main():
    parser = argparse.ArgumentParser(description="Copy results from the old PostgreSQL app into SQLite")
    parser.add_argument("--db", type=Path, default=DB_PATH, help=f"SQLite database to fill (default: {DB_PATH})")
    args = parser.parse_args()

    rows = read_postgres_rows()
    print(f"Read {len(rows)} results from PostgreSQL")

    args.db.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(args.db)
    try:
        migrate(conn)
        summary = import_rows(conn, rows)
    except ValueError as e:
        sys.exit(f"Import stopped, nothing was saved: {e}")
    finally:
        conn.close()

    print(f"Copied and verified {summary['results']} results in {summary['reports']} reports -> {args.db}")
    if summary["new_tests"]:
        print(f"Tests not in the catalog (added without a category): {summary['new_tests']}")


if __name__ == "__main__":
    main()
