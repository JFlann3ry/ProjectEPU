-- stamp_alembic_version_to_20250911_0022.sql
-- Back up current alembic_version rows, then replace with single target revision.
-- Run this only after you've applied the schema changes (or if schema already matches).

BEGIN TRY
    BEGIN TRANSACTION;

    -- Create a backup table with a timestamp suffix if it doesn't already exist
    IF OBJECT_ID('dbo.alembic_version_backup_before_20250911_0022', 'U') IS NULL
    BEGIN
        SELECT GETDATE() AS BackupTime, version_num INTO dbo.alembic_version_backup_before_20250911_0022 FROM dbo.alembic_version;
    END

    -- Make sure alembic_version exists
    IF OBJECT_ID('dbo.alembic_version', 'U') IS NULL
    BEGIN
        RAISERROR('Table dbo.alembic_version does not exist. Alembic metadata table is required.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END

    -- Replace contents with the single revision we want
    DELETE FROM dbo.alembic_version;
    INSERT INTO dbo.alembic_version (version_num) VALUES ('20250911_0022_add_theme_isactive');

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH

-- Verify after running:
-- SELECT * FROM dbo.alembic_version;
