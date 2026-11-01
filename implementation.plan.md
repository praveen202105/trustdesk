# Implementation plan

This is a future implementation sequence. No stage is marked complete. Build the required end-to-end workflow before optional enhancements. See [architecture](architecture.md), [API contracts](api-contracts.md), [edge cases](edge-cases.md) and [acceptance mapping](testing-and-evaluation.md).

## M0 — Verify source material and establish contracts

Inspect the source repository, its README, actual data files, tool catalog and `data/eval_cases.jsonl`. Record available fields, expected labels, document formats and any existing starter-code conventions. Map real source fields to this specification without renaming source IDs. Confirm `start_refund_review` arguments and mock tool response format; adapt illustrative contracts where source requirements demand it and update all related docs together.

Create a requirements checklist using R01–R14 in the testing document. Record unresolved policy dates/windows instead of guessing them. Pin compatible package/runtime versions in lockfiles after checking current official documentation. Choose a live model and embedding model explicitly, record embedding dimension, token limits, pricing assumptions and environment names.

Completion gate: source schema inventory, sample import mapping, evaluation schema adapter and exact tool contract documented; no unresolved issue prevents core implementation.

## M1 — Application skeleton and persistence

Create Next.js UI, FastAPI API, shared Python services, worker, Compose services and migrations. Implement demo login/session/Origin checks, health checks, shared errors and idempotent mutation storage. Add provider interfaces and deterministic mocks. Define the entities and indexes in architecture.md, including vector extension and job leases.

Completion gate: local services start, database migration succeeds, unauthenticated access is rejected, health readiness reflects dependencies, API can enqueue a durable job and worker can claim/finish it without duplicate commits.

## M2 — Import and ticket/context workflow

Implement an atomic importer for all six supplied data groups, source validation/hash tracking and reimport behavior. Preserve document IDs. Build ticket list/detail APIs and UI with linked customer/order context, missing-data states and ownership checks. Do not expose secrets or unnecessary PII.

Completion gate: clean import and identical reimport produce identical source counts; malformed required data rolls back with diagnostics; source links and ticket timestamps are verified. UI opens a representative supplied ticket.

## M3 — Retrieval and evidence display

Chunk knowledge documents with stable source references, index text and embeddings, implement the configured fusion/ranking and source excerpt endpoint. Establish policy metadata and deterministic eligibility checks from actual policy wording. Record retrieved IDs and versions before model generation.

Completion gate: known policy queries retrieve expected supplied IDs, citations open correct source versions, index changes invalidate stale drafts, and missing/conflicting evidence yields an explicit safe outcome.

## M4 — AI triage and cited drafts

Implement async triage and draft jobs with typed outputs, one schema repair attempt and provider timeouts. Apply allowed enums, backend escalation rules, claim/citation checks and eligibility verification. Build UI buttons, progress/status, citation review and escalation states. Persist sanitized traces, final status and token usage when available.

Completion gate: a supported ticket produces inspectable triage and grounded draft; an unsupported case escalates; invalid output never reaches an action. A slow model call does not block ticket reads.

## M5 — Human-approved refund review

Implement immutable proposals derived from reviewed drafts, authenticated approve/reject decisions and atomic execution-job scheduling. Revalidate context and policy before execution. Implement downstream mock idempotency, transactional duplicate-action prevention and recovery with stable action keys. UI shows proposed arguments/evidence, human decision and external result.

Completion gate: rejection causes zero calls; approval causes one logical review; concurrent decisions and crash-after-external-success do not duplicate the action. Stale or changed arguments require a new proposal and approval.

## M6 — Adversarial and reliability hardening

Security checks are required from earlier milestones; this stage consolidates attack and failure coverage. Test hidden-coupon injection, identity bypass, secret disclosure, malicious KB content, provider/network errors, lease expiry, partial completion and redaction. Validate deadlines, retry classification and recovery status presentation.

Completion gate: all deterministic safety/idempotency tests pass, including the known adversarial document. No customer or retrieved instruction can create approval or invoke arbitrary tools.

## M7 — Evaluation and acceptance

Import supplied evaluation cases through the inspected schema adapter. Implement CLI and API evaluation entry points, per-case child jobs, isolated test state and report generation. Calculate metrics from explicit denominators, include provider/dataset versions and expose failed/skipped cases in UI. Run supplied cases and project-specific failure tests; record measured outcomes without inventing passing scores.

Completion gate: one command or UI flow runs all imported cases, reports triage/citation/safety/escalation metrics, and supplies an R01–R14 evidence checklist. No skipped case is counted as passed.

## M8 — Demo and handoff

Finish setup/API documentation, environment template, reproducible mock demo and optional live-provider instructions. Capture a sanitized verification report and explainer video. Link public source repository and disclose limitations and outstanding AI-quality failures.

Completion gate: another developer follows setup from a clean environment, reproduces the complete workflow, inspects reports/traces and verifies every required submission item.
