-- 20250911_0021_add_eventtask.sql
-- Creates dbo.EventTask if it does not exist.
BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (
        SELECT 1 FROM sys.tables t
        JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE t.name = 'EventTask' AND s.name = 'dbo'
    )
    BEGIN
        CREATE TABLE dbo.EventTask (
            EventTaskID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
            EventID INT NOT NULL,
            UserID INT NOT NULL,
            [Key] NVARCHAR(64) NOT NULL,
            [State] NVARCHAR(32) NOT NULL CONSTRAINT DF_EventTask_State DEFAULT ('pending'),
            CompletedAt DATETIME2 NULL,
            CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_EventTask_CreatedAt DEFAULT (GETDATE()),
            UpdatedAt DATETIME2 NOT NULL CONSTRAINT DF_EventTask_UpdatedAt DEFAULT (GETDATE())
        );

        -- Optional FK to dbo.Event if the Event table exists
        IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'Event')
        BEGIN
            ALTER TABLE dbo.EventTask
            ADD CONSTRAINT FK_EventTask_Event FOREIGN KEY (EventID) REFERENCES dbo.Event(EventID);
        END

        -- Note: No FK added for UserID because the user table name/ schema may vary.
    END

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH

-- If you prefer explicit FK for UserID, tell me the user table name and schema and I will add it.
