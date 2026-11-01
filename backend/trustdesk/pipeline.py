import time
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict

from .config import settings
from .jobs import Completion
from .knowledge import retrieve, valid_citations
from .models import Artifact, Trace, uid
from .policy import context_for, context_hash, decision
from .privacy import redact
from .providers import provider


class TriageOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Literal["shipping", "refund", "warranty", "billing", "account_security", "general"]
    priority: Literal["low", "medium", "high", "urgent"]
    sentiment: str
    escalation_required: bool
    reason: str


def analyze(context: dict, kind: str, session) -> tuple[dict, dict]:
    started = time.monotonic()
    rules = decision(context)
    query = rules["category"] + " " + context["ticket"]["subject"] + " " + context["ticket"]["body"]
    results = retrieve(session, query)
    matching = [item for item in results if item["document_id"] == rules["policy_document"]]
    guards = list(rules["guardrails"])
    if not matching:
        rules.update(
            escalation_required=True,
            recommended_actions=["escalate_to_human"],
            reason="Required evidence was not retrieved",
            safe_template="A support specialist must review this request because policy evidence is insufficient.",
        )
        guards.append("evidence_insufficient")
    triage = TriageOutput.model_validate({key: rules[key] for key in TriageOutput.model_fields}).model_dump()
    usage = None
    if kind == "triage":
        response = provider().generate(
            {
                "task": "triage",
                "ticket": context["ticket"],
                "customer": context["customer"],
                "order": context["order"],
                "evidence": results,
                "safe_template": rules["reason"],
                **({"mock_triage": triage} if settings.ai_provider == "mock" else {}),
            }
        )
        result = TriageOutput.model_validate(response.get("triage")).model_dump()
        result["reason"] = redact(result["reason"])
        usage = response.get("usage")
        if guards or triage["escalation_required"]:
            result = triage
        elif result["category"] != triage["category"]:
            result.update(
                escalation_required=True, reason="Model classification conflicts with policy checks"
            )
            rules.update(escalation_required=True, recommended_actions=["escalate_to_human"])
            guards.append("classification_conflict")
        priorities = ["low", "medium", "high", "urgent"]
        if priorities.index(result["priority"]) < priorities.index(triage["priority"]):
            result["priority"] = triage["priority"]
        rules["escalation_required"] = result["escalation_required"]
        if result["escalation_required"]:
            rules["recommended_actions"] = ["escalate_to_human"]
    else:
        response = provider().generate(
            {
                "task": "draft",
                "ticket": context["ticket"],
                "customer": context["customer"],
                "order": context["order"],
                "evidence": matching,
                "safe_template": rules["safe_template"],
            }
        )
        usage = response.get("usage")
        # V1 permits only reviewed policy templates. Live-provider paraphrases need a separate grounding review.
        if response.get("text") != rules["safe_template"]:
            guards.append("unreviewed_model_claims_blocked")
            rules.update(escalation_required=True, recommended_actions=["escalate_to_human"])
        citations = [{**item, "claim": rules["reason"]} for item in matching]
        for item in citations:
            item.pop("score", None)
        if not valid_citations(session, citations, results):
            raise HTTPException(422, "INVALID_CITATIONS")
        result = {
            "text": rules["safe_template"],
            "citations": citations,
            "status": "escalated" if rules["escalation_required"] else "ready_for_review",
            "escalation_required": rules["escalation_required"],
            "recommended_actions": rules["recommended_actions"],
        }
    trace = {
        "retrieved_doc_ids": list(dict.fromkeys(item["document_id"] for item in results)),
        "tool_calls": [],
        "recommended_actions": rules["recommended_actions"],
        "guardrail_results": guards or ["passed"],
        "final_status": "escalated" if rules["escalation_required"] else "succeeded",
        "model_provider": settings.ai_provider,
        "model_name": settings.ai_model,
        "triage_engine": "deterministic_mock" if settings.ai_provider == "mock" else "llm_with_policy_checks",
        "prompt_version": "reviewed-template-v1",
        "latency_ms": round((time.monotonic() - started) * 1000),
        "token_usage": usage,
    }
    return result, trace


def dispatch(job, factory):
    if job["kind"] in ("evaluation", "eval_case"):
        from .evaluation import evaluation_job

        return evaluation_job(job, factory)
    if job["kind"] == "execute_action":
        from .actions import execute

        return execute(job, factory)
    if job["kind"] not in ("triage", "draft"):
        raise ValueError("Unsupported job type")
    with factory() as session:
        context = context_for(session, job["ticket_id"])
        digest = context_hash(context)
        prior_triage = None
        if job["kind"] == "draft":
            from sqlalchemy import select

            prior_triage = session.scalar(
                select(Artifact)
                .where(Artifact.ticket_id == job["ticket_id"], Artifact.kind == "triage")
                .order_by(Artifact.created_at.desc())
                .limit(1)
            )
            if not prior_triage or prior_triage.context_hash != digest:
                raise HTTPException(409, "TRIAGE_REQUIRED")
        result, trace = analyze(context, job["kind"], session)
        if prior_triage and prior_triage.data["escalation_required"]:
            result.update(
                status="escalated", escalation_required=True, recommended_actions=["escalate_to_human"]
            )
            trace["final_status"] = "escalated"
    artifact_id, trace_id = uid(), uid()

    def persist(session):
        if context_hash(context_for(session, job["ticket_id"])) != digest:
            raise HTTPException(409, "STALE_CONTEXT")
        session.add(
            Artifact(
                id=artifact_id, ticket_id=job["ticket_id"], kind=job["kind"], data=result, context_hash=digest
            )
        )
        session.add(Trace(id=trace_id, ticket_id=job["ticket_id"], run_type=job["kind"], data=trace))

    return Completion({"artifact_id": artifact_id, "ai_run_id": trace_id, **result}, persist)
