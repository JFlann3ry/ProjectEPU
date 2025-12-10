# Alembic / Migrations Guide (SQL Server)

This guide explains safe workflows for generating and applying Alembic migrations against SQL Server.

## Basics
- Create an autogenerate migration:

```powershell
alembic revision --autogenerate -m "message"
```

- Inspect the generated migration and hand-edit where necessary for SQL Server-specific types.

## Generating SQL for manual application
- To produce raw SQL for review or to run in SSMS:

```powershell
alembic upgrade --sql head > C:\temp\alembic_upgrade.sql
```

- Review the SQL carefully before executing in SSMS; wrap in a transaction when possible.

## Multiple heads & merges
- If you encounter multiple heads, create a merge revision:

```powershell
alembic revision --message "merge heads" --rev-id merge_xxx --head <head1> --head <head2> --splice
```

- Prefer to coordinate merges rather than allowing divergent heads to accumulate.

## Troubleshooting
- Duplicate column errors: if the column already exists in production, consider stamping the migration as applied after verifying schema parity:

```powershell
alembic stamp <revision_id>
```

- Long-running sessions blocking migrations: identify and kill blockers in SQL Server (see `SSMS_migration_steps.md`).

## Best practices
- Keep migrations small and review SQL before applying to prod.
- For destructive changes (DROP column): schedule maintenance and backups.
- Add tests that exercise upgraded schema where possible.

## Verify head is applied (local/dev)
- To ensure your schema is up to date:

```powershell
alembic upgrade head
```

- In VS Code: run the “db:migrate” task.
- If you have multiple heads, resolve them first (see section above), then upgrade again.
