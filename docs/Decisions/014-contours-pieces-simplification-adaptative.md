# 014 — Simplification adaptative des contours de pièces

> **Statut** : Accepté
> **Date** : 2026-09-18
> **Décideur(s)** : PAB34 + Codex
> **Session liée** : `[[Sessions/2026-09-18 — Contours de pièces éditables]]`

## Contexte

La polygonisation des limites d'un PDF vectoriel restitue souvent des dizaines de sommets : tableaux
de portes, petits redans et zigzags près d'une baie. Forcer tous ces résultats à quatre côtés corrige
les bureaux rectangulaires, mais détruit les grands espaces réellement en L ou en U. Le thermicien doit
en outre pouvoir ajuster la proposition sur le plan.

## Décision

Le moteur essaie d'abord une reconstruction par quatre droites dominantes avec garde-fous géométriques,
puis, si elle n'est pas fiable, une simplification multi-côtés à tolérance métrique. Le contour brut est
conservé et la correction manuelle devient toujours la nouvelle vérité.

## Conséquences

### Positives

- les pièces ordinaires obtiennent quatre côtés propres portés par les traits du plan ;
- les grands espaces perdent leurs zigzags sans perdre leurs vrais changements de direction ;
- un résultat douteux est refusé plutôt que déformé silencieusement ;
- le recalage manuel reste possible sommet par sommet.

### Négatives / coûts assumés

- la tolérance métrique devra être éprouvée sur d'autres conventions de dessin ;
- un contour très ouvert ou très faux peut encore demander une correction manuelle.

### Alternatives écartées

- **Toujours imposer quatre côtés** — transforme les locaux en L/U et les grands espaces irréguliers.
- **Conserver tout le contour raster** — laisse les zigzags et rend l'édition pénible.
- **Lissage sans garde-fou de surface** — peut produire une zone visuellement propre mais fausse.

## Liens

- Décisions détaillées : `docs/thermique/contours-pieces-decisions.md`
- Moteur : `saas/backend/thermique_moteur/quadrilatere.py`
- Commit : `af9dc199`

