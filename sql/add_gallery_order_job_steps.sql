/*
  add_gallery_order_job_steps.sql

  Run as a sysadmin in msdb. This script will add a T-SQL job step to the existing
  job 'EPU_Prepare_GalleryOrder'. It inserts the full contents of sql/prepare_gallery_order.sql
  as an inline T-SQL step. If you prefer to run the file via sqlcmd, use the alternative
  CMDEXEC step (commented below) and set the @file_path to the script location on the SQL Server host.

  Usage: open in SSMS, inspect, then execute.
*/

USE msdb;
GO

DECLARE @job_name SYSNAME = N'EPU_Prepare_GalleryOrder';
DECLARE @step_name SYSNAME = N'Run prepare_gallery_order (inline)';
DECLARE @command NVARCHAR(MAX);

-- Inline the script from sql/prepare_gallery_order.sql here. If that file is updated, re-run this script to refresh the step.
SET @command = N'
-- BEGIN prepare_gallery_order.sql
IF OBJECT_ID(''dbo.EventGalleryOrder'',''U'') IS NULL
BEGIN
    CREATE TABLE dbo.EventGalleryOrder(
        EventID INT NOT NULL,
        FileMetadataID INT NOT NULL,
        Ordinal INT NOT NULL,
        UpdatedAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
        CONSTRAINT PK_EventGalleryOrder PRIMARY KEY (EventID, Ordinal)
    );
    CREATE INDEX IX_EventGalleryOrder_Event_File ON dbo.EventGalleryOrder(EventID, FileMetadataID);
END

;WITH Src AS (
    SELECT f.EventID, f.FileMetadataID, f.CapturedDateTime, f.UploadDate
    FROM dbo.FileMetadata f
    WHERE f.Deleted = 0
), Ordered AS (
  SELECT EventID, FileMetadataID,
       ROW_NUMBER() OVER (
         PARTITION BY EventID
         ORDER BY CASE WHEN CapturedDateTime IS NULL THEN 1 ELSE 0 END,
            CapturedDateTime ASC,
            UploadDate ASC,
            FileMetadataID ASC
       ) AS Ordinal
  FROM Src
)

DECLARE @now DATETIME2 = SYSUTCDATETIME();

-- Build a staging temp table with the computed ordering and a timestamp
SELECT EventID, FileMetadataID, Ordinal, @now AS UpdatedAt
INTO #new_order
FROM Ordered;

-- Ensure uniqueness and optimize joins
CREATE UNIQUE CLUSTERED INDEX IX_new_order_event_ordinal ON #new_order(EventID, Ordinal);

-- Merge staging into the target table: update existing rows, insert new, and delete rows that are no longer present
MERGE INTO dbo.EventGalleryOrder AS target
USING #new_order AS src
  ON target.EventID = src.EventID AND target.Ordinal = src.Ordinal
WHEN MATCHED AND (target.FileMetadataID <> src.FileMetadataID OR target.UpdatedAt <> src.UpdatedAt)
  THEN UPDATE SET FileMetadataID = src.FileMetadataID, UpdatedAt = src.UpdatedAt
WHEN NOT MATCHED BY TARGET
  THEN INSERT (EventID, FileMetadataID, Ordinal, UpdatedAt)
     VALUES (src.EventID, src.FileMetadataID, src.Ordinal, src.UpdatedAt)
WHEN NOT MATCHED BY SOURCE
  THEN DELETE
;

-- Cleanup staging
DROP INDEX IF EXISTS IX_new_order_event_ordinal ON #new_order;
DROP TABLE IF EXISTS #new_order;
DELETE o FROM dbo.EventGalleryOrder o LEFT JOIN dbo.Event e ON e.EventID = o.EventID WHERE e.EventID IS NULL;
UPDATE dbo.EventGalleryOrder SET UpdatedAt = @now WHERE UpdatedAt IS NULL OR UpdatedAt < DATEADD(MINUTE,-30,@now);
PRINT ''Gallery order prepared.'';
-- END prepare_gallery_order.sql
';

-- Remove existing step with the same name (if present)
IF EXISTS (SELECT 1 FROM msdb.dbo.sysjobsteps s JOIN msdb.dbo.sysjobs j ON s.job_id = j.job_id WHERE j.name = @job_name AND s.step_name = @step_name)
BEGIN
  PRINT 'Removing existing job step: ' + @step_name;
  DECLARE @job_id UNIQUEIDENTIFIER;
  SELECT @job_id = job_id FROM msdb.dbo.sysjobs WHERE name = @job_name;
  EXEC msdb.dbo.sp_delete_jobstep @job_id = @job_id, @step_id = (SELECT s.step_id FROM msdb.dbo.sysjobsteps s WHERE s.job_id = @job_id AND s.step_name = @step_name);
END

-- Add the inline T-SQL step
EXEC msdb.dbo.sp_add_jobstep
  @job_name = @job_name,
  @step_name = @step_name,
  @subsystem = N'TSQL',
  @command = @command,
  @database_name = N'EPU',
  @retry_attempts = 1,
  @retry_interval = 5;

PRINT 'Added inline TSQL step to job: ' + @job_name;

/*
-- Alternative: add a CmdExec step to run the script file via sqlcmd on the server
DECLARE @file_path NVARCHAR(4000) = N'C:\db-scripts\prepare_gallery_order.sql';
EXEC msdb.dbo.sp_add_jobstep
  @job_name = @job_name,
  @step_name = N'Run prepare_gallery_order (sqlcmd file)',
  @subsystem = N'CMDEXEC',
  @command = N'sqlcmd -S (local) -d EPU -i "' + @file_path + '"',
  @retry_attempts = 1,
  @retry_interval = 5;
*/

-- Optional: start the job now
-- EXEC msdb.dbo.sp_start_job @job_name = @job_name;
