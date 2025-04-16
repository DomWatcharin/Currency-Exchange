#!/bin/bash
set -e

# Use the default postgres database for setup
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "postgres" <<-EOSQL
    -- Create the database if it doesn't exist
    DO
    \$do\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_database WHERE datname = '$POSTGRES_DB') THEN
            CREATE DATABASE $POSTGRES_DB;
        END IF;
    END
    \$do\$;

    -- Create the user if it doesn't exist
    DO
    \$do\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$POSTGRES_USER') THEN
            CREATE ROLE $POSTGRES_USER WITH LOGIN PASSWORD '$POSTGRES_PASSWORD' SUPERUSER;
        END IF;
    END
    \$do\$;

    -- Grant necessary privileges on the database to $POSTGRES_USER
    GRANT ALL PRIVILEGES ON DATABASE $POSTGRES_DB TO $POSTGRES_USER;
EOSQL

# Connect to the newly created database and configure permissions for the public schema
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    -- Change ownership of the public schema to $POSTGRES_USER
    ALTER SCHEMA public OWNER TO $POSTGRES_USER;

    -- Grant all privileges on the public schema to $POSTGRES_USER
    GRANT ALL ON SCHEMA public TO $POSTGRES_USER;

    -- Grant default privileges on all future objects in the public schema to $POSTGRES_USER
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON TABLES TO $POSTGRES_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON SEQUENCES TO $POSTGRES_USER;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL PRIVILEGES ON FUNCTIONS TO $POSTGRES_USER;
EOSQL

# Execute additional setup SQL if required
if [ -f /docker-entrypoint-initdb.d/setup.sql ]; then
    echo "Executing additional SQL setup..."
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -f /docker-entrypoint-initdb.d/setup.sql
fi

# Insert initial data into banks table
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    INSERT INTO banks (name, code) VALUES
    ('BOT', 'BOTHTHBK'),
    ('SCB', 'SICOTHBK'),
    ('KBANK', 'KASITHBK'),
    ('BBL', 'BKKBTHBK'),
    ('TTB', 'TMBKTHBK')
    ON CONFLICT (code) DO NOTHING;
EOSQL

# Insert initial data into currencies table
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    INSERT INTO currencies (code, name) VALUES
    ('USD', 'United States Dollar'),
    ('THB', 'Thai Baht')
    ON CONFLICT (code) DO NOTHING;
EOSQL
