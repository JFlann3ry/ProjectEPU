# SQL Server Agent maintenance jobs (EPU)

This doc proposes safe, low‑risk jobs the database can own (instead of app code) for clean‑ups and summaries. All timestamps assume UTC and dbo schema (adjust if different).

## Guardrails
- Prefer UPDATE/DELETE in small batches to avoid long locks (TOP (N), ORDER BY, WAITFOR DELAY between batches).
- Wrap steps in TRY/CATCH and log to a simple table (`dbo.JobRunLog`).
- Keep destructive jobs idempotent and with generous retention windows.
- Use Agent PowerShell steps for filesystem actions (don’t enable xp_cmdshell).

```sql
-- One‑time setup for lightweight job logging
IF OBJECT_ID('dbo.JobRunLog','U') IS NULL
BEGIN
  CREATE TABLE dbo.JobRunLog(
    LogID       INT IDENTITY(1,1) PRIMARY KEY,
    JobName     SYSNAME NOT NULL,
    StepName    NVARCHAR(128) NULL,
    StartedAt   DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    FinishedAt  DATETIME2 NULL,
    Succeeded   BIT NOT NULL DEFAULT 0,
    Details     NVARCHAR(4000) NULL
  );
END
```

---

## 1) Purge old PaymentLog rows
- Rationale: webhook noise grows quickly; keep ~90 days.
- Schedule: daily 02:10.

```sql
-- Delete in batches of 10k to minimize blocking
WHILE 1=1
BEGIN
  DELETE TOP (10000) FROM dbo.PaymentLog
  WHERE CreatedAt < DATEADD(DAY,-90,SYSUTCDATETIME());
  IF @@ROWCOUNT = 0 BREAK;
  WAITFOR DELAY '00:00:02';
END
```

## 2) Expire completed exports (and files)
- Table: dbo.UserDataExportJob
- Policy: Completed > 7 days => delete row, and remove file from disk via Agent PowerShell step.
- Schedule: daily 02:20.

```sql
-- Mark rows to remove and capture paths in a temp table for PS step
IF OBJECT_ID('tempdb..#to_remove') IS NOT NULL DROP TABLE #to_remove;
SELECT JobID, FilePath
INTO #to_remove
FROM dbo.UserDataExportJob WITH (READPAST)
WHERE Status = 'completed'
  AND COALESCE(ExpiresAt, DATEADD(DAY,7,CompletedAt)) < SYSUTCDATETIME();

DELETE dbo.UserDataExportJob
FROM dbo.UserDataExportJob j
JOIN #to_remove r ON r.JobID = j.JobID;
```

PowerShell step (same job, next step):

```powershell
# Remove files listed by step output (or requery via Invoke-Sqlcmd if preferred)
# Example assumes you requery the same predicate; safer to archive to storage first.
```

## 3) Prune soft‑deleted guest messages
- Table: dbo.GuestMessage
- Policy: Deleted = 1 for 30+ days.
- Schedule: daily 02:30.

```sql
DELETE TOP (5000) FROM dbo.GuestMessage
WHERE Deleted = 1 AND CreatedAt < DATEADD(DAY,-30,SYSUTCDATETIME());
```

## 4) Remove stale guest sessions with no uploads
- Tables: dbo.GuestSession, dbo.FileMetadata
- Policy: Sessions older than 60 days with UploadCount = 0 and no files.
- Schedule: daily 02:40.

```sql
;WITH empty_sessions AS (
  SELECT s.GuestID
  FROM dbo.GuestSession s
  LEFT JOIN dbo.FileMetadata f ON f.GuestID = s.GuestID
  WHERE s.CreatedAt < DATEADD(DAY,-60,SYSUTCDATETIME())
    AND COALESCE(s.UploadCount,0) = 0
    AND f.FileMetadataID IS NULL
)
DELETE s
FROM dbo.GuestSession s
JOIN empty_sessions x ON x.GuestID = s.GuestID;
```

## 5) Recompute EventStorage usage and lock status
- Tables: dbo.EventStorage, dbo.FileMetadata
- Purpose: Keep `CurrentUsageMB` accurate and toggle `IsLocked` when exceeding limit.
- Schedule: hourly at :05 (or nightly if sufficient).

```sql
;WITH usage_mb AS (
  SELECT EventID, CAST(SUM(COALESCE(FileSize,0))/1048576.0 AS INT) AS UsedMB
  FROM dbo.FileMetadata WITH (READPAST)
  WHERE Deleted = 0
  GROUP BY EventID
)
UPDATE es
SET es.CurrentUsageMB = COALESCE(u.UsedMB,0),
    es.IsLocked = CASE WHEN COALESCE(u.UsedMB,0) >= es.StorageLimitMB THEN 1 ELSE 0 END,
    es.UpdatedAt = SYSUTCDATETIME()
FROM dbo.EventStorage es
LEFT JOIN usage_mb u ON u.EventID = es.EventID;
```

