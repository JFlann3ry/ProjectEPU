-- validation_and_checks.sql
-- Run these queries to validate schema and alembic stamp state.

-- 1) Show alembic_version
SELECT * FROM dbo.alembic_version;

-- 2) Confirm tables exist
SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_NAME IN ('CustomEventType','EventTask','Theme');

-- 3) Confirm Theme.IsActive column
SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, ORDINAL_POSITION, COLUMN_DEFAULT, IS_NULLABLE, DATA_TYPE
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'Theme' AND COLUMN_NAME = 'IsActive';

-- 4) Quick counts (optional)
SELECT COUNT(*) AS CustomEventTypeCount FROM dbo.CustomEventType;
SELECT COUNT(*) AS EventTaskCount FROM dbo.EventTask;
SELECT COUNT(*) AS ThemeCount FROM dbo.Theme;
