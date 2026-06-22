# 2026-06-22 - Boîte de rapprochement patrimoine (PO2-PAT-003)

> IA : Claude (Opus 4.8)
> Branche : `feat/patrimoine-rapprochement`

## Objectif

Combler le maillon faible prioritaire : rattacher les objets externes (compteurs)
au référentiel Site / Bâtiment / Local, sans jamais perdre les introuvables.

## Arbitrages utilisateur

- Sources v1 = **PRM ENEDIS + PCE GRDF** (les compteurs).
- Cible = **Bâtiment d'abord** (repli Site).

## Constat de code

- Référentiel : `sites`, `buildings.site_id`, `locals.building_id`.
- Aucun lien systématique compteur -> patrimoine : `energy_accounting_site_mappings`
  (PRM, 496 lignes) et `gas_pces` (PCE, vide en prod) sans rattachement fiable ;
  `building_meter_links` = saisie manuelle sans file de rapprochement.

## Livré

Backend :
- modèle `PatrimoineMatchItem` + migration `0056_add_patrimoine_match_items` ;
- `services/patrimoine_match.py` : collecte (upsert préservant les décisions),
  proposition de candidat par similarité de tokens (Jaccard + bonus inclusion),
  application de la décision écrivant le lien canonique (`building_meter_links`
  fluid elec/gaz, `gas_pces.building_id`), lien en masse (score >= 90) ;
- endpoints `/api/patrimoine/matches` (list, counts, targets, collect, bulk-link, PATCH).

Frontend :
- page `PatrimoineMatchPage` (`/patrimoine/rapprochements`) : cartes de statut,
  filtres source/statut, collecte, lien-en-masse, lier/ignorer/à-créer + sélecteur
  de cible (recherche bâtiment/site) ;
- entrée de menu Patrimoine > « Rapprochements (file) ».

## Validation (sur staging, copie réelle de la prod)

- `compileall` + import app OK localement (npm absent -> build front validé par CI/staging).
- Déploiement staging de la branche : build front OK (TypeScript compile), migration 0056 appliquée.
- Moteur sur données réelles : **496 PRM collectés, 97 candidats** (beaucoup à score 100,
  ex. GYMNASE FERRARI -> GYMNASE FERRARI), 399 sans candidat (ex. plusieurs « MAIRIE DE SETE »).
- Chaîne HTTP : counts/list/targets OK, 401 sans token.
- Écriture : PATCH « lier » crée le `building_meter_link` (bâtiment, elec, source RAPPROCHEMENT) ;
  lien-en-masse >= 90 a rattaché 23 compteurs supplémentaires.

## Reste à faire / handoff

1. Merger en prod, puis lancer « Collecter les compteurs » + « Lier les évidences ».
2. Étendre les sources : sites CPE (`cpe_sites`), contrats de maintenance.
3. Cible Local (au-delà de Bâtiment/Site).
4. Améliorer le score : matching par adresse en plus du nom.
5. Brancher la fiche bâtiment sur les compteurs ainsi rattachés.
