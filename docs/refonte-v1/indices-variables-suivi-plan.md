# Suivi des indices & variables (page Marchés) — plan

> Décisions « fil du dev » — 2026-07-02. Feature choisie comme 1er incrément V2 : une **table + graphiques
> de suivi des indices/variables** de révision, nouvelle entrée sur `/refonte-v1/marches`. Enabler du
> « coefficient directeur » et du budget révisé fiable (cf. `budget-revise-fixe-variable-sourcing.md`).

## Décisions actées
- **Maille cible du budget révisé (incréments suivants) : site / PRM** (pour brancher conso ENEDIS + parts
  fixes par point de livraison). Ne concerne pas directement cette feature (visualisation), mais oriente la suite.
- **1er incrément = la table de suivi des indices** (visualisation), avant les moteurs.

## Sources existantes (aucune à créer — tout a déjà une API)
| Variable | Granularité | Source / API |
|---|---|---|
| ICHT-IME, FSD2, BT40 (révision DALKIA P2/P3) | trimestre | `GET /cpe/revision-indices?year=` ; obs. `GET /cpe/revision-observations` |
| PEG gaz (fourniture €/MWh) | mois | `GET /billing/gas/revisable` (`GasSupplyRevisablePrice.fourniture_eur_mwh`) |
| TURPE (acheminement élec) | version datée / événements | `GET /billing/turpe/versions`, `GET /bpu/turpe-evolution` |

Graphes : **recharts 2.15.3 déjà présent** ; suivre `components/BpuTimelineChart.tsx` / `PowerCalibrationChart.tsx`.

## Plan (v1 = visualisation, lecture seule)
1. **Backend — endpoint d'agrégation** `GET /api/marches/indices-variables?year_from=&year_to=` (calcul à
   la volée, aucune migration) : normalise les sources hétérogènes en séries temporelles homogènes
   `{code, label, unit, market, points:[{period, value}]}` + les **coefficients observés** par marché/trimestre
   (réutilise `list_revision_indices`, `list_revisable`/PEG, `list_turpe_evolution_events`, `list_revision_observations`).
2. **Schéma Pydantic** + tests ciblés (sqlite) du service d'agrégation.
3. **Frontend** — 3e segment « Indices & variables » sur `/refonte-v1/marches` : par variable, un
   graphe recharts (évolution) + une table des valeurs par période ; regroupées par usage (indices DALKIA,
   PEG gaz, TURPE élec). Lecture seule en v1 (l'édition reste sur les écrans CRUD existants).
4. Pas de « coefficient directeur » calculé en v1 : on **affiche** l'évolution (la tendance devient lisible) ;
   la projection par régression sera un incrément suivant qui s'appuiera sur cette table.

## Hors périmètre v1 (incréments suivants)
- Édition inline des indices dans cette page (les endpoints POST/PUT existent déjà).
- Coefficient directeur (régression/projection) branché sur l'atterrissage.
- Reconstitution fixe/variable par site/PRM (gaz TotalEnergies puis ENGIE/EDF).

## Questions restantes (mineures)
1. Regroupement d'affichage : un graphe par famille (DALKIA / gaz / élec) ou un graphe par variable ?
2. Faut-il afficher, à côté des indices, la **courbe du coefficient observé** (revised/base) par marché
   pour matérialiser directement la tendance qui pilotera le budget révisé ? (recommandé).
