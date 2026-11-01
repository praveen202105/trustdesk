# Railway deployment runbook

## Actual status

Deployment is blocked before provisioning: on 2026-11-01 Railway rejected `railway init --name TrustDesk --workspace 4844be13-d59f-44a6-8201-37efbd4da160` with **Your trial has expired. Please select a plan to continue using Railway.** Read-back confirmed no TrustDesk project exists. Authentication works. No plan upgrade, payment, hosted database, or public URL was created. Phases 10 and 11 have not passed their acceptance gates.

[Service configuration](deploy/railway-services.json) and [private config generator](deploy/render_config.py) are prepared; the configuration has not been applied to Railway. The Docker equivalents have passed local testing. No hosted validation or rollback rehearsal is claimed.

## Prerequisites and scope

An active Railway workspace with deployment access is required. Do not upgrade billing without explicit authorization. Create a separate TrustDesk project, not services in HireLens AI or AskMyPolicy. Use stable bundled Node if the system runtime fails. Every Railway invocation uses `RAILWAY_CALLER=skill:use-railway@1.2.1` and the stable session `RAILWAY_AGENT_SESSION=railway-skill-trustdesk-implementation-20261101`.

Use explicit project, environment and service IDs from read-back. Commands below omit these telemetry prefixes for readability. Keep private inventory/config/archive files outside the Git repository. Never print resolved variable lists or private config files.

## Staging provisioning

1. Confirm `railway whoami --json` and `railway project list --json`; reuse only an existing project named TrustDesk if one was created during a prior attempt. Otherwise run the init command above. Record project ID.
2. Create an empty staging environment with `railway environment new staging`. Keep default production empty. Create five empty services: `Postgres`, `api`, `worker`, `mock-actions`, `web`. Resolve and record their IDs; do not set sources yet.
3. Attach a fresh volume to staging Postgres using `railway volume --project PROJECT --environment staging --service POSTGRES_ID add --mount-path /var/lib/postgresql/data --json`. Do not provision a TCP proxy or public domain for the database.
4. Create the web domain with `railway domain --project PROJECT --environment staging --service WEB_ID --port 3000 --json`. Only web receives a public domain. Record the HTTPS origin.
5. Create private inventory JSON mapping each of the five exact names to its service UUID. Generate a single config file using `python3 deploy/render_config.py --inventory /private/inventory.json --origin https://WEB_DOMAIN --revision FULL_GREEN_MAIN_SHA --environment staging --output /private/staging.json`. Output uses mode 0600 and refuses overwrite. Do not regenerate secrets while services are running.
6. Apply just the Postgres block from that private JSON with `railway environment edit --project PROJECT --environment staging --json` using subprocess stdin. Verify the fresh volume is attached, image is pgvector PG17, private database URL resolves, and the database deployment is healthy before applying remaining service blocks.
7. Apply the remaining four blocks using the same stdin mechanism. Full repository build context is required: do not set a backend/web root directory. Staging source follows main with `checkSuites: true` (Wait for CI). Read back source/build/deploy settings without printing variables. Verify a green main CI, not skipped/neutral checks.
8. Each backend deployment runs `python -m trustdesk.manage` before activation. Its bounded readiness check precedes serialized advisory-locked additive migrations. Worker and mock-actions run the same migration gate. Failed migration stops that release; never bypass it.
9. Explicitly seed once through API SSH: `railway ssh --project PROJECT --environment staging --service API_ID python -m trustdesk.cli import-data`, then `python -m trustdesk.cli index-knowledge` through the same SSH boundary. Startup never imports seeds automatically. Verify 6 customers, 6 orders, 8 tickets, 8 documents, 8 evaluation cases, and vector extension availability with read-only queries.

All backend services share per-environment session/action secrets; production gets different values. AI and embeddings default to mocks without a paid key. The Next.js server proxies `/api/v1` to private API; browser code receives no internal connection credentials. Backend binds dual-stack `::` and only web uses public ingress.

## Staging acceptance gate

Read the staging demo token privately from the generated config into `TRUSTDESK_ACCESS_TOKEN`; never add it to shell command text or public reports. Run `uv run --directory backend python ../scripts/smoke_http.py --base-url https://WEB_DOMAIN --approve --output ../reports/staging-smoke.json`. Verify actual health revision equals the green main commit, including after any evidence-only or documentation pushes.

Complete browser login → ticket → triage → cited draft → policy viewer → human approval → evaluation. Record actual 8-case results; default mock scores do not establish live AI quality. Inspect sanitized logs for secret exposure without printing credentials. Restart app services, then the database; repeat smoke, verify same downstream review ID, exactly one mock effect, persisted sessions/data and worker job recovery. Save sanitized evidence and deployment IDs in phase-progress.md.

Before schema changes, create a custom-format `pg_dump` inside the Postgres volume outside PGDATA. Protect backup access; do not expose a database port. Verify `pg_restore --list`, restore into a new throwaway verification database on staging, compare source counts and mock effect IDs, then remove only that disposable verification database. A dump that has never been restored is not a verified recoverable backup.

Rehearse application rollback in staging: record current and previous successful deployment IDs, redeploy the prior tested application revision, smoke-test against the unchanged additive schema, then restore the intended candidate and test again. Never automatically downgrade or destructively restore the active database. Record which exact source revision passed this rehearsal.

## Production promotion

Begin only after staging passes, including restart, backup restoration and rollback rehearsal. Instantiate the project-level services in the empty production environment (`isCreated: true` for new instances), attach a new Postgres volume and generate a fresh private production config. Do not duplicate staging volume IDs, sessions, secrets or action records. Source repo hooks are deliberately absent from production config; verify this by read-back.

Export the exact staging-tested commit using `git archive FULL_TESTED_SHA` into a separate clean directory. Apply production database settings first, verify readiness/backup, then application settings. Upload that immutable archive to each application service with `railway up --project PROJECT --environment production --service SERVICE_ID --detach -m "TrustDesk release FULL_TESTED_SHA"`. The generated REVISION is the tested commit. Seed/index explicitly only for a fresh database. Verify all four services' deployed revision, source archive and configuration match the candidate.

Repeat production smoke/browser/worker/persistence/log checks. Keep previous successful application deployment IDs for rollback; no destructive database downgrade. Only after success push `v1.0.0` pointing to the actual deployed commit. Handoff live URL, GitHub URL, revision/tag, actual reports, limitations and privately delivered demo token. Later documentation-only commits may follow the release tag without changing production.
