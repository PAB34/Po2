# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

**PatrimoineOp** — a SaaS platform for municipal building/property portfolio management. It consolidates data from DGFiP (MAJIC/DGFP fiscal registers), IGN, and OSM to build a geospatial building inventory. Users are scoped to a city (multi-tenant by `city_id`).

## Stack

| Layer | Tech |
|---|---|
| Backend | FastAPI, SQLAlchemy 2.0, Alembic, Pydantic, PostgreSQL 16 + PostGIS |
| Frontend | React 18, Vite, TypeScript, React Router v6, React Query v5 |
| Auth | JWT (python-jose), bcrypt — token stored in `localStorage`, sent as `Authorization: Bearer` |
| Infra | Docker Compose, Caddy (reverse proxy), Nginx (frontend static), GitHub Actions → VPS SSH deploy |

## Common Commands

### Backend

```bash
# Install dependencies
cd saas/backend
pip install -r requirements.txt

# Run dev server (from saas/backend/)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run migrations
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "description"

# Run tests
pytest
```

### Frontend

```bash
cd saas/frontend
npm install
npm run dev        # dev server on :5173
npm run build      # tsc + vite build
```

### Full stack (Docker Compose production)

```bash
# From saas/ with a .env file (copy from .env.example)
docker compose -f infra/docker-compose.prod.yml --env-file .env up -d --build
```

## Architecture

### Backend (`saas/backend/app/`)

```
api/
  router.py          # mounts all route groups under /api
  deps.py            # FastAPI Depends: get_db, get_current_user
  routes/            # auth, buildings, cities, health
core/
  config.py          # Pydantic Settings (reads .env)
  db.py              # SQLAlchemy engine + SessionLocal
  security.py        # JWT encode/decode, password hashing
models/              # SQLAlchemy ORM models (User, City, Building, Local)
schemas/             # Pydantic request/response schemas
services/            # Business logic (auth, buildings, cities, building_naming)
scripts/             # One-off data import scripts (import_cities.py)
```

Routes are thin; business logic lives in `services/`. All DB access goes through `Depends(get_db)` session injection.

### Frontend (`saas/frontend/src/`)

```
lib/api.ts           # All fetch calls — single source of API truth
providers/AuthProvider.tsx  # AuthContext: token + user, persisted in localStorage
pages/               # Feature pages (one per route)
components/          # Shared / map components
App.tsx              # Route definitions + sidebar shell
```

React Query manages all server state. `lib/api.ts` exposes typed async functions; pages call them via `useQuery`/`useMutation`.

### Data models

- **Building** — core entity; tracks DGFiP source data, geocoordinates, IGN/OSM identifiers, MAJIC fiscal properties
- **Local** — a premises/unit linked to a Building (e.g., floors, separate units)
- **City** — scoping entity; every User and Building belongs to one city
- **User** — has `city_id`; all data queries are filtered by the logged-in user's city

### Building naming workflow

`services/building_naming.py` handles the reconciliation logic between DGFP/MAJIC Excel imports and IGN/OSM geodata. The frontend `BuildingCreateEditPage` drives a multi-step import/create flow.

## Environment

Copy `saas/.env.example` to `saas/.env`. Key variables:

```
DATABASE_URL=postgresql+psycopg://patrimoineop:patrimoineop@db:5432/patrimoineop
SECRET_KEY=<random string>
VITE_API_URL=/api           # frontend uses this to reach the backend via Caddy
```

## Deployment

GitHub Actions (`.github/workflows/deploy.yml`) triggers on push to `main` when `saas/` or `infra/` files change. It SSHs into the VPS, `git pull`s, and runs `docker compose up --build -d`.

CI (`.github/workflows/ci.yml`) runs on every push/PR: Python `compileall` check for backend, `npm run build` for frontend.
