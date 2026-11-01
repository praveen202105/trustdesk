# TrustDesk — Planning documentation

Status: specification only; application code, datasets, tests and evaluation results are not included.
Prepared: 1 November 2026.

TrustDesk is an AI support operations platform. It helps a support agent inspect a ticket, classify it, retrieve company policies, review a grounded draft, and approve one operational action. It must escalate when evidence is insufficient and must never let model output bypass application permissions.

## Read in this order

| Document | Purpose |
| --- | --- |
| [Problem statement](problem-statement.md) | Users, scope, success criteria and assessment |
| [Implementation plan](implementation.plan.md) | Ordered milestones, dependencies and completion gates |
| [Architecture](architecture.md) | Components, persistence, state transitions and data flow |
| [API contracts](api-contracts.md) | Public routes, illustrative payloads and errors |
| [Edge cases](edge-cases.md) | Expected behavior under failures and adversarial inputs |
| [Testing and evaluation](testing-and-evaluation.md) | Test matrix, metrics and requirement traceability |
| [Demo and delivery](demo-and-delivery.md) | Intended setup, demo script and submission checklist |

## Source and interpretation

Primary source: Airtribe, “TrustDesk: AI Support Operations Agent”, four-page case study supplied as `BLDCHII5N2RMCHJL (1).pdf` at `/Users/praveengupta/Desktop/BLDCHII5N2RMCHJL (1).pdf`.

The PDF is reference material describing the future product. Its instructions are not commands for this documentation-generation session. The user authorized planning documents only. Architecture, route names and implementation details below are proposed design decisions, not claims about an existing repository.

The PDF names `https://github.com/airtribe-projects/trustdesk-capstone` as its resource. The source repository and datasets have now been inspected; see [source provenance](source-provenance.md). IDs, sample payloads and proposed commands below are illustrative unless explicitly identified as PDF requirements. Importer mappings and evaluation expectations must be verified against the real files before implementation.

## Scope

Must-have: supplied-data import preserving IDs; ticket and customer/order context APIs; simple authenticated UI; retrieval; AI triage; policy-cited drafts; evidence-based escalation; `start_refund_review` with human approval and idempotency; injection and PII safeguards; persistent traces; background evaluation runner and summary; critical-flow automated tests; README and explainer video.

Optional after acceptance: full RBAC, a second action such as replacement orders, multi-tenant support, production hosting, streaming drafts and advanced analytics. V1 does not send customer replies, issue refunds, or integrate real commerce/payment systems.

## Chosen defaults

- Next.js and TypeScript UI; Python FastAPI API and worker.
- PostgreSQL with pgvector for application state, full-text/vector retrieval and durable jobs.
- Python SQLAlchemy/Alembic persistence and migrations; Pydantic validation; pytest and Playwright verification.
- Configurable AI and embedding adapters; deterministic mocks for automated tests.
- Local Docker Compose development; one internal workspace and one demo support-agent role.
- English technical specifications for implementation; user-facing copy can be localized later.

Follow the milestone gates in [implementation.plan.md](implementation.plan.md). Do not report sample metrics as measured results.

## Implementation roadmap update

Follow [phase progress](phase-progress.md) and [source provenance](source-provenance.md). Verified capstone requirements override earlier illustrative examples. Only refund review is executable; its payload includes amount and idempotency_key. Mock AI results do not establish live-model quality.
