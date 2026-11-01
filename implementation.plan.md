# Development through deployment

Each phase is gated by implementation → relevant local tests/regressions → commit/push → PR CI → merge → main CI → evidence commit. Failed checks must be fixed on the phase branch; do not advance by bypassing CI.

| Phase | Scope | Implementation | Acceptance checks |
| --- | --- | --- | --- |
| 00 | Source and docs | Validate source pack, preserve IDs, establish PR/CI gates | Source validator, docs links and credential review |
| 01 | Foundation | Next.js/FastAPI, dependencies, Compose and CI | Lint, types, build, API health |
| 02 | Persistence | Migrations and atomic source import | Fresh migration, reimport, ownership/rollback checks |
| 03 | Ticket workspace | Session login, ticket/context APIs and UI | Auth/Origin, pagination, browser login/search/sign-out |
| 04 | Durable jobs | Worker, leases, retry bounds and adapters | Concurrent claims, fencing, recovery and completion |
| 05 | Retrieval | Approved versions, full-text/pgvector ranking and citations | Index freshness, excerpts, historical policy boundaries |
| 06 | Triage and drafts | Typed model output, grounded templates, traces and UI | Schema repair, escalation, browser citations, stale selection race |
| 07 | Human-approved action | Proposal, human decision, idempotent mock effect | Zero unapproved effects, decision conflicts, crash-after-success replay |
| 08 | Safety | Injection/PII protection, request limits, errors and tool permissions | Adversarial cases, HTML escaping, blocked-provider responsiveness |
| 09 | Release candidate | Evaluation child jobs, reports, runtime docs and containers | Full regression, all supplied cases, image builds and Compose smoke |
| 10 | Staging | Render Free supervised processes, private ports, Neon Free data, secrets and explicit migration/seed | Hosted smoke, worker/restart persistence, logs and rollback rehearsal |
| 11 | Production | Promote tested revision, tag, docs and handoff | Production smoke, version/persistence checks and final evidence |

Actual commit SHAs, PRs, test results and completion status belong in [phase-progress.md](phase-progress.md). Deployment-specific evidence belongs in [deployment-runbook.md](deployment-runbook.md). See [architecture](architecture.md), [APIs](api-contracts.md), [edge cases](edge-cases.md) and [testing](testing-and-evaluation.md) for behavior contracts.

Use `phase/NN-description` branches with meaningful implementation/fix commits. Public source contains no real secrets. Staging follows green main CI; production is an explicit promotion of the exact staging-tested application revision. Documentation-only evidence commits may be newer than the deployed code; record the deployed SHA rather than claiming HEAD is deployed.
