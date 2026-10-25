def test_index_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "BloodTestTracker" in response.text


def test_app_creates_database_on_startup(client, db_path):
    assert db_path.exists()
