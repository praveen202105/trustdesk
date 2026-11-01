# Problem statement

## Problem and audience

Support agents repeatedly investigate shipping, refunds, warranties, billing and account-security tickets. They must combine policy documents with customer and order context, distinguish supported answers from guesses, and avoid unsafe actions. A fluent response alone does not solve that problem: the agent needs evidence, a reviewable recommendation and an audit trail.

Primary user: an internal support agent who reviews tickets and approves refund-review requests. Secondary user: a reviewer who inspects traces and evaluation reports. Customers supply ticket content; they do not access the internal console in V1.

## Product outcome

Given an imported ticket, TrustDesk presents its linked context, classifies category and priority, retrieves relevant company policy, and generates a draft with document citations. When evidence is missing, policy conflicts, or account security is implicated, it escalates with a reason. If a refund review is appropriate, it proposes `start_refund_review`. An authenticated human reviews the proposal before the backend executes the permitted mock action exactly once per logical request through idempotency.

A refund review is a request for review, not an actual refund. Generated drafts remain internal until a person uses them outside this V1 product.

## Core user journey

1. Sign in to the local demo and select a ticket.
2. Inspect the original customer message and linked customer/order data.
3. Trigger triage; inspect category, priority, escalation decision and reason.
4. Generate a draft; inspect relevant policy excerpts and citation IDs.
5. Review an action proposal, approve or reject it, and inspect execution status.
6. Inspect the AI trace and run the supplied evaluation suite.

## Required behavior

- Import customers, orders, tickets, tool catalog, evaluation cases and knowledge documents without changing source IDs. Preserve IDs such as `KB-REFUND-001`.
- Use each ticket's `created_at`, never the current date, as the policy evaluation time. Interpret the actual policy's eligibility anchor and boundary explicitly; do not invent a return period.
- Categories: `shipping`, `refund`, `warranty`, `billing`, `account_security`, `general`. Priorities: `low`, `medium`, `high`, `urgent`.
- Ground customer-facing policy claims in retrieved documents. Refuse or escalate unsupported answers.
- Persist drafts, actions, approvals and minimum debugging traces.
- Treat customer messages and retrieved documents as untrusted content. The PDF identifies `KB-ADVERSARIAL-001` as intentionally unsafe.
- Require human approval before the single sensitive action. Retries must not create duplicate effects.
- Run AI and evaluation work without blocking unrelated API requests.

## Assessment and success

| PDF assessment | Weight | Evidence to submit |
| --- | --- | --- |
| Must-have workflow | 60% | Working import, APIs/UI, triage, cited drafts, approval action, traces and evaluation |
| AI quality and guardrails | 25% | Policy-grounded answers, valid citations, uncertainty escalation and adversarial-case handling |
| Engineering, documentation and demo | 15% | Maintainable implementation, reproducible setup, design rationale and full workflow video |

These weights come from the supplied PDF. It provides no universal accuracy cutoff. Project acceptance therefore requires every must-have capability to be demonstrated, all deterministic safety tests to pass, and actual evaluation metrics plus failures to be reported. Any AI-quality release threshold must be selected after inspecting the provided cases; do not silently drop failing cases.

## Boundaries

V1 is a single-workspace capstone with demo authentication and mock external actions. It excludes customer message delivery, real financial execution, full RBAC, production compliance certification and additional action types. Optional features do not compensate for missing must-haves.
