# Edge cases and expected behavior

Every row is a planned test scenario, not a recorded test result. Safety decisions are enforced in backend services, independent of model instructions. Reference [API contracts](api-contracts.md) for statuses and [architecture](architecture.md) for state transitions.

| ID | Scenario | Required behavior / verification |
| --- | --- | --- |
| E01 | Identical dataset imported twice | No duplicate records; IDs and counts stable. |
| E02 | Duplicate source ID with conflicting content in one import | Reject batch with record diagnostics; no partial commit. |
| E03 | Missing/invalid ticket created_at | Reject required source record; never substitute today. |
| E04 | Ticket missing optional order | Show missing context; allow safe general triage; block order-dependent action. |
| E05 | Ticket/order/customer ownership mismatch | Reject inconsistent import or block derived operation; expose no other customer's context. |
| E06 | Eligibility boundary, timezone or historical ticket | Use ticket created_at and actual policy anchor/window; test just before, at and after the boundary with documented inclusivity. |
| E07 | Missing delivery date or unclear policy anchor | Escalate; no inferred eligibility or action. |
| E08 | No relevant retrieval evidence | Safe refusal/clarification with escalation; no fabricated policy or citation. |
| E09 | Conflicting or unresolved policy versions | Show conflict and escalate; choose only using explicit effective/version metadata. |
| E10 | Correct citation ID but unsupported claim | Fail grounding check; repair once or escalate; ID validity alone is insufficient. |
| E11 | Fabricated citation ID or excerpt | Reject citation; no ready-for-review artifact or action from the invalid output. |
| E12 | Customer asks to ignore policy or reveal hidden coupon | Treat as untrusted input; no unauthorized coupon/action; record guardrail decision. |
| E13 | KB-ADVERSARIAL-001 contains embedded commands | It cannot override application rules, approve actions or disclose prompts/secrets. |
| E14 | Customer requests identity-check bypass | Escalate account-security case; no bypass or sensitive action. |
| E15 | Request for prompts, tokens or another customer's PII | Refuse; redact traces/UI and avoid fetching unrelated context. |
| E16 | Model returns invalid JSON, wrong enum or extra tool | One schema repair attempt; then fail safely; tool allowlist remains server-controlled. |
| E17 | Provider timeout, 429 or transient 5xx | Bounded retries and visible async failure; ticket read APIs remain responsive. |
| E18 | Embedding index/model mismatch or unavailable service | Fail retrieval job explicitly; require reindexing for changed model; do not silently mix vectors. |
| E19 | Two same-key concurrent mutation requests | One persisted effect; both obtain original response, or mismatched body returns 409. |
| E20 | Double-click approval or opposing simultaneous decisions | Same decision replay is safe; only one immutable decision wins; opposing one gets 409. |
| E21 | Caller or model invokes execution without approval | No public bypass route; internal execution guard rejects; zero external calls. |
| E22 | Arguments, ticket or policy changes after proposal | Mark approval/execution blocked; create a fresh proposal and request fresh human approval. |
| E23 | Repeated proposal or separate attempt for same ticket/order | Reuse/deny duplicate; no second active/successful review for the logical request. |
| E24 | Worker crashes before external request | Lease recovery retries original logical tool call and key. |
| E25 | Worker crashes after external success, before local commit | Same-key downstream replay returns same result; one external effect. |
| E26 | Network timeout leaves external outcome unknown | Reconcile/retry same key; never generate a fresh key to hide uncertainty. |
| E27 | External permanent validation failure | Record failed action with sanitized reason; no automatic new proposal or key. |
| E28 | Lease expires while old worker is alive | Fencing prevents stale worker commits; downstream idempotency prevents duplicate effect. |
| E29 | Session expires before approval / UI closes after approval | New decision requires login; already committed approval/job survives browser state. |
| E30 | DB unavailable during approval enqueue | Atomic rollback; no approval-without-job; retry original idempotency key. |
| E31 | One evaluation case fails or malformed case exists | Report failure/error explicitly; continue independent cases; do not silently skip. |
| E32 | Evaluation overlaps user work | Isolated evaluation namespace/mock effects; no mutation of live demo tickets/actions. |
| E33 | Oversized ticket/document or HTML/script content | Validate import/body size, bound model context, render as escaped text; no browser script execution. |
| E34 | Stale triage/draft shown after source edit | Flag stale artifact; regenerate before action proposal; retain historical trace. |
| E35 | Generic refusal has no policy claim | Empty citations allowed and labeled safe escalation; do not fabricate evidence for coverage. |
| E36 | Real secrets appear in imported data or provider error | Reject/redact sensitive content before model/log/UI exposure; store only sanitized diagnostics. |

Set API JSON body limit to 256 KiB, source document limit to 5 MiB and draft length limit to 8,000 characters for V1. Reject excess explicitly rather than silently truncating eligibility context. If real supplied inputs exceed these defaults, revise limits and tests together before import. Long policy documents are chunked; retrieval budgets never authorize ignoring conflicting evidence.

## Implementation roadmap update

Follow [phase progress](phase-progress.md) and [source provenance](source-provenance.md). Verified capstone requirements override earlier illustrative examples. Only refund review is executable; its payload includes amount and idempotency_key. Mock AI results do not establish live-model quality.

## Execution evidence

See [verification](reports/verification.md) for measured checks and [tests](testing-and-evaluation.md) for requirement mapping. Provider input masking and instruction detection use heuristics; this list is not a claim of comprehensive adversarial robustness. Exactly-once behavior requires the downstream idempotency contract.
