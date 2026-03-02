-- Create the app user (admin user is created by POSTGRES_USER env var)
-- This user has RLS enforced — used by the API at runtime.
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'new_phone_app') THEN
        CREATE ROLE new_phone_app WITH LOGIN PASSWORD 'change_me_app';
    END IF;
END
$$;

-- Grant connect
GRANT CONNECT ON DATABASE new_phone TO new_phone_app;

-- Grant schema usage (tables granted after migrations create them)
GRANT USAGE ON SCHEMA public TO new_phone_app;

-- Default privileges: auto-grant SELECT/INSERT/UPDATE/DELETE on future tables
ALTER DEFAULT PRIVILEGES FOR ROLE new_phone_admin IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO new_phone_app;

-- Default privileges: auto-grant USAGE on future sequences
ALTER DEFAULT PRIVILEGES FOR ROLE new_phone_admin IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO new_phone_app;
