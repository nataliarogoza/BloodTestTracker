-- Initial schema: a catalog of tests, lab reports (one per lab visit / PDF),
-- and the individual results inside each report.
-- STRICT makes SQLite reject values of the wrong type (off by default).

CREATE TABLE tests (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL UNIQUE,
    category     TEXT,               -- e.g. "Lipids", "Thyroid"
    default_unit TEXT
) STRICT;

CREATE TABLE reports (
    id          INTEGER PRIMARY KEY,
    date        TEXT NOT NULL        -- SQLite has no date type: stored as YYYY-MM-DD
                CHECK (date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
    lab_name    TEXT,
    source_file TEXT,                -- the PDF this report came from (PDF import phase)
    notes       TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
) STRICT;

CREATE TABLE results (
    id         INTEGER PRIMARY KEY,
    report_id  INTEGER NOT NULL REFERENCES reports(id) ON DELETE CASCADE,  -- deleting a report deletes its results
    test_id    INTEGER NOT NULL REFERENCES tests(id) ON DELETE RESTRICT,   -- can't delete a test that has results
    value      REAL,                 -- the number, full precision
    value_text TEXT,                 -- results that aren't a plain number, e.g. "<0.5"
    unit       TEXT,
    ref_low    REAL,                 -- the lab's reference range, when known
    ref_high   REAL,
    UNIQUE (report_id, test_id),     -- a test appears at most once per report
    CHECK (value IS NOT NULL OR value_text IS NOT NULL)
) STRICT;
