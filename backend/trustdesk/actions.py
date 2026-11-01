from typing import Literal

import httpx
from fastapi import HTTPException
from sqlalchemy import select

from .config import settings
from .ingest import checksum
from .jobs import Completion, TransientError, advisory, enqueue
from .models import (
    Approval,
    Artifact,
    Customer,
    Document,
    Order,
    Proposal,
    Ticket,
    ToolCall,
    ToolDefinition,
    Trace,
    uid,
)
from .policy import action_arguments, context_for, context_hash, decision


def proposal_json(proposal: Proposal) -> dict:
    return {"proposal_id": proposal.id, "ticket_id": proposal.ticket_id, "action_type": proposal.action_type,
            "arguments": proposal.arguments, "arguments_hash": proposal.arguments_hash, "state": proposal.state,
            "evidence_document_ids": proposal.evidence_document_ids,
            "execution_job_id": proposal.execution_job_id, "result": proposal.result}


def validate_catalog(session, arguments: dict, category: str):
    catalog = session.get(ToolDefinition, "start_refund_review")
    if (not catalog or category not in catalog.data["allowed_categories"] or
            not catalog.data["requires_human_approval"] or
            any(field not in arguments for field in catalog.data["required_fields"])):
        raise HTTPException(403, "ACTION_NOT_ALLOWED")


def propose(session, ticket_id: str, draft_id: str) -> dict:
    draft = session.get(Artifact, draft_id)
    if not draft or draft.ticket_id != ticket_id or draft.kind != "draft":
        raise HTTPException(404, "RESOURCE_NOT_FOUND")
    context = context_for(session, ticket_id)
    digest = context_hash(context)
    if draft.context_hash != digest:
        raise HTTPException(409, "STALE_CONTEXT")
    rules = decision(context)
    arguments = action_arguments(context, rules)
    if (not arguments or draft.data["status"] != "ready_for_review" or
            "start_refund_review" not in draft.data["recommended_actions"]):
        raise HTTPException(422, "EVIDENCE_INSUFFICIENT")
    advisory(session, "refund-review:" + ticket_id + ":" + arguments["order_id"])
    existing = session.scalar(select(Proposal).where(Proposal.ticket_id == ticket_id,
                               Proposal.order_id == arguments["order_id"],
                               Proposal.state.in_(["proposed", "approved", "executing", "succeeded"])))
    if existing:
        if existing.draft_id == draft_id:
            return proposal_json(existing)
        raise HTTPException(409, "DUPLICATE_ACTION")
    if session.scalar(select(Proposal).where(Proposal.draft_id == draft_id)):
        raise HTTPException(409, "INVALID_STATE")
    proposal_id = uid()
    arguments["idempotency_key"] = "refund-review:" + proposal_id
    validate_catalog(session, arguments, rules["category"])
    proposal = Proposal(id=proposal_id, ticket_id=ticket_id, order_id=arguments["order_id"], draft_id=draft_id,
                        arguments=arguments, arguments_hash=checksum(arguments), context_hash=digest,
                        evidence_document_ids=[rules["policy_document"]])
    session.add(proposal)
    session.flush()
    return proposal_json(proposal)


def decide(session, proposal_id: str, value: Literal["approved", "rejected"], reason: str, actor: str) -> dict:
    proposal = session.scalar(select(Proposal).where(Proposal.id == proposal_id).with_for_update())
    if not proposal:
        raise HTTPException(404, "RESOURCE_NOT_FOUND")
    prior = session.scalar(select(Approval).where(Approval.proposal_id == proposal.id))
    if prior:
        if prior.decision != value:
            raise HTTPException(409, "DECISION_CONFLICT")
        return proposal_json(proposal)
    if proposal.state != "proposed":
        raise HTTPException(409, "INVALID_STATE")
    if context_hash(context_for(session, proposal.ticket_id)) != proposal.context_hash:
        raise HTTPException(409, "STALE_CONTEXT")
    session.add(Approval(proposal_id=proposal.id, actor=actor, decision=value, reason=reason,
                         arguments_hash=proposal.arguments_hash))
    proposal.state = value
    if value == "approved":
        submitted = enqueue(session, "execute_action", proposal.ticket_id, {"proposal_id": proposal.id})
        proposal.execution_job_id = submitted["job_id"]
        session.add(ToolCall(id=proposal.arguments["idempotency_key"], proposal_id=proposal.id))
    session.flush()
    return proposal_json(proposal)


