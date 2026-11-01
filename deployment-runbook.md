# Deployment runbook

Target: Railway project TrustDesk; staging and production isolated environments. Services: web, api, worker, mock-actions, PostgreSQL with vector capability. Only web is public. Mock AI is clearly labeled and uses no paid key.

Preflight: authenticate Railway, verify workspace/project, verify PostgreSQL vector extension availability without changing extension configuration, verify billing access without upgrading a plan. Use stable bundled Node runtime if host Node fails.

Staging follows green main CI with Railway Wait for CI enabled. API migration runs before API activation under a database advisory lock; use compatible additive migrations. Worker rollout waits for migration completion. Initial seed and indexing are explicit, idempotent commands, never unconditional startup jobs.

Production deploys the exact staging-tested revision. Verify login, ticket detail, triage, citations, human approval, evaluation, persistence and worker health. Record URLs, deployment IDs and commit. Tag v1.0.0 only after success. Keep prior application revision for rollback; no automatic destructive schema downgrade. Verify recoverable backup before schema changes.

Credentials stay in Railway variables. No public API/DB/mock-action endpoints. See phase-progress.md for actual deployment status; this runbook alone is not deployment evidence.
