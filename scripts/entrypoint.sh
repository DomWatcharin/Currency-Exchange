#!/bin/bash
set -e

# Wait for the database to be ready
export PGPASSWORD="$POSTGRES_PASSWORD"
until psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "Postgres is up - executing command"

# Set the PYTHONPATH environment variable
export PYTHONPATH=/app

# Run the create_admin_user.py script
python /app/scripts/create_admin_user.py

# Check if port 8000 is available
if lsof -i:8000; then
  >&2 echo "Port 8000 is already in use"
  exit 1
fi

# Health check for Airflow scheduler
if ! curl -f http://localhost:8080/health; then
  >&2 echo "Airflow scheduler health check failed"
  exit 1
fi

# Execute the container's main process
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
