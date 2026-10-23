from datetime import date

import pytest

from bloodtracker import services
from bloodtracker.services import NotFoundError, ValidationError

TODAY = date(2026, 10, 23) # Fixed "today", so the future-date check doesn't depend on the real clock


def lookup_test_id(conn, name): # Not named test_...: pytest would try to run it as a test
    return conn.execute("SELECT id FROM tests WHERE name = ?", (name,)).fetchone()["id"]


@pytest.fixture
def ferritin(conn):
    return lookup_test_id(conn, "Ferritin")


@pytest.fixture
def hemoglobin(conn):
    return lookup_test_id(conn, "Hemoglobin (HGB)")


def add(conn, test, day="2024-10-29", value="85", unit="ng/ml"):
    return services.add_result(conn, test, day, value, unit, today=TODAY)


def report_count(conn):
    return conn.execute("SELECT count(*) FROM reports").fetchone()[0]


# --- Parsing values ---

@pytest.mark.parametrize("typed, expected", [
    ("13.5", (13.5, None)),
    ("13,5", (13.5, None)),     # decimal comma
    ("  7 ", (7.0, None)),
    ("-2.1", (-2.1, None)),
    ("<0,5", (None, "<0.5")),   # a bound, kept as text
    (">= 1000", (None, ">=1000")),
])
def test_parse_value_accepts(typed, expected):
    assert services.parse_value(typed) == expected


@pytest.mark.parametrize("typed", ["", "   ", "abc", "nan", "inf", "1,2,3", "<", "<abc"])
def test_parse_value_rejects(typed):
    with pytest.raises(ValidationError):
        services.parse_value(typed)


# --- Parsing dates ---

def test_parse_date_accepts_today_and_past():
    assert services.parse_date("2026-10-23", today=TODAY) == "2026-10-23"
    assert services.parse_date("2016-12-28", today=TODAY) == "2016-12-28"


@pytest.mark.parametrize("typed", ["", "23.10.2026", "2026-13-01", "2026-10-24"]) # last one: tomorrow
def test_parse_date_rejects(typed):
    with pytest.raises(ValidationError):
        services.parse_date(typed, today=TODAY)


# --- Adding ---

def test_add_result_creates_report_for_new_date(conn, ferritin):
    result_id = add(conn, ferritin)
    row = services.get_result(conn, result_id)
    assert (row["date"], row["test_name"], row["value"], row["unit"]) == ("2024-10-29", "Ferritin", 85.0, "ng/ml")
    assert report_count(conn) == 1


def test_add_result_joins_existing_report_for_same_date(conn, ferritin, hemoglobin):
    first = add(conn, ferritin)
    second = add(conn, hemoglobin, value="13,4", unit="g/dl")
    assert services.get_result(conn, first)["report_id"] == services.get_result(conn, second)["report_id"]
    assert report_count(conn) == 1


def test_add_result_stores_bound_as_text(conn, ferritin):
    row = services.get_result(conn, add(conn, ferritin, value="<5"))
    assert (row["value"], row["value_text"]) == (None, "<5")


def test_add_same_test_twice_on_one_date_is_refused(conn, ferritin):
    add(conn, ferritin)
    with pytest.raises(ValidationError, match="already have Ferritin on 2024-10-29"):
        add(conn, ferritin, value="90")


def test_add_unknown_test_is_refused(conn):
    with pytest.raises(ValidationError, match="choose a test"):
        add(conn, 99999)


def test_empty_unit_is_stored_as_none(conn, ferritin):
    assert services.get_result(conn, add(conn, ferritin, unit="  "))["unit"] is None


def test_failed_add_saves_nothing(conn, ferritin):
    with pytest.raises(ValidationError):
        add(conn, ferritin, value="abc")
    assert conn.execute("SELECT count(*) FROM results").fetchone()[0] == 0
    assert report_count(conn) == 0


# --- Editing ---

def test_update_changes_value(conn, ferritin):
    result_id = add(conn, ferritin)
    services.update_result(conn, result_id, ferritin, "2024-10-29", "90,5", "ng/ml", today=TODAY)
    assert services.get_result(conn, result_id)["value"] == 90.5
    assert report_count(conn) == 1


