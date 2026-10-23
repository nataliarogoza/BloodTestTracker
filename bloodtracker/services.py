""" Everything the app does with results: list, add, edit, delete, and statistics.

    Functions take an open database connection, so web pages, tests and later
    features (PDF import, chat) all share the same rules. Problems the user can fix
    raise ValidationError with a message that's safe to show on the page. """
import math
import re
import sqlite3
from dataclasses import dataclass
from datetime import date

# Suggested in the unit field, carried over from the old app's units list.
# Units already used in results are suggested too, and any unit can be typed in.
KNOWN_UNITS = [
    "%", "10^9/l", "IU/l", "IU/ml", "K/μl", "M/μl", "cells/l", "fl", "g/dl", "g/l",
    "mIU/ml", "mg/dl", "mg/l", "ml/min/1.73 m²", "mm/h", "mmol/l", "ng/dl", "ng/ml",
    "nmol/l", "pg", "pg/ml", "pmol/l", "sec", "μIU/ml", "μg/dl",
]

# A bound instead of an exact number, e.g. "<0.5" or ">= 1000"
BOUND_VALUE = re.compile(r"([<>]=?)\s*(\d+(?:[.,]\d+)?)")


class ValidationError(ValueError):
    """ Input the user needs to correct; the message is shown on the page """


class NotFoundError(LookupError):
    """ The requested result doesn't exist (e.g. it was already deleted) """


@dataclass(frozen=True)
class Stats:
    count: int
    min: float
    max: float
    mean: float
    std: float # Population standard deviation, the same formula the old app used


@dataclass(frozen=True)
class UnitSeries:
    """ One test's numeric results in a single unit: one line on the chart """
    unit: str | None
    dates: list[str]
    values: list[float]
    stats: Stats


# --- Parsing user input ---

def parse_value(raw: str) -> tuple[float | None, str | None]:
    """ Turn what the user typed into (number, text). Exactly one is set:
        "13.5" and "13,5" -> (13.5, None);  "<0,5" -> (None, "<0.5") """
    text = (raw or "").strip()
    if not text:
        raise ValidationError("Please enter a result value.")
    try:
        number = float(text.replace(",", ".")) # Polish lab sheets use a decimal comma
    except ValueError:
        bound = BOUND_VALUE.fullmatch(text)
        if bound:
            return None, bound.group(1) + bound.group(2).replace(",", ".")
        raise ValidationError(f"“{text}” isn't a number. Examples: 13.5, 13,5 or <0.5.")
    if not math.isfinite(number): # float() also accepts "nan" and "inf"
        raise ValidationError(f"“{text}” isn't a number. Examples: 13.5, 13,5 or <0.5.")
    return number, None


def parse_date(raw: str, today: date | None = None) -> str:
    """ Validate a YYYY-MM-DD date that isn't in the future; returns it unchanged """
    try:
        day = date.fromisoformat((raw or "").strip())
    except ValueError:
        raise ValidationError("Please enter a date as YYYY-MM-DD.") from None
    if day > (today or date.today()):
        raise ValidationError("The test date can't be in the future.")
    return day.isoformat()


# --- Reading ---

RESULT_COLUMNS = """
    rs.id, rp.date, rs.test_id, t.name AS test_name, t.category,
    rs.value, rs.value_text, rs.unit, rs.report_id
    FROM results rs
    JOIN reports rp ON rp.id = rs.report_id
    JOIN tests t ON t.id = rs.test_id"""


