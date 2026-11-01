# Architecture

## Runtime components

| Component | Responsibility |
| --- | --- |
| Next.js UI | Ticket/context views, async job status, citations, proposal review, traces and evaluation reports |
| FastAPI API | Authentication, validation, query endpoints, job submission and human decisions |
| Python worker | Retrieval, model calls, triage/draft generation, action execution and evaluation |
| PostgreSQL + pgvector | Source data, full-text/vector indexes, jobs, artifacts and audit state |
| Provider adapters | Live or deterministic mock model/embedding calls with deadlines and typed results |
| Mock action service | Idempotent `start_refund_review`; no actual refund |

Browser calls the same-origin Next.js `/api/v1` proxy, which forwards to FastAPI `/api/v1`. Provider credentials stay server-side. API and worker share database models and services. The API returns persisted job IDs immediately; browser polling renders progress. Use one worker process initially; transactional claiming must remain safe with multiple workers.

## Persistence model

Use source IDs as text primary keys for customers, orders, tickets and knowledge documents. Use UUIDs for generated artifacts. Foreign keys bind orders to customers, tickets to customers/orders and all derived records to their ticket. Missing optional order links are permitted and visible; contradictory ownership is a failed import or blocked operation.

| Entity | Required content |
| --- | --- |
| customers / orders / tickets | Original IDs, validated source fields, ticket `created_at`, source hash; minimize PII |
| knowledge_documents / chunks | Original document ID, content/version hash, source offsets, policy metadata when present, text index, embedding model/version/vector |
| tool_catalog | Imported tool definitions and hash; backend independently allowlists only the implemented action |
| triage_results | Ticket/version, category, priority, escalation flag/reason, AI run ID |
| drafts | Ticket/version, text, claim-to-citation references, reviewability status, AI run ID |
| action_proposals | Ticket/order, immutable canonical arguments/hash, evidence references, policy/context version, state and source run |
| approvals | Proposal, actor, approved/rejected decision, decision time and immutable argument hash |
| tool_calls | Proposal, stable idempotency key, attempts, external result/reference and failure classification |
| jobs | Type, sanitized input reference, status, attempt, lease owner/expiry, next eligible time, result/error |
| ai_runs / traces | Ticket, run type, retrieved document IDs, model, guardrail results, tool references, timing, token usage if supplied, final status |
| evaluation_runs / cases | Dataset hash, expected/actual comparison, per-case status, metric counts and report |

Add uniqueness for source IDs, one decision per proposal, one logical tool call per proposal, and idempotency keys scoped by actor + endpoint. Monetary values use decimals, timestamps are timezone-aware UTC. Migrations enable pgvector and pin embedding dimension to the configured adapter; changing the embedding model requires explicit reindexing.

## Data and AI flow

Import validates records and stages writes before an atomic commit; an invalid required record fails the batch with row/file diagnostics. Reimporting identical IDs/content is a no-op. Changed records are versioned or hash-updated, invalidate derived artifacts and trigger document reindexing. Never execute instructions from imported content or expose imported secrets.

For a ticket run, snapshot ticket/context hashes and policy corpus version. Retrieve with PostgreSQL full-text ranking and cosine vector search, fuse via reciprocal-rank fusion (`k=60`), return up to six chunks with at most two per document, and cap total retrieved context at 8,000 tokens. Missing embedding service fails the job with a clear retryable error; do not silently change retrieval semantics. Mock mode uses deterministic embeddings.

Pass delimited untrusted content into the model alongside a server-owned schema. Validate model output with Pydantic, then apply backend policy and guardrail checks. Citations must refer to retrieved document IDs and actual excerpt spans; critical eligibility claims require deterministic checks against policy evidence. Unsupported or conflicting critical facts produce escalation, not action eligibility. Invalid model output gets one repair attempt; otherwise fail safely. Store a concise decision rationale, not hidden chain-of-thought.

The retrieved policy may state dates/windows; compare against ticket `created_at` using its declared anchor (for example delivery date). If the policy cannot be interpreted reliably, or its effective version cannot be resolved from available metadata, escalate. Account-security requests always require escalation/identity verification outside V1; never approve bypasses.

## Action state machine

`proposed → approved → executing → succeeded` is the normal path. `proposed → rejected` is terminal. `approved → blocked` occurs on stale context or failed policy/guardrail revalidation. `executing → failed` records a permanent external failure. Transient failures remain `executing` while the durable job retries; exhausted uncertain outcomes remain `executing` with a reconciliation-required error, never a new logical action.

Only an authenticated human decision endpoint can insert an approval. The model may propose allowed arguments but cannot approve or execute. Approval is immutable and bound to the exact proposal argument hash. Approve and enqueue execution in one database transaction. Execute only after checking approval, ownership, current evidence and allowed tool type. Changed context requires a new proposal and new approval; no force-execute endpoint.

Every downstream attempt uses the same stable key derived from the proposal ID. The mock action service atomically stores key + argument hash + result, replays identical calls and rejects mismatches. A worker crash after external success must replay the same key and recover the result. Without downstream idempotency support, exactly-once side effects cannot be guaranteed; V1 requires that support.

## Durable work and authentication

Claim jobs using `FOR UPDATE SKIP LOCKED`, a lease and attempt fencing token. Heartbeat every 10 seconds; lease expires after 60 seconds. Only the current lease holder may commit results. Use an outbox-style database job row in the same transaction as approval. API `job.status` values are `queued`, `running`, `succeeded`, `failed`; action state is separate.

Set model/embedding deadlines to 30 seconds, mock-action deadline to 10 seconds, and ordinary job deadline to 120 seconds. Retry transport failures, 429s and 5xx up to three total attempts with bounded exponential backoff; honor bounded `Retry-After`. For side-effect jobs, retry only with the original key. Evaluation parent jobs orchestrate individually bounded case jobs; they may exceed 120 seconds overall.

Demo login exchanges a configured token for an eight-hour signed HttpOnly, SameSite=Strict session cookie. Keep the token out of URLs and browser storage. Validate Origin on mutations, restrict CORS, rate-limit login and redact credentials. Use HTTPS/Secure cookies outside localhost. A fixed demo actor is sufficient; full RBAC is optional. Protect every route except health and login.

## Observability

Correlate requests, jobs and AI runs. Record sanitized error codes, latency, retries, citation validity, guardrail decisions and external references. Never log tokens, hidden prompts or unnecessary customer PII. Console displays inspectable traces with restricted/redacted data; local retention defaults to 30 days with a documented purge task.

## Implementation roadmap update

Follow [phase progress](phase-progress.md) and [source provenance](source-provenance.md). Verified capstone requirements override earlier illustrative examples. Only refund review is executable; its payload includes amount and idempotency_key. Mock AI results do not establish live-model quality.

## Live provider contract verification

The compatible adapter uses Chat Completions JSON mode, validates returned triage fields with Pydantic, and permits one schema-repair attempt. JSON mode alone is not treated as schema validation. Completion output is bounded with `max_completion_tokens`; no deprecated `max_tokens` field is sent. These details were verified against the [official API reference](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create). No live-provider quality or account-access result is claimed. Draft prose is restricted to reviewed policy templates in V1; unreviewed paraphrases trigger human escalation.
