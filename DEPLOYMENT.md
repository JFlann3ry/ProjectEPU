# Deployment Guide

Options: Docker or systemd + Nginx. Include healthchecks, environment, and basic recovery steps.

## Docker (recommended for repeatable deployments)

Build and run:

```powershell
docker build -t epu:latest .
docker run -p 4200:4200 --env-file .env epu:latest
```

Healthcheck example (Dockerfile):
```
HEALTHCHECK --interval=30s --timeout=5s CMD curl -f http://localhost:4200/health || exit 1
```

## Systemd + Nginx
- Place project at `/opt/epu`, create a venv and install requirements.
- Use `deploy/epu.service` as template; ensure `EnvironmentFile=/etc/epu/.env` is created.
- Nginx config: reverse proxy to `http://127.0.0.1:4200`, add security headers.

## Backups
- DB: scheduled SQL Server backups, retain according to policy.
- Storage: sync `storage/` to object storage or backup host; verify restores periodically.

## Rollback
- Keep DB migrations reversible where possible; snapshot DB before destructive changes.

## Notes
- Prefer using a secrets manager in prod; `.env` is for dev and quick deployments only.