def test_update_to_new_date_moves_result_and_removes_empty_report(conn, ferritin):
    result_id = add(conn, ferritin)
    services.update_result(conn, result_id, ferritin, "2025-01-15", "85", "ng/ml", today=TODAY)
    assert services.get_result(conn, result_id)["date"] == "2025-01-15"
    assert [r["date"] for r in conn.execute("SELECT date FROM reports")] == ["2025-01-15"]


def test_update_to_date_that_already_has_the_test_is_refused(conn, ferritin):
    add(conn, ferritin, day="2024-10-29")
    later = add(conn, ferritin, day="2025-01-15")
    with pytest.raises(ValidationError, match="already have Ferritin on 2024-10-29"):
        services.update_result(conn, later, ferritin, "2024-10-29", "85", "ng/ml", today=TODAY)


def test_update_without_changing_date_is_not_a_duplicate(conn, ferritin):
    result_id = add(conn, ferritin)
    services.update_result(conn, result_id, ferritin, "2024-10-29", "85", "ng/ml", today=TODAY) # Same date: fine


def test_update_missing_result_raises_not_found(conn, ferritin):
    with pytest.raises(NotFoundError):
        services.update_result(conn, 12345, ferritin, "2024-10-29", "85", "ng/ml", today=TODAY)


# --- Deleting ---

def test_delete_last_result_removes_its_report(conn, ferritin):
    services.delete_result(conn, add(conn, ferritin))
    assert report_count(conn) == 0


def test_delete_keeps_report_with_other_results(conn, ferritin, hemoglobin):
    first = add(conn, ferritin)
    add(conn, hemoglobin, value="13.4", unit="g/dl")
    services.delete_result(conn, first)
    assert report_count(conn) == 1


def test_delete_missing_result_raises_not_found(conn):
    with pytest.raises(NotFoundError):
        services.delete_result(conn, 12345)


# --- Listing ---

def test_list_results_newest_first(conn, ferritin, hemoglobin):
    add(conn, ferritin, day="2020-02-18")
    add(conn, ferritin, day="2024-10-29")
    add(conn, hemoglobin, day="2024-10-29", value="13.4", unit="g/dl")
    rows = [(r["date"], r["test_name"]) for r in services.list_results(conn)]
    assert rows == [("2024-10-29", "Ferritin"), ("2024-10-29", "Hemoglobin (HGB)"), ("2020-02-18", "Ferritin")]


def test_list_tests_includes_whole_catalog_grouped(conn):
    tests = services.list_tests(conn)
    assert len(tests) == 73
    categories = [t["category"] for t in tests]
    assert categories == sorted(categories) # Grouped: each category's tests are together


def test_list_units_keeps_old_units_and_used_ones(conn, ferritin):
    add(conn, ferritin, unit="custom-unit")
    units = services.list_units(conn)
    assert {"mm/h", "nmol/l", "ng/ml", "custom-unit"} <= set(units)
    assert len(units) == len(set(units))


def test_history_is_oldest_first_and_only_that_test(conn, ferritin, hemoglobin):
    add(conn, ferritin, day="2024-10-29", value="85")
    add(conn, ferritin, day="2020-02-18", value="40")
    add(conn, hemoglobin, day="2024-10-29", value="13.4", unit="g/dl")
    history = services.test_history(conn, ferritin)
    assert [(r["date"], r["value"]) for r in history] == [("2020-02-18", 40.0), ("2024-10-29", 85.0)]


# --- Statistics ---

def test_stats_known_values():
    stats = services.compute_stats([2, 4, 4, 4, 5, 5, 7, 9]) # A textbook example: mean 5, std 2
    assert (stats.count, stats.min, stats.max, stats.mean, stats.std) == (8, 2, 9, 5, 2)


def test_stats_single_value_has_zero_spread():
    assert services.compute_stats([85.0]).std == 0


def test_stats_of_nothing_is_none():
    assert services.compute_stats([]) is None
