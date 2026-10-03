#!/bin/bash
set -e

echo "Starting Sentinel..."
mkdir -p /app/data

# Bring the database schema up to date. Every migration is safe to re-run, so this works on a
# brand-new database, an existing one, and one whose tables were created without migrations.
# If it fails, stop here: starting the app on a half-migrated schema only hides the problem.
echo "Running database migrations..."
if ! alembic upgrade head; then
    echo "Database migration failed; not starting. Fix the error above (back up data/ first)." >&2
    exit 1
fi
echo "Database is at revision $(alembic current 2>/dev/null | tail -n 1)"

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
