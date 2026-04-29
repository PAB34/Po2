import os
import sys
import time
import subprocess

from sqlalchemy import create_engine, text

print("Waiting for database...", flush=True)
engine = create_engine(os.environ["DATABASE_URL"])
for attempt in range(30):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        break
    except Exception as exc:
        print(f"  DB not ready ({exc}), retrying in 2s...", flush=True)
        time.sleep(2)
else:
    print("Database not reachable after 60s, aborting.", file=sys.stderr)
    sys.exit(1)

print("Running migrations...", flush=True)
result = subprocess.run(["python", "-m", "alembic", "upgrade", "head"])
if result.returncode != 0:
    print("Migration failed, aborting.", file=sys.stderr)
    sys.exit(result.returncode)

print("Starting server...", flush=True)
os.execvp("uvicorn", ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"])
