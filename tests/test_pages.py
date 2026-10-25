""" Tests that go through the real web routes, like the browser does (temporary database) """
import json

import pytest

from bloodtracker.db import connect


@pytest.fixture
def ferritin(db_path, client): # client first, so the app has created and migrated the database
    conn = connect(db_path)
    test_id = conn.execute("SELECT id FROM tests WHERE name = 'Ferritin'").fetchone()["id"]
    conn.close()
    return test_id


def add(client, test_id, date="2024-10-29", value="85", unit="ng/ml", **headers):
    return client.post("/results", data={"test_id": test_id, "date": date, "value": value, "unit": unit},
                       headers=headers)


def result_count(db_path):
    conn = connect(db_path)
    count = conn.execute("SELECT count(*) FROM results").fetchone()[0]
    conn.close()
    return count


def only_result_id(db_path):
    conn = connect(db_path)
    result_id = conn.execute("SELECT id FROM results").fetchone()["id"]
    conn.close()
    return result_id


# --- Main page ---

def test_page_shows_form_with_tests_grouped_by_category(client):
    page = client.get("/").text
    assert '<optgroup label="Blood count">' in page
    assert 'data-unit="ng/ml"' in page  # Ferritin's usual unit, used by app.js to pre-fill
    assert "No results yet" in page


def test_page_lists_existing_results(client, ferritin):
    add(client, ferritin, value="85,5")
    page = client.get("/").text
    assert "Ferritin" in page and "85.5" in page and "2024-10-29" in page


def test_unit_suggestions_include_old_units(client):
    assert '<option value="mm/h">' in client.get("/").text


# --- Adding ---

def test_add_saves_and_returns_fresh_form_plus_table(client, db_path, ferritin):
    response = add(client, ferritin)
    assert response.status_code == 200
    assert result_count(db_path) == 1
    assert "Added Ferritin: 85 ng/ml on 2024-10-29" in response.text
    assert 'id="results-body" hx-swap-oob="true"' in response.text  # The table refreshes too
    assert 'id="result-count" hx-swap-oob="true">1<' in response.text


def test_add_keeps_test_date_and_unit_for_next_entry(client, ferritin):
    form = add(client, ferritin).text
    assert f'value="{ferritin}" data-unit="ng/ml" selected' in form
    assert 'name="date" value="2024-10-29"' in form
    assert 'name="value" value=""' in form  # Only the value is cleared


def test_add_with_bad_value_shows_error_and_keeps_input(client, db_path, ferritin):
    response = add(client, ferritin, value="abc")
    assert "isn&#39;t a number" in response.text  # Escaped apostrophe, as in the page source
    assert 'name="value" value="abc"' in response.text
    assert result_count(db_path) == 0


def test_add_duplicate_shows_friendly_error(client, ferritin):
    add(client, ferritin)
    assert "already have Ferritin on 2024-10-29" in add(client, ferritin, value="90").text


def test_add_without_choosing_test_shows_error(client):
    assert "Please choose a test" in add(client, test_id="").text


def test_typed_text_is_escaped_not_run(client, ferritin):
    page = add(client, ferritin, unit="<script>alert(1)</script>").text
    assert "<script>alert(1)" not in page
    assert "&lt;script&gt;" in page


# --- Editing ---

def test_edit_row_shows_current_values(client, db_path, ferritin):
    add(client, ferritin, value="85,5")
    row = client.get(f"/results/{only_result_id(db_path)}/edit").text
    assert 'class="editing"' in row
    assert 'name="value" value="85.5"' in row


def test_save_updates_and_redraws_table(client, db_path, ferritin):
    add(client, ferritin)
    result_id = only_result_id(db_path)
    response = client.put(f"/results/{result_id}",
                          data={"test_id": ferritin, "date": "2025-01-15", "value": "90", "unit": "ng/ml"})
    assert response.headers["HX-Retarget"] == "#results-body"
    assert "2025-01-15" in response.text and ">90<" in response.text


def test_save_with_bad_input_keeps_row_in_edit_mode(client, db_path, ferritin):
    add(client, ferritin)
    response = client.put(f"/results/{only_result_id(db_path)}",
                          data={"test_id": ferritin, "date": "2024-10-29", "value": "", "unit": "ng/ml"})
    assert "HX-Retarget" not in response.headers
    assert 'class="editing"' in response.text and "Please enter a result value" in response.text


