-- Read-only. Run this in DBeaver against the Neon database BEFORE any migration.
-- Nothing here writes. It answers one question: is anything already sitting
-- where we are about to build?
--
-- What we need to see:
--   1. No 'lab' schema, or an empty one.
--   2. No 'core' schema -- or if there is one, core.patients must have the
--      columns 001-003 expect. 000_core_compat.sql uses IF NOT EXISTS, so a
--      pre-existing core.patients of a different shape is skipped silently and
--      the functions then fail at runtime against the wrong columns.
--   3. pg_trgm is installable (001 needs it for fuzzy alias + UHID matching).

-- 1. schemas present
SELECT nspname AS schema
FROM pg_namespace
WHERE nspname NOT LIKE 'pg\_%' AND nspname <> 'information_schema'
ORDER BY nspname;

-- 2. tables outside pg_catalog (what is already here)
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
ORDER BY table_schema, table_name;

-- 3. does a core.patients already exist, and in what shape?
SELECT column_name, data_type, character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_schema = 'core' AND table_name = 'patients'
ORDER BY ordinal_position;

-- 4. extensions installed
SELECT extname, extversion FROM pg_extension ORDER BY extname;

-- 5. is pg_trgm available to install?
SELECT name, default_version, installed_version
FROM pg_available_extensions
WHERE name IN ('pg_trgm', 'uuid-ossp', 'pgcrypto');

-- 6. our role, and may it create schemas here?
SELECT current_user,
       current_database(),
       has_database_privilege(current_user, current_database(), 'CREATE') AS may_create_schema;
