# 004 — Specs canoniques restent dans `saas/specs/`, référencées depuis Obsidian

> **Statut** : Accepté
> **Date** : 2026-05-19
> **Décideur(s)** : PAB34 + IA (Claude Sonnet 4.5)
> **Session liée** : [[Sessions/2026-05-19 — Intégration specs historiques au vault]]

## Contexte

Lors de la création du vault Obsidian dans `docs/`, on a découvert un dossier `saas/specs/` contenant 9 fichiers Markdown / JSON datés d'avril-mai 2026. L'audit (cf. [[Specs]]) a révélé :
- 4 specs **canoniques** (mapping ENGIE, matrice contrôles, TURPE 7, kit ENEDIS async) — toujours fraîches et structurantes
- 3 specs **partielles** dont quelques pépites mériteraient d'être lisibles depuis Obsidian
- 1 spec **obsolète** (architecture v0.1)

Question : faut-il copier le contenu des specs dans le vault Obsidian, ou les laisser à leur place ?

## Décision

**Les specs restent dans `saas/specs/`. Le vault Obsidian les *référence* (par chemin) mais ne duplique pas leur contenu.**

Exception : les **pépites chiffrées** (codes d'erreur, marges, seuils, formules) sont matérialisées dans les modules Obsidian pour qu'elles soient lisibles d'un coup d'œil — par exemple :
- Les marges 20/12/5 % des préconisations puissance → recopiées dans [[Modules/Energie-Preconisations]]
- Les gaps du kit ENEDIS async → recopiés dans [[Modules/Energie-Consommation]]

Les specs obsolètes sont déplacées dans `saas/specs/_archives/` plutôt que supprimées.

## Conséquences

### Positives
- **Pas de duplication** : pas de risque que le vault Obsidian dérive de la spec source
- **Historique préservé** : `saas/specs/` reste l'emplacement historique versionné, parfait pour `git blame` et `git log`
- **Catalogue clair** : [[Specs]] sert d'aiguillage avec verdict par fichier (à jour / partiel / archive)
- **Lecture rapide** : les pépites chiffrées sont à portée de main dans les modules sans ouvrir un PDF/MD source

### Négatives / coûts assumés
- **Discipline** : une IA qui découvre une nouvelle spec doit penser à l'ajouter au catalogue [[Specs]]
- **Cycle de vie ambigu** : on a décidé que **les nouvelles décisions n'iront PAS dans `saas/specs/`** mais dans `docs/Decisions/` (ADRs) ou les modules. À surveiller pour éviter le drift.

### Alternatives écartées
- **Tout copier dans `docs/`** — Risque de divergence, double maintenance, perte de l'historique git de `saas/specs/`
- **Tout déplacer dans `docs/`** — Casse les références externes et le `git mv` brouillerait l'historique
- **Supprimer `saas/specs/`** — Perd de l'info contextuelle utile (notamment les specs obsolètes qui expliquent pourquoi on en est là)

## Liens

- Catalogue : [[Specs]]
- Session : [[Sessions/2026-05-19 — Intégration specs historiques au vault]]
- Modules enrichis avec pépites : [[Modules/Patrimoine]], [[Modules/Energie-Facturation]], [[Modules/Energie-Preconisations]], [[Modules/Energie-Consommation]], [[Modules/Energie-TURPE]]
