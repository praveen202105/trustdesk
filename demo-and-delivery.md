# Demo and delivery

This is a runbook contract for future implementation. Commands, paths, module names and environment variables below are proposed interfaces; they do not exist in this documentation-only folder yet. Final application README must replace placeholders with verified commands.

## Local setup contract

Use Docker with Compose to run `db`, `api`, `worker`, `web` and mock provider/action services. Include a Dockerfile for each custom service, lockfiles, migrations, health checks and an `.env.example` with placeholders. Pin compatible runtime/package versions during M0; the PDFs do not specify versions.

| Variable | Purpose |
| --- | --- |
| DATABASE_URL | PostgreSQL connection; never expose to browser |
| DEMO_LOGIN_TOKEN | Local login credential; no hard-coded public credential |
| SESSION_SECRET | Session signing secret |
| AI_PROVIDER / AI_MODEL | `mock` or selected live adapter and model |
| AI_API_KEY | Live provider credential; server only |
| EMBEDDING_PROVIDER / EMBEDDING_MODEL | Adapter/model matching vector index metadata |
| EMBEDDING_API_KEY / EMBEDDING_DIMENSION | Provider credential and verified index dimension |
| MOCK_ACTION_BASE_URL | Local idempotent action service |
| DATA_DIR | Location of verified supplied dataset |
| APP_ORIGIN / API_INTERNAL_URL | Browser origin and server proxy target |
| TRACE_RETENTION_DAYS | Default 30-day local retention |

Proposed commands, to be implemented and verified:

```sh
cp .env.example .env
# Set local secrets and point DATA_DIR at the actual supplied dataset.
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api python -m trustdesk.cli import-data --directory /data
docker compose exec api python -m trustdesk.cli index-knowledge
docker compose exec api python -m trustdesk.cli evaluate --suite provided --output /reports/evaluation.json
docker compose exec api pytest
docker compose exec web npm run test:e2e
```

Compose must mount the source data read-only at `/data` and a writable report directory at `/reports`. Document browser URL, first login, reset procedure, clean shutdown and schema migration. Mock mode must not require a paid AI key. Reset commands that delete data must be labeled destructive and never run as part of normal startup.

## Reproducible demo script

Select actual supplied ticket IDs after inspecting data; do not use illustrative IDs as if they exist. Reset only the isolated demo/evaluation environment.

1. Show login and ticket list; open a ticket with linked customer/order information.
2. Trigger triage and show category, priority, escalation decision and trace.
3. Generate a supported draft and open each policy citation to its versioned excerpt.
4. Show proposed `start_refund_review` arguments and policy evidence. Demonstrate that no execution occurs before approval.
5. Approve; show the persisted human decision and completed mock review reference. Retry/double-click and show one external effect.
6. Reject a separate proposal and show no downstream action.
7. Show unsupported/conflicting evidence escalation and an account-security identity-bypass request.
8. Show the hidden-coupon injection, unsafe KB document and prompt/secret disclosure cases; inspect sanitized guardrail traces.
9. Run the supplied evaluation flow; show metrics, denominators, failed cases and runtime mode.
10. Demonstrate slow-provider responsiveness and a worker crash/recovery test; distinguish planned evidence from recorded results.

Do not show live credentials, customer PII or hidden system prompts in the video. Use mock data and visibly identify mock versus live inference.

## Verification report template

- Commit/repository URL, environment, date and setup command results.
- Imported source counts, source hashes and preserved-ID checks.
- Test commands, pass/fail totals and logs with secrets redacted.
- Evaluation case count, completed/errored/skipped counts, category/priority accuracy, citation coverage/validity, unsafe blocking and escalation matrix.
- Provider/model/prompt/embedding versions and mock/live mode.
- Approval/idempotency evidence: proposal, decision, retries and independently observed downstream count.
- Recovery evidence: crash boundary, original key replay, final state and external reference.
- Known failures, design tradeoffs, policy ambiguities and remaining limitations.

All fields start as “not run” or “not available”; fill them only from real execution.

## Final submission checklist

- [ ] Functional application with all R01–R14 requirements verified.
- [ ] README with setup, APIs, architecture, decisions, evaluation flow and limitations.
- [ ] Public GitHub repository link, checked for secrets and private customer data before publication.
- [ ] Seeded/mock demo instructions using actual source IDs.
- [ ] Explainer video covering triage, cited drafts, human approval, guardrails and evaluations.
- [ ] Evaluation summary with the required metrics and disclosed failures.
- [ ] Automated-test and recovery evidence; no unverified claims of production readiness.

Publishing a repository, uploading a video or deploying a service is outside this documentation task. Prepare reviewable artifacts first and use the user's applicable authorization for any later external publication.