## 6) Mark stale pending purchases as abandoned
- Table: dbo.Purchase
- Policy: `Status = 'pending'` with `CreatedAt < 48h` => `abandoned`.
- Schedule: hourly at :15.

```sql
UPDATE dbo.Purchase
SET Status = 'abandoned', UpdatedAt = SYSUTCDATETIME()
WHERE Status = 'pending'
  AND CreatedAt < DATEADD(HOUR,-48,SYSUTCDATETIME());
```

## 7) Optional: Archive old FileMetadata
- When tables grow large, archive by month into `dbo.FileMetadata_Archive`.
- Schedule: weekly Sunday 03:30. Ensure application tolerates archival.

```sql
-- Example: move rows older than 365 days and marked Deleted = 1
IF OBJECT_ID('dbo.FileMetadata_Archive','U') IS NULL
BEGIN
  SELECT TOP 0 * INTO dbo.FileMetadata_Archive FROM dbo.FileMetadata;
  ALTER TABLE dbo.FileMetadata_Archive ADD CONSTRAINT PK_FileMetadata_Archive PRIMARY KEY (FileMetadataID);
END

INSERT INTO dbo.FileMetadata_Archive
SELECT * FROM dbo.FileMetadata WITH (READPAST)
WHERE Deleted = 1 AND UploadDate < DATEADD(DAY,-365,SYSUTCDATETIME());

DELETE dbo.FileMetadata
WHERE Deleted = 1 AND UploadDate < DATEADD(DAY,-365,SYSUTCDATETIME());
```

## 8) Index and statistics maintenance
- Use a proven solution (e.g., Ola Hallengren scripts) or a light job:

```sql
-- Update stats (daily)
EXEC sp_MSforeachtable 'UPDATE STATISTICS ? WITH FULLSCAN';

-- Simple rebuild for highly fragmented indexes (weekly)
-- Consider Ola scripts for robust handling.
```

## 9) Optional: daily materialized summaries
- Example: Event uploads per day for dashboards.

```sql
IF OBJECT_ID('dbo.EventDailyUploads','U') IS NULL
BEGIN
  CREATE TABLE dbo.EventDailyUploads(
    EventID INT NOT NULL,
    [Date]  DATE NOT NULL,
    Uploads INT NOT NULL,
    PRIMARY KEY (EventID,[Date])
  );
END

;WITH d AS (
  SELECT EventID, CAST(UploadDate AS DATE) AS [Date], COUNT(*) AS Cnt
  FROM dbo.FileMetadata WITH (READPAST)
  WHERE UploadDate >= DATEADD(DAY,-30, CAST(SYSUTCDATETIME() AS DATE))
  GROUP BY EventID, CAST(UploadDate AS DATE)
)
MERGE dbo.EventDailyUploads AS t
USING d AS s
ON (t.EventID=s.EventID AND t.[Date]=s.[Date])
WHEN MATCHED THEN UPDATE SET t.Uploads = s.Cnt
WHEN NOT MATCHED THEN INSERT (EventID,[Date],Uploads) VALUES (s.EventID,s.[Date],s.Cnt);
```

---

## Scheduling summary
- 02:05 usage recompute (hourly optional)
- 02:10 PaymentLog purge (daily)
- 02:20 Export expiry + file removal (daily)
- 02:30 GuestMessage prune (daily)
- 02:40 GuestSession cleanup (daily)
- 03:30 Archive FileMetadata (weekly, optional)
- 03:40 Rebuild/Stats (weekly/daily)
- 15 past each hour: mark abandoned purchases

## Agent creation skeleton
Create jobs with `sp_add_job`, `sp_add_jobstep`, `sp_add_schedule`, `sp_attach_schedule`, `sp_add_jobserver`. Example skeleton:

```sql
DECLARE @job_id UNIQUEIDENTIFIER;
EXEC msdb.dbo.sp_add_job
  @job_name = N'EPU_PaymentLog_Purge',
  @enabled = 1,
  @description = N'Delete PaymentLog rows older than 90 days',
  @job_id = @job_id OUTPUT;

EXEC msdb.dbo.sp_add_jobstep
  @job_id=@job_id,
  @step_name=N'Purge',
  @subsystem=N'TSQL',
  @command=N"-- paste T-SQL from section 1 here";

EXEC msdb.dbo.sp_add_schedule
  @schedule_name = N'Daily_0210',
  @freq_type = 4, -- daily
  @freq_interval = 1,
  @active_start_time = 21000; -- 02:10:00

EXEC msdb.dbo.sp_attach_schedule @job_id=@job_id, @schedule_name=N'Daily_0210';
EXEC msdb.dbo.sp_add_jobserver  @job_id=@job_id;
```

## Notes
- If filesystem cleanup is critical, prefer an Agent PowerShell step that queries paths then removes safely (try/catch + log). Leave a generous retention buffer.
- Review foreign keys and cascade rules before deletes. Run on a staging copy first.
- Keep application behavior consistent with DB policies (e.g., abandoned purchases). Update app logic/minimum retention if needed.
