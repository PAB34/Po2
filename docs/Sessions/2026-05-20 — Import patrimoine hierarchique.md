# 2026-05-20 — Import patrimoine hierarchique

## Objectif

Conserver et exploiter les niveaux d'information presents dans les listings patrimoine importes depuis `/buildings/create-edit` : sites, batiments et locaux. Exemple source analyse : `V4_Inventaire_proprietes_SETE_DGFP_251106.xlsm`.

## Constat fichier

Le classeur contient plusieurs onglets :

- `Rapport_Controle` : onglet de controle, premier onglet du fichier, pas l'onglet d'import metier principal.
- `Feuille_fusionnee` : onglet utile avec `Typologie`, `Parent`, `Designation`, `Adresse`, `N° local`, `N°batiment`, `Niveau`, `Porte`, `Droit`.
- `memo` : notes.

Le lecteur precedent prenait le premier onglet Excel par defaut. Il pouvait donc tomber sur `Rapport_Controle` au lieu de `Feuille_fusionnee`.

## Changements livres

- Backend `building_naming.py`
  - selection automatique du meilleur onglet Excel selon presence de colonnes `Adresse`, `Designation`, `Typologie`, `Parent`;
  - detection des colonnes hierarchiques (`Typologie`, `Parent`, `N° local`, parcelle, niveau, porte, droit);
  - preview enrichie avec `asset_type` (`site` / `building` / `local`), parent source et metadonnees local.
- Backend schemas
  - `BuildingImportRow` enrichi avec champs hierarchiques;
  - `BuildingImportPreview` expose `typology_column`, `parent_column`, `hierarchy_detected`, `hierarchy_counts`;
  - `BuildingCreate.create_default_local` permet d'eviter le local principal automatique quand on rattache de vrais locaux importes.
- Modele durable
  - nouvelle table `sites` via migration `0017_add_sites_hierarchy`;
  - nouveau modele SQLAlchemy `Site`;
  - nouvelle colonne `buildings.site_id` avec FK `ON DELETE SET NULL`;
  - nouveaux endpoints `/api/buildings/sites` pour lister/creer/mettre a jour les sites.
- Frontend `BuildingCreateEditPage`
  - les lignes importees gardent leur typologie;
  - validation finale cree/reutilise les sites, cree les batiments avec `site_id`, puis rattache les lignes `LOCAL` au batiment parent detecte;
  - l'import peut rattacher un local a un batiment deja cree dans la session ou deja present en base si le nom/adresse correspond.

## Limite connue

La relation durable `Site -> Building -> Local` existe maintenant cote schema. Il reste a enrichir les ecrans de consultation pour afficher explicitement les sites comme niveau de navigation, pas seulement comme rattachement technique.

## Documentation durable

- [[Modules/Patrimoine]] decrit la hierarchie metier, l'import et les routes `Site`.
- [[03-Roadmap-fonctionnalites]] rappelle que le socle patrimoine inclut maintenant `Site`.
- [[04-Etat-actuel-du-dev]] reference la migration `0017_add_sites_hierarchy`.

## Validation

- OK : `python -m compileall` sur modeles/schemas/services/routes/migration patrimoine modifies
- OK : `git diff --check` sur les fichiers modifies.
- Non fait localement : build frontend complet, car `npm` / `node_modules` ne sont pas disponibles sur le poste.

## Handoff suivant

- Tester l'import reel du fichier `V4_Inventaire_proprietes_SETE_DGFP_251106.xlsm` sur un environnement connecte.
- Ajouter ensuite une UI de navigation/filtre par site dans la liste patrimoine et les pages techniques.
