# TrustDesk

Evidence-led support operations with policy citations and human-approved refund reviews.

TrustDesk combines a Next.js workspace, FastAPI API, PostgreSQL/pgvector retrieval and durable background workers. The default demo uses deterministic mock AI and fictional Airtribe data. Live-compatible model and embedding adapters are optional. No actual payment, customer message or replacement order is sent.

## Run locally with Docker

Prerequisite: Docker with Compose. Ports 3000, 8000 and 5438 must be available on localhost.

```sh
cp .env.example .env
docker compose up -d --build
docker compose exec api python -m trustdesk.cli import-data
docker compose exec api python -m trustdesk.cli index-knowledge
```

Open http://localhost:3000 and use the local-only token `local-demo-only`, unless you changed `DEMO_LOGIN_TOKEN` in `.env`. Hosted deployments require unique secrets and secure cookies; these local defaults are rejected for HTTPS hosting.

The migration service waits for PostgreSQL and applies serialized Alembic migrations. Import/index are explicit commands, not recurring startup behavior. Reimporting unchanged source data preserves IDs and artifacts. Imports are blocked during an active evaluation. `docker compose down` stops services without deleting the named database volume. Do not use `down -v` unless you intentionally want to destroy local demo data.

## Try the workflow

1. Open `tkt_9008` (duplicate charge), triage it and generate a cited draft.
2. Open `KB-BILLING-001` from the draft and inspect the policy.
3. Prepare a refund review, inspect its amount/reason, and approve or reject it.
4. Inspect traces. A review request never means money has been refunded.
5. Open `tkt_9006` or `tkt_9007` to demonstrate injection/disclosure blocking.
6. Run the provided evaluation suite from Evaluations. The runner generates recommendations without executing tools.

Only `start_refund_review` is executable. Other catalog actions can appear as policy recommendations. Seed expected labels are stripped from runtime tickets and used only by the evaluator.

## Tests and measured evaluation

```sh
cd backend
uv sync --frozen
uv run ruff check .
uv run mypy trustdesk
uv run pytest
cd ../web
npm ci
npm run lint
npm run typecheck
npm run build
npx playwright install chromium
npm run test:e2e
```

Host-side tests need the local PostgreSQL service (`docker compose up -d db`). Stop local API/web containers before Playwright starts its own isolated servers: `docker compose stop api worker mock-actions web`. Browser tests create and clean a disposable schema; they do not write demo artifacts/actions. Python 3.12 and Node 24 are the tested development runtimes.

```sh
docker compose exec api python -m trustdesk.cli evaluate --suite provided --output /reports/evaluation.json
docker compose cp api:/reports/evaluation.json ./evaluation.json
```

See [measured mock evaluation](reports/evaluation.mock.json), [verification](reports/verification.md) and [phase evidence](phase-progress.md). Mock scores measure deterministic behavior on eight supplied cases; they do not establish live-model generalization or semantic grounding. Answer-requirement grading uses documented heuristics.

## Documentation

| Document | Purpose |
| --- | --- |
| [Problem statement](problem-statement.md) | Users, scope and assessment |
| [Implementation plan](implementation.plan.md) | Development through release phases |
| [Architecture](architecture.md) | Data flow, state machines and safety boundaries |
| [API contracts](api-contracts.md) | Implemented routes and payloads |
| [Edge cases](edge-cases.md) | Expected failure/adversarial behavior |
| [Testing and evaluation](testing-and-evaluation.md) | Requirement mapping and test strategy |
| [Demo and delivery](demo-and-delivery.md) | Reproducible demo and submission |
| [GitHub workflow](github-workflow.md) | Commit/PR/CI gates |
| [Deployment runbook](deployment-runbook.md) | Hosting, migrations, backup and rollback |
| [Source provenance](source-provenance.md) | Upstream revision and contract decisions |

Repository: https://github.com/praveen202105/trustdesk. Verified hosting details are recorded in the deployment runbook after deployment.

## Live mode and limits

Set `AI_PROVIDER=compatible`, `AI_BASE_URL`, `AI_MODEL` and `AI_API_KEY` for a Chat-Completions-compatible JSON provider. Live embeddings additionally require `EMBEDDING_PROVIDER=compatible`, `EMBEDDING_MODEL` and the exact `EMBEDDING_DIMENSION`, followed by explicit reindexing. Default mock embeddings are hashed token vectors, not a pretrained semantic model.

Customer emails, long numeric payment strings, labeled credentials and configured secrets are masked before live-provider input. Names/tracking numbers are omitted. This is heuristic protection, not a comprehensive PII classifier. Raw seed messages remain unchanged in the audit store.

V1 live drafts are restricted to reviewed policy templates; unreviewed paraphrases escalate. Full RBAC, multi-tenancy, actual commerce/payment integrations and production-scale load certification are outside this capstone. See the verification report for current limitations and dependency-audit evidence.
