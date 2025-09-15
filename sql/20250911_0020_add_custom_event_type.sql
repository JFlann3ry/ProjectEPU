-- 20250911_0020_add_custom_event_type.sql
-- Creates dbo.CustomEventType if it does not exist and adds FKs when referenced tables are present.
BEGIN TRY
    BEGIN TRANSACTION;

    IF NOT EXISTS (
        SELECT 1 FROM sys.tables t
        JOIN sys.schemas s ON t.schema_id = s.schema_id
        WHERE t.name = 'CustomEventType' AND s.name = 'dbo'
    )
    BEGIN
        CREATE TABLE dbo.CustomEventType (
            CustomEventTypeID INT IDENTITY(1,1) NOT NULL PRIMARY KEY,
            EventID INT NOT NULL,
            EventTypeID INT NULL,
            CustomEventName NVARCHAR(255) NULL,
            CreatedAt DATETIME2 NOT NULL CONSTRAINT DF_CustomEventType_CreatedAt DEFAULT (GETDATE()),
            UpdatedAt DATETIME2 NOT NULL CONSTRAINT DF_CustomEventType_UpdatedAt DEFAULT (GETDATE())
        );

        -- Add FK to dbo.Event if that table exists
        IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'Event')
        BEGIN
            ALTER TABLE dbo.CustomEventType
            ADD CONSTRAINT FK_CustomEventType_Event FOREIGN KEY (EventID) REFERENCES dbo.Event(EventID);
        END

        -- Add FK to dbo.EventType if that table exists
        IF EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'EventType')
        BEGIN
            ALTER TABLE dbo.CustomEventType
            ADD CONSTRAINT FK_CustomEventType_EventType FOREIGN KEY (EventTypeID) REFERENCES dbo.EventType(EventTypeID);
        END
    END

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH

-- Note: This creates CreatedAt/UpdatedAt defaults; it does not add an automatic ON UPDATE for UpdatedAt.
-- If you need UpdatedAt to be refreshed on row updates, let me know and I can add a trigger definition.
