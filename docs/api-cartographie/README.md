# Cartographie API — outil de gouvernance des endpoints

Outil **autonome** (aucun serveur) pour cartographier, auditer et planifier la surface d'API du backend Po2.

## Ouvrir
Double-clique sur **`index.html`** (s'ouvre dans le navigateur). Il lit `api_catalog.js` (même dossier).

## À quoi ça sert
- **Catalogue** : arbre Routeur → Préfixe → Endpoints, régénéré depuis le code (source de vérité).
- **Audit de pertinence** : pour chaque endpoint, marquer *utile en front ?* / *utile en back ?* et un **statut**
  (à garder / à revoir / à retirer / planifié).
- **Planification** : créer un endpoint, **cloner** un endpoint, ou **cloner tout un groupe vers un nouveau
  préfixe** (ex. répliquer le contrat DALKIA en SPIE : remplacer `dalkia` → `spie` dans les chemins).
- **Frictions structurelles** : onglet dédié à la dette de liaison (3 « sites », 3 liens compteur, 2 prix,
  2 inventaires…) avec une note de décision par point.
- **Commentaires / étiquettes** par endpoint.

## Où vont mes annotations
- Stockées dans le **navigateur** (`localStorage`) — elles **survivent à la régénération** du catalogue.
- **Exporter** → télécharge `api_cartographie_annotations.json` (à versionner dans Git si tu veux les partager
  ou les sauvegarder). **Importer** → recharge/fusionne un export.

## Régénérer le catalogue (après évolution du backend)
Depuis `saas/backend` :
```bash
DATABASE_URL="sqlite:///:memory:" python -m app.scripts.build_api_catalog
```
Réécrit `docs/api-cartographie/api_catalog.js` (≈ 279 endpoints). Tes annotations locales sont conservées
(elles sont indexées par `méthode + chemin`).

## Fichiers
- `index.html` — l'outil (autoportant).
- `api_catalog.js` — données générées (`window.API_CATALOG`). **Ne pas éditer à la main.**
- `../11-Analyse-backend-et-socle-refonte-UX.md` — l'analyse qui fonde cette cartographie.
