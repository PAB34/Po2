# AGENTS.md

Porte d'entrée pour Codex. **Travailler en mode économe en tokens** : lire le minimum,
ne pas explorer le dépôt sans raison, ne pas suivre les liens Markdown automatiquement.

## Lire au démarrage (uniquement ces fichiers)

1. `docs/00-Index.md` — carte de la documentation
2. `docs/04-Etat-actuel-du-dev.md` — surtout la section « Reprise prochaine session »
3. `docs/05-Conventions-IA.md` — **règles agent complètes (source de vérité)**

Contrainte poste entreprise (zéro install locale) : `docs/07-Environnement-poste-entreprise.md`.

## Ne PAS lire / ne PAS faire par défaut

- Ne pas lire `docs/Archives/`, le journal `docs/Archives/Journal-etat-dev-2026.md`,
  `docs/Sessions/` ni les fichiers historiques, sauf demande explicite ou besoin justifié.
- **Ne pas explorer globalement le dépôt** (grep/scan massif) sans justification précise.
- Ne pas suivre automatiquement les liens Markdown ; respecter `read_policy` dans l'en-tête d'un fichier.
- Lire un fichier de `docs/Modules/` **seulement si la tâche concerne ce module** ; ouvrir la spec active citée dans l'index.

## Au début d'une session

Déduire l'objectif probable depuis la section « Reprise » de `docs/04-Etat-actuel-du-dev.md`, puis
**le faire confirmer avant de coder**, en annonçant :

- objectif déduit + **niveau de confiance : élevé / moyen / faible** ;
- fichiers/modules probablement concernés ;
- tests ciblés probables.

## Pendant le travail

- Proposer un **plan court** avant modification.
- Modifier le **minimum de fichiers** nécessaire.
- Lancer **uniquement les tests ciblés**.
- Résumer le **diff final en moins de 10 lignes**.
- **Fil du dev (obligatoire)** : tout sujet non trivial = un fichier `docs/refonte-v1/<sujet>-decisions-ux.md`
  écrit AVANT de coder (existant vérifié + décisions datées + questions ouvertes numérotées). Vérifier
  l'existant (`services/`/`models/`/classeurs sources) et les données réelles avant d'annoncer du neuf.
  Règle complète : `docs/05-Conventions-IA.md` §2 « fil du dev ».

## Commandes essentielles

```bash
# Backend (saas/backend/)
uvicorn app.main:app --reload --port 8000   # dev
alembic upgrade head                         # migrations
pytest                                        # tests (env avec deps)

# Frontend (saas/frontend/)
npm run build        # tsc + vite build  (npx tsc -b pour le typecheck seul)
```

Stack, arborescence, conventions de code et déploiement : `docs/02-Architecture.md`.
Règles inter-IA détaillées (handoff, ADR, git partagé avec Claude Code) : `docs/05-Conventions-IA.md`.
