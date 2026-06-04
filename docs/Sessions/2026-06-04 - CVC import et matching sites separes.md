# 2026-06-04 - CVC import et matching sites separes

## Contexte

Le premier increment CVC persistait l'inventaire des l'upload et affichait le rattachement Site/Batiment directement dans le tableau. Retour utilisateur : le workflow attendu est separe entre upload, enregistrement explicite, puis une page dediee de matching des sites importes avec le patrimoine.

## Travaux realises

- `/buildings/cvc-import` separe maintenant le bouton `Uploader le fichier` (preview non persistante) du bouton `Enregistrer l'inventaire`.
- Nouvelle route frontend `/buildings/cvc-import/sites` pour choisir un import, voir les sites source, les suggestions automatiques Site/Batiment, corriger puis appliquer le matching.
- Nouveaux endpoints CVC :
  - `GET /api/cvc/imports/{import_batch}/site-matches`
  - `PATCH /api/cvc/imports/{import_batch}/site-mappings`
- Le matching applique Site/Batiment en masse a toutes les lignes du lot pour un `site_raw`.
- Le tableau inventaire n'edite plus Site/Batiment ligne par ligne ; il affiche les valeurs issues du matching et garde l'edition Local, reference duree de vie et fluide frigorigene.
- Les pages CVC utilisent un gabarit pleine largeur et des tables a colonnes compactes pour reduire le scroll horizontal.

## Validation

- `python -m compileall app` OK depuis `saas/backend`.
- `npm run build` non execute localement : `npm` absent du poste et pas de `node_modules` frontend.

## Handoff suivant

1. Lancer la CI frontend sur GitHub pour valider TypeScript/Vite.
2. Tester en prod ou environnement deploye : upload preview, enregistrement, page matching, application du mapping, retour tableau inventaire.
3. Si le fichier contient des niveaux Batiment/Local fiables, ajouter ensuite une aide de matching plus fine pour preselectionner le batiment/local a partir des colonnes source `BATIMENT`, `NIVEAU`, `LOCAL`.
