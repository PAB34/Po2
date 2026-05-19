# 001 — Vault Obsidian versionné dans `docs/` (et non hors repo)

> **Statut** : Accepté
> **Date** : 2026-05-19
> **Décideur(s)** : PAB34 + IA (Claude Sonnet 4.5)
> **Session liée** : [[Sessions/2026-05-19 — BPU + Codespaces + Vault Obsidian]]

## Contexte

L'utilisateur a installé Obsidian sur son ordinateur entreprise et a ouvert `C:\Users\pa.borja\Documents\Po2` comme vault (le coffre Obsidian = le dépôt git Po2).

Il veut un système où **toutes les IA** qui interviennent sur le projet peuvent :
- Comprendre l'état du projet sans tout ré-expliquer
- Passer la main proprement quand la limite de tokens est atteinte

Question : où mettre les notes Obsidian ?

## Décision

Les notes vivent dans le sous-dossier **`docs/`** du dépôt git, donc versionnées avec le code.

Le dossier `.obsidian/` (config locale Obsidian) est **gitignored** (`.obsidian/` ajouté au `.gitignore`).

## Conséquences

### Positives
- Une IA distante (Claude Code sur un autre poste, GPT via API, etc.) accède au vault via `git pull` standard
- L'historique git devient le journal des évolutions de la doc — utile pour blame & rollback
- Le workflow PR/squash-merge s'applique aussi aux changements de doc structurels
- L'utilisateur n'a qu'**un seul** endroit à ouvrir (Obsidian sur le repo)

### Négatives / coûts assumés
- Les commits de doc apparaissent dans `git log` mélangés aux commits de code — atténué par les préfixes `docs(...)` dans les messages
- Le déploiement OVH est filtré par path (`saas/**` + `infra/**`) donc `docs/` ne déclenche pas de redéploiement — vérifié, OK

### Alternatives écartées
- **Vault dans un repo séparé `Po2-docs`** — Synchronisation manuelle, friction inutile pour un projet à 1 mainteneur
- **Vault sur un service externe (Notion, Confluence)** — Pas accessible aux IA distantes par défaut, pas versionné dans git
- **Vault dans `.obsidian/`** — `.obsidian/` est de la config Obsidian, ce n'est pas le bon emplacement sémantique

## Liens

- Sessions : [[Sessions/2026-05-19 — BPU + Codespaces + Vault Obsidian]]
- Conventions inter-IA : [[05-Conventions-IA]]
- Commit initial du vault : `8bd5697 docs(obsidian): initialiser vault de coordination IA-a-IA`
