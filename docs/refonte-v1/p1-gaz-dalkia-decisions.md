# P1 gaz DALKIA — reconstitution par site (OS3 × conso DJU) — décisions

> Rapport « fil du dev » — 2026-07-03. Suite de [[project_gas_budget_revise]] (moteur gaz TE) et du
> sourcing `budget-revise-fixe-variable-sourcing.md` §1.2. Écrit AVANT de coder.

## Décision actée (validée utilisateur)

Reconstituer le **budget/atterrissage P1 gaz DALKIA par site** = **conso attendue (DJU) × prix OS3**,
et non plus un coefficient global (aujourd'hui P1 est EXCLU de la révision dans l'atterrissage → budget = base).
Même patron que le moteur gaz TE, appliqué au CPE avec les sources CPE.

## Le principe

```
budget_P1_site(année) = conso_attendue_site(année) × Pu_OS3(année, tarif_site)
atterrissage_P1_site  = réalisé P1 à date + reste (conso restante DJU × Pu_OS3)
```
- **P1 gaz = quasi tout variable** : l'acompte P1 est un provisionnel de trésorerie, régularisé sur la conso
  réelle × prix. Pas de part fixe séparée à isoler (≠ gaz TE qui a abo/ATRD fixe/CTA).
- `qt_mwh_pci` (relevés) et `pu_eur_mwh_pci` (OS3) sont **tous deux en PCI** → `conso × Pu` direct, sans
  conversion PCS (la conversion PCS ne sert qu'au contrôle vs `base_price` facture, en €/MWhPCS).

## Sources existantes (aucune à créer — on branche)

| Brique | Source |
|---|---|
| Conso par site/mois | `cpe.get_releves(db, site_id, année)` → `CpeGazReleve.qt_mwh_pci` |
| Prix OS3 par tarif/année | `cpe.get_prix_gaz(db, année, tarif)` → `CpePrixGaz.pu_eur_mwh_pci` |
| Tarif du site | `cpe_accounting.resolve_p1_gaz_tarif(db, code_site, city_id)` |
| Conso attendue (climat) | profil DJU DALKIA Montpellier + formule `cpe_atterrissage` (`conso × DJU_projeté/DJU_écoulé`) |
| Cible/repère conso | `cpe.resolve_nb_for_year(db, site, année)` (NB contractuel) en fallback |
| Réalisé P1 | lignes factures P1 CHAUFFAGE (`CpeFinanceLine`, `amount_ht`) |

## Méthode v1 (par site, année Y)

- **Conso attendue** = relevés N-1 du site corrigés du climat (`DJU_normal / DJU_N-1`, profil Montpellier) ;
  fallback = NB contractuel si pas de relevés N-1. (Même logique que le moteur gaz TE.)
- **Prix de référence** = `Pu_OS3(Y, tarif)` (déjà révisé par la formule OS3 côté données).
- **budget P1** = Σ_sites conso_attendue × Pu_OS3.
- **Réalisé** = Σ lignes P1 CHAUFFAGE de l'année Y.
- **Atterrissage** = réalisé + reste projeté (conso restante DJU × Pu_OS3), base = mois RÉELLEMENT
  couverts (fix repris du moteur gaz TE).

## Intégration dans l'atterrissage DALKIA

Le poste **P1** de `accounting_contract_budget.build_contract_budget_landing` : remplacer `coef=1 → budget=base`
par le **budget reconstitué** (Σ sites) ; `revision_detail` = « reconstitué OS3×conso DJU ». P1-ELEC inchangé
(Lot 2 piscines, pas de révision). Détail par site exposé via le nouveau service (endpoint dédié) pour une
future vue « P1 gaz par site ».

## Livrables

1. `app/services/cpe_p1_gaz_revise.py` — reconstitution par site + total (calcul à la volée, aucune migration).
2. Branchement dans `accounting_contract_budget` (poste P1 = budget reconstitué).
3. Endpoint `GET /api/cpe/finances/p1-gaz-revise?year=` (détail par site) — optionnel v1.
4. Tests ciblés (sqlite) : conso attendue DJU, budget = conso×OS3, atterrissage partiel, site sans relevés (NB fallback).

## Hors périmètre v1
- Régularisation acompte/trésorerie (le budget vise le coût énergie, pas l'échéancier d'acomptes).
- Décomposition thermosensible/ECS fine (modèle pur-DJU, comme le moteur gaz TE).
- Formule OS3 recalculée à la main (on lit `get_prix_gaz`, déjà révisé).

## Questions restantes (mineures)
1. Base de conso attendue : relevés N-1 (retenu) vs NB contractuel par défaut ? → N-1, fallback NB.
2. Faut-il une vue front « P1 gaz par site » en v1, ou d'abord juste corriger le poste P1 de l'atterrissage ? → à confirmer.
