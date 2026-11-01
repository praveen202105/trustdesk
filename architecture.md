# Architecture

## Components and request path

Browser → Next.js same-origin `/api/v1` proxy → FastAPI → PostgreSQL. A separate Python worker claims durable jobs. An internal mock-actions service records idempotent refund-review effects in a separate transaction. On Railway, only the web service has a public domain; other traffic uses private networking.

Next.js: ticket list/detail, customer/order context, triage/drafts, source viewer, approval review, traces and evaluation results. FastAPI: session checks, body validation, idempotency, job submission and reads. PostgreSQL: source records, versions, vectors, jobs, artifacts, approvals, traces and evaluation reports.

## Persistent records

| Record | Function |
| --- | --- |
| Customer / Order / Ticket | Preserved source IDs and source hashes; ticket dates retained; expected labels excluded |
| Document / DocumentVersion / Chunk | Current source, immutable versions, approved-policy flag, indexed text and embedding/model identity |
| ToolDefinition / EvalCase | Original catalog and separate grading cases |
| Artifact | Versioned triage or draft tied to a runtime-context hash |
| Job / Idempotency | Durable execution, leases, attempts, response replay and request-body hash |
| Proposal / Approval / ToolCall | Immutable canonical arguments, human decision, stable execution key and result |
| MockEffect | Independent downstream idempotency record |
| Trace / EvaluationRun | Sanitized decision evidence, per-case results, counts and source/config fingerprints |

Use Alembic migrations under a database advisory lock acquired before version-table work. Automatic destructive downgrades are disabled. PostgreSQL connection establishment, statements and lock waits are bounded. Source imports validate all groups before committing; evaluation activity blocks reimport to keep results consistent.

## AI and retrieval

Only explicitly approved hashes of the seven supplied policy documents can be retrieved. The vendor adversarial document remains in storage for audit. A changed policy must be explicitly approved in server configuration before use.

Chunk policies at paragraph boundaries around 1,500 characters. Rank with PostgreSQL full-text search and pgvector cosine distance, fuse by reciprocal-rank fusion (`k=60`), and select at most six chunks/two per document. Model/dimension mismatches or missing/stale indexes fail explicitly. Mock embeddings are deterministic token hashes; live compatible embeddings require reindexing.

Generation context comes from runtime ticket/customer/order/policy state, never seed expected labels. Emails, payment-like numeric sequences, labeled credential values and configured secrets are masked before external model input; customer names and tracking numbers are omitted. This redaction is heuristic.

Mock triage uses documented policy rules. Live triage accepts typed category/priority/sentiment/escalation/reason fields and applies backend safety/priority checks. Conflicting model classification escalates. JSON mode output is validated with Pydantic, with one schema-repair attempt. The live adapter uses `max_completion_tokens`, verified against the [official reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create).

Drafts use reviewed templates tied to approved policy content. Unknown live paraphrases are not accepted as policy claims; they trigger escalation. Citations must reference retrieved, current, approved document versions and actual excerpts. Reference validity and required-document coverage are not semantic grounding scores.

Policy windows use ticket `created_at`, not the wall clock. Physical returns use the verified seven-day inclusive delivery window; warranty uses 12 months plus an eligible gold-tier six-month extension. Unknown conditions and safety issues go to specialists.

## Durable execution

Job states: `queued → running → succeeded/failed`. Claim with `FOR UPDATE SKIP LOCKED`, a unique owner token and a 60-second lease. Heartbeat every ten seconds; commit only if the lease/owner still match. Transient job failures receive at most three attempts with bounded backoff. The worker reconnects after database outages without logging connection details. Every provider call has a 30-second timeout and action calls have a ten-second timeout. There is no separate process-kill deadline; calls and database operations are bounded individually.

Evaluation parents schedule child case jobs, defer without consuming retry attempts while children run, and aggregate every result. A 30-minute evaluation deadline prevents indefinite parent polling. CLI evaluation uses the same analysis/grading functions synchronously. Neither evaluation entry point executes tools or creates ticket drafts/proposals.

## Human approval and effects

Proposal states: `proposed → approved → executing → succeeded`; `rejected`, `blocked` and `failed` represent non-success outcomes. Approval is an authenticated human API operation, bound to the exact argument hash. Approval and execution-job insertion commit atomically. The AI never receives approval permissions or service credentials.

The backend derives order, reason and amount from validated context. It enforces catalog required fields, category, risk and approval requirement. Revalidate policy/ownership/context before the external call and hold source read locks over it. Changed evidence needs a fresh draft/proposal/approval. Concurrent proposals for the same active/successful ticket/order review are blocked.

The downstream mock service atomically stores idempotency key, argument hash and result. Replay after a worker crash returns the same review reference. Exactly-once effects depend on downstream idempotency; they are not guaranteed for arbitrary services. An exhausted uncertain attempt keeps its logical action/key for manual reconciliation.

## Authentication and observability

One demo agent/session, signed HttpOnly SameSite=Strict cookie, eight-hour TTL, mutation Origin checks and ten login attempts per IP/minute. HTTPS hosting requires unique secrets and Secure cookies. Full RBAC and distributed login throttling are not implemented.

Persist ticket/run type, retrieved IDs, recommendations/tool calls, guardrail outcome, final status, model/config information and available token counts. Failure traces and API errors exclude raw exceptions and credentials. No hidden chain-of-thought is stored. Retention/purge automation is not included; operators manage retention explicitly.

## Free hosting profile

[Render + Neon](free-deployment.md) uses four supervised processes in a single free Render container, with API and action ports bound to loopback. PostgreSQL/pgvector stays on a separate Neon project for each environment. The job and approval contracts are unchanged; workers resume persisted work when the host wakes after idle sleep. Local Compose retains separate containers. This hosting profile trades always-on availability for zero-cost demo hosting.
