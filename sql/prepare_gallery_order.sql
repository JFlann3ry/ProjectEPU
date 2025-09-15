-- prepare_gallery_order.sql
-- This script computes a stable ordering for gallery files per event and writes
-- an EventGalleryOrder table which stores FileMetadataID and an ordering integer.
-- Run regularly (e.g., every 5-15 minutes) as a SQL Agent job to improve gallery
-- load consistency and let the app query using the precomputed order.

IF OBJECT_ID('dbo.EventGalleryOrder','U') IS NULL
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

-- Replace the following SELECT logic with the app's desired sort: captured asc, nulls last, upload asc
-- We'll generate a dense rank per event so tiles keep the same relative ordering unless new files arrive.

;WITH Src AS (
    SELECT
        f.EventID,
        f.FileMetadataID,
        f.CapturedDateTime,
        f.UploadDate
    FROM dbo.FileMetadata f
    WHERE f.Deleted = 0
), Ordered AS (
    SELECT
        EventID,
        FileMetadataID,
        -- Use ROW_NUMBER() to guarantee a unique, deterministic ordinal per event/file.
        ROW_NUMBER() OVER (
            PARTITION BY EventID
            ORDER BY CASE WHEN CapturedDateTime IS NULL THEN 1 ELSE 0 END,
                     CapturedDateTime ASC,
                     UploadDate ASC,
                     FileMetadataID ASC
        ) AS Ordinal
    FROM Src
)

-- Upsert into EventGalleryOrder: delete existing for events in scope, then insert fresh rows.
-- To minimize locks, process per event in small batches if needed. Here we do a single statement for simplicity.

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
DROP INDEX IF EXISTS IX_new_order_event_ordinal ON #new_order; -- SQL Server 2016+ syntax; safe to ignore if not supported
DROP TABLE IF EXISTS #new_order;

-- Optional: trim old rows for events that no longer exist
DELETE o
FROM dbo.EventGalleryOrder o
LEFT JOIN dbo.Event e ON e.EventID = o.EventID
WHERE e.EventID IS NULL;

-- Update timestamps for touched events
UPDATE dbo.EventGalleryOrder SET UpdatedAt = @now WHERE UpdatedAt IS NULL OR UpdatedAt < DATEADD(MINUTE,-30,@now);

PRINT 'Gallery order prepared.';
