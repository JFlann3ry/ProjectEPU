# Documentation Index and Consolidation Map

Status: Active
Last updated: 2026-03-26

This file is the single navigation and consolidation map for project documentation.

## Canonical Docs (Primary Source of Truth)

- Product and project overview: README.md
- Contributor workflow and rules: CONTRIBUTING.md
- Change history: CHANGELOG.md
- Security controls and policy: SECURITY.md
- Testing and validation: TESTING.md
- Deployment and operations runbook: DEPLOYMENT.md
- Database migrations and schema change workflow: MIGRATIONS.md
- Remediation execution status: RISK_REMEDIATION_PLAN.md
- AI assistant canonical rules: PERMANENT_INSTRUCTIONS.md

## Consolidation Policy

- Keep only one canonical doc per topic.
- Merge overlapping docs into the canonical target, then archive superseded docs.
- Do not delete historical docs immediately. Move to docs/archive/ after merge confirmation.
- Keep README.md short and route readers to canonical docs.

## File-by-File Classification

| File | Classification | Target / Action |
|---|---|---|
| README.md | Keep (Canonical) | Root entry point |
| CONTRIBUTING.md | Keep (Canonical) | Contribution workflow |
| CHANGELOG.md | Keep (Canonical) | Release history |
| SECURITY.md | Keep (Canonical) | Security source of truth |
| TESTING.md | Keep (Canonical) | Testing source of truth |
| DEPLOYMENT.md | Keep (Canonical) | Deployment source of truth |
| MIGRATIONS.md | Keep (Canonical) | Migration workflow |
| RISK_REMEDIATION_PLAN.md | Keep (Canonical while active) | Archive once fully closed and summarized |
| PERMANENT_INSTRUCTIONS.md | Keep (Canonical) | Assistant behavior source of truth |
| .github/copilot-instructions.md | Keep (Mirror) | Mirror of PERMANENT_INSTRUCTIONS.md |
| .github/pull_request_template.md | Keep | PR process template |
| docs/Gallery.md | Keep (Topic doc) | Gallery behavior and usage |
| static/tutorial/README.md | Keep (Local README) | Asset-local documentation |
| tests/e2e/README.md | Keep (Local README) | E2E test-local documentation |
| PRIVACY.md | Keep (Canonical legal/policy) | Privacy policy |
| DB_AGENT_JOBS.md | Merge candidate | Merge operational portions into DEPLOYMENT.md and/or MIGRATIONS.md; then archive |
| AWS_DEPLOYMENT_GUIDE.md | Archived (stub at root) | Archived content: docs/archive/AWS_DEPLOYMENT_GUIDE.md |
| DEPLOYMENT_PLAN.md | Archived (stub at root) | Archived content: docs/archive/DEPLOYMENT_PLAN.md |
| ENFORCEMENT_GUIDE.md | Merge candidate | Merge into SECURITY.md; then archive |
| REDIS_USAGE.md | Merge candidate | Merge into SECURITY.md and/or DEPLOYMENT.md; then archive |
| SSMS_migration_steps.md | Merge candidate | Merge into MIGRATIONS.md; then archive |
| PACKAGE_FEATURE_MATRIX.md | Keep (Reference) | Feature/package mapping reference |
| USER_JOURNEYS.md | Keep (Reference) | Product and UX journey reference |
| EMAIL_PROGRAM.md | Keep (Reference) | Messaging program reference |
| TUTORIAL.md | Keep (User-facing) | End-user walkthrough |
| Tasks.md | Merge candidate | Merge actionable items into RISK_REMEDIATION_PLAN.md or issue tracker; then archive |
| CLEANUP_CANDIDATES.md | Keep (Ops backlog) | Cleanup inventory and rationale |
| CENTERING_CHECKLIST.md | Archive candidate | Short-lived checklist, likely superseded |
| WEBSITE_TODO.md | Archive candidate | Short-lived backlog snapshot, likely superseded |
| WEBSITE_REVIEW_2026-03-23.md | Archive candidate | Historical snapshot |
| WEBSITE_REVIEW_2026-03-24.md | Archive candidate | Historical snapshot |
| WEBSITE_REVIEW_2026-03-26.md | Keep (Short term) | Source input for recent remediation; archive after final summary |

## Suggested Next Consolidation Batch

1. Security batch:
- Merge ENFORCEMENT_GUIDE.md and REDIS_USAGE.md into SECURITY.md.
- Move both files to docs/archive/.

2. Migrations batch:
- Merge SSMS_migration_steps.md into MIGRATIONS.md.
- Move source file to docs/archive/.

3. Historical cleanup batch:
- Move WEBSITE_REVIEW_2026-03-23.md, WEBSITE_REVIEW_2026-03-24.md, WEBSITE_TODO.md, CENTERING_CHECKLIST.md to docs/archive/.

## Guardrails for Doc Moves

- For each moved file, leave a short pointer stub at the original path for one release cycle.
- Verify links from README.md and key docs before removing stubs.
- Keep all legal/compliance docs at stable paths unless explicitly versioned.
