# Architecture

## Stack technique

| Couche | Tech |
|---|---|
| Backend | FastAPI · SQLAlchemy 2.0 · Alembic · Pydantic v2 · Python 3.12 |
| Base | PostgreSQL 16 + extension **PostGIS** |
| Frontend | React 18 · Vite · TypeScript · React Router v6 · TanStack Query v5 · Recharts |
| Auth | JWT (`python-jose`) + bcrypt — token en `localStorage`, header `Authorization: Bearer ...` |
| Infra prod | Docker Compose · Caddy (reverse proxy + TLS auto) · Nginx (static frontend) |
| CI/CD | GitHub Actions → SSH deploy sur VPS OVH (`135.125.152.112`) |

## Arborescence du repo

```
Po2/
├── .devcontainer/                       # Codespaces only (sans docker-in-docker)
├── .github/workflows/                    # ci.yml, deploy.yml
├── docs/                                 # ← CE VAULT OBSIDIAN
├── saas/
│   ├── backend/
│   │   ├── alembic/versions/             # migrations versionnees (0017 ajoute la hierarchie Site -> Building)
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── deps.py                # get_db, get_current_user
│   │   │   │   ├── router.py              # mount /api/*
│   │   │   │   └── routes/                # 12 fichiers : auth, billing, bpu, buildings, cities,
│   │   │   │                              # enedis_async, enedis_sync, energie, engie, equipment, health
│   │   │   ├── core/                      # config (Pydantic Settings), db, scheduler (APScheduler), security
│   │   │   ├── models/                    # SQLAlchemy : user, city, site, building, local, billing(×4),
│   │   │   │                              # bpu(×5), enedis_async, equipment(×2), invoice
│   │   │   ├── schemas/                   # Pydantic : auth, billing, building, city, energie,
│   │   │   │                              # engie, equipment, invoice, user, bpu
│   │   │   ├── services/                  # Logique métier
│   │   │   │   ├── invoice_parsers/       # engie_pdf.py (seul parser)
│   │   │   │   └── *.py                   # 19 services (cf. Modules/)
│   │   │   └── scripts/                   # CLI : import_cities, import_equipment_references,
│   │   │                                  # import_bpu_documents
│   │   ├── tests/                         # pytest
│   │   ├── data/                          # CSV : durees_vie_powerbi_base_wide.csv (référentiel équip.)
│   │   ├── Dockerfile                     # python:3.12-slim + tesseract-ocr-fra + poppler-utils
│   │   └── requirements.txt
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── pages/                     # 17 pages
│   │   │   ├── components/                # 5 composants partagés
│   │   │   ├── providers/AuthProvider.tsx # AuthContext + localStorage
│   │   │   └── lib/api.ts                 # 1742 lignes — single source of truth des appels API
│   │   └── package.json
│   ├── energie/                           # Documents source (gitignored : *.pdf)
│   │   ├── HERAULT ENERGIE/HISTORIQUE BPU/   # 17 PDFs (uploadés via SCP en prod)
│   │   ├── ENGIE/                            # Échantillons factures
│   │   ├── GRDF/                             # (prévu)
│   │   └── output/                           # CSVs générés par les syncs ENEDIS
│   └── infra/
│       ├── docker-compose.prod.yml        # 4 services : db, backend, frontend, caddy
│       └── caddy/Caddyfile
└── README.md
```

## Conventions de code

### Backend
- **Routes minces** : tout le business logic vit dans `services/`, jamais dans les routes
- **DB via `Depends(get_db)`** uniquement, jamais d'instance globale
- **Filtre `city_id` systématique** sur toute requête tenant-scoped
- **Migrations alembic** : 1 migration = 1 changement cohérent, jamais d'autogenerate sans relecture
- **Tests** : pas obligatoires partout mais critiques pour les modules sensibles (enedis_common rate-limit, bpu parser)

### Frontend
- **Pas de fetch direct** : tout passe par `lib/api.ts` (qui définit aussi les types TS)
- **TanStack Query** : pas de `useState` pour le server state, uniquement pour l'UI state
- **Dark mode aware** : palettes Tailwind avec variants `dark:` partout (badges, bordures, fonds)
- **Pas d'emoji dans le code/UI** sauf si l'utilisateur le demande explicitement

### Git
- **Commit + push systématique** en fin de session (cf. MEMORY.md de l'utilisateur)
- **PR + squash-merge** via `gh` CLI (installé en user-scope via winget)
- **Token GitHub** stocké dans Windows Credential Manager (récupérable via `git credential fill`)
- **`.pdf` est gitignored** — les fichiers source restent locaux + sur le VPS

## Déploiement

### Workflow `deploy.yml`
Déclenché sur push à `main` quand `saas/**` ou `.github/workflows/deploy.yml` change (path filter strict). SSH au VPS, `git pull`, `docker compose up --build -d`, restart Caddy.

### VPS OVH (`135.125.152.112`, Ubuntu 25.04)
- Conteneurs actifs : `infra-backend-1`, `infra-frontend-1`, `infra-caddy-1`, `infra-db-1`
- Anciens conteneurs `saas-*` toujours up (legacy, à nettoyer un jour)
- **Le VPS héberge AUSSI le FTP ENEDIS** (vsftpd, user `enedis_ftp`, password dans `/root/.ftp_password_enedis`, UFW whitelist IPs ENEDIS prod)
- `.env` prod situé à `/home/ubuntu/Po2/.env` (variables ENEDIS_*, FTP_*, DATABASE_URL, etc.)
- Volume mount : `../../:/workspace:ro` → le backend accède au dépôt complet en read-only, utile pour `import_bpu_documents.py` qui lit les PDFs

### Migrations en prod
```bash
ssh -i ~/.ssh/po2_vps2 ubuntu@135.125.152.112
docker exec infra-backend-1 alembic upgrade head
```

### Import de données en prod
```bash
docker exec infra-backend-1 python -m app.scripts.import_bpu_documents
docker exec infra-backend-1 python -m app.scripts.import_equipment_references /workspace/saas/backend/data/durees_vie_powerbi_base_wide.csv --truncate
```
