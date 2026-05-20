# 2026-05-20 — Fiche bâtiment centrale, occupation, CVC et BACS

## Contexte

L'utilisateur souhaite faire évoluer Po2 vers une fiche bâtiment centrale :

- rattachement de chaque bâtiment aux compteurs électricité, gaz et eau ;
- collecte et modification des plannings d'occupation par les usagers/responsables de site ;
- alerte d'un tiers final en cas de modification ;
- collecte des programmations CVC, températures de départ et consignes ;
- à terme, évaluation de la classe GTB/BAC vis-à-vis du décret BACS à partir de l'inventaire CVC et du tableau 6 NF EN ISO 52120.

## Sources locales vérifiées

- `saas/CVC/PF - Annexe n°9 - Occupation des bâtiments.xlsx`
  - 78 lignes.
  - Colonnes : Code, Nom du site, Lot, Occupation, Nettoyage, Fermetures, Responsable, Tel, Mail.
- `saas/CVC/listing materiels V2.xlsx`
  - 1301 lignes.
  - Colonnes : SITE, BATIMENT, NIVEAU, LOCAL, DESIGNATION, STATUT, ETAT SANTE, QTE QTE RELEVEE, FAMILLE, MARQUE, MODELE, DATE MES.
- `saas/CVC/TABLEAU 6 NORME NF EN ISO 52120.pdf`
  - 11 pages.
  - Source future à transformer en référentiel tabulaire pour l'évaluation GTB/BACS.

## Mises à jour Obsidian

- `docs/Backlog.md`
  - Ajout de `PO2-METER-001`.
  - Ajout de `PO2-CVC-001`.
  - Transformation de l'occupation en `PO2-OCC-001`, `PO2-OCC-002`, `PO2-OCC-003`.
  - Remplacement de `PO2-TEMP-001` par `PO2-CVC-002`.
  - Ajout de `PO2-BACS-001` en statut Futur.
- `docs/03-Roadmap-fonctionnalites.md`
  - Enrichissement des sections occupation et programmation CVC.
  - Ajout des sections GTB/BACS et rattachement compteurs.
  - Ajout de la vision "fiche bâtiment centrale".
- `docs/Modules/Gestion-technique.md`
  - Ajout des sources CVC locales.
  - Ajout des pistes modèle pour compteurs, occupation, portail usagers, programmation CVC et BACS.
- `docs/Modules/Patrimoine.md`
  - Ajout de la vision fiche bâtiment centrale et du modèle cible `BuildingMeterLink`.
- `docs/00-Index.md`
  - Mise à jour des descriptions des modules Patrimoine et Gestion technique.

## Recommandation

Ordre de développement conseillé :

1. `PO2-METER-001` — rattachement compteurs fluides aux bâtiments.
2. `PO2-OCC-001` — import occupation depuis l'annexe 9.
3. `PO2-CVC-001` — import/rapprochement inventaire matériel CVC.
4. `PO2-CVC-002` — programmation CVC et températures.
5. `PO2-OCC-002` / `PO2-OCC-003` — portail usagers + alertes.
6. `PO2-BACS-001` — moteur de classe GTB/BACS, seulement une fois les données socles fiables.

## Handoff suivant

Ne pas lancer `PO2-BACS-001` en premier. Le tableau 6 NF EN ISO 52120 doit devenir une table de référence plus tard, mais le prérequis métier est d'abord de fiabiliser :

- le rapprochement bâtiments ↔ compteurs ;
- le rapprochement bâtiments ↔ occupation ;
- le rapprochement bâtiments ↔ inventaire CVC terrain.
