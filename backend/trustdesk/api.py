import base64
import hmac
import time
from collections import defaultdict
from typing import Any

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
    response.set_cookie("trustdesk_session", serializer.dumps({"actor": "demo-agent"}), max_age=28800,
                        httponly=True, secure=settings.secure_cookies, samesite="strict", path="/")


@router.delete("/auth/session", status_code=204)
def logout(response: Response):
    response.delete_cookie("trustdesk_session", path="/")


def latest(session, ticket_id: str, kind: str) -> dict[str, Any] | None:
    row = session.scalar(select(Artifact).where(Artifact.ticket_id == ticket_id, Artifact.kind == kind)
                         .order_by(Artifact.created_at.desc(), Artifact.id.desc()).limit(1))
    return {"id": row.id, **row.data, "context_hash": row.context_hash} if row else None


def get_ticket(session, ticket_id: str) -> Ticket:
    row = session.get(Ticket, ticket_id)
    if not row:
        raise HTTPException(404, "RESOURCE_NOT_FOUND")
    return row


@router.get("/tickets")
def tickets(limit: int = Query(default=25, ge=1, le=100), cursor: str | None = None,
            category: str | None = None, priority: str | None = None, escalation: bool | None = None):
    after = ""
    if cursor:
        try:
            after = base64.urlsafe_b64decode(cursor.encode()).decode()
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
            items.append({**row.data, "customer_name": customer.data["name"] if customer else "Unknown",
                          "triage": triage})
        page = items[:limit]
        next_cursor = base64.urlsafe_b64encode(page[-1]["ticket_id"].encode()).decode() if len(items) > limit else None
        return {"items": page, "next_cursor": next_cursor, "mode": settings.ai_provider}


@router.get("/tickets/{ticket_id}")
def ticket_detail(ticket_id: str):
    with SessionLocal() as session:
        ticket = get_ticket(session, ticket_id)
        customer = session.get(Customer, ticket.customer_id)
        order = session.get(Order, ticket.order_id) if ticket.order_id else None
        if order and order.customer_id != ticket.customer_id:
            raise HTTPException(403, "CONTEXT_OWNERSHIP_MISMATCH")
        return {"ticket": ticket.data,
                "customer": {k: v for k, v in customer.data.items() if k in
                             ("customer_id", "name", "tier", "country", "verified")} if customer else None,
                "order": order.data if order else None,
                "triage": latest(session, ticket_id, "triage"),
                "draft": latest(session, ticket_id, "draft"),
                "warnings": [] if order else ["Order context is unavailable"]}


@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    from .models import Job
    with SessionLocal() as session:
        job = session.get(Job, job_id)
        if not job:
            raise HTTPException(404, "RESOURCE_NOT_FOUND")
        return {"job_id": job.id, "status": job.status, "result": job.result,
                "error": job.error, "attempts": job.attempts}
