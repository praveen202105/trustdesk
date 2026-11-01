import base64
import hmac
import time
from collections import defaultdict
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from .config import settings
from .db import SessionLocal
from .models import Artifact, Customer, Order, Ticket

router = APIRouter(prefix="/api/v1")
serializer = URLSafeTimedSerializer(settings.session_secret)
login_attempts: dict[str, list[float]] = defaultdict(list)


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginBody(StrictBody):
    token: str = Field(max_length=256)


def actor(request: Request) -> str:
    try:
        value = serializer.loads(request.cookies.get("trustdesk_session", ""), max_age=28800)
        if value.get("actor") != "demo-agent":
            raise BadSignature("Invalid actor")
        return value["actor"]
    except (BadSignature, SignatureExpired):
        raise HTTPException(401, "SESSION_REQUIRED") from None


@router.post("/auth/session", status_code=204)
def login(body: LoginBody, request: Request, response: Response):
    host = request.client.host if request.client else "unknown"
    cutoff = time.monotonic() - 60
    attempts = [x for x in login_attempts[host] if x > cutoff]
    login_attempts[host] = attempts
    if len(attempts) >= 10:
        raise HTTPException(429, "RATE_LIMITED", headers={"Retry-After": "60"})
    attempts.append(time.monotonic())
    if not hmac.compare_digest(body.token, settings.demo_login_token):
        raise HTTPException(401, "INVALID_TOKEN")
    response.set_cookie(
        "trustdesk_session",
        serializer.dumps({"actor": "demo-agent"}),
        max_age=28800,
        httponly=True,
        secure=settings.secure_cookies,
        samesite="strict",
        path="/",
    )


@router.delete("/auth/session", status_code=204)
def logout(response: Response):
    response.delete_cookie("trustdesk_session", path="/")


def latest(session, ticket_id: str, kind: str) -> dict[str, Any] | None:
    row = session.scalar(
        select(Artifact)
        .where(Artifact.ticket_id == ticket_id, Artifact.kind == kind)
        .order_by(Artifact.created_at.desc(), Artifact.id.desc())
        .limit(1)
    )
    return {"id": row.id, **row.data, "context_hash": row.context_hash} if row else None


def get_ticket(session, ticket_id: str) -> Ticket:
    row = session.get(Ticket, ticket_id)
    if not row:
        raise HTTPException(404, "RESOURCE_NOT_FOUND")
    return row


@router.get("/tickets")
def tickets(
    limit: int = Query(default=25, ge=1, le=100),
    cursor: str | None = None,
    category: str | None = None,
    priority: str | None = None,
    escalation: bool | None = None,
):
    after = ""
    if cursor:
        try:
            after = base64.b64decode(cursor.encode(), altchars=b"-_", validate=True).decode()
            if not after:
                raise ValueError("Empty cursor")
        except Exception:
            raise HTTPException(422, "INVALID_CURSOR") from None
    with SessionLocal() as session:
        rows = session.scalars(select(Ticket).where(Ticket.id > after).order_by(Ticket.id)).all()
        items = []
        for row in rows:
            triage = latest(session, row.id, "triage")
            if category and (not triage or triage["category"] != category):
                continue
            if priority and (not triage or triage["priority"] != priority):
                continue
            if escalation is not None and (not triage or triage["escalation_required"] != escalation):
                continue
            customer = session.get(Customer, row.customer_id)
            items.append(
                {
                    **row.data,
                    "customer_name": customer.data["name"] if customer else "Unknown",
                    "triage": triage,
                }
            )
        page = items[:limit]
        next_cursor = (
            base64.urlsafe_b64encode(page[-1]["ticket_id"].encode()).decode() if len(items) > limit else None
        )
        return {"items": page, "next_cursor": next_cursor, "mode": settings.ai_provider}


@router.get("/tickets/{ticket_id}")
def ticket_detail(ticket_id: str):
    with SessionLocal() as session:
        ticket = get_ticket(session, ticket_id)
        customer = session.get(Customer, ticket.customer_id)
        order = session.get(Order, ticket.order_id) if ticket.order_id else None
        if order and order.customer_id != ticket.customer_id:
            raise HTTPException(403, "CONTEXT_OWNERSHIP_MISMATCH")
        return {
            "ticket": ticket.data,
            "customer": {
                k: v
                for k, v in customer.data.items()
                if k in ("customer_id", "name", "tier", "country", "verified")
            }
            if customer
            else None,
            "order": order.data if order else None,
            "triage": latest(session, ticket_id, "triage"),
            "draft": latest(session, ticket_id, "draft"),
            "warnings": [] if order else ["Order context is unavailable"],
        }


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    from .models import Job

    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(404, "RESOURCE_NOT_FOUND")
        return {
            "job_id": job.id,
            "status": job.status,
            "result": job.result,
            "error": job.error,
            "attempts": job.attempts,
        }


@router.get("/knowledge/search")
def knowledge_search(query: str = Query(min_length=1, max_length=2000)):
    from .knowledge import retrieve

    with SessionLocal() as session:
        return {"query": query, "results": retrieve(session, query)}


