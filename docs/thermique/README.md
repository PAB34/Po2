---
read_policy: toujours, en entrée de la documentation de l'outil thermique
---

# Outil thermique — par où commencer

Rangement du 2026-10-02 : la plateforme est reprise selon le **guide du thermicien**, pour devenir un **assistant IA
à la réalisation d'études thermiques, en local avec Claude**. Rien n'a été supprimé : les documents dépassés sont
dans `docs/Archives/thermique/` (avec la raison de chaque archivage).

## 1. Référence de la nouvelle version — `reference/` (à lire en premier)

| Document | Ce qu'il dit |
|---|---|
| `reference/guide-etude-thermique-14-etapes.md` | **Le guide du thermicien** : 14 étapes, une étape + un plan par mission. À garder précieusement, à ne pas modifier sans son accord |
| `reference/refondation-assistant-ia-local-decisions.md` | Le parcours d'une étude (dépôt, tri, lecture, registre des informations, manques, étapes 2 à 14), l'existant face au guide, l'ordre de reprise |
| `reference/regles-metier-validees.md` | **Toutes les règles thermiques déjà tranchées**, en une page : base du fichier de conventions de chaque projet |
| `reference/serveur-mcp-plateforme-decisions.md` | **Premier lot de la nouvelle version** : le serveur MCP de la plateforme (outils, livrables, accès, premier essai) |
| `reference/interaction-claude-plateforme-recherche.md` | Comment Claude travaille avec la plateforme : serveur MCP de la plateforme, connecteur claude.ai, alternatives |
| `reference/convention-nommage-pieces-decisions.md` | Codes des pièces (`PLAN-N1`, `COUPE-AA`…) et tri par l'IA au dépôt du client |
| `reference/analyse-par-missions-decisions.md` | Analyse par missions courtes où l'agent exécute du code d'image ; mesure sur le R+1 |
| `reference/cotes-et-murs-une-geometrie-decisions.md` | Option C, en production : un mur = la composition d'une paroi de local ; coupures, menuiseries posées, surfaces |

## 2. Fonctions en service — `en-service/`

Ce qui décrit des fonctions encore utilisées par le site ou la chaîne d'analyse ; à lire quand on touche à la
fonction concernée.

- **Plans et niveaux** : `calage-autocad-decisions.md`, `nord-et-edition-plan-decisions.md`,
  `superposition-niveaux-decisions.md`, `report-entre-niveaux-decisions.md` (en attente).
- **Coupes et élévations** : `coupes-elevations-fenetre-decisions.md`, `vues-manuelles-decisions.md`,
  `vues-sans-ia-decisions.md`, `cadres-des-vues-decisions.md`, `coupes-elevations-S5-decisions.md` (hauteurs,
  rattachement coupe → locaux), `elevations-S5e-decisions.md`, `verite-terrain-coupes.md` et `.json`.
- **Locaux** : `locaux-decisions.md`, `fiches-locaux-decisions.md`, `nature-locaux-gaine-decisions.md`,
  `creation-suppression-locaux-decisions.md`, `annulation-edition-contour-decisions.md`, `edition-locale-par-lot-decisions.md`,
  `cote-vers-plan-decisions.md`.
- **Menuiseries** : `modeles-menuiseries-decisions.md`, `menuiseries-reunies-exposition-decisions.md`.
- **Étude d'un niveau, versions, éléments** : `etude-niveau-E2-decisions.md`, `edition-pieces-E3-decisions.md`,
  `parcours-par-niveau-E3bis-decisions.md`, `elements-F4-decisions.md`, `annuler-retablir-decisions.md`,
  `espace-thermicien-decisions.md`, `etapes-parois-menuiseries-decisions.md`, `metres-sur-plan-F3-decisions.md`.
- **Ponts thermiques** : `retours-ponts-2026-09-28-decisions.md` (P2, P3, P6 encore ouverts).
- **Chaîne d'analyse actuelle (agents, relais)** : `chaine-analyse-plan-raster.md`, `parcours-enveloppe-decisions.md`,
  `relais-local-F0-decisions.md`.
- **Bibliothèques** (objectif « bibliothèques fiables ») : `bibliotheque-composants-decisions.md`,
  `bibliotheque-projet-decisions.md`.
- **Bilans du 2026-10-02** : `audit-workflow-2026-10-02.md`, `detection-composants-bilan-2026-10-02.md`.

## 3. Archives — `docs/Archives/thermique/`

Pistes abandonnées, décisions remplacées, anciennes boussoles et passations. Index et raisons :
`docs/Archives/thermique/README.md`. Ne pas lire par défaut (règle de `CLAUDE.md`).
