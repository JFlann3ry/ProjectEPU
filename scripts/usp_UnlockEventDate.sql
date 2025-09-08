/*
  Procedure: dbo.usp_UnlockEventDate
  Purpose:   Unlocks an event date by clearing IsDateLocked and DateLockedAt.
  Notes:
    - Designed for SQL Server.
    - Uses row-level locks to avoid concurrent updates.
    - Returns:
        1  = Unlocked successfully
        0  = No-op (already unlocked)
       -1  = Not found
*/
GO
IF OBJECT_ID('dbo.usp_UnlockEventDate', 'P') IS NULL
    EXEC('CREATE PROCEDURE dbo.usp_UnlockEventDate AS RETURN 0');
GO

ALTER PROCEDURE dbo.usp_UnlockEventDate
    @EventID             INT,
    @PerformedByUserID   INT = NULL,         -- optional: for external audit use
    @Reason              NVARCHAR(200) = NULL, -- optional: for external audit use
    @RequestID           NVARCHAR(64) = NULL   -- optional: for external audit use
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    BEGIN TRY
        BEGIN TRAN;

        -- Ensure the row exists and take an update lock to serialize
        IF NOT EXISTS (SELECT 1 FROM dbo.[Event] WITH (UPDLOCK, HOLDLOCK) WHERE EventID = @EventID)
        BEGIN
            ;THROW 51000, 'Event not found.', 1;
        END

        DECLARE @WasLocked BIT;
        DECLARE @OldLockedAt DATETIME2(6);
        SELECT @WasLocked = IsDateLocked, @OldLockedAt = DateLockedAt
        FROM dbo.[Event] WITH (UPDLOCK, HOLDLOCK)
        WHERE EventID = @EventID;

        IF (ISNULL(@WasLocked, 0) = 0)
        BEGIN
            COMMIT TRAN;
            RETURN 0; -- already unlocked
        END

        UPDATE dbo.[Event]
        SET IsDateLocked = 0,
            DateLockedAt = NULL
        WHERE EventID = @EventID;

        COMMIT TRAN;

        -- Final state echo (optional for callers)
        SELECT EventID,
               CAST(IsDateLocked AS BIT) AS IsDateLocked,
               DateLockedAt
        FROM dbo.[Event]
        WHERE EventID = @EventID;

        RETURN 1;
    END TRY
    BEGIN CATCH
        IF XACT_STATE() <> 0 ROLLBACK TRAN;
        DECLARE @ErrMsg NVARCHAR(2048) = ERROR_MESSAGE();
        DECLARE @ErrNum INT = ERROR_NUMBER();
        DECLARE @ErrState INT = ERROR_STATE();
        RAISERROR(@ErrMsg, 16, 1);
        RETURN -1;
    END CATCH
END
GO
