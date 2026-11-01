import copy
from datetime import datetime

from sqlalchemy import select

from trustdesk.ingest import checksum
from trustdesk.jobs import enqueue, run_once
from trustdesk.knowledge import index_knowledge
from trustdesk.models import Artifact, Job, Ticket
from trustdesk.pipeline import analyze
from trustdesk.policy import action_arguments, context_for, decision, return_eligible


def test_billing_pipeline_and_trace(database):
    with database.begin() as session:
        index_knowledge(session)
        triage = enqueue(session, "triage", "tkt_9008")["job_id"]
    assert run_once(database)
    with database.begin() as session:
        assert session.get(Job, triage).result["category"] == "billing"
        draft = enqueue(session, "draft", "tkt_9008")["job_id"]
    assert run_once(database)
    with database() as session:
        result = session.get(Job, draft).result
        assert result["status"] == "ready_for_review"
        assert "KB-BILLING-001" in {x["document_id"] for x in result["citations"]}
        assert "start_refund_review" in result["recommended_actions"]
        assert session.scalar(select(Artifact).where(Artifact.kind == "draft"))


def test_historical_window_and_final_sale(database):
    with database() as session:
        context = context_for(session, "tkt_9001")
        assert return_eligible(context)
        for day, expected in (("2026-07-01T23:59:00+05:30",True),("2026-07-02T00:00:00+05:30",False)):
            altered = copy.deepcopy(context)
            altered["ticket"]["created_at"] = day
            assert return_eligible(altered) is expected
        context = context_for(session, "tkt_9003")
        assert action_arguments(context, decision(context)) is None


def test_adversarial_and_safety_cases(database):
    with database.begin() as session:
        index_knowledge(session)
        for ticket_id in ("tkt_9004", "tkt_9005", "tkt_9006", "tkt_9007"):
            context = context_for(session, ticket_id)
            result, trace = analyze(context, "draft", session)
            assert result["escalation_required"]
            assert result["recommended_actions"] == ["escalate_to_human"]
            assert action_arguments(context, decision(context)) is None
            assert trace["guardrail_results"] != ["passed"]


def test_unseen_content_does_not_use_expected_labels(database):
    with database.begin() as session:
        row = session.get(Ticket, "tkt_9008")
        row.data = {**row.data, "subject":"Unrecognized request", "body":"Please explain an unsupported service."}
        row.checksum = checksum(row.data)
        row.created_at = datetime.fromisoformat(row.data["created_at"])
        assert decision(context_for(session, row.id))["escalation_required"]
