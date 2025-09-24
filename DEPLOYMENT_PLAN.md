# Deployment Plan for ProjectEPU

This document outlines a practical plan to get ProjectEPU live in production: recommended hosting options, services, deployment steps, security and monitoring, and a checklist of required artifacts. Use this as a living guide — adapt choices to your budget, operational comfort, and anticipated traffic.

## Goals
- Run the FastAPI backend securely and reliably
- Host static assets (JS/CSS/images) using a CDN for speed
- Provide durable object storage for uploads (S3-compatible)
- Use a managed relational database with backups and migrations
- Provide CI/CD with automated tests, builds, and deployments
- Monitor, log, and alert for errors and outages

---

## Architecture overview (recommended)
- Application: FastAPI (uvicorn + Gunicorn or use uvicorn with process manager)
- Reverse proxy / TLS: Managed load balancer (ALB, Cloud Run HTTPS, or Cloud Load Balancer)
- App hosting: Container-hosted service (ECS/Fargate, GKE Cloud Run, or DigitalOcean App Platform)
- Static assets: S3 + CloudFront (or equivalent) for caching
- Object storage: S3 (AWS) or DigitalOcean Spaces / Backblaze B2 with CDN
- Database: Managed Postgres (RDS/Aurora, Cloud SQL, DigitalOcean Managed DB)
- Cache / Tasks: Redis (ElastiCache or managed Redis) and Celery or RQ for background jobs
- Migrations: Alembic via CI/CD or run as part of deployment
- Worker jobs: Container tasks for background jobs (data export, thumbnailing)
- Logs/Monitoring: CloudWatch / Stackdriver + Sentry + Prometheus/Grafana
- Secrets: AWS Secrets Manager / Parameter Store or HashiCorp Vault

---

## Hosting options (high level)
Pick one stack based on team familiarity and budget.

1) AWS (recommended for scale)
- App: ECS Fargate or EKS + Horizontal Autoscaling
- DB: RDS Postgres
- Storage: S3 + CloudFront
- Redis: ElastiCache
- CI/CD: GitHub Actions -> ECR -> ECS deploy, or CodePipeline
- Pros: Highly scalable, many managed services
- Cons: Cost complexity, steeper learning curve

2) Google Cloud (simple managed services)
- App: Cloud Run (serverless containers) or GKE
- DB: Cloud SQL (Postgres)
- Storage: Cloud Storage + Cloud CDN
- Redis: Memorystore
- CI/CD: GitHub Actions -> Cloud Run or Cloud Build
- Pros: Simple serverless experience with Cloud Run
- Cons: Regional locking, pricing differences

3) DigitalOcean (developer-friendly / lower cost)
- App: App Platform or Kubernetes (DOKS) or Docker Droplets
- DB: Managed Postgres
- Storage: Spaces (S3-compatible) + CDN
- Redis: Managed Redis
- CI/CD: GitHub Actions -> Docker image -> deploy
- Pros: Lower cost, simpler UI
- Cons: Less enterprise-level features, scaling limits

4) Fully-managed PaaS (best for minimal ops)
- Platform.sh, Render, Fly.io, Railway
- Deploy container (or directly from repo) and use managed Postgres + object storage
- Pros: Very fast to get running
- Cons: Less control, potential vendor lock-in

---

## Detailed required components
- Container registry (ECR / GCR / Docker Hub) for images
- CI pipeline (GitHub Actions) with steps:
  - Run lint and tests
  - Build image and push to registry
  - Run DB migrations against a staging DB
  - Deploy to staging/production
