#!/bin/sh
set -e

PYTHON="/app/.venv/bin/python"
export PYTHONPATH="/app:${PYTHONPATH}"

echo "Waiting for PostgreSQL to be ready..."
until $PYTHON -c "import psycopg; psycopg.connect(host='${DB_HOST:-db}', port='${DB_PORT:-5432}', user='${POSTGRES_USER:-user}', password='${POSTGRES_PASSWORD:-ekskursijos}', dbname='${POSTGRES_DB:-ekskursijos_db}')" 2>/dev/null; do
    echo "PostgreSQL is unavailable - sleeping"
    sleep 2
done

echo "PostgreSQL is up."

# # Generate fresh migrations if none exist (fresh DB)
# if [ ! -d "ekskursijos/migrations" ] || [ -z "$(ls -A ekskursijos/migrations/*.py 2>/dev/null | grep -v __init__)" ]; then
#     echo "Generating initial migrations..."
#     $PYTHON manage.py makemigrations ekskursijos --noinput
# fi

echo "Generating initial migrations..."
$PYTHON manage.py makemigrations ekskursijos --noinput

echo "Running migrations..."
$PYTHON manage.py migrate --noinput

echo "Populating database with test data..."
$PYTHON manage.py populate_db

echo "Collecting static files..."
$PYTHON manage.py collectstatic --noinput

exec "$@"
