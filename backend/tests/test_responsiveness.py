import threading
import time
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from trustdesk import api, providers
from trustdesk.config import settings
from trustdesk.jobs import run_once
from trustdesk.knowledge import index_knowledge
from trustdesk.main import app


def test_ticket_reads_do_not_wait_for_blocked_provider(database, monkeypatch):
    with database.begin() as session:
        index_knowledge(session)
    monkeypatch.setattr(api, "SessionLocal", database)
    api.login_attempts.clear()
    entered, release = threading.Event(), threading.Event()
    original = providers.MockProvider.generate

    def blocked(self, context):
        entered.set()
        assert release.wait(10)
        return original(self, context)

    monkeypatch.setattr(providers.MockProvider, "generate", blocked)
    with TestClient(app) as client:
        client.headers["Origin"] = settings.app_origin
        client.post("/api/v1/auth/session", json={"token": settings.demo_login_token})
        response = client.post(
            "/api/v1/tickets/tkt_9008/triage", json={}, headers={"Idempotency-Key": "slow-provider-test"}
        )
        assert response.status_code == 202
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(run_once, database)
            try:
                assert entered.wait(5)
                started = time.monotonic()
                assert client.get("/api/v1/tickets").status_code == 200
                assert time.monotonic() - started < 2
            finally:
                release.set()
            assert future.result(timeout=5)
