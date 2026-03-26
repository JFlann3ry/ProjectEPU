# Deployment Guide

This is the canonical deployment and operations runbook for ProjectEPU.

Archived references:
- `docs/archive/AWS_DEPLOYMENT_GUIDE.md`
- `docs/archive/DEPLOYMENT_PLAN.md`

## Goals
- Deploy a secure and repeatable production stack.
- Keep deployment safety gates explicit and easy to automate.
- Provide a practical path from single-host deployment to managed cloud runtime.

## Architecture options

Choose based on budget and operations overhead.

1. Managed cloud (AWS/GCP/DO): container runtime, managed DB, managed cache, object storage, CDN.
2. Single host VM: systemd + reverse proxy, with external backup and monitoring.
3. PaaS: minimal ops with managed build/deploy.

For AWS-specific step-by-step provisioning, see `docs/archive/AWS_DEPLOYMENT_GUIDE.md`.

## Fast path checklist

1. Build artifact
- Verify container image builds locally.
- Ensure health endpoint responds on `/health`.

2. Provision dependencies
- Database (managed preferred).
- Object storage for uploads/static assets.
- Redis for cache/rate limits/queues if enabled.

3. Configure secrets and environment
- Store production secrets in a secrets manager.
- Set required env vars (DB, storage, base URL, secure cookies, secret key, email, Stripe).

4. Deploy app
- Roll out the new image/release to staging first.
- Run migrations and smoke tests.
- Promote to production.

5. Verify and monitor
- Confirm health endpoint and key user flows.
- Watch logs/errors/metrics for at least one full traffic cycle.

## Local container deploy

```powershell
docker build -t epu:latest .
docker run -p 4200:4200 --env-file .env epu:latest
```

Healthcheck example in Dockerfile:

```dockerfile
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:4200/health || exit 1
```

## Systemd + Nginx deploy

- Place project at `/opt/epu`, create a venv, and install requirements.
- Use `deploy/epu.service` as template.
- Ensure `EnvironmentFile=/etc/epu/.env` exists and is permission-restricted.
- Reverse proxy to `http://127.0.0.1:4200` and terminate TLS at Nginx or load balancer.

## Required production env baseline

- `BASE_URL=https://...`
- `COOKIE_SECURE=true`
- `DEBUG_ROUTES_ENABLED=false`
- non-default `SECRET_KEY`

If using managed storage/caching, configure:
- `REDIS_URL`
- provider credentials/roles and bucket names

## Pre-deploy safety gates

Run before restart/deploy:

```powershell
venv\Scripts\python.exe scripts\preflight_security.py --mode production
```

Expected: `status=ok`.

Run code quality gates:

```powershell
venv\Scripts\python.exe -m ruff check .
venv\Scripts\python.exe -m pytest -q
```

## Post-deploy verification

```powershell
curl http://localhost:4200/health
```

Validate:
- HTTPS is active.
- HSTS is present on HTML responses behind TLS/reverse proxy.
- Login, event creation, upload, and gallery access all succeed.

## Migrations and rollback

- Run Alembic migrations during release rollout.
- Snapshot DB before destructive changes.
- Keep migration revisions focused and reversible when possible.
- Roll back by redeploying previous artifact and, if required, downgrading schema.

## Maintenance jobs

Standalone runners:

```powershell
venv\Scripts\python.exe scripts\purge_payment_logs.py --retention-days 90 --batch-size 10000
venv\Scripts\python.exe scripts\cleanup_completed_exports.py --retention-days 30 --batch-size 1000
venv\Scripts\python.exe scripts\cleanup_stale_guest_sessions.py --retention-days 30 --batch-size 5000
```

Operational guidance:
- Use a large retention value first as dry-run behavior check in stage.
- Schedule off-peak.
- Keep batch sizes conservative to reduce lock contention.

## Backups and recovery

- DB: automated backups, tested restore procedure, and retention policy.
- Storage: periodic backup/replication and sampled restore checks.
- App config: secure backup of critical env/secrets metadata (not plaintext secrets).

## Monitoring and alerting

- Centralized logs with request correlation.
- Error tracking (for example, Sentry).
- Infra metrics and alarms (CPU/memory/latency/error rate/unhealthy hosts).
- On-call runbook for common failure modes.

## Cost planning (rough)

- Small managed stack: typically low hundreds USD/month.
- Cost drivers: DB tier, egress/CDN traffic, and always-on network components.
- Optimize with right-sized instances, cache/CDN hit rate improvements, and retention tuning.

## Related docs

- `README.md`
- `SECURITY.md`
- `TESTING.md`
- `docs/DOCS_INDEX.md`