def execute_remote(arguments: dict) -> dict:
    try:
        response = httpx.post(settings.mock_action_base_url.rstrip("/") + "/internal/refund-reviews",
                              headers={"X-Action-Secret": settings.mock_action_secret,
                                       "Idempotency-Key": arguments["idempotency_key"]}, json=arguments, timeout=10)
        if response.status_code == 429 or response.status_code >= 500:
            raise TransientError("Mock action service temporarily unavailable")
        response.raise_for_status()
        data = response.json()
        if not isinstance(data.get("external_review_id"), str):
            raise ValueError("Invalid action response")
        return data
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        raise TransientError("Action outcome unknown; reconcile using original key") from exc


def execute(job, factory) -> Completion:
    proposal_id = job["payload"]["proposal_id"]
    try:
        with factory.begin() as session:
            proposal = session.scalar(select(Proposal).where(Proposal.id == proposal_id).with_for_update())
            if not proposal or proposal.state not in ("approved", "executing", "succeeded"):
                raise HTTPException(403, "APPROVAL_REQUIRED")
            approval = session.scalar(select(Approval).where(Approval.proposal_id == proposal_id))
            if (not approval or approval.decision != "approved" or
                    approval.arguments_hash != proposal.arguments_hash or checksum(proposal.arguments) != proposal.arguments_hash):
                raise HTTPException(403, "APPROVAL_REQUIRED")
            if proposal.state == "succeeded":
                return Completion(proposal.result or {})
            proposal.state = "executing"
            call = session.get(ToolCall, proposal.arguments["idempotency_key"])
            call.attempts += 1
            call.status = "executing"
        with factory.begin() as session:
            proposal = session.scalar(select(Proposal).where(Proposal.id == proposal_id).with_for_update())
            # Hold source-row read locks over the external call so imports cannot race policy revalidation.
            session.scalars(select(Ticket).where(Ticket.id == proposal.ticket_id).with_for_update(read=True)).all()
            session.scalars(select(Order).where(Order.id == proposal.order_id).with_for_update(read=True)).all()
            session.scalars(select(Customer).where(Customer.id == session.get(Ticket, proposal.ticket_id).customer_id)
                            .with_for_update(read=True)).all()
            session.scalars(select(Document).with_for_update(read=True)).all()
            context = context_for(session, proposal.ticket_id)
            if context_hash(context) != proposal.context_hash:
                raise HTTPException(409, "STALE_CONTEXT")
            arguments = action_arguments(context, decision(context))
            if not arguments or any(proposal.arguments.get(key) != val for key, val in arguments.items()):
                raise HTTPException(422, "EVIDENCE_INSUFFICIENT")
            validate_catalog(session, proposal.arguments, decision(context)["category"])
            result = execute_remote(proposal.arguments)
    except HTTPException:
        with factory.begin() as session:
            proposal = session.get(Proposal, proposal_id)
            if proposal and proposal.state in ("approved", "executing"):
                proposal.state = "blocked"
        raise
    except httpx.HTTPStatusError:
        with factory.begin() as session:
            proposal = session.get(Proposal, proposal_id)
            proposal.state = "failed"
        raise HTTPException(502, "TOOL_EXECUTION_FAILED") from None
    def persist(session):
        proposal = session.get(Proposal, proposal_id)
        proposal.state, proposal.result = "succeeded", result
        call = session.get(ToolCall, proposal.arguments["idempotency_key"])
        call.status, call.result = "succeeded", result
        session.add(Trace(ticket_id=proposal.ticket_id, run_type="tool_execution", data={
            "retrieved_doc_ids": proposal.evidence_document_ids,
            "tool_calls": [{"tool_name": "start_refund_review", "proposal_id": proposal.id, "result": result}],
            "guardrail_results": ["approval_verified", "policy_revalidated", "idempotency_enforced"], "final_status": "succeeded"}))
    return Completion(result, persist)
