import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from .models import Customer, Document, DocumentVersion, EvalCase, Order, Ticket, ToolDefinition


def checksum(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def source_data(path: Path) -> dict[str, Any]:
    data = {
        name: json.loads((path / f"{name}.json").read_text())
        for name in ("customers", "orders", "tickets", "tool_actions")
    }
    data["eval_cases"] = [
        json.loads(line) for line in (path / "eval_cases.jsonl").read_text().splitlines() if line.strip()
    ]
    data["documents"] = []
    for p in sorted((path / "knowledge_base").glob("*.md")):
        content = p.read_text()
        if len(content.encode()) > 5 * 1024 * 1024:
            raise ValueError("Document size exceeded")
        doc_id = re.search(r"Doc ID: (.+)", content)
        version = re.search(r"Version: (.+)", content)
        if not doc_id or not version:
            raise ValueError("Knowledge document metadata missing")
        data["documents"].append(
            {
                "id": doc_id[1].strip(),
                "version": version[1].strip(),
                "title": content.splitlines()[0].lstrip("# "),
                "content": content,
            }
        )
    return data


def validate(data: dict[str, Any]) -> None:
    keys = {
        "customers": "customer_id",
        "orders": "order_id",
        "tickets": "ticket_id",
        "tool_actions": "tool_name",
        "eval_cases": "case_id",
        "documents": "id",
    }
    for group, key in keys.items():
        ids = [row[key] for row in data[group]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate source ID in {group}")
    customers = {x["customer_id"] for x in data["customers"]}
    orders = {x["order_id"]: x for x in data["orders"]}
    for order in orders.values():
        if order["customer_id"] not in customers or order["total"] < 0:
            raise ValueError("Invalid order customer or amount")
    for tool in data["tool_actions"]:
        if (
            not isinstance(tool.get("required_fields"), list)
            or not isinstance(tool.get("allowed_categories"), list)
            or not isinstance(tool.get("requires_human_approval"), bool)
            or tool.get("risk_level") not in ("low", "medium", "high")
        ):
            raise ValueError("Invalid tool catalog schema")
    for ticket in data["tickets"]:
        dt = datetime.fromisoformat(ticket["created_at"])
        if not dt.tzinfo or ticket["customer_id"] not in customers or not ticket["body"].strip():
            raise ValueError("Invalid ticket timestamp/customer/body")
        if len(ticket["body"].encode()) > 256 * 1024:
            raise ValueError("Ticket size exceeded")
        if ticket.get("order_id"):
            order = orders.get(ticket["order_id"])
            if not order or order["customer_id"] != ticket["customer_id"]:
                raise ValueError("Order ownership mismatch")
    tickets = {x["ticket_id"] for x in data["tickets"]}
    if any(x["ticket_id"] not in tickets for x in data["eval_cases"]):
        raise ValueError("Evaluation ticket missing")


def ingest(session: Session, path: Path) -> dict[str, int]:
    from datetime import timedelta

    from sqlalchemy import select

    from .jobs import advisory
    from .models import EvaluationRun, Job, now

    advisory(session, "source-import")
    active_jobs = session.scalar(
        select(Job.id)
        .where(Job.status.in_(["queued", "running"]), Job.kind.in_(["evaluation", "eval_case"]))
        .limit(1)
    )
    active_sync = session.scalar(
        select(EvaluationRun.id)
        .where(
            EvaluationRun.job_id.is_(None),
            EvaluationRun.status == "running",
            EvaluationRun.created_at > now() - timedelta(minutes=30),
        )
        .limit(1)
    )
    if active_jobs or active_sync:
        raise ValueError("Import blocked while an evaluation is active")
    data = source_data(path)
    validate(data)  # Validate all groups before writing any rows.
    for model, group, key in (
        (Customer, "customers", "customer_id"),
        (Order, "orders", "order_id"),
        (Ticket, "tickets", "ticket_id"),
    ):
        for row in data[group]:
            safe = {k: v for k, v in row.items() if not k.startswith("expected_")}
            values: dict[str, Any] = {"id": row[key], "data": safe, "checksum": checksum(safe)}
            if model in (Order, Ticket):
                values["customer_id"] = row["customer_id"]
            if model is Ticket:
                values.update(
                    order_id=row.get("order_id"), created_at=datetime.fromisoformat(row["created_at"])
                )
            session.merge(model(**values))
        session.flush()
    for doc in data["documents"]:
        digest = checksum(doc["content"])
        # Trust is server policy metadata, not a command in retrieved text.
        approved = json.loads((Path(__file__).parent / "approved_policies.json").read_text())
        session.merge(
            Document(
                id=doc["id"],
                title=doc["title"],
                content=doc["content"],
                checksum=digest,
                version=doc["version"],
                trusted_policy=approved.get(doc["id"]) == digest,
            )
        )
        session.flush()
        session.merge(
            DocumentVersion(
                id=doc["id"] + ":" + digest,
                document_id=doc["id"],
                checksum=digest,
                content=doc["content"],
                title=doc["title"],
            )
        )
    for row in data["tool_actions"]:
        session.merge(ToolDefinition(id=row["tool_name"], data=row))
    for row in data["eval_cases"]:
        session.merge(EvalCase(id=row["case_id"], data=row))
    session.flush()
    return {key: len(value) for key, value in data.items()}
