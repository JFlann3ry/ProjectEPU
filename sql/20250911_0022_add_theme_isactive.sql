-- 20250911_0022_add_theme_isactive.sql
-- Adds IsActive BIT NOT NULL default 1 to dbo.Theme if missing.
BEGIN TRY
    BEGIN TRANSACTION;

    -- Only add column if it doesn't already exist
    IF COL_LENGTH('dbo.Theme', 'IsActive') IS NULL
    BEGIN
        ALTER TABLE dbo.Theme
        ADD IsActive BIT NOT NULL CONSTRAINT DF_Theme_IsActive DEFAULT (1);

        -- Ensure existing rows are set to 1 (defensive; column is NOT NULL so this should be redundant)
        UPDATE dbo.Theme SET IsActive = 1 WHERE IsActive IS NULL;
    END

    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH
