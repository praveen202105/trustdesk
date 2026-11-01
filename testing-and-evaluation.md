# Testing and evaluation

Status: test specification only. No tests have run and no scores are claimed.

## Verification layers

- Unit tests (pytest): policy date boundaries, typed model outputs, evidence references, tool allowlist, idempotency hashes, context version checks, safe redaction and state transitions.
- Integration tests with real PostgreSQL/pgvector and mock providers: atomic imports, text/vector retrieval, source preservation, auth, durable jobs, approval/enqueue atomicity and evaluation persistence. SQLite is not an adequate substitute for concurrency/locking tests.
- Reliability tests with two workers: concurrent approval, lease expiry, duplicate submissions, provider failures, kill-before-call and kill-after-external-success recovery. Count mock-world effects independently of local database rows.
- Browser tests (Playwright): login, ticket inspection, triage, draft/citation review, approve/reject, action status, escalation and evaluation summary. Escape malicious text and verify no secret appears in rendered traces.
- Supplied evaluations: inspect and adapt `data/eval_cases.jsonl`; preserve every case, original expectations and document IDs. Separate extra project cases from supplied cases in reports.

## Metrics

| Metric | Definition |
| --- | --- |
| Category accuracy | Correct expected categories / cases with category labels; report count and per-category breakdown |
| Priority accuracy | Correct expected priorities / cases with priority labels |
| Citation coverage | Supported policy claims with valid source references / all generated policy claims requiring evidence |
| Citation validity | Valid retrieved document/version/excerpt references / all emitted references |
| Unsafe-action blocking | Unsafe cases with zero forbidden effects and the expected safe decision / all unsafe-action cases |
| Escalation behavior | Expected-versus-actual escalation confusion matrix, precision and recall, plus case reasons |
| Execution completion | Successfully processed cases / all supplied cases, with errored/skipped counts separately |

Coverage and validity are different: an existing ID does not prove a claim is supported. Use supplied case expectations and human-reviewed claim annotations to score grounding; do not let an unchecked model grade itself as the sole acceptance authority. If the supplied suite uses a different native metric, report it alongside these metrics without changing its expectations. Report unavailable/undefined metrics as N/A with denominator zero. Never exclude processing errors from a headline success rate without disclosure.

Report dataset hash, corpus version, model/embedding IDs, prompt version, mock/live mode, configuration, timestamps, expected/actual outputs and sanitized failures. Deterministic mock scores prove plumbing; they are not evidence of live-model quality. Keep live-provider results separately labeled.

## PDF requirement traceability

| ID | Required capability | Milestone | Acceptance evidence |
| --- | --- | --- | --- |
| R01 | Load customers/orders/tickets/tools/evals/KB, preserve IDs | M0–M2 | Import counts, ID assertions, repeat-import and rollback tests |
| R02 | Policy windows evaluated at ticket created_at | M3–M4 | Boundary/timezone tests; current-clock changes do not change decision |
| R03 | List/detail/context APIs and simple UI | M2 | Contract tests and ticket-view browser flow |
| R04 | Retrieval and policy-cited drafts | M3–M4 | Source links, claim/excerpt checks and grounding evaluation |
| R05 | Category, priority and escalation triage | M4 | Enum validation, expected-label comparisons and escalation matrix |
| R06 | One human-approved idempotent tool action | M5 | Approve/reject, bypass denial, concurrency and crash recovery |
| R07 | Identity/coupon/secret/injected-document defenses | M4–M6 | E12–E16 and E21; zero forbidden effects |
| R08 | Minimum trace per AI run | M4 | Ticket/run type, retrieved IDs, tool actions, guardrail result and final status persisted |
| R09 | Evaluation runner and visible summary | M7 | One command/API/UI flow, complete case counts and four required metric families |
| R10 | Persistent store and simple authentication | M1–M5 | Restart persistence, session checks and protected-route tests |
| R11 | Retrieval layer and mockable AI adapter | M1–M4 | Real retrieval integration; mock/live adapter contract tests |
| R12 | Nonblocking long AI/evaluation operations | M1, M4, M7 | While provider is held for 10 seconds, ticket reads finish within 2 seconds locally |
| R13 | Critical-flow/guardrail automated tests | M2–M7 | Saved test command output and failure details |
| R14 | README, public repo, explainer video, evaluation summary | M8 | Reproducible clean setup and submission checklist |

The 2-second local responsiveness check is a project target, not a PDF-specified performance promise. Record machine/environment details and investigate failures rather than relabeling the threshold after the run.

## Acceptance gates

1. R01–R14 each has actual evidence, not a planned checkbox alone.
2. All deterministic safety, authentication, data-integrity and idempotency checks pass; unsafe tests cause zero forbidden external effects.
3. Crash-after-success test observes exactly one downstream effect and a recoverable final action result.
4. All provided cases are accounted for; actual category/priority, citation, blocking and escalation metrics are disclosed with failures.
5. AI-quality failures are fixed or explicitly documented. No numerical accuracy threshold is invented from the PDF.
6. Another developer reproduces the mock workflow from clean setup; live-provider limitations are visible.

Maintain an evidence table with requirement ID, test/demo reference, observed result, date and unresolved issue. A template or planned test is never a passing result.
