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
# IMPORTANT : on capture stdout/stderr pour voir l'erreur exacte si la migration échoue,
# mais on NE quitte PAS si l'alembic plante — sinon le backend ne démarre jamais
# et tout le site tombe en 502 (login compris). On log et on continue : uvicorn démarrera
# quand même et on pourra investiguer via les endpoints.
try:
    result = subprocess.run(
        ["python", "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.stdout:
        print("=== alembic stdout ===", flush=True)
        print(result.stdout, flush=True)
    if result.stderr:
        print("=== alembic stderr ===", file=sys.stderr, flush=True)
        print(result.stderr, file=sys.stderr, flush=True)
    if result.returncode != 0:
        print(
            f"!!! Migration FAILED (exit={result.returncode}) — démarrage uvicorn malgré tout pour préserver l'API.",
            file=sys.stderr,
            flush=True,
        )
    else:
        print("Migrations OK.", flush=True)
except Exception as exc:
    print(f"!!! Exception pendant alembic upgrade head : {exc}", file=sys.stderr, flush=True)
    print("Démarrage uvicorn malgré tout pour préserver l'API.", file=sys.stderr, flush=True)

print("Starting server...", flush=True)
workers = os.environ.get("WEB_CONCURRENCY", "2")
os.execvp(
    "uvicorn",
    ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", workers],
)
