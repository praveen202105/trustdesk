"""Exercise a seeded mock workspace through its public HTTP boundary."""
import argparse
import json
import os
import time
import uuid
from pathlib import Path

import httpx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:3000")
    parser.add_argument("--approve", action="store_true", help="Approve the fictional seeded refund-review proposal")
    parser.add_argument("--output")
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    token = os.getenv("TRUSTDESK_ACCESS_TOKEN")
    if not token and base in ("http://localhost:3000", "http://127.0.0.1:3000"):
        token = "local-demo-only"
    if not token:
        raise SystemExit("Set TRUSTDESK_ACCESS_TOKEN for the hosted workspace")
    report = {"base_url": base, "checks": []}
    with httpx.Client(timeout=20, headers={"Origin": base}) as client:
        def call(method, path, body=None, key=None):
            headers = {"Idempotency-Key": key or str(uuid.uuid4())} if method == "POST" else {}
            response = client.request(method, base + "/api/v1" + path, json=body, headers=headers)
            response.raise_for_status()
            return response.json() if response.status_code != 204 else None

        def wait(job_id):
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                job = call("GET", "/jobs/" + job_id)
                if job["status"] == "succeeded":
                    return job["result"]
                if job["status"] == "failed":
                    raise AssertionError(f"Job failed: {job['error']['code']}")
                time.sleep(0.5)
            raise AssertionError("Timed out waiting for a job")

        report["health"] = call("GET", "/health")
        assert report["health"]["mode"] == "mock", "This script exercises the deterministic mock demo only"
        assert client.get(base + "/api/v1/tickets").status_code == 401
        call("POST", "/auth/session", {"token": token})
        tickets = call("GET", "/tickets")
        assert len(tickets["items"]) == 8
        report["checks"].append("authenticated_ticket_list")
        detail = call("GET", "/tickets/tkt_9008")
        assert detail["ticket"]["customer_id"] == detail["order"]["customer_id"]
        triage = wait(call("POST", "/tickets/tkt_9008/triage", {})["job_id"])
        assert triage["category"] == "billing"
        draft = wait(call("POST", "/tickets/tkt_9008/drafts", {})["job_id"])
        assert "KB-BILLING-001" in {c["document_id"] for c in draft["citations"]}
        report["checks"].extend(["linked_context", "background_triage", "cited_draft"])
        if args.approve:
            proposals = call("GET", "/tickets/tkt_9008/action-proposals")["items"]
            active = [p for p in proposals if p["state"] in ("proposed", "approved", "executing", "succeeded")]
            proposal = active[0] if active else call("POST", "/tickets/tkt_9008/action-proposals", {"draft_id": draft["artifact_id"]})
            if proposal["state"] == "proposed":
                body = {"decision": "approved", "reason": "Authorized seeded mock smoke test"}
                key = str(uuid.uuid4())
                first = call("POST", f"/action-proposals/{proposal['proposal_id']}/decision", body, key)
                replay = call("POST", f"/action-proposals/{proposal['proposal_id']}/decision", body, key)
                assert first["execution_job_id"] == replay["execution_job_id"]
                wait(first["execution_job_id"])
            elif proposal["state"] != "succeeded":
                wait(proposal["execution_job_id"])
            proposal = call("GET", "/action-proposals/" + proposal["proposal_id"])
            assert proposal["state"] == "succeeded"
            assert proposal["result"]["money_refunded"] is False
            report["proposal_id"] = proposal["proposal_id"]
            report["external_review_id"] = proposal["result"]["external_review_id"]
            report["checks"].append("approved_idempotent_mock_review")
        evaluation = call("POST", "/evaluations", {"suite": "provided"})
        wait(evaluation["job_id"])
        result = call("GET", "/evaluations/" + evaluation["evaluation_id"])
        assert result["total_cases"] == result["passed_cases"] == 8
        assert result["errored_cases"] == 0
        report["evaluation_id"] = evaluation["evaluation_id"]
        report["evaluation_passed"] = result["passed_cases"]
        report["evaluation_total"] = result["total_cases"]
        report["checks"].append("all_supplied_mock_cases")
        call("DELETE", "/auth/session")
        assert client.get(base + "/api/v1/tickets").status_code == 401
        report["checks"].append("logout_protects_workspace")
    if args.output:
        target = Path(args.output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
