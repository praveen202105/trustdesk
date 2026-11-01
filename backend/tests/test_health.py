from fastapi.testclient import TestClient

from trustdesk.main import app


def test_health():
    response = TestClient(app).get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["mode"] == "mock"
