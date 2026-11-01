# Free demo deployment: Render + Neon

The user selected free hosting instead of Railway on 2026-11-01. Railway requires a paid plan on the connected account; no upgrade was made. The supported free profile keeps the application code and PostgreSQL contracts and changes its deployment footprint.

## Footprint

A Render **Free web service** runs four supervised child processes: Next.js, FastAPI, the PostgreSQL job worker and isolated mock-actions HTTP service. Only Next.js binds the public port; API and mock-actions bind loopback. The [root Dockerfile](Dockerfile) packages this profile. The supervisor exits if any child exits and terminates/reaps all children on shutdown. All migrations complete before any server starts. No data is automatically imported on startup.

Neon **Free PostgreSQL 17** stores records and pgvector data outside the ephemeral Render container. Staging and production use separate Neon projects, separate Render services and separate session/action/login secrets. The existing [Compose deployment](compose.yml) retains separate containers for local development.

The Render instance has 512 MB RAM and 0.1 CPU. It sleeps after 15 minutes without inbound traffic and resumes on a visit; cold starts take time. Workers pause while the instance sleeps; persisted jobs resume on wake and expired leases are reclaimed. It is a demo deployment, not an always-on production service. No artificial keep-alive requests are configured.

Free usage limits apply: Render currently includes 750 running instance hours per workspace/month; both environments share this quota. Neon currently includes 100 CU-hours/month and 1 GB storage per project, with plan-default scale-to-zero. Keep accounts on their free plans and do not add a payment method or paid resources. If capacity is exhausted, accept service suspension instead of upgrading automatically. Use on-demand staging so it consumes minimal runtime.

Sources verified 2026-11-01: [Render free limitations](https://render.com/docs/free), [Render compute plans](https://render.com/docs/compute-plans), [Neon pricing](https://neon.com/pricing).

## Provision and seed

1. Authenticate Render and Neon through their CLI browser flows; confirm workspace/organization. Never print CLI credentials. Inspect existing resources before creating new ones.
2. Create a free Neon staging project in Singapore on PG17 at 0.25 CU. Capture its TLS connection string privately. Run `python -m trustdesk.manage`, then explicit `python -m trustdesk.cli import-data` and `python -m trustdesk.cli index-knowledge` against that database from the local backend environment. Validate counts and vector extension. Repeat separately for production only after staging passes.
3. Create a mode-0600 JSON string map outside the repository containing DATABASE_URL, APP_ORIGIN (actual HTTPS origin), unique DEMO_LOGIN_TOKEN, SESSION_SECRET and MOCK_ACTION_SECRET; SECURE_COOKIES=true; AI_PROVIDER=mock; AI_MODEL=mock-policy-v1; EMBEDDING_PROVIDER=mock; EMBEDDING_MODEL=mock-hash-v1; EMBEDDING_DIMENSION=64. Do not share this file or commit it.
4. After PR and main CI pass, create a Render web service with runtime docker, root Dockerfile, plan free, Singapore region, health path `/api/v1/health`, GitHub main source and automatic deployment disabled. Supply the private JSON as secret file `trustdesk.json`; the supervisor loads `/etc/secrets/trustdesk.json` without printing it. CLI `--secret-file trustdesk.json:ABSOLUTE_PRIVATE_PATH` transmits this secret without placing values in arguments. Verify the returned URL matches APP_ORIGIN; correct configuration before allowing login if it differs.
5. All releases use an explicit green CI commit via `render deploys create SERVICE_ID --commit FULL_SHA`. Never deploy an arbitrary newer main revision. The supervisor exports Render's actual Git commit as the health/trace revision. Record service/deployment IDs and revision.

## Acceptance and recovery

Run the existing authenticated [HTTP smoke](scripts/smoke_http.py) against the HTTPS URL with its demo token supplied through process environment. Verify 8 tickets, source-linked context, background triage, valid billing citations, human-approved review, repeated idempotency key and all eight mock evaluation cases. Run browser checks on the live URL and verify secure session cookies. Confirm production service ID and database project differ from staging.

Restart the service and repeat smoke; the same review ID and one mock effect must persist. Inspect worker health, completed jobs and sanitized logs. Since free Render has no SSH or one-off jobs, seed, index, database verification and backup commands run locally against TLS Neon connections; do not expose a new admin web endpoint.

Before schema changes, take a PostgreSQL 17 custom-format dump through a private connection. Restore that dump into a disposable local database, compare counts and review IDs, and protect backup files outside source control. Rehearse application rollback in staging by deploying a prior successful compatible revision and returning to the tested candidate. Never downgrade or restore destructively over the active database. A staging-tested commit alone is eligible for production promotion. Tag v1.0.0 only after production checks pass.

## Actual evidence

Staging is live at https://trustdesk-staging-praveen202105.onrender.com on Render plan `free`, service `srv-dbjjncg473hc73a2b1u0`, tested commit `e4ce9068e13f188cadba0c1d2700c3a136ee6625`. Four hosted browser tests and the full HTTP workflow passed, including 8/8 mock evaluations. Restart replaced the instance, preserved the same review and one effect, and the worker reclaimed a deliberately expired pure-triage lease. Secure cookie flags and foreign-Origin rejection passed. Recent provider logs contained none of the configured secret values. Rollback rehearsal passed: candidate `427966047682ab090656426a8af84617af13b3ab` → baseline `e4ce9068e13f188cadba0c1d2700c3a136ee6625` → candidate. Each revision passed HTTP/evaluation and preserved the same review; a signed session also survived release replacement. The candidate is eligible for production promotion. These compatible revisions differ in documentation, so this verifies release mechanics without claiming compatibility for arbitrary future schema changes. Production remains pending. See [phase progress](phase-progress.md) and [verification](reports/verification.md). Provisioned staging database: `polished-wildflower-00057496` (Neon, PG17, Singapore); explicit migration/import/index succeeded with 6 customers, 6 orders, 8 tickets, 8 documents and 7 approved chunks. This database initialization alone is not a completed application deployment.

## Production delivery complete

Production: https://trustdesk-praveen202105.onrender.com — Render service `srv-dbjjvnfb9u1s73e8q920`, plan `free`, Neon project `patient-band-83922454` (PG17/vector 0.8.0/schema 004). Runtime source is staging-tested commit `427966047682ab090656426a8af84617af13b3ab` on pinned branch `release/v1.0.0`; automatic deploys are off. Deploying a new runtime requires successful CI and staged verification before an explicit promotion.

Four production browser tests and full HTTP flow passed, including mock evaluation 8/8. Restart replaced the instance and preserved the signed session and review `review_4af993b9-7e29-4cd5-a9ce-77998155828f`; one effect and 35 successful jobs were verified. Expired-lease recovery, secure cookie/Origin checks, recent-log secret scan and cross-environment credential/cookie rejection passed. A separate production backup was restored into an isolated local PG17 database before release.

The browser approval scenario was run against the fresh production seed. Repeat production verification uses the idempotent HTTP smoke to reuse its persisted review. Do not erase audit records or reset production just to repeat a write-path browser case; use a fresh isolated staging dataset instead. Local and CI browser tests use disposable schemas.

See [release evidence](reports/release-verification.json). Hosted demo credentials are supplied privately outside Git. Free limits and mock/provider caveats above still apply.
