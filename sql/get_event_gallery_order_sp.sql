-- Stored procedure to return FileMetadataIDs for an event in the canonical gallery order
-- Uses CREATE OR ALTER for idempotency on SQL Server
CREATE OR ALTER PROCEDURE dbo.GetEventGalleryOrder
    @EventID INT
AS
BEGIN
    SET NOCOUNT ON;
    -- Return FileMetadataID rows ordered by Ordinal for the given EventID
    SELECT FileMetadataID
    FROM EventGalleryOrder
    WHERE EventID = @EventID
    ORDER BY Ordinal;
END;
