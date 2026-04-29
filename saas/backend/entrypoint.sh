#!/bin/sh
set -e

echo "Waiting for database..."
until python -c "
import os, sys
from sqlalchemy import create_engine, text
engine = create_engine(os.environ['DATABASE_URL'])
try:
    with engine.connect() as conn: conn.execute(text('SELECT 1'))
    sys.exit(0)
except: sys.exit(1)
" 2>/dev/null; do
  sleep 2
done

echo "Running migrations..."
python -m alembic upgrade head

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
