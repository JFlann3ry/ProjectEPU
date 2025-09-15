# SSMS Migration Steps — Resolve Alembic overlap and finish migrations

This file tells you, step-by-step, what to run in SSMS and PowerShell, what I need from you at each step, and safe fallback options. Back up your DB before doing any changes.

---

## What I need from you before we start

1. Confirm you have a recent full backup of the `EPU` database (take one now if not).
2. Tell me whether you can run PowerShell commands on the server where the DB lives; if not, we'll proceed entirely with SSMS.
3. Paste the outputs of the SQL checks in Section A below (I already saw partial outputs; include the exact output rows as text).

---

## A — Diagnostic checks to run in SSMS (copy/paste results back here)

Run these queries in SSMS and paste the results into your reply.

1) List alembic_version contents:

```sql
SELECT * FROM dbo.alembic_version;
```

You should paste the full rows (looks like you have multiple rows — paste them all).

2) Confirm tables exist (CustomEventType & EventTask):

```sql
SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME IN ('CustomEventType','EventTask');
```

3) Confirm Theme.IsActive column exists and its default:

```sql
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, COLUMN_DEFAULT, IS_NULLABLE, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'Theme' AND COLUMN_NAME = 'IsActive';
```

4) Optional: show rows of `alembic_version` (for clarity):

```sql
SELECT version_num FROM dbo.alembic_version;
```


---

## B — If schema already contains the migration changes (likely in your case)

You reported that `CustomEventType`, `EventTask` tables exist and `Theme.IsActive` exists. That means the DB schema has those migration changes applied, but Alembic's metadata is out of sync. The safe fix is to mark (stamp) the DB as having the appropriate revision(s) without re-running DDL.

Preferred (safe) method — use Alembic stamp (PowerShell):

Run in PowerShell on the machine with the repo and virtualenv (NOT in Python REPL):

```powershell
# Mark DB as having applied through 20250911_0022_add_theme_isactive
E:\ProjectEPU\venv\Scripts\python.exe -m alembic stamp 20250911_0022_add_theme_isactive
# Verify
E:\ProjectEPU\venv\Scripts\python.exe -m alembic current
```

What I need from you if you choose this: run those two commands and paste the output of the `alembic current` command.

If PowerShell is not available to you, do it manually in SSMS (less recommended). See manual SQL below.

Manual (SSMS) method — update `alembic_version` table directly:

1) Inspect the table (if it currently has multiple rows):

```sql
SELECT * FROM dbo.alembic_version;
```

2) Replace contents with single row for the target revision (example):

```sql
DELETE FROM dbo.alembic_version;
INSERT INTO dbo.alembic_version (version_num) VALUES ('20250911_0022_add_theme_isactive');
```

3) Verify:

```sql
SELECT * FROM dbo.alembic_version;
```

What I need from you if you choose this: paste the output of the `SELECT` after the change.


---

## C — If schema does NOT contain the migration changes

If one or more of the checks in Section A return 'missing' (e.g., the table `EventTask` does not exist), then do one of the following safe options:

Option 1 (preferred): Generate SQL for the Alembic migration and run it in SSMS.

On your dev machine run:

```powershell
# generate SQL for EventTask migration
E:\ProjectEPU\venv\Scripts\python.exe -m alembic upgrade 20250911_0021_add_eventtask --sql > C:\temp\20250911_0021_add_eventtask.sql
# inspect the generated SQL file, then run it in SSMS inside a transaction
```

After running SQL in SSMS, stamp the DB to that revision (Section B steps).

Option 2: Run Alembic upgrade directly from PowerShell (simpler if you have repo access):

```powershell
E:\ProjectEPU\venv\Scripts\python.exe -m alembic upgrade 20250911_0020_add_custom_event_type
E:\ProjectEPU\venv\Scripts\python.exe -m alembic upgrade 20250911_0021_add_eventtask
E:\ProjectEPU\venv\Scripts\python.exe -m alembic upgrade 20250911_0022_add_theme_isactive
```

Run them one-by-one and paste outputs if any fail.


---

## D — After stamping / applying migrations

1) Verify Alembic current revision:

```powershell
E:\ProjectEPU\venv\Scripts\python.exe -m alembic current
```

2) Verify `alembic heads` shows a single head or the state you expect:

```powershell
E:\ProjectEPU\venv\Scripts\python.exe -m alembic heads
```

3) Run a quick smoke test of the app (start dev server or run a small API call) to confirm runtime errors are gone.


---

## E — If anything fails or you are unsure

- Paste the exact SQL/text outputs of steps in Section A and the results of any Alembic commands you ran.
- If you used the manual SQL approach to edit `alembic_version`, keep the backup and paste the previous `alembic_version` contents so I can help restore if needed.


---

## Quick summary: What I need from you now (minimum):

1. Confirm you have DB backup.
2. Tell me whether you can run PowerShell on the server (preferred).
3. Paste results of the Section A diagnostic queries (full rows). You already provided partial data; paste exact outputs for the SELECTs listed.
4. Tell me whether you want me to (A) produce SQL files for the missing migrations, (B) run Alembic stamp via PowerShell, or (C) provide exact SSMS SQL to update `alembic_version`.

---

If you want, I can now generate the SQL for `20250911_0021_add_eventtask` and `20250911_0022_add_theme_isactive` so you can run them in SSMS; say "generate SQL" and I'll create the SQL files in `C:\temp` (and print the paths).
