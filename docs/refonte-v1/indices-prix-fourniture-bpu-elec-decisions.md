# Indices & variables — série « prix fourniture BPU élec par typologie » : décisions

> Doc « fil du dev » — 2026-07-07. Ajout d'une série au **suivi des indices/variables**
> (`/refonte-v1/marches` → sous-onglet « Indices & variables », service `marches_indices_variables.py`,
> front `IndicesVariablesV1.tsx`). S'appuie sur la brique typologie livrée aujourd'hui (PR #46/#48).

## 1. Existant (audité, EN PROD)
Le suivi indices/variables est **déjà livré** (PR #38) : 8 séries — DALKIA (ICHT-IME/FSD2/BT40 +
coefficient observé P2/P3), gaz (PEG), élec (**TURPE** évolution + indice cumulé). Front : 1 carte + 1
graphe **par famille** (`dalkia` / `gaz` / `elec`), axes `period` partagés. Tier ENGIE/EDF → `families=["elec"]`.

**Manque constaté** : côté élec, on ne voit que le **réseau (TURPE)**, pas le **prix de fourniture**. Or
on résout désormais la fourniture BPU **par typologie** (`build_bpu_fourniture_index` dans
`engie_elec_budget_revise`, PR #46). → série naturelle à ajouter.

## 2. Décisions
- **D1 — Nouvelle famille `elec_bpu`** (pas fusionner dans `elec`) : le TURPE est en `%`/indice, la
  fourniture en `€/MWh` → graphe dédié plus lisible. Tier ENGIE/EDF : `families=["elec","elec_bpu"]`.
- **D2 — Une série par typologie canonique** : `HTA` (C1/C2/C3), `BT_SUP36` (C4), `BT_INF36` (C5 bâtiment),
  `EP` (éclairage public). Valeur = **prix fourniture moyen €/MWh par année**, depuis
  `build_bpu_fourniture_index(...)["by_year"]` (moyenne postes, tous fournisseurs élec — c'est le marché
  Hérault Énergie, pas un fournisseur).
- **D3 — Périodicité annuelle** : `period = "YYYY"`, `unit = "EUR/MWh"`, `family = "elec_bpu"`,
  `market = "Electricite"`. Source = « BPU Hérault Énergie (moyenne postes, tous fournisseurs) ».
- **D4 — Lecture seule** : aucune saisie, aucune migration ; réutilise l'index existant.

## 3. Périmètre / limites (assumées)
- La moyenne par (typologie, année) lisse les postes et, pour l'ancien marché, les classes C1/C2/C3 (déjà
  le cas dans l'atterrissage). Objectif = **tendance de prix**, pas un tarif contractuel exact.
- Pas de nouvel indice OS3 ici (item séparé) ni d'enrichissement PEG (donnée).

## 4. Fichiers
- Back : `services/marches_indices_variables.py` (+ `_bpu_fourniture_series`, import
  `build_bpu_fourniture_index` + `load_historical_bpu_prices`). Schéma inchangé (série générique).
- Front : `features/marches/MarketsBudgetPageV1.tsx` (familles ENGIE/EDF) + `IndicesVariablesV1.tsx`
  (`FAMILY_LABELS`/`FAMILY_DETAILS` `elec_bpu`). Type `MarketVariableSeriesV1.family` = string (inchangé).
- Tests : `tests/test_marches_indices_variables*.py` (ou nouveau) : la série `elec_bpu` a des points €/MWh
  par typologie/année.
