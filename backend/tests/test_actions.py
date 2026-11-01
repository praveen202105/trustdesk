from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from trustdesk import actions, mock_actions
from trustdesk.actions import decide, execute, propose
from trustdesk.config import settings
from trustdesk.jobs import claim, complete, enqueue, run_once
from trustdesk.knowledge import index_knowledge
from trustdesk.models import Approval, Artifact, Job, MockEffect, Proposal, Ticket, now


@pytest.fixture
def ready(database, monkeypatch):
    monkeypatch.setattr(mock_actions, "SessionLocal", database)
    remote = TestClient(mock_actions.app)

    def send(arguments):
        response = remote.post(
            "/internal/refund-reviews",
            json=arguments,
            headers={
                "X-Action-Secret": settings.mock_action_secret,
                "Idempotency-Key": arguments["idempotency_key"],
            },
        )
        response.raise_for_status()
        return response.json()

    monkeypatch.setattr(actions, "execute_remote", send)
    with database.begin() as session:
        index_knowledge(session)
        enqueue(session, "triage", "tkt_9008")
    run_once(database)
    with database.begin() as session:
        enqueue(session, "draft", "tkt_9008")
    run_once(database)
    with database.begin() as session:
        draft = session.scalar(select(Artifact).where(Artifact.kind == "draft"))
        proposal = propose(session, "tkt_9008", draft.id)
    return proposal["proposal_id"]


def test_approval_and_rejection_guard(database, ready):
    with pytest.raises(HTTPException):
        execute({"payload": {"proposal_id": ready}}, database)
    with database.begin() as session:
        decide(session, ready, "rejected", "Not approved", "demo-agent")
    with pytest.raises(HTTPException):
        execute({"payload": {"proposal_id": ready}}, database)
    with database() as session:
        assert session.scalar(select(func.count()).select_from(MockEffect)) == 0


def test_crash_after_external_success_replays_same_effect(database, ready):
    with database.begin() as session:
        response = decide(session, ready, "approved", "Reviewed", "demo-agent")
        job_id = response["execution_job_id"]
    first = claim(database)
    outcome = execute(first, database)  # Simulated crash: do not commit the Completion.
    with database.begin() as session:
        session.get(Job, job_id).lease_until = now() - timedelta(seconds=1)
    assert run_once(database)
    assert not complete(first, outcome, database)
    with database() as session:
        assert session.scalar(select(func.count()).select_from(MockEffect)) == 1
        assert session.get(Proposal, ready).state == "succeeded"
        assert session.get(Job, job_id).status == "succeeded"
        assert session.get(Proposal, ready).result["money_refunded"] is False


def test_concurrent_opposing_decisions(database, ready):
    def choose(value):
        try:
            with database.begin() as session:
                return decide(session, ready, value, "Reviewed", "demo-agent")["state"]
        except HTTPException as exc:
            return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(choose, ["approved", "rejected"]))
    assert 409 in result
    with database() as session:
        assert session.scalar(select(func.count()).select_from(Approval)) == 1


def test_changed_context_blocks_execution(database, ready):
    with database.begin() as session:
        decide(session, ready, "approved", "Reviewed", "demo-agent")
        ticket = session.get(Ticket, "tkt_9008")
        ticket.data = {**ticket.data, "body": "Changed after approval"}
    run_once(database)
    with database() as session:
        assert session.get(Proposal, ready).state == "blocked"
        assert session.scalar(select(func.count()).select_from(MockEffect)) == 0


def test_api_idempotency_and_forged_actor_are_rejected(database, ready, monkeypatch):
    from trustdesk import api
    from trustdesk.main import app

    monkeypatch.setattr(api, "SessionLocal", database)
    api.login_attempts.clear()
    with TestClient(app) as client:
        client.headers["Origin"] = settings.app_origin
        client.post("/api/v1/auth/session", json={"token": settings.demo_login_token})
        url = f"/api/v1/action-proposals/{ready}/decision"
        body = {"decision": "approved", "reason": "Reviewed"}
        assert (
            client.post(
                url, json={**body, "actor": "model"}, headers={"Idempotency-Key": "forged"}
            ).status_code
            == 422
        )
        headers = {"Idempotency-Key": "same-decision"}
        first = client.post(url, json=body, headers=headers)
        second = client.post(url, json=body, headers=headers)
        assert first.status_code == second.status_code == 200
        assert first.json()["execution_job_id"] == second.json()["execution_job_id"]
        conflict = client.post(url, json={**body, "decision": "rejected"}, headers=headers)
        assert conflict.status_code == 409
        assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    with database() as session:
        assert session.scalar(select(func.count()).select_from(Approval)) == 1
        assert session.scalar(select(func.count()).select_from(Job).where(Job.kind == "execute_action")) == 1


def test_stale_worker_failure_cannot_poison_new_owner(database, ready, monkeypatch):
    import httpx

    original = actions.execute_remote
    with database.begin() as session:
        response = decide(session, ready, "approved", "Reviewed", "demo-agent")
        job_id = response["execution_job_id"]
    old = claim(database)

    def late_failure(arguments):
        with database.begin() as session:
            session.get(Job, job_id).owner = "newer-worker"
        raise httpx.HTTPStatusError(
            "expired worker credentials",
            request=httpx.Request("POST", "http://mock-actions/internal/refund-reviews"),
            response=httpx.Response(401),
        )

    monkeypatch.setattr(actions, "execute_remote", late_failure)
    with pytest.raises(HTTPException):
        execute(old, database)
    with database.begin() as session:
        assert session.get(Proposal, ready).state == "executing"
        session.get(Job, job_id).lease_until = now() - timedelta(seconds=1)
    monkeypatch.setattr(actions, "execute_remote", original)
    run_once(database)
    with database() as session:
        assert session.get(Proposal, ready).state == "succeeded"
        assert session.scalar(select(func.count()).select_from(MockEffect)) == 1
