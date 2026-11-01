# Implemented API contracts

Base path: `/api/v1`. Source ticket IDs remain `tkt_*`; generated artifacts/jobs/proposals/evaluations use UUIDs. JSON uses snake_case. All routes except health and login require the demo session cookie. Mutations require the exact configured `Origin`. The browser uses the Next.js proxy; provider/action credentials remain server-side.

## Routes

| Method / route | Input | Success |
| --- | --- | --- |
| GET `/health` | None | 200 status, mode and revision; unavailable database 503 |
| POST `/auth/session` | `{ "token": "<access token>" }` | 204 and cookie |
| DELETE `/auth/session` | None | 204, cookie removed |
| GET `/tickets` | limit 1–100 (25 default), opaque cursor, optional category/priority/escalation | items, next_cursor and AI mode |
| GET `/tickets/{ticket_id}` | Source ID | ticket, minimal customer context, associated order, latest triage/draft and warnings |
| POST `/tickets/{ticket_id}/triage` | `{}` | 202 job_id/status |
| POST `/tickets/{ticket_id}/drafts` | `{}`; successful current triage required | 202 job_id/status |
| GET `/tickets/{ticket_id}/drafts` | Source ID | up to 100 versioned drafts |
| GET `/tickets/{ticket_id}/traces` | Source ID | up to 100 recent sanitized traces |
| GET `/knowledge/search` | query, 1–2,000 characters | ranked chunks with source/version/excerpt/score |
| GET `/knowledge/documents/{document_id}` | optional version_hash | versioned source content, title and approval flag |
| GET `/jobs/{job_id}` | UUID | queued/running/succeeded/failed, attempts, result or error |
| POST `/tickets/{ticket_id}/action-proposals` | `{ "draft_id": "<uuid>" }` | 201 validated proposal |
| GET `/tickets/{ticket_id}/action-proposals` | Source ID | up to 100 recent proposals |
| GET `/action-proposals/{proposal_id}` | UUID | state, canonical arguments, evidence and execution result |
| POST `/action-proposals/{proposal_id}/decision` | decision approved/rejected; reason 1–1,000 characters | 200 proposal; approval also returns execution_job_id |
| POST `/evaluations` | `{ "suite": "provided" }` | 202 evaluation_id, job_id, status |
| GET `/evaluations/{evaluation_id}` | UUID | progress or complete case/metric report, with errors disclosed |

Data import/index are local management commands. Ticket creation, customer reply delivery and direct tool execution are not public endpoints. The original capstone permits documented route-shape changes; its workflows are preserved.

## Idempotent mutation contract

All POST operations except login require `Idempotency-Key` (maximum 200 characters). Scope is actor + route + key. The same key/body replays the original status/body; a changed body returns `409 IDEMPOTENCY_CONFLICT`. V1 retains these records without automatic expiry. Approval/action uniqueness provides additional protection across different request keys.

Submission returns a job before model work begins. Poll `/jobs/{job_id}` until terminal; errors after acceptance appear in the job record, not as a changed historical HTTP response. Triage results contain category, priority, sentiment, escalation_required and reason. Completed jobs link artifact_id and ai_run_id. Drafts contain text, citations, status, escalation_required and recommended_actions.

A citation includes document_id, version_hash, chunk_id, quote and claim. A ready draft is `ready_for_review`; a safe refusal/escalation is `escalated`. Generic refusals without policy claims may have no citations.

## Refund-review payload

Illustrative shape using real source IDs; UUIDs and review references are generated at runtime:

```json
{
  "proposal_id": "<uuid>",
  "ticket_id": "tkt_9008",
  "action_type": "start_refund_review",
  "arguments": {
    "order_id": "ord_5006",
    "reason": "A duplicate charge requires billing review",
    "amount": "15999",
    "idempotency_key": "refund-review:<proposal uuid>"
  },
  "state": "proposed",
  "execution_job_id": null
}
```

The client cannot supply or edit action arguments. Rejecting prevents execution. Approving inserts an immutable Approval and durable Job atomically. A successful result contains an external_review_id, status `review_requested` and `money_refunded: false`. Existing decisions replay; opposing decisions return 409. Changed context blocks execution and requires new reviewed evidence.

## Errors

Common envelope:

```json
{"error":{"code":"STALE_CONTEXT","message":"Stale context","request_id":"<uuid>","details":{}}}
```

401: invalid/missing/expired session. 403: Origin, tool permission or ownership failure. 404: missing resource/version. 409: stale context, decision/body conflict, duplicate action or required triage. 413: body over 256 KiB. 422: invalid schema/enum, evidence or missing idempotency key. 429: login throttling with Retry-After. 503: database/API/retrieval unavailable. Job errors are sanitized and do not include provider bodies, credentials or stack traces.

## Internal service

`POST /internal/refund-reviews` belongs only to mock-actions, not the public API proxy. It requires `X-Action-Secret`, a matching Idempotency-Key header and the catalog-required payload. It atomically replays an existing effect or rejects a mismatched body. Only web receives public networking in the Railway setup.
