# Cartographie API - outil de gouvernance des endpoints

Outil autonome pour cartographier, annoter et restructurer la surface d'API du backend Po2.

## Ouvrir

Double-cliquer sur `index.html`. Il lit `api_catalog.js` et `vendor/vis-network.min.js` dans le meme dossier.

Pour une verification navigateur plus stricte, servir temporairement le dossier :

```bash
python -m http.server 8765 --bind 127.0.0.1 --directory docs/api-cartographie
```

Puis ouvrir `http://127.0.0.1:8765/index.html`.

## A quoi ca sert

- **Diagramme dynamique** : graphe Routeur -> Prefixe -> Endpoints, base sur le catalogue genere depuis FastAPI.
- **Edition directe** : renommer un noeud, modifier son type, son chemin, son routeur/prefixe, son statut, ses notes.
- **Relations editables** : ajouter une relation entre deux noeuds, modifier son libelle, supprimer une relation.
- **Suppressions locales** : masquer un noeud ou une relation du diagramme sans toucher au code backend.
- **Audit de pertinence** : marquer *utile front*, *utile back*, statut `keep/review/remove/planned`, commentaire.
- **Liste de secours** : vue Liste pour retrouver rapidement un endpoint et le selectionner dans le graphe.
- **Frictions structurelles** : onglet dedie a la dette de liaison (sites, compteurs, prix, inventaires, ENGIE, pronostics).

## Ou vont les modifications

Les annotations et modifications de graphe sont stockees dans le navigateur (`localStorage`) sous
`po2-api-cartographie-graph-v2`.

Le bouton **Exporter** telecharge `api_cartographie_graph.json`, qui contient :

- annotations d'audit ;
- endpoints planifies importes de l'ancien outil ;
- renommages de noeuds ;
- relations personnalisees ;
- noeuds masques ;
- notes de frictions.

Le bouton **Importer** fusionne un export. Les anciens exports `po2-api-cartographie-v1` restent partiellement
compatibles : annotations, endpoints planifies et notes de frictions sont repris.

## Regenerer le catalogue

Depuis `saas/backend` :

```bash
DATABASE_URL="sqlite:///:memory:" python -m app.scripts.build_api_catalog
```

La commande reecrit `docs/api-cartographie/api_catalog.js`. Les annotations locales sont conservees car elles vivent
dans le navigateur/export JSON, pas dans le catalogue genere.

## Fichiers

- `index.html` - interface graphe editable.
- `api_catalog.js` - donnees generees (`window.API_CATALOG`), ne pas editer a la main.
- `vendor/vis-network.min.js` - moteur de graphe embarque pour usage offline.
- `propositions_claude.json` - premiere passe de propositions importables.
- `../11-Analyse-backend-et-socle-refonte-UX.md` - analyse qui fonde cette cartographie.