@router.get("/knowledge/documents/{document_id}")
def knowledge_document(document_id: str, version_hash: str | None = None):
    from .models import Document, DocumentVersion

    with SessionLocal() as session:
        doc = session.get(Document, document_id)
        if not doc:
            raise HTTPException(404, "RESOURCE_NOT_FOUND")
        version = version_hash or doc.checksum
        saved = session.get(DocumentVersion, document_id + ":" + version)
        if not saved:
            raise HTTPException(404, "RESOURCE_NOT_FOUND")
        return {
            "document_id": doc.id,
            "title": saved.title,
            "content": saved.content,
            "version_hash": version,
            "trusted_policy": doc.trusted_policy,
        }


class EmptyBody(StrictBody):
    pass


@router.post("/tickets/{ticket_id}/triage")
def submit_triage(ticket_id: str, body: EmptyBody, request: Request):
    from .jobs import enqueue, mutate

    def operation(session):
        get_ticket(session, ticket_id)
        return enqueue(session, "triage", ticket_id)

    return mutate(request, body.model_dump(), operation, factory=SessionLocal)


@router.post("/tickets/{ticket_id}/drafts")
def submit_draft(ticket_id: str, body: EmptyBody, request: Request):
    from .jobs import enqueue, mutate

    def operation(session):
        get_ticket(session, ticket_id)
        if not latest(session, ticket_id, "triage"):
            raise HTTPException(409, "TRIAGE_REQUIRED")
        return enqueue(session, "draft", ticket_id)

    return mutate(request, body.model_dump(), operation, factory=SessionLocal)


@router.get("/tickets/{ticket_id}/drafts")
def list_drafts(ticket_id: str):
    with SessionLocal() as session:
        get_ticket(session, ticket_id)
        rows = session.scalars(
            select(Artifact)
            .where(Artifact.ticket_id == ticket_id, Artifact.kind == "draft")
            .order_by(Artifact.created_at.desc())
            .limit(100)
        ).all()
        return {"items": [{"id": row.id, **row.data} for row in rows]}


@router.get("/tickets/{ticket_id}/traces")
def traces(ticket_id: str):
    from .models import Trace

    with SessionLocal() as session:
        get_ticket(session, ticket_id)
        rows = session.scalars(
            select(Trace).where(Trace.ticket_id == ticket_id).order_by(Trace.created_at.desc()).limit(100)
        ).all()
        return {"items": [{"id": row.id, "run_type": row.run_type, **row.data} for row in rows]}


class ProposalBody(StrictBody):
    draft_id: str


class DecisionBody(StrictBody):
    decision: Literal["approved", "rejected"]
    reason: str = Field(min_length=1, max_length=1000)


@router.post("/tickets/{ticket_id}/action-proposals")
def create_proposal(ticket_id: str, body: ProposalBody, request: Request):
    from .actions import propose
    from .jobs import mutate

    return mutate(
        request,
        body.model_dump(),
        lambda session: propose(session, ticket_id, body.draft_id),
        status=201,
        factory=SessionLocal,
    )


@router.get("/tickets/{ticket_id}/action-proposals")
def ticket_proposals(ticket_id: str):
    from .actions import proposal_json
    from .models import Proposal

    with SessionLocal() as session:
        get_ticket(session, ticket_id)
        rows = session.scalars(
            select(Proposal)
            .where(Proposal.ticket_id == ticket_id)
            .order_by(Proposal.created_at.desc())
            .limit(100)
        ).all()
        return {"items": [proposal_json(row) for row in rows]}


@router.get("/action-proposals/{proposal_id}")
def get_proposal(proposal_id: str):
    from .actions import proposal_json
    from .models import Proposal

    with SessionLocal() as session:
        row = session.get(Proposal, proposal_id)
        if not row:
            raise HTTPException(404, "RESOURCE_NOT_FOUND")
        return proposal_json(row)


@router.post("/action-proposals/{proposal_id}/decision")
def decision_proposal(proposal_id: str, body: DecisionBody, request: Request):
    from .actions import decide
    from .jobs import mutate

    return mutate(
        request,
        body.model_dump(),
        lambda session: decide(session, proposal_id, body.decision, body.reason, request.state.actor),
        status=200,
        factory=SessionLocal,
    )


class EvaluationBody(StrictBody):
    suite: Literal["provided"] = "provided"


@router.post("/evaluations")
def submit_evaluation(body: EvaluationBody, request: Request):
    from .jobs import enqueue, mutate
    from .models import EvaluationRun, uid

    def operation(session):
        from .jobs import advisory

        advisory(session, "source-import")
        evaluation_id = uid()
        submitted = enqueue(session, "evaluation", payload={"evaluation_id": evaluation_id})
        session.add(EvaluationRun(id=evaluation_id, job_id=submitted["job_id"]))
        return {"evaluation_id": evaluation_id, **submitted}

    return mutate(request, body.model_dump(), operation, factory=SessionLocal)


@router.get("/evaluations/{evaluation_id}")
def get_evaluation(evaluation_id: str):
    from .models import EvaluationRun, Job

    with SessionLocal() as session:
        row = session.get(EvaluationRun, evaluation_id)
        if not row:
            raise HTTPException(404, "RESOURCE_NOT_FOUND")
        parent = session.get(Job, row.job_id) if row.job_id else None
        return {
            "evaluation_id": row.id,
            "status": "failed" if parent and parent.status == "failed" else row.status,
            "error": parent.error if parent else None,
            **row.data,
        }
