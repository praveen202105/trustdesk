# Release candidate verification

Measured locally on 2026-11-01; Railway deployment remains pending Phase 10.

- Backend: Ruff clean; mypy 19 modules clean; 41 PostgreSQL-backed tests passed. Includes concurrent approval, downstream replay, stale-worker fencing, database-outage retry, label isolation and evaluation denominator tests.
- Browser: 4 Playwright tests passed (login/context/search/logout; triage/citations/approval; escaped customer HTML; evaluation report).
- Frontend: lint, TypeScript and production build passed. Production dependency audit: 0 findings. Development toolchain audit: 14 moderate findings associated with the compatibility-pinned ESLint 9 toolchain; these are not represented as a clean full dependency audit.
- Docker: backend and frontend builds passed; all six Compose services started (migration exits successfully). Public-proxy HTTP workflow passed, including authenticated approval and all eight supplied evaluations.
- Recovery: application restart and database restart preserved the same proposal and downstream review; one mock effect persisted. Worker remained running and completed new jobs after database restart.
- Mock evaluation: 8/8 supplied cases passed, no errors or skips; allowed-action recall 7/7, answer requirements 22/22. See evaluation.mock.json for exact denominators, corpus/source fingerprints and limitations.

## Evidence

- [Initial HTTP smoke](compose-smoke.json)
- [Application restart smoke](compose-restart-smoke.json)
- [Database restart smoke](compose-database-restart-smoke.json)
- [Supplied mock evaluation](evaluation.mock.json)

## Limits

Default AI and embeddings are deterministic mocks. No real-provider quality, paid API usage, or production deployment is claimed by this report. Citation-reference validity and heuristic requirement coverage do not prove semantic grounding. PII masking is heuristic. Only start_refund_review executes, against an isolated mock service; no money moves. Demo shared-token sessions are not production RBAC. FastAPI test client emits one upstream deprecation warning; tests pass.

## Railway preflight

Authentication succeeded. Project creation was rejected on 2026-11-01 because the workspace trial expired. Read-back found no TrustDesk project. No billing change or hosted verification occurred. Staging and production remain pending.
