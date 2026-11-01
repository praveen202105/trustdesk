# API contracts

Design contract for the future implementation. All payload examples are illustrative, not verified supplied-data schemas. Base path: `/api/v1`. JSON uses snake_case; generated IDs are UUIDs in implementation. Timestamps use ISO 8601 UTC. Pagination uses `limit` (default 25, maximum 100) and opaque `cursor`.

## Shared behavior

Authenticate with the demo session cookie. All mutation routes require valid Origin. For POST operations other than login/logout, require `Idempotency-Key`. Persist actor + route + key + canonical body hash atomically with the mutation: same request replays the original response; a different body returns `409 IDEMPOTENCY_CONFLICT`. Retain request keys for 30 days; action proposal uniqueness and downstream action keys remain permanent.

Async submissions return `202 {"job_id":"<uuid>","status":"queued"}`. `GET /jobs/{id}` returns status and a typed `result` on success or sanitized `error` on failure. Poll at two-second intervals, back off to ten seconds, and stop on terminal status. A failed draft/triage job can be resubmitted with a new key after its cause is fixed.

Errors use `{"error":{"code":"EVIDENCE_INSUFFICIENT","message":"Policy evidence is missing","request_id":"<uuid>","details":{}}}`. Never return provider secrets or raw stack traces.

## Routes

| Method and route | Input | Result |
| --- | --- | --- |
| GET `/health` | None | 200 with service readiness; no credentials/config dump |
| POST `/auth/session` | `{ "token": "<demo token>" }` | 204 and session cookie; invalid token 401 |
| DELETE `/auth/session` | None | 204, clears session |
| GET `/tickets` | Optional category, priority, escalation filters, cursor, limit | 200 items and next_cursor; filters use latest successful triage |
| GET `/tickets/{ticket_id}` | Source ticket ID | 200 ticket, linked customer/order, latest artifacts and data warnings; missing ticket 404 |
| POST `/tickets/{ticket_id}/triage` | `{}` | 202 triage job |
| POST `/tickets/{ticket_id}/drafts` | `{}` | 202 draft job; latest successful triage required, otherwise 409 TRIAGE_REQUIRED |
| GET `/tickets/{ticket_id}/drafts` | Pagination | 200 versioned drafts |
| GET `/knowledge/documents/{document_id}` | Document ID, optional version hash | 200 policy text/excerpts for citation review; unavailable version 404 |
| POST `/tickets/{ticket_id}/action-proposals` | `{ "draft_id": "<uuid>" }` | 201 validated proposal; only server derives action arguments from draft/context |
| GET `/action-proposals/{proposal_id}` | Proposal ID | 200 proposal, decision and execution state |
| POST `/action-proposals/{proposal_id}/decision` | `{ "decision": "approved", "reason": "Reviewed evidence" }` | 200 decision/proposal; approved also creates execution job atomically |
| GET `/tickets/{ticket_id}/traces` | Pagination | 200 sanitized AI traces and action references |
| GET `/jobs/{job_id}` | Job ID | 200 status, result or error |
| POST `/evaluations` | `{ "suite": "provided" }` | 202 evaluation job over configured imported dataset; no client filesystem paths |
| GET `/evaluations/{evaluation_id}` | Evaluation ID | 200 counts, metrics, cases, failures and completion status |

Data import is a local management CLI, not a browser file-upload endpoint. No customer-send, direct refund, approval-bypass or arbitrary tool-execution endpoint exists.

## Representative results

Successful triage job result:

```json
{
  "triage_id": "<uuid>",
  "ticket_id": "TICKET-EXAMPLE-001",
  "category": "refund",
  "priority": "medium",
  "escalation_required": false,
  "reason": "A policy-supported review path is available",
  "ai_run_id": "<uuid>"
}
```

Successful draft job result:

```json
{
  "draft_id": "<uuid>",
  "ticket_id": "TICKET-EXAMPLE-001",
  "text": "We can request a refund review under the applicable policy.",
  "citations": [
    {"document_id": "KB-REFUND-001", "version_hash": "<hash>", "chunk_id": "<uuid>", "quote": "<actual supporting excerpt>", "claim": "A refund review may be requested"}
  ],
  "status": "ready_for_review",
  "escalation_required": false,
  "ai_run_id": "<uuid>"
}
```

Draft status is `ready_for_review` or `escalated`. An escalated draft may contain only a safe clarification/refusal; it cannot support an action proposal. Citations need not exist for a generic safe refusal that makes no policy claims.

Action proposal shape:

```json
{
  "proposal_id": "<uuid>",
  "ticket_id": "TICKET-EXAMPLE-001",
  "action_type": "start_refund_review",
  "arguments": {"order_id": "ORDER-EXAMPLE-001", "reason": "Policy-supported review request"},
  "arguments_hash": "<sha256>",
  "state": "proposed",
  "evidence_document_ids": ["KB-REFUND-001"],
  "execution_job_id": null
}
```

Decision values are only `approved` and `rejected`. An identical repeated decision returns the stored result; an opposing decision returns 409. Approval returns `execution_job_id`; execution proceeds asynchronously. Proposal terminal result includes `external_review_id` if successful. One proposal per draft/action type prevents accidental double clicks; execution also rejects another active or successful refund-review action for the same ticket/order. A genuinely new review after prior success is outside V1.

## Validation and errors

| HTTP | Codes and expected client behavior |
| --- | --- |
| 400 / 422 | Malformed request, missing idempotency key, invalid enum/schema; show validation feedback |
| 401 | SESSION_REQUIRED / INVALID_TOKEN; require login |
| 403 | ORIGIN_REJECTED / ACTION_NOT_ALLOWED; do not retry blindly |
| 404 | RESOURCE_NOT_FOUND; show missing-record state |
| 409 | TRIAGE_REQUIRED, IDEMPOTENCY_CONFLICT, DECISION_CONFLICT, STALE_CONTEXT, DUPLICATE_ACTION, INVALID_STATE; refresh context |
| 422 | EVIDENCE_INSUFFICIENT / CONTEXT_INCOMPLETE; show escalation reason |
| 429 | RATE_LIMITED with Retry-After |
| 503 | DATABASE_UNAVAILABLE / QUEUE_UNAVAILABLE; request not accepted, safe retry using same key |

Model/provider failures after 202 appear as failed job error codes (`PROVIDER_TIMEOUT`, `PROVIDER_UNAVAILABLE`, `INVALID_AI_OUTPUT`, `RETRIEVAL_UNAVAILABLE`). They do not retroactively change the submission HTTP response. Once approval is committed, UI/network failure must not erase the decision; reread proposal/job state.

## Implementation roadmap update

Follow [phase progress](phase-progress.md) and [source provenance](source-provenance.md). Verified capstone requirements override earlier illustrative examples. Only refund review is executable; its payload includes amount and idempotency_key. Mock AI results do not establish live-model quality.
