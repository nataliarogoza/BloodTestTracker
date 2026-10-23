""" Tests that go through the real web routes, like the browser does (temporary database) """
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
