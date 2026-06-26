# Diagnostic environnement local API + base

Date : 2026-06-25
Contexte : refonte React V1, atelier Matrices + futur ecran Factures & decisions.

## Resume court

Le frontend React fonctionne localement sur :

- `http://127.0.0.1:5173`

Mais l'API locale ne fonctionne pas aujourd'hui parce que :

- rien n'ecoute sur `127.0.0.1:8000` ;
- rien n'ecoute sur `127.0.0.1:5432` ;
- `uvicorn` n'est pas installe dans le Python global detecte ;
- `docker` n'est pas disponible dans le terminal ;
- le `.env` local pointe `DATABASE_URL` vers `db`, qui est un nom de service Docker, pas une base locale Windows.

Conclusion : ce n'est pas un probleme de page React. C'est un probleme d'environnement backend/base.

## Ports et roles

| Port | Role | Etat constate |
|---|---|---|
| 8765 | serveur statique docs/prototypes | utile pour atelier BPMN/prototypes HTML |
| 5173 | frontend React Vite | OK |
| 8000 | backend FastAPI | absent localement |
| 5432 | PostgreSQL/PostGIS | absent localement |

## Ce qui fonctionne

- `http://127.0.0.1:5173/refonte-v1/matrices-preview` fonctionne sans backend.
- La production repond : `https://patrimoineaucarre.com/api/health` retourne `status: ok`.
- Le frontend TypeScript compile avec le Node installe dans `C:\Users\pa.borja\Documents\Analyse ENEDIS\node`.

## Ce qui ne fonctionne pas

- `http://127.0.0.1:8000/api/health` : serveur non joignable.
- `http://127.0.0.1:5173/api/health` : le proxy Vite renvoie une erreur car il proxy vers `8000`.
- `staging.patrimoineaucarre.com` : DNS non resolu au moment du test.
- `python -m uvicorn app.main:app` : echoue car `uvicorn` n'est pas installe dans le Python global.
- `docker ps` : echoue car `docker` n'est pas dans le PATH / non disponible.

## Pourquoi SQLite/in-memory n'est pas retenu comme solution principale

Une API SQLite locale pourrait donner l'impression que le backend fonctionne, mais ce serait trompeur pour la refonte :

- la plateforme cible utilise PostgreSQL/PostGIS ;
- les migrations Alembic sont ecrites pour la base reelle ;
- les tests d'UX Matrices/Factures doivent rencontrer les vraies donnees et les vrais cas limites ;
- le workflow facture -> controle -> imputation -> export finance doit etre valide sur le modele reel.

SQLite reste utile pour certains tests unitaires, pas pour valider l'application refondue.

## Nouvelle configuration ajoutee

Fichier ajoute : `saas/infra/docker-compose.dev.yml`

Objectif : lancer localement uniquement :

- `db` : PostgreSQL/PostGIS expose sur `127.0.0.1:5432` ;
- `backend` : FastAPI expose sur `127.0.0.1:8000`.

Le frontend reste lance separement via Vite sur `5173`.

## Procedure recommandee si Docker Desktop est disponible

Depuis `C:\Users\pa.borja\Documents\Po2\saas` :

```powershell
docker compose -f infra/docker-compose.dev.yml --env-file .env up -d --build
```

Voir les logs backend :

```powershell
docker compose -f infra/docker-compose.dev.yml --env-file .env logs -f backend
```

Verifier l'API :

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing
```

Puis lancer le front :

```powershell
cd frontend
npm run dev
```

Ouvrir :

- preview sans backend : `http://127.0.0.1:5173/refonte-v1/matrices-preview`
- page reelle avec backend : `http://127.0.0.1:5173/refonte-v1/matrices`

## Si Docker n'est pas installe/disponible

Options :

1. Installer/demarrer Docker Desktop, puis utiliser `docker-compose.dev.yml`.
2. Utiliser la production uniquement en lecture avec beaucoup de prudence, mais ne pas brancher le front dev dessus par defaut car les actions Matrices/Factures peuvent ecrire.
3. Remettre en place un staging DNS/fonctionnel pour tester les donnees reelles sans risque prod.

## Recommandation assistant

Pour la refonte, la meilleure strategie est :

1. garder les previews UX pour avancer vite ;
2. relancer un backend local Docker propre pour tester sans toucher prod ;
3. remettre le staging en service pour validation semi-reelle avant merge/deploiement ;
4. ne jamais utiliser la prod comme bac a sable d'ecriture.

## Suite technique proposee

1. Verifier si Docker Desktop est installe mais non demarre, ou absent.
2. Si Docker est disponible : lancer `docker-compose.dev.yml`.
3. Si le backend demarre : creer/verifier un compte utilisateur local, puis tester `/refonte-v1/matrices`.
4. Si les migrations echouent : lire `logs -f backend`, corriger migration par migration.
5. Ensuite seulement : raccorder l'ecran Factures & decisions V1 aux vraies donnees.
## Mise a jour - staging sslip.io actif

Le staging documente dans `docs/Decisions/009-environnement-staging.md` est actif via :

- `https://staging.135-125-152-112.sslip.io`
- `https://staging.135-125-152-112.sslip.io/api/health`

Test realise le 2026-06-25 : API OK, app `PatrimoineOp API (staging)`, version `0.1.0-staging`.

Conclusion mise a jour : il n'est pas necessaire de forcer Docker local sur le poste entreprise pour tester les donnees reelles. Le staging devient l'environnement recommande pour valider les routes raccordees a l'API.
