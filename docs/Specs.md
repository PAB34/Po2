# Catalogue des specs `saas/specs/`

> Les anciennes specs sont restées dans `saas/specs/` (elles font partie du repo).
> Ce fichier les **catalogue avec un verdict** pour qu'une IA sache rapidement laquelle est encore d'actualité et laquelle est obsolète. Toute synthèse utile a été intégrée aux modules Obsidian correspondants.

Date de l'audit : **2026-05-19**

## Légende

| Statut | Signification |
|---|---|
| ✅ **À jour** | Toujours canonique. À référencer depuis Obsidian. |
| 🟡 **Partiel** | Encore utile mais des bouts sont obsolètes. Synthèse pertinente intégrée au module. |
| 📦 **Archive** | Décrit un état antérieur du produit. Garder pour l'historique mais ne plus lire. |

## Le tableau

| # | Fichier `saas/specs/` | Sujet | Statut | Où chercher la version vivante |
|---|---|---|---|---|
| 01 | `01_Po2_fonctionnalites.md` | Spécifications fonctionnelles v0.2 | 🟡 Partiel | [[Modules/Patrimoine]] (workflow consolidation DGFiP) |
| 02 | `02_architecture_technique.md` | Architecture MVP v0.1 (sans ENEDIS / sans IA) | 📦 Archive | [[02 Architecture]] (état réel à jour) |
| 03 | `03_plan_facturation_optimisation_energie.md` | Plan dev facturation + optim puissance | 🟡 Partiel | [[Modules/Énergie - Facturation]] section "Cadre Hérault Énergies" |
| 04 | `04_mapping_facture_engie.md` | Reverse-engineering exhaustif facture ENGIE | ✅ À jour | Référencée depuis [[Modules/Énergie - Facturation]] |
| 05 | `05_matrice_controles_factures_energie.md` | Matrice de contrôles + codes d'erreur | ✅ À jour | Référencée depuis [[Modules/Énergie - Facturation]] |
| 06 | `06_preconisation_abonnement_v1.md` | Règles V1 préconisations puissance (marges 20/12/5 %) | ✅ À jour | Référencée depuis [[Modules/Énergie - Préconisations]] |
| 07a | `07_plan_execution_factures_decisions.md` | Plan exécution en 5 phases | 🟡 Partiel | [[03 Roadmap fonctionnalités]] (phases 4-5 ouvertes) |
| 07b | `07_referentiel_turpe_7.md` | Référentiel TURPE 7 (CRE 2025-78 / 2026-33) | ✅ À jour | Référencée depuis [[Modules/Énergie - TURPE]] |
| 08 | `08_enedis_async_kit_analysis.json` | Analyse kit portage ENEDIS async + gaps | ✅ À jour | Référencée depuis [[Modules/Énergie - Consommation]] + [[04 État actuel du dev]] |

## Pépites canoniques (à ne JAMAIS perdre)

Si une IA touche aux modules concernés, elle DOIT consulter la spec source :

- **Mapping facture ENGIE** (`04_…md`) — Tableau colonnes page 3, codes index HPSH/HCSH/HPSB/HCSB/Base/Pointe, conversion EUR/kWh ↔ EUR/MWh. Modèle de données candidat plus fin que `EnergyInvoiceAnalysis` actuel — utile pour étendre à DALKIA / TOTAL.
- **Matrice contrôles factures** (`05_…md`) — 40+ codes d'erreur normalisés (`BPU_PRICE_MISMATCH`, `TURPE_VERSION_MISSING`, `POWER_LOAD_CURVE_OVERRUN`, etc.), tolérances chiffrées (0,05 EUR, 0,05 EUR/MWh), règles de rapprochement BPU. Doc canonique du moteur de décision.
- **Préconisations V1** (`06_…md`) — Marges 20 % (kVA, security pour increase), 12 % (kVA, decrease prudent), 5 % (tolérance maintain). Conditions exactes du flag `high` (10 mois de données + 240 jours utilisés). Sinon ces seuils sont perdus.
- **TURPE 7** (`07_referentiel_…md`) — Sources CRE 2025-78 (validité 2025-08-01 → 2026-07-31) et 2026-33. Mapping libellés facture → composantes (`network_management` / `counting` / `withdrawal` / `variable`). Couverture CU4 / MU4 / LU / CUd / MUDTd / C4 / HTA. Date de prochain refresh : 2026-08-01.
- **Kit ENEDIS async** (`08_…json`) — Limites plateforme (5 req/s, 1000/h, fenêtres 7 j CDC, 36 mois ENERGIE/PMAX/IDX). IP allowlist prod (192.196.114.95, 163.116.11.145). **Gaps identifiés** : `CDC_WINDOW_TOO_LARGE`, `UNFILTERED_PRM_BATCH`, `ALL_OR_NOTHING_PUBLICATION`, `NO_PMAX_ASYNC`. Voir [[04 État actuel du dev]] section "Chantiers ouverts".

## Cycle de vie de ces specs

- Les specs sont **versionnées dans git** (`saas/specs/`) → l'historique est dans le repo, pas besoin de les déplacer
- Quand le contenu d'une spec devient totalement obsolète, on la déplace dans `saas/specs/_archives/` (jamais on ne supprime)
- Toute nouvelle décision d'architecture/produit majeure va dans un fichier dédié `docs/Modules/...` ou `docs/Sessions/AAAA-MM-JJ ...`. **On n'écrit plus dans `saas/specs/`**.
- Si une IA met à jour un module en s'appuyant sur une spec source, elle ajoute la ligne `> Source : saas/specs/0X_xxx.md` en début de section du module.
