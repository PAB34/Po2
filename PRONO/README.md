# PRONO — Ligue 1 (app privée)

Application web privée : tableau de probabilités de la prochaine journée de
Ligue 1 + dynamiques des équipes + blessés (Transfermarkt) + actu (Google News).

Projet **autonome** (n'impacte pas `saas`), mais qui **réutilise le même
mécanisme d'authentification** que `pronostics` : FastAPI + **JWT (HS256) +
bcrypt**, accès réservé à **un seul compte privé** (toi).

## Architecture

```
PRONO/
  backend/        FastAPI : auth JWT + API Ligue 1 (moteur porté, sans scipy)
    app/
      main.py, config.py, security.py, db.py, auth.py, routes_ligue1.py
      ligue1/     data, probabilities, dynamics, injuries_tm, news, service
    Dockerfile, requirements.txt
  frontend/       UI statique (nginx) : écran login + tableau (thème stade)
    index.html, styles.css, app.js, Dockerfile, nginx.conf
  infra/
    docker-compose.yml     services prono-backend + prono-frontend
    caddy-snippet.txt      bloc à ajouter au Caddy existant (sous-domaine)
    .env.example
```

Le front et l'API sont sur le **même domaine** (`ligue1.patrimoineaucarre.com`) :
Caddy route `/api/*` vers le backend, le reste vers le front. Le front envoie le
jeton `Authorization: Bearer ...` sur chaque appel `/api/ligue1/*` (protégés).

## Lancer en local (dev)

```bash
cd PRONO/backend
pip install -r requirements.txt
set PRONO_ADMIN_EMAIL=ton@email.com
set PRONO_ADMIN_PASSWORD=motdepasse
set PRONO_SECRET_KEY=devsecret
set PRONO_SERVE_FRONTEND=1
python -m uvicorn app.main:app --port 5000 --app-dir .
# -> http://127.0.0.1:5000   (PRONO_SERVE_FRONTEND=1 sert le front depuis le même process)
```

## Déploiement sur ton VPS (à côté de saas)

1. **DNS** : créer un enregistrement A `ligue1.patrimoineaucarre.com` → IP du VPS.
2. **Env** : `cp infra/.env.example infra/.env` puis renseigner
   `PRONO_SECRET_KEY` (clé aléatoire), `PRONO_ADMIN_EMAIL`, `PRONO_ADMIN_PASSWORD`.
3. **Caddy** : ajouter le contenu de `infra/caddy-snippet.txt` au Caddyfile de
   `saas` (`saas/infra/caddy/Caddyfile`), puis recharger Caddy
   (`docker compose -f saas/infra/docker-compose.prod.yml restart caddy`).
   > Le réseau partagé `po2-edge` existe déjà (utilisé par le staging).
4. **Lancer PRONO** :
   ```bash
   cd PRONO/infra
   docker compose up -d --build
   ```
5. Ouvrir `https://ligue1.patrimoineaucarre.com` → écran de connexion → tes identifiants.
   (HTTPS émis automatiquement par Caddy dès que le DNS est en place.)


## Workflow GitHub Actions

Le workflow `.github/workflows/deploy-prono.yml` déploie uniquement PRONO sur le VPS.
Il se déclenche manuellement ou sur push `main`/`master` touchant `PRONO/**`.

Pré-requis côté VPS :

- `PRONO/infra/.env` existe et contient `PRONO_SECRET_KEY`, `PRONO_ADMIN_EMAIL`, `PRONO_ADMIN_PASSWORD` ;
- le bloc Caddy `ligue1.patrimoineaucarre.com` est présent dans `saas/infra/caddy/Caddyfile` ;
- le DNS `ligue1.patrimoineaucarre.com` pointe vers le VPS.

## Accès privé

- Aucune inscription publique. **Un seul compte**, créé au démarrage depuis
  `PRONO_ADMIN_EMAIL` / `PRONO_ADMIN_PASSWORD`. Personne d'autre ne peut entrer.
- Toutes les routes `/api/ligue1/*` exigent un jeton JWT valide.
- Pour changer le mot de passe : modifier `.env` et supprimer `users.db` du volume
  `prono_data` (il sera reseedé), ou ajouter un endpoint dédié si besoin.

## Données & limites

- Probabilités = **consensus du marché dévigotté** (Pinnacle > Bet365 > moyenne).
  Meilleure estimation gratuite, **aucun avantage** sur les bookmakers.
- Blessés = scraping Transfermarkt (cache 12 h, alerte si cassure dans
  `/data/injuries.log`). Depuis une IP datacenter, possible throttling → repli cache.
- Historique Football-Data mis en cache 24 h dans le volume `/data`.

Dépendances backend : fastapi, uvicorn/gunicorn, python-jose, passlib/bcrypt,
pandas, numpy, beautifulsoup4, lxml. **Pas de scipy.**

## Pivot value betting booste

Une specification de pivot vers un moteur de simulation/backtest value betting booste est ouverte dans `specs/value-betting-booste.md`.

Regle de transition : l'ecran actuel conserve les probabilites de marche devigottees comme baseline. Le nouveau moteur doit d'abord rester separe, teste et valide par backtest walk-forward avant toute presentation front comme signal exploitable.
