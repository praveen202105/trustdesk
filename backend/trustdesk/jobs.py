import hashlib
import threading
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, Callable

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import and_, or_, select, text, update

from .db import SessionLocal
from .ingest import checksum
from .models import Idempotency, Job, Trace, now, uid


class TransientError(Exception):
    pass


@dataclass
class Completion:
    result: dict[str, Any] = field(default_factory=dict)
    persist: Callable | None = None


def advisory(session, value: str):
    session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"),
        {"key": int(hashlib.sha256(value.encode()).hexdigest()[:15], 16)},
    )


def mutate(request: Request, body: dict, operation: Callable, status: int = 202, factory=SessionLocal):
    key = request.headers.get("Idempotency-Key", "")
    if not key or len(key) > 200:
        raise HTTPException(422, "IDEMPOTENCY_KEY_REQUIRED")
    scope = request.state.actor + ":" + request.url.path + ":" + key
    digest = checksum(body)
    with factory.begin() as session:
        advisory(session, scope)
        existing = session.get(Idempotency, scope)
        if existing:
            if existing.request_hash != digest:
                raise HTTPException(409, "IDEMPOTENCY_CONFLICT")
            return JSONResponse(existing.response, status_code=existing.status_code)
        response = operation(session)
        session.add(Idempotency(id=scope, request_hash=digest, response=response, status_code=status))
    return JSONResponse(response, status_code=status)


def enqueue(session, kind: str, ticket_id: str | None = None, payload: dict | None = None) -> dict:
    job = Job(id=uid(), kind=kind, ticket_id=ticket_id, payload=payload or {})
    session.add(job)
    session.flush()
    return {"job_id": job.id, "status": "queued"}


def claim(factory=SessionLocal) -> dict | None:
    with factory.begin() as session:
        job = session.scalar(
            select(Job)
            .where(
                or_(
                    and_(Job.status == "queued", Job.available_at <= now()),
                    and_(Job.status == "running", Job.lease_until < now()),
                )
            )
            .order_by(Job.available_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if not job:
            return None
        if job.attempts >= 3:
            job.status = "failed"
            job.error = {
                "code": "RETRY_EXHAUSTED",
                "message": "Manual reconciliation required for uncertain actions",
            }
            return None
        job.status, job.owner = "running", uid()
        job.lease_until = now() + timedelta(seconds=60)
        job.attempts += 1
        return {
            "id": job.id,
            "kind": job.kind,
            "ticket_id": job.ticket_id,
            "payload": job.payload,
            "owner": job.owner,
            "attempts": job.attempts,
        }


def heartbeat(job: dict, stop: threading.Event, factory):
    while not stop.wait(10):
        try:
            with factory.begin() as session:
                session.execute(
                    update(Job)
                    .where(Job.id == job["id"], Job.owner == job["owner"], Job.status == "running")
                    .values(lease_until=now() + timedelta(seconds=60))
                )
        except Exception:
            return  # Lost connectivity: final fencing check still prevents stale commits.


def complete(job: dict, outcome: Completion, factory=SessionLocal) -> bool:
    with factory.begin() as session:
        row = session.scalar(select(Job).where(Job.id == job["id"]).with_for_update())
        if not row or row.owner != job["owner"] or row.status != "running" or row.lease_until < now():
            return False
        if outcome.persist:
            outcome.persist(session)
        row.result, row.status, row.error = outcome.result, "succeeded", None
        row.lease_until = None
        return True


def run_once(factory=SessionLocal, handler: Callable | None = None) -> bool:
    job = claim(factory)
    if not job:
        return False
    stop = threading.Event()
    thread = threading.Thread(target=heartbeat, args=(job, stop, factory), daemon=True)
    thread.start()
    try:
        if handler is None:
            from .pipeline import dispatch

            handler = dispatch
        outcome = handler(job, factory)
        complete(job, outcome, factory)
    except Exception as exc:
        retryable = isinstance(exc, TransientError)
        with factory.begin() as session:
            row = session.scalar(select(Job).where(Job.id == job["id"]).with_for_update())
            if row and row.owner == job["owner"] and row.status == "running":
                row.status = "queued" if retryable and row.attempts < 3 else "failed"
                row.available_at = now() + timedelta(seconds=2**row.attempts)
                row.lease_until = None
                code = "PROVIDER_UNAVAILABLE" if retryable else "JOB_FAILED"
                if isinstance(exc, HTTPException):
                    code = str(exc.detail)
                row.error = {"code": code, "message": "Operation failed safely; inspect the run status"}
                if job["ticket_id"] and job["kind"] in ("triage", "draft"):
                    session.add(
                        Trace(
                            ticket_id=job["ticket_id"],
                            run_type=job["kind"],
                            data={
                                "job_id": job["id"],
                                "attempt": job["attempts"],
                                "retrieved_doc_ids": [],
                                "tool_calls": [],
                                "guardrail_results": ["failed_closed"],
                                "final_status": "failed",
                                "error_code": code,
                            },
                        )
                    )
    finally:
        stop.set()
        thread.join(timeout=2)
    return True