def test_cancel_returns_normal_row(client, db_path, ferritin):
    add(client, ferritin)
    row = client.get(f"/results/{only_result_id(db_path)}").text
    assert "hx-confirm" in row and "editing" not in row


def test_editing_missing_result_reloads_page(client):
    assert client.get("/results/999/edit").headers["HX-Refresh"] == "true"


# --- Deleting ---

def test_delete_removes_result_and_updates_count(client, db_path, ferritin):
    add(client, ferritin)
    response = client.delete(f"/results/{only_result_id(db_path)}")
    assert result_count(db_path) == 0
    assert 'id="result-count" hx-swap-oob="true">0<' in response.text


def test_delete_missing_result_is_harmless(client):
    assert client.delete("/results/999").status_code == 200


# --- Security ---

def test_change_from_another_website_is_refused(client, db_path, ferritin):
    response = add(client, ferritin, Origin="https://evil.example")
    assert response.status_code == 403
    assert result_count(db_path) == 0


def test_change_flagged_cross_site_is_refused(client, db_path, ferritin):
    assert add(client, ferritin, **{"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert result_count(db_path) == 0


def test_change_from_the_app_itself_is_allowed(client, db_path, ferritin):
    assert add(client, ferritin, Origin="http://127.0.0.1", **{"Sec-Fetch-Site": "same-origin"}).status_code == 200
    assert result_count(db_path) == 1


def test_request_with_foreign_host_name_is_refused(client):
    assert client.get("/", headers={"Host": "evil.example"}).status_code == 400


def test_developer_docs_page_is_disabled(client):
    assert client.get("/docs").status_code == 404


def test_htmx_is_served_locally(client):
    response = client.get("/static/js/htmx.min.js")
    assert response.status_code == 200 and "htmx" in response.text


# --- Charts page ---

from bloodtracker.app import format_rounded  # noqa: E402 (only used by the tests below)


def chart_data(page):
    """ The JSON the page embeds for charts.js """
    start = page.index('id="chart-data">') + len('id="chart-data">')
    return json.loads(page[start:page.index("</script>", start)])


def id_of_test(db_path, name): # Not named test_...: pytest would run it as a test
    conn = connect(db_path)
    test_id = conn.execute("SELECT id FROM tests WHERE name = ?", (name,)).fetchone()["id"]
    conn.close()
    return test_id


def test_charts_page_without_test_asks_to_choose(client):
    page = client.get("/charts").text
    assert "Choose a test above" in page
    assert "plotly.min.js" in page  # Plotly is loaded on this page...


def test_results_page_does_not_load_plotly(client):
    assert "plotly.min.js" not in client.get("/").text  # ...but not on the results page


def test_charts_dropdown_lists_only_recorded_tests_with_counts(client, ferritin):
    add(client, ferritin, date="2020-02-18")
    add(client, ferritin, date="2024-10-29")
    page = client.get("/charts").text
    assert "Ferritin (2)" in page
    assert "Hemoglobin (HGB)" not in page  # No results, nothing to chart


def test_charts_page_for_a_test_shows_chart_stats_and_history(client, ferritin):
    add(client, ferritin, date="2020-02-18", value="40")
    add(client, ferritin, date="2024-10-29", value="85")
    page = client.get(f"/charts?test={ferritin}").text
    assert chart_data(page) == {"series": [{"unit": "ng/ml", "dates": ["2020-02-18", "2024-10-29"], "values": [40.0, 85.0]}]}
    assert "2 results · 2020-02-18 → 2024-10-29" in page
    assert "62.5 ± 22.5" in page  # Average ± spread
    assert f'value="{ferritin}" selected' in page


def test_htmx_request_gets_only_the_panel(client, ferritin):
    add(client, ferritin)
    response = client.get(f"/charts?test={ferritin}", headers={"HX-Request": "true"})
    assert 'id="chart-data"' in response.text
    assert "<html" not in response.text  # Just the panel, not the whole page
    assert response.headers["Vary"] == "HX-Request"


def test_back_button_request_gets_whole_page(client, ferritin):
    add(client, ferritin)
    response = client.get(f"/charts?test={ferritin}",
                          headers={"HX-Request": "true", "HX-History-Restore-Request": "true"})
    assert "<html" in response.text


def test_mixed_units_are_explained(client, db_path):
    ft4 = id_of_test(db_path, "Free Thyroxine (FT4)")
    add(client, ft4, date="2024-10-29", value="12.45", unit="pmol/l")
    add(client, ft4, date="2025-11-29", value="1.31", unit="ng/dl")
    page = client.get(f"/charts?test={ft4}").text
    assert "different units (pmol/l, ng/dl)" in page


def test_text_values_are_listed_but_not_charted(client, ferritin):
    add(client, ferritin, date="2020-02-18", value="<5")
    add(client, ferritin, date="2024-10-29", value="85")
    page = client.get(f"/charts?test={ferritin}").text
    assert "1 result like" in page and "&lt;5" in page
    assert chart_data(page)["series"][0]["values"] == [85.0]


def test_only_text_values_means_no_chart(client, ferritin):
    add(client, ferritin, value="<5")
    page = client.get(f"/charts?test={ferritin}").text
    assert "No numeric results to chart" in page and 'id="chart"' not in page


def test_unknown_test_shows_message(client):
    assert "wasn&#39;t found" in client.get("/charts?test=99999").text
    assert "wasn&#39;t found" in client.get("/charts?test=abc").text


def test_results_rows_link_to_their_chart(client, ferritin):
    add(client, ferritin)
    assert f'href="/charts?test={ferritin}"' in client.get("/").text


def test_pages_disable_htmx_history_storage(client):
    assert 'hx-history="false"' in client.get("/charts").text


@pytest.mark.parametrize("number, shown", [
    (61.2333, "61.23"), (62.5, "62.5"), (85.0, "85"), (0.00412, "0.00412"), (0, "0"), (1234.567, "1234.57")])
def test_rounded_numbers(number, shown):
    assert format_rounded(number) == shown


# --- Data page ---

from bloodtracker import config  # noqa: E402


def test_data_page_shows_export_and_backup(client, ferritin):
    add(client, ferritin)
    page = client.get("/data").text
    assert "Download all 1 results" in page
    assert 'href="/export/results.csv"' in page
    assert "No backups yet" in page
    assert 'href="/data"' in page  # In the top bar


def test_export_downloads_csv(client, ferritin):
    add(client, ferritin, value="85,5")
    response = client.get("/export/results.csv")
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["content-disposition"].startswith('attachment; filename="blood_test_results_')
    assert "Ferritin,Iron,85.5,ng/ml" in response.text


def test_backup_button_creates_backup_and_lists_it(client, backup_dir, ferritin):
    add(client, ferritin)
    response = client.post("/backups")
    [backup] = list(backup_dir.glob("tracker_*_manual.db"))
    assert f"Saved {backup.name}" in response.text
    assert backup.name in client.get("/data").text
    assert connect(backup).execute("SELECT count(*) FROM results").fetchone()[0] == 1


def test_backup_from_another_website_is_refused(client, backup_dir):
    assert client.post("/backups", headers={"Origin": "https://evil.example"}).status_code == 403
    assert not backup_dir.exists()


def test_tests_never_use_the_real_backup_folder(client, backup_dir):
    assert client.app.state.backup_dir == backup_dir != config.BACKUP_DIR


def test_default_backup_folder_sits_next_to_the_project():
    assert config.BACKUP_DIR == config.PROJECT_DIR.parent / f"{config.PROJECT_DIR.name}_backups"


# --- Automatic backup when the app starts ---

from bloodtracker.app import create_app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


def test_new_database_is_not_backed_up_at_startup(client, backup_dir):
    assert not list(backup_dir.glob("*.db"))  # The client fixture created a brand-new database


def test_existing_database_is_backed_up_at_startup(client, db_path, backup_dir, ferritin):
    add(client, ferritin)
    create_app(db_path, backup_dir)  # The app starts again
    [backup] = backup_dir.glob("*_startup.db")
    assert connect(backup).execute("SELECT count(*) FROM results").fetchone()[0] == 1


def test_failed_startup_backup_still_starts_app_and_warns(db_path, tmp_path):
    create_app(db_path, tmp_path / "backups")  # Create the database
    blocked = tmp_path / "not-a-folder"
    blocked.write_text("a file where the backup folder should be")
    app = create_app(db_path, blocked)
    page = TestClient(app, base_url="http://127.0.0.1").get("/data").text
    assert "automatic backup when the app started failed" in page


def test_backups_list_shows_their_type(client, backup_dir):
    client.post("/backups")
    assert "<td>Manual</td>" in client.get("/data").text
