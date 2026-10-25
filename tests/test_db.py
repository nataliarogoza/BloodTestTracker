import os
import time
import sqlite3

import pytest

from bloodtracker.db import connect, migrate


def add_test(conn, name="Example Test"): # A name not in the seeded catalog
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
    assert migrate(conn) == ["001_initial.sql", "002_seed_test_catalog.sql"]
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


# --- Test catalog ---

def test_catalog_is_seeded(conn):
    count, uncategorized = conn.execute(
        "SELECT count(*), count(*) FILTER (WHERE category IS NULL) FROM tests").fetchone()
    assert count == 73
    assert uncategorized == 0


# --- Backups ---

from bloodtracker.db import backup_database, list_backups  # noqa: E402


def test_backup_is_a_complete_copy(conn, tmp_path):
    report_id, test_id = add_report(conn), add_test(conn)
    add_result(conn, report_id, test_id, value=0.004)
    conn.commit()
    path = backup_database(conn, tmp_path / "backups")
    copy = connect(path)
    assert copy.execute("SELECT value FROM results").fetchone()["value"] == 0.004
    assert copy.execute("SELECT count(*) FROM tests").fetchone()[0] == 74  # Catalog + "Example Test"
    copy.close()


def test_two_backups_in_the_same_second_get_different_names(conn, tmp_path):
    first = backup_database(conn, tmp_path / "backups")
    second = backup_database(conn, tmp_path / "backups")
    assert first != second and first.exists() and second.exists()


def test_list_backups_newest_first_and_only_database_files(conn, tmp_path):
    folder = tmp_path / "backups"
    old = backup_database(conn, folder)
    new = backup_database(conn, folder)
    os.utime(old, (1_000_000_000, 1_000_000_000))  # Make "old" clearly older
    (folder / "blood_test_backup_20261008.csv").write_text("old CSV from the previous app")
    assert list_backups(folder) == [new, old]


def test_list_backups_of_missing_folder_is_empty(tmp_path):
    assert list_backups(tmp_path / "nope") == []


def make_migrations(folder, *names):
    folder.mkdir(exist_ok=True)
    for i, name in enumerate(names):
        (folder / name).write_text(f"CREATE TABLE t{i} (x INTEGER);")


def test_existing_database_is_backed_up_before_new_migration(tmp_path):
    migrations, backups = tmp_path / "migrations", tmp_path / "backups"
    make_migrations(migrations, "001_first.sql")
    conn = connect(tmp_path / "test.db")
    migrate(conn, migrations, backup_dir=backups)
    assert list_backups(backups) == []  # Brand-new database: nothing to back up

    make_migrations(migrations, "001_first.sql", "002_second.sql")
    migrate(conn, migrations, backup_dir=backups)
    [backup] = list_backups(backups)
    assert "before-002_second" in backup.name
    tables = {r["name"] for r in connect(backup).execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "t0" in tables and "t1" not in tables  # The backup shows the database as it was

    migrate(conn, migrations, backup_dir=backups)
    assert len(list_backups(backups)) == 1  # Nothing new to apply: no extra backup


# --- Automatic backup at startup ---

from bloodtracker.db import backup_on_startup  # noqa: E402


def set_age(path, seconds_ago):
    """ Pretend a file was last written `seconds_ago` seconds ago """
    t = time.time() - seconds_ago
    os.utime(path, (t, t))


def test_startup_backup_is_made_when_there_is_none_yet(conn, db_path, tmp_path):
    path = backup_on_startup(conn, db_path, tmp_path / "backups")
    assert path is not None and "_startup" in path.name


def test_startup_backup_skipped_when_nothing_changed(conn, db_path, tmp_path):
    folder = tmp_path / "backups"
    first = backup_on_startup(conn, db_path, folder)
    set_age(db_path, 100)  # Database last written before the backup
    set_age(first, 50)
    assert backup_on_startup(conn, db_path, folder) is None
    assert len(list_backups(folder)) == 1


def test_startup_backup_made_again_after_a_change(conn, db_path, tmp_path):
    folder = tmp_path / "backups"
    set_age(backup_on_startup(conn, db_path, folder), 100)
    add_report(conn)  # A change...
    conn.commit()     # ...saved to the file, which updates its modified time
    assert backup_on_startup(conn, db_path, folder) is not None
    assert len(list_backups(folder)) == 2


def test_only_the_newest_automatic_backups_are_kept(conn, db_path, tmp_path):
    folder = tmp_path / "backups"
    manual = backup_database(conn, folder, reason="manual")
    upgrade = backup_database(conn, folder, reason="before-002_x")
    set_age(manual, 10_000)
    set_age(upgrade, 10_000)  # Oldest of all - but these kinds are never deleted
    for i in range(5):
        set_age(backup_on_startup(conn, db_path, folder, keep=3), 1000 - i)  # Each newer than the last
        set_age(db_path, 0)  # Pretend something changed, so the next startup backs up again
    automatic = [p for p in list_backups(folder) if "_startup" in p.name]
    assert len(automatic) == 3
    assert manual.exists() and upgrade.exists()