def list_results(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """ Every result, newest test date first """
    return conn.execute(f"SELECT {RESULT_COLUMNS} ORDER BY rp.date DESC, t.name").fetchall()


def get_result(conn: sqlite3.Connection, result_id: int) -> sqlite3.Row:
    row = conn.execute(f"SELECT {RESULT_COLUMNS} WHERE rs.id = ?", (result_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Result {result_id} doesn't exist")
    return row


def list_tests(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """ All known tests, grouped by category (uncategorized ones last) """
    return conn.execute(
        "SELECT id, name, category, default_unit FROM tests "
        "ORDER BY category IS NULL, category, name").fetchall()


def list_units(conn: sqlite3.Connection) -> list[str]:
    """ Units to suggest: the old app's list, every test's usual unit, and every unit used """
    rows = conn.execute("SELECT default_unit FROM tests UNION SELECT unit FROM results").fetchall()
    return sorted({unit for (unit,) in rows if unit} | set(KNOWN_UNITS), key=str.lower)


def test_history(conn: sqlite3.Connection, test_id: int) -> list[sqlite3.Row]:
    """ One test's results over time, oldest first (for the chart) """
    return conn.execute(f"SELECT {RESULT_COLUMNS} WHERE rs.test_id = ? ORDER BY rp.date", (test_id,)).fetchall()


def get_test(conn: sqlite3.Connection, test_id: int) -> sqlite3.Row:
    row = conn.execute("SELECT id, name, category, default_unit FROM tests WHERE id = ?", (test_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Test {test_id} doesn't exist")
    return row


def list_tests_with_results(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    """ Tests that have at least one result, with how many - the charts page only offers these """
    return conn.execute(
        "SELECT t.id, t.name, t.category, count(rs.id) AS result_count FROM tests t "
        "JOIN results rs ON rs.test_id = t.id GROUP BY t.id "
        "ORDER BY t.category IS NULL, t.category, t.name").fetchall()


def series_by_unit(history: list[sqlite3.Row]) -> list[UnitSeries]:
    """ Split a test's history into one series per unit. Mixing units on one line (or in
        one average) would be meaningless, e.g. FT4 in ng/dl and pmol/l. Text values like
        "<0.5" aren't exact numbers, so they're left out. Units appear in the order first used. """
    by_unit = {}
    for row in history:
        if row["value"] is not None:
            dates, values = by_unit.setdefault(row["unit"], ([], []))
            dates.append(row["date"])
            values.append(row["value"])
    return [UnitSeries(unit, dates, values, compute_stats(values)) for unit, (dates, values) in by_unit.items()]


def compute_stats(values: list[float]) -> Stats | None:
    """ Summary of the numeric values; None when there are none """
    if not values:
        return None
    mean = sum(values) / len(values)
    std = math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))
    return Stats(count=len(values), min=min(values), max=max(values), mean=mean, std=std)


# --- Changing ---

def add_result(conn: sqlite3.Connection, test_id: int, date_raw: str, value_raw: str,
               unit: str | None, today: date | None = None) -> int:
    """ Save a new result, in the report for its date (created if needed). Returns its id. """
    test_name, day, value, value_text, unit = _validate(conn, test_id, date_raw, value_raw, unit, today)
    _refuse_duplicate(conn, test_id, test_name, day)
    with conn: # One transaction: committed if everything succeeds, rolled back otherwise
        report_id = _report_for_date(conn, day)
        return conn.execute(
            "INSERT INTO results (report_id, test_id, value, value_text, unit) VALUES (?, ?, ?, ?, ?)",
            (report_id, test_id, value, value_text, unit)).lastrowid


def update_result(conn: sqlite3.Connection, result_id: int, test_id: int, date_raw: str,
                  value_raw: str, unit: str | None, today: date | None = None):
    """ Change a result. A new date moves it to that date's report. """
    old = get_result(conn, result_id)
    test_name, day, value, value_text, unit = _validate(conn, test_id, date_raw, value_raw, unit, today)
    _refuse_duplicate(conn, test_id, test_name, day, ignore_result_id=result_id)
    with conn:
        report_id = old["report_id"] if day == old["date"] else _report_for_date(conn, day)
        conn.execute(
            "UPDATE results SET report_id = ?, test_id = ?, value = ?, value_text = ?, unit = ? WHERE id = ?",
            (report_id, test_id, value, value_text, unit, result_id))
        if report_id != old["report_id"]:
            _delete_report_if_empty(conn, old["report_id"])


def delete_result(conn: sqlite3.Connection, result_id: int):
    """ Delete a result; its report goes too if nothing else is left in it """
    old = get_result(conn, result_id)
    with conn:
        conn.execute("DELETE FROM results WHERE id = ?", (result_id,))
        _delete_report_if_empty(conn, old["report_id"])


# --- Helpers ---

def _validate(conn, test_id, date_raw, value_raw, unit, today):
    test = conn.execute("SELECT name FROM tests WHERE id = ?", (test_id,)).fetchone()
    if test is None:
        raise ValidationError("Please choose a test from the list.")
    day = parse_date(date_raw, today)
    value, value_text = parse_value(value_raw)
    unit = (unit or "").strip() or None # Some results have no unit (e.g. ratios)
    return test["name"], day, value, value_text, unit


def _refuse_duplicate(conn, test_id, test_name, day, ignore_result_id=None):
    """ A test can be recorded only once per date - friendlier than the database's own error """
    clash = conn.execute(
        "SELECT rs.id FROM results rs JOIN reports rp ON rp.id = rs.report_id "
        "WHERE rs.test_id = ? AND rp.date = ? AND rs.id IS NOT ?",
        (test_id, day, ignore_result_id)).fetchone()
    if clash:
        raise ValidationError(f"You already have {test_name} on {day} - edit that result instead.")


def _report_for_date(conn, day) -> int:
    """ The report (lab visit) for this date, created if there isn't one yet """
    row = conn.execute("SELECT id FROM reports WHERE date = ? ORDER BY id LIMIT 1", (day,)).fetchone()
    if row:
        return row["id"]
    return conn.execute("INSERT INTO reports (date) VALUES (?)", (day,)).lastrowid


def _delete_report_if_empty(conn, report_id):
    conn.execute(
        "DELETE FROM reports WHERE id = ? AND NOT EXISTS (SELECT 1 FROM results WHERE report_id = ?)",
        (report_id, report_id))
