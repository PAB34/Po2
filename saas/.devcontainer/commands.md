# Lancement rapide dans le devcontainer

## Backend

```bash
cd /workspace/saas/backend
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Frontend

```bash
cd /workspace/saas/frontend
npm run dev
```

## Vérifications

- Backend: `/api/health`
- Docs API: `/docs`
- Frontend: port `5173`
