/*
  run_prepare_gallery_order_test.sql

  Purpose: Run the same logic as the SQL Agent job for preparing EventGalleryOrder,
  but with additional diagnostics so you can run it interactively in SSMS or via sqlcmd.

  Usage:
    - Edit @test_event_id to a specific EventID to limit the run to one event for faster testing,
      or set it to NULL to run for all events.
    - Run in the context of the EPU database (USE EPU).

  Notes:
    - This script is safe to run multiple times.
    - It prints counts before/after and a few sample rows for inspection.
*/

SET NOCOUNT ON;

-- Set to an integer to test a single event, or leave NULL to process all events.
DECLARE @test_event_id INT = NULL; -- e.g., 123
DECLARE @now DATETIME2 = SYSUTCDATETIME();

PRINT 'Preparing gallery order - test run';

-- Diagnostic counts before
PRINT 'Counts before run:';
SELECT COUNT(*) AS total_rows_in_EventGalleryOrder FROM dbo.EventGalleryOrder;
IF @test_event_id IS NOT NULL
BEGIN
  SELECT COUNT(*) AS rows_for_event_before FROM dbo.EventGalleryOrder WHERE EventID = @test_event_id;
END

-- Build source and ordered CTEs; restrict to a single event if requested
;WITH Src AS (
    SELECT f.EventID, f.FileMetadataID, f.CapturedDateTime, f.UploadDate
    FROM dbo.FileMetadata f
    WHERE f.Deleted = 0
      AND (@test_event_id IS NULL OR f.EventID = @test_event_id)
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

-- Create staging and merge (same as job)
SELECT EventID, FileMetadataID, Ordinal, @now AS UpdatedAt
INTO #new_order
FROM Ordered;

-- Create index for merge efficiency
CREATE UNIQUE CLUSTERED INDEX IX_new_order_event_ordinal ON #new_order(EventID, Ordinal);

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
IF EXISTS (SELECT 1 FROM tempdb.sys.indexes i WHERE i.object_id = OBJECT_ID(''tempdb..#new_order'') AND i.name = 'IX_new_order_event_ordinal')
BEGIN
  EXEC('DROP INDEX IX_new_order_event_ordinal ON #new_order');
END

IF OBJECT_ID(''tempdb..#new_order'',''U'') IS NOT NULL
  DROP TABLE #new_order;

-- Optional maintenance and diagnostics after run
PRINT 'Counts after run:';
SELECT COUNT(*) AS total_rows_in_EventGalleryOrder FROM dbo.EventGalleryOrder;
IF @test_event_id IS NOT NULL
BEGIN
  SELECT COUNT(*) AS rows_for_event_after FROM dbo.EventGalleryOrder WHERE EventID = @test_event_id;
  PRINT 'Sample rows for event:';
  SELECT TOP 50 EventID, FileMetadataID, Ordinal, UpdatedAt
  FROM dbo.EventGalleryOrder
  WHERE EventID = @test_event_id
  ORDER BY Ordinal;
END
ELSE
BEGIN
  PRINT 'Sample rows (first 200):';
  SELECT TOP 200 EventID, FileMetadataID, Ordinal, UpdatedAt
  FROM dbo.EventGalleryOrder
  ORDER BY EventID, Ordinal;
END

PRINT 'Test run complete.';

SET NOCOUNT OFF;
