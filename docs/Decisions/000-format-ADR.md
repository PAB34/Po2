# 000 — Format ADR pour tracer les décisions durables

> **Statut** : Accepté
> **Date** : 2026-05-19
> **Décideur(s)** : PAB34 + IA (Claude Sonnet 4.5)
> **Session liée** : [[Sessions/2026-05-19 — Renommage + Templates + ADRs]]

## Contexte

Le projet Po2 accumule des choix d'architecture/produit dans :
- Des notes de session (`docs/Sessions/...`) — temporelles, dispersées
- Des sections de modules — mêlées à la doc descriptive
- Des commit messages — peu lisibles à distance
- Des conversations IA — perdues quand la session ferme

Quand une IA reprend le projet, ou que l'utilisateur veut comprendre **pourquoi** un choix a été fait il y a 6 mois, c'est introuvable.

## Décision

Adopter le format **ADR (Architecture Decision Records)** dans `docs/Decisions/`.

Un fichier par décision durable, numéroté incrémentalement (`001-`, `002-`, ...). Structure imposée :

1. **Statut** (Proposé / Accepté / Déprécié / Remplacé par)
2. **Date** + décideur(s) + session liée
3. **Contexte** (le problème, les contraintes, les forces opposées)
4. **Décision** (la solution choisie, en une phrase)
5. **Conséquences** (positives, négatives, alternatives écartées)
6. **Liens** (specs, modules, commits)

Le template de base : [[Decisions/_template]].

### Quand créer une ADR

✅ **OUI** :
- Choix de schéma de données structurant (5 tables BPU plutôt qu'à plat)
- Choix de stack ou de pattern (sync vs async ENEDIS, versioning du vault)
- Convention de nommage qui contraint le futur (préfixes numériques, slugs sans accents)
- Workflow inter-IA (handoff via Sessions/)

❌ **NON** :
- Détail d'implémentation (le nom d'une variable, l'ordre des paramètres)
- Décision facilement réversible (couleur d'un badge, libellé d'un bouton)
- Choix purement temporaire (workaround en attendant un fix amont)

## Conséquences

### Positives
- L'historique des choix durables devient consultable en quelques minutes
- Les IA suivantes peuvent re-challenger une décision en connaissance de cause (statut « Déprécié » + nouvelle ADR « Remplace »)
- L'utilisateur peut auditer le pourquoi sans relire toutes les sessions

### Négatives / coûts assumés
- Discipline requise : il faut **vraiment** écrire une ADR quand la décision est prise (sinon le vault dérive)
- Légère duplication possible avec les notes de session — accepter et trancher : les détails du « comment » restent dans Sessions/, le « quoi » et le « pourquoi » vont dans Decisions/

### Alternatives écartées
- **Pas d'ADR, tout dans Sessions/** — Décisions noyées dans le chronologique, retrouvabilité faible
- **Pas d'ADR, tout dans les modules** — Décisions mélangées à la doc descriptive, difficile à distinguer
- **Format différent (ex: MADR plus complet)** — Trop verbeux pour un projet à 1 mainteneur principal

## Liens

- Pattern d'origine : Michael Nygard, *Documenting Architecture Decisions* (2011)
- Inspiré aussi des [adr-tools](https://github.com/npryce/adr-tools)
- Modules mentionnant des décisions à formaliser : [[Modules/Energie-BPU]], [[Modules/Energie-Consommation]]
