# 009 — Environnement de staging sur le même VPS

> **Statut** : Accepté
> **Date** : 2026-06-16
> **Décideur(s)** : PAB34 + Claude (Opus 4.8)
> **Session liée** : `[[Sessions/2026-06-16 - Parcours Factures marche et consolidation finances]]`

## Contexte

La refonte frontend va enchaîner plusieurs parcours. Aujourd'hui il n'existe aucun
moyen de tester une branche autrement qu'en la mergeant dans `main`, ce qui déclenche
le déploiement prod (`patrimoineaucarre.com`) et remplace le build en cours. Le build
frontend n'est pas exécutable sur le poste utilisateur (npm/node absents). Contraintes :
un seul VPS OVH, un seul Caddy occupant 80/443, budget limité (pas de 2ᵉ serveur).

## Décision

Mettre en place un environnement de staging **sur le même VPS**, isolé dans un projet
Docker distinct (`po2-staging`) avec sa **propre base de données**, exposé sur le
sous-domaine `staging.patrimoineaucarre.com` routé par le **Caddy de la prod** via un
réseau Docker partagé `po2-edge`. Déploiement **manuel** (`workflow_dispatch`) avec
choix de la branche. Base staging = **copie de la prod**, accès protégé par le
basic-auth existant.

## Conséquences

### Positives
- Tester n'importe quelle PR sur des données réelles sans toucher la prod ni merger.
- Réutilise l'infra existante (un seul Caddy, mêmes secrets VPS) → coût quasi nul.
- Isolation des données : base, volumes et projet Docker séparés.

### Négatives / coûts assumés
- Le staging partage les ressources CPU/RAM du VPS de prod.
- Un re-deploy prod one-shot est nécessaire (Caddy rejoint `po2-edge` + bloc staging).
- Données réelles en staging ⇒ basic-auth obligatoire ; connecteurs externes coupés.
- Le Caddy prod doit être redémarré après chaque deploy staging (IP des upstreams).

### Alternatives écartées
- **2ᵉ VPS / VM dédiée** — isolation parfaite mais coût récurrent, écarté (budget).
- **Preview frontend seul (Pages/Netlify) contre l'API prod** — exposerait la prod aux
  écritures de test, et pas de backend isolé. Écarté.
- **Auto-deploy sur une branche `staging`** — moins flexible que le déclenchement manuel
  par branche pour valider des PR ponctuelles.

## Mise en place (ordre)

1. **DNS** (action utilisateur) : enregistrement A `staging` → IP du VPS.
2. **Secrets/env** (action utilisateur, sur le VPS) : créer `saas/.env.staging`
   (gabarit `saas/.env.staging.example`) avec DB et `SECRET_KEY` distincts ; ajouter
   `STAGING_SITE_ADDRESS=staging.patrimoineaucarre.com` dans le `.env` **prod**.
3. **Merge dans `main`** → re-deploy prod : Caddy rejoint `po2-edge` et charge le bloc staging.
4. **Base staging** : restaurer un dump prod (`infra/backup/backup.sh` → `pg_restore`
   dans la base `po2-staging` db).
5. **Déployer** : lancer le workflow « Deploy staging » en choisissant la branche.

## Liens

- Compose : `saas/infra/docker-compose.staging.yml`
- Caddy : `saas/infra/caddy/Caddyfile` (bloc `{$STAGING_SITE_ADDRESS}`)
- Workflows : `.github/workflows/deploy-staging.yml`, `deploy.yml` (réseau `po2-edge`)
- Gabarit env : `saas/.env.staging.example`