- Kubernetes manifests or ECS Task definitions / Cloud Run containers
- NGINX or managed LB + TLS termination (Let's Encrypt via cert-manager or managed certs)
- Postgres DB with automated daily backups and point-in-time recovery
- Redis for ephemeral caches and background queues
- Object storage with public/secure buckets for user uploads
- Domain name plus DNS records and CDN configuration
- Monitoring & alerting (Sentry for errors, Prometheus/Grafana for metrics)
- Logging aggregation (CloudWatch / Stackdriver / ELK)

---

## Suggested deployment steps (fast path)
1. Prepare repo artifacts
   - Ensure `Dockerfile` builds the app producing a runnable container
   - Ensure `requirements.txt` or `pyproject.toml` is up-to-date
   - Add small `healthz` endpoint for load balancer checks
2. CI setup
   - Add GitHub Actions workflow to run tests and build image
   - Workflow pushes image to registry on `main` or on merge
3. Provision infra (quick start)
   - Create a managed Postgres instance
   - Create an S3 bucket (or Spaces) for uploads
   - Create a Redis instance (ElastiCache or managed Redis)
   - Configure IAM/service principals for the app to access buckets and DB
4. Deploy app
   - Deploy image to chosen runtime (Cloud Run, ECS Fargate, Render)
   - Ensure env vars are configured: DB URL, S3 creds, SECRET_KEY, STRIPE keys, etc.
   - Point domain and enable CDN
5. Run DB migrations
   - Run Alembic to apply pending migrations
6. Smoke tests
   - API health checks
   - Try a minimal user flow: login, create event, upload photo, request export
7. Monitoring & backups
   - Wire Sentry and basic metrics
   - Configure daily DB backups and retention
8. Go live
   - Remove maintenance flag, open DNS to traffic, watch for errors

---

## Security checklist
- Use TLS for all web endpoints (Cloud CDN / ALB with managed certs)
- Store secrets in a secrets manager (do not commit keys)
- Run containers with a non-root user where possible
- Set up firewall rules / security groups to restrict DB access to app only
- Enable automatic OS/container patching where possible
- Regularly rotate keys (Stripe, email API)
- Use CSP headers and prevent open redirects

---

## Performance & cost optimizations
- Serve JS/CSS/images from S3 + CDN
- Generate thumbnails and store them (rather than resizing on the fly)
- Use pagination / infinite scroll for galleries (don't load everything)
- Use Redis to cache frequent queries
- Use autoscaling with sensible limits

---

## Migration and release plan
- Create a staging environment with identical services
- Test alembic migrations against staging DB
- Use feature flags for risky features
- Do canary or blue-green release if possible

---

## Operational runbook (minimal)
- How to scale the app: increase task count or replicas
- How to restore DB from backups
- How to rotate secrets
- How to roll back a release (re-deploy previous image)
- How to investigate errors (Sentry + logs)

---

## Deliverables checklist
- [ ] Docker image builds locally and on CI
- [ ] GitHub Actions workflow for build/test/deploy
- [ ] Production Postgres with backups
- [ ] Object storage bucket + CDN
- [ ] Redis instance for cache/queue
- [ ] Sentry integrated
- [ ] Monitoring dashboards
- [ ] Runbook and rollback plan

---

## Quick decision guide
- Small team, limited ops: Render or Fly.io for app + managed Postgres + Spaces
- Larger scale or enterprise: AWS ECS/EKS + RDS + S3 + CloudFront

---

## Next steps I can take (I can do these for you)
- Create a GitHub Actions CI workflow that runs lint/tests and builds/pushes Docker image
- Add a small `healthz` endpoint and a production `docker-compose.yml` for local testing
- Create Terraform snippets for AWS or DigitalOcean resources
- Wire a sample Sentry integration and a Grafana dashboard for request latency

If you want, I’ll generate a concrete `github/workflows/ci.yml` and a starter `deploy` workflow for your preferred host.
 
## Estimated monthly costs (rough)

These are ballpark monthly ranges for planning only. Actual costs vary with traffic, storage, backup retention, CDN egress, and SLA choices. Assumes a small-to-moderate production workload (tens of thousands of requests/month), ~100GB of object storage, managed Postgres, and light background workers.

1) AWS (recommended for scale)
- Small / PoC: $80 — $250 / month
   - Example breakdown: ECS Fargate (1–2 small tasks) $20–$80, RDS db.t3.small $30–$60, S3 + CloudFront $5–$30, ElastiCache small $15–$40, monitoring/logging $10–$40
- Medium / production-ready: $500 — $2,000+ / month
   - Add multi-AZ RDS, larger instances, higher CloudFront egress, autoscaling, and additional instances

2) Google Cloud
- Small: $70 — $220 / month
   - Cloud Run small services $20–$80, Cloud SQL small instance $30–$70, Cloud Storage + CDN $5–$30, Memorystore $10–$40
- Medium: $400 — $1,500+ / month

3) DigitalOcean (developer-friendly / lower cost)
- Small: $40 — $120 / month
   - App Platform or small Droplet $5–$40, Managed Postgres $15–$50, Spaces + CDN $5–$20, Managed Redis $10–$20
- Medium: $150 — $600 / month

4) Fully-managed PaaS (Render / Fly / Railway)
- Small: $15 — $80 / month
   - One small service instance, managed DB $15–$50, modest bandwidth
- Medium: $100 — $400 / month
   - Multiple instances, higher DB tiers, additional addons

Notes:
- Egress (CDN/bandwidth) is often the largest variable — use caching to reduce costs.
- Backup retention, PITR, multi-AZ and higher SLA levels increase costs.
- These estimates exclude enterprise support and large-volume egress.
