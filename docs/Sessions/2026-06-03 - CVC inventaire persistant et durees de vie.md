# 2026-06-03 - CVC inventaire persistant et durees de vie

## Contexte

Demande utilisateur : reprendre `/buildings/cvc-import`, car le workflow historique importait trop vite et perdait les lignes non rattachees.

Workflow cible :

1. uploader le fichier terrain ;
2. enregistrer l'inventaire brut en base et l'afficher en tableau ;
3. rattacher chaque ligne a un element patrimoine Site / Batiment / Local ;
4. associer chaque ligne au referentiel de durees de vie issu de `durees_vie_powerbi_base_wide.csv` ;
5. afficher les durees mini / reference / maxi et la duree restante ;
6. ajouter une quantite de fluide frigorigene uniquement pour les categories `Production de froid :` et `Pompes a chaleur Air/Air, Air/Eau, Eau/Eau`.

## Travaux realises

- Migration `0042_extend_cvc_inventory_workflow.py` :
  - `cvc_inventory_items.building_id` devient nullable ;
  - ajout `city_id`, `site_id`, `local_id`, `quantite_fluide_frigorigene` ;
  - FK vers `cities`, `sites`, `buildings`, `locals`.
- Backend CVC :
  - l'import `/api/cvc/import` accepte un mapping vide et persiste toutes les lignes avec designation ;
  - nouveaux endpoints :
    - `GET /api/cvc/imports`
    - `GET /api/cvc/imports/{import_batch}/items`
    - `PATCH /api/cvc/items/{item_id}`
  - recalcul de `duree_vie_restante` apres changement de reference ;
  - exposition `equipment_ref`, mini/reference/maxi, criticite, et flag `requires_refrigerant_quantity`.
- Frontend :
  - refonte de `CvcImportPage.tsx` en tableau editable ;
  - upload = sauvegarde immediate d'un batch ;
  - choix Site / Batiment / Local depuis le patrimoine ;
  - choix du referentiel duree de vie depuis `equipment_references` filtre CVC ;
  - champ fluide kg affiche seulement pour les references concernees.

## Validation

- `python -m compileall app` OK depuis `saas/backend`.
- `python -c "from app.api.routes import cvc ..."` non executable localement : `fastapi` absent.
- `npm run build` non executable localement : `npm` absent et pas de `node_modules` projet.

## Handoff suivant

1. Lancer la CI ou une build frontend dans un environnement avec `npm install`.
2. Appliquer la migration `0042` en environnement de test/prod.
3. Tester `/buildings/cvc-import` avec le vrai fichier CVC :
   - upload sans mapping ;
   - selection d'un import existant ;
   - modification Site / Batiment / Local ;
   - attribution d'une reference duree de vie ;
   - verification du champ fluide sur une PAC ou production de froid.
4. Decider si l'interface doit ajouter un mapping groupe par site source en plus du mapping ligne par ligne.
