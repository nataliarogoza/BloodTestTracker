import sqlite3

import pytest

from bloodtracker.db import connect, migrate


def add_test(conn, name="Ferritin"):
    return conn.execute("INSERT INTO tests (name) VALUES (?)", (name,)).lastrowid


def add_report(conn, date="2024-10-29"):
    return conn.execute("INSERT INTO reports (date) VALUES (?)", (date,)).lastrowid


def add_result(conn, report_id, test_id, value=42.0, value_text=None):
    return conn.execute(
        "INSERT INTO results (report_id, test_id, value, value_text) VALUES (?, ?, ?, ?)",
        (report_id, test_id, value, value_text)).lastrowid


# --- Migrations ---

def test_migrate_creates_tables(conn):
    tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"tests", "reports", "results", "schema_migrations"} <= tables


def test_migrate_runs_each_migration_only_once(db_path):
    conn = connect(db_path)
    assert migrate(conn) == ["001_initial.sql"]
    assert migrate(conn) == [] # Second run: nothing left to do
    conn.close()


def test_failed_migration_keeps_no_changes(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "001_good.sql").write_text("CREATE TABLE a (x INTEGER);")
    (migrations / "002_broken.sql").write_text("CREATE TABLE b (x INTEGER);\nTHIS IS NOT SQL;")
    conn = connect(tmp_path / "test.db")

    with pytest.raises(sqlite3.Error):
        migrate(conn, migrations)

    tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "a" in tables      # The good migration stayed applied
    assert "b" not in tables  # The broken one was rolled back completely
    recorded = [row["name"] for row in conn.execute("SELECT name FROM schema_migrations")]
    assert recorded == ["001_good.sql"]


def test_badly_named_migration_is_rejected(tmp_path):
    migrations = tmp_path / "migrations"
    migrations.mkdir()
    (migrations / "initial.sql").write_text("CREATE TABLE a (x INTEGER);")
    with pytest.raises(ValueError):
        migrate(connect(tmp_path / "test.db"), migrations)


# --- Rules the schema enforces ---

def test_result_must_point_to_existing_report(conn):
    test_id = add_test(conn)
    with pytest.raises(sqlite3.IntegrityError):
        add_result(conn, report_id=999, test_id=test_id) # No report 999


def test_result_needs_a_value_or_text(conn):
    report_id, test_id = add_report(conn), add_test(conn)
    with pytest.raises(sqlite3.IntegrityError):
        add_result(conn, report_id, test_id, value=None, value_text=None)


def test_text_result_like_less_than_is_allowed(conn):
    report_id, test_id = add_report(conn), add_test(conn)
    add_result(conn, report_id, test_id, value=None, value_text="<0.5")


def test_same_test_twice_in_one_report_is_rejected(conn):
    report_id, test_id = add_report(conn), add_test(conn)
    add_result(conn, report_id, test_id)
    with pytest.raises(sqlite3.IntegrityError):
        add_result(conn, report_id, test_id)


def test_wrong_type_is_rejected(conn):
    report_id, test_id = add_report(conn), add_test(conn)
    with pytest.raises(sqlite3.IntegrityError):
        add_result(conn, report_id, test_id, value="not a number")


def test_badly_formatted_date_is_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_report(conn, date="29/10/2024")


def test_values_keep_full_precision(conn):
    report_id, test_id = add_report(conn), add_test(conn)
    add_result(conn, report_id, test_id, value=0.004) # The old database would have stored 0.00
    stored = conn.execute("SELECT value FROM results").fetchone()["value"]
    assert stored == 0.004


def test_deleting_report_deletes_its_results(conn):
    report_id, test_id = add_report(conn), add_test(conn)
    add_result(conn, report_id, test_id)
    conn.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    assert conn.execute("SELECT count(*) FROM results").fetchone()[0] == 0


def test_test_with_results_cannot_be_deleted(conn):
    report_id, test_id = add_report(conn), add_test(conn)
    add_result(conn, report_id, test_id)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("DELETE FROM tests WHERE id = ?", (test_id,))
