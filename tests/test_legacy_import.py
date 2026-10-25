""" Tests for the one-off PostgreSQL import, using fake rows - no PostgreSQL needed """
from datetime import date
from decimal import Decimal

import pytest

from bloodtracker.legacy_import import LegacyRow, import_rows, verify


def row(name, value, unit, day):
    return LegacyRow(name, Decimal(value), unit, date.fromisoformat(day))


ROWS = [
    row("Ferritin", "85.00", "ng/ml", "2024-10-29"),
    row("Hemoglobin (HGB)", "13.45", "g/dl", "2024-10-29"),
    row("Ferritin", "61.20", "ng/ml", "2026-02-07"),
]


def count(conn, table):
    return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def test_each_date_becomes_one_report(conn):
    summary = import_rows(conn, ROWS)
    assert summary["results"] == 3
    assert summary["reports"] == 2
    assert [r["date"] for r in conn.execute("SELECT date FROM reports ORDER BY date")] == ["2024-10-29", "2026-02-07"]


def test_values_and_units_are_copied_exactly(conn):
    import_rows(conn, ROWS)
    copied = conn.execute(
        "SELECT rs.value, rs.unit FROM results rs JOIN tests t ON t.id = rs.test_id "
        "JOIN reports rp ON rp.id = rs.report_id "
        "WHERE t.name = 'Hemoglobin (HGB)' AND rp.date = '2024-10-29'").fetchone()
    assert (copied["value"], copied["unit"]) == (13.45, "g/dl")


def test_results_link_to_catalog_tests(conn):
    tests_before = count(conn, "tests")
    summary = import_rows(conn, ROWS)
    assert summary["new_tests"] == []
    assert count(conn, "tests") == tests_before # No duplicates of catalog tests


def test_unknown_test_is_added_without_category(conn):
    summary = import_rows(conn, ROWS + [row("Mystery Marker", "1.5", "U/l", "2024-10-29")])
    assert summary["new_tests"] == ["Mystery Marker"]
    assert conn.execute("SELECT category FROM tests WHERE name = 'Mystery Marker'").fetchone()[0] is None


def test_importing_twice_is_refused(conn):
    import_rows(conn, ROWS)
    with pytest.raises(ValueError, match="refusing to import twice"):
        import_rows(conn, ROWS)
    assert count(conn, "results") == 3


def test_failed_import_saves_nothing(conn):
    duplicate = ROWS + [ROWS[0]] # Same test twice on one date breaks the one-per-report rule
    with pytest.raises(Exception):
        import_rows(conn, duplicate)
    assert count(conn, "results") == 0
    assert count(conn, "reports") == 0


def test_verify_catches_a_changed_value(conn):
    import_rows(conn, ROWS)
    conn.execute("UPDATE results SET value = 13.4 WHERE value = 13.45") # Simulate a copy error
    with pytest.raises(ValueError, match="doesn't match"):
        verify(conn, ROWS)
