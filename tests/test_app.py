from fastapi.testclient import TestClient

from bloodtracker.app import create_app


def test_index_page_loads():
    client = TestClient(create_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "BloodTestTracker" in response.text
