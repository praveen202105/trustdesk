from datetime import timedelta

from sqlalchemy import func, select

from trustdesk.evaluation import aggregate, evaluate_sync
from trustdesk.jobs import enqueue, run_once
from trustdesk.knowledge import index_knowledge
from trustdesk.models import Artifact, EvaluationRun, Job, MockEffect, Proposal, now, uid


def test_supplied_evaluation_accounts_for_every_case_without_actions(database):
    with database.begin() as session:
        index_knowledge(session)
    report = evaluate_sync(database)
    assert report["total_cases"] == 8
    assert report["completed_cases"] == 8
    assert report["errored_cases"] == 0
    assert {case["case_id"] for case in report["cases"]} == {f"eval_{i:03}" for i in range(1, 9)}
    assert report["metrics"]["unsafe_action_block_rate"]["rate"] == 1
    with database() as session:
        for model in (MockEffect, Proposal, Artifact):
            assert session.scalar(select(func.count()).select_from(model)) == 0


def test_errors_are_not_silently_removed_from_metrics():
    sources = [
        {"case_id": "a", "expected": {"should_escalate": True}},
        {"case_id": "b", "expected": {"should_escalate": False}},
    ]
    report = aggregate([{"case_id": "a", "error": "failed", "checks": {}, "passed": False}], sources)
    assert report["metrics"]["category_accuracy"]["total"] == 2
    assert report["metrics"]["category_accuracy"]["rate"] == 0
    assert report["errored_cases"] == 2


def test_background_evaluation_uses_case_jobs_and_completes(database):
    with database.begin() as session:
        index_knowledge(session)
        evaluation_id = uid()
        submitted = enqueue(session, "evaluation", payload={"evaluation_id": evaluation_id})
        session.add(EvaluationRun(id=evaluation_id, job_id=submitted["job_id"]))
    for _ in range(30):
        run_once(database)
        with database.begin() as session:
            children_pending = session.scalar(
                select(Job.id).where(Job.kind == "eval_case", Job.status.in_(["queued", "running"])).limit(1)
            )
            if not children_pending:
                parent = session.get(Job, submitted["job_id"])
                if parent.status == "queued":
                    parent.available_at = now() - timedelta(seconds=1)
            evaluation = session.get(EvaluationRun, evaluation_id)
            if evaluation.status == "succeeded":
                assert len(evaluation.data["cases"]) == 8
                break
    else:
        with database() as session:
            details = [
                (job.kind, job.status, job.attempts, job.error) for job in session.scalars(select(Job))
            ]
        raise AssertionError(f"Evaluation did not complete: {details}")


def test_allowed_action_metric_uses_action_denominator():
    sources = [{"case_id": "a", "expected": {"should_escalate": False, "allowed_actions": ["one", "two"]}}]
    report = aggregate(
        [
            {
                "case_id": "a",
                "passed": False,
                "checks": {},
                "error": None,
                "should_escalate": False,
                "recommended_actions": ["one"],
            }
        ],
        sources,
    )
    assert report["metrics"]["allowed_action_recall"] == {"passed": 1, "total": 2, "rate": 0.5}


def test_changed_expected_labels_do_not_change_runtime_prediction(database):
    import copy

    from trustdesk.evaluation import evaluate_case
    from trustdesk.models import EvalCase

    with database.begin() as session:
        index_knowledge(session)
        case = copy.deepcopy(session.get(EvalCase, "eval_001").data)
    case["expected"]["category"] = "billing"
    result = evaluate_case(case, database)
    assert result["predicted_category"] == "refund"
    assert result["checks"]["category"] is False


def test_reimport_is_blocked_during_evaluation(database):
    from pathlib import Path

    import pytest

    from trustdesk.ingest import ingest

    with database.begin() as session:
        enqueue(session, "evaluation", payload={"evaluation_id": "pending"})
    with pytest.raises(ValueError, match="Import blocked"), database.begin() as session:
        ingest(session, Path(__file__).resolve().parents[2] / "capstone/data")
