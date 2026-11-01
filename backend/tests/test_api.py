import pytest
from fastapi.testclient import TestClient

from trustdesk import api
from trustdesk.config import settings
from trustdesk.main import app


@pytest.fixture
def client(database, monkeypatch):
    monkeypatch.setattr(api, "SessionLocal", database)
    api.login_attempts.clear()
    with TestClient(app) as client:
        client.headers["Origin"] = settings.app_origin
        yield client


def sign_in(client):
    assert client.post("/api/v1/auth/session", json={"token": settings.demo_login_token}).status_code == 204


def test_auth_and_context(client):
    assert client.get("/api/v1/tickets").status_code == 401
    assert client.post("/api/v1/auth/session", json={"token": "wrong"}).status_code == 401
    sign_in(client)
    response = client.get("/api/v1/tickets")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 8
    assert "expected_category" not in response.text
    detail = client.get("/api/v1/tickets/tkt_9008").json()
    assert detail["order"]["customer_id"] == detail["ticket"]["customer_id"]
    assert "email" not in detail["customer"]
    assert client.get("/api/v1/tickets/missing").status_code == 404
    assert client.get("/api/v1/tickets?limit=0").status_code == 422
    assert client.delete("/api/v1/auth/session").status_code == 204
    assert client.get("/api/v1/tickets").status_code == 401


def test_origin_cookie_and_pagination(client):
    sign_in(client)
    assert client.cookies.get("trustdesk_session")
    response = client.get("/api/v1/tickets?limit=3").json()
    next_page = client.get("/api/v1/tickets", params={"cursor": response["next_cursor"], "limit": 3}).json()
    assert not {x["ticket_id"] for x in response["items"]} & {x["ticket_id"] for x in next_page["items"]}
    client.headers["Origin"] = "https://evil.example"
    assert client.delete("/api/v1/auth/session").status_code == 403


def test_oversized_body_and_login_limit(client):
    assert client.post("/api/v1/auth/session", content="x" * (256 * 1024 + 1)).status_code == 413
    for _ in range(10):
        assert client.post("/api/v1/auth/session", json={"token": "wrong"}).status_code == 401
    assert client.post("/api/v1/auth/session", json={"token": "wrong"}).status_code == 429


def test_invalid_cursor_is_rejected(client):
    sign_in(client)
    assert client.get("/api/v1/tickets?cursor=!!!!").status_code == 422
