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

## Free-host profile checks

The user selected Render Free + Neon Free instead of Railway. Root Docker image built successfully. Three supervisor/configuration tests passed. Full HTTP flow and 8/8 supplied mock cases passed with the container constrained to 512 MiB and 0.1 CPU, using a separate local schema. [Resource sample](free-container-resources.json) and [HTTP results](free-container-smoke.json) record actual observations; the memory sample is not a measured peak. Cold start under hard CPU throttling took several minutes. Neon staging PG17 migration, explicit import and approved-policy indexing passed. No hosted application acceptance is claimed yet. The new image build reported 16 moderate development dependency advisories; runtime audit remains gated by CI.

## Actual free staging verification

Render Free staging is live at https://trustdesk-staging-praveen202105.onrender.com. Deployed revision e4ce9068e13f188cadba0c1d2700c3a136ee6625 matched health and green main CI 41310143143. Four hosted browser tests passed in 26.2 seconds. Full HTTP flow, cited drafts, approval replay and supplied mock evaluation 8/8 passed. An instance restart preserved review_dbbaca21-3ea0-406d-843c-7d2bb572408d and one mock effect. A pure-triage job with an expired lease succeeded on attempt two under the deployed worker. Secure/HttpOnly/SameSite=Strict cookies, foreign-Origin rejection and focused recent-log secret scan passed. Initial provider log retrieval returned 503; retry succeeded. Neon PG17/vector 0.8.0/migration 004 and data counts verified. A custom-format backup was restored to an isolated local PG17 database and checked. No active database was overwritten. Application rollback and production are still pending. See the staging and Neon JSON reports in this directory.

## Staging acceptance gate complete

Candidate 427966047682ab090656426a8af84617af13b3ab passed main CI 41311034950 and actual staged HTTP/evaluation tests, rollback to e4ce9068e13f188cadba0c1d2700c3a136ee6625, and restoration to the candidate. The same review ID and authenticated session survived. Final database check: 68 successful jobs, none queued/running/failed, exactly one mock effect; PG17/vector 0.8.0/schema 004. Recent log scan passed after final restore. The rollback used compatible documentation-only revisions, not a destructive database downgrade. Production promotion remains pending.
