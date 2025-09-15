-- stamp_alembic_version_to_20250912_0024.sql
-- Back up current alembic_version rows, then replace with single final-merge revision.
-- Run this only after you've confirmed the DB schema matches the repo (you've already validated Theme.IsActive, CustomEventType, EventTask).

BEGIN TRY
    BEGIN TRANSACTION;

    -- Create a timestamped backup table (only once)
    IF OBJECT_ID('dbo.alembic_version_backup_before_20250912_0024', 'U') IS NULL
    BEGIN
        SELECT GETDATE() AS BackupTime, version_num INTO dbo.alembic_version_backup_before_20250912_0024 FROM dbo.alembic_version;
    END

    -- Ensure alembic_version exists
    IF OBJECT_ID('dbo.alembic_version', 'U') IS NULL
    BEGIN
        RAISERROR('Table dbo.alembic_version does not exist. Alembic metadata table is required.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END

    -- Replace contents with the single final-merge revision we want
    DELETE FROM dbo.alembic_version;
    INSERT INTO dbo.alembic_version (version_num) VALUES ('20250912_0024_final_merge');

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH

-- Verify after running:
-- SELECT * FROM dbo.alembic_version;
